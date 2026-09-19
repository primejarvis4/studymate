import pytest
import db
import app as app_module
import weak_topics


@pytest.fixture(autouse=True)
def temp_env(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_FILE", str(tmp_path / "test.db"))
    monkeypatch.setattr(weak_topics, "MODEL_DIR", str(tmp_path))
    db.init_db()


def make_client(username):
    client = app_module.app.test_client()
    response = client.post("/signup", json={"username": username, "password": "study2026"})
    assert response.status_code == 200
    return client


def test_study_routes_require_login():
    anonymous = app_module.app.test_client()
    for method, url in [
        ("post", "/chat"), ("post", "/summarize"), ("post", "/add_note"),
        ("post", "/generate_quiz"), ("post", "/submit_quiz"), ("get", "/weak_topics"),
    ]:
        response = getattr(anonymous, method)(url, json={})
        assert response.status_code == 401, url


def test_notes_are_private(monkeypatch):
    monkeypatch.setattr(app_module, "get_embedding", lambda text: [0.1])
    monkeypatch.setattr(app_module, "generate_quiz", lambda c, n, d: {"questions": [{"question": "q"}]})

    alice = make_client("alice_1")
    bob = make_client("bob_1")

    alice.post("/add_note", json={"text": "Cells are small", "subject": "Biology"})

    assert "questions" in alice.post("/generate_quiz", json={"subject": "Biology"}).get_json()
    assert "No notes found" in bob.post("/generate_quiz", json={"subject": "Biology"}).get_json()["error"]


def test_quiz_results_belong_to_the_submitter():
    alice = make_client("alice_1")
    make_client("bob_1")

    alice.post("/submit_quiz", json={
        "questions": [{"correct_answer": "A"}], "user_answers": ["A"], "subject": "Biology",
    })

    assert len(db.get_all_quiz_results(user_id=1)) == 1
    assert len(db.get_all_quiz_results(user_id=2)) == 0


def test_chat_uses_only_the_callers_notes(monkeypatch):
    seen = []

    def fake_ask(question, history, user_id=None):
        seen.append(user_id)
        return "hi", None, 0.9

    monkeypatch.setattr(app_module, "ask_with_context", fake_ask)

    alice = make_client("alice_1")
    bob = make_client("bob_1")
    payload = {"history": [{"role": "user", "parts": [{"text": "hello"}]}]}

    alice.post("/chat", json=payload)
    bob.post("/chat", json=payload)

    assert seen == [1, 2]
    assert len(db.get_all_messages(user_id=1)) == 2
    assert len(db.get_all_messages(user_id=2)) == 2


def test_weak_topics_only_uses_own_results():
    alice = make_client("alice_1")
    bob = make_client("bob_1")

    db.save_quiz_result(
        "Biology", "easy", [{"correct_answer": "A"}] * 6,
        ["A", "A", "A", "B", "B", "A"], 4, 6, user_id=1,
    )

    response = alice.get("/weak_topics")
    assert response.status_code == 200
    assert [t["subject"] for t in response.get_json()["topics"]] == ["Biology"]

    assert bob.get("/weak_topics").status_code == 400  # bob has no quiz history