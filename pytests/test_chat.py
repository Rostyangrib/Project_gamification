# Импорты необходимых библиотек для тестирования
import pytest  # Фреймворк для тестирования Python
from unittest.mock import patch  # Для мокирования (подмены) функций в тестах
from datetime import datetime  # Для работы с датами и временем
import uuid  # Для генерации уникальных идентификаторов


def unique_email():
    """
    Генерирует уникальный email для каждого теста.
    Используется UUID для гарантии уникальности.
    """
    return f"test_{uuid.uuid4()}@example.com"

@pytest.fixture
def registered_user(client):
    """
    Фикстура для создания и регистрации тестового пользователя.
    Возвращает данные пользователя и его токен авторизации.
    
    Args:
        client: Тестовый HTTP клиент FastAPI
    
    Returns:
        dict: {"user": данные пользователя, "token": JWT токен}
    """
    # Генерируем уникальный email для избежания конфликтов между тестами
    email = unique_email()
    # Задаем пароль для пользователя
    password = "userpass"
    # Регистрируем нового пользователя через POST /register
    res = client.post("/register", json={
        "first_name": "User",  # Имя пользователя
        "last_name": "Test",  # Фамилия пользователя
        "email": email,  # Уникальный email
        "password": password  # Пароль пользователя
    })
    # Извлекаем данные зарегистрированного пользователя из ответа
    user = res.json()
    # Выполняем вход под созданным пользователем для получения токена
    login_res = client.post("/login", json={"email": email, "password": password})
    # Извлекаем JWT токен из ответа
    token = login_res.json()["access_token"]
    # Возвращаем данные пользователя и токен для использования в тестах
    return {"user": user, "token": token}


@pytest.fixture
def sample_task_status(client, registered_user):
    """
    Фикстура для создания тестовых статусов задач.
    Создает админа и через него создает статусы "В работе" и "К выполнению".
    
    Args:
        client: Тестовый HTTP клиент FastAPI
        registered_user: Фикстура зарегистрированного пользователя (для зависимости)
    """
    # Создаём уникальный email для администратора
    admin_email = unique_email()
    # Создаем нового пользователя через POST /users
    admin = client.post("/users", json={
        "first_name": "Admin",  # Имя администратора
        "last_name": "Test",  # Фамилия администратора
        "email": admin_email,  # Уникальный email
        "password": "adminpass"  # Пароль администратора
    }).json()
    
    # Импортируем движок БД для прямого SQL запроса
    from db import engine
    # Импортируем text для выполнения SQL команд
    from sqlalchemy import text
    
    # Открываем соединение с БД для изменения роли пользователя
    with engine.connect() as conn:
        # Обновляем роль созданного пользователя на 'admin' напрямую через SQL
        # (так как через API нельзя создать админа сразу)
        conn.execute(text("UPDATE users SET role = 'admin' WHERE id = :user_id"), {"user_id": admin["id"]})
        # Сохраняем изменения в БД
        conn.commit()
    
    # Выполняем вход под администратором для получения токена
    login = client.post("/login", json={"email": admin_email, "password": "adminpass"}).json()
    
    # Создаем статус "В работе" (in_progress) через API админа
    client.post("/task-statuses", json={"code": "in_progress", "name": "В работе"},
                headers={"Authorization": f"Bearer {login['access_token']}"})
    
    # Создаем статус "К выполнению" (todo) через API админа
    client.post("/task-statuses", json={"code": "todo", "name": "К выполнению"},
                headers={"Authorization": f"Bearer {login['access_token']}"})


@pytest.fixture
def sample_tag(client, registered_user):
    """
    Фикстура для создания тестового тега "срочно".
    Создает админа и через него создает тег для задач.
    
    Args:
        client: Тестовый HTTP клиент FastAPI
        registered_user: Фикстура зарегистрированного пользователя (для зависимости)
    """
    # Генерируем уникальный email для администратора
    admin_email = unique_email()
    # Создаем нового пользователя через POST /users
    admin = client.post("/users", json={
        "first_name": "Admin",  # Имя администратора
        "last_name": "Test",  # Фамилия администратора
        "email": admin_email,  # Уникальный email
        "password": "adminpass"  # Пароль администратора
    }).json()
    
    # Импортируем движок БД для прямого SQL запроса
    from db import engine
    # Импортируем text для выполнения SQL команд
    from sqlalchemy import text
    
    # Открываем соединение с БД для изменения роли
    with engine.connect() as conn:
        # Обновляем роль пользователя на 'admin' через SQL
        conn.execute(text("UPDATE users SET role = 'admin' WHERE id = :user_id"), {"user_id": admin["id"]})
        # Фиксируем изменения в базе данных
        conn.commit()
    
    # Выполняем вход под администратором для получения JWT токена
    login = client.post("/login", json={"email": admin_email, "password": "adminpass"}).json()
    
    # Создаем тег "срочно" через API с токеном администратора
    client.post("/tags", json={"name": "срочно"},
                headers={"Authorization": f"Bearer {login['access_token']}"})


