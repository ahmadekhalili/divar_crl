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


# setup:
.env structure:
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
screenshot_image_path=media/file_{uid}/file_images
screenshot_map_path=media/file_{uid}/file_mapes
```

docker run -d --name redis -p 6379:6379 redis:6.2  # install redis insite

- run mongo
- run postgres
- run fastapi (8001)
- fill .env
