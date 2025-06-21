import httpx
import openai
from typing import List, Dict, Any
import os
from dotenv import load_dotenv
import asyncio
from datetime import datetime

from .models import ChatMessage, ChatRequest, ChatResponse

load_dotenv()

openai.api_key = os.getenv("OPENAI_API_KEY")

class OpenAIService:
    def __init__(self):
        self.client = openai.AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.rate_limit = int(os.getenv("API_RATE_LIMIT", "100"))
    
    async def create_chat_completion(
        self, 
        messages: List[Dict[str, str]], 
        model: str = "gpt-3.5-turbo",
        max_tokens: int = 150,
        temperature: float = 0.7
    ) -> ChatResponse:
        """
        Create a chat completion using OpenAI API
        """
        try:
            response = await self.client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature
            )
            
            return ChatResponse(
                id=response.id,
                message=response.choices[0].message.content,
                model=response.model,
                usage=response.usage.model_dump(),
                created_at=datetime.utcnow()
            )
        
        except openai.RateLimitError as e:
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded. Please try again later."
            )
        except openai.APIError as e:
            raise HTTPException(
                status_code=500,
                detail=f"OpenAI API error: {str(e)}"
            )
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Unexpected error: {str(e)}"
            )

class HuggingFaceService:
    def __init__(self):
        self.api_url = "https://api-inference.huggingface.co/models"
        self.headers = {
            "Authorization": f"Bearer {os.getenv('HUGGINGFACE_API_KEY', '')}"
        }
    
    async def generate_text(
        self, 
        prompt: str, 
        model: str = "microsoft/DialoGPT-medium"
    ) -> Dict[str, Any]:
        url = f"{self.api_url}/{model}"
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    url,
                    headers=self.headers,
                    json={"inputs": prompt},
                    timeout=30.0
                )
                response.raise_for_status()
                return response.json()
            
            except httpx.TimeoutException:
                raise HTTPException(
                    status_code=408,
                    detail="Request timeout"
                )
            except httpx.HTTPStatusError as e:
                raise HTTPException(
                    status_code=e.response.status_code,
                    detail=f"HuggingFace API error: {e.response.text}"
                )

openai_service = OpenAIService()
huggingface_service = HuggingFaceService()
