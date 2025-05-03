from django.conf import settings
from django.core.files import File

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support.ui import Select
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    StaleElementReferenceException,
    ElementClickInterceptedException
)


import pygetwindow as gw
from fake_useragent import UserAgent
from webdriver_manager.chrome import ChromeDriverManager
import undetected_chromedriver as uc
from selenium_stealth import stealth
from urllib.parse import quote
from PIL import Image

from pathlib import Path
import jdatetime
import logging
import environ
import random
import string
import time
import re
import os

from .methods import HumanMouseMove

BASE_DIR = Path(__file__).resolve().parent.parent
extension_title_path = os.path.join(BASE_DIR, 'scripts', 'extension_close')


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

def setup2():
    options = Options()
    service = Service(driver_path=env('DRIVER_PATH2'))
    options.binary_location = env('CHROME_PATH2')  # C:\chrome\chrome_browser_134.0.6998.35
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
    logger.info(f"DRIVER_PATH: {env('DRIVER_PATH2')}")
    return driver

def setup3():
    options = Options()
    service = Service(driver_path=env('DRIVER_PATH3'))
    options.binary_location = env('CHROME_PATH3')  # C:\chrome\chrome_browser_134.0.6998.35
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
    logger.info(f"DRIVER_PATH: {env('DRIVER_PATH3')}")
    return driver

setup_funcs = {1: setup, 2: setup2, 3: setup3}



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


