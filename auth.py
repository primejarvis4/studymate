import re
from werkzeug.security import generate_password_hash, check_password_hash

USERNAME_PATTERN = re.compile(r"^[A-Za-z0-9_]{3,20}$")


def validate_username(username):
    """Returns (clean_username, error)."""
    if not isinstance(username, str):
        return None, "Username is required."
    username = username.strip()
    if not USERNAME_PATTERN.match(username):
        return None, "Username must be 3-20 characters: letters, numbers, or underscore."
    return username, None


def validate_password(password):
    """Returns an error message, or None if the password is acceptable."""
    if not isinstance(password, str):
        return "Password is required."
    if len(password) < 8:
        return "Password must be at least 8 characters."
    if len(password) > 128:
        return "Password must be 128 characters or less."
    if password.isdigit() or password.isalpha():
        return "Password must mix letters and numbers."
    return None


def hash_password(password):
    return generate_password_hash(password)


def verify_password(password, password_hash):
    return check_password_hash(password_hash, password)