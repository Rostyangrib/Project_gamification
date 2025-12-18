# pytests/test_post.py
import pytest
from jose import jwt
from datetime import datetime, timedelta
import uuid
from sqlalchemy import text

# Безопасный импорт с fallback
try:
    from auth import SECRET_KEY, ALGORITHM
except ImportError:
    SECRET_KEY = "test-secret-key-for-pytest-fallback"
    ALGORITHM = "HS256"


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


# ----------------------------------------
# Auth: /register, /login
# ----------------------------------------

def test_register_new_user(client):
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
    email = unique_email()
    client.post("/register", json={"email": email, "first_name": "A", "last_name": "B", "password": "123"})
    response = client.post("/register", json={"email": email, "first_name": "C", "last_name": "D", "password": "456"})
    assert response.status_code == 400


def test_login_success(client):
    email = unique_email()
    password = "pass123"
    client.post("/register", json={"email": email, "first_name": "Test", "last_name": "User", "password": password})
    response = client.post("/login", json={"email": email, "password": password})
    assert response.status_code == 200


def test_login_wrong_password(client):
    email = unique_email()
    client.post("/register", json={"email": email, "first_name": "Bad", "last_name": "Login", "password": "correct"})
    response = client.post("/login", json={"email": email, "password": "wrong"})
    assert response.status_code == 401


# ----------------------------------------
# Фикстуры: создание пользователей с нужной ролью
# ----------------------------------------

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
    # Создаём через /users (твой эндпоинт без защиты)
    res = client.post("/users", json={"email": email, "first_name": "Admin", "last_name": "Test", "password": password})
    user = res.json()
    # Меняем роль на admin через SQL (используем text!)
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
    res = client.post("/users",
                      json={"email": email, "first_name": "Manager", "last_name": "Test", "password": password})
    user = res.json()
    from db import engine
    with engine.connect() as conn:
        conn.execute(text("UPDATE users SET role = 'manager' WHERE id = :user_id"), {"user_id": user["id"]})
        conn.commit()
    login_res = client.post("/login", json={"email": email, "password": password})
    token = login_res.json()["access_token"]
    return {"user": user, "token": token}


# ----------------------------------------
# TaskStatus (admin only)
# ----------------------------------------

def test_create_task_status_as_admin(client, registered_admin):
    headers = {"Authorization": f"Bearer {registered_admin['token']}"}
    response = client.post("/task-statuses", json={"code": "test", "name": "Test"}, headers=headers)
    assert response.status_code == 201


def test_create_task_status_as_user_forbidden(client, registered_user):
    headers = {"Authorization": f"Bearer {registered_user['token']}"}
    response = client.post("/task-statuses", json={"code": "forbidden", "name": "Test"}, headers=headers)
    assert response.status_code == 403


def test_create_duplicate_task_status_code(client, registered_admin):
    headers = {"Authorization": f"Bearer {registered_admin['token']}"}
    client.post("/task-statuses", json={"code": "dup", "name": "A"}, headers=headers)
    response = client.post("/task-statuses", json={"code": "dup", "name": "B"}, headers=headers)
    assert response.status_code == 400


# ----------------------------------------
# Tags (public)
# ----------------------------------------

def test_create_tag(client):
    response = client.post("/tags", json={"name": "Urgent"})
    assert response.status_code == 201


def test_create_duplicate_tag(client):
    name = f"tag_{uuid.uuid4().hex[:6]}"
    client.post("/tags", json={"name": name})
    response = client.post("/tags", json={"name": name})
    assert response.status_code == 400


# ----------------------------------------
# Tasks
# ----------------------------------------

def test_create_task_as_user(client, registered_user, registered_admin):
    # Сначала создаём статус (через админа)
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
    headers = {"Authorization": f"Bearer {registered_admin['token']}"}
    response = client.post("/tasks/999999", json={
        "title": "Impossible",
        "status_id": 1,
        "due_date": "2025-12-31T23:59:59"
    }, headers=headers)
    assert response.status_code == 404


# ----------------------------------------
# TaskTags
# ----------------------------------------

def test_create_task_tag(client, registered_user, registered_admin):
    # Создаём статус
    client.post("/task-statuses", json={"code": "tag_task", "name": "Tag Task"},
                headers={"Authorization": f"Bearer {registered_admin['token']}"})

    headers = {"Authorization": f"Bearer {registered_user['token']}"}
    task = client.post("/tasks", json={"title": "Task for tag", "status_id": 1, "due_date": "2025-12-31"},
                       headers=headers).json()
    tag = client.post("/tags", json={"name": f"tag_{uuid.uuid4().hex[:6]}"}).json()

    response = client.post("/task-tags", json={"task_id": task["id"], "tag_id": tag["id"]}, headers=headers)
    assert response.status_code == 201


# ----------------------------------------
# RewardTypes (admin only)
# ----------------------------------------

def test_create_reward_type_as_admin(client, registered_admin):
    headers = {"Authorization": f"Bearer {registered_admin['token']}"}
    response = client.post("/reward-types", json={"code": "test", "name": "Test Reward"}, headers=headers)
    assert response.status_code == 201


def test_create_reward_type_as_user_forbidden(client, registered_user):
    headers = {"Authorization": f"Bearer {registered_user['token']}"}
    response = client.post("/reward-types", json={"code": "forbidden", "name": "Test"}, headers=headers)
    assert response.status_code == 403


# ----------------------------------------
# Rewards
# ----------------------------------------

def test_create_reward(client, registered_user, registered_admin):
    # Создаём тип награды
    rt = client.post("/reward-types", json={"code": "pytest", "name": "Pytest Reward"},
                     headers={"Authorization": f"Bearer {registered_admin['token']}"})
    rt_id = rt.json()["id"]

    headers = {"Authorization": f"Bearer {registered_user['token']}"}
    response = client.post("/rewards", json={"type_id": rt_id, "points_amount": 50, "reason": "Test"}, headers=headers)
    assert response.status_code == 201


# ----------------------------------------
# Competitions (manager only)
# ----------------------------------------

def test_create_competition_as_manager(client, registered_manager):
    headers = {"Authorization": f"Bearer {registered_manager['token']}"}
    response = client.post("/competitions", json={
        "title": "Test Comp",
        "description": "Test",
        "start_date": "2025-01-01T00:00:00",
        "end_date": "2025-01-31T23:59:59"
    }, headers=headers)
    assert response.status_code == 201


def test_create_competition_as_user_forbidden(client, registered_user):
    headers = {"Authorization": f"Bearer {registered_user['token']}"}
    response = client.post("/competitions", json={
        "title": "Forbidden",
        "description": "Test",
        "start_date": "2025-02-01T00:00:00",
        "end_date": "2025-02-28T23:59:59"
    }, headers=headers)
    assert response.status_code == 403


def test_create_duplicate_competition_title(client, registered_manager):
    headers = {"Authorization": f"Bearer {registered_manager['token']}"}
    title = f"Comp_{uuid.uuid4().hex[:8]}"
    client.post("/competitions",
                json={"title": title, "description": "A", "start_date": "2025-03-01", "end_date": "2025-03-31"},
                headers=headers)
    response = client.post("/competitions", json={"title": title, "description": "B", "start_date": "2025-04-01",
                                                  "end_date": "2025-04-30"}, headers=headers)
    assert response.status_code == 400