# ========== ТЕСТЫ ==========

def test_chat_create_task_success(client, registered_user, sample_task_status, sample_tag):
    """
    Тест успешного создания задачи через чат-интерфейс.
    Проверяет полный цикл: парсинг запроса, создание задачи, возврат ответа.
    """
    # Формируем заголовок с JWT токеном для аутентификации запроса
    headers = {"Authorization": f"Bearer {registered_user['token']}"}

    # Мокаем функцию analyze_task_with_commands (первый вызов AI - парсинг команды)
    with patch("routes_chat.analyze_task_with_commands") as mock_cmd:
        # Задаем возвращаемое значение мока - структурированная команда создания задачи
        mock_cmd.return_value = {
            "reply": "Отлично!",  # Текстовый ответ для пользователя
            "commands": [{  # Массив команд для выполнения
                "action": "create_task",  # Тип команды - создание задачи
                "task_data": {  # Данные задачи
                    "title": "Купить фрукты",  # Название задачи
                    "description": "Нужно сходить в магазин и купить яблоки и бананы.",  # Описание
                    "status_code": "in_progress",  # Код статуса задачи
                    "due_date": datetime(2025, 12, 15),  # Срок выполнения
                    "tags": ["срочно"],  # Теги задачи
                    "estimated_points": 15  # ВАЖНО: добавляем оценку сложности из AI
                }
            }]
        }

        # Отправляем POST запрос к чат API с сообщением на естественном языке
        response = client.post("/chat", json={
            "message": "Создай задачу 'Купить фрукты' на 15.12.2025, статус В работе, тег срочно"
        }, headers=headers)

        # Проверяем что ответ успешный (HTTP 200)
        assert response.status_code == 200
        # Извлекаем JSON данные из ответа
        data = response.json()
        # Проверяем что в ответе есть подтверждение создания задачи
        assert "Задача «Купить фрукты» создана" in data["reply"]
        # Проверяем что задача действительно была создана
        assert data["task_created"] is not None
        # Проверяем что название задачи совпадает с ожидаемым
        assert data["task_created"]["title"] == "Купить фрукты"


def test_chat_create_task_missing_date(client, registered_user, sample_task_status):
    """
    Тест проверки валидации отсутствующей даты выполнения.
    Система должна отклонить создание задачи без указания срока.
    """
    # Формируем заголовок с токеном авторизации
    headers = {"Authorization": f"Bearer {registered_user['token']}"}

    # Мокаем функцию парсинга команд AI
    with patch("routes_chat.analyze_task_with_commands") as mock_cmd:
        # AI распарсил команду, но дата отсутствует (due_date не указан)
        mock_cmd.return_value = {
            "reply": "Понял!",  # Ответ от AI
            "commands": [{  # Команда создания задачи
                "action": "create_task",
                "task_data": {
                    "title": "Купить хлеб",  # Название задачи
                    "description": "Сходить в булочную",  # Описание задачи
                    "status_code": "todo",  # Статус задачи
                    "estimated_points": 10  # Оценка сложности
                    # ВАЖНО: нет поля due_date - это должно вызвать ошибку валидации
                }
            }]
        }

        # Отправляем запрос на создание задачи без указания даты
        response = client.post("/chat", json={"message": "Создай задачу на покупку хлеба"}, headers=headers)
        # Проверяем что запрос обработан (HTTP 200, но задача не создана)
        assert response.status_code == 200
        # Проверяем что в ответе есть сообщение об отсутствии даты
        assert "не указана конкретная дата выполнения" in response.json()["reply"]


