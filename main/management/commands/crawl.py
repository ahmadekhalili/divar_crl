from concurrent.futures import ThreadPoolExecutor, as_completed
from django.core.management.base import BaseCommand
from django.db import close_old_connections
from django.conf import settings
from main.serializers import FileMongoSerializer
from main.crawl import get_files, crawl_file, test_crawl
from main.methods import write_by_django, add_driver_to_redis

import os
import sys
import signal
import logging
import environ
import threading

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
logger = logging.getLogger('web')
env = environ.Env()
env.read_env(os.path.join(BASE_DIR, '.env'))


class Command(BaseCommand):
    help = "Launch the Divar crawler in a 3-thread pool (no web requests)."

    def __init__(self):
        super().__init__()
        self.shutdown_event = threading.Event()

    def signal_handler(self, signum, frame):
        self.stdout.write(self.style.WARNING('Received interrupt signal. Shutting down...'))
        self.shutdown_event.set()
        sys.exit(0)

    def handle(self, *args, **options):
        # When you press Ctrl+C, OS sends SIGINT signal and so calls self.signal_handler
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)

        max_files = settings.MAX_FILE_CRAWL
        location_to_search = 'کیانشهر'

        test_uids_urls = settings.TEST_MANUAL_CARD_SELECTION
        if test_uids_urls:
            with ThreadPoolExecutor(max_workers=1, thread_name_prefix="test_thread") as executor:
                task = executor.submit(test_crawl, test_uids_urls[0][0], test_uids_urls[0][1])
                try:
                    # Use timeout to allow periodic checking for interrupts
                    result = task.result(timeout=1.0)
                    logger.debug("Thread finished: %s", result)
                except TimeoutError:
                    # Check if shutdown was requested
                    if self.shutdown_event.is_set():
                        task.cancel()
                        return
                    # Continue waiting
                    result = task.result()
                    logger.debug("Thread finished: %s", result)
                except Exception as e:
                    logger.exception(f"Crawl thread error: {e}")

        else:
            add_driver_to_redis()

            task1 = threading.Thread(target=get_files, name="cards_finder", args=(location_to_search, max_files))
            task1.start()
            logger.info(f"Started main thread to get cards")

            max_threads = settings.DRIVERS_COUNT-1      # thread = drivers - 1 (one thread for card_finder main thread)
            logger.info("Starting crawl with %d threads...", max_threads)
            # give the pool a prefix; threads will be named thread_0, thread_1, …
            with ThreadPoolExecutor(max_workers=max_threads, thread_name_prefix="thread_pol") as executor:
                tasks = [executor.submit(crawl_file) for _ in range(max_threads)]
                for future in as_completed(tasks):
                    try:
                        result = future.result()
                        logger.info("Thread finished: %s", result)
                    except Exception as e:
                        logger.exception(f"Crawl thread error: {e}")

        logger.info("All threads complete.")
