import os
from fastapi.testclient import TestClient
from sqlalchemy import text
from unittest.mock import patch
import pytest

os.environ["TESTING"] = "true"

from database import Base
from db import engine
from main import app

@pytest.fixture(scope="function")
def client():
    Base.metadata.create_all(bind=engine)

    with TestClient(app) as c:
        yield c

    with engine.connect() as conn:
        trans = conn.begin()
        for table in reversed(Base.metadata.sorted_tables):
            conn.execute(text(f"TRUNCATE TABLE {table.name} RESTART IDENTITY CASCADE"))
        trans.commit()


@pytest.fixture(autouse=True)
def mock_ai_analyzer():
    with patch("routes_post.analyze_task") as mock:
        mock.return_value = {"estimated_points": 10, "complexity": "medium", "suggested_tags": []}
        yield mock