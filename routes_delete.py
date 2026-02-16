from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from db import get_db
from database import User, TaskStatus, Tag, Task, TaskTag, RewardType, Reward, Competition, Participant
from dependencies import get_current_user, require_admin, require_manager

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

    # db.query(Board).filter(Board.user_id == user.id).delete()
    # db.query(Category).filter(Category.user_id == user.id).delete()

    db.query(Reward).filter(Reward.user_id == user.id).delete()

    db.query(Task).filter(Task.user_id == user.id).delete()

    db.delete(user)
    db.commit()
    return

@router.delete("/admin/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user_by_admin(
    user_id: int,
    current_user: dict = Depends(require_admin),
    db: Session = Depends(get_db)
):

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    tasks = db.query(Task).filter(Task.user_id == user_id).all()
    for task in tasks:
        db.delete(task)

    # db.query(Board).filter(Board.user_id == user_id).delete()
    # db.query(Category).filter(Category.user_id == user_id).delete()

    db.query(Reward).filter(Reward.user_id == user_id).delete()

    db.query(Task).filter(Task.user_id == user_id).delete()

    db.delete(user)
    db.commit()
    return

# @router.delete("/boards/{board_id}", status_code=status.HTTP_204_NO_CONTENT)
# def delete_board(
#         board_id: int
#      ,
#         current_user: dict = Depends(get_current_user),
#         db: Session = Depends(get_db)
# ):
#     # board = db.query(Board).filter(
#     #     Board.id == board_id,
#     #     Board.user_id == current_user["user"].id
#     # ).first()
#     if not board:
#         raise HTTPException(status_code=404, detail="Board не найден или не принадлежит вам")
#
#     db.query(Task).filter(Task.board_id == board_id).delete()
#
#     db.delete(board)
#     db.commit()
#     return

@router.delete("/task-statuses/{status_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task_status(
        status_id: int,
        current_user: dict = Depends(require_admin),
        db: Session = Depends(get_db)
):
    status_obj = db.query(TaskStatus).filter(TaskStatus.id == status_id).first()
    if not status_obj:
        raise HTTPException(status_code=404, detail="TaskStatus не найден")

    db.delete(status_obj)
    db.commit()
    return

# @router.delete("/categories/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
# def delete_category(
#         category_id: int
#      ,
#         current_user: dict = Depends(get_current_user),
#         db: Session = Depends(get_db)
# ):
#     category = db.query(Category).filter(
#         Category.id == category_id,
#         Category.user_id == current_user["user"].id
#     ).first()
#     if not category:
#         raise HTTPException(status_code=404, detail="Category не найдена или не принадлежит вам")
#
#     db.delete(category)
#     db.commit()
#     return

@router.delete("/tags/{tag_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_tag(
        tag_id: int,
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
        task_id: int,
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
        type_id: int,
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
        reward_id: int,
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

@router.delete("/competitions/{competition_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_competition(
    competition_id: int,
    current_user: dict = Depends(require_manager), # Админ или менеджер может удалять
    db: Session = Depends(get_db)
):
    competition = db.query(Competition).filter(Competition.id == competition_id).first()
    if not competition:
        raise HTTPException(status_code=404, detail="Соревнование не найдено")

    db.query(User).filter(User.cur_comp == competition_id).update({User.cur_comp: None})
    db.query(Participant).filter(Participant.competition_id == competition_id).delete()

    db.delete(competition)
    db.commit()
    return

@router.delete("/participants/{participant_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_participant(
    participant_id: int,
    current_user: dict = Depends(require_manager),
    db: Session = Depends(get_db)
):
    """Удаляет участника из соревнования по participant_id"""
    participant = db.query(Participant).filter(Participant.id == participant_id).first()
    if not participant:
        raise HTTPException(status_code=404, detail="Участник не найден")
    
    # Обновляем cur_comp пользователя, если он был в этом соревновании
    user = db.query(User).filter(User.id == participant.user_id).first()
    if user and user.cur_comp == participant.competition_id:
        user.cur_comp = None
    
    db.delete(participant)
    db.commit()
    return

@router.delete("/participants/competition/{competition_id}/user/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_participant_by_competition_and_user(
    competition_id: int,
    user_id: int,
    current_user: dict = Depends(require_manager),
    db: Session = Depends(get_db)
):
    """Удаляет участника из соревнования по competition_id и user_id"""
    participant = db.query(Participant).filter(
        Participant.competition_id == competition_id,
        Participant.user_id == user_id
    ).first()
    if not participant:
        raise HTTPException(status_code=404, detail="Участник не найден")
    
    # Обновляем cur_comp пользователя, если он был в этом соревновании
    user = db.query(User).filter(User.id == user_id).first()
    if user and user.cur_comp == competition_id:
        user.cur_comp = None
    
    db.delete(participant)
    db.commit()
    return