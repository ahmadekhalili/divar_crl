from django.conf import settings
from django.core.files import File

from datetime import datetime
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
from selenium_stealth import stealth
from urllib.parse import quote, urljoin
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

from .crawl_setup import advance_setup

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env()
env.read_env(os.path.join(BASE_DIR, '.env'))
logger = logging.getLogger('web')
logger_file = logging.getLogger('file')


class RunModules:        # run a task (for example close map, go next image, ...) and dont important returning specefic elment value (like phone ,...)
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
                    raise  # Re-raise the last exception if retries exhausted
            except ElementClickInterceptedException:
                try:
                    logger.error(f"Something’s overlaying it. try JS fallback")
                    self.driver.execute_script("arguments[0].click();", btn)
                    logger.info(f"map closed by js fallback")
                    return
                except:
                    logger.error(f"Could not click the button by js")
                    raise  # Re-raise the last exception if retries exhausted
            except TimeoutException:
                logger.error(f"Didn’t become clickable in time")
                if attempt == retries:
                    logger.error(f"Could not click the button after {retries} attempts")
                    raise  # Re-raise the last exception if retries exhausted
            # short pause before retry
            time.sleep(1)

    def next_image(self):
        # click on '<' icon to get next image. return 'end of image' of reach end of gallary
        wait = WebDriverWait(self.driver, 10)
        try:
            # Wait for the element to be clickable
            next_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[@aria-label='تصویر بعدی']")))
            # Attempt to click the element
            next_button.click()
            message = f"Successfully clicked the 'تصویر بعدی' button."
            logger_file.info(message)
            return True, message

        except TimeoutException:
            logger_file.error(f"Timeout waiting for the 'تصویر بعدی' button to be clickable within 10 seconds.")
            return False, f"Timeout waiting for the 'تصویر بعدی' button to be clickable within 10 seconds."
        except NoSuchElementException:
            logger_file.error("The 'تصویر بعدی' button element was not found on the page.")
            return False, "The 'تصویر بعدی' button element was not found on the page."
        except ElementClickInterceptedException:
            logger_file.error("Click intercepted: Another element is covering the 'تصویر بعدی' button.")
            # In a real-world scenario, you might add additional logic here to handle
            # the interception, like scrolling or clicking the intercepting element.
            return False, "Click intercepted: Another element is covering the 'تصویر بعدی' button."
        except StaleElementReferenceException:
            logger_file.error(f"Element Staled: Element founded but changed in DOM. may updated by js or page loading")
            return False, f"Element Staled: Element founded but changed in DOM. may updated by js or page loading"
        except Exception as e:
            message = f"An unexpected error occurred hitting next image button: {e}"
            logger_file.error(message)
            return False, message

    def check_end_of_gallery(self):  # check there isnt any next button to get next image
        wait = WebDriverWait(self.driver, 10)
        try:
            wait.until(EC.element_to_be_clickable((By.XPATH, "//button[@aria-label='تصویر بعدی']")))
        except:
            pre_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[@aria-label='تصویر قبلی']")))
            if pre_button:
                logger_file.error("reached end of images")
                return True, ''         # end of the gallery
        return False, ''


class GetElement:    # get specefic element and return its value
    def __init__(self, driver, retry=1):
        self.driver = driver
        self.retry = retry

    def get_phone(self):
        phone_button = WebDriverWait(self.driver, 10).until(EC.element_to_be_clickable(
            (By.XPATH, "//button[@class='kt-button kt-button--primary post-actions__get-contact']")))
        phone_button.click()
        try:
            phone_element = WebDriverWait(self.driver, 10).until(EC.visibility_of_element_located(
                (By.XPATH, "//a[@class='kt-unexpandable-row__action kt-text-truncate']")))
            phone_number = phone_element.get_attribute('href').replace('tel:', '')
            int(phone_number)  # if no phone provided by client, phone_number is some characters not number
        except:  # if it's not prodived phone number, set None
            phone_number = None
        return phone_number

    def get_image(self):
        image_element = None
        for i in range(self.retry):
            logger_file.info(f"retry {i+1}:")
            selector = 'img.kt-image-block__image'  # The CSS selector for the image
            driver = self.driver

            try:
                logger_file.info(f"Attempting to check for presence of element: {selector}")
                # Wait for the element to be present in the DOM
                image_element = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, selector)))
                logger_file.info(f"Element is PRESENT in the DOM: {selector}")
                return image_element

            except TimeoutException:
                logger_file.warning(f"Timeout waiting for visibility of element: {selector}. The element might not be present or visible.")
                # Now wait for visibility again after scrolling
                logger_file.info(f"Waiting for visibility after scrolling: {selector}")
                image_element = WebDriverWait(driver, 10).until(EC.visibility_of_element_located((By.CSS_SELECTOR, selector)))
                # Attempt to scroll the element into view
                logger_file.info(f"Attempting to scroll element into view: {selector}")
                driver.execute_script("arguments[0].scrollIntoView(true);", image_element)
                image_element = WebDriverWait(driver, 10).until(EC.visibility_of_element_located((By.CSS_SELECTOR, selector)))
                logger_file.info(f"Successfully found and element is visible after scrolling: {selector}")
                return image_element
            except:
                logger_file.warning(f"failed getting image element totally")
        return image_element

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
        logger.info(f"title crawld: {title}")
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
        '''
        # Find the first button element that opens the gallery using the class name
        initial_button = driver.find_elements(By.CLASS_NAME, 'kt-base-carousel__thumbnail-button')
        if initial_button:  # clicking on first button will cause opening gallery page
            initial_button = initial_button[0]
        actions = ActionChains(driver)  # Initialize ActionChains for more complex interactions
        # Click the initial button to open the gallery
        try:
            actions.move_to_element(initial_button).click().perform()
            time.sleep(2)  # Add a delay to allow the new content or page to load
        except Exception as e:
            logger.error(f"can't click on initial button to open the gallery. error: {e}")
        '''
        run_tasks = RunModules(driver)
        get_element = GetElement(driver, 2)
        image_srcs = set()
        image_success, image_counts = 0, 0  # -1 because always one time finding of next image image ('<') fails after reaching galary's end
        for i in range(50):       # can crawl max 50 images, dont use while loop for safety
            image_counts += 1
            image_element = get_element.get_image()

            # Get the src attribute
            try:
                image_url = image_element.get_attribute('src')
                if image_url:
                    image_success += 1
                    image_srcs.add(image_url)
                else:
                    logger_file.info(f"image src is blank (while element founded)")
            except Exception as e:
                logger_file.error(f"erorr raise getting image's src. error: {e}")

            next_image = run_tasks.next_image()
            time.sleep(1)     # just for test trace
            # end_of_gallery = run_tasks.check_end_of_gallery()  # check there isnt any next button to get next image
            logger_file.info(f"--image {i+1} {next_image[0]}")


            if not next_image[0]:
                logger_file.info(f"next_image icon not found, reached end of images")
                break

        # in mismatch maybe duplicates or fails
        logger_file.info(f"crawled images: {image_success}/{image_counts}.")
        self.file['image_srcs'] = image_srcs

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
        logger.info(f"going to crawl_main_data")
        self.crawl_main_data(driver)
        self.crawl_images(driver)
        self.crawl_extra_data(driver)


