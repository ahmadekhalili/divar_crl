from concurrent.futures import ThreadPoolExecutor, as_completed
from django.core.management.base import BaseCommand
from django.db import close_old_connections
from django.conf import settings
from main.serializers import FileMongoSerializer
from main.crawl import get_files, crawl_file
from main.methods import write_by_django

import logging
import threading
logger = logging.getLogger('web')


class Command(BaseCommand):   # 3 thread of craw card and 1 thread of find_cards so need 4 separate driver
    help = "Launch the Divar crawler in a 3-thread pool (no web requests)."

    def handle(self, *args, **options):
        max_files = settings.MAX_FILE_CRAWL
        location_to_search = 'کیانشهر'

        task1 = threading.Thread(target=get_files, args=(location_to_search, max_files))
        task1.start()
        logger.info(f"Started main thread to get cards")

        max_threads = 4
        logger.info("Starting crawl with %d threads...", max_threads)
        # use ThreadPoolExecutor for simple parallelism
        with ThreadPoolExecutor(max_workers=max_threads) as executor:
            tasks = [executor.submit(crawl_file) for _ in range(max_threads)]
            for future in as_completed(tasks):
                try:
                    result = future.result()
                    logger.info("Thread finished: %s", result)
                except Exception as e:
                    logger.exception(f"Crawl thread error: {e}")

        logger.info("All crawl threads complete.")
