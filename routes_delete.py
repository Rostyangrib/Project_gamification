from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from uuid import UUID

from config.db import get_db
from database import User, Board, TaskStatus, Category, Tag, Task, TaskTag, RewardType, Reward
from dependencies import get_current_user, require_admin

router = APIRouter(prefix="", tags=["DELETE"])

@router.delete("/users/me", status_code=status.HTTP_204_NO_CONTENT)
def delete_own_account(
        current_user: dict = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    user = current_user["user"]

    tasks = db.query(Task).filter(Task.user_id == user.id).all()
    for task in tasks:
        db.delete(task)

    db.query(Board).filter(Board.user_id == user.id).delete()

    db.query(Category).filter(Category.user_id == user.id).delete()

    db.query(Reward).filter(Reward.user_id == user.id).delete()

    db.delete(user)
    db.commit()
    return

@router.delete("/admin/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user_by_admin(
    user_id: UUID,
    current_user: dict = Depends(require_admin),  # ← только админ
    db: Session = Depends(get_db)
):

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    tasks = db.query(Task).filter(Task.user_id == user_id).all()
    for task in tasks:
        db.delete(task)

    db.query(Board).filter(Board.user_id == user_id).delete()

    db.query(Category).filter(Category.user_id == user_id).delete()

    db.query(Reward).filter(Reward.user_id == user_id).delete()

    db.delete(user)
    db.commit()
    return

@router.delete("/boards/{board_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_board(
        board_id: UUID,
        current_user: dict = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    board = db.query(Board).filter(
        Board.id == board_id,
        Board.user_id == current_user["user"].id
    ).first()
    if not board:
        raise HTTPException(status_code=404, detail="Board не найден или не принадлежит вам")

    db.query(Task).filter(Task.board_id == board_id).delete()

    db.delete(board)
    db.commit()
    return

@router.delete("/task-statuses/{status_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task_status(
        status_id: UUID,
        current_user: dict = Depends(require_admin),
        db: Session = Depends(get_db)
):
    status_obj = db.query(TaskStatus).filter(TaskStatus.id == status_id).first()
    if not status_obj:
        raise HTTPException(status_code=404, detail="TaskStatus не найден")

    db.delete(status_obj)
    db.commit()
    return

@router.delete("/categories/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_category(
        category_id: UUID,
        current_user: dict = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    category = db.query(Category).filter(
        Category.id == category_id,
        Category.user_id == current_user["user"].id
    ).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category не найдена или не принадлежит вам")

    db.delete(category)
    db.commit()
    return

@router.delete("/tags/{tag_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_tag(
        tag_id: UUID,
        current_user: dict = Depends(require_admin),
        db: Session = Depends(get_db)
):
    tag = db.query(Tag).filter(Tag.id == tag_id).first()
    if not tag:
        raise HTTPException(status_code=404, detail="Tag не найден")

    db.query(TaskTag).filter(TaskTag.tag_id == tag_id).delete()

    db.delete(tag)
    db.commit()
    return

@router.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(
        task_id: UUID,
        current_user: dict = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    task = db.query(Task).filter(
        Task.id == task_id,
        Task.user_id == current_user["user"].id
    ).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task не найдена или не принадлежит вам")

    db.query(TaskTag).filter(TaskTag.task_id == task_id).delete()

    db.delete(task)
    db.commit()
    return

@router.delete("/reward-types/{type_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_reward_type(
        type_id: UUID,
        current_user: dict = Depends(require_admin),
        db: Session = Depends(get_db)
):
    rt = db.query(RewardType).filter(RewardType.id == type_id).first()
    if not rt:
        raise HTTPException(status_code=404, detail="RewardType не найден")

    db.delete(rt)
    db.commit()
    return

@router.delete("/rewards/{reward_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_reward(
        reward_id: UUID,
        current_user: dict = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    reward = db.query(Reward).filter(
        Reward.id == reward_id,
        Reward.user_id == current_user["user"].id
    ).first()
    if not reward:
        raise HTTPException(status_code=404, detail="Reward не найден или не принадлежит вам")

    db.delete(reward)
    db.commit()
    return
