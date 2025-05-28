from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from rest_framework.response import Response

from pathlib import Path
from redis.commands.json.path import Path as RedisPath
from mapbox_vector_tile import decode
import numpy as np
import random
import time
import os
import re
from scipy.special import expit
import requests
import logging
import redis
import json
import functools
import threading
import environ

from .redis_client import REDIS

BASE_DIR = Path(__file__).resolve().parent.parent
logger = logging.getLogger('web')
logger_separation = logging.getLogger("web_separation")
logger_file = logging.getLogger('file')
driver_logger = logging.getLogger('driver')
env = environ.Env()
env.read_env(os.path.join(BASE_DIR, '.env'))


class HumanMouseMove:
    @staticmethod
    def generate_bezier_curve(start, control, end, num_points=40):
        """تولید مسیر منحنی Bézier برای حرکت طبیعی موس"""
        t_values = np.linspace(0, 1, num_points)
        curve = np.array([
            (1 - t) ** 2 * np.array(start) +
            2 * (1 - t) * t * np.array(control) +
            t ** 2 * np.array(end)
            for t in t_values
        ])
        return curve

    @staticmethod
    def sigmoid_speed_curve(num_points):
        """ایجاد لیستی از زمان‌بندی‌های حرکت بر اساس تابع سیگموئید"""
        x = np.linspace(-5, 5, num_points)
        y = expit(x)  # خروجی تابع سیگموئید
        return np.diff(y) * 2  # تبدیل به اختلاف زمانی برای حرکت نرم‌تر

    @staticmethod
    def add_random_noise(path, max_noise=2):
        """افزودن نویز تصادفی برای شبیه‌سازی لرزش‌های طبیعی دست انسان"""
        noise = np.random.randint(-max_noise, max_noise + 1, path.shape)
        return np.clip(path + noise, 0, None)  # جلوگیری از مقدار منفی

    @staticmethod
    def human_mouse_move(actions, start, end, duration=2, window_width=1920, window_height=1080):
        """Simulate human-like mouse movement while ensuring the mouse stays within bounds."""
        control = (
            (start[0] + end[0]) // 2 + random.randint(-100, 100),
            (start[1] + end[1]) // 2 + random.randint(-100, 100)
        )

        path = HumanMouseMove.generate_bezier_curve(start, control, end)
        path = HumanMouseMove.add_random_noise(path, max_noise=3)
        speed_curve = HumanMouseMove.sigmoid_speed_curve(len(path) + 1)
        actions.move_by_offset(0, 0)
        x,y = 0,0
        for i in range(1, len(path)):
            # Clamp the coordinates to ensure they stay within window bounds
            step1, step2 = path[i-1], path[i]
            step1_x, step1_y = min(max(0, int(step1[0])), window_width),  min(max(0, int(step1[1])), window_height)
            step2_x, step2_y = min(max(0, int(step2[0])), window_width), min(max(0, int(step2[1])), window_height)
            x += step2_x - step1_x
            y += step2_y - step1_y
            actions.move_by_offset(step2_x - step1_x, step2_y - step1_y)  # Move relative to start
            delay = (speed_curve[i] * duration / sum(speed_curve)) + random.uniform(0.001, 0.01)
            time.sleep(delay)

            if random.random() < 0.05:
                time.sleep(random.uniform(0.05, 0.2))
        return actions


def sync_upload_and_get_image_paths(urls, file_number):   # upload the image full url to example: /media/file_images/file 1
    folder = 'file_images'
    sub_folder = f"file {file_number}"
    paths = []
    for url in urls:
        response = requests.get(url)
        if response.status_code == 200:
            filename = os.path.basename(url.split('?')[0])  # حذف query params
            path = os.path.join(folder, sub_folder, filename)
            saved_path = default_storage.save(path, ContentFile(response.content))
            paths.append(path)
    return None


