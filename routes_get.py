from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from schemas import TaskTitleAndDate, UserLeaderboard
from db import get_db
from database import User, TaskStatus, Tag, Task, RewardType, Reward, Competition, Participant
from schemas import (
    UserResponse, TaskStatusResponse,
    TagResponse, TaskResponse, RewardTypeResponse, RewardResponse,
    CompetitionResponse, CompetitionDatesResponse
)
from dependencies import get_current_user, require_admin, require_manager

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

@router.get("/users", response_model=List[UserResponse])
def get_all_users(
    current_user: dict = Depends(require_admin),
    db: Session = Depends(get_db)
):
    users = db.query(User).all()
    return users

@router.get("/competitions/{competition_id}/dates", response_model=CompetitionDatesResponse)
def get_competition_dates(
    competition_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    competition = db.query(Competition).filter(Competition.id == competition_id).first()
    if not competition:
        raise HTTPException(status_code=404, detail="Соревнование не найдено")

    return CompetitionDatesResponse(start_date=competition.start_date, end_date=competition.end_date)


@router.get("/users/only", response_model=List[UserResponse])
def get_all_users(
    current_user: dict = Depends(require_manager),
    db: Session = Depends(get_db)
):
    users = db.query(User).filter(User.role == "user").all()
    return users

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

# Получение списка всех соревнований
@router.get("/competitions", response_model=List[CompetitionResponse])
def get_competitions(
    current_user: dict = Depends(require_manager),
    db: Session = Depends(get_db)
):
    competitions = db.query(Competition).all()
    return competitions

# Получение конкретного соревнования по ID
@router.get("/competitions/{competition_id}", response_model=CompetitionResponse)
def get_competition(
    competition_id: int,
    current_user: dict = Depends(get_current_user), # Только админ может получить конкретное
    db: Session = Depends(get_db)
):
    competition = db.query(Competition).filter(Competition.id == competition_id).first()
    if not competition:
        raise HTTPException(status_code=404, detail="Соревнование не найдено")
    return competition

# Получение лидерборда конкретного соревнования
@router.get("/leaderboard/{competition_id}", response_model=List[UserLeaderboard])
def get_leaderboard(
    competition_id: int,
    #current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Лидерборд по соревнованию, использует таблицу participants и поле score.
    """
    comp = db.query(Competition).filter(Competition.id == competition_id).first()
    if not comp:
        raise HTTPException(status_code=404, detail="Соревнование не найдено")

    participants = (
        db.query(Participant, User.first_name, User.last_name)
        .join(User, Participant.user_id == User.id)
        .filter(Participant.competition_id == competition_id)
        .order_by(Participant.score.desc())
        .all()
    )
    leaderboard = [
        UserLeaderboard(first_name=first_name, last_name=last_name, score=participant.score)
        for participant, first_name, last_name in participants
    ]
    return leaderboard


@router.get("/participants/competition/{competition_id}")
def get_competition_participants(
    competition_id: int,
    current_user: dict = Depends(require_manager),
    db: Session = Depends(get_db)
):
    """
    Возвращает участников соревнования из таблицы participants,
    вместе с базовой информацией о пользователях.
    """
    comp = db.query(Competition).filter(Competition.id == competition_id).first()
    if not comp:
        raise HTTPException(status_code=404, detail="Соревнование не найдено")

    rows = (
        db.query(Participant, User)
        .join(User, Participant.user_id == User.id)
        .filter(Participant.competition_id == competition_id)
        .all()
    )

    return [
        {
            "participant_id": participant.id,
            "competition_id": participant.competition_id,
            "user_id": user.id,
            "score": participant.score,
            "user": {
                "id": user.id,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "email": user.email,
                "role": user.role,
                "cur_comp": user.cur_comp,
            },
        }
        for participant, user in rows
    ]


@router.get("/participants/users")
def get_users_with_participations(
    current_user: dict = Depends(require_manager),
    db: Session = Depends(get_db)
):
    """
    Возвращает пользователей (role == 'user') и их участия в соревнованиях
    из таблицы participants. Используется для панели менеджера.
    """
    users = db.query(User).filter(User.role == "user").all()
    participations = db.query(Participant).all()

    parts_by_user: dict[int, list[dict]] = {}
    for p in participations:
        parts_by_user.setdefault(p.user_id, []).append(
            {
                "id": p.id,
                "competition_id": p.competition_id,
                "score": p.score,
            }
        )

    result = []
    for u in users:
        result.append(
            {
                "id": u.id,
                "first_name": u.first_name,
                "last_name": u.last_name,
                "email": u.email,
                "role": u.role,
                "cur_comp": u.cur_comp,
                "participants": parts_by_user.get(u.id, []),
            }
        )

    return result
