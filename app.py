import os
import secrets
from datetime import timedelta
from functools import wraps

from dotenv import load_dotenv
from flask import Flask, request, jsonify, session, send_from_directory

from main import ask_ai, summarize_text, ask_with_context
from db import (
    init_db, save_message, get_all_messages, save_note, get_notes_by_subject,
    save_quiz_result, create_user, get_user_by_username, get_user_by_id,
    claim_unowned_data, record_failed_login, count_recent_failures, clear_failures,
)
from embeddings import get_embedding
from quiz import generate_quiz, calculate_score
from weak_topics import train_model, find_weak_topics
from validators import (  # change to "from input_checks import (" if you renamed the file
    clean_subject, clean_text, clean_difficulty,
    clean_num_questions, check_quiz_submission,
)
from auth import validate_username, validate_password, hash_password, verify_password

load_dotenv()

# set STUDYMATE_ENV=production on the host, never on your own laptop
IS_PRODUCTION = os.getenv("STUDYMATE_ENV") == "production"

app = Flask(__name__)

secret_key = os.getenv("FLASK_SECRET_KEY")
if not secret_key:
    if IS_PRODUCTION:
        raise RuntimeError("FLASK_SECRET_KEY must be set in production.")
    print("WARNING: FLASK_SECRET_KEY is not set in .env. Using a temporary key.")
    secret_key = secrets.token_hex(32)
app.secret_key = secret_key

app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = IS_PRODUCTION      # cookie only travels over HTTPS
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(days=7)
app.config["MAX_CONTENT_LENGTH"] = 1 * 1024 * 1024       # reject request bodies over 1 MB

init_db()

LOGIN_WINDOW_SECONDS = 600     # 10 minutes
LOGIN_MAX_FAILURES = 5         # per username
LOGIN_MAX_FAILURES_PER_IP = 20


def bad_request(message):
    return jsonify({"error": message}), 400


def login_required(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            return jsonify({"error": "Please log in first."}), 401
        return view(*args, **kwargs)
    return wrapper


@app.route("/")
def home():
    return send_from_directory(app.static_folder, "index.html")


# ---------- auth ----------

@app.route("/signup", methods=["POST"])
def signup():
    data = request.get_json(silent=True) or {}

    username, error = validate_username(data.get("username"))
    if error:
        return bad_request(error)

    password = data.get("password")
    error = validate_password(password)
    if error:
        return bad_request(error)

    user_id = create_user(username, hash_password(password))
    if user_id is None:
        return jsonify({"error": "That username is already taken."}), 409

    # the very first account inherits everything saved before accounts existed
    if user_id == 1:
        claim_unowned_data(user_id)

    session.clear()
    session["user_id"] = user_id
    session.permanent = True
    return jsonify({"username": username})


@app.route("/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}
    username = data.get("username")
    password = data.get("password")

    if not isinstance(username, str) or not isinstance(password, str):
        return bad_request("Username and password are required.")

    username = username.strip()
    user_key = "user:" + username.lower()[:50]
    ip_key = "ip:" + (request.remote_addr or "unknown")

    too_many = (
        count_recent_failures(user_key, LOGIN_WINDOW_SECONDS) >= LOGIN_MAX_FAILURES
        or count_recent_failures(ip_key, LOGIN_WINDOW_SECONDS) >= LOGIN_MAX_FAILURES_PER_IP
    )
    if too_many:
        return jsonify({"error": "Too many failed attempts. Please try again in 10 minutes."}), 429

    user = get_user_by_username(username)

    # same message for "no such user" and "wrong password", so nobody can
    # use this form to find out which usernames exist
    if user is None or not verify_password(password, user[2]):
        record_failed_login(user_key)
        record_failed_login(ip_key)
        return jsonify({"error": "Incorrect username or password."}), 401

    clear_failures(user_key)
    session.clear()
    session["user_id"] = user[0]
    session.permanent = True
    return jsonify({"username": user[1]})


@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"status": "logged out"})


@app.route("/me", methods=["GET"])
@login_required
def me():
    user = get_user_by_id(session["user_id"])
    if user is None:
        session.clear()
        return jsonify({"error": "Please log in first."}), 401
    return jsonify({"username": user[1]})


# ---------- study features (each user sees only their own data) ----------

@app.route("/chat", methods=["POST"])
@login_required
def chat():
    user_id = session["user_id"]
    data = request.get_json(silent=True) or {}
    full_history = data.get("history")
    if not isinstance(full_history, list) or len(full_history) == 0:
        return bad_request("History is required.")

    try:
        question = full_history[-1]["parts"][0]["text"]
    except (KeyError, IndexError, TypeError):
        return bad_request("Invalid message format.")

    question, error = clean_text(question, max_length=2000)
    if error:
        return bad_request(error)

    prior_history = full_history[:-1]
    answer, note, score = ask_with_context(question, prior_history, user_id)

    if not answer.startswith("Error:"):
        save_message("user", question, user_id)
        save_message("model", answer, user_id)
    return jsonify({"answer": answer, "used_note": note})


@app.route("/summarize", methods=["POST"])
@login_required
def summarize():
    data = request.get_json(silent=True) or {}
    text, error = clean_text(data.get("text"), max_length=10000)
    if error:
        return bad_request(error)

    summary = summarize_text(text)
    return jsonify({"summary": summary})


@app.route("/add_note", methods=["POST"])
@login_required
def add_note():
    user_id = session["user_id"]
    data = request.get_json(silent=True) or {}
    text, error = clean_text(data.get("text"), max_length=5000)
    if error:
        return bad_request(error)

    subject, error = clean_subject(data.get("subject", "General"))
    if error:
        return bad_request(error)

    embedding = get_embedding(text)
    save_note(text, embedding, subject, user_id)
    return jsonify({"status": "saved"})


@app.route("/generate_quiz", methods=["POST"])
@login_required
def make_quiz():
    user_id = session["user_id"]
    data = request.get_json(silent=True) or {}
    subject, error = clean_subject(data.get("subject"))
    if error:
        return bad_request(error)

    difficulty = clean_difficulty(data.get("difficulty", "medium"))
    num_questions = clean_num_questions(data.get("num_questions", 3))

    notes = get_notes_by_subject(subject, user_id)
    if not notes:
        return jsonify({"error": "No notes found for that subject"})

    combined_content = " ".join(note[1] for note in notes)
    quiz = generate_quiz(combined_content, num_questions, difficulty)
    return jsonify(quiz)


@app.route("/submit_quiz", methods=["POST"])
@login_required
def submit_quiz():
    user_id = session["user_id"]
    data = request.get_json(silent=True) or {}
    questions = data.get("questions")
    user_answers = data.get("user_answers")

    error = check_quiz_submission(questions, user_answers)
    if error:
        return bad_request(error)

    subject, error = clean_subject(data.get("subject"))
    if error:
        return bad_request(error)

    difficulty = clean_difficulty(data.get("difficulty", "medium"))

    score = calculate_score(questions, user_answers)
    save_quiz_result(subject, difficulty, questions, user_answers, score, len(questions), user_id)
    return jsonify({"score": score, "total": len(questions)})


@app.route("/weak_topics", methods=["GET"])
@login_required
def weak_topics():
    user_id = session["user_id"]
    result = train_model(user_id)
    if "error" in result:
        return jsonify({"error": result["error"]}), 400
    topics = find_weak_topics(user_id)
    return jsonify({
        "topics": [
            {"subject": subject, "chance_correct": chance}
            for subject, chance in topics
        ]
    })


if __name__ == "__main__":
    app.run(debug=True)