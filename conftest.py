import pytest
import db


@pytest.fixture(autouse=True)
def never_touch_the_real_database(monkeypatch):
    monkeypatch.setattr(db, "DATABASE_URL", None)