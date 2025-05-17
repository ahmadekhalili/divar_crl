from runpy import run_module

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
from selenium.webdriver.common.actions.wheel_input import ScrollOrigin
from selenium.common.exceptions import (
    TimeoutException,
    WebDriverException,
    NoSuchElementException,
    StaleElementReferenceException,
    ElementClickInterceptedException
)

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
import threading
import time
import re
import os

from .crawl_setup import advance_setup, uc_replacement_setup, set_driver_to_free
from .serializers import FileMongoSerializer
from .mongo_client import get_mongo_db
from .redis_client import REDIS
from .methods import add_to_redis, set_random_agent, set_uid_url_redis, get_uid_url_redis, retry_func

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env()
env.read_env(os.path.join(BASE_DIR, '.env'))
logger = logging.getLogger('web')
logger_separation = logging.getLogger("web_separation")
logger_file = logging.getLogger('file')

_pop_lock = threading.Lock()

class Retry:
    retry = 2   # one additional times methods runs by itself (to generate real personal exception messages)

    @staticmethod
    def run_retry(func, *args, retry=retry, **kwargs):
        '''
        can use in:
        @Retry.run_retry
        @Retry.run_retry()
        @Retry.run_retry(retry=2)
        '''
        def wrapper(*args, **kwargs):
            for i in range(retry):
                try:
                    return func(*args, **kwargs)
                except StaleElementReferenceException as e:
                    logger_file.error(f"Stale Element error {func} method. wait and retry again. {i+1}/{retry}")
                    time.sleep(1)
                    if i == retry-1:
                        raise    # reraise so related exception runs in func method dont lose true logs of func exceptions
                except Exception as e:
                    raise  # reraise so related exception runs in func method to dont lose true logs of func exceptions
        return wrapper


