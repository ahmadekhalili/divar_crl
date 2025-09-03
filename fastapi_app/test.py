import asyncio
from redis.asyncio import Redis as aRedis
import json
from httpx import AsyncClient

# use fastapi create_files to create a test record in mongodb
payload = {
        "uid": "test345",
        "title": "My Test File",
        "url": "http://example.com/resource",
        "image_srcs": ["https://postimage01.divarcdn.com/static/photo/neda/post/YtJgq8a9xMZL_wNFMrCjpA/c4974c36-e05c-4473-acf5-ba6aafea68fd.jpg"],
        "file_errors": [],
        "category": "zamin_kolangy",
        "sell_ejare": "sell"
}


async def main():
    async with AsyncClient(base_url="http://127.0.0.1:8001") as client:
        response = await client.post("/files_create", json=payload)
        print("Status:", response.status_code)
        try:
            print("Response JSON:", response.json())
        except Exception:
            print("Response text:", response.text)


async def write_to_redis():
    r = aRedis()
    await r.xadd('data_stream', {'data': json.dumps(payload)})


if __name__ == "__main__":
    asyncio.run(write_to_redis())

