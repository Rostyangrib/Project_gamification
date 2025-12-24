from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from passlib.context import CryptContext
from ml.ai_analyzer import analyze_task, YandexRateLimitError, YandexAPIError

from db import get_db
from database import (
    User, TaskStatus, Tag, TaskTag, Task, RewardType, Reward, Competition
)
from schemas import (
    UserCreate, UserResponse, Token, UserLogin,
    TaskStatusCreate, TaskStatusResponse,
    TagCreate, TagResponse,
    TaskCreate, TaskResponse,
    RewardTypeCreate, RewardTypeResponse,
    RewardCreate, RewardResponse,
    TaskTagCreate, CompetitionCreate,
    CompetitionResponse
)
from auth import verify_password, get_password_hash, create_access_token
from dependencies import get_current_user, require_admin, require_manager

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

router = APIRouter()

# Регистрация пользователя
@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(user: UserCreate, db: Session = Depends(get_db)):
    # Проверка на уникальность email
    if db.query(User).filter(User.email == user.email).first():
        raise HTTPException(
            status_code=400, detail="Пользователь с таким email уже существует"
        )
    # Шифрование пароля
    hashed_password = get_password_hash(user.password)
    db_user = User(
        first_name=user.first_name,
        last_name=user.last_name,
        email=user.email,
        password_hash=hashed_password,
        total_points=0,
        role="user"
    )
    # Запись в бд
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

@router.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    hashed_password = pwd_context.hash(user.password[:72])
    db_user = User(
        first_name=user.first_name,
        last_name=user.last_name,
        email=user.email,
        password_hash=hashed_password,
        total_points=0
    )
    try:
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Пользователь с таким email уже существует"
        )
    return db_user

# Логин
@router.post("/login", response_model=Token)
def login(user: UserLogin, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.email == user.email).first()
    # Если пользователя не существует, неправильная почта или пароль
    if not db_user or not verify_password(user.password, db_user.password_hash):
        raise HTTPException(
            status_code=401,
            detail="Неверный email или пароль",
            headers={"WWW-Authenticate": "Bearer"},
        )
    # Генерируем токен
    access_token = create_access_token(str(db_user.id), db_user.role)
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": str(db_user.id),
            "email": db_user.email,
            "first_name": db_user.first_name,
            "last_name": db_user.last_name,
            "total_points": db_user.total_points,
            "role": db_user.role
        }
    }

# @router.post("/boards", response_model=BoardResponse, status_code=status.HTTP_201_CREATED)
# def create_board(
#     board: BoardCreate,
#     current_user: dict = Depends(get_current_user),
#     db: Session = Depends(get_db)
# ):
#     db_board = Board(
#         user_id=current_user["user"].id,
#         name=board.name,
#         description=board.description
#     )
#     db.add(db_board)
#     db.commit()
#     db.refresh(db_board)
#     return db_board

# Создание статуса
@router.post("/task-statuses", response_model=TaskStatusResponse, status_code=status.HTTP_201_CREATED)
def create_task_status(
    status_data: TaskStatusCreate,
    current_user: dict = Depends(require_admin), # Только для админа
    db: Session = Depends(get_db)
):
    if db.query(TaskStatus).filter(TaskStatus.code == status_data.code).first():
        raise HTTPException(status_code=400, detail="TaskStatus с таким code уже существует")
    db_status = TaskStatus(code=status_data.code, name=status_data.name)
    db.add(db_status)
    db.commit()
    db.refresh(db_status)
    return db_status

# @router.post("/categories", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED)
# def create_category(
#     category: CategoryCreate,
#     current_user: dict = Depends(get_current_user),
#     db: Session = Depends(get_db)
# ):
#     db_category = Category(
#         user_id=current_user["user"].id,
#         name=category.name,
#         color=category.color
#     )
#     db.add(db_category)
#     db.commit()
#     db.refresh(db_category)
#     return db_category

@router.post("/tags", response_model=TagResponse, status_code=status.HTTP_201_CREATED)
def create_tag(
    tag: TagCreate,
    db: Session = Depends(get_db)
):
    if db.query(Tag).filter(Tag.name == tag.name).first():
        raise HTTPException(status_code=400, detail="Tag с таким именем уже существует")
    db_tag = Tag(name=tag.name)
    db.add(db_tag)
    db.commit()
    db.refresh(db_tag)
    return db_tag