class RunModules:        # run a task (for example close map, go next image, ...) and dont important returning specefic elment value (like phone ,...)
    def __init__(self, driver, file=None, retry=2):
        self.driver = driver
        self.retry = retry
        self.file = file

    def close_map(self, retries=1):
        """
            Clicks the 'بستن نقشه' showin in cards list (different from each file  map's location in file detail page)
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
        # click on '<' icon to get next image. return 'end of image' of reach end of gallery
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

    def check_is_video(self):
        wait = WebDriverWait(self.driver, 5)
        video_selector = "//button[span[text()='play-f']]"
        try:
            video_button = wait.until(EC.element_to_be_clickable((By.XPATH, video_selector)))
            return True, f"video is founded in gallery. video_button boolean: {bool(video_button)}"
        except TimeoutException:  # element not found
            return False, ''

    def check_end_of_gallery(self):
        wait = WebDriverWait(self.driver, 10)
        try:
            next_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[@aria-label='تصویر بعدی']")))
            logger_file.info(f"next_button found")
            return False, ''
        except:
            logger_file.info(f"next_button not found")
            return True, ''

    def zoom_canvas(self, canvas, steps: int = 7, delta: int = -200):
        """
        steps: number of wheel scrolls
        delta: pixes to scroll. positive → scroll down, negative → scroll up
        """
        try:
            origin = ScrollOrigin.from_element(canvas)
            actions = ActionChains(self.driver)
            for _ in range(steps):
                actions.scroll_from_origin(origin, 0, delta)
            actions.perform()

        except Exception as e:
            self.file.file_errors.append(f"failed zoming canvas of the file. error: {e}")
            logger_file.error(f"failed zoming canvas of the file. error: {e}")

    def open_map(self):  # here should stop further crawling of map if fails (return False)
        self.available_map_element = False
        for i in range(self.retry):
            logger_file.info(f"try open map. retry: {i+1}/{self.retry}")
            try:
                locator = (By.CSS_SELECTOR, "div.image-dbbad picture.kt-image-block--radius-sm img[alt='موقعیت مکانی']")
                # 2) Wait up to 10s for the element to be present in the DOM
                elem = WebDriverWait(self.driver, 10).until(EC.presence_of_element_located(locator))
                # 3) Scroll it into view (smoothly, centered)
                self.available_map_element = bool(elem)
                self.driver.execute_script(
                    "arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});",
                    elem
                )
                # 4) (Optional) give the scroll a moment to settle
                WebDriverWait(self.driver, 2).until(
                    lambda d: elem.is_displayed() and elem.location_once_scrolled_into_view
                )
                # 5) Now wait until it’s clickable
                clickable = WebDriverWait(self.driver, 10).until(EC.element_to_be_clickable(locator))
                clickable.click()  # Click to open the map canvas
                logger_file.info(f"clicked on map successfully.")
                return True, ''
            except Exception as e:
                if self.available_map_element:
                    logger_file.error(f"failed opening the map of the file. error: {e}")

                if i+1 == self.retry:
                    if self.available_map_element:
                        self.file.file_errors.append(f"failed opening the map of the file.")  # dont write several times
                    raise      # reraise for upstream (should stop map crawling)

    def upload_map_image(self, canvas, path, image_name):
        # 'path' like: media/file_wZzD48fy/file_mapes, 'image_name' like: normal_view.png
        try:
            os.makedirs(path, exist_ok=True)  # ensure directory exists, no os.path.join here!
            ok_shot = canvas.screenshot(os.path.join(path, image_name))  # 3. take screenshot and save to image_path
            if ok_shot:
                logger_file.info(f"screenshot {image_name} of map canvas has uploaded successfully to: {path}")
                return True, ''
            else:
                logger_file.error(f"Element.screenshot() returned False, could not write {path}")
            return False, 'raise error in taking map screenshots'
        except Exception as e:
            message = f"failed take screenshot for: {image_name}. path: {path}. full error: {e}"
            logger_file.info(f"failed take screenshot for: {image_name}. path: {path}. full error: {e}")
            self.file.file_errors.append(f"failed take screenshot in path: {path}/{image_name}")
            return False, 'raise error in taking map screenshots'

    def close_canvas(self, timeout=10, retries=3):
        """
        Close the “موقعیت مکانی” modal by its close-button.

        Args:
            driver: Selenium WebDriver instance
            timeout: seconds to wait on each attempt
            retries: number of retry attempts

        Raises:
            TimeoutException if the button never becomes clickable.
        """
        # Unique XPath: find the div whose <p> text is exactly “موقعیت مکانی”
        close_xpath = (
            "//div[contains(@class,'kt-new-modal__title-box') "
            "and .//p[text()='موقعیت مکانی']]"
            "//button[contains(@class,'kt-new-modal__close-button')]"
        )

        for attempt in range(1, retries + 1):
            try:
                # wait for it to be clickable
                btn = WebDriverWait(self.driver, timeout).until(
                    EC.element_to_be_clickable((By.XPATH, close_xpath))
                )
                # ensure it's in view
                self.driver.execute_script("arguments[0].scrollIntoView({block:'center'});", btn)
                # try JS click first
                self.driver.execute_script("arguments[0].click();", btn)
                logger_file.info(f"successfully clicked on close map by js")
                return  # success

            except (TimeoutException, StaleElementReferenceException, ElementClickInterceptedException):
                # fallback to ActionChains click
                try:
                    btn = self.driver.find_element(By.XPATH, close_xpath)
                    ActionChains(self.driver).move_to_element(btn).pause(0.2).click(btn).perform()
                    logger_file.info(f"successfully clicked on close map by ActionChains click")
                    return  # success
                except Exception:
                    # wait and retry
                    time.sleep(1)

        # if we get here, nothing worked
        raise TimeoutException(
            f"Could not locate/click the close button after {retries} attempts ({timeout}s each)."
        )

    def click_show_all_details(self, timeout=15, y_offset=-100):
        """
        click for the "نمایش همهٔ جزئیات" button.
        """
        locator = (
            By.XPATH,
            "//p[normalize-space(text())='نمایش همهٔ جزئیات']"
            "/ancestor::div[@role='button']"
        )
        wait = WebDriverWait(self.driver, timeout)

        try:
            # 1) Wait until visible
            btn = wait.until(EC.visibility_of_element_located(locator))

            # 2) Scroll into center, then nudge up by y_offset px
            self.driver.execute_script("""
                arguments[0].scrollIntoView({block:'center', inline:'nearest'});
                window.scrollBy(0, arguments[1]);
            """, btn, y_offset)

            # tiny pause to let layout settle
            wait.until(EC.element_to_be_clickable(locator))

            # 3) Move focus there (sometimes helps)
            ActionChains(self.driver).move_to_element(btn).perform()

            # 4a) Try normal click
            try:
                btn.click()
                return
            except (ElementClickInterceptedException, StaleElementReferenceException):
                # 4b) Fallback: JS click
                self.driver.execute_script("arguments[0].click();", btn)
                return

        except TimeoutException:
            raise RuntimeError(
                f"Could not find or click 'نمایش همهٔ جزئیات' within {timeout}s"
            )


class GetElement:    # get specific element and return its value
    def __init__(self, driver, file=None, retry=2):
        # for distinguish is element available or unable to find we use: has_parent_element = True
        self.driver = driver
        self.retry = retry
        self.file = file

    def get_title_from_cardbox(self, card):  # get title from card box (not inside file page)
        try:
            title_element = card.find_element(By.CSS_SELECTOR, "h2.unsafe-kt-post-card__title")
            logger.info(f"first attempt title_element bool: {bool(title_element)}")
            if not title_element:
                title_element = card.find_elements(By.CSS_SELECTOR, '.kt-new-post-card__title')
                logger.info(f"sec attempt title_elements: {title_element}")
            title = title_element.text.strip()
            return True, title
            # Target the specific 'a' tag using its class
        except Exception as e:
            return False, e

    def get_url_from_cardbox(self, card):
        try:
            link_element = card.find_element(By.CSS_SELECTOR, "a.unsafe-kt-post-card__action")
            return True, link_element.get_attribute('href')
        except Exception as e:
            return False, e

    def get_uid(self, url):
        try:
            uid = url.rstrip("/").split("/")[-1]
            logger.debug(f"successfully obtained uid: {uid}")
            return True, uid
        except Exception as e:
            return False, f"couldn't get uid from card's url. url: {e}"


    def get_phone(self):
        phone_number = [False, '']
        phone_button = WebDriverWait(self.driver, 10).until(EC.element_to_be_clickable(
            (By.XPATH, "//button[@class='kt-button kt-button--primary post-actions__get-contact']")))
        phone_button.click()
        try:
            phone_element = WebDriverWait(self.driver, 10).until(EC.visibility_of_element_located(
                (By.XPATH, "//a[@class='kt-unexpandable-row__action kt-text-truncate']")))
            phone_number = phone_element.get_attribute('href').replace('tel:', '')
            return True, int(phone_number)  # if no phone provided by client, phone_number is some characters not number
        except:  # if it's not prodived phone number, set None
            phone_number = None
        return phone_number

    def get_image(self, element=None):
        image_element = [False, '']
        for i in range(self.retry):
            logger_file.info(f"retry {i+1} for get image element:")
            selector = 'img.kt-image-block__image'  # The CSS selector for the image
            driver = self.driver

            try:
                mini_message = " from sub element." if element else ""
                logger_file.debug(f"Attempting to find the image element{mini_message}.")
                if element:
                    image_element = element.find_element(By.CSS_SELECTOR, 'img.kt-image-block__image')
                else:
                    image_element = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, selector)))
                logger_file.debug(f"Successfully get PRESENT of the image. in retry {i+1}/{self.retry}")
                return True, image_element

            except TimeoutException:
                logger_file.warning(f"Timeout; waiting for presence of image element. wait and retry again {i+1}/{self.retry}")
                time.sleep(1)
            except:
                logger_file.warning(f"failed getting image element totally. wait and retry again {i+1}/{self.retry}")
                time.sleep(1)
        return image_element

    def get_image_src(self, image_element):
        for i in range(self.retry):
            try:
                image_url = image_element.get_attribute('src')
                logger_file.info(f"successfully get image src. in retry {i+1}/{self.retry}")
                return True, image_url
            except StaleElementReferenceException as e:
                logger_file.error(f"error StaleElement getting image's src. wait and retry again. retry {i+1}/{self.retry}")
                time.sleep(1)
                is_image = GetElement(self.driver, file=None, retry= 1).get_image()
                if is_image[0]:
                    image_element = is_image[1]
            except Exception as e:
                logger_file.error(f"error getting image's src. retry. error: {e}")
        return False, None

    def get_tags(self):
        try:
            # Wait until all relevant <span> elements are present
            spans = WebDriverWait(self.driver, 10).until(
                EC.presence_of_all_elements_located(
                    (By.CSS_SELECTOR, "div.kt-wrapper-row button.kt-chip span")
                )
            )
            return True, [span.text.strip() for span in spans if span.text.strip()]
        except Exception as e:
            logger_file.error(f"Failed to get tags: {e}")
            return False, []

    @Retry.run_retry
    def get_agency_info(self):
        try:
            # Wait for the full agency card to appear
            container = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((
                    By.CSS_SELECTOR,
                    "label.kt-event-card.kt-event-card--has-action"
                ))
            )

            # Now wait and fetch title
            title_elem = WebDriverWait(container, 5).until(
                EC.presence_of_element_located((
                    By.CSS_SELECTOR, "p.kt-event-card__title"
                ))
            )
            subtitle_elem = container.find_element(By.CSS_SELECTOR, "p.kt-event-card__subtitle")

            return True, {"title": title_elem.text.strip(), "subtitle": subtitle_elem.text.strip()}

        except Exception as e:
            logger.error(f"Error getting agency info: {e}")
            return False, ''

    def get_time_and_address(self):  # return almost date and time shown in one date
        # for example: time: دقایقی پیش or یک هفته پیش
        # address: تهران هروی
        try:
            elem = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((
                    By.CSS_SELECTOR,
                    "div.kt-page-title__subtitle.kt-page-title__subtitle--responsive-sized"
                ))
            )
            full_text = elem.text.strip()

            # Extract parts using regex
            time_match = re.search(r"^(.*?پیش)", full_text)  # take any text before پیش and itself, like یک هفته پیش
            address_match = re.search(r"در\s+(.*)$", full_text)  # take text after در like: تهران هروی

            time_text = time_match.group(1).strip() if time_match else ""
            address_text = address_match.group(1).strip() if address_match else ""
            if time_text and address_text:
                return True, (time_text, address_text)
            else:
                logger.error(f"get rough time and rough address element but blank value. {time_text} {address_text}")
                self.file.file_errors.append("get rough time and rough address element but blank value")
                return False, ''
        except Exception as e:
            logger.error(f"Error extracting time and address: {e}")
            self.file.file_errors.append("Error extracting rough_time and rough_address element")
            return False, ''


class GetValue:       # get final values ready to add in file fields
    def __init__(self, driver, file_crawl=None, retry=2):
        # for distinguish is element available or unable to find we use: has_parent_element = True
        self.driver = driver
        self.file_crawl = file_crawl
        self.retry = retry

    def get_title_of_file(self):
        try:
            title = self.driver.find_element(By.CLASS_NAME, 'kt-page-title__title').text.strip()
            logger.info(f"title crawld: {title}")
            return title
        except Exception as e:
            logger_file.error(f"couldn't get title of the card. error: {e}")
            self.file_crawl.file_errors.append(f"couldn't get title of the card.")
            return self.file_crawl.file['title']   # return default (dynamic programming)

    def get_metraj_age_oragh(self):
        try:
            file = self.file_crawl.file
            # Extract the table values (مترج، ساخت، اتاق)
            td_elements = self.driver.find_elements(By.XPATH, "//tr[@class='kt-group-row__data-row']//td")
            file['metraj'] = td_elements[0].text.strip()
            file['age'] = td_elements[1].text.strip()
            file['otagh'] = td_elements[2].text.strip()
            return file['metraj'], file['age'], file['otagh']
        except Exception as e:
            logger_file.error(f"couldn't get 'metraj', 'sakht', 'oraq' specs of the card. error: {e}")
            self.file_crawl.file_errors.append(f"couldn't get 'metraj', 'sakht', 'oraq' specs of the card.")
            return file['metraj'], file['age'], file['otagh']

    def get_tprice_pprice_floor(self, verbose1, verbose2, verbose3):  # this class used in several classes. this section in each file has different name. for example in apartmant has totalprice, price_per_meter, floor_number. but in vilaii is is: metraj_zamin, total_price, price_per_meter and ..
        # Extract pricing information like: (total_price, price_per_meter, floor_number)
        try:
            file = self.file_crawl.file
            texts = []
            base_divs = self.driver.find_elements(By.CSS_SELECTOR, ".kt-base-row.kt-base-row--large.kt-unexpandable-row")
            for div in base_divs:
                value_box = div.find_element(By.CSS_SELECTOR, ".kt-base-row__end.kt-unexpandable-row__value-box")
                # required to use try statement (some value_boxes are not real and have not p tag inside themselves)
                try:
                    p_element = value_box.find_element(By.XPATH, ".//p")
                except:
                    p_element = None
                if p_element:
                    texts.append(p_element.text)
            if len(texts) == 4:  # texts[0] == 'bale' | 'kheir' some properties have it.
                total_price, price_per_meter, floor_number = texts[1], texts[2], texts[3]
            else:
                total_price, price_per_meter, floor_number = texts[0], texts[1], texts[2]
            return total_price, price_per_meter, floor_number
        except Exception as e:
            logger_file.error(f"couldn't get {verbose1}, {verbose2}, {verbose3} the card. error: {e}")
            self.file_crawl.file_errors.append(f"couldn't get {verbose1}, {verbose2}, {verbose3} the card.")
            return self.file_crawl.file['total_price'], file['price_per_meter'], file['floor_number']  # return default values

    def get_vadie_ejare_andsoon(self):  # get vadie, ejare, vadie_exchange, floor_number
        # Extract 4 ejar information like: (ودیعه, اجارهٔ ماهانه, ودیعه و اجاره, طبقه)
        try:
            file = self.file_crawl.file
            texts = []
            base_divs = self.driver.find_elements(By.CSS_SELECTOR, ".kt-base-row.kt-base-row--large.kt-unexpandable-row")
            for div in base_divs:
                value_box = div.find_element(By.CSS_SELECTOR, ".kt-base-row__end.kt-unexpandable-row__value-box")
                # required to use try statement (some value_boxes are not real and have not p tag inside themselves)
                try:
                    p_element = value_box.find_element(By.XPATH, ".//p")
                except:
                    p_element = None
                if p_element:
                    texts.append(p_element.text)
            logger.info(f"method1 vadie ejare, ..: {texts}")
            if len(texts) == 5:  # texts[0] == 'bale' | 'kheir' some properties have it.
                vadie, ejare, vadie_exchange, floor_number = texts[1], texts[2], texts[3], texts[4]
            else:
                vadie, ejare, vadie_exchange, floor_number = texts[0], texts[1], texts[2], texts[3]
            return vadie, ejare, vadie_exchange, floor_number

        except Exception as e:
            logger_file.error(f"method 1 get vadie, ejare, .. floor_number failed. try another way. error: {e}")
            try:
                vadie_exchange_text, vadie, ejare = '', None, None
                try:
                    elem = WebDriverWait(self.driver, 10).until(EC.visibility_of_element_located(
                            (By.CSS_SELECTOR, "p.kt-feature-row__title")
                        )
                    )
                    vadie_exchange_text = elem.text.strip()  # in exchange mode must be: "ودیعه و اجارهٔ این ملک قابل تبدیل است."
                    logger.info(f"vadie_exchange_text value: {vadie_exchange_text}")
                except Exception as e:
                    logger_file.error(f"failed getting vadie_exchange_text. {e}")
                    raise

                try:
                    convert = WebDriverWait(self.driver, 10).until(
                        EC.visibility_of_element_located((By.CSS_SELECTOR, ".convert-slider"))
                    )
                    # now find only the cells in that section’s kt-group-row
                    cells = convert.find_elements(
                        By.CSS_SELECTOR,
                        "table.kt-group-row tbody tr.kt-group-row__data-row td.kt-group-row-item__value"
                    )
                    vadie, ejare = cells[0].text.strip(), cells[1].text.strip()
                except Exception as e:
                    logger_file.error(f"failed vadie ejare values. {e}")
                    raise

                logger_file.info(f"texts: {texts}, {texts[0]}")
                # texts[0] could be 'bale' | 'kheir'
                floor_number = texts[1] if len(texts) == 2 else texts[0]
                logger_file.info(f"get values of ejare, vadie, vadie_exchange, floor_number  in method2. {vadie, ejare, vadie_exchange_text, floor_number}")
                return vadie, ejare, vadie_exchange_text, floor_number
            except Exception as e:
                logger_file.error(f"Failed getting ejera, vadie, vadie_exchange_text, floor_number values in method 2. failed totally. error: {e}")
                self.file_crawl.file_errors.append(f"Failed getting ejera, vadie, vadie_exchange, floor_number values in method 1 & 2.")
            return self.file_crawl.file['vadie'], file['ejare'], file['vadie_exchange'], file['floor_number']  # return default values

    def get_description(self):
        try:
            # Extract and clean description
            description_element = self.driver.find_element(By.CLASS_NAME, 'kt-description-row__text--primary')
            description = description_element.text.strip() if description_element else False
            description_clean = re.sub(r'[^\w\s!@#$%^&*()\-_=+;:\'"~,،؛{}\]\[]', '', description)    # remove all symbols, only text + new lines + required signs
            return description_clean
        except Exception as e:
            logger_file.error(f"couldn't get 'description' the card. error: {e}")
            self.file_crawl.file_errors.append(f"couldn't get 'description' the card.")
            return self.file_crawl.file['description']

    def get_active_slide(self, driver):
        """
        Returns the slide element that is currently change (via 'next_button' pressing).
        each slider has a matrix like: (1, 0, 0, x, y). x changes if press to 'next_button'.
        for example slider1 (1, 0, 0, 0, y) --next--> (1, 0, 0, -480, y)
                    slider2 (1, 0, 0, -480, y) -next->(1, 0, 0, 0, y)
        with this we can identify image went on next with hight accurate.
        """
        # 1. Find all slides and the container
        slides = driver.find_elements(
            By.CSS_SELECTOR,
            'div.keen-slider__slide.kt-base-carousel__slide'
        )
        logger_file.debug(f"slides numbers founded: {len(slides)}")
        if not slides:
            logger_file.warning("No slides found in slider.")
            return None

        container = driver.find_element(By.CSS_SELECTOR, '.keen-slider')
        c_rect = driver.execute_script(
            "return arguments[0].getBoundingClientRect();",
            container
        )

        # 2. Precompute slide width (assumed constant)
        slide_width = driver.execute_script(
            "return arguments[0].clientWidth;",
            slides[0]
        )

        logger_file.info(f"Looking through {len(slides)} slides (width={slide_width}px)")

        for idx, slide in enumerate(slides, start=1):
            # 3. Get the transform and extract tx
            transform = driver.execute_script(
                "return window.getComputedStyle(arguments[0]).transform || 'none';",
                slide
            )
            logger_file.debug(f"[slide {idx}] raw transform: {transform}")

            # default tx=0 for 'none'
            tx = 0.0
            if transform != 'none':
                m = re.match(r"matrix\([^,]+,[^,]+,[^,]+,[^,]+,([-\d.]+),", transform)
                if m:
                    tx = float(m.group(1))
                else:
                    logger_file.debug(f"[slide {idx}] couldn't parse tx from {transform}")

            logger_file.debug(f"[slide {idx}] translateX = {tx}px")

            # 4. Check that tx is essentially a multiple of slide_width
            #    (i.e. it's one of the carousel's discrete positions)
            if slide_width and abs(tx) % slide_width > 1e-3:
                logger_file.debug(f"[slide {idx}] offset not aligned to slide width, skipping")
                continue

            # 5. Finally, verify the slide's bounding box sits inside the container
            s_rect = driver.execute_script(
                "return arguments[0].getBoundingClientRect();",
                slide
            )
            if (s_rect['left'] >= c_rect['left'] - 1 and
                    s_rect['right'] <= c_rect['right'] + 1):
                logger_file.info(f"[slide {idx}] is fully in view — selecting as active")
                return slide
            else:
                logger_file.debug(f"[slide {idx}] partially out of view, skipping")

        logger_file.warning("No active slide found.")
        return None

    def get_image_srcs(self):
        run_tasks = RunModules(self.driver, self)
        get_element = GetElement(self.driver, file=None, retry=2)
        get_value = GetValue(self.driver)
        image_srcs = set()
        image_success, image_counts = 0, 0  # -1 because always one time finding of next image ('<') fails after reaching galary's end
        parent_image_element = None
        for i in range(settings.MAX_IMAGE_CRAWL):  # crawl maximum MAX_IMAGE_CRAWL images. 1 and sec of image secs for video type. others assume is image. (video checks take at leats 10 sec)
            is_image = [False]  # if a file has not image, dont raise confuse error (reference before assignment below)

            # show current image processing
            logger_file.info(f"---image {i + 1}, processing...")   # putting here make so easy debugging (shown real iamge processing, not next image)
            time.sleep(1)
            # without this, always we have some extra counted images (get_image reference to previouse images because they are sill in doom with same attrs (only transform changes))
            parent_image_element = get_value.get_active_slide(self.driver)
            if parent_image_element:
                image_counts += 1        # if the file has not image at all why we print:"crawled images: 0/1"? it should be "crawled images: 0/0"
            if i == 0 or i == 1:  # check_is_video add 10 sec delay timeout, so dont run in every loop
                is_video = run_tasks.check_is_video()
                if is_video[0]:  # skip if was video (go next image)
                    logger_file.info(f"is_video: {is_video}")
                    image_counts -= 1  # dont count videos
                else:  # its image, get image
                    is_image = get_element.get_image(element=parent_image_element)
            else:
                is_image = get_element.get_image(element=parent_image_element)
            # Get the src attribute
            if is_image[0]:
                image_url = get_element.get_image_src(is_image[1])
                if image_url[0]:
                    image_success += 1
                    image_srcs.add(image_url[1])
                else:
                    logger_file.info(f"image src failed getting")

            logger_file.debug(f"image_element boolean: {is_image[0]}")
            # try next images even not found image in current loop (dont lose others)
            next_image = run_tasks.next_image()
            #end_of_gallery = run_tasks.check_end_of_gallery()  # check via end_of_gallery may is safe and reasonable

            if not next_image[0]:
                logger_file.info(f"next_image icon not found, reached end of images")
                break

        # in mismatch maybe duplicates or fails
        message = f"--crawled images: {image_success}/{image_counts}. duplicates: {image_success-len(list(image_srcs))}"
        logger_file.info(message)
        if image_success != image_counts:
            self.file_crawl.file_errors.append(message)

        return list(image_srcs)

class FileBase:
    def __init__(self, uid):
        self.uid = uid
        self.file = {'uid': uid, 'title': None, 'url': None}
        self.file_errors = []
        self.screenshot_map_path = env('screenshot_map_path').format(uid=uid)

    def run(self):  # start crawling (run sub methods)
        # its important to use try except here, to stop some further crawling at specific point (for example in crawl_map) but dont let whole programs runs flow stop at all. (get to except and prevent stop failing). so stopabale arcitecture without stop of flow is our purpose
        # its important to catch raise of downstream methods to stop in specific point
        try:
            pass
        except:
            pass


class Apartment:
    def __init__(self, uid, is_ejare):
        self.uid = uid
        self.is_ejare = is_ejare
        self.file = {
            'uid': uid, 'phone': None, 'title': None, 'metraj': None, 'age': None, 'otagh': None, 'total_price': None,
            'price_per_meter': None, 'floor_number': None, 'general_features': [], 'description': '', 'tags': [],
            'agency': None, 'rough_time': None, 'rough_address': None,
            'vadie': None, 'ejare': None, 'vadie_exchange': None,      # just for ejare files, vadie_exchange means can ejare vadie can be exchange or not, it is str
            'image_srcs': [], 'specs': {}, 'features': [], 'url': None
        }
        self.file_errors = []
        self.screenshot_map_path = env('screenshot_map_path').format(uid=uid)

    def __repr__(self):
        # Get the current module and class name dynamically
        current_module = self.__class__.__module__
        current_class = self.__class__.__name__
        title = getattr(self, 'title', None)   # if use class before crawling, raise error so here required
        return f"<{current_module}.{current_class}> {title}"  # is like: '<main.crawl.Apartment title...'

    def get(self, attr, default=None):  # add get support to use like: Apartment.get('title', None)
        return getattr(self, attr, default)

    def crawl_main_data(self, driver):
        # Extract the title
        try:
            get_element = GetElement(driver, self)
            get_value = GetValue(driver, file_crawl=self)
            self.file['title'] = get_value.get_title_of_file()

            is_timeaddress = get_element.get_time_and_address()  # returns blank if not found
            if is_timeaddress[0]:
                rough_time, rough_address = is_timeaddress[1]
                self.file['rough_time'] = rough_time
                self.file['rough_address'] = rough_address

            self.file['metraj'], self.file['age'], self.file['otagh'] = get_value.get_metraj_age_oragh()

            # Extract ejare section
            if self.is_ejare:
                self.file["vadie"], self.file["ejare"], self.file["vadie_exchange"], self.file["floor_number"] = get_value.get_vadie_ejare_andsoon()
            else:
                self.file['total_price'], self.file['price_per_meter'], self.file['floor_number'] = get_value.get_tprice_pprice_floor("total_price", "price_per_meter", "floor_number")

            try:
                # Extract پارکینگ، آسانسور، انباری، بالکن information
                general_features = [td.text.strip() for td in driver.find_elements(By.XPATH, "//td[@class='kt-group-row-item kt-group-row-item__value kt-body kt-body--stable']")]
                self.file['general_features'] = general_features
            except Exception as e:
                logger_file.error(f"couldn't get 'general_features' the card. error: {e}")
                self.file_errors.append(f"couldn't get 'general_features' the card.")

            self.file['description'] = get_value.get_description()

            tags = get_element.get_tags()
            if tags[0]:
                self.file['tags'] = tags[1]
                logger_file.info(f"tags: {tags[1]}")

            # returns like:  {'title': 'مشاورین املاک پلاک', 'subtitle': 'همهٔ آگهی\u200cهای کسب\u200cو\u200cکار'}
            agency = get_element.get_agency_info()
            if agency[0] and agency[1].get('title'):
                self.file['agency'] = agency[1].get('title')
                logger_file.info(f"agency_info: {agency[1].get('title')}")
        except Exception as e:
            logger_file.error(f"raise error in crawl main data section. error: {e}")
            self.file_errors.append(f"raise error in crawl main data section.")

    def crawl_images(self, driver):
        try:
            get_value = GetValue(driver, self)
            self.file['image_srcs'] = get_value.get_image_srcs()        # 'set' is not json serializer
        except Exception as e:
            logger.error(f"error in map section. error: {e}")
            self.file_errors.append(f"error in map section.")

    def crawl_map(self, driver):
        run_modules = RunModules(driver, self)
        map_paths = []
        map_opended = False
        run_modules.available_map_element = False  # can set True in open_map, False means there isnt any map for the file so dont add error of like: "unable to find map .." in self.file_errors
        try:
            map_opended = run_modules.open_map()[0]  # open map to take screenshot from canvas (map area)
            if not map_opended:
                return   # stop further crawling
            time.sleep(6)            # its required, canvas element cant be wait at all via selenium functions
            canvas = driver.find_element(By.CSS_SELECTOR, "canvas.mapboxgl-canvas")
            logger_file.info(f"bool map's canvas: {bool(canvas)}")

            is_uploaded = run_modules.upload_map_image(canvas, self.screenshot_map_path, "normal_view.png")
            if is_uploaded[0]:
                map_paths.append(os.path.join(self.screenshot_map_path, "normal_view.png"))
            elif run_modules.available_map_element:
                self.file_errors.append(is_uploaded[1])

            # 4. Zoom in default steps of zoom_canvas
            run_modules.zoom_canvas(canvas)
            time.sleep(5)
            is_uploaded2 = run_modules.upload_map_image(canvas, self.screenshot_map_path, "zoom_view.png")
            if is_uploaded2[0]:
                map_paths.append(os.path.join(self.screenshot_map_path, "zoom_view.png"))
            elif run_modules.available_map_element:
                self.file_errors.append(is_uploaded2[2])
        except TimeoutException:
            message = f"TimeoutException in map section."
            logger_file.error(message)
            if run_modules.available_map_element:
                self.file_errors.append(f"Exception in map section. element not found.")
        except Exception as e:
            message = f"Exception in map section. error: {e}"
            logger_file.error(message)
            if run_modules.available_map_element:
                self.file_errors.append(f"Some Fails in map section.")

        if map_opended:
            try:
                close_btn = run_modules.close_canvas(retries=3)
            except TimeoutException as e:
                message = f"map opended but cant close it. TimeoutException maybe close element not found, {e}"
                logger_file.error(message)
                self.file_errors.append("map opended but cant close it. TimeoutException maybe close element not found")
            except NoSuchElementException as e:
                message = f"map opended but cant close it. close element not found, {e}"
                logger_file.error(message)
                self.file_errors.append("map opended but cant close it. close element not found")
            except Exception as e:
                message = f"unexpected exception. map opended but cant close it. error in clicking close button: {e}"
                logger_file.error(message)
                self.file_errors.append("unexpected exception. map opended but cant close it.")
        self.file['map_paths'] = map_paths

    @Retry.run_retry
    def crawl_extra_data(self, driver):  # opens "نمایش همهٔ جزئیات" button and get: 'specs', 'features'
        # 'specs' for key:value information, and 'features' for single values (end of the subscreen)
        logger_file.info(f"starting crawl_extra_data nice")
        run_modules = RunModules(driver, self)
        try:
            run_modules.click_show_all_details()
            logger_file.info(f"successfully clicked on 'نمایش همهٔ جزئیات' button")
        except Exception as e:
            logger_file.error(f"Failed clicking on 'نمایش همهٔ جزئیات'. error: {e}")
            self.file_errors.append(f"Failed to get extra data. cant click on 'نمایش همهٔ جزئیات'")
            return       # cant get other data too so return
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
            logger_file.info(f"successfully filled 'specs'. specs number: {len(specs)}")

            # Extract full features under "امکانات"
            features = []
            feature_elements = modal_body.find_elements(By.CLASS_NAME, 'kt-feature-row')
            for el in feature_elements:
                feature = el.find_element(By.CLASS_NAME, 'kt-feature-row__title').text
                features.append(feature)
            self.file['features'] = features
            logger_file.info(f"successfully filled 'features'. features number: {len(specs)}")
        except StaleElementReferenceException as e:
            logger.exception("Error extracting data in ('نمایش همهٔ جزئیات') section. error: Stale exception.")
        except NoSuchElementException as e:
            logger.exception("Error extracting data in ('نمایش همهٔ جزئیات') section. error: Element not found – check your selector or wait conditions.")
        except TimeoutException as e:
            logger.exception("Error extracting data in ('نمایش همهٔ جزئیات') section. error: Timed out waiting for visibility.")
        except WebDriverException as e:
            logger.exception(f"Error extracting data in ('نمایش همهٔ جزئیات') section. error: WebDriver blew up: {e.__class__.__name__}, message={e.msg}")
        except Exception as e:
            message = f"Error extracting data in ('نمایش همهٔ جزئیات') section. error: {e}"
            logger_file.error(message)
            self.file_errors.append("Error extracting data in ('نمایش همهٔ جزئیات') section (after opening)")
            return {}, []

        # Close the modal by clicking the close button
        close_button = driver.find_element(By.XPATH, "//button[@class='kt-button kt-button--inlined kt-button--circular kt-modal__close-button']")
        close_button.click()

    def run(self, driver):  # Crawl all the information and add to self.file
        # its important to use try except here, to stop some further crawling at specific point (for example in crawl_map) but dont let whole programs runs flow stop at all. (get to except and prevent stop failing). so stopabale arcitecture without stop of flow is our purpose
        logger.info(f"going to crawl_main_data")
        try:
            self.crawl_main_data(driver)
        except Exception as e:
            logger.debug(f"error in .run crawl_main_data, just for debug {e}")

        try:
            self.crawl_images(driver)
        except Exception as e:
            logger.debug(f"error in .run crawl_images, just for debug {e}")

        try:
            self.crawl_map(driver)
        except Exception as e:
            logger.debug(f"error in .run crawl_map, just for debug {e}")

        try:
            self.crawl_extra_data(driver)
        except Exception as e:
            logger.debug(f"error in .run crawl_extra_data, just for debug {e}")


class ZaminKolangy(Apartment):  # general_features, specs, features removed
    def __init__(self, uid, is_ejare):
        super().__init__(uid)
        del self.file['general_features']
        del self.file['specs']
        del self.file['features']
        del self.file['age']
        del self.file['otagh']
        del self.file['floor_number']

    def crawl_main_data(self, driver):
        # Extract the title
        try:
            get_element = GetElement(driver, self)
            get_value = GetValue(driver, file_crawl=self)
            self.file['title'] = get_value.get_title_of_file()

            is_timeaddress = get_element.get_time_and_address()  # returns blank if not found
            if is_timeaddress[0]:
                rough_time, rough_address = is_timeaddress[1]
                self.file['rough_time'] = rough_time
                self.file['rough_address'] = rough_address

            # in ZaminKolagy files, we have not ejare part.
            self.file['metraj'], self.file['total_price'], self.file['price_per_meter'] = get_value.get_tprice_pprice_floor("metraj", "total_price", "price_per_meter")

            self.file['description'] = get_value.get_description()

            tags = get_element.get_tags()
            if tags[0]:
                self.file['tags'] = tags[1]
                logger_file.info(f"tags: {tags[1]}")

            # returns like:  {'title': 'مشاورین املاک پلاک', 'subtitle': 'همهٔ آگهی\u200cهای کسب\u200cو\u200cکار'}
            agency = get_element.get_agency_info()
            if agency[0] and agency[1].get('title'):
                self.file['agency'] = agency[1].get('title')
                logger_file.info(f"agency_info: {agency[1].get('title')}")
        except Exception as e:
            logger_file.error(f"raise error in crawl main data section. error: {e}")
            self.file_errors.append(f"raise error in crawl main data section.")

    def run(self, driver):  # Crawl all the information and add to self.file
        # its important to use try except here, to stop some further crawling at specific point (for example in crawl_map) but dont let whole programs runs flow stop at all. (get to except and prevent stop failing). so stopabale arcitecture without stop of flow is our purpose
        logger.info(f"going to crawl_main_data")
        try:
            self.crawl_main_data(driver)
        except Exception as e:
            logger.debug(f"error in .run crawl_main_data, just for debug {e}")

        try:
            self.crawl_images(driver)
        except Exception as e:
            logger.debug(f"error in .run crawl_images, just for debug {e}")

        try:
            self.crawl_map(driver)
        except Exception as e:
            logger.debug(f"error in .run crawl_map, just for debug {e}")


class Vila(Apartment):  # file data same with apartment
    def __init__(self, uid, is_ejare):
        super().__init__(uid, is_ejare)
        self.file['zamin_metraj'] = ''
        del self.file['floor_number']

    def crawl_main_data(self, driver):
        # Extract the title
        try:
            get_element = GetElement(driver, self)
            get_value = GetValue(driver, file_crawl=self)
            self.file['title'] = get_value.get_title_of_file()

            is_timeaddress = get_element.get_time_and_address()  # returns blank if not found
            if is_timeaddress[0]:
                rough_time, rough_address = is_timeaddress[1]
                self.file['rough_time'] = rough_time
                self.file['rough_address'] = rough_address

            self.file['metraj'], self.file['age'], self.file['otagh'] = get_value.get_metraj_age_oragh()

            # Extract ejare section
            if self.is_ejare:  # in is_ejare, Apartment and vila have a bit differrence keys
                self.file["zamin_metraj"], self.file["vadie"], self.file["ejare"], self.file["vadie_exchange"] = get_value.get_vadie_ejare_andsoon()
            else:  # in sell, Apartment and vila have a bit differrence keys
                self.file['zamin_metraj'], self.file['total_price'], self.file['price_per_meter'] = get_value.get_tprice_pprice_floor("zamin_metraj", "total_price", "price_per_meter")

            try:
                # Extract پارکینگ، آسانسور، انباری، بالکن information
                general_features = [td.text.strip() for td in driver.find_elements(By.XPATH, "//td[@class='kt-group-row-item kt-group-row-item__value kt-body kt-body--stable']")]
                self.file['general_features'] = general_features
            except Exception as e:
                logger_file.error(f"couldn't get 'general_features' the card. error: {e}")
                self.file_errors.append(f"couldn't get 'general_features' the card.")

            self.file['description'] = get_value.get_description()

            tags = get_element.get_tags()
            if tags[0]:
                self.file['tags'] = tags[1]
                logger_file.info(f"tags: {tags[1]}")

            # returns like:  {'title': 'مشاورین املاک پلاک', 'subtitle': 'همهٔ آگهی\u200cهای کسب\u200cو\u200cکار'}
            agency = get_element.get_agency_info()
            if agency[0] and agency[1].get('title'):
                self.file['agency'] = agency[1].get('title')
                logger_file.info(f"agency_info: {agency[1].get('title')}")
        except Exception as e:
            logger_file.error(f"raise error in crawl main data section. error: {e}")
            self.file_errors.append(f"raise error in crawl main data section.")

    def run(self, driver):  # Crawl all the information and add to self.file
        # its important to use try except here, to stop some further crawling at specific point (for example in crawl_map) but dont let whole programs runs flow stop at all. (get to except and prevent stop failing). so stopabale arcitecture without stop of flow is our purpose
        logger.info(f"going to crawl_main_data")
        try:
            self.crawl_main_data(driver)
        except Exception as e:
            pass

        try:
            self.crawl_images(driver)
        except Exception as e:
            pass

        try:
            self.crawl_map(driver)
        except Exception as e:
            pass

        try:
            self.crawl_extra_data(driver)
        except Exception as e:
            pass

def get_files(location_to_search, max_files=1):
    # cards_on_screen just for test. crawl only specific card. its value is a ["a card element (html)"]
    driver = uc_replacement_setup()
    wait = WebDriverWait(driver, 10)
    base_url = "https://divar.ir"
    url = settings.APARTMENT_EJARE_ZAMIN
    retry, attempt = 2, 1
    #url = ""
    # video
    #url = "https://divar.ir/s/tehran/buy-apartment?bbox=51.0929756%2C35.5609856%2C51.6052132%2C35.8353386&has-photo=true&has-video=true&map_bbox=51.09297561645508%2C35.56098556518555%2C51.6052131652832%2C35.8353385925293&map_place_hash=1%7C%7Capartment-sell"
    try:
        driver.get(url)  # Load the web page
        crawl_modules = RunModules(driver)

        try:
            crawl_modules.close_map(retries=1)
        except Exception as e:
            logger.info(f"failed in map closing task. skipping.")

        try:
            # search box
            search_input = wait.until(
                EC.visibility_of_element_located((By.CSS_SELECTOR, 'input.kt-nav-text-field__input')))
            search_input.send_keys(location_to_search)  # type in search box to search
            search_input.send_keys(Keys.ENTER)
            time.sleep(1)

            # Initialize variables to track scroll position and loaded cards
            last_height = driver.execute_script("return document.body.scrollHeight")

            # Scroll down and add all founded card to 'cards'
            cards = []  # using set() make unordered of cards
            unique_cards_counts = 0
            while True:
                try:
                    card_selector = "article.unsafe-kt-post-card"
                    wait.until(EC.presence_of_element_located(
                        (By.CSS_SELECTOR,
                         card_selector)))  # driver.find_elements(By.CSS_SELECTOR, 'article.kt-post-card')
                    # 2. Find all card elements now that we know they exist
                    cards_on_screen = driver.find_elements(By.CSS_SELECTOR, card_selector)
                    logger.info(f"cards_on_screen: {len(cards_on_screen)}")
                except Exception as e:
                    logger.error(f"Fails getting cards via article.kt-post-card element. error: {e}")
                    cards_on_screen = []
                get_element = GetElement(driver)
                urls_of_cards = [url for uid, url in cards]
                for card in cards_on_screen:
                    sucs_title = get_element.get_title_from_cardbox(card)
                    sucs_url = get_element.get_url_from_cardbox(card)
                    sucs_uid = get_element.get_uid(sucs_url[1])
                    # some carts are blank or duplicate crawling. required to be checked here
                    if sucs_title[0] and sucs_url[0]:
                        # we dont want uid prints to mutch in our .log, to find faster specific file and debug it
                        logger.info(f"succesfully obtained url and title of the card: {bool(sucs_url[1])}, {bool(sucs_title[1])}")
                    elif sucs_url[0] and not sucs_title[0]:
                        logger.error(f"Could not retrieve title for the card. url of card: {sucs_url[1]}, full error message: {sucs_title[1]}")
                    elif not sucs_url[0] and sucs_title[0]:
                        logger.error(f"Could not retrieve url for the card. title of card: {sucs_title[1]}, full error message: {sucs_url[1]}")
                    else:
                        logger.error(f"Could not retrieve title and url of the card. title error: {sucs_title}, url error: {sucs_url}")

                    if sucs_url[0] and sucs_title[0] and sucs_url[1] not in urls_of_cards and \
                            (not max_files or len(cards) < max_files):  # Note '<=' is false!
                        # absolute_url = urljoin(base_url, sucs_url[1])
                        cards.append((sucs_uid[1], sucs_url[1]))  # sucs_url[1] is already full url
                    else:  # some carts are blank, required to skip them
                        pass
                unique_cards_counts =+ set_uid_url_redis(cards)
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
                    break  # skip scroll and exit while loop

            logger.info(f"---cards finds: {unique_cards_counts}")
        except Exception as e:
            logger.error(f"failed add to search box and so on. error: {e}")

    except Exception as e:
        logger.error(f"failed running driver. retry: {attempt}/{retry}. error: {e}")

    finally:
        driver.quit()  # dont need reraise to came here
        set_driver_to_free()
        logger.info(f"---card finder quited clean.")


@retry_func(max_attempts=5, delay=20, fail_message_after_attempts='max retry. going to terminate thread. cards not founds')
def crawl_file():  # each thread runs separatly
    category = settings.CATEGORY
    is_ejare = settings.IS_EJARE
    is_saved_to_redis = False
    errors = []
    with _pop_lock:
        uid, url = get_uid_url_redis()
    if url and uid:
        driver = None
        try:
            driver = uc_replacement_setup(uid)

            if category == 'apartment':
                file_instance = Apartment
            elif category == 'zamin_kolangy':
                file_instance = ZaminKolangy
            elif category == 'vila':
                file_instance = Vila
            logger_separation.info("")
            logger_separation.info("----------")
            logger_file.info(f"--going to card {uid}. card url: {url}")
            set_random_agent(driver)  # set random agent every time called
            driver.get(url)
            time.sleep(2)
            file_crawl = file_instance(uid=uid, is_ejare=is_ejare)
            logger_file.info(f"selected file_crawl category {category}: {file_crawl}")
            try:
                file_crawl.file['url'] = url  # save url before crawl others
                file_crawl.file['uid'] = uid
                file_crawl.run(driver)  # fills .file

                if settings.WRITE_REDIS_MONGO:  # is_ejare should no conflicts with 'ejare' price inside redis
                    add_to_redis({**file_crawl.file, "category": category, "is_ejare": is_ejare,
                                  "file_errors": file_crawl.file_errors})
                    is_saved_to_redis = True
            except Exception as e:
                logger_file.error(f"failed cart to crawl. error: {e}")
                errors.append(f"failed cart to crawl. error: {e}")
                raise

            return True   # for retry functionality
        except Exception as e:
            errors.append(f"Failed totally. error: {e}")
        finally:
            if driver:
                driver.quit()
                set_driver_to_free(uid, is_saved_to_redis, errors)
                logger.info(f"card crawler quited clean.")
    else:
        logger_file.info(f"cards list is blank. wait to find by card finder..")


def test_crawl(url="https://divar.ir"):
    driver = advance_setup()
    driver.get(url)
