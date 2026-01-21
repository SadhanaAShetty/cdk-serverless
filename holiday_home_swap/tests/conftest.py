import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock

from holiday_home_swap.api import create_app
from holiday_home_swap.app.db import get_db


fake_user = {
    "name": "Test User",
    "email": "example@example.com",
    "password": "password123"
}
