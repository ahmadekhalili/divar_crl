from django .conf import settings

import logging
import os
import re
import random
import time
import environ
import threading
from pathlib import Path

from selenium import webdriver
from fake_useragent import UserAgent
#import undetected_chromedriver as uc
from selenium.webdriver import ActionChains
from selenium.webdriver.chrome import webdriver as chrome_webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from seleniumwire import webdriver as wire_webdriver

from .methods import HumanMouseMove, retry_func, get_driver_from_redis, set_driver_to_redis
from .serializers import logger_file
from .redis_client import REDIS

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env()
env.read_env(os.path.join(BASE_DIR, '.env'))
logger = logging.getLogger('web')
driver_logger = logging.getLogger('driver')
logger_separation = logging.getLogger("web_separation")
logger_file = logging.getLogger('file')

lock_thread = threading.Lock()


@retry_func(max_attempts=settings.RETRY_FOR_DRIVER, delay=20, fail_message_after_attempts='No free driver', loger=driver_logger)
def get_driver_chrome(thread_name=None):
    """Try to acquire a free driver in a thread-safe way. Return paths or False if none.
        redis structure is like: ["uid": <thread_name>, "driver_path": <driver_path>, "chrome_path": <chrome_path>],
        each calling of get_driver_chrome fill the thread name on a blank uid"""
    with lock_thread:
        DRIVERS_CHROMS = get_driver_from_redis()
        driver_logger.debug(f"content of DRIVERS_CHROMS from redis: {DRIVERS_CHROMS}")

        if not thread_name:
            thread_name = "main_thread"
        for idx, item in enumerate(DRIVERS_CHROMS):
            if not item.get('uid'):
                item['uid'] = thread_name
                REDIS.json().set('drivers_chromes', f'[{idx}]', item)
                driver_logger.info(f"Successfully obtained  and set driver. thread_name: {thread_name}")
                return item['driver_path'], item['chrome_path']
        else:
            driver_logger.info("All drivers are busy, will retry...", extra={"thread_name": threading.current_thread().name})
            return False


#@retry_func(max_attempts=1)  # dont want to show "Not found any driver to " additionally
def set_driver_to_free(thread_name=None, is_saved_to_redis=None, errors=None):  # for main thread is_saved_to_redis should be None
    if not thread_name:
        thread_name = "main_thread"

    with lock_thread:
        DRIVERS_CHROMS = get_driver_from_redis()

        message_status = "Successfully saved to Redis" if is_saved_to_redis else "Failed to save to Redis" if is_saved_to_redis is False else ""
        for item in DRIVERS_CHROMS:
            if item.get('uid') == thread_name:
                item['uid'] = None
                driver_logger.info(f"{message_status} and exit. set driver for free uid: {thread_name}. errors: {errors}", extra={"thread_name": threading.current_thread().name})
                set_driver_to_redis(DRIVERS_CHROMS)
                break
        else:      # if not found any item.get('uid') in whole lists
            driver_logger.info(f"Not found any driver to free up. {message_status} (uid={thread_name}). errors: {errors}")
        free_drivers_count = len([True for item in DRIVERS_CHROMS if item['uid'] is None])
        driver_logger.info(f"Totally free drivers: {free_drivers_count}/{len(DRIVERS_CHROMS)}")
        return True   # required for @retry_func functionality


def _apply_stealth_cdp(driver: webdriver.Chrome) -> None:
    """
    Use Chrome DevTools Protocol to redefine navigator properties
    before any script runs on each page.
    """
    script = r"""
    // overwrite the `navigator.webdriver` property to undefined
    Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
    // mock plugins and languages
    Object.defineProperty(navigator, 'plugins', { 
        get: () => [1, 2, 3, 4, 5] 
    });
    Object.defineProperty(navigator, 'languages', {
        get: () => ['en-US', 'en']
    });
    """
    driver.execute_cdp_cmd(
        "Page.addScriptToEvaluateOnNewDocument",
        {"source": script}
    )

