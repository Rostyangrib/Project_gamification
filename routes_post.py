from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from passlib.context import CryptContext

from config.db import get_db
from database import (
    User, Board, TaskStatus, Category, Tag, TaskTag, Task, RewardType, Reward
)
from schemas import (
    UserCreate, UserResponse, Token, UserLogin,
    BoardCreate, BoardResponse,
    TaskStatusCreate, TaskStatusResponse,
    CategoryCreate, CategoryResponse,
    TagCreate, TagResponse,
    TaskCreate, TaskResponse,
    RewardTypeCreate, RewardTypeResponse,
    RewardCreate, RewardResponse,
    TaskTagCreate
)
from auth import verify_password, get_password_hash, create_access_token
from dependencies import get_current_user, require_admin

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

router = APIRouter()

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(user: UserCreate, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == user.email).first():
        raise HTTPException(
            status_code=400, detail="Пользователь с таким email уже существует"
        )

    hashed_password = get_password_hash(user.password)
    db_user = User(
        first_name=user.first_name,
        last_name=user.last_name,
        email=user.email,
        password_hash=hashed_password,
        total_points=0,
        role="user"
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


@router.post("/login", response_model=Token)
def login(user: UserLogin, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.email == user.email).first()
    if not db_user or not verify_password(user.password, db_user.password_hash):
        raise HTTPException(
            status_code=401,
            detail="Неверный email или пароль",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token(str(db_user.id), db_user.role)
    return {"access_token": access_token, "token_type": "bearer"}


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

@router.post("/boards", response_model=BoardResponse, status_code=status.HTTP_201_CREATED)
def create_board(
    board: BoardCreate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    db_board = Board(
        user_id=current_user["user"].id,
        name=board.name,
        description=board.description
    )
    db.add(db_board)
    db.commit()
    db.refresh(db_board)
    return db_board

@router.post("/task-statuses", response_model=TaskStatusResponse, status_code=status.HTTP_201_CREATED)
def create_task_status(
    status_data: TaskStatusCreate,
    current_user: dict = Depends(require_admin),
    db: Session = Depends(get_db)
):
    if db.query(TaskStatus).filter(TaskStatus.code == status_data.code).first():
        raise HTTPException(status_code=400, detail="TaskStatus с таким code уже существует")
    db_status = TaskStatus(code=status_data.code, name=status_data.name)
    db.add(db_status)
    db.commit()
    db.refresh(db_status)
    return db_status

@router.post("/categories", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED)
def create_category(
    category: CategoryCreate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    db_category = Category(
        user_id=current_user["user"].id,
        name=category.name,
        color=category.color
    )
    db.add(db_category)
    db.commit()
    db.refresh(db_category)
    return db_category

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
    board = db.query(Board).filter(Board.id == task.board_id, Board.user_id == current_user["user"].id).first()
    if not board:
        raise HTTPException(status_code=404, detail="Board не найден или не принадлежит пользователю")

    category = db.query(Category).filter(Category.id == task.category_id, Category.user_id == current_user["user"].id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category не найдена или не принадлежит пользователю")

    if not db.query(TaskStatus).filter(TaskStatus.id == task.status_id).first():
        raise HTTPException(status_code=404, detail="TaskStatus не найден")

    db_task = Task(
        user_id=current_user["user"].id,
        board_id=task.board_id,
        status_id=task.status_id,
        category_id=task.category_id,
        title=task.title,
        description=task.description,
        estimated_points=task.estimated_points,
        due_date=task.due_date
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
