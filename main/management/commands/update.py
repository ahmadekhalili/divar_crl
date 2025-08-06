from concurrent.futures import ThreadPoolExecutor, as_completed
from django.core.management.base import BaseCommand
from django.db import close_old_connections
from django.conf import settings
from main.serializers import FileMongoSerializer
from main.crawl import get_files, update_file, provide_update_file
from main.methods import write_by_django, add_driver_to_redis

import os
import logging
import environ
import threading

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
logger = logging.getLogger('web')
env = environ.Env()
env.read_env(os.path.join(BASE_DIR, '.env'))


class Command(BaseCommand):   # 3 thread of craw card and 1 thread of find_cards so need 4 separate driver
    help = "Launch the Divar crawler in a 3-thread pool (no web requests)."

    def handle(self, *args, **options):
        max_files = settings.MAX_FILE_CRAWL
        location_to_search = 'کیانشهر'

        add_driver_to_redis()

        task1 = threading.Thread(target=provide_update_file, name="file_provider")
        task1.start()
        logger.info(f"Started main thread to update cards")

        max_threads = settings.DRIVERS_COUNT - 1
        logger.info("Starting crawl with %d threads...", max_threads)
        # give the pool a prefix; threads will be named thread_0, thread_1, …
        with ThreadPoolExecutor(max_workers=max_threads, thread_name_prefix="thread_pol") as executor:
            tasks = [executor.submit(update_file) for _ in range(max_threads)]
            for future in as_completed(tasks):
                try:
                    result = future.result()
                    logger.info("Thread finished: %s", result)
                except Exception as e:
                    logger.exception(f"Crawl thread error: {e}")

        logger.info("All threads complete.")
