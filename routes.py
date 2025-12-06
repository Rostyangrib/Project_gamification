# routes.py
from fastapi import APIRouter, Depends, HTTPException, status, Header
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from jose import JWTError, jwt
from datetime import timedelta
from passlib.context import CryptContext
from typing import Annotated

from config.db import get_db, engine
from database import init_db, User
from schemas import (
    UserCreate, UserResponse, Token, UserLogin
)
from auth import verify_password, get_password_hash, create_access_token
from datetime import datetime
from sqlalchemy import text
import os

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

from fastapi.security import HTTPBearer
security = HTTPBearer()
router = APIRouter()


def get_current_user(token: str = Depends(security), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Не удалось проверить токен",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, os.getenv("SECRET_KEY"), algorithms=[os.getenv("ALGORITHM", "HS256")])
        user_id = payload.get("sub")
        role = payload.get("role")  # ← получаем роль из токена
        if user_id is None or role is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise credentials_exception
    return {"user": user, "role": role}


# --- Функция: требовать роль admin ---
def require_admin(current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Требуются права администратора"
        )
    return current_user


# --- Маршруты ---

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
        role="user"  # ← по умолчанию "user"
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


@router.post("/token", response_model=Token)
def login(user: UserLogin, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.email == user.email).first()
    if not db_user or not verify_password(user.password, db_user.password_hash):
        raise HTTPException(
            status_code=401,
            detail="Неверный email или пароль",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(str(db_user.id), db_user.role)  # ← передаём роль
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/users/me", response_model=UserResponse)
def read_own_info(current_user: dict = Depends(get_current_user)):
    return current_user["user"]


@router.get("/admin/dashboard", dependencies=[Depends(require_admin)])
def admin_dashboard():
    return {"message": "Добро пожаловать, администратор!"}

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


@router.get("/")
async def root():
    return {
        "message": "Gamification API запущен!",
        "time": datetime.now().isoformat()
    }

