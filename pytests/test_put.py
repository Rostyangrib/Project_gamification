import pytest
from jose import jwt
from datetime import datetime, timedelta
import uuid
from sqlalchemy import text
from auth import SECRET_KEY, ALGORITHM


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
    res = client.post("/register", json={
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
    res = client.post("/register", json={
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
        "title": "PUT Test Comp",
        "description": "For PUT tests",
        "start_date": "2025-06-01T00:00:00",
        "end_date": "2025-08-31T23:59:59"
    }, headers=headers).json()
    return comp


@pytest.fixture
def sample_task_status(client, registered_admin):
    headers = {"Authorization": f"Bearer {registered_admin['token']}"}
    status = client.post("/task-statuses", json={"code": "put_test", "name": "PUT Test"},
                        headers=headers).json()
    return status


@pytest.fixture
def sample_tag(client, registered_admin):
    headers = {"Authorization": f"Bearer {registered_admin['token']}"}
    tag = client.post("/tags", json={"name": "PUT Tag"}, headers=headers).json()
    return tag


@pytest.fixture
def sample_task(client, registered_user, sample_task_status):
    headers = {"Authorization": f"Bearer {registered_user['token']}"}
    task = client.post("/tasks", json={
        "title": "PUT Test Task",
        "status_id": sample_task_status["id"],
        "due_date": "2025-12-31T23:59:59"
    }, headers=headers).json()
    return task


@pytest.fixture
def sample_reward_type(client, registered_admin):
    headers = {"Authorization": f"Bearer {registered_admin['token']}"}
    rt = client.post("/reward-types", json={"code": "put_test", "name": "PUT Test Reward"},
                    headers=headers).json()
    return rt


@pytest.fixture
def sample_reward(client, registered_user, sample_reward_type):
    headers = {"Authorization": f"Bearer {registered_user['token']}"}
    reward = client.post("/rewards", json={
        "type_id": sample_reward_type["id"],
        "points_amount": 10,
        "reason": "PUT test reward"
    }, headers=headers).json()
    return reward



# Тесты
# /users/me
def test_update_own_user_success(client, registered_user):
    headers = {"Authorization": f"Bearer {registered_user['token']}"}
    new_email = unique_email()
    response = client.put("/users/me", json={
        "email": new_email,
        "first_name": "Updated"
    }, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == new_email
    assert data["first_name"] == "Updated"


def test_update_own_user_duplicate_email(client, registered_user):
    # Создаём второго пользователя
    other_email = unique_email()
    client.post("/register", json={
        "first_name": "Other",
        "last_name": "User",
        "email": other_email,
        "password": "pass123"
    })
    # Пытаемся обновить email на существующий
    headers = {"Authorization": f"Bearer {registered_user['token']}"}
    response = client.put("/users/me", json={"email": other_email}, headers=headers)
    assert response.status_code == 400


# /admin/users/{id}

def test_update_user_by_admin(client, registered_admin, registered_user):
    headers = {"Authorization": f"Bearer {registered_admin['token']}"}
    new_email = unique_email()  # ← Генерируем уникальный!
    response = client.put(f"/admin/users/{registered_user['user']['id']}", json={
        "role": "manager",
        "email": new_email  # Используем уникальный
    }, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["role"] == "manager"
    assert data["email"] == new_email


def test_update_user_by_non_admin_forbidden(client, registered_user):
    headers = {"Authorization": f"Bearer {registered_user['token']}"}
    response = client.put("/admin/users/1", json={"email": "hacker@test.com"}, headers=headers)
    assert response.status_code == 403


def test_update_nonexistent_user_by_admin(client, registered_admin):
    headers = {"Authorization": f"Bearer {registered_admin['token']}"}
    response = client.put("/admin/users/999999", json={"first_name": "Ghost"}, headers=headers)
    assert response.status_code == 404


# /users/{id}/competition
def test_assign_user_to_competition(client, registered_manager, registered_user, sample_competition):
    headers = {"Authorization": f"Bearer {registered_manager['token']}"}
    response = client.put(f"/users/{registered_user['user']['id']}/competition", json={
        "competition_id": sample_competition["id"]
    }, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["cur_comp"] == sample_competition["id"]
    assert data["total_points"] == 0


def test_remove_user_from_competition(client, registered_manager, registered_user, sample_competition):
    # Сначала назначим
    headers = {"Authorization": f"Bearer {registered_manager['token']}"}
    client.put(f"/users/{registered_user['user']['id']}/competition", json={
        "competition_id": sample_competition["id"]
    }, headers=headers)
    # Теперь уберём
    response = client.put(f"/users/{registered_user['user']['id']}/competition", json={
        "competition_id": None
    }, headers=headers)
    assert response.status_code == 200
    assert response.json()["cur_comp"] is None


def test_assign_to_nonexistent_competition(client, registered_manager, registered_user):
    headers = {"Authorization": f"Bearer {registered_manager['token']}"}
    response = client.put(f"/users/{registered_user['user']['id']}/competition", json={
        "competition_id": 999999
    }, headers=headers)
    assert response.status_code == 404


# /task-statuses/{id}
def test_update_task_status_by_admin(client, registered_admin, sample_task_status):
    headers = {"Authorization": f"Bearer {registered_admin['token']}"}
    new_code = "updated_put"
    response = client.put(f"/task-statuses/{sample_task_status['id']}", json={
        "code": new_code,
        "name": "Updated PUT"
    }, headers=headers)
    assert response.status_code == 200
    assert response.json()["code"] == new_code


def test_update_task_status_duplicate_code(client, registered_admin, sample_task_status):
    # Создаём второй статус
    client.post("/task-statuses", json={"code": "conflict", "name": "Conflict"},
                headers={"Authorization": f"Bearer {registered_admin['token']}"})
    # Пытаемся обновить первый на код второго
    headers = {"Authorization": f"Bearer {registered_admin['token']}"}
    response = client.put(f"/task-statuses/{sample_task_status['id']}", json={
        "code": "conflict"
    }, headers=headers)
    assert response.status_code == 400


# /tags/{id}
def test_update_tag_by_admin(client, registered_admin, sample_tag):
    headers = {"Authorization": f"Bearer {registered_admin['token']}"}
    new_name = "Updated PUT Tag"
    response = client.put(f"/tags/{sample_tag['id']}", json={"name": new_name}, headers=headers)
    assert response.status_code == 200
    assert response.json()["name"] == new_name


def test_update_tag_duplicate_name(client, registered_admin, sample_tag):
    # Создаём второй тег
    client.post("/tags", json={"name": "conflict_tag"},
                headers={"Authorization": f"Bearer {registered_admin['token']}"})
    # Пытаемся обновить первый на имя второго
    headers = {"Authorization": f"Bearer {registered_admin['token']}"}
    response = client.put(f"/tags/{sample_tag['id']}", json={"name": "conflict_tag"}, headers=headers)
    assert response.status_code == 400


# /tasks/{id}
def test_update_task_success(client, registered_user, sample_task, sample_task_status):
    headers = {"Authorization": f"Bearer {registered_user['token']}"}
    response = client.put(f"/tasks/{sample_task['id']}", json={
        "title": "Updated PUT Task",
        "description": "Updated description"
    }, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Updated PUT Task"
    assert data["description"] == "Updated description"


def test_update_task_status_to_done_during_competition(
    client, registered_user, sample_competition, registered_admin
):
    # Назначим пользователя на соревнование
    from db import engine
    with engine.connect() as conn:
        conn.execute(text("UPDATE users SET cur_comp = :comp_id WHERE id = :user_id"),
                     {"comp_id": sample_competition["id"], "user_id": registered_user["user"]["id"]})
        conn.commit()

    headers = {"Authorization": f"Bearer {registered_user['token']}"}
    # Создадим статус через админа
    done_status = client.post("/task-statuses", json={"code": "done", "name": "Выполнено"},
                              headers={"Authorization": f"Bearer {registered_admin['token']}"})
    done_id = done_status.json()["id"]

    # Создадим задачу
    task = client.post("/tasks", json={
        "title": "Task for done test",
        "status_id": 1,
        "due_date": "2025-12-31T23:59:59"
    }, headers=headers).json()

    # Обновим статус на done
    response = client.put(f"/tasks/{task['id']}", json={"status_id": done_id}, headers=headers)
    assert response.status_code == 200


def test_update_task_nonexistent(client, registered_user):
    headers = {"Authorization": f"Bearer {registered_user['token']}"}
    response = client.put("/tasks/999999", json={"title": "Ghost"}, headers=headers)
    assert response.status_code == 404


# /reward-types/{id}
def test_update_reward_type_by_admin(client, registered_admin, sample_reward_type):
    headers = {"Authorization": f"Bearer {registered_admin['token']}"}
    response = client.put(f"/reward-types/{sample_reward_type['id']}", json={
        "name": "Updated PUT Reward",
        "description": "Updated description"
    }, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated PUT Reward"


# /rewards/{id}
def test_update_reward_success(client, registered_user, sample_reward):
    headers = {"Authorization": f"Bearer {registered_user['token']}"}
    new_points = 25
    response = client.put(f"/rewards/{sample_reward['id']}", json={
        "points_amount": new_points,
        "reason": "Updated reason"
    }, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["points_amount"] == new_points

    # Проверим что total_points обновились
    me = client.get("/users/me", headers=headers).json()
    assert me["total_points"] == new_points


# /competitions/{id}
def test_update_competition_by_manager(client, registered_manager, sample_competition):
    headers = {"Authorization": f"Bearer {registered_manager['token']}"}
    new_title = "Updated PUT Competition"
    response = client.put(f"/competitions/{sample_competition['id']}", json={
        "title": new_title,
        "description": "Updated description"
    }, headers=headers)
    assert response.status_code == 200
    assert response.json()["title"] == new_title


def test_update_competition_by_user_forbidden(client, registered_user, sample_competition):
    headers = {"Authorization": f"Bearer {registered_user['token']}"}
    response = client.put(f"/competitions/{sample_competition['id']}", json={"title": "Hack"}, headers=headers)
    assert response.status_code == 403
