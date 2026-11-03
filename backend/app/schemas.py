from pydantic import BaseModel, Field
from typing import Optional

class ChatRequest(BaseModel):
    question: str = Field(min_length=2, max_length=4000)
    document_ids: list[int] = []

class GenerateRequest(BaseModel):
    document_ids: list[int] = []
    count: int = Field(default=5, ge=1, le=20)
    difficulty: str = "mixed"
    topic: Optional[str] = None

class ChatResponse(BaseModel):
    answer: str
    citations: list[dict]
    mode: str
