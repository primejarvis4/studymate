import os
import joblib
import pandas as pd
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder
from sklearn.linear_model import LogisticRegression
from quiz import build_training_data

MODEL_DIR = os.getenv("STUDYMATE_MODEL_DIR", ".")


def model_path(user_id):
    suffix = "all" if user_id is None else f"user{int(user_id)}"
    return os.path.join(MODEL_DIR, f"weak_topic_model_{suffix}.joblib")


def train_model(user_id=None):
    rows = build_training_data(user_id)
    if len(rows) < 5:
        return {"error": "Need at least 5 answered questions to train."}

    df = pd.DataFrame(rows)
    if df["correct"].nunique() < 2:
        return {"error": "Need both right and wrong answers to learn from."}

    X = df[["subject", "difficulty"]]
    y = df["correct"]

    model = Pipeline([
        ("encode", ColumnTransformer([
            ("cat", OneHotEncoder(handle_unknown="ignore"), ["subject", "difficulty"])
        ])),
        ("clf", LogisticRegression()),
    ])
    model.fit(X, y)
    joblib.dump(model, model_path(user_id))
    return {"trained_on": len(df)}


def find_weak_topics(user_id=None, difficulty="medium"):
    rows = build_training_data(user_id)
    subjects = sorted({r["subject"] for r in rows})
    if not subjects:
        return []

    model = joblib.load(model_path(user_id))
    X = pd.DataFrame({"subject": subjects, "difficulty": difficulty})
    probs = model.predict_proba(X)[:, 1]  # chance of answering correctly

    results = [(s, round(float(p), 2)) for s, p in zip(subjects, probs)]
    results.sort(key=lambda pair: pair[1])  # weakest first
    return results