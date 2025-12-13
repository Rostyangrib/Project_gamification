from datetime import datetime
from pydantic import BaseModel, EmailStr
from typing import Optional, List

class UserCreate(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: int
    first_name: str
    last_name: str
    email: str
    total_points: int
    role: Optional[str] = None
    cur_comp: Optional[int] = None

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

class UserCompetitionAssign(BaseModel):
    competition_id: Optional[int] = None

class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    password: Optional[str] = None

class TaskStatusCreate(BaseModel):
    code: str
    name: str

class TaskStatusUpdate(BaseModel):
    code: Optional[str] = None
    name: Optional[str] = None

class TaskStatusResponse(BaseModel):
    id: int
    code: str
    name: str

    class Config:
        from_attributes = True

class TagCreate(BaseModel):
    name: str

class TagUpdate(BaseModel):
    name: Optional[str] = None

class TagResponse(BaseModel):
    id: int
    name: str

    class Config:
        from_attributes = True

class TaskTagCreate(BaseModel):
    task_id: int
    tag_id: int

class TaskCreate(BaseModel):
    status_id: int
    title: str
    description: Optional[str] = None
    ai_analysis_metadata: Optional[dict] = None
    estimated_points: Optional[int] = 0
    due_date: Optional[datetime] = None

class TaskUpdate(BaseModel):
    status_id: Optional[int] = None
    title: Optional[str] = None
    description: Optional[str] = None
    ai_analysis_metadata: Optional[dict] = None
    estimated_points: Optional[int] = None
    due_date: Optional[datetime] = None
    completed_at: Optional[datetime] = None

class TaskResponse(BaseModel):
    id: int
    user_id: int
    status_id: int
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
    id: int
    code: str
    name: str
    description: Optional[str]

    class Config:
        from_attributes = True

class RewardCreate(BaseModel):
    type_id: int
    points_amount: int
    reason: Optional[str] = None

class RewardUpdate(BaseModel):
    type_id: Optional[int] = None
    points_amount: Optional[int] = None
    reason: Optional[str] = None

class RewardResponse(BaseModel):
    id: int
    user_id: int
    type_id: int
    points_amount: int
    awarded_at: datetime
    reason: Optional[str]

    class Config:
        from_attributes = True

class CompetitionCreate(BaseModel):
    title: str
    start_date: datetime
    end_date: datetime

class CompetitionUpdate(BaseModel):
    title: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None

class CompetitionResponse(BaseModel):
    id: int
    title: str
    start_date: datetime
    end_date: datetime
    created_at: datetime
    updated_at: datetime

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

class CompetitionDatesResponse(BaseModel):
    start_date: datetime
    end_date: datetime