import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock

from app.main import app
from app.db import get_db


fake_user = {
    "name": "Test User",
    "email": "example@example.com",
    "password": "password123"
}
