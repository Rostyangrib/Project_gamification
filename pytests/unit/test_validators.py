import pytest
from pydantic import ValidationError
from schemas import UserCreate

def test_invalid_email():
    with pytest.raises(ValidationError):
        UserCreate(
            first_name="Test",
            last_name="User",
            email="invalid-email",
            password="123456"
        )

def test_short_password():
    with pytest.raises(ValidationError):
        UserCreate(
            first_name="Test",
            last_name="User",
            email="test@example.com",
            password="12"
        )

def test_expired_token_forbidden(client):
    expired_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.xxxxx"
    headers = {"Authorization": f"Bearer {expired_token}"}
    response = client.get("/users/me", headers=headers)
    assert response.status_code == 401