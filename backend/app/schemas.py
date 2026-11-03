from pydantic import BaseModel, EmailStr, Field
from typing import Any, Literal

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=10, max_length=128)

class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = 'bearer'
    user: dict

class ChatRequest(BaseModel):
    question: str = Field(min_length=2, max_length=4000)
    document_ids: list[int] = Field(default_factory=list)

class GenerateRequest(BaseModel):
    document_ids: list[int] = Field(default_factory=list)
    count: int = Field(default=5, ge=1, le=20)
    difficulty: Literal['easy', 'medium', 'hard', 'mixed'] = 'mixed'
    topic: str | None = None

class QuizResultRequest(BaseModel):
    score: int = Field(ge=0)
    total: int = Field(ge=1)
    details: dict[str, Any] = Field(default_factory=dict)

class ChatResponse(BaseModel):
    answer: str
    citations: list[dict]
    mode: str