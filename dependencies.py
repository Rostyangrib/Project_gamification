from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from jose import JWTError, jwt
import os

from db import get_db
from database import User

#Читает authorization из запроса
security = HTTPBearer()

#Подтверждение токена и данных из него(зависимость для эндпоинтов)
def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    #стандартная ошибка при неудаче проверки токена
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Не удалось проверить токен",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
                #расшифровывается токен и проверяется на подлиность
        payload = jwt.decode(
            credentials.credentials,
            os.getenv("SECRET_KEY"),
            algorithms=[os.getenv("ALGORITHM", "HS256")]
        )
        user_id = payload.get("sub")
        role = payload.get("role")
        if user_id is None or role is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    #проверка на существование пользователя в бд
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise credentials_exception
        #возвращаем расшифрованные данные о пользователе(все из бд)
    return {"user": user, "role": role}


def require_admin(current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Требуются права администратора"
        )
    return current_user

def require_manager(current_user: dict = Depends(get_current_user)):
    if current_user["role"] not in ["admin", "manager"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Требуются права менеджера или администратора"
        )
    return current_user
