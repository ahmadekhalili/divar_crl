# 🚀 FastAPI Docker Setup

## ⚡ Quick Start

### 📋 Prerequisites
Start Redis and MongoDB containers on your host machine:
```bash
docker start redis mongo  # you should add mongo and redis ipin .env (REDIS_HOST and MONGO_HOST)
```

### 🔨 Build & Run
```bash
# Build and run in detached mode
docker compose up --build -d

# Stop the service
docker compose down
```

### ✅ Verification
Test FastAPI by requesting: `http://192.168.1.103:8001/test`

Expected response:
```json
{"status":"up","version":"0.1.0"}
```

---

## ⚙️ Configuration

| Component | Requirement |
|-----------|-------------|
| **Redis & MongoDB** | Must be running on host before starting FastAPI container |
| **Environment** | Edit `.env` in project root - changes are automatically synced to container |

---

## 📝 Notes

- ✨ Container automatically uses the latest `.env` configuration from project root
- 📁 Logs are shared between host and container via volume mounting  
- 🔧 Redis and MongoDB should be manually started on host machine before running FastAPI