def retry_func(max_attempts=2, delay=20, fail_message_after_attempts='', loger=logger, retry_msg=''):
    """Retry decorator for acquiring Chrome driver in a thread-safe way."""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_attempts):
                loger.info(f"try run {func.__name__}, attempt: {attempt+1}/{max_attempts}", extra={"thread_name": threading.current_thread().name})
                result = func(*args, **kwargs)
                if result:
                    return result
                if retry_msg:
                    loger.info(f"{retry_msg}. attempts: {attempt+1}/{max_attempts}")
                else:
                    loger.debug(f"retry again, result was: {result}")
                time.sleep(delay)
            if fail_message_after_attempts:
                loger.info(f"{fail_message_after_attempts} after {max_attempts} attempts.")
            return None
        return wrapper
    return decorator


def write_by_django(serializer, unique_files, errors):
    s = serializer(data=unique_files, many=True)
    if s.is_valid():
        logger.info(f"for is valid")
        files = s.save()
        return Response({'files_saved': len(files), 'files_failed': errors})
    else:
        logger.error(f"for is not valid, error: {s.errors}")
        return Response(s.errors)


def get_paths_from_template(full_path: str,
                        start_index: int = 1,
                        stop_index: int = 100):
    """
    full_path (template): e.g. /.../drivers/driver-1/chrome.exe
    Return a list of Paths like
    [/.../drivers/driver-2/chrome.exe, /.../drivers/driver-3/chrome.exe, ...]
    """
    full_path = Path(full_path).expanduser().resolve()

    filename         = full_path.name            # chrome.exe
    series_dir       = full_path.parent          # driver-1
    drivers_root_dir = series_dir.parent         # drivers

    # strip “-<digits>” at end of directory name
    series_stem = re.sub(r'-\d+\s*$', '', series_dir.name)  # -> 'driver'

    missing_in_a_row = False
    siblings = []

    for i in range(start_index, stop_index):
        candidate_dir = drivers_root_dir / f"{series_stem}-{i}"
        candidate_file = candidate_dir / filename

        if candidate_dir.is_dir():
            if missing_in_a_row:
                logger.error(f"*******driver {siblings[-1]} has not valid format. skip others")
            siblings.append(str(candidate_file))
        else:
            if missing_in_a_row:
                break  # two missing_in_a_row, means we reach end of drivers and there is not more
            missing_in_a_row = True

    if not siblings:
        logger.error("No sibling driver directories found for %s", full_path)

    return siblings


def add_driver_to_redis():  # rewrite (refresh with new dirs) if needed
    DRIVERS_CHROMS = []   # should be list of like: {'uid': None, 'driver_path': .., 'chrome_path': ..}
    drivers_path = get_paths_from_template(env('DRIVER_PATH1'))
    chromes_path = get_paths_from_template(env('CHROME_PATH1'))
    limit = min(settings.DRIVERS_COUNT, len(drivers_path), len(chromes_path))
    for driver_dir, chrome_dir in zip(drivers_path[:limit], chromes_path[:limit]):  # auto iter based on smallest of drivers_path, chromes_path
        DRIVERS_CHROMS.append({'uid': None, 'driver_path': driver_dir, 'chrome_path': chrome_dir})
    REDIS.json().set('drivers_chromes', RedisPath.root_path(), DRIVERS_CHROMS)


def get_driver_from_redis():
    return REDIS.json().get('drivers_chromes')


def set_driver_to_redis(data=None):
    REDIS.json().set('drivers_chromes', RedisPath.root_path(), data)
    driver_logger.info(f"successfully updates redis 'drivers_chromes")


def add_final_card_to_redis(data, file_crawl_extra):
    try:
        logger.info(f"going to write in redis data: {data}")
        REDIS.xadd('data_stream', {'data': json.dumps(data, ensure_ascii=False),
                                   'file_crawl_extra': json.dumps(file_crawl_extra, ensure_ascii=False)})
    except Exception as e:
        logger.error(f"raise error adding file record to the redis. error: {e}")
        raise   # reraise for upstream workflow


