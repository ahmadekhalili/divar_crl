# 🏠 Divar CRL - Real Estate Crawler

A Django-based web crawler system for scraping real estate listings from Divar.ir with multi-threaded processing and advanced data extraction capabilities.

## 🚀 Quick Start

### 1. Prerequisites Installation

#### 📦 Required Services
```bash
# MongoDB
https://www.mongodb.com/try/download/community
https://www.mongodb.com/try/download/shell
net start MongoDB

# Redis
docker run -d --name redis -p 6379:6379 -v redis_data:/data redis/redis-stack-server:latest

# PostgreSQL (optional)
# Run on localhost:5432
```

#### 🍃 MongoDB Setup
```bash
mongo
> use admin
db.createUser({
    user: "akh",
    pwd: "a13431343",
    roles: [{ role: "readWrite", db: "divar" }]
})
```

### 2. Environment Configuration

Create `.env` file in project root:

```env
# 🧪 Testing Configuration
SECURE_SSL_REDIRECT=False  # Disable for local development

# 🖥️ WebDriver Configuration (Linux)
DRIVER_PATH1=/mnt/c/chrome/linux/chromedriver-linux64-1/chromedriver
CHROME_PATH1=/mnt/c/chrome/linux/chrome-headless-shell-linux64-1/chrome-headless-shell

# 🪟 WebDriver Configuration (Windows)
DRIVER_PATH1_win=C:\chrome\chromedriver-win64-1\chromedriver.exe
CHROME_PATH1_win=C:\chrome\chrome-win64-1\chrome.exe

# 👤 Chrome Profile (optional)
CHROME_PROFILE_PATH=C:\\Users\\Admin\\AppData\\Local\\Google\\Chrome\\User Data
CHROME_PROFILE_FOLDER=Profile 7

# 🔑 Database Credentials
REDIS_PASS=
POSTGRES_DBNAME=divar
POSTGRES_USERNAME=postgres
POSTGRES_USERPASS=a13431343
MONGO_USER_NAME=akh
MONGO_USER_PASS=a13431343
MONGO_DBNAME=divar
MONGO_SOURCE=admin
MONGO_HOST=127.0.0.1

# 📁 File Paths
SCREENSHOT_IMAGE_PATH=media/file_{uid}/file_images
screenshot_map_path=media/file_{uid}/file_mapes
```

### 3. Core Configuration

Configure crawler settings in `divar_crl/settings.py`:

```python
# 🎯 Target Configuration (must be set together!)
APARTMENT_EJARE_ZAMIN = "https://divar.ir/s/tehran/buy-apartment"
CATEGORY = "apartment"  # Options: 'apartment', 'zamin_kolangy', 'vila'
IS_EJARE = False  # True for rental, False for sale

# 🧪 Testing
TEST_MANUAL_CARD_SELECTION = None  # or [(file_uid, file_url)] for specific testing
```

## 🎮 Running the Crawler

### Main Commands

```bash
# 🏃‍♂️ Start main crawler (multi-threaded)
python manage.py crawl

# 🔄 Update existing listings and mark expired
python manage.py update

# 🌐 Run Django development server
python manage.py runserver

# ⚡ Start FastAPI service (port 8001)
uvicorn fastapi_app.main:app --port 8001
```

### Test Endpoints

Access test features via Django views:
- `http://localhost:8000/api/` - REST API endpoints for testing

## ⚙️ Configuration Details

### 🎯 Target Settings
All three settings must be configured together:

| Setting | Description | Example Values |
|---------|-------------|----------------|
| `APARTMENT_EJARE_ZAMIN` | Target URL for crawling | Different URLs for each category/type |
| `CATEGORY` | Property type | `apartment`, `zamin_kolangy`, `vila` |
| `IS_EJARE` | Rental vs Sale | `True` (rental), `False` (sale) |

### 🚗 Multi-Driver Setup

Only configure **Driver 1** in `.env` - additional drivers are auto-generated:

```env
# ✅ Configure only Driver 1
DRIVER_PATH1=/path/to/chromedriver1
CHROME_PATH1=/path/to/chrome1

# ⚡ Auto-generated from template:
# DRIVER_PATH2, DRIVER_PATH3, DRIVER_PATH4...
# CHROME_PATH2, CHROME_PATH3, CHROME_PATH4...
```

**Example Auto-generation:**
```
Driver 1: /mnt/c/chrome/linux/chromedriver-linux64-1/chromedriver
Driver 2: /mnt/c/chrome/linux/chromedriver-linux64-2/chromedriver
Driver 3: /mnt/c/chrome/linux/chromedriver-linux64-3/chromedriver
```

### 🔍 Testing Specific Properties

For testing specific listings:
```python
# In settings.py
TEST_MANUAL_CARD_SELECTION = [
    ("abc123", "https://divar.ir/v/apartment-xyz"),
    ("def456", "https://divar.ir/v/villa-abc")
]
```

## 🏗️ Architecture Overview

### Core Components
- **Django App** (`main/`): Crawler logic, REST API, management commands
- **FastAPI Service** (`fastapi_app/`): File uploads, MongoDB operations
- **Multi-threading**: Configurable driver pool with Redis coordination
- **Property Classes**: `Apartment`, `Vila`, `ZaminKolangy` with specialized extraction

### 📊 Data Flow
1. **Crawl Command** → Multi-threaded property discovery
2. **Redis Queue** → Task coordination between drivers  
3. **MongoDB** → Primary data storage
4. **File System** → Images and map screenshots

## 🔧 Developer Notes

### 🛠️ Driver Verification
```bash
# Check driver version
/mnt/c/chrome/linux/chrome-headless-shell-linux64-1/chrome --version
```

### ⚠️ Important Notes
- **FastAPI Root**: Don't change FastAPI directory structure - Django media paths are calculated relative to FastAPI location
- **Error Handling**: Errors are logged but don't re-raise to prevent double exceptions
- **Thread Safety**: Use Redis for driver coordination in multi-threaded environment

### 📝 Logging
Centralized logging with separate files:
- `django.log`, `driver.log`, `redis.log`, `fastapi.log`, `cards.log`

## 🎯 Property Types Supported

| Type | Description | Special Features |
|------|-------------|------------------|
| 🏠 **Apartment** | Full residential units | Floor, elevator, parking details |
| 🏘️ **Vila** | Villa properties | Land area, different pricing structure |
| 🏞️ **ZaminKolangy** | Land/old houses | Simplified data model |

## 📋 Service Dependencies

- **MongoDB** (port 27017) - Required for data storage
- **Redis** (port 6379) - Required for task coordination  
- **FastAPI** (port 8001) - Required for file operations
- **PostgreSQL** (port 5432) - Optional additional database