def test_setup():
    options = Options()
    service = Service(executable_path=env("DRIVER_PATH1_win"))
    options.binary_location = env("CHROME_PATH1_win")
    #options.add_argument("--headless=new")

    # Optional but useful Chrome args
    #options.add_argument("--incognito")
    options.add_argument("--no-sandbox")
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')

    driver = webdriver.Chrome(service=Service(executable_path=env("DRIVER_PATH1_win")), options=options)

    driver.maximize_window()
    return driver


def advance_setup():
    service = Service(driver_path=settings.DRIVER_PATH1)

    options = uc.ChromeOptions()

    options.binary_location = settings.CHROME_PATH1
    #options.add_argument("--headless")
    #options.add_argument(f"user-data-dir={env('CHROME_PROFILE_PATH')}")
    #options.add_argument(f"--profile-directory={env('CHROME_PROFILE_FOLDER')}")
    profile_path = env("CHROME_PROFILE_PATH")
    options.add_argument(f"--user-data-dir={profile_path}")
    options.add_argument(f"--profile-directory={env('CHROME_PROFILE_FOLDER')}")
    #options.add_argument("--disable-extensions")
    options.add_argument('--no-sandbox')
    #options.add_argument('--disable-dev-shm-usage')
    #options.add_argument('--disable-gpu')

    #options.add_argument("--disable-webrtc-encryption")
    #options.add_argument("--disable-ipv6")
    #options.add_argument("--disable-blink-features=AutomationControlled")
    #options.add_argument("--lang=en-US")
    #options.add_argument("--disable-geolocation")

    driver = uc.Chrome(options=options)
    #print('driver path: ', driver.service.path)
    driver.set_window_size(1920, 1080)
    # user_agent = UserAgent().random  #"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
    # options.add_argument(f"user-agent={user_agent}")  # implemented inside crawl.py (via 'set_random_agent') here unstable
    #stealth(driver, languages=["en-US", "en"], vendor="Google Inc.", platform="Win32", webgl_vendor="Intel Inc.", renderer="Intel Iris OpenGL Engine", fix_hairline=True, run_on_insecure_origins=True, hide_webdriver=True)
    # Open a blank page to start with a clean slate
    logger.debug('before open the page')
    #driver.get("about:blank")
    logger.debug('blank opended')
    # Create an ActionChains instance
    actions = ActionChains(driver)
    # Optionally, position the mouse at a central point (this is our starting point)
    start_x, start_y = 1078, 521
    logger.debug('ActionChains opended')
    actions.move_by_offset(start_x, start_y).perform()
    logger.debug('move_by_offset run')
    time.sleep(0.41)  # a slight pause to mimic natural behavior
    actions = HumanMouseMove.human_mouse_move(actions, (random.randint(0, 500), random.randint(0, 500)), (random.randint(0, 500), random.randint(0, 500)))
    logger.debug('human_mouse_move was run')
    driver.maximize_window()
    return driver


