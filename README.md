## installation:
https://www.mongodb.com/try/download/community
https://www.mongodb.com/try/download/shell
net start MongoDB


mongo
> use admin
db.createUser({
    user:   "akh",
    pwd:    "a13431343",
    roles: [ { role: "readWrite", db: "divar" } ]
  })

docker run -d --name redis -p 6379:6379 redis:6.2  # install redis insite

- run postgres (localhost, 5432)
- run mongo (localhost, default port)
- run redis (localhost, 6379), `docker run -d --name redis -p 6379:6379 -v redis_data:/data redis:6.2 redis-server --bind 0.0.0.0 --port 6379 --protected-mode no`
- run fastapi (8001).

## setup:
### .env:
```
TEST_RESERVATION=True  # if be True, last submit button will not be pressed (used for test environments)
SECURE_SSL_REDIRECT=False  # False in test environments without ssl domain
#DRIVER_PATH=C:\\Users\\Admin\\.wdm\\drivers\\chromedriver\\win64\\135.0.7049.97\\chromedriver-win32\\chromedriver.exe
#CHROME_PATH=C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe
DRIVER_PATH1=C:\chrome\chromedriver1-win64\chromedriver.exe
CHROME_PATH1=C:\chrome\chrome1-win64\chrome.exe
DRIVER_PATH2=C:\chrome\chromedriver2-win64\chromedriver.exe
CHROME_PATH2=C:\chrome\chrome2-win64\chrome.exe
DRIVER_PATH3=C:\chrome\chromedriver3-win64\chromedriver.exe
CHROME_PATH3=C:\chrome\chrome3-win64\chrome.exe
CHROME_PROFILE_PATH=C:\\Users\\skh\\AppData\\Local\\Google\\Chrome for Testing\\User Data
CHROME_PROFILE_FOLDER=Profile 3
#CHROME_PROFILE_PATH=C:\\Users\\Admin\\AppData\\Local\\Google\\Chrome\\User Data
#CHROME_PROFILE_FOLDER=Profile 7
EXTENSION_PATH=C:\\10\\xa\\nobat\\scripts\\extension_minimize
WINDOWS_CRAWL=True  # Set to False on Linux
REDIS_PASS=
POSTGRES_DBNAME=divar
POSTGRES_USERNAME=postgres
POSTGRES_USERPASS=a13431343
POSTGRES_DBNAME_CHANEL=
POSTGRES_USERNAME_CHANEL=
POSTGRES_USERPASS_CHANEL=
MONGO_USER_NAME=akh
MONGO_USER_PASS=a13431343
MONGO_DBNAME=divar
MONGO_SOURCE=admin
MONGO_HOST=127.0.0.1
SCREENSHOT_IMAGE_PATH=media/file_{uid}/file_images
screenshot_map_path=media/file_{uid}/file_mapes
```


### settings.py
APARTMENT_EJARE_ZAMIN = "https//:..."
CATEGORY = "apartment"  # can be 'apartment', 'zamin_kolangy', 'vila'
IS_EJARE = True
TEST_MANUAL_CARD_SELECTION = None

**`APARTMENT_EJARE_ZAMIN:`**
apartment and ejare and zamin saves in different dbs. you have to specify url, to crawl each of them by specify settings.APARTMENT_EJARE_ZAMIN.  
Note: each of categories ejera has difference url. so for switch to ejare each of them should specify its url. so apartment ejare, vali ejera,.. has differrent url.  
it is also possible to set files only contain images or only videos or no images ... here.

**`CATEGORY:`**
set CATEGORY based on APARTMENT_EJARE_ZAMIN selection.

**`IS_EJARE:`**
can be True, False  
if True, get ejare houses (vadie, ejare atts added in same table). also APARTMENT_EJARE_ZAMIN should change based on it.

**all these 3 settings confs should change with each other!**  

**`TEST_MANUAL_CARD_SELECTION:`**
to test specefic file crawling in divar, set settings.TEST_MANUAL_CARD_SELECTION, or `None` in production and pass to crawl_files. structure: `[(file_uid, file_url)]`



## developer section section
notes:
- dont change fastapi roots. to upload file images in fastapi, django media dir calculate from one back of fastapi dir .


### why not reraise
why not **reraise** for upstream?
```
def open_map(self):
    try:
        ...
    except Exception as e:
        logger_file.error(f"failed opening the map of the file. error: {e}")
        self.file.file_errors.append(f"failed opening the map of the file.")
        raise      # reraise for upstream (should stop map crawling)


try:
    map_opended = run_modules.open_map()
    canvas = driver.find_element(By.CSS_SELECTOR, "canvas.mapboxgl-canvas")
            logger_file.info(f"bool map's canvas: {bool(canvas)}")
    ...
except Exception as e:    
    message = f"Exception in map section. error: {e}"
    logger_file.error(message)
    self.file_errors.append(f"Some Fails in map section.")
```
unexpected happend here, we dont want raise two time for just open_map
