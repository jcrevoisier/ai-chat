from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum

class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: str = Field(..., pattern=r'^[\w\.-]+@[\w\.-]+\.\w+$')  # Changed from regex to pattern
    password: str = Field(..., min_length=8)

class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    created_at: datetime
    
    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class TokenData(BaseModel):
    username: Optional[str] = None

class ChatRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"

class ChatMessage(BaseModel):
    role: ChatRole
    content: str
    timestamp: Optional[datetime] = None

class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=1000)
    model: str = Field(default="gpt-3.5-turbo")
    max_tokens: Optional[int] = Field(default=150, le=1000)
    temperature: Optional[float] = Field(default=0.7, ge=0.0, le=2.0)

class ChatResponse(BaseModel):
    id: str
    message: str
    model: str
    usage: dict
    created_at: datetime

class ConversationResponse(BaseModel):
    id: int
    messages: List[ChatMessage]
    created_at: datetime
    updated_at: datetime

class TaskStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class BackgroundTaskResponse(BaseModel):
    task_id: str
    status: TaskStatus
    result: Optional[dict] = None
    error: Optional[str] = None