def uc_replacement_setup(thread_name=None):
    driver_chrome = get_driver_chrome(thread_name)
    if not driver_chrome:
        return None

    driver_load_retries = 2
    for i in range(driver_load_retries):
        try:
            options = Options()
            service = Service(executable_path=driver_chrome[0])
            options.binary_location = driver_chrome[1]
            options.set_capability("goog:loggingPrefs", {"performance": "ALL"})  # trace network
            if settings.HEADLESS:
                options.add_argument("--headless=new")  # if you need headless
            #profile_dir = env('CHROME_PROFILE_PATH').format(profile_num=my_profile)
            #options.add_argument(f"--user-data-dir={profile_dir}")
            #options.add_argument(f"--profile-directory={env('CHROME_PROFILE_FOLDER')}")
            # profile_path = os.path.join(os.getenv('APPDATA'), 'Local', 'Google', 'Chrome', 'User Data', 'Profile5')
            # options.add_argument(f"user-data-dir={profile_path}")
            # options.add_argument("--disable-extensions")
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-gpu')

            # –– 2) Anti-detection flags
            options.add_argument("--disable-blink-features=AutomationControlled")
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_experimental_option("useAutomationExtension", False)

            # –– 3) Random User-Agent
            USER_AGENT = random.choice(settings.AGENTS)  # randomly select one of lists

            #USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
            #ua = UserAgent().random
            options.add_argument(f"--user-agent={USER_AGENT}")  # refresh inside crawl.py (via 'set_random_agent')

            # –– 4) Insecure-certs & any other “caps” via Options
            options.set_capability("acceptInsecureCerts", True)
            # If you had other caps: options.set_capability("someCap", someValue)

            driver = webdriver.Chrome(service=service, options=options)
            break
        except:
            logger.error(f"Failed initializing driver. attempts: {i+1}/{driver_load_retries}")
            time.sleep(2)
            if i+1 == driver_load_retries:
                return None  # prevent raise stealth error in _apply_stealth_cdp(driver)
    try:
        # –– 6) CDP stealth patch + window sizing
        _apply_stealth_cdp(driver)
        driver.execute_cdp_cmd("Network.enable", {})
        driver.execute_cdp_cmd("Network.clearBrowserCache", {})
        driver.execute_cdp_cmd("Network.clearBrowserCookies", {})
        #stealth(driver, languages=["en-US", "en"], vendor="Google Inc.", platform="Win32", webgl_vendor="Intel Inc.", renderer="Intel Iris OpenGL Engine", fix_hairline=True, run_on_insecure_origins=True, hide_webdriver=True)
        # Open a blank page to start with a clean slate
        #logger.debug('before open the page')
        #driver.get("about:blank")
        # Create an ActionChains instance
        #actions = ActionChains(driver)
        # Optionally, position the mouse at a central point (this is our starting point)
        #start_x, start_y = 1078, 521
        #logger.debug('ActionChains opended')
        #actions.move_by_offset(start_x, start_y).perform()
        #logger.debug('move_by_offset run')
        #time.sleep(0.41)  # a slight pause to mimic natural behavior
        #actions = HumanMouseMove.human_mouse_move(actions, (random.randint(0, 500), random.randint(0, 500)), (random.randint(0, 500), random.randint(0, 500)))
        #logger.debug('human_mouse_move was run')
        if not settings.HEADLESS:
            driver.maximize_window()    # dont use in headless
    except Exception as e:     # highly import quite driver safly and dont lost and let it open indie tones of blocks of try exception...
        logger.error(f"failed hide mecanism after driver creation. quite driver safty. reason: {e}")
        driver.quit()
        driver = None
    return driver


def setup_driver():
    # open the chrome with current cookies
    chrome_options = Options()
    if os.name == 'nt':  # project running in a Windows os
        chrome_profile_path = "C:/Users/akh/AppData/Local/Google/Chrome/User Data/Profile 4"  # your Chrome profile

    else:  # project running in a linux os
        chrome_profile_path = "/root/.config/google-chrome/myprofile"
    if not os.path.exists(chrome_profile_path):  # need to be created before running the crawler
        raise FileNotFoundError(f"The specified Chrome profile path does not exist: {chrome_profile_path}")
    chrome_options.add_argument("--headless")  # crawl without graphical interface, used in linux servers
    chrome_options.add_argument(f"user-data-dir={chrome_profile_path}")
    chrome_options.add_argument("--disable-extensions")

    chrome_options.add_argument('--no-sandbox')  # these args required in linux servers (headless mode)
    chrome_options.add_argument('--disable-dev-shm-usage')  # Fixes error related to shared memory usage
    chrome_options.add_argument('--remote-debugging-port=9222')  # Optional: enables debugging port
    chrome_options.add_argument('--disable-gpu')  # Disables GPU hardware acceleration (useful for headless mode)
    return webdriver.Chrome(options=chrome_options)