def test_chat_create_task_no_description(client, registered_user, sample_task_status):
    """
    Тест проверки валидации пустого описания задачи.
    Система должна требовать осмысленное описание для всех задач.
    """
    # Заголовок с JWT токеном для аутентификации
    headers = {"Authorization": f"Bearer {registered_user['token']}"}

    # Мокаем функцию парсинга AI команды
    with patch("routes_chat.analyze_task_with_commands") as mock_cmd:
        # AI распарсил команду, но description пустой
        mock_cmd.return_value = {
            "reply": "Понял!",  # Ответ AI на запрос пользователя
            "commands": [{  # Команда на создание задачи
                "action": "create_task",
                "task_data": {
                    "title": "Купить хлеб",  # Название есть
                    "description": "",  # ВАЖНО: пустое описание - должно вызвать ошибку
                    "status_code": "todo",  # Статус задачи
                    "due_date": datetime(2025, 12, 15),  # Дата указана
                    "estimated_points": 10  # Оценка сложности
                }
            }]
        }

        # Отправляем запрос на создание задачи с пустым описанием
        response = client.post("/chat", json={"message": "Создай задачу на покупку хлеба"}, headers=headers)
        # Проверяем что запрос обработан (HTTP 200)
        assert response.status_code == 200
        # Проверяем что система отклонила задачу из-за отсутствия описания
        assert "Описание задачи отсутствует" in response.json()["reply"]


def test_chat_create_task_banned_content(client, registered_user, sample_task_status):
    """
    Тест проверки фильтрации запрещенного контента.
    Система должна отклонять задачи, связанные с курением и другими вредными привычками.
    """
    # Заголовок с токеном аутентификации
    headers = {"Authorization": f"Bearer {registered_user['token']}"}

    # Мокаем AI парсер команд
    with patch("routes_chat.analyze_task_with_commands") as mock_cmd:
        # AI может распарсить команду, но backend должен отфильтровать запрещенный контент
        mock_cmd.return_value = {
            "reply": "Хорошо!",  # AI ответил положительно (пока не знает о запрете)
            "commands": [{  # Команда создания задачи
                "action": "create_task",
                "task_data": {
                    "title": "Покурить",  # ЗАПРЕЩЕННОЕ слово - содержит "покур"
                    "description": "Сходить за сигаретами",  # ЗАПРЕЩЕННОЕ слово - "сигарет"
                    "status_code": "todo",  # Статус задачи
                    "due_date": datetime(2025, 12, 15),  # Дата выполнения
                    "estimated_points": 5  # Оценка сложности
                }
            }]
        }

        # Отправляем запрос с запрещенным контентом
        response = client.post("/chat", json={"message": "Создай задачу 'Покурить'"}, headers=headers)
        # Проверяем что запрос обработан (HTTP 200)
        assert response.status_code == 200
        # Проверяем что система отклонила задачу из-за запрещенного контента
        assert "не могу создавать задачи, связанные с курением" in response.json()["reply"]


def test_chat_unsupported_action(client, registered_user):
    """
    Тест обработки неподдерживаемых команд.
    Система должна корректно сообщать что поддерживает только создание задач.
    """
    # Заголовок с JWT токеном для авторизации
    headers = {"Authorization": f"Bearer {registered_user['token']}"}

    # Мокаем AI парсер - он возвращает неподдерживаемую команду
    with patch("routes_chat.analyze_task_with_commands") as mock_cmd:
        # AI распознал команду, но это не create_task
        mock_cmd.return_value = {
            "reply": "Проверю погоду",  # Ответ AI
            "commands": [{"action": "check_weather"}]  # ВАЖНО: неподдерживаемая команда
        }

        # Отправляем запрос который не связан с созданием задач
        response = client.post("/chat", json={"message": "Какая погода?"}, headers=headers)
        # Проверяем что запрос обработан успешно (HTTP 200)
        assert response.status_code == 200
        # Проверяем что система вернула сообщение о том, что умеет только создавать задачи
        assert response.json()["reply"] == "Я пока умею только создавать задачи."


def test_chat_no_commands(client, registered_user):
    """
    Тест обработки обычных сообщений без команд.
    Система должна корректно отвечать на приветствия и общие вопросы.
    """
    # Заголовок с токеном аутентификации
    headers = {"Authorization": f"Bearer {registered_user['token']}"}

    # Мокаем AI парсер - он возвращает только ответ без команд
    with patch("routes_chat.analyze_task_with_commands") as mock_cmd:
        # AI распознал что это просто приветствие, не команда
        mock_cmd.return_value = {
            "reply": "Привет! Чем могу помочь?",  # Дружелюбный ответ
            "commands": []  # ВАЖНО: пустой массив команд - нет действий для выполнения
        }

        # Отправляем простое приветствие
        response = client.post("/chat", json={"message": "Привет"}, headers=headers)
        # Проверяем что запрос успешен (HTTP 200)
        assert response.status_code == 200
        # Проверяем что система вернула правильный ответ без попытки создания задачи
        assert response.json()["reply"] == "Привет! Чем могу помочь?"


