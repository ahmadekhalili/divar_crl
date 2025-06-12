from central_logging import init_central_logging, get_logger
init_central_logging()

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

from .crawl import get_files, test_crawl, provide_update_file
from .crawl_setup import advance_setup, test_setup, uc_replacement_setup, set_driver_to_free
from .serializers import FileMongoSerializer
from .mongo_client import get_mongo_db, ConnectionFailure
from .methods import add_final_card_to_redis, write_by_django, set_uid_url_redis, logger_file, get_files_for_update_redis
from .redis_client import REDIS as r

logger = logging.getLogger('web')
logger_separation = logging.getLogger("web_separation")
logger_file = logging.getLogger('file')

from pathlib import Path
from urllib.parse import quote_plus
import pymongo
import os
import environ
import threading
import requests

env = environ.Env()
environ.Env.read_env(os.path.join(Path(__file__).resolve().parent.parent.parent, '.env'))
import redis

class test(APIView):
    def get(self, request):
        #get_mongo_db()['test'].insert_one({'message': 'hi2'})
        #url = "https://divar.ir/s/tehran/buy-apartment"
        #thread_name = 'test'
        #driver = test_setup()
        #driver.get(url)  # Load the web page
        #title = driver.title
        dc = get_files_for_update_redis()
        print('1111111111111', type(dc), dc)
        #provide_update_file()
        return Response({'success': 'L'})


class CrawlView(APIView):
    def get(self, request):
        logger.info(f"logger working")
        location_to_search = 'کیانشهر'  # request.data['location_to_search']  # like 'کیانشهر'
        get_files(location_to_search=location_to_search, max_files=settings.MAX_FILE_CRAWL)
        return Response({"status:": "program returned"})
