import numpy as np
import random
import time
import os
from scipy.special import expit
import requests

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage


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


def upload_and_get_image_paths(url, file_number):   # upload the image full url to example: /media/file_images/file 1
    folder = 'file_images'
    sub_folder = f"file {file_number}"
    response = requests.get(url)
    if response.status_code == 200:
        filename = os.path.basename(url.split('?')[0])  # حذف query params
        path = os.path.join(folder, sub_folder, filename)
        saved_path = default_storage.save(path, ContentFile(response.content))
        return path
    return None
