import pymongo
from django.conf import settings
import logging # Optional: for logging connection status

logger = logging.getLogger(__name__)

_mongo_client = None
_mongo_db = None

def get_mongo_client():
    """
    Initializes and returns a singleton pymongo MongoClient instance.
    Reads connection details from Django settings.
    """
    global _mongo_client
    if _mongo_client is None:
        try:
            uri = settings.MONGO_URI # Use the URI constructed in settings.py
            logger.info(f"Connecting to MongoDB using URI: {settings.MONGO_HOST}:{settings.MONGO_PORT}...") # Avoid logging full URI with creds
            _mongo_client = pymongo.MongoClient(uri, serverSelectionTimeoutMS=5000)  # Add timeout

            # The ismaster command is cheap and does not require auth.
            _mongo_client.admin.command('ismaster')
            logger.info("MongoDB connection successful.")

        except pymongo.errors.ConnectionFailure as e:
            logger.error(f"MongoDB connection failed: {e}")
            # Decide how to handle: raise exception, return None, etc.
            # Raising might be appropriate on startup if DB is critical
            _mongo_client = None # Ensure it stays None on failure
            raise ConnectionFailure("Could not connect to MongoDB") from e
        except Exception as e:
            logger.error(f"An unexpected error occurred during MongoDB connection: {e}")
            _mongo_client = None
            raise ConnectionFailure("Could not connect to MongoDB") from e

    return _mongo_client

def get_mongo_db():
    """
    Returns a singleton pymongo database instance based on the client.
    """
    global _mongo_db
    if _mongo_db is None:
        client = get_mongo_client() # Ensures client is initialized
        if client:
            try:
                db_name = settings.MONGO_DBNAME
                _mongo_db = client[db_name]
            except Exception as e:
                logger.error(f"Could not get MongoDB database handle '{settings.MONGO_DBNAME}': {e}")
                _mongo_db = None # Ensure it stays None on failure
                raise # Re-raise after logging
        else:
             # Client connection failed earlier, cannot get DB handle
             logger.error("Cannot get MongoDB database handle because client connection failed.")
             # Depending on application logic, you might return None or raise error
             return None # Or raise ConnectionFailure("MongoDB client not available")

    return _mongo_db

# Custom exception for clarity
class ConnectionFailure(Exception):
    pass