def set_uid_url_redis(cards, data_key='uid_url_list', uid_set_key='unique_uid'):
    """
    cards: list of (title, url)
    data_key: in db like. title_url_list: 1) "Title 1|https://example.com/page1"
                                          2) "Title 2|https://example.com/page2"
    url_set_key: Redis set to track unique uids. is like: unique_uid: 1) "uid1" 2) "uid2"
    Important: unique_uid remains untouched, but uid_url_list popes by card crawler thread (after crawled)
    """
    added_count = 0
    duplicate_count = 0

    for uid, url in cards:
        if REDIS.sadd(uid_set_key, uid):  # Returns 1 if added (unique), 0 if already exists
            REDIS.rpush(data_key, f"{uid}|{url}")  # or use json.dumps({...})
            added_count += 1
        else:
            duplicate_count += 1

    logger.debug(f"Added cards to redis: {added_count}, duplicates not added: {duplicate_count}")
    return added_count

def get_uid_url_redis():  # return (None, None) in blank is required
    uid, url = None, None
    # Blocks until an element is available
    # suppose 20 threads arrive here; Redis makes each thread block (sleep). They do not consume CPU
    try:
        logger_file.info("pending to get card from redis to start crawl...")
        item = REDIS.blpop("uid_url_list", timeout=settings.CARD_CRAWLER_PENDDINGS)  # pops oldest item (left-most), brpop newest. returns None after 120
        if item:
            _, value = item
            uid, url = value.split("|", 1)  # max split 1
            remaining = REDIS.llen("uid_url_list")  # get remaining number of items
            logger_file.info(f"uid & url popped successfully from redis to start crawl. remains cards in db: {remaining}")
            return uid, url
        else:
            logger_file.info(f"there isn't any card in redis to get and crawl.")
    except Exception as e:
        logger_file.error(f"Error getting from redis record. error: {e}")
    return uid, url


class MapTileHandlerBalad:  # in crawl, its for divar canvas

    def vector_to_pixel(self, x, y, extend):  # i think every site totally has same extend, but send extend value in each network request
        px = x / extend * 256
        py = 256 - (y / extend * 256)
        return px, py

    def get_tile_cordinator(self, url):  # return 42134,25816 from url like: https://tiles.raah.ir/tiles/high/16/42134/25816.pbf?version=3
        pattern = r"/(\d+)/(\d+)\.pbf"
        match = re.search(pattern, url)
        if match:
            return match.groups()
        return None, None

    def generate_tile_key(self, url):      # key identifier for saves, query ... in db.  like: '42134_25816'
        tile_x_y = self.get_tile_cordinator(url)
        return f"{tile_x_y[0]}_{tile_x_y[1]}"

    def get_tile_location_and_buildings(self, pbf_url):
        buildings_info = []   # in fastapi model field, buildings_info is list
        pbf = requests.get(pbf_url, timeout=15).content
        tile_dict = decode(pbf)
        if not "Points_of_Interest" in tile_dict:
            logger_file.info(".pbf has not 'Points_of_Interest' layer.")
        else:
            buildings_data = tile_dict["Points_of_Interest"]
            buildings = buildings_data["features"]
            extent = buildings_data.get("extent", 4096)

            success, total = 0, len(buildings)
            for i, building in enumerate(buildings):
                px, py = None, None
                try:
                    vector_location = building['geometry'].get('coordinates')
                    # building not be out of tile
                    if vector_location and 0 <= vector_location[0] <= extent and 0 <= vector_location[1] <= extent:
                        px, py = self.vector_to_pixel(vector_location[0], vector_location[1], extent)

                        building_name = building["properties"].get("title_fa")
                        building_icon = building["properties"].get("icon")
                        buildings_info.append({'building_location': (px, py), 'building_name': building_name, 'building_icon': building_icon})
                    success += 1  # out of if scop

                except Exception as e:
                    logger_file.error(f"raise error getting buildings info, skip. error: {e}")
        logger_file.info(f"successfully extrac map buildings: {success}/{total}")
        return buildings_info

    def get_tiles_location_and_buildings(self, pbf_urls):
        tiles_info = {}
        for pbf_url in pbf_urls:
            tile_x_y = self.get_tile_cordinator(pbf_url)
            tiles_info[self.generate_tile_key(pbf_url)] = self.get_tile_location_and_buildings(pbf_url)
        return tiles_info

    def download_pbfs(self, start_x, start_y, end_x, end_y):
        pass


class MapTileHandlerDivar(MapTileHandlerBalad):  # url of pbfs is exact same
    pass
