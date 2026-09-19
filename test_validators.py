from validators import (
    clean_subject, clean_text, clean_difficulty,
    clean_num_questions, check_quiz_submission,
)


def test_subject_typo_is_fixed():
    assert clean_subject("  bIOLOGY ") == ("Biology", None)


def test_subject_extra_spaces_collapse():
    assert clean_subject("world    history") == ("World History", None)


def test_empty_subject_rejected():
    subject, error = clean_subject("   ")
    assert subject is None and error is not None


def test_long_subject_rejected():
    subject, error = clean_subject("a" * 51)
    assert subject is None and error is not None


def test_non_text_subject_rejected():
    subject, error = clean_subject(123)
    assert subject is None and error is not None


def test_empty_text_rejected():
    text, error = clean_text("")
    assert text is None and error is not None


def test_bad_difficulty_becomes_medium():
    assert clean_difficulty("impossible") == "medium"
    assert clean_difficulty("hard") == "hard"


def test_question_count_limits():
    assert clean_num_questions(500) == 15
    assert clean_num_questions(0) == 1
    assert clean_num_questions("abc") == 3
    assert clean_num_questions("5") == 5


def test_submission_length_mismatch():
    questions = [{"correct_answer": "A"}, {"correct_answer": "B"}]
    assert check_quiz_submission(questions, ["A"]) is not None


def test_valid_submission():
    questions = [{"correct_answer": "A"}]
    assert check_quiz_submission(questions, ["A"]) is None