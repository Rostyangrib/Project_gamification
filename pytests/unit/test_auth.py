from auth import get_password_hash, verify_password, create_access_token, SECRET_KEY, ALGORITHM
from jose import jwt

def test_password_hashing():
    """
    Тест хеширования и проверки паролей.
    Проверяет что функция get_password_hash создает хеш, а verify_password корректно проверяет правильный и неправильный пароли.
    """
    password = "secret123"
    hashed = get_password_hash(password)
    assert verify_password(password, hashed) is True
    assert verify_password("wrong", hashed) is False


def test_create_access_token():
    """
    Тест создания JWT токена доступа.
    Проверяет что create_access_token создает валидный JWT токен с правильными полями sub (user_id) и role.
    """
    token = create_access_token("123", "user")
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    assert payload["sub"] == "123"
    assert payload["role"] == "user"