import asyncio
from httpx import AsyncClient

# use fastapi create_files to create a test record in mongodb
payload = [
    {
        "file_uid": "test123",
        "title": "My Test File",
        "url": "http://example.com/resource",
        "image_srcs": []
    }
]

async def main():
    async with AsyncClient(base_url="http://127.0.0.1:8001") as client:

        response = await client.post("/files_create", json=payload)
        print("Status:", response.status_code)
        try:
            print("Response JSON:", response.json())
        except Exception:
            print("Response text:", response.text)

if __name__ == "__main__":
    asyncio.run(main())
