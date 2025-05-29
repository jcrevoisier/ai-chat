# AI Chat API

A comprehensive FastAPI application demonstrating modern Python web development practices.

## Features

- ✅ **FastAPI + Pydantic**: RESTful API with automatic validation
- ✅ **JWT Authentication**: Secure user authentication
- ✅ **OpenAI Integration**: Chat completions with GPT models
- ✅ **HuggingFace Integration**: Alternative AI service
- ✅ **Async Programming**: Full async/await support
- ✅ **Background Tasks**: Both Celery and FastAPI BackgroundTasks
- ✅ **Docker**: Containerized application
- ✅ **Database**: SQLAlchemy with async support
- ✅ **Rate Limiting**: Basic rate limiting implementation

## Quick Start

1. **Clone and setup**:
```bash
git clone <repo>
cd ai-chat-api
cp .env.example .env
```

2. **Update environment variables**:
```bash
# Edit .env file with your actual values
OPENAI_API_KEY=your-openai-api-key
SECRET_KEY=your-super-secret-key
```

3. **Run with Docker**:
```bash
docker-compose up --build
```

4. **Or run locally**:
```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## API Usage Examples

### 1. Register a User
```bash
curl -X POST "http://localhost:8000/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "email": "test@example.com",
    "password": "password123"
  }'
```

### 2. Login and Get Token
```bash
curl -X POST "http://localhost:8000/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "password": "password123"
  }'
```

### 3. Chat with OpenAI
```bash
curl -X POST "http://localhost:8000/chat" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Hello, how are you?",
    "model": "gpt-3.5-turbo",
    "max_tokens": 150,
    "temperature": 0.7
  }'
```

### 4. Background Task (Celery)
```bash
curl -X POST "http://localhost:8000/chat/background" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Process this in background",
    "model": "gpt-3.5-turbo"
  }'
```

### 5. Check Task Status
```bash
curl -X GET "http://localhost:8000/chat/tasks/TASK_ID" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### 6. Get Conversation History
```bash
curl -X GET "http://localhost:8000/conversations" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

## Testing the Application

### Manual Testing Script
```python
import httpx
import asyncio
import json

async def test_api():
    base_url = "http://localhost:8000"
    
    async with httpx.AsyncClient() as client:
        # 1. Register user
        register_response = await client.post(
            f"{base_url}/auth/register",
            json={
                "username": "testuser",
                "email": "test@example.com", 
                "password": "password123"
            }
        )
        print("Register:", register_response.status_code)
        
        # 2. Login
        login_response = await client.post(
            f"{base_url}/auth/login",
            json={
                "username": "testuser",
                "password": "password123"
            }
        )
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        print("Login:", login_response.status_code)
        
        # 3. Chat
        chat_response = await client.post(
            f"{base_url}/chat",
            headers=headers,
            json={
                "message": "Hello, AI!",
                "model": "gpt-3.5-turbo"
            }
        )
        print("Chat:", chat_response.status_code)
        print("Response:", chat_response.json())

# Run the test
asyncio.run(test_api())
```

## Architecture Overview

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   FastAPI App   │    │   Celery Worker │    │   Redis Broker  │
│                 │    │                 │    │                 │
│ • JWT Auth      │◄──►│ • Background    │◄──►│ • Task Queue    │
│ • Chat API      │    │   Tasks         │    │ • Results       │
│ • Rate Limiting │    │ • OpenAI Calls  │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   SQLite DB     │    │   OpenAI API    │    │  HuggingFace    │
│                 │    │                 │    │      API        │
│ • Users         │    │ • Chat Models   │    │ • Alt Models    │
│ • Conversations │    │ • Completions   │    │ • Inference     │
│ • Tasks         │    │                 │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## Key Learning Points

### 1. FastAPI + Pydantic
- **Request/Response Models**: Automatic validation and serialization
- **Dependency Injection**: Clean separation of concerns
- **Async Endpoints**: Non-blocking request handling

### 2. JWT Authentication
- **Token Structure**: `header.payload.signature`
- **Validation Flow**: Extract → Decode → Verify → Get User
- **Security**: Password hashing, token expiration

### 3. Async Programming
```python
# Async database operations
async def get_user(db: AsyncSession, user_id: int):
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()

# Async HTTP calls
async with httpx.AsyncClient() as client:
    response = await client.post(url, json=data)
```

### 4. Background Tasks
- **Celery**: Distributed task queue for heavy operations
- **FastAPI BackgroundTasks**: Simple in-process tasks
- **Use Cases**: Long-running AI processing, email sending, data processing

### 5. Docker Best Practices
- **Multi-stage builds**: Optimize image size
- **Non-root user**: Security best practice
- **Health checks**: Container monitoring
- **Environment variables**: Configuration management

### 6. Error Handling
```python
try:
    result = await openai_service.create_completion(...)
except openai.RateLimitError:
    raise HTTPException(status_code=429, detail="Rate limit exceeded")
except Exception as e:
    raise HTTPException(status_code=500, detail=str(e))
```

## Monitoring

- **Application**: http://localhost:8000/docs (Swagger UI)
- **Celery Tasks**: http://localhost:5555 (Flower)
- **Health Check**: http://localhost:8000/health

## Production Considerations

1. **Security**:
   - Use strong SECRET_KEY
   - Implement proper CORS
   - Add request validation
   - Use HTTPS

2. **Database**:
   - Switch to PostgreSQL
   - Add connection pooling
   - Implement migrations

3. **Monitoring**:
   - Add logging
   - Implement metrics
   - Set up alerts

4. **Scaling**:
   - Load balancer
   - Multiple workers
   - Database replicas
```

## 12. Simple Test File

```python:tests/test_main.py
import pytest
import asyncio
from httpx import AsyncClient
from fastapi.testclient import TestClient

from app.main import app

# Sync test client for simple tests
client = TestClient(app)

def test_health_check():
    """Test the health check endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

def test_register_user():
    """Test user registration"""
    response = client.post(
        "/auth/register",
        json={
            "username": "testuser",
            "email": "test@example.com",
            "password": "password123"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "testuser"
    assert data["email"] == "test@example.com"

@pytest.mark.asyncio
async def test_full_flow():
    """Test complete authentication and chat flow"""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        # Register
        register_response = await ac.post(
            "/auth/register",
            json={
                "username": "flowtest",
                "email": "flow@example.com",
                "password": "password123"
            }
        )
        assert register_response.status_code == 200
        
        # Login
        login_response = await ac.post(
            "/auth/login",
            json={
                "username": "flowtest",
                "password": "password123"
            }
        )
        assert login_response.status_code == 200
        token = login_response.json()["access_token"]
        
        # Test protected endpoint
        headers = {"Authorization": f"Bearer {token}"}
        conversations_response = await ac.get(
            "/conversations",
            headers=headers
        )
        assert conversations_response.status_code == 200
```

## Final Setup Commands

```bash
# Create the project
mkdir ai-chat-api && cd ai-chat-api

# Set up environment
cp .env.example .env
# Edit .env with your OpenAI API key

# Run with Docker
docker-compose up --build

# Or run locally
pip install -r requirements.txt
uvicorn app.main:app --reload