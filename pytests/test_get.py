import pytest
from datetime import datetime, timedelta
import uuid
from sqlalchemy import text
from auth import SECRET_KEY, ALGORITHM
from jose import jwt


def create_token(user_id: int, email: str, role: str = "user"):
    payload = {
        "sub": email,
        "user_id": user_id,
        "role": role,
        "exp": datetime.utcnow() + timedelta(hours=1)
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def unique_email():
    return f"test_{uuid.uuid4()}@example.com"


@pytest.fixture
def registered_user(client):
    email = unique_email()
    password = "userpass"
    res = client.post("/register", json={
        "first_name": "User",
        "last_name": "Test",
        "email": email,
        "password": password
    })
    user = res.json()
    login_res = client.post("/login", json={"email": email, "password": password})
    token = login_res.json()["access_token"]
    return {"user": user, "token": token}


@pytest.fixture
def registered_admin(client):
    email = unique_email()
    password = "adminpass"
    res = client.post("/users", json={
        "first_name": "Admin",
        "last_name": "Test",
        "email": email,
        "password": password
    })
    user = res.json()
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
    res = client.post("/users", json={
        "first_name": "Manager",
        "last_name": "Test",
        "email": email,
        "password": password
    })
    user = res.json()
    from db import engine
    with engine.connect() as conn:
        conn.execute(text("UPDATE users SET role = 'manager' WHERE id = :user_id"), {"user_id": user["id"]})
        conn.commit()
    login_res = client.post("/login", json={"email": email, "password": password})
    token = login_res.json()["access_token"]
    return {"user": user, "token": token}


@pytest.fixture
def sample_competition(client, registered_manager):
    headers = {"Authorization": f"Bearer {registered_manager['token']}"}
    comp = client.post("/competitions", json={
        "title": "Test Comp",
        "description": "For GET tests",
        "start_date": "2025-01-01T00:00:00",
        "end_date": "2025-01-31T23:59:59"
    }, headers=headers).json()
    return comp


@pytest.fixture
def sample_task(client, registered_user, registered_admin):
    # Создаём статус
    client.post("/task-statuses", json={"code": "get_test", "name": "GET Test"},
                headers={"Authorization": f"Bearer {registered_admin['token']}"})
    # Создаём задачу
    headers = {"Authorization": f"Bearer {registered_user['token']}"}
    task = client.post("/tasks", json={
        "title": "GET Test Task",
        "description": "For /tasks/latest",
        "status_id": 1,
        "due_date": "2025-12-31T23:59:59"
    }, headers=headers).json()
    return task


# Тесты
def test_get_tasks_latest_authorized(client, registered_user, sample_task):
    headers = {"Authorization": f"Bearer {registered_user['token']}"}
    response = client.get("/tasks/latest", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert data[0]["title"] == "GET Test Task"


def test_get_tasks_latest_unauthorized(client):
    response = client.get("/tasks/latest")
    assert response.status_code == 401


def test_get_all_users_as_admin(client, registered_admin):
    headers = {"Authorization": f"Bearer {registered_admin['token']}"}
    response = client.get("/users", headers=headers)
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_get_all_users_as_user_forbidden(client, registered_user):
    headers = {"Authorization": f"Bearer {registered_user['token']}"}
    response = client.get("/users", headers=headers)
    assert response.status_code == 403


def test_get_competition_dates(client, registered_user, sample_competition):
    headers = {"Authorization": f"Bearer {registered_user['token']}"}
    comp_id = sample_competition["id"]
    response = client.get(f"/competitions/{comp_id}/dates", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert "start_date" in data
    assert "end_date" in data


def test_get_competition_dates_not_found(client, registered_user):
    headers = {"Authorization": f"Bearer {registered_user['token']}"}
    response = client.get("/competitions/999999/dates", headers=headers)
    assert response.status_code == 404


def test_get_users_only_as_manager(client, registered_manager):
    headers = {"Authorization": f"Bearer {registered_manager['token']}"}
    response = client.get("/users/only", headers=headers)
    assert response.status_code == 200
    users = response.json()
    assert all(u["role"] == "user" for u in users)


def test_get_users_only_as_user_forbidden(client, registered_user):
    headers = {"Authorization": f"Bearer {registered_user['token']}"}
    response = client.get("/users/only", headers=headers)
    assert response.status_code == 403


def test_get_own_info(client, registered_user):
    headers = {"Authorization": f"Bearer {registered_user['token']}"}
    response = client.get("/users/me", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == registered_user["user"]["email"]


def test_get_task_statuses_public(client):
    response = client.get("/task-statuses")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_get_tags_public(client):
    response = client.get("/tags")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_get_tasks_authorized(client, registered_user, sample_task):
    headers = {"Authorization": f"Bearer {registered_user['token']}"}
    response = client.get("/tasks", headers=headers)
    assert response.status_code == 200
    tasks = response.json()
    assert len(tasks) >= 1
    assert tasks[0]["title"] == "GET Test Task"


def test_get_reward_types_public(client):
    response = client.get("/reward-types")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_get_rewards_authorized(client, registered_user, registered_admin):
    rt = client.post("/reward-types", json={"code": "get_test", "name": "GET Test"},
                     headers={"Authorization": f"Bearer {registered_admin['token']}"})
    client.post("/rewards", json={
        "type_id": rt.json()["id"],
        "points_amount": 10,
        "reason": "Test reward"
    }, headers={"Authorization": f"Bearer {registered_user['token']}"})

    response = client.get("/rewards", headers={"Authorization": f"Bearer {registered_user['token']}"})
    assert response.status_code == 200
    rewards = response.json()
    assert len(rewards) >= 1


def test_get_competitions_as_manager(client, registered_manager, sample_competition):
    headers = {"Authorization": f"Bearer {registered_manager['token']}"}
    response = client.get("/competitions", headers=headers)
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_get_competitions_as_user_forbidden(client, registered_user):
    headers = {"Authorization": f"Bearer {registered_user['token']}"}
    response = client.get("/competitions", headers=headers)
    assert response.status_code == 403


def test_get_competition_by_id_authorized(client, registered_user, sample_competition):
    headers = {"Authorization": f"Bearer {registered_user['token']}"}
    comp_id = sample_competition["id"]
    response = client.get(f"/competitions/{comp_id}", headers=headers)
    assert response.status_code == 200
    assert response.json()["id"] == comp_id


def test_get_competition_by_id_not_found(client, registered_user):
    headers = {"Authorization": f"Bearer {registered_user['token']}"}
    response = client.get("/competitions/999999", headers=headers)
    assert response.status_code == 404


def test_get_leaderboard_public(client, registered_user, sample_competition):
    comp_id = sample_competition["id"]
    from db import engine
    with engine.connect() as conn:
        conn.execute(text("UPDATE users SET cur_comp = :comp_id WHERE id = :user_id"),
                     {"comp_id": comp_id, "user_id": registered_user["user"]["id"]})
        conn.commit()

    response = client.get(f"/leaderboard/{comp_id}")
    assert response.status_code == 200
    leaderboard = response.json()
    assert isinstance(leaderboard, list)

def test_get_leaderboard_not_found(client):
    response = client.get("/leaderboard/999999")
    assert response.status_code == 404