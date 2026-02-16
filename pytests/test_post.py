import pytest
from jose import jwt
from datetime import datetime, timedelta
import uuid
from sqlalchemy import text
from unittest.mock import patch
from auth import SECRET_KEY, ALGORITHM


def create_token(user_id: int, email: str, role: str = "user"):
    payload = {
        "sub": email,
        "user_id": user_id,
        "role": role,
        "exp": datetime.utcnow() + timedelta(hours=1)
    }
    if not SECRET_KEY:
        raise ValueError("SECRET_KEY is not set!")
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def unique_email():
    return f"test_{uuid.uuid4()}@example.com"


# Auth: /register, /login
def test_register_new_user(client):
    """
    Тест успешной регистрации нового пользователя.
    Проверяет что новый пользователь может зарегистрироваться через POST /register и получает роль "user".
    """
    email = unique_email()
    response = client.post("/register", json={
        "first_name": "Test",
        "last_name": "User",
        "email": email,
        "password": "password123"
    })
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == email
    assert data["role"] == "user"


def test_register_duplicate_email(client):
    """
    Тест регистрации с дублирующимся email.
    Проверяет что попытка зарегистрироваться с уже существующим email возвращает 400 Bad Request.
    """
    email = unique_email()
    client.post("/register", json={"email": email, "first_name": "A", "last_name": "B", "password": "123456"})
    response = client.post("/register", json={"email": email, "first_name": "C", "last_name": "D", "password": "123456"})
    assert response.status_code == 400


def test_login_success(client):
    """
    Тест успешного входа пользователя.
    Проверяет что зарегистрированный пользователь может войти через POST /login с правильными credentials.
    """
    email = unique_email()
    password = "pass123"
    client.post("/register", json={"email": email, "first_name": "Test", "last_name": "User", "password": password})
    response = client.post("/login", json={"email": email, "password": password})
    assert response.status_code == 200


def test_login_wrong_password(client):
    """
    Тест входа с неправильным паролем.
    Проверяет что попытка входа с неправильным паролем возвращает 401 Unauthorized.
    """
    email = unique_email()
    client.post("/register", json={"email": email, "first_name": "Bad", "last_name": "Login", "password": "correct"})
    response = client.post("/login", json={"email": email, "password": "wrong"})
    assert response.status_code == 401


# Фикстуры: создание пользователей с нужной ролью
@pytest.fixture
def registered_user(client):
    email = unique_email()
    password = "userpass"
    res = client.post("/register",
                      json={"email": email, "first_name": "User", "last_name": "Test", "password": password})
    user = res.json()
    login_res = client.post("/login", json={"email": email, "password": password})
    token = login_res.json()["access_token"]
    return {"user": user, "token": token}


@pytest.fixture
def registered_admin(client):
    email = unique_email()
    password = "adminpass"
    # Создаём через /register
    res = client.post("/register", json={"email": email, "first_name": "Admin", "last_name": "Test", "password": password})
    user = res.json()
    # Меняем роль на admin
    from db import engine
    with engine.connect() as conn:
        conn.execute(text("UPDATE users SET role = 'admin' WHERE id = :user_id"), {"user_id": user["id"]})
        conn.commit()
    login_res = client.post("/login", json={"email": email, "password": password})
    token = login_res.json()["access_token"]
    return {"user": user, "token": token}


@pytest.fixture
def registered_manager(client):
    email = unique_email()
    password = "managerpass"
    res = client.post("/register",
                      json={"email": email, "first_name": "Manager", "last_name": "Test", "password": password})
    user = res.json()
    from db import engine
    with engine.connect() as conn:
        conn.execute(text("UPDATE users SET role = 'manager' WHERE id = :user_id"), {"user_id": user["id"]})
        conn.commit()
    login_res = client.post("/login", json={"email": email, "password": password})
    token = login_res.json()["access_token"]
    return {"user": user, "token": token}



