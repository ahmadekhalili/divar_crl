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

from .crawl import get_files, test_crawl
from .crawl_setup import advance_setup, test_setup, uc_replacement_setup
from .serializers import FileMongoSerializer
from .mongo_client import get_mongo_db, ConnectionFailure
from .methods import add_to_redis, write_by_django, set_uid_url_redis

logger = logging.getLogger('web')

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
    driver = uc_replacement_setup()
    driver.get(url)  # Load the web page
    #test_crawl(url="https://divar.ir/v/%D9%81%D8%B1%D9%88%D8%B4-%D8%A2%D9%BE%D8%A7%D8%B1%D8%AA%D9%85%D8%A7%D9%86-%DB%B1%DB%B0%DB%B4-%D9%85%D8%AA%D8%B1%DB%8C-%DB%B2-%D8%AE%D9%88%D8%A7%D8%A8%D9%87-%D8%AF%D8%B1-%D9%86%D8%B8%D8%A7%D9%85-%D8%A2%D8%A8%D8%A7%D8%AF/AafYQfSu")
    #set_uid_url_redis([('uid1', 'qweqwe'), ('uid1', 'tretert')])
    return HttpResponse(f"success")


class CrawlView(APIView):
    def get(self, request):
        logger.info(f"logger working")
        location_to_search = 'کیانشهر'  # request.data['location_to_search']  # like 'کیانشهر'
        get_files(location_to_search=location_to_search, max_files=settings.MAX_FILE_CRAWL)
        return Response({"status:": "program returned"})
