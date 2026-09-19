import pytest
import db
import app as app_module


@pytest.fixture(autouse=True)
def temp_db(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_FILE", str(tmp_path / "test.db"))
    db.init_db()


@pytest.fixture
def client():
    return app_module.app.test_client()


def signup(client, username="ram_123", password="study2026"):
    return client.post("/signup", json={"username": username, "password": password})


def test_signup_logs_you_in(client):
    response = signup(client)
    assert response.status_code == 200
    assert client.get("/me").get_json() == {"username": "ram_123"}


def test_signup_rejects_weak_password(client):
    assert signup(client, password="short1").status_code == 400
    assert signup(client, password="onlyletters").status_code == 400


def test_signup_rejects_bad_username(client):
    assert signup(client, username="a b").status_code == 400
    assert signup(client, username="ab").status_code == 400


def test_signup_rejects_duplicate_username_ignoring_case(client):
    assert signup(client, username="Ram_123").status_code == 200
    other = app_module.app.test_client()
    assert signup(other, username="ram_123").status_code == 409


def test_login_with_correct_password(client):
    signup(client)
    client.post("/logout")
    response = client.post("/login", json={"username": "RAM_123", "password": "study2026"})
    assert response.status_code == 200
    assert client.get("/me").status_code == 200


def test_wrong_password_and_unknown_user_look_the_same(client):
    signup(client)
    client.post("/logout")
    wrong = client.post("/login", json={"username": "ram_123", "password": "wrongpass1"})
    unknown = client.post("/login", json={"username": "nobody", "password": "study2026"})
    assert wrong.status_code == 401
    assert unknown.status_code == 401
    assert wrong.get_json() == unknown.get_json()


def test_me_requires_login(client):
    assert client.get("/me").status_code == 401


def test_logout_ends_the_session(client):
    signup(client)
    client.post("/logout")
    assert client.get("/me").status_code == 401


def test_first_signup_claims_old_data(client):
    db.save_note("old note", [0.1], "Biology")  # saved before accounts existed
    signup(client)
    assert len(db.get_notes_by_subject("Biology", user_id=1)) == 1


def test_password_is_not_stored_in_plain_text(client):
    signup(client)
    stored = db.get_user_by_username("ram_123")[2]
    assert stored != "study2026"
    assert "study2026" not in stored