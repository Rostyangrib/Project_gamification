import pytest
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


def test_protected_endpoint_without_token(client):
    """
    Тест доступа к защищенному эндпоинту без токена.
    Проверяет что запрос к защищенному эндпоинту без токена авторизации возвращает 401 Unauthorized.
    """
    response = client.get("/users/me")
    assert response.status_code == 401


def test_user_cannot_access_admin_endpoint(client, registered_user):
    """
    Тест запрета доступа обычного пользователя к админским эндпоинтам.
    Проверяет что обычный пользователь не может получить доступ к админским эндпоинтам (403 Forbidden).
    """
    headers = {"Authorization": f"Bearer {registered_user['token']}"}
    response = client.get("/users", headers=headers)  # только для админа
    assert response.status_code == 403


def test_name_sql_injection(client):
    """
    Тест защиты от SQL инъекций в поле имени.
    Проверяет что система корректно обрабатывает попытки SQL инъекций в полях регистрации.
    """
    response = client.post("/register", json={
        "first_name": "Test'; DROP TABLE users; --",
        "last_name": "User",
        "email": "injection@test.com",
        "password": "123456"
    })
    assert response.status_code in (201, 400)