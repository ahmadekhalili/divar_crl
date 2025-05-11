from django.shortcuts import render
from django.http import HttpResponse
from django.conf import settings
from django.core.cache import cache
from rest_framework.response import Response
from rest_framework.views import APIView

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import logging

from .crawl import crawl_files, test_crawl
from .serializers import FileMongoSerializer
from .mongo_client import get_mongo_db, ConnectionFailure
from .crawl_setup import advance_setup, setup
from .methods import add_to_redis

logger = logging.getLogger('django')

from pathlib import Path
from urllib.parse import quote_plus
import pymongo
import os
import environ

env = environ.Env()
environ.Env.read_env(os.path.join(Path(__file__).resolve().parent.parent.parent, '.env'))


def test(request):
    re = add_to_redis({"aaaaa": 33})
    #get_mongo_db()['test'].insert_one({'message': 'hi2'})
    url = "https://divar.ir/s/tehran/buy-apartment"
    #driver = advance_setup()
    #driver.get(url)  # Load the web page
    #test_crawl(url="https://divar.ir/v/%D9%81%D8%B1%D9%88%D8%B4-%D8%A2%D9%BE%D8%A7%D8%B1%D8%AA%D9%85%D8%A7%D9%86-%DB%B1%DB%B0%DB%B4-%D9%85%D8%AA%D8%B1%DB%8C-%DB%B2-%D8%AE%D9%88%D8%A7%D8%A8%D9%87-%D8%AF%D8%B1-%D9%86%D8%B8%D8%A7%D9%85-%D8%A2%D8%A8%D8%A7%D8%AF/AafYQfSu")

    return HttpResponse(f"{re}")


class CrawlView(APIView):
    def get(self, request):
        logger.info(f"logger working")
        location_to_search = 'کیانشهر'  # request.data['location_to_search']  # like 'کیانشهر'
        files, errors = crawl_files(location_to_search, settings.MAX_FILE_CRAWL)
        unique_titles, unique_files = [], []
        for file in files:  # field unique validation only done when save file singular (so we have to validate here)
            if file['title'] not in unique_titles:
                cleaned_file = {key: value for key, value in file.items() if value is not None}
                unique_titles.append(cleaned_file['title'])
                unique_files.append(cleaned_file)
        try:
            if unique_titles:
                logger.info(f"--all crawled files: {len(unique_titles)}, duplicates: {len(files)-len(unique_titles)}")
                s = FileMongoSerializer(data=unique_files, many=True)
                if s.is_valid():
                    logger.info(f"for is valid")
                    files = s.save()
                    return Response({'files_saved': len(files), 'files_failed': errors})
                else:
                    logger.error(f"for is not valid, error: {s.errors}")
                    return Response(s.errors)
            else:
                logger.info(f"there isn't any unique titles.")
                return Response({'files_failed': errors})
        except Exception as e:
            return Response(f"Unexpected exception: {e}")
