from django .conf import settings

import logging
import os
import random
import time
import environ
import threading
from pathlib import Path

from selenium import webdriver
from fake_useragent import UserAgent
import undetected_chromedriver as uc
from selenium.webdriver import ActionChains
from selenium.webdriver.chrome import webdriver as chrome_webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities

from .methods import HumanMouseMove, retry_func
from .serializers import logger_file

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env()
env.read_env(os.path.join(BASE_DIR, '.env'))
logger = logging.getLogger('web')
driver_logger = logging.getLogger('driver')

def load_drivers(driver_counts):
    for i in range(1, driver_counts + 1):
        pass


lock_thread = threading.Lock()
DRIVERS_CHROMS = [{'uid': None, 'driver_path': env('DRIVER_PATH1'), 'chrome_path': env('CHROME_PATH1')},
                  {'uid': None, 'driver_path': env('DRIVER_PATH2'), 'chrome_path': env('CHROME_PATH2')},
                  {'uid': None, 'driver_path': env('DRIVER_PATH3'), 'chrome_path': env('CHROME_PATH3')},
                  {'uid': None, 'driver_path': env('DRIVER_PATH4'), 'chrome_path': env('CHROME_PATH4')},
                  {'uid': None, 'driver_path': env('DRIVER_PATH5'), 'chrome_path': env('CHROME_PATH5')},]

driver_logger.debug(f"content of DRIVERS_CHROMS: {DRIVERS_CHROMS}")
@retry_func(max_attempts=settings.RETRY_FOR_DRIVER, delay=20, fail_message_after_attempts='No free driver', loger=driver_logger)
def get_driver_chrome(uid=None):
    """Try to acquire a free driver in a thread-safe way. Return paths or False if none."""
    if not uid:
        uid = "main_thread"
    with lock_thread:
        for item in DRIVERS_CHROMS:
            if not item.get('uid'):
                item['uid'] = uid
                driver_logger.info(f"Successfully obtained driver. card uid: {uid}", extra={"thread_name": threading.current_thread().name})
                return item['driver_path'], item['chrome_path']
        else:
            driver_logger.info("All drivers are busy, will retry...", extra={"thread_name": threading.current_thread().name})
            return False


#@retry_func(max_attempts=1)  # dont want to show "Not found any driver to " additionally
def set_driver_to_free(uid=None, is_saved_to_redis=None, errors=None):  # for main thread is_saved_to_redis should be None
    if not uid:
        uid = "main_thread"
    message_status = "Successfully saved to Redis" if is_saved_to_redis else "Failed to save to Redis" if is_saved_to_redis is False else ""
    with lock_thread:
        for item in DRIVERS_CHROMS:
            if item.get('uid') == uid:
                item['uid'] = None
                driver_logger.info(f"{message_status} and exit. set driver for free uid: {uid}. errors: {errors}", extra={"thread_name": threading.current_thread().name})
                break
        else:      # if not found any item.get('uid') in whole lists
            driver_logger.info(f"Not found any driver to free up. {message_status} (uid={uid}). errors: {errors}")
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
    service = Service(driver_path="/mnt/c/chrome/linux/chromedriver1-linux64/chromedriver")
    options.binary_location = "/mnt/c/chrome/linux/chrome1-linux64/chrome"
    # options.add_argument("--incognito")  # Enable incognito mode (disable extensions)
    # options.add_argument('--no-sandbox')
    # options.add_argument('--disable-dev-shm-usage')
    # options.add_argument('--disable-gpu')
    # options.add_argument('--disable-dev-shm-usage')
    # options.add_argument('--ignore-certificate-errors')
    # options.add_argument('--dns-prefetch-disable')
    # options.add_argument('--no-proxy-server')
    # options.add_argument('--proxy-bypass-list=*')

    driver = webdriver.Chrome(service=service, options=options)
    # driver.delete_all_cookies()  # Clear all cookies
    driver.maximize_window()
    return driver


def advance_setup():
    service = Service(driver_path=env('DRIVER_PATH1'))

    options = uc.ChromeOptions()

    options.binary_location = env('CHROME_PATH1')
    #options.add_argument("--headless")
    #options.add_argument(f"user-data-dir={env('CHROME_PROFILE_PATH')}")
    #options.add_argument(f"--profile-directory={env('CHROME_PROFILE_FOLDER')}")
    #profile_path = os.path.join(os.getenv('APPDATA'), 'Local', 'Google', 'Chrome', 'User Data', 'Profile5')
    #options.add_argument(f"user-data-dir={profile_path}")
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


def uc_replacement_setup(uid=None):
    driver_chrome = get_driver_chrome(uid)
    if not driver_chrome:
        return None

    driver_load_retries = 2
    for i in range(driver_load_retries):
        try:
            options = Options()
            service = Service(executable_path=driver_chrome[0])
            options.binary_location = driver_chrome[1]
            options.add_argument("--headless=new")  # if you need headless

            #options.add_argument(f"user-data-dir={env('CHROME_PROFILE_PATH')}")
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
            USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) " \
                         "AppleWebKit/537.36 (KHTML, like Gecko) " \
                         "Chrome/114.0.0.0 Safari/537.36"
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
        #driver.maximize_window()  dont use in headless
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