class FileCrawl:
    def __init__(self):
        self.file = {
            'phone': None, 'title': None, 'metraj': None, 'age': None, 'otagh': None, 'total_price': None,
            'price_per_meter': None, 'floor_number': None, 'general_features': None, 'description': None,
            'image_srcs': None, 'specs': None, 'features': None, 'url': None
        }

    def __repr__(self):
        # Get the current module and class name dynamically
        current_module = self.__class__.__module__
        current_class = self.__class__.__name__
        return f"<{current_module}.{current_class}> {self.title}"  # is like: '<main.crawl.FileCrawl title...'

    def get(self, attr, default=None):  # add get support to use like: FileCrawl.get('title', None)
        return getattr(self, attr, default)

    def crawl_main_data(self, driver):
        # Extract the title
        title = driver.find_element(By.CLASS_NAME, 'kt-page-title__title').text.strip()
        self.file['title'] = title

        # Extract the table values (مترج، ساخت، اتاق)
        td_elements = driver.find_elements(By.XPATH, "//tr[@class='kt-group-row__data-row']//td")
        metraj = td_elements[0].text.strip()
        age = td_elements[1].text.strip()
        otagh = td_elements[2].text.strip()
        self.file['metraj'], self.file['age'], self.file['otagh'] = metraj, age, otagh

        # Extract pricing information (total_price, price_per_meter, floor_number)
        texts = []
        base_divs = driver.find_elements(By.CSS_SELECTOR, ".kt-base-row.kt-base-row--large.kt-unexpandable-row")
        for div in base_divs:
            value_box = div.find_element(By.CSS_SELECTOR, ".kt-base-row__end.kt-unexpandable-row__value-box")
            # required to use try statement (some value_boxes are not real and have not p tag inside themselves)
            try:
                p_element = value_box.find_element(By.XPATH, ".//p")
            except:
                p_element = None
            if p_element:
                texts.append(p_element.text)
        if len(texts) == 4:     # texts[0] == 'bale' | 'kheir' some properties have it.
             total_price, price_per_meter, floor_number = texts[1], texts[2], texts[3]
        else:
            total_price, price_per_meter, floor_number = texts[0], texts[1], texts[2]
        self.file['total_price'], self.file['price_per_meter'], self.file['floor_number'] = total_price, price_per_meter, floor_number

        # Extract پارکینگ، آسانسور، انباری، بالکن information
        general_features = [td.text.strip() for td in driver.find_elements(By.XPATH, "//td[@class='kt-group-row-item kt-group-row-item__value kt-body kt-body--stable']")]
        self.file['general_features'] = general_features

        # Extract and clean description
        description_element = driver.find_element(By.CLASS_NAME, 'kt-description-row__text--primary')
        description = description_element.text.strip() if description_element else False
        description_clean = re.sub(r'[^\w\s!@#$%^&*()\-_=+;:\'"~,،؛{}\]\[]', '', description)    # remove all symbols, only text + new lines + required signs
        self.file['description'] = description_clean

    def crawl_images(self, driver):
        # Find the first button element that opens the gallery using the class name
        initial_button = driver.find_elements(By.CLASS_NAME, 'kt-base-carousel__thumbnail-button')
        if initial_button:  # clicking on first button will cause opening gallery page
            initial_button = initial_button[0]

        actions = ActionChains(driver)  # Initialize ActionChains for more complex interactions

        # Click the initial button to open the gallery
        try:
            actions.move_to_element(initial_button).click().perform()
            time.sleep(2)  # Add a delay to allow the new content or page to load

            # Now, focus on the gallery container specifically
            gallery_container = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CLASS_NAME, 'kt-gallery-view__thumbnails'))
            )

            # Find all the buttons within the gallery container
            gallery_buttons = gallery_container.find_elements(By.CLASS_NAME, 'kt-base-carousel__thumbnail-button')
            image_srcs = set()

            # Loop through each button in the gallery and click it to load the image
            for gallery_button in gallery_buttons:
                try:
                    driver.execute_script("arguments[0].click();", gallery_button)
                    time.sleep(1)  # Wait for the image to load

                    # Add loaded image to the set
                    new_image_elements = driver.find_elements(By.CSS_SELECTOR, '.kt-base-carousel__slides img.kt-image-block__image')
                    for img in new_image_elements:
                        src = img.get_attribute('src')
                        if src:
                            image_srcs.add(src)

                except Exception as e:
                    print(f"Error clicking gallery button: {e}")

            # Close the gallery
            close_button = driver.find_element(By.XPATH, "//button[@class='kt-button kt-button--inlined kt-button--circular kt-dimmer__close']")
            close_button.click()
            self.file['image_srcs'] = image_srcs

        except Exception as e:
            print(f"An error occurred: {e}")

    def crawl_extra_data(self, driver):  # opens "نمایش همهٔ جزئیات" button and crawl all information
        button = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, "//div[@role='button' and .//p[text()='نمایش همهٔ جزئیات']]")))
        driver.execute_script("arguments[0].scrollIntoView(true);", button)  # scroll to get element in view (important)
        button.click()  # Click the outer div button

        try:
            # Wait for the modal to be present
            modal_body = WebDriverWait(driver, 10).until(
                EC.visibility_of_element_located((By.CLASS_NAME, 'kt-modal__body'))
            )

            # Extract the titles and values for general specs
            specs = {}
            rows = modal_body.find_elements(By.CLASS_NAME, 'kt-unexpandable-row')
            for row in rows:
                title = row.find_element(By.CLASS_NAME, 'kt-base-row__title').text
                value = row.find_element(By.CLASS_NAME, 'kt-unexpandable-row__value').text
                specs[title] = value
            self.file['specs'] = specs

            # Extract full features under "امکانات"
            features = []
            feature_elements = modal_body.find_elements(By.CLASS_NAME, 'kt-feature-row')
            for el in feature_elements:
                feature = el.find_element(By.CLASS_NAME, 'kt-feature-row__title').text
                features.append(feature)
            self.file['features'] = features

        except Exception as e:
            print(f"Error extracting modal data: {e}")
            return {}, []

        # Close the modal by clicking the close button
        close_button = driver.find_element(By.XPATH, "//button[@class='kt-button kt-button--inlined kt-button--circular kt-modal__close-button']")
        close_button.click()

    def crawl_file(self, driver):  # Crawl all the information and add to self.file
        # get the phone number of the client
        phone_button = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, "//button[@class='kt-button kt-button--primary post-actions__get-contact']")))
        phone_button.click()
        try:
            phone_element = WebDriverWait(driver, 10).until(EC.visibility_of_element_located((By.XPATH, "//a[@class='kt-unexpandable-row__action kt-text-truncate']")))
            phone_number = phone_element.get_attribute('href').replace('tel:', '')
            int(phone_number)     # if no phone provided by client, phone_number is some characters not number
        except:      # if it's not prodived phone number, set None
            phone_number = None
        self.file['phone'] = phone_number
        if phone_number:      # without phone, you have to chat with the client (that is impossible)
            self.crawl_main_data(driver)
            self.crawl_images(driver)
            self.crawl_extra_data(driver)


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


