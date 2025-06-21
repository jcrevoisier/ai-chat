import time
from celery import Celery
from typing import Dict, Any
import asyncio
import os
from dotenv import load_dotenv
from fastapi import BackgroundTasks

from .services import openai_service
from .models import ChatRequest

load_dotenv()

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
    """
    try:
        self.update_state(state="PROCESSING", meta={"progress": 0})
        
        time.sleep(2)
        
        self.update_state(state="PROCESSING", meta={"progress": 50})

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

async def simple_background_task(
    user_id: int, 
    chat_data: Dict[str, Any],
    db_session_factory
):
    """
    Simple background task using FastAPI BackgroundTasks
    """
    try:
        await asyncio.sleep(1)
        
        print(f"Background task completed for user {user_id}")
            
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
        None
    )

