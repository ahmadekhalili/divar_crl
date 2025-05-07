from django.shortcuts import render
from django.http import HttpResponse

from rest_framework.response import Response
from rest_framework.views import APIView

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import logging

from .crawl import crawl_files
from .serializers import FileMongoSerializer
from .mongo_client import get_mongo_db, ConnectionFailure
from .crawl_setup import advance_setup, setup
from .methods import get_next_sequence

logger = logging.getLogger('django')

from pathlib import Path
from urllib.parse import quote_plus
import pymongo
import os
import environ

env = environ.Env()
environ.Env.read_env(os.path.join(Path(__file__).resolve().parent.parent.parent, '.env'))


def test(request):
    #get_mongo_db()['test'].insert_one({'message': 'hi2'})
    url = "https://divar.ir/s/tehran/buy-apartment"
    #driver = advance_setup()
    #driver.get(url)  # Load the web page
    #num = get_next_sequence(get_mongo_db(), 'test')
    return HttpResponse(f"{num}")


class CrawlView(APIView):
    def get(self, request):
        logger.info(f"logger working")
        location_to_search = 'کیانشهر'  # request.data['location_to_search']  # like 'کیانشهر'
        files, errors = crawl_files(location_to_search, 1)
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
                    return Response({'files_saved': files, 'files_failed': errors})
                else:
                    logger.error(f"for is not valid, error: {s.errors}")
                    return Response(s.errors)
            else:
                logger.info(f"there isn't any unique titles.")
                return Response({'files_failed': errors})
        except Exception as e:
            return Response(f"Unexpected exception: {e}")
