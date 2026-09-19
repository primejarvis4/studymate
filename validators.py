VALID_DIFFICULTIES = ("easy", "medium", "hard")


def clean_subject(value):
    """Returns (cleaned_subject, error). Error is None if fine."""
    if not isinstance(value, str):
        return None, "Subject must be text."
    value = " ".join(value.split())  # removes extra spaces
    if value == "":
        return None, "Subject can't be empty."
    if len(value) > 50:
        return None, "Subject must be 50 characters or less."
    return value.title(), None  # "bIOLOGY" -> "Biology"


def clean_text(value, max_length=5000):
    if not isinstance(value, str):
        return None, "Text is required."
    value = value.strip()
    if value == "":
        return None, "Text can't be empty."
    if len(value) > max_length:
        return None, f"Text must be {max_length} characters or less."
    return value, None


def clean_difficulty(value):
    if value not in VALID_DIFFICULTIES:
        return "medium"
    return value


def clean_num_questions(value, default=3, minimum=1, maximum=15):
    try:
        number = int(value)
    except (ValueError, TypeError):
        return default
    return max(minimum, min(number, maximum))


def check_quiz_submission(questions, user_answers):
    """Returns an error message, or None if the submission is valid."""
    if not isinstance(questions, list) or not isinstance(user_answers, list):
        return "Questions and answers must be lists."
    if len(questions) == 0:
        return "Quiz has no questions."
    if len(questions) != len(user_answers):
        return "Number of answers doesn't match number of questions."
    for q in questions:
        if not isinstance(q, dict) or "correct_answer" not in q:
            return "Each question needs a correct_answer."
    return None