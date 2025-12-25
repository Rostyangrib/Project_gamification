# Project_gamification

### Как запустить проект

1. Запустить Docker
2. Запустить ```docker-compose build```
3. Запустить ```docker-compose up```
4. Перейти по адресу 0.0.0.0:8000
5. Откроется само веб-приложение с frontend части


### Запуск без докера

1. ```pip install -r requirements.txt ``` - для установки зависимостей  
2. ```cd frontend``` - перейти в папку frontend  
3. ```npm install``` - установка зависимостей для frontend
4. ```npm run build``` - сборка react
5. ```cd ..``` - возврат в корень проекта
6. ```python start.py``` - запуск приложения

### Тесты производительности locust
```locust -f locust/locustfile.py --host=http://127.0.0.1:8000/```

### Тесты Pytest

```python pytest\generate_full_report.py```  
```start test_reports\full_test_report.html```


### Доступ к админ-панели

1. В адресной строке перейти по 0.0.0.0:8000/docs
2. Откроется страница c /get, /post, /put и /delete запросами
3. Чтобы воспользоваться запросами, необходимо авторизоваться в системе:
    - Если ещё нет профиля, нужно его создать с помощью /register:
      - Нажать "Try It Out"
      - /post запрос /register имеет следующие поля, здесь указываем свои данные
        - {
            "first_name": "string",
            "last_name": "string",
            "email": "user@example.com",
            "password": "string"
          }
      - После нажимаем Execute и создается профиль (по умолчанию с ролью user)
    - Далее нужно получить токен:
      - Воспользуемся /login, в полях указываем почту и пароль от своего профиля
      - Запрос возвращает:
        - {
            "access_token": "your_token",
            "token_type": "bearer"
          }
      - Копируем данный токен
    - В верней части страницы есть кнопка Authorize, где нужно вставить полученный токен и нажать Authorize
    - Поздравляем, мы вошли в админ-панель!

4. После этого можно воспользоваться всеми запросами
