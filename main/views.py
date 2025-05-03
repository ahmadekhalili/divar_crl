from django.shortcuts import render
from django.http import HttpResponse

from rest_framework.response import Response

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import logging

from .crawl import setup, advance_setup, crawl_files
from .serializers import FileMongoSerializer
from .mongo_client import get_mongo_db, ConnectionFailure

logger = logging.getLogger('django')

from pathlib import Path
from urllib.parse import quote_plus
import pymongo
import os
import environ

env = environ.Env()
environ.Env.read_env(os.path.join(Path(__file__).resolve().parent.parent.parent, '.env'))


def test(request):
    get_mongo_db()['test'].insert_one({'message': 'hi2'})
    url = "https://divar.ir/s/tehran/buy-apartment"
    driver = advance_setup()
    driver.get(url)  # Load the web page
    time.sleep(2)

    # add location 'tehran' to the site
    cookies = [{"name": "city", "value": "tehran", "domain": ".divar.ir"},
               {"name": "multi-city", "value": "tehran%7C", "domain": ".divar.ir"}]
    for cookie in cookies:
        driver.add_cookie(cookie)
    driver.refresh()
    logger.info(f"driver refreshed (for cookie)")
    return HttpResponse('asd')


def crawl_view(request):
    logger.info(f"logger working")
    location_to_search = 'کیانشهر'  # request.data['location_to_search']  # like 'کیانشهر'
    files, errors = crawl_files(location_to_search, 2)
    unique_titles, unique_files = [], []
    for file in files:  # field unique validation only done when save file singular (so we have to validate here)
        if file['title'] not in unique_titles:
            cleaned_file = {key: value for key, value in file.items() if value is not None}
            unique_titles.append(cleaned_file['title'])
            unique_files.append(cleaned_file)
    if unique_titles:
        s = FileMongoSerializer(data=unique_files, request=request, many=True)
        if s.is_valid():
            files = s.save()
            return Response({'files_saved': files, 'files_failed': errors})
        else:
            return Response(s.errors)
    else:
        return Response({'files_failed': errors})
