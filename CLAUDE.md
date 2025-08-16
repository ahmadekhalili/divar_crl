# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Django-based web crawler system for scraping real estate listings from Divar.ir (Iranian classified ads). The project uses a hybrid architecture combining Django as the main web framework with FastAPI for specific operations, MongoDB for data storage, Redis for task coordination, and Selenium for web scraping.

## Architecture

### Core Components
- **Django App** (`main/`): Main crawler logic, REST API endpoints, management commands
- **FastAPI Service** (`fastapi_app/`): Handles file uploads and MongoDB operations
- **Crawler Engine** (`main/crawl.py`): Multi-threaded scraping with property-specific classes (`Apartment`, `ZaminKolangy`, `Vila`)
- **Centralized Logging** (`central_logging.py`): Thread-aware logging across all components

### Key Databases
- **MongoDB**: Primary storage for crawled listings (required)
- **Redis**: Task queuing and driver coordination (required) 
- **SQLite**: Django's default database for admin/sessions

## Essential Setup

### Required External Services
```bash
# MongoDB (port 27017)
net start MongoDB

# Redis (port 6379)
docker run -d --name redis -p 6379:6379 -v redis_data:/data redis/redis-stack-server:latest

# FastAPI service (port 8001)
uvicorn fastapi_app.main:app --port 8001
```

### Environment Configuration (.env)
Key settings that must be configured together:
- `FILE_STATUS`: Target URL for crawling
- `CATEGORY`: "apartment", "zamin_kolangy", or "vila" 
- `IS_EJARE`: Boolean for rental vs sale listings

Cross-platform driver paths:
- `DRIVER_PATH1`/`CHROME_PATH1`: Linux paths
- `DRIVER_PATH1_win`/`CHROME_PATH1_win`: Windows paths

## Development Commands

### Django Management
```bash
# Main multi-threaded crawler
python manage.py crawl

# Update existing listings and mark expired
python manage.py update

# Django development server
python manage.py runserver
```

### Testing Specific Properties
Set `TEST_MANUAL_CARD_SELECTION = [(file_uid, file_url)]` in settings.py for targeted crawling.

## Important Implementation Details

### Multi-Threading Architecture
- Configurable driver pool (`DRIVERS_COUNT = 3`)
- Redis-based coordination prevents driver conflicts
- Each thread handles multiple properties (`CARDS_EACH_DRIVER = 7`)

### Property Type Classes
Different scraping logic for each property type:
- `Apartment`: Full feature set (floor, elevator, parking)
- `Vila`: Land area focus, different pricing structure
- `ZaminKolangy`: Simplified land/old house model

### File Organization
- Images: `media/file_{uid}/file_images/`
- Maps: `media/file_{uid}/file_mapes/`
- Logs: Separate files per component (django.log, driver.log, redis.log, etc.)

## Testing and Debugging
Map crawling includes sophisticated building detection from Mapbox tiles and screenshot capture for debugging.