def test_chat_create_for_multiple_users(client, registered_user, sample_task_status):
    """
    Тест создания одной задачи для нескольких пользователей одновременно.
    Система должна создать копию задачи для каждого указанного пользователя.
    """
    # Создаём второго пользователя для теста
    other = client.post("/register", json={
        "first_name": "Other",  # Имя второго пользователя
        "last_name": "User",  # Фамилия второго пользователя
        "email": unique_email(),  # Уникальный email
        "password": "pass123"  # Пароль
    }).json()

    # Заголовок с токеном первого пользователя (инициатор создания задачи)
    headers = {"Authorization": f"Bearer {registered_user['token']}"}

    # Мокаем AI парсер команды
    with patch("routes_chat.analyze_task_with_commands") as mock_cmd:
        # AI распарсил команду создания задачи
        mock_cmd.return_value = {
            "reply": "Создаю задачу!",  # Подтверждение от AI
            "commands": [{  # Команда создания задачи
                "action": "create_task",
                "task_data": {
                    "title": "Общее задание",  # Название задачи
                    "description": "Выполнить всем вместе",  # Описание задачи
                    "status_code": "todo",  # Статус задачи
                    "due_date": datetime(2025, 12, 20),  # Срок выполнения
                    "estimated_points": 10  # ВАЖНО: оценка сложности уже в task_data
                }
            }]
        }

        # Отправляем запрос на создание задачи с указанием нескольких получателей
        response = client.post("/chat", json={
            "message": "Создай общую задачу",  # Сообщение пользователя
            "user_ids": [registered_user["user"]["id"], other["id"]]  # ВАЖНО: ID двух пользователей
        }, headers=headers)

        # Проверяем что запрос успешен (HTTP 200)
        assert response.status_code == 200
        # Извлекаем данные ответа
        data = response.json()
        # Проверяем что в ответе указано количество пользователей (2)
        assert "для 2 пользователей" in data["reply"]


def test_chat_rate_limit_error(client, registered_user, sample_task_status):
    """
    Тест обработки ошибки rate limit от Groq API.
    Проверяет что при ошибке "Too many requests" (429) API возвращает корректный HTTP 429 статус,
    и тест фиксирует эту ошибку как неудачный.
    """
    # Импортируем исключение для rate limit
    from ml.ai_analyzer import GroqRateLimitError
    
    # Заголовок с токеном авторизации
    headers = {"Authorization": f"Bearer {registered_user['token']}"}

    # Мокаем analyze_task_with_commands чтобы он выбрасывал ошибку rate limit
    with patch("routes_chat.analyze_task_with_commands") as mock_cmd:
        # Имитируем ошибку rate limit после исчерпания всех retry
        mock_cmd.side_effect = GroqRateLimitError("Groq API rate limit exceeded after 3 attempts")

        # Отправляем запрос к чат API
        response = client.post("/chat", json={
            "message": "Создай задачу 'Тестовая задача'"
        }, headers=headers)

        # ВАЖНО: Проверяем что API вернул HTTP 429 (Too Many Requests)
        # Это означает, что ошибка была правильно обработана и проброшена
        assert response.status_code == 429
        # Проверяем что в ответе есть сообщение об ошибке
        assert "Слишком много запросов" in response.json()["detail"]


def test_chat_groq_api_error(client, registered_user, sample_task_status):
    """
    Тест обработки других ошибок Groq API.
    Проверяет что при других ошибках API (не rate limit) возвращается HTTP 503.
    """
    # Импортируем исключение для ошибок API
    from ml.ai_analyzer import GroqAPIError
    
    # Заголовок с токеном авторизации
    headers = {"Authorization": f"Bearer {registered_user['token']}"}

    # Мокаем analyze_task_with_commands чтобы он выбрасывал ошибку API
    with patch("routes_chat.analyze_task_with_commands") as mock_cmd:
        # Имитируем ошибку API
        mock_cmd.side_effect = GroqAPIError("Groq API error 500 after 3 attempts")

        # Отправляем запрос к чат API
        response = client.post("/chat", json={
            "message": "Создай задачу 'Тестовая задача'"
        }, headers=headers)

        # Проверяем что API вернул HTTP 503 (Service Unavailable)
        assert response.status_code == 503
        # Проверяем что в ответе есть сообщение об ошибке
        assert "Ошибка при обращении к AI сервису" in response.json()["detail"]