def crawl_files(location_to_search, max_files=None):
    logger.info(f"wait for driver to load")
    driver = advance_setup()
    wait = WebDriverWait(driver, 10)
    base_url = "https://divar.ir"
    url = "https://divar.ir/s/tehran/buy-apartment"

    driver.get(url)     # Load the web page
    crawl_modules = RunModules(driver)

    try:
        crawl_modules.close_map()
    except Exception as e:
        logger.error(f"{e}")       # skip closing if failed

    try:
        # search box
        search_input = wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, 'input.kt-nav-text-field__input')))
        search_input.send_keys(location_to_search)  # type in search box to search
        search_input.send_keys(Keys.ENTER)
        time.sleep(1)

        # Initialize variables to track scroll position and loaded cards
        last_height = driver.execute_script("return document.body.scrollHeight")

        # Scroll down and add all founded card to 'cards'
        cards = []       # using set() make unordered of cards
        while True:
            try:
                card_selector = "article.unsafe-kt-post-card"
                wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, card_selector)))  #driver.find_elements(By.CSS_SELECTOR, 'article.kt-post-card')
                # 2. Find all card elements now that we know they exist
                cards_on_screen = driver.find_elements(By.CSS_SELECTOR, card_selector)
                logger.info(f"cards_on_screen: {len(cards_on_screen)}")
            except Exception as e:
                logger.error(f"Fails getting cards via article.kt-post-card element. error: {e}")
                cards_on_screen = []
            for card in cards_on_screen:
                try:
                    failed_title = [False]
                    title_element = card.find_element(By.CSS_SELECTOR, "h2.unsafe-kt-post-card__title")
                    logger.info(f"first attempt itle_element: {title_element}")
                    if not title_element:
                        title_element = card.find_elements(By.CSS_SELECTOR, '.kt-new-post-card__title')
                        logger.info(f"sec attempt title_elements: {title_element}")
                    title = title_element.text.strip()
                    #    Target the specific 'a' tag using its class
                except Exception as e:
                    logger.error('aaaaaaaaaa')
                    failed_title = [True, e]
                try:
                    failed_url = [False]
                    link_element = card.find_element(By.CSS_SELECTOR, "a.unsafe-kt-post-card__action")
                    card_url = link_element.get_attribute('href')
                except Exception as e:
                    failed_url = [True, e]
                    # some carts are blank or duplicate crawling. required to be checked here
                if not failed_title[0] and not failed_url[0]:
                    logger.info(f"succesfully optained url and title of the card: {card_url}, {title}")
                elif failed_title[0] and not failed_url[0]:
                    logger.error(f"Could not retrieve title for the card. url of card: {card_url}, full error message: {failed_title[1]}")
                elif not failed_title[0] and failed_url[0]:
                    logger.error(f"Could not retrieve url for the card. title of card: {title}, full error message: {failed_url[1]}")
                else:
                    logger.error(f"Could not retrieve title and url of the card. title error: {failed_title}, url error: {failed_url}")

                if card_url and title and card_url not in cards and \
                        (not max_files or len(cards) < max_files):  # Note '<=' is false!
                    absolute_url = urljoin(base_url, card_url)
                    cards.append(card_url)
                else:                   # some carts are blank, required to skip them
                    pass

            if max_files > 11:
                # Scroll down to the bottom of the page
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(1)  # Wait for the page to load new cards
                # Get the new scroll height and compare with the last scroll height
                new_height = driver.execute_script("return document.body.scrollHeight")
                # If the scroll height hasn't changed, we've reached end of scroll
                if new_height == last_height:
                    break
                last_height = new_height
            else:
                break   # skip scroll and exit while loop

        logger.info(f"cards finds: {len(cards)}")
        files, errors = [], {}    # if some files not crawled, trace them in error list
        for i, card_url in enumerate(cards):
            logger.info(f"going to card {i+1}. card url: {card_url}")
            driver.get(card_url)
            time.sleep(2)
            file_crawl = FileCrawl()
            try:
                file_crawl.file['url'] = card_url  # save url before crawl others
                file_crawl.crawl_file(driver)  # fills .file
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
