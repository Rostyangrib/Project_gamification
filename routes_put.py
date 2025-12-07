from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from uuid import UUID
from typing import Optional

from config.db import get_db
from database import Board, TaskStatus, Category, Tag, Task, RewardType, Reward
from schemas import (
    BoardUpdate, BoardResponse,
    TaskStatusUpdate, TaskStatusResponse,
    CategoryUpdate, CategoryResponse,
    TagUpdate, TagResponse,
    TaskUpdate, TaskResponse,
    RewardTypeUpdate, RewardTypeResponse,
    RewardUpdate, RewardResponse
)
from dependencies import get_current_user, require_admin

router = APIRouter(prefix="", tags=["PUT"])

@router.put("/boards/{board_id}", response_model=BoardResponse)
def update_board(
    board_id: UUID,
    update_data: BoardUpdate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    board = db.query(Board).filter(
        Board.id == board_id,
        Board.user_id == current_user["user"].id
    ).first()
    if not board:
        raise HTTPException(status_code=404, detail="Board не найден или не принадлежит вам")

    for field, value in update_data.dict(exclude_unset=True).items():
        if value is not None:
            setattr(board, field, value)

    db.commit()
    db.refresh(board)
    return board

@router.put("/task-statuses/{status_id}", response_model=TaskStatusResponse)
def update_task_status(
    status_id: UUID,
    update_data: TaskStatusUpdate,
    current_user: dict = Depends(require_admin),
    db: Session = Depends(get_db)
):
    status_obj = db.query(TaskStatus).filter(TaskStatus.id == status_id).first()
    if not status_obj:
        raise HTTPException(status_code=404, detail="TaskStatus не найден")

    if update_data.code and update_data.code != status_obj.code:
        if db.query(TaskStatus).filter(TaskStatus.code == update_data.code).first():
            raise HTTPException(status_code=400, detail="TaskStatus с таким code уже существует")

    for field, value in update_data.dict(exclude_unset=True).items():
        if value is not None:
            setattr(status_obj, field, value)

    db.commit()
    db.refresh(status_obj)
    return status_obj

@router.put("/categories/{category_id}", response_model=CategoryResponse)
def update_category(
    category_id: UUID,
    update_data: CategoryUpdate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    category = db.query(Category).filter(
        Category.id == category_id,
        Category.user_id == current_user["user"].id
    ).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category не найдена или не принадлежит вам")

    for field, value in update_data.dict(exclude_unset=True).items():
        if value is not None:
            setattr(category, field, value)

    db.commit()
    db.refresh(category)
    return category

@router.put("/tags/{tag_id}", response_model=TagResponse)
def update_tag(
    tag_id: UUID,
    update_data: TagUpdate,
    current_user: dict = Depends(require_admin),
    db: Session = Depends(get_db)
):
    tag = db.query(Tag).filter(Tag.id == tag_id).first()
    if not tag:
        raise HTTPException(status_code=404, detail="Tag не найден")

    if update_data.name and update_data.name != tag.name:
        if db.query(Tag).filter(Tag.name == update_data.name).first():
            raise HTTPException(status_code=400, detail="Tag с таким именем уже существует")

    for field, value in update_data.dict(exclude_unset=True).items():
        if value is not None:
            setattr(tag, field, value)

    db.commit()
    db.refresh(tag)
    return tag

@router.put("/tasks/{task_id}", response_model=TaskResponse)
def update_task(
    task_id: UUID,
    update_data: TaskUpdate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    task = db.query(Task).filter(
        Task.id == task_id,
        Task.user_id == current_user["user"].id
    ).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task не найдена или не принадлежит вам")

    if update_data.board_id and update_data.board_id != task.board_id:
        board = db.query(Board).filter(
            Board.id == update_data.board_id,
            Board.user_id == current_user["user"].id
        ).first()
        if not board:
            raise HTTPException(status_code=400, detail="Недопустимый board_id")

    if update_data.category_id and update_data.category_id != task.category_id:
        category = db.query(Category).filter(
            Category.id == update_data.category_id,
            Category.user_id == current_user["user"].id
        ).first()
        if not category:
            raise HTTPException(status_code=400, detail="Недопустимый category_id")

    if update_data.status_id and update_data.status_id != task.status_id:
        if not db.query(TaskStatus).filter(TaskStatus.id == update_data.status_id).first():
            raise HTTPException(status_code=400, detail="Недопустимый status_id")

    for field, value in update_data.dict(exclude_unset=True).items():
        if value is not None:
            setattr(task, field, value)

    db.commit()
    db.refresh(task)
    return task

@router.put("/reward-types/{type_id}", response_model=RewardTypeResponse)
def update_reward_type(
    type_id: UUID,
    update_data: RewardTypeUpdate,
    current_user: dict = Depends(require_admin),
    db: Session = Depends(get_db)
):
    rt = db.query(RewardType).filter(RewardType.id == type_id).first()
    if not rt:
        raise HTTPException(status_code=404, detail="RewardType не найден")

    if update_data.code and update_data.code != rt.code:
        if db.query(RewardType).filter(RewardType.code == update_data.code).first():
            raise HTTPException(status_code=400, detail="RewardType с таким code уже существует")

    for field, value in update_data.dict(exclude_unset=True).items():
        if value is not None:
            setattr(rt, field, value)

    db.commit()
    db.refresh(rt)
    return rt

@router.put("/rewards/{reward_id}", response_model=RewardResponse)
def update_reward(
    reward_id: UUID,
    update_data: RewardUpdate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    reward = db.query(Reward).filter(
        Reward.id == reward_id,
        Reward.user_id == current_user["user"].id
    ).first()
    if not reward:
        raise HTTPException(status_code=404, detail="Reward не найден или не принадлежит вам")

    old_points = reward.points_amount

    if update_data.type_id and update_data.type_id != reward.type_id:
        if not db.query(RewardType).filter(RewardType.id == update_data.type_id).first():
            raise HTTPException(status_code=400, detail="Недопустимый type_id")

    for field, value in update_data.dict(exclude_unset=True).items():
        if value is not None:
            setattr(reward, field, value)

    if update_data.points_amount is not None and update_data.points_amount != old_points:
        delta = update_data.points_amount - old_points
        current_user["user"].total_points += delta

    db.commit()
    db.refresh(reward)
    return reward