import numpy as np
import random
import time
import os

from django.conf import settings
from rest_framework.response import Response
from scipy.special import expit
import requests
import logging
import redis
import json

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage

logger = logging.getLogger('web')


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


def write_by_django(serializer, unique_files, errors):
    s = serializer(data=unique_files, many=True)
    if s.is_valid():
        logger.info(f"for is valid")
        files = s.save()
        return Response({'files_saved': len(files), 'files_failed': errors})
    else:
        logger.error(f"for is not valid, error: {s.errors}")
        return Response(s.errors)

def set_random_agent(driver):
    agents = settings.AGENTS
    rnd = random.randrange(len(agents))
    ua = agents[rnd]
    logger.info(f"--change user agent. number: {rnd}")
    driver.execute_cdp_cmd(
        "Network.setUserAgentOverride",
        {"userAgent": ua}
    )


def add_to_redis(data):
    try:
        r = redis.Redis()
        logger.info(f"going to write in redis data: {data}")
        r.xadd('data_stream', {'data': json.dumps(data, ensure_ascii=False)})
    except Exception as e:
        logger.error(f"raise error adding file record to the redis. error: {e}")
        raise   # reraise for upstream workflow
