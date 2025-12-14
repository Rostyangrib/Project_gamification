from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session


from config.db import get_db
from database import TaskStatus, Tag, Task, RewardType, Reward, User, Competition
from schemas import (
    TaskStatusUpdate, TaskStatusResponse,
    TagUpdate, TagResponse,
    TaskUpdate, TaskResponse,
    RewardTypeUpdate, RewardTypeResponse,
    RewardUpdate, RewardResponse,
    UserUpdate, UserResponse, CompetitionResponse, CompetitionUpdate,
    UserCompetitionAssign
)
from dependencies import get_current_user, require_admin, require_manager
from auth import get_password_hash

router = APIRouter(prefix="", tags=["PUT"])

@router.put("/users/me", response_model=UserResponse)
def update_own_user(
    payload: UserUpdate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    user: User = current_user["user"]

    # Обновление email с проверкой уникальности
    if payload.email and payload.email != user.email:
        if db.query(User).filter(User.email == payload.email).first():
            raise HTTPException(status_code=400, detail="Пользователь с таким email уже существует")
        user.email = payload.email

    # Обновление пароля
    if payload.password:
        user.password_hash = get_password_hash(payload.password)

    # Роль можно менять только через админский endpoint
    # Здесь игнорируем payload.role для безопасности

    db.commit()
    db.refresh(user)
    return user

@router.put("/admin/users/{user_id}", response_model=UserResponse)
def update_user_by_admin(
    user_id: int,
    payload: UserUpdate,
    current_user: dict = Depends(require_admin),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    # Обновление имени
    if payload.first_name is not None:
        user.first_name = payload.first_name

    # Обновление фамилии
    if payload.last_name is not None:
        user.last_name = payload.last_name

    # Обновление email с проверкой уникальности
    if payload.email and payload.email != user.email:
        if db.query(User).filter(User.email == payload.email).first():
            raise HTTPException(status_code=400, detail="Пользователь с таким email уже существует")
        user.email = payload.email

    # Обновление пароля
    if payload.password:
        user.password_hash = get_password_hash(payload.password)

    # Обновление роли
    if payload.role:
        if payload.role not in ['user', 'manager', 'admin']:
            raise HTTPException(status_code=400, detail="Недопустимая роль. Используйте 'user', 'manager' или 'admin'")
        user.role = payload.role

    db.commit()
    db.refresh(user)
    return user


@router.put("/users/{user_id}/competition", response_model=UserResponse)
def assign_user_to_competition(
    user_id: int,
    payload: UserCompetitionAssign,
    current_user: dict = Depends(require_manager),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    if payload.competition_id is not None:
        competition = db.query(Competition).filter(Competition.id == payload.competition_id).first()
        if not competition:
            raise HTTPException(status_code=404, detail="Соревнование не найдено")
        user.cur_comp = payload.competition_id
        user.total_points = 0
    else:
        user.cur_comp = None
    

    db.commit()
    db.refresh(user)
    return user

# @router.put("/boards/{board_id}", response_model=BoardResponse)
# def update_board(
#     board_id: int,
#     update_data: BoardUpdate,
#     current_user: dict = Depends(get_current_user),
#     db: Session = Depends(get_db)
# ):
#     board = db.query(Board).filter(
#         Board.id == board_id,
#         Board.user_id == current_user["user"].id
#     ).first()
#     if not board:
#         raise HTTPException(status_code=404, detail="Board не найден или не принадлежит вам")
#
#     for field, value in update_data.dict(exclude_unset=True).items():
#         if value is not None:
#             setattr(board, field, value)
#
#     db.commit()
#     db.refresh(board)
#     return board

@router.put("/task-statuses/{status_id}", response_model=TaskStatusResponse)
def update_task_status(
    status_id: int,
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

# @router.put("/categories/{category_id}", response_model=CategoryResponse)
# def update_category(
#     category_id: int,
#     update_data: CategoryUpdate,
#     current_user: dict = Depends(get_current_user),
#     db: Session = Depends(get_db)
# ):
#     category = db.query(Category).filter(
#         Category.id == category_id,
#         Category.user_id == current_user["user"].id
#     ).first()
#     if not category:
#         raise HTTPException(status_code=404, detail="Category не найдена или не принадлежит вам")
#
#     for field, value in update_data.dict(exclude_unset=True).items():
#         if value is not None:
#             setattr(category, field, value)
#
#     db.commit()
#     db.refresh(category)
#     return category

@router.put("/tags/{tag_id}", response_model=TagResponse)
def update_tag(
    tag_id: int,
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
    task_id: int,
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

    # if update_data.board_id and update_data.board_id != task.board_id:
    #     board = db.query(Board).filter(
    #         Board.id == update_data.board_id,
    #         Board.user_id == current_user["user"].id
    #     ).first()
    #     if not board:
    #         raise HTTPException(status_code=400, detail="Недопустимый board_id")
    #
    # if update_data.category_id and update_data.category_id != task.category_id:
    #     category = db.query(Category).filter(
    #         Category.id == update_data.category_id,
    #         Category.user_id == current_user["user"].id
    #     ).first()
    #     if not category:
    #         raise HTTPException(status_code=400, detail="Недопустимый category_id")

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
    type_id: int,
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
    reward_id: int,
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

@router.put("/competitions/{competition_id}", response_model=CompetitionResponse)
def update_competition(
    competition_id: int,
    competition_update: CompetitionUpdate,
    current_user: dict = Depends(require_manager), # Админ или менеджер может обновлять
    db: Session = Depends(get_db)
):
    competition = db.query(Competition).filter(Competition.id == competition_id).first()
    if not competition:
        raise HTTPException(status_code=404, detail="Соревнование не найдено")

    # Обновляем поля, которые пришли в запросе
    update_data = competition_update.model_dump(exclude_unset=True)
    
    # Конвертируем datetime с timezone в naive datetime (локальное время)
    if 'start_date' in update_data and update_data['start_date'] is not None:
        start_date = update_data['start_date']
        if start_date.tzinfo is not None:
            update_data['start_date'] = start_date.replace(tzinfo=None)
    
    if 'end_date' in update_data and update_data['end_date'] is not None:
        end_date = update_data['end_date']
        if end_date.tzinfo is not None:
            update_data['end_date'] = end_date.replace(tzinfo=None)
    
    for field, value in update_data.items():
        setattr(competition, field, value)

    db.commit()
    db.refresh(competition)

    return competition
