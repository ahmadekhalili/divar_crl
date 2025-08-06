# central_logging.py
import os
import logging
import logging.config
from pathlib import Path

# Get the base directory (adjust path as needed for your project structure)
BASE_DIR = Path(__file__).resolve().parent

# Create logs directory if it doesn't exist
LOGS_DIR = BASE_DIR / 'logs'
LOGS_DIR.mkdir(exist_ok=True)

CENTRAL_LOGGING_CONFIG = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        # Django formatters
        'verbose': {
            'format': '[%(asctime)s] %(levelname)s [%(threadName)s] %(message)s',
            'datefmt': '%Y-%m-%d %H:%M:%S',
        },
        'indented': {
            'format': '  [%(asctime)s] %(levelname)s [%(threadName)s] %(message)s',
            'datefmt': '%Y-%m-%d %H:%M:%S',
        },
        'card_separation': {
            'format': '%(message)s',
        },
        'reverse_verbose': {
            'format': '[%(message)s %(asctime)s] %(levelname)s [%(threadName)s]',
            'datefmt': '%Y-%m-%d %H:%M:%S',
        },
        'simple': {
            'format': '%(levelname)s %(message)s',
        },
        # FastAPI formatters
        'default': {
            'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        },
        'clean_card': {
            'format': '%(asctime)s - %(message)s'
        }
    },
    'handlers': {
        # Django handlers
        'django_file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': str(LOGS_DIR / 'django.log'),
            'formatter': 'verbose',
            'encoding': 'utf-8',
        },
        'web_file': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': str(LOGS_DIR / 'web.log'),
            'formatter': 'verbose',
            'encoding': 'utf-8',
        },
        'web_file_separation': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': str(LOGS_DIR / 'web.log'),
            'formatter': 'card_separation',
            'encoding': 'utf-8',
        },
        'file_file': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': str(LOGS_DIR / 'web.log'),
            'formatter': 'indented',
            'encoding': 'utf-8',
        },
        'driver_handler': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': str(LOGS_DIR / 'driver.log'),
            'formatter': 'verbose',
            'encoding': 'utf-8',
        },
        'redis_handler': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': str(LOGS_DIR / 'redis.log'),
            'formatter': 'reverse_verbose',
            'encoding': 'utf-8',
        },
        # FastAPI handlers
        'fastapi_file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': str(LOGS_DIR / 'fastapi.log'),
            'maxBytes': 5*1024*1024,
            'backupCount': 2,
            'formatter': 'default',
            'encoding': 'utf-8',
        },
        'cards_file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': str(LOGS_DIR / 'cards.log'),
            'maxBytes': 5*1024*1024,
            'backupCount': 2,
            'formatter': 'clean_card',
            'encoding': 'utf-8',
        },
        # Console handlers
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
            'level': 'INFO',
        },
        'console_file': {
            'class': 'logging.StreamHandler',
            'formatter': 'indented',
            'level': 'INFO',
        },
        'console_fastapi': {
            'class': 'logging.StreamHandler',
            'formatter': 'default'
        },
    },
    'loggers': {
        # Root logger
        '': {
            'handlers': ['console'],
            'level': 'INFO',
        },
        # Django loggers
        'django': {
            'handlers': ['django_file', 'console'],
            'level': 'INFO',
            'propagate': False,
        },
        'web': {
            'handlers': ['web_file', 'console'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'web_separation': {
            'handlers': ['web_file_separation', 'console'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'file': {
            'handlers': ['file_file', 'console_file'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'driver': {
            'handlers': ['driver_handler', 'console'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'redis': {
            'handlers': ['redis_handler'],
            'level': 'DEBUG',
            'propagate': False,
        },
        # FastAPI loggers
        'fastapi': {
            'handlers': ['fastapi_file'],
            'level': 'DEBUG',
            'propagate': False
        },
        'cards': {
            'handlers': ['cards_file'],
            'level': 'DEBUG',
            'propagate': False
        },
    },
}

def init_central_logging():
    """Initialize the central logging configuration"""
    logging.config.dictConfig(CENTRAL_LOGGING_CONFIG)

# Convenience function to get loggers
def get_logger(name):
    """Get a logger with the specified name"""
    return logging.getLogger(name)

# Initialize logging when this module is imported
init_central_logging()
