from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime

from schemas import TaskTitleAndDate
from config.db import get_db
from database import User, TaskStatus, Tag, Task, RewardType, Reward
from schemas import (
    UserResponse, TaskStatusResponse,
    TagResponse, TaskResponse, RewardTypeResponse, RewardResponse,
    AllUsersResponse
)
from dependencies import get_current_user, require_admin

router = APIRouter()

@router.get("/tasks/latest", response_model=list[TaskTitleAndDate])
def get_tasks(
        current_user: dict = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    tasks = db.query(Task.title, Task.due_date).filter(
        Task.user_id == current_user["user"].id
    ).all()

    return [{"title": task.title, "due_date": task.due_date} for task in tasks]


@router.get("/users/me", response_model=UserResponse)
def read_own_info(current_user: dict = Depends(get_current_user)):
    return current_user["user"]

# @router.get("/", summary="Root endpoint")
# async def root():
#     return {
#         "message": "Gamification API запущен!",
#         "time": datetime.now().isoformat()
#     }

# @router.get("/boards", response_model=List[BoardResponse])
# def get_boards(current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
#     return db.query(Board).filter(Board.user_id == current_user["user"].id).all()

@router.get("/task-statuses", response_model=List[TaskStatusResponse])
def get_task_statuses(db: Session = Depends(get_db)):
    return db.query(TaskStatus).all()

# @router.get("/categories", response_model=List[CategoryResponse])
# def get_categories(current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
#     return db.query(Category).filter(Category.user_id == current_user["user"].id).all()

@router.get("/tags", response_model=List[TagResponse])
def get_tags(db: Session = Depends(get_db)):
    return db.query(Tag).all()

@router.get("/tasks", response_model=List[TaskResponse])
def get_tasks(current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.query(Task).filter(Task.user_id == current_user["user"].id).all()

@router.get("/reward-types", response_model=List[RewardTypeResponse])
def get_reward_types(db: Session = Depends(get_db)):
    return db.query(RewardType).all()

@router.get("/rewards", response_model=List[RewardResponse])
def get_rewards(current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.query(Reward).filter(Reward.user_id == current_user["user"].id).all()

@router.get("/leaderboard", response_model=AllUsersResponse)
def get_all_users(
    db: Session = Depends(get_db)
):
    users = db.query(User).all()
    return {
        "users": [
            {
                "first_name": u.first_name,
                "last_name": u.last_name,
                "total_points": u.total_points
            }
            for u in users
        ]
    }
