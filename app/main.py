from fastapi import FastAPI, Depends, HTTPException, status, BackgroundTasks
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, insert
from datetime import timedelta, datetime
from typing import List
import uvicorn
import os
from dotenv import load_dotenv

from .database import get_database, create_tables, User, Conversation, ChatTask
from .models import (
    UserCreate, UserResponse, Token, ChatRequest, ChatResponse,
    ConversationResponse, BackgroundTaskResponse, TaskStatus
)
from .auth import (
    authenticate_user, create_access_token, get_current_user,
    get_password_hash, ACCESS_TOKEN_EXPIRE_MINUTES
)
from .services import openai_service, huggingface_service
from .background_tasks import (
    celery_app, process_long_chat_task, add_simple_background_task
)

load_dotenv()

app = FastAPI(
    title="AI Chat API",
    description="FastAPI application with JWT auth, OpenAI integration, and background tasks",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    """Initialize database tables on startup"""
    await create_tables()

# Authentication endpoints
@app.post("/auth/register", response_model=UserResponse)
async def register(user: UserCreate, db: AsyncSession = Depends(get_database)):
    """
    Register a new user
    Demonstrates: Pydantic validation, password hashing, database operations
    """
    # Check if user already exists
    existing_user = await db.execute(
        select(User).where(
            (User.username == user.username) | (User.email == user.email)
        )
    )
    if existing_user.scalar_one_or_none():
        raise HTTPException(
            status_code=400,
            detail="Username or email already registered"
        )
    
    # Create new user
    hashed_password = get_password_hash(user.password)
    db_user = User(
        username=user.username,
        email=user.email,
        hashed_password=hashed_password
    )
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    
    return UserResponse.model_validate(db_user)

@app.post("/auth/login", response_model=Token)
async def login(
    username: str,
    password: str,
    db: AsyncSession = Depends(get_database)
):
    """
    Login and get JWT token
    Demonstrates: JWT creation, authentication flow
    """
    user = await authenticate_user(db, username, password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return Token(access_token=access_token)

# Chat endpoints
@app.post("/chat", response_model=ChatResponse)
async def chat_completion(
    request: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_database)
):
    """
    Create a chat completion using OpenAI
    Demonstrates: OpenAI integration, async operations, error handling
    """
    messages = [{"role": "user", "content": request.message}]
    
    try:
        response = await openai_service.create_chat_completion(
            messages=messages,
            model=request.model,
            max_tokens=request.max_tokens,
            temperature=request.temperature
        )
        
        # Save conversation to database
        conversation_data = {
            "user_id": current_user.id,
            "messages": [
                {"role": "user", "content": request.message, "timestamp": datetime.utcnow().isoformat()},
                {"role": "assistant", "content": response.message, "timestamp": datetime.utcnow().isoformat()}
            ]
        }
        
        conversation = Conversation(**conversation_data)
        db.add(conversation)
        await db.commit()
        
        return response
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/chat/background", response_model=BackgroundTaskResponse)
async def chat_background_celery(
    request: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_database)
):
    """
    Process chat request in background using Celery
    Demonstrates: Celery background tasks, task tracking
    """
    # Create task in database
    task = process_long_chat_task.delay(
        request.model_dump(),
        current_user.id
    )
    
    # Store task info in database
    chat_task = ChatTask(
        id=task.id,
        user_id=current_user.id,
        status="pending",
        request_data=request.model_dump()
    )
    db.add(chat_task)
    await db.commit()
    
    return BackgroundTaskResponse(
        task_id=task.id,
        status=TaskStatus.PENDING
    )

@app.post("/chat/background-simple")
async def chat_background_simple(
    request: ChatRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user)
):
    """
    Process chat request using FastAPI BackgroundTasks
    Demonstrates: FastAPI background tasks (simpler alternative to Celery)
    """
    add_simple_background_task(
        background_tasks,
        current_user.id,
        request.model_dump()
    )
    
    return {"message": "Task added to background queue"}

@app.get("/chat/tasks/{task_id}", response_model=BackgroundTaskResponse)
async def get_task_status(
    task_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_database)
):
    """
    Get background task status
    Demonstrates: Task status tracking, Celery result backend
    """
    # Get task from Celery
    task = celery_app.AsyncResult(task_id)
    
    # Get task from database
    db_task = await db.execute(
        select(ChatTask).where(
            (ChatTask.id == task_id) & (ChatTask.user_id == current_user.id)
        )
    )
    db_task = db_task.scalar_one_or_none()
    
    if not db_task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # Map Celery states to our TaskStatus enum
    status_mapping = {
        "PENDING": TaskStatus.PENDING,
        "PROCESSING": TaskStatus.PROCESSING,
        "SUCCESS": TaskStatus.COMPLETED,
        "FAILURE": TaskStatus.FAILED
    }
    
    return BackgroundTaskResponse(
        task_id=task_id,
        status=status_mapping.get(task.state, TaskStatus.PENDING),
        result=task.result if task.successful() else None,
        error=str(task.info) if task.failed() else None
    )

@app.get("/conversations", response_model=List[ConversationResponse])
async def get_conversations(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_database)
):
    """
    Get user's conversation history
    Demonstrates: Database queries, relationships, JSON handling
    """
    result = await db.execute(
        select(Conversation).where(Conversation.user_id == current_user.id)
    )
    conversations = result.scalars().all()
    
    return [
        ConversationResponse(
            id=conv.id,
            messages=conv.messages,
            created_at=conv.created_at,
            updated_at=conv.updated_at
        )
        for conv in conversations
    ]

@app.get("/chat/huggingface")
async def chat_huggingface(
    prompt: str,
    model: str = "microsoft/DialoGPT-medium",
    current_user: User = Depends(get_current_user)
):
    """
    Alternative AI service using HuggingFace
    Demonstrates: Multiple AI service integrations, httpx usage
    """
    try:
        result = await huggingface_service.generate_text(prompt, model)
        return {"result": result, "service": "huggingface"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Health check endpoint
@app.get("/health")
async def health_check():
    """Simple health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0"
    }

# Rate limiting example (basic implementation)
from collections import defaultdict
import time

request_counts = defaultdict(list)

@app.middleware("http")
async def rate_limit_middleware(request, call_next):
    """
    Basic rate limiting middleware
    Demonstrates: Middleware, rate limiting concepts
    """
    client_ip = request.client.host
    current_time = time.time()
    
    # Clean old requests (older than 1 minute)
    request_counts[client_ip] = [
        req_time for req_time in request_counts[client_ip]
        if current_time - req_time < 60
    ]
    
    # Check rate limit (100 requests per minute)
    if len(request_counts[client_ip]) >= 100:
        return HTTPException(status_code=429, detail="Rate limit exceeded")
    
    # Add current request
    request_counts[client_ip].append(current_time)
    
    response = await call_next(request)
    return response

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
