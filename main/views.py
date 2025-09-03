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
from selenium.common.exceptions import TimeoutException, ElementClickInterceptedException
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
import redis

env = environ.Env()
environ.Env.read_env(os.path.join(Path(__file__).resolve().parent.parent, '.env'))  # point to django root dir


class test_close_map(APIView):
    def get(self, request):
        from selenium.webdriver.common.action_chains import ActionChains
        import time
        #get_mongo_db()['test'].insert_one({'message': 'hi2'})
        url = "https://divar.ir/s/tehran/buy-apartment"
        #thread_name = 'test'
        driver = test_setup()
        try:
            driver.get(url)  # Load the web page
            
            # Wait for page to load completely
            time.sleep(3)
            
            # Multiple XPath strategies to find the close map button
            xpaths_to_try = [
                # Strategy 1: Based on your HTML structure
                "//div[@role='button' and contains(@class, 'absolute')]//div[contains(text(), 'بستن نقشه')]",
                # Strategy 2: More specific with kt-fab-button class
                "//div[@role='button']//div[contains(@class, 'kt-fab-button') and contains(text(), 'بستن نقشه')]",
                # Strategy 3: Looking for the icon and text combination
                "//div[@role='button']//div[contains(@class, 'kt-fab-button')]//i[contains(@class, 'kt-icon-close')]/parent::div",
                # Strategy 4: Direct text search
                "//div[contains(text(), 'بستن نقشه')]",
                # Strategy 5: Your original xpath
                "//div[@role='button'][.//div[contains(@class,'kt-fab-button--raised') and normalize-space(text())='بستن نقشه']]",
                # Strategy 6: Looking for the parent container
                "//div[contains(@class, 'absolute') and @role='button']"
            ]
            
            btn2 = None
            successful_xpath = None
            
            for i, xpath in enumerate(xpaths_to_try):
                try:
                    logger.info(f"Trying XPath strategy {i+1}: {xpath}")
                    btn2 = WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.XPATH, xpath)))
                    successful_xpath = xpath
                    logger.info(f"Successfully found element with strategy {i+1}")
                    break
                except TimeoutException:
                    logger.warning(f"XPath strategy {i+1} failed, trying next...")
                    continue
                except Exception as e:
                    logger.warning(f"XPath strategy {i+1} failed with error: {e}")
                    continue
            
            if btn2 is None:
                logger.error("Could not find the close map button with any strategy")
                return Response({'error': 'Button not found'})
            
            logger.info(f"Found element HTML: {btn2.get_attribute('outerHTML')}")
            logger.info(f"Element location: {btn2.location}")
            logger.info(f"Element size: {btn2.size}")
            logger.info(f"Element displayed: {btn2.is_displayed()}")
            logger.info(f"Element enabled: {btn2.is_enabled()}")
            
            # Scroll element into view
            driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", btn2)
            time.sleep(1)
            
            # Try multiple click strategies
            click_strategies = [
                ("Regular click", lambda: btn2.click()),
                ("JavaScript click", lambda: driver.execute_script("arguments[0].click();", btn2)),
                ("ActionChains click", lambda: ActionChains(driver).move_to_element(btn2).click().perform()),
                ("ActionChains with pause", lambda: ActionChains(driver).move_to_element(btn2).pause(0.5).click().perform()),
                ("Force JavaScript click", lambda: driver.execute_script("arguments[0].dispatchEvent(new MouseEvent('click', {bubbles: true}));", btn2))
            ]
            
            for strategy_name, click_func in click_strategies:
                try:
                    logger.info(f"Attempting {strategy_name}")
                    click_func()
                    logger.info(f"Successfully clicked using {strategy_name}")
                    time.sleep(2)  # Wait to see if click was successful
                    
                    # Check if map is closed by looking for the button disappearing
                    # or page changes
                    try:
                        WebDriverWait(driver, 3).until_not(EC.element_to_be_clickable((By.XPATH, successful_xpath)))
                        logger.info("Map appears to be closed (button disappeared)")
                        break
                    except:
                        logger.info("Button still visible, checking if map state changed")
                        # You could add additional checks here to verify if map is closed
                        break
                        
                except ElementClickInterceptedException as e:
                    logger.warning(f"{strategy_name} failed with intercepted exception: {e}")
                    continue
                except Exception as e:
                    logger.warning(f"{strategy_name} failed: {e}")
                    continue
            
            logger.info(f"Click operation completed")
            time.sleep(5)  # Reduced from 40 seconds for testing

        except Exception as e:
            logger.error(f"failed, error: {e}")
        finally:
            driver.quit()
        #title = driver.title
        #dc = get_files_for_update_redis()
        #print('1111111111111', type(dc), dc)
        #provide_update_file()
        return Response({'success': 'L'})


class Test(APIView):
    """Simple fallback approach for closing the map button"""
    def get(self, request):
        from selenium.webdriver.common.action_chains import ActionChains
        import time
        
        url = "https://divar.ir/s/tehran/buy-apartment"
        driver = test_setup()
        try:
            driver.get(url)
            time.sleep(5)  # Wait for page to load

            xpath = (
            "//div[@role='button']"
            "[.//div[contains(@class,'kt-fab-button--raised') "
            "and normalize-space(text())='بستن نقشه']]"
        )
            btn = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, xpath))
                )
            btn.click()
            time.sleep(2)
        except Exception as e:
            logger.error(f"Simple test failed: {e}")
        finally:
            driver.quit()
            
        return Response({'success': 'Simple test completed'})


class CrawlView(APIView):
    def get(self, request):
        logger.info(f"logger working")
        location_to_search = 'کیانشهر'  # request.data['location_to_search']  # like 'کیانشهر'
        get_files(location_to_search=location_to_search, max_files=settings.MAX_FILE_CRAWL)
        return Response({"status:": "program returned"})
