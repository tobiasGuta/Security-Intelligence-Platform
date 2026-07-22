from uuid import UUID
from datetime import datetime
from pydantic import BaseModel
from typing import Optional


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    csrf_token: str


class CSRFResponse(BaseModel):
    csrf_token: str


class UserResponse(BaseModel):
    id: UUID
    username: str
    email: str
    is_active: bool
    is_superuser: bool
    created_at: datetime
    updated_at: Optional[datetime] = None


class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None
