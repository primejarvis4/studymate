import pytest
import db


@pytest.fixture(autouse=True)
def temp_db(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_FILE", str(tmp_path / "test.db"))
    db.init_db()


def test_init_db_can_run_twice():
    db.init_db()  # should not crash or duplicate anything


def test_subject_lookup_ignores_capitals():
    db.save_note("Cells are small", [0.1], "Biology")
    assert len(db.get_notes_by_subject("biology")) == 1
    assert len(db.get_notes_by_subject("BIOLOGY")) == 1


def test_notes_are_separated_by_user():
    db.save_note("Alice note", [0.1], "Biology", user_id=1)
    db.save_note("Bob note", [0.2], "Biology", user_id=2)
    alice_notes = db.get_notes_by_subject("Biology", user_id=1)
    assert len(alice_notes) == 1
    assert alice_notes[0][1] == "Alice note"


def test_no_user_id_returns_everything():
    db.save_note("one", [0.1], "Biology", user_id=1)
    db.save_note("two", [0.2], "Biology", user_id=2)
    assert len(db.get_all_notes()) == 2


def test_quiz_results_keep_seven_columns():
    db.save_quiz_result("Biology", "easy", [{"correct_answer": "A"}], ["A"], 1, 1)
    row = db.get_all_quiz_results()[0]
    assert len(row) == 7
    assert row[3] == [{"correct_answer": "A"}]  # decoded back from JSON


def test_quiz_results_are_separated_by_user():
    db.save_quiz_result("Biology", "easy", [], [], 0, 0, user_id=1)
    db.save_quiz_result("Biology", "easy", [], [], 0, 0, user_id=2)
    assert len(db.get_all_quiz_results(user_id=1)) == 1


def test_duplicate_username_rejected_ignoring_case():
    assert db.create_user("Ram", "hash1") is not None
    assert db.create_user("ram", "hash2") is None


def test_get_user_by_username_ignores_case():
    user_id = db.create_user("Ram", "hash1")
    assert db.get_user_by_username("RAM")[0] == user_id


def test_claim_unowned_data():
    db.save_note("old note", [0.1], "Biology")  # saved before auth, no owner
    db.save_quiz_result("Biology", "easy", [], [], 0, 0)
    user_id = db.create_user("Ram", "hash1")
    claimed = db.claim_unowned_data(user_id)
    assert claimed["notes"] == 1
    assert claimed["quiz_results"] == 1
    assert len(db.get_notes_by_subject("Biology", user_id=user_id)) == 1