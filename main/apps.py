from django.apps import AppConfig

import os


class MainConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'main'

    def ready(self):
        # Avoid running on autoreload
        if os.environ.get('RUN_MAIN') == 'true':
            from .methods import add_driver_to_redis
            add_driver_to_redis()
