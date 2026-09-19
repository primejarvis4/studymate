from auth import validate_username, validate_password, hash_password, verify_password


def test_valid_username():
    assert validate_username("  ram_123 ") == ("ram_123", None)


def test_short_username_rejected():
    username, error = validate_username("ab")
    assert username is None and error is not None


def test_username_with_spaces_or_symbols_rejected():
    assert validate_username("ram kumar")[1] is not None
    assert validate_username("ram@home")[1] is not None


def test_non_text_username_rejected():
    assert validate_username(None)[1] is not None


def test_short_password_rejected():
    assert validate_password("abc123") is not None


def test_all_letters_or_all_digits_rejected():
    assert validate_password("onlyletters") is not None
    assert validate_password("12345678") is not None


def test_good_password_accepted():
    assert validate_password("study2026") is None


def test_hash_is_not_the_password():
    hashed = hash_password("study2026")
    assert hashed != "study2026"
    assert "study2026" not in hashed


def test_correct_password_verifies():
    hashed = hash_password("study2026")
    assert verify_password("study2026", hashed) is True


def test_wrong_password_fails():
    hashed = hash_password("study2026")
    assert verify_password("study2027", hashed) is False


def test_same_password_gets_different_hashes():
    # each hash includes a random "salt", so two users with the same password look different
    assert hash_password("study2026") != hash_password("study2026")