class CrawlModules:
    def __init__(self, driver):
        self.driver = driver

    def close_map(self, retries=3):
        """
            Clicks the 'بستن نقشه' FAB button under its role=button parent.
            Retries on common Selenium hiccups and falls back to JS click if needed.
            """
        xpath = (
            "//div[@role='button']"
            "[.//div[contains(@class,'kt-fab-button--raised') "
            "and normalize-space(text())='بستن نقشه']]"
        )

        for attempt in range(1, retries + 1):
            try:
                # 1) wait until clickable
                btn = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, xpath))
                )

                # 2) scroll into view
                self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", btn)

                # 3) normal click
                btn.click()
                logger.info(f"map closed successfully")
                return  # success

            except StaleElementReferenceException:
                logger.error(f"The DOM updated—retry locating")
                if attempt == retries:
                    raise
            except ElementClickInterceptedException:
                logger.error(f"Something’s overlaying it. try JS fallback")
                self.driver.execute_script("arguments[0].click();", btn)
                logger.info(f"map closed by js fallback")
                return
            except TimeoutException:
                logger.error(f"Didn’t become clickable in time")
                if attempt == retries:
                    logger.error(f"Could not click the button after {retries} attempts")
            # short pause before retry
            time.sleep(1)


def crawl_files(location_to_search, max_files=None):
    logger.info(f"wait for driver to load")
    driver = advance_setup()

    url = "https://divar.ir/s/tehran/buy-apartment"
    driver.get(url)     # Load the web page
    crawl_modules = CrawlModules(driver)

    crawl_modules.close_map()
    try:
        # search box
        search_input = WebDriverWait(driver, 10).until(EC.visibility_of_element_located((By.CSS_SELECTOR, 'input.kt-nav-text-field__input')))
        search_input.send_keys(location_to_search)  # type in search box to search
        search_input.send_keys(Keys.ENTER)
        time.sleep(1)

        # Initialize variables to track scroll position and loaded cards
        last_height = driver.execute_script("return document.body.scrollHeight")

        # Scroll down and add all founded card to 'cards'
        cards = []       # using set() make unordered of cards
        while True:
            cards_on_screen = driver.find_elements(By.CSS_SELECTOR, 'article.kt-post-card')
            for card in cards_on_screen:
                try:
                    title_elements = card.find_elements(By.CSS_SELECTOR, '.kt-post-card__title')  # Find title of card
                    if not title_elements:
                        title_elements = card.find_elements(By.CSS_SELECTOR, '.kt-new-post-card__title')
                    card_url = card.find_element(By.TAG_NAME, 'a').get_attribute('href')  # Find the url of the card
                    # some carts are blank or duplicate crawling. required to be checked here
                    if card_url and title_elements and card_url not in cards and \
                            (not max_files or len(cards) < max_files):  # Note '<=' is false!
                        title = title_elements[0].text
                        cards.append(card_url)
                    else:                   # some carts are blank, required to skip them
                        pass
                except Exception as e:
                    print(f"Could not retrieve title for card: {e}")

            # Scroll down to the bottom of the page
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(1)  # Wait for the page to load new cards
            # Get the new scroll height and compare with the last scroll height
            new_height = driver.execute_script("return document.body.scrollHeight")
            # If the scroll height hasn't changed, we've reached end of scroll
            if new_height == last_height:
                break
            last_height = new_height

        files, errors = [], {}    # if some files not crawled, trace them in error list
        for card_url in cards:
            driver.get(card_url)
            time.sleep(2)
            file_crawl = FileCrawl()
            try:
                file_crawl.crawl_file(driver)  # fills .file
                file_crawl.file['url'] = card_url
            except Exception as e:
                errors['cart_url'] = str(e)
            files.append(file_crawl.file)

            driver.back()
            time.sleep(2)

    except Exception as e:
        raise e

    finally:
        driver.quit()

    return (files, errors)
