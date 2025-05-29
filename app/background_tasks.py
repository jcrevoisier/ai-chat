from celery import Celery
from typing import Dict, Any
import asyncio
import os
from dotenv import load_dotenv

from .services import openai_service
from .models import ChatRequest

load_dotenv()

# Celery configuration
celery_app = Celery(
    "chat_tasks",
    broker=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
    backend=os.getenv("REDIS_URL", "redis://localhost:6379/0")
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    result_expires=3600,
)

@celery_app.task(bind=True)
def process_long_chat_task(self, chat_data: Dict[str, Any], user_id: int):
    """
    Background task for processing long-running chat requests
    This demonstrates Celery integration with async code
    """
    try:
        # Update task status
        self.update_state(state="PROCESSING", meta={"progress": 0})
        
        # Simulate some processing steps
        import time
        time.sleep(2)  # Simulate processing time
        
        self.update_state(state="PROCESSING", meta={"progress": 50})
        
        # Process with OpenAI (we need to run async code in sync context)
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            messages = [{"role": "user", "content": chat_data["message"]}]
            result = loop.run_until_complete(
                openai_service.create_chat_completion(
                    messages=messages,
                    model=chat_data.get("model", "gpt-3.5-turbo"),
                    max_tokens=chat_data.get("max_tokens", 150),
                    temperature=chat_data.get("temperature", 0.7)
                )
            )
            
            self.update_state(state="PROCESSING", meta={"progress": 90})
            
            return {
                "status": "completed",
                "result": result.model_dump(),
                "user_id": user_id
            }
        finally:
            loop.close()
            
    except Exception as e:
        self.update_state(
            state="FAILURE",
            meta={"error": str(e)}
        )
        raise

# FastAPI Background Tasks (alternative to Celery for simpler tasks)
from fastapi import BackgroundTasks

async def simple_background_task(
    user_id: int, 
    chat_data: Dict[str, Any],
    db_session_factory
):
    """
    Simple background task using FastAPI's BackgroundTasks
    Good for lightweight operations that don't need persistence
    """
    try:
        # Simulate some background processing
        await asyncio.sleep(1)
        
        # Log the completion (in real app, you might update database)
        print(f"Background task completed for user {user_id}")
        
        # You could update database here if needed
        # async with db_session_factory() as db:
        #     # Update task status in database
        #     pass
            
    except Exception as e:
        print(f"Background task failed for user {user_id}: {str(e)}")

def add_simple_background_task(
    background_tasks: BackgroundTasks,
    user_id: int,
    chat_data: Dict[str, Any]
):
    """Helper function to add simple background tasks"""
    background_tasks.add_task(
        simple_background_task,
        user_id,
        chat_data,
        None  # db_session_factory if needed
    )

