from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr
from typing import Optional, List

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
        
class UserLeaderboard(BaseModel):
    first_name: str
    last_name: str
    total_points: int

    class Config:
        from_attributes = True

class AllUsersResponse(BaseModel):
    users: List[UserLeaderboard]

class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    password: Optional[str] = None

# class BoardCreate(BaseModel):
#     name: str
#     description: Optional[str] = None
#
# class BoardUpdate(BaseModel):
#     name: Optional[str] = None
#     description: Optional[str] = None
#
# class BoardResponse(BaseModel):
#     id: UUID
#     user_id: UUID
#     name: str
#     description: Optional[str]
#     created_at: datetime
#     updated_at: datetime
#
#     class Config:
#         from_attributes = True

class TaskStatusCreate(BaseModel):
    code: str
    name: str

class TaskStatusUpdate(BaseModel):
    code: Optional[str] = None
    name: Optional[str] = None

class TaskStatusResponse(BaseModel):
    id: UUID
    code: str
    name: str

    class Config:
        from_attributes = True

# class CategoryCreate(BaseModel):
#     name: str
#     color: Optional[str] = None
#
# class CategoryUpdate(BaseModel):
#     name: Optional[str] = None
#     color: Optional[str] = None
#
# class CategoryResponse(BaseModel):
#     id: UUID
#     user_id: UUID
#     name: str
#     color: Optional[str]
#
#     class Config:
#         from_attributes = True

class TagCreate(BaseModel):
    name: str

class TagUpdate(BaseModel):
    name: Optional[str] = None

class TagResponse(BaseModel):
    id: UUID
    name: str

    class Config:
        from_attributes = True

class TaskTagCreate(BaseModel):
    task_id: UUID
    tag_id: UUID

class TaskCreate(BaseModel):
    #board_id: UUID
    status_id: UUID
    #category_id: UUID
    title: str
    description: Optional[str] = None
    ai_analysis_metadata: Optional[dict] = None
    estimated_points: Optional[int] = 0
    due_date: Optional[datetime] = None

class TaskUpdate(BaseModel):
    #board_id: Optional[UUID] = None
    status_id: Optional[UUID] = None
    #category_id: Optional[UUID] = None
    title: Optional[str] = None
    description: Optional[str] = None
    ai_analysis_metadata: Optional[dict] = None
    estimated_points: Optional[int] = None
    due_date: Optional[datetime] = None
    completed_at: Optional[datetime] = None

class TaskResponse(BaseModel):
    id: UUID
    user_id: UUID
    #board_id: UUID
    status_id: UUID
    #category_id: UUID
    title: str
    description: Optional[str]
    ai_analysis_metadata: Optional[dict]
    estimated_points: int
    awarded_points: int
    due_date: Optional[datetime]
    completed_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class RewardTypeCreate(BaseModel):
    code: str
    name: str
    description: Optional[str] = None

class RewardTypeUpdate(BaseModel):
    code: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None

class RewardTypeResponse(BaseModel):
    id: UUID
    code: str
    name: str
    description: Optional[str]

    class Config:
        from_attributes = True

class RewardCreate(BaseModel):
    type_id: UUID
    points_amount: int
    reason: Optional[str] = None

class RewardUpdate(BaseModel):
    type_id: Optional[UUID] = None
    points_amount: Optional[int] = None
    reason: Optional[str] = None

class RewardResponse(BaseModel):
    id: UUID
    user_id: UUID
    type_id: UUID
    points_amount: int
    awarded_at: datetime
    reason: Optional[str]

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str
    user: Optional[dict] = None

class TokenData(BaseModel):
    user_id: Optional[str] = None
    role: Optional[str] = None

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class TaskTitleAndDate(BaseModel):
    title: str
    due_date: Optional[datetime] = None

    class Config:
        from_attributes = True