@router.post("/tasks", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
def create_task(
        task: TaskCreate,
        current_user: dict = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    # board = db.query(Board).filter(Board.id == task.board_id, Board.user_id == current_user["user"].id).first()
    # if not board:
    #     raise HTTPException(status_code=404, detail="Board не найден или не принадлежит пользователю")
    #
    # category = db.query(Category).filter(Category.id == task.category_id,
    #                                      Category.user_id == current_user["user"].id).first()
    # if not category:
    #     raise HTTPException(status_code=404, detail="Category не найдена или не принадлежит пользователю")

    if not db.query(TaskStatus).filter(TaskStatus.id == task.status_id).first():
        raise HTTPException(status_code=404, detail="TaskStatus не найден")

    try:
        ai_result = analyze_task(task.title, task.description or "")
    except YandexRateLimitError as e:
        # Пробрасываем ошибку rate limit, чтобы тесты могли её зафиксировать
        raise HTTPException(
            status_code=429,
            detail="Слишком много запросов к AI. Пожалуйста, подождите несколько секунд и попробуйте снова."
        )
    except YandexAPIError as e:
        # Обработка других ошибок Yandex Cloud API
        raise HTTPException(
            status_code=503,
            detail=f"Ошибка при обращении к AI сервису: {str(e)}"
        )

    # Проверяем, является ли задача бессмысленной
    if ai_result.get("estimated_points") is None or ai_result.get("is_meaningless"):
        raise HTTPException(
            status_code=400,
            detail=f"Задача бессмысленна или неконкретна: {ai_result.get('explanation', 'Не удалось оценить задачу')}"
        )

    estimated_points = ai_result["estimated_points"]
    ai_metadata = ai_result

    db_task = Task(
        user_id=current_user["user"].id,
        #board_id=task.board_id,
        status_id=task.status_id,
        #category_id=task.category_id,
        title=task.title,
        description=task.description,
        estimated_points=estimated_points,
        ai_analysis_metadata=ai_metadata,
        due_date=task.due_date,
        awarded_points=0
    )
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    return db_task

@router.post("/tasks/{user_id}", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
def create_task(
        user_id: int,
        task: TaskCreate,
        current_user: dict = Depends(require_admin),
        db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    if not db.query(TaskStatus).filter(TaskStatus.id == task.status_id).first():
        raise HTTPException(status_code=404, detail="TaskStatus не найден")

    try:
        ai_result = analyze_task(task.title, task.description or "")
    except YandexRateLimitError as e:
        # Пробрасываем ошибку rate limit, чтобы тесты могли её зафиксировать
        raise HTTPException(
            status_code=429,
            detail="Слишком много запросов к AI. Пожалуйста, подождите несколько секунд и попробуйте снова."
        )
    except YandexAPIError as e:
        # Обработка других ошибок Yandex Cloud API
        raise HTTPException(
            status_code=503,
            detail=f"Ошибка при обращении к AI сервису: {str(e)}"
        )

    # Проверяем, является ли задача бессмысленной
    if ai_result.get("estimated_points") is None or ai_result.get("is_meaningless"):
        raise HTTPException(
            status_code=400,
            detail=f"Задача бессмысленна или неконкретна: {ai_result.get('explanation', 'Не удалось оценить задачу')}"
        )

    estimated_points = ai_result["estimated_points"]
    ai_metadata = ai_result

    # Создаем задачу для указанного пользователя
    db_task = Task(
        user_id=user_id,
        status_id=task.status_id,
        title=task.title,
        description=task.description,
        estimated_points=estimated_points,
        ai_analysis_metadata=ai_metadata,
        due_date=task.due_date,
        awarded_points=0
    )
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    return db_task


@router.post("/task-tags", status_code=status.HTTP_201_CREATED)
def create_task_tag(
    task_tag: TaskTagCreate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    task = db.query(Task).filter(Task.id == task_tag.task_id, Task.user_id == current_user["user"].id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task не найдена или не принадлежит пользователю")

    if not db.query(Tag).filter(Tag.id == task_tag.tag_id).first():
        raise HTTPException(status_code=404, detail="Tag не найден")

    existing = db.query(TaskTag).filter(
        TaskTag.task_id == task_tag.task_id,
        TaskTag.tag_id == task_tag.tag_id
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Связь Task-Tag уже существует")

    db_task_tag = TaskTag(task_id=task_tag.task_id, tag_id=task_tag.tag_id)
    db.add(db_task_tag)
    db.commit()
    return {"message": "Tag успешно привязан к задаче"}

@router.post("/reward-types", response_model=RewardTypeResponse, status_code=status.HTTP_201_CREATED)
def create_reward_type(
    reward_type: RewardTypeCreate,
    current_user: dict = Depends(require_admin),
    db: Session = Depends(get_db)
):
    if db.query(RewardType).filter(RewardType.code == reward_type.code).first():
        raise HTTPException(status_code=400, detail="RewardType с таким code уже существует")
    db_rt = RewardType(
        code=reward_type.code,
        name=reward_type.name,
        description=reward_type.description
    )
    db.add(db_rt)
    db.commit()
    db.refresh(db_rt)
    return db_rt

@router.post("/rewards", response_model=RewardResponse, status_code=status.HTTP_201_CREATED)
def create_reward(
    reward: RewardCreate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not db.query(RewardType).filter(RewardType.id == reward.type_id).first():
        raise HTTPException(status_code=404, detail="RewardType не найден")

    db_reward = Reward(
        user_id=current_user["user"].id,
        type_id=reward.type_id,
        points_amount=reward.points_amount,
        reason=reward.reason
    )
    db.add(db_reward)
    db.commit()
    db.refresh(db_reward)

    current_user["user"].total_points += reward.points_amount
    db.commit()

    return db_reward

@router.post("/competitions", response_model=CompetitionResponse, status_code=status.HTTP_201_CREATED)
def create_competition(
    competition: CompetitionCreate,
    current_user: dict = Depends(require_manager), # Админ или менеджер может создавать
    db: Session = Depends(get_db)
):
    existing = db.query(Competition).filter(Competition.title == competition.title).first()
    if existing:
        raise HTTPException(status_code=400, detail="Соревнование с таким названием уже существует")

    competition_data = competition.model_dump()
    if competition_data.get('start_date'):
        start_date = competition_data['start_date']
        if start_date.tzinfo is not None:
            competition_data['start_date'] = start_date.replace(tzinfo=None)
    
    if competition_data.get('end_date'):
        end_date = competition_data['end_date']
        if end_date.tzinfo is not None:
            competition_data['end_date'] = end_date.replace(tzinfo=None)

    db_competition = Competition(**competition_data)
    db.add(db_competition)
    db.commit()
    db.refresh(db_competition)
    return db_competition