# TaskStatus только для админа
def test_create_task_status_as_admin(client, registered_admin):
    """
    Тест создания статуса задачи администратором.
    Проверяет что администратор может создать статус задачи через POST /task-statuses.
    """
    headers = {"Authorization": f"Bearer {registered_admin['token']}"}
    response = client.post("/task-statuses", json={"code": "test", "name": "Test"}, headers=headers)
    assert response.status_code == 201


def test_create_task_status_as_user_forbidden(client, registered_user):
    """
    Тест запрета создания статуса задачи обычным пользователем.
    Проверяет что обычный пользователь не может создать статус задачи (403 Forbidden).
    """
    headers = {"Authorization": f"Bearer {registered_user['token']}"}
    response = client.post("/task-statuses", json={"code": "forbidden", "name": "Test"}, headers=headers)
    assert response.status_code == 403


def test_create_duplicate_task_status_code(client, registered_admin):
    """
    Тест создания статуса задачи с дублирующимся кодом.
    Проверяет что попытка создать статус с уже существующим кодом возвращает 400 Bad Request.
    """
    headers = {"Authorization": f"Bearer {registered_admin['token']}"}
    client.post("/task-statuses", json={"code": "dup", "name": "A"}, headers=headers)
    response = client.post("/task-statuses", json={"code": "dup", "name": "B"}, headers=headers)
    assert response.status_code == 400


# Tags
def test_create_tag(client):
    """
    Тест создания тега.
    Проверяет что можно создать тег через POST /tags без авторизации.
    """
    response = client.post("/tags", json={"name": "Urgent"})
    assert response.status_code == 201


def test_create_duplicate_tag(client):
    """
    Тест создания тега с дублирующимся именем.
    Проверяет что попытка создать тег с уже существующим именем возвращает 400 Bad Request.
    """
    name = f"tag_{uuid.uuid4().hex[:6]}"
    client.post("/tags", json={"name": name})
    response = client.post("/tags", json={"name": name})
    assert response.status_code == 400


# Tasks
def test_create_task_as_user(client, registered_user, registered_admin):
    """
    Тест создания задачи пользователем.
    Проверяет что пользователь может создать задачу для себя через POST /tasks.
    """
    # Сначала создаём статус через админа
    client.post("/task-statuses", json={"code": "test_status", "name": "Test"},
                headers={"Authorization": f"Bearer {registered_admin['token']}"})

    headers = {"Authorization": f"Bearer {registered_user['token']}"}
    response = client.post("/tasks", json={
        "title": "Test task",
        "status_id": 1,
        "due_date": "2025-12-31T23:59:59"
    }, headers=headers)
    assert response.status_code == 201


def test_create_task_for_other_user_as_admin(client, registered_admin, registered_user):
    """
    Тест создания задачи для другого пользователя администратором.
    Проверяет что администратор может создать задачу для любого пользователя через POST /tasks/{user_id}.
    """
    client.post("/task-statuses", json={"code": "admin_task", "name": "Admin Task"},
                headers={"Authorization": f"Bearer {registered_admin['token']}"})

    response = client.post(f"/tasks/{registered_user['user']['id']}", json={
        "title": "Admin-created task",
        "status_id": 1,
        "due_date": "2025-12-31T23:59:59"
    }, headers={"Authorization": f"Bearer {registered_admin['token']}"})
    assert response.status_code == 201
    assert response.json()["user_id"] == registered_user['user']['id']


def test_create_task_for_nonexistent_user(client, registered_admin):
    """
    Тест создания задачи для несуществующего пользователя.
    Проверяет что попытка создать задачу для несуществующего пользователя возвращает 404 Not Found.
    """
    headers = {"Authorization": f"Bearer {registered_admin['token']}"}
    response = client.post("/tasks/999999", json={
        "title": "Impossible",
        "status_id": 1,
        "due_date": "2025-12-31T23:59:59"
    }, headers=headers)
    assert response.status_code == 404



