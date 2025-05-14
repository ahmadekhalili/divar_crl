import logging
import logging.config
from pathlib import Path

Path("logs").mkdir(parents=True, exist_ok=True)


LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",  # dont use — in utf8 encoding
        },
        "clean_card": {
            "format": "%(asctime)s - %(message)s"
        }
    },
    "handlers": {
        "fastapi_file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": "logs/fastapi.log",
            "maxBytes": 5*1024*1024,
            "backupCount": 2,
            "formatter": "default",
            "encoding": "utf-8",
        },
        "cards_file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": "logs/cards.log",
            "maxBytes": 5*1024*1024,
            "backupCount": 2,
            "formatter": "clean_card",
            "encoding": "utf-8",
        },
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "default"
        },
    },
    "loggers": {
        "": {  # root logger
            "handlers": ["console"],
            "level": "INFO",
        },
        "fastapi": {
            "handlers": ["fastapi_file"],
            "level": "DEBUG",
            "propagate": False
        },
        "cards": {
            "handlers": ["cards_file"],
            "level": "DEBUG",
            "propagate": False
        },
    }
}

def init_logging():
    logging.config.dictConfig(LOGGING)

