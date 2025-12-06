from uuid import UUID

from pydantic import BaseModel, EmailStr
from typing import Optional

class UserCreate(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: UUID
    first_name: str
    last_name: str
    email: str
    total_points: int

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    user_id: Optional[str] = None
    role: Optional[str] = None  # например: "user" или "admin"

class UserLogin(BaseModel):
    email: EmailStr
    password: str