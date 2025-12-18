# pytests/test_chat.py
import pytest
from unittest.mock import patch
from datetime import datetime, timedelta
import uuid


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
def sample_task_status(client, registered_user):
    # Создаём статус через админа
    admin_email = unique_email()
    admin = client.post("/users", json={
        "first_name": "Admin",
        "last_name": "Test",
        "email": admin_email,
        "password": "adminpass"
    }).json()
    from db import engine
    from sqlalchemy import text
    with engine.connect() as conn:
        conn.execute(text("UPDATE users SET role = 'admin' WHERE id = :user_id"), {"user_id": admin["id"]})
        conn.commit()
    login = client.post("/login", json={"email": admin_email, "password": "adminpass"}).json()
    client.post("/task-statuses", json={"code": "in_progress", "name": "В работе"},
                headers={"Authorization": f"Bearer {login['access_token']}"})
    # Также создаём "todo" на всякий случай
    client.post("/task-statuses", json={"code": "todo", "name": "К выполнению"},
                headers={"Authorization": f"Bearer {login['access_token']}"})


@pytest.fixture
def sample_tag(client, registered_user):
    admin_email = unique_email()
    admin = client.post("/users", json={
        "first_name": "Admin",
        "last_name": "Test",
        "email": admin_email,
        "password": "adminpass"
    }).json()
    from db import engine
    from sqlalchemy import text
    with engine.connect() as conn:
        conn.execute(text("UPDATE users SET role = 'admin' WHERE id = :user_id"), {"user_id": admin["id"]})
        conn.commit()
    login = client.post("/login", json={"email": admin_email, "password": "adminpass"}).json()
    client.post("/tags", json={"name": "срочно"},
                headers={"Authorization": f"Bearer {login['access_token']}"})


# ----------------------------------------
# Тесты
# ----------------------------------------

def test_chat_create_task_success(client, registered_user, sample_task_status, sample_tag):
    headers = {"Authorization": f"Bearer {registered_user['token']}"}

    # Мокаем analyze_task_with_commands
    with patch("routes_chat.analyze_task_with_commands") as mock_cmd:
        mock_cmd.return_value = {
            "reply": "Отлично!",
            "commands": [{
                "action": "create_task",
                "task_data": {
                    "title": "Купить фрукты",
                    "description": "Нужно сходить в магазин и купить яблоки и бананы.",
                    "status_code": "in_progress",
                    "due_date": datetime(2025, 12, 15),
                    "tags": ["срочно"]
                }
            }]
        }

        # Мокаем analyze_task
        with patch("routes_chat.analyze_task") as mock_analyze:
            mock_analyze.return_value = {"estimated_points": 15}

            response = client.post("/chat", json={
                "message": "Создай задачу 'Купить фрукты' на 15.12.2025, статус В работе, тег срочно"
            }, headers=headers)

            assert response.status_code == 200
            data = response.json()
            assert "Задача «Купить фрукты» создана" in data["reply"]
            assert data["task_created"] is not None
            assert data["task_created"]["title"] == "Купить фрукты"


def test_chat_create_task_missing_date(client, registered_user, sample_task_status):
    headers = {"Authorization": f"Bearer {registered_user['token']}"}

    with patch("routes_chat.analyze_task_with_commands") as mock_cmd:
        mock_cmd.return_value = {
            "reply": "Понял!",
            "commands": [{
                "action": "create_task",
                "task_data": {
                    "title": "Купить хлеб",
                    "description": "Сходить в булочную",
                    "status_code": "todo"
                    # нет due_date
                }
            }]
        }

        response = client.post("/chat", json={"message": "Создай задачу на покупку хлеба"}, headers=headers)
        assert response.status_code == 200
        assert "не указана конкретная дата выполнения" in response.json()["reply"]


def test_chat_create_task_no_description(client, registered_user, sample_task_status):
    headers = {"Authorization": f"Bearer {registered_user['token']}"}

    with patch("routes_chat.analyze_task_with_commands") as mock_cmd:
        mock_cmd.return_value = {
            "reply": "Понял!",
            "commands": [{
                "action": "create_task",
                "task_data": {
                    "title": "Купить хлеб",
                    "description": "",  # пустое
                    "status_code": "todo",
                    "due_date": datetime(2025, 12, 15)
                }
            }]
        }

        response = client.post("/chat", json={"message": "Создай задачу на покупку хлеба"}, headers=headers)
        assert response.status_code == 200
        assert "Описание задачи отсутствует" in response.json()["reply"]


def test_chat_create_task_banned_content(client, registered_user, sample_task_status):
    headers = {"Authorization": f"Bearer {registered_user['token']}"}

    with patch("routes_chat.analyze_task_with_commands") as mock_cmd:
        mock_cmd.return_value = {
            "reply": "Хорошо!",
            "commands": [{
                "action": "create_task",
                "task_data": {
                    "title": "Покурить",
                    "description": "Сходить за сигаретами",
                    "status_code": "todo",
                    "due_date": datetime(2025, 12, 15)
                }
            }]
        }

        response = client.post("/chat", json={"message": "Создай задачу 'Покурить'"}, headers=headers)
        assert response.status_code == 200
        assert "не могу создавать задачи, связанные с курением" in response.json()["reply"]


def test_chat_unsupported_action(client, registered_user):
    headers = {"Authorization": f"Bearer {registered_user['token']}"}

    with patch("routes_chat.analyze_task_with_commands") as mock_cmd:
        mock_cmd.return_value = {
            "reply": "Проверю погоду",
            "commands": [{"action": "check_weather"}]
        }

        response = client.post("/chat", json={"message": "Какая погода?"}, headers=headers)
        assert response.status_code == 200
        assert response.json()["reply"] == "Я пока умею только создавать задачи."


def test_chat_no_commands(client, registered_user):
    headers = {"Authorization": f"Bearer {registered_user['token']}"}

    with patch("routes_chat.analyze_task_with_commands") as mock_cmd:
        mock_cmd.return_value = {
            "reply": "Привет! Чем могу помочь?",
            "commands": []
        }

        response = client.post("/chat", json={"message": "Привет"}, headers=headers)
        assert response.status_code == 200
        assert response.json()["reply"] == "Привет! Чем могу помочь?"


def test_chat_create_for_multiple_users(client, registered_user, sample_task_status):
    # Создаём второго пользователя
    other = client.post("/register", json={
        "first_name": "Other",
        "last_name": "User",
        "email": unique_email(),
        "password": "pass123"
    }).json()

    headers = {"Authorization": f"Bearer {registered_user['token']}"}

    with patch("routes_chat.analyze_task_with_commands") as mock_cmd:
        mock_cmd.return_value = {
            "reply": "Создаю задачу!",
            "commands": [{
                "action": "create_task",
                "task_data": {
                    "title": "Общее задание",
                    "description": "Выполнить всем вместе",
                    "status_code": "todo",
                    "due_date": datetime(2025, 12, 20)
                }
            }]
        }

        with patch("routes_chat.analyze_task") as mock_analyze:
            mock_analyze.return_value = {"estimated_points": 10}

            response = client.post("/chat", json={
                "message": "Создай общую задачу",
                "user_ids": [registered_user["user"]["id"], other["id"]]
            }, headers=headers)

            assert response.status_code == 200
            data = response.json()
            assert "для 2 пользователей" in data["reply"]