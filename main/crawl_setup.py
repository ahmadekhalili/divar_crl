import logging
import os
import random
import time
import environ
from pathlib import Path

from fake_useragent import UserAgent
import undetected_chromedriver as uc
from selenium.webdriver import ActionChains
from selenium.webdriver.chrome import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service

from .methods import HumanMouseMove

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env()
env.read_env(os.path.join(BASE_DIR, '.env'))
logger = logging.getLogger('web')


def setup():
    options = Options()
    service = Service(driver_path=env('DRIVER_PATH1'))
    options.binary_location = env('CHROME_PATH1')  # C:\chrome\chrome_browser_134.0.6998.35
    #options.add_argument("--incognito")  # Enable incognito mode (disable extensions)
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--ignore-certificate-errors')
    options.add_argument('--dns-prefetch-disable')
    options.add_argument('--no-proxy-server')
    options.add_argument('--proxy-bypass-list=*')
    user_agent = UserAgent().random
    options.add_argument(f"--user-agent={user_agent}")
    driver = webdriver.Chrome(service=service, options=options)
    #driver.delete_all_cookies()  # Clear all cookies
    driver.maximize_window()
    return driver


def advance_setup():
    service = Service(driver_path=env('DRIVER_PATH1'))

    options = uc.ChromeOptions()

    options.binary_location = env('CHROME_PATH1')
    #options.add_argument(r"user-data-dir=C:/Users/akh/AppData/Local/Google/Chrome/User Data")
    #options.add_argument(r"--profile-directory=Profile 6")
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

    driver = uc.Chrome(service=service, options=options)
    #print('driver path: ', driver.service.path)
    driver.set_window_size(1920, 1080)
    user_agent = UserAgent().random  #"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
    options.add_argument(f"user-agent={user_agent}")
    #stealth(driver, languages=["en-US", "en"], vendor="Google Inc.", platform="Win32", webgl_vendor="Intel Inc.", renderer="Intel Iris OpenGL Engine", fix_hairline=True, run_on_insecure_origins=True, hide_webdriver=True)
    # Open a blank page to start with a clean slate
    logger.info('before open the page')
    #driver.get("about:blank")
    logger.info('blank opended')
    # Create an ActionChains instance
    actions = ActionChains(driver)
    # Optionally, position the mouse at a central point (this is our starting point)
    start_x, start_y = 1078, 521
    logger.info('ActionChains opended')
    actions.move_by_offset(start_x, start_y).perform()
    logger.info('move_by_offset run')
    time.sleep(0.41)  # a slight pause to mimic natural behavior
    actions = HumanMouseMove.human_mouse_move(actions, (random.randint(0, 500), random.randint(0, 500)), (random.randint(0, 500), random.randint(0, 500)))
    logger.info('human_mouse_move was run')
    driver.maximize_window()
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
