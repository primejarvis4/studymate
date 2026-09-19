from dotenv import load_dotenv
import os
import requests
import json
from db import get_all_quiz_results

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

def generate_quiz(note_content, num_questions=3, difficulty="medium"):
    prompt = f"""Based on this note, create {num_questions} multiple choice questions at {difficulty} difficulty.

Note: {note_content}

Return ONLY valid JSON, no markdown formatting, no extra text, in this exact shape:
{{
  "questions": [
    {{"question": "...", "options": ["...", "...", "...", "..."], "correct_answer": "..."}}
  ]
}}"""

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-flash-lite:generateContent?key={api_key}"
    body = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}]
    }
    try:
        response = requests.post(url, json=body, timeout=45)
        data = response.json()
        text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        return json.loads(text)
    except Exception as e:
        return {"error": str(e)}

def calculate_score(questions, user_answers):
    score = 0
    for i, q in enumerate(questions):
        if user_answers[i] == q["correct_answer"]:
            score += 1
    return score

def build_training_data(user_id=None):
    results = get_all_quiz_results(user_id)
    rows = []
    for id, subject, difficulty, questions, user_answers, score, total in results:
        # the database may give these back as JSON text, so convert if needed
        subject= subject.strip().title()
        if isinstance(questions, str):
            questions = json.loads(questions)
        if isinstance(user_answers, str):
            user_answers = json.loads(user_answers)

        for i, q in enumerate(questions):
            was_correct = 1 if user_answers[i] == q["correct_answer"] else 0
            rows.append({
                "subject": subject,
                "difficulty": difficulty,
                "correct": was_correct,
            })
    return rows