# TaskTags
def test_create_task_tag(client, registered_user, registered_admin):
    """
    Тест привязки тега к задаче.
    Проверяет что владелец задачи может привязать тег к своей задаче через POST /task-tags.
    """
    client.post("/task-statuses", json={"code": "tag_task", "name": "Tag Task"},
                headers={"Authorization": f"Bearer {registered_admin['token']}"})

    headers = {"Authorization": f"Bearer {registered_user['token']}"}
    task = client.post("/tasks", json={"title": "Task for tag", "status_id": 1, "due_date": "2025-12-31"},
                       headers=headers).json()
    tag = client.post("/tags", json={"name": f"tag_{uuid.uuid4().hex[:6]}"}).json()

    response = client.post("/task-tags", json={"task_id": task["id"], "tag_id": tag["id"]}, headers=headers)
    assert response.status_code == 201



# RewardTypes
def test_create_reward_type_as_admin(client, registered_admin):
    """
    Тест создания типа награды администратором.
    Проверяет что администратор может создать тип награды через POST /reward-types.
    """
    headers = {"Authorization": f"Bearer {registered_admin['token']}"}
    response = client.post("/reward-types", json={"code": "test", "name": "Test Reward"}, headers=headers)
    assert response.status_code == 201


def test_create_reward_type_as_user_forbidden(client, registered_user):
    """
    Тест запрета создания типа награды обычным пользователем.
    Проверяет что обычный пользователь не может создать тип награды (403 Forbidden).
    """
    headers = {"Authorization": f"Bearer {registered_user['token']}"}
    response = client.post("/reward-types", json={"code": "forbidden", "name": "Test"}, headers=headers)
    assert response.status_code == 403


# Rewards
def test_create_reward(client, registered_user, registered_admin):
    """
    Тест создания награды пользователем.
    Проверяет что пользователь может создать награду для себя через POST /rewards.
    """
    # Создаём тип награды
    rt = client.post("/reward-types", json={"code": "pytest", "name": "Pytest Reward"},
                     headers={"Authorization": f"Bearer {registered_admin['token']}"})
    rt_id = rt.json()["id"]

    headers = {"Authorization": f"Bearer {registered_user['token']}"}
    response = client.post("/rewards", json={"type_id": rt_id, "points_amount": 50, "reason": "Test"}, headers=headers)
    assert response.status_code == 201


# Competitions
def test_create_competition_as_manager(client, registered_manager):
    """
    Тест создания соревнования менеджером.
    Проверяет что менеджер может создать соревнование через POST /competitions.
    """
    headers = {"Authorization": f"Bearer {registered_manager['token']}"}
    response = client.post("/competitions", json={
        "title": "Test Comp",
        "description": "Test",
        "start_date": "2025-01-01T00:00:00",
        "end_date": "2025-01-31T23:59:59"
    }, headers=headers)
    assert response.status_code == 201


def test_create_competition_as_user_forbidden(client, registered_user):
    """
    Тест запрета создания соревнования обычным пользователем.
    Проверяет что обычный пользователь не может создать соревнование (403 Forbidden).
    """
    headers = {"Authorization": f"Bearer {registered_user['token']}"}
    response = client.post("/competitions", json={
        "title": "Forbidden",
        "description": "Test",
        "start_date": "2025-02-01T00:00:00",
        "end_date": "2025-02-28T23:59:59"
    }, headers=headers)
    assert response.status_code == 403


def test_create_duplicate_competition_title(client, registered_manager):
    """
    Тест создания соревнования с дублирующимся названием.
    Проверяет что попытка создать соревнование с уже существующим названием возвращает 400 Bad Request.
    """
    headers = {"Authorization": f"Bearer {registered_manager['token']}"}
    title = f"Comp_{uuid.uuid4().hex[:8]}"
    client.post("/competitions",
                json={"title": title, "description": "A", "start_date": "2025-03-01", "end_date": "2025-03-31"},
                headers=headers)
    response = client.post("/competitions", json={"title": title, "description": "B", "start_date": "2025-04-01",
                                                  "end_date": "2025-04-30"}, headers=headers)
    assert response.status_code == 400
