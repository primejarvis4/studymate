from dotenv import load_dotenv
import os
import requests
from retrieval import find_relevant_note

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")


def ask_ai(history):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-flash-lite:generateContent?key={api_key}"
    body = {
        "system_instruction": {"parts": {"text": "Answer in plain text only,no markdown formatting."}},
        "contents": history,
    }
    try:
        response = requests.post(url, json=body, timeout=45)
        data = response.json()
        return data["candidates"][0]["content"]["parts"][0]["text"]
    except Exception as e:
        return f"Error: {e}"


def summarize_text(text):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-flash-lite:generateContent?key={api_key}"
    body = {
        "system_instruction": {"parts": {"text": "Summarize concisely, in plain text, no markdown formatting."}},
        "contents": [{"role": "user", "parts": [{"text": text}]}]
    }
    try:
        response = requests.post(url, json=body, timeout=45)
        data = response.json()
        return data["candidates"][0]["content"]["parts"][0]["text"]
    except Exception as e:
        return f"Error: {e}"


def ask_with_context(question, history, user_id=None):
    # only searches this user's notes; returns (answer, note_used, similarity_score)
    note, score = find_relevant_note(question, user_id)
    if note:
        augmented_question = f"Use the following note to help answer if it's relevant:\n\nNote: {note}\n\nQuestion: {question}"
    else:
        augmented_question = question

    temp_history = history + [{"role": "user", "parts": [{"text": augmented_question}]}]
    answer = ask_ai(temp_history)

    history.append({"role": "user", "parts": [{"text": question}]})
    history.append({"role": "model", "parts": [{"text": answer}]})

    return answer, note, score


if __name__ == "__main__":
    print("StudyMate is ready. Type 'quit' to exit.")
    history = []
    question = ""
    while question.strip().lower() != "quit":
        question = input("\nYou: ")
        if question.strip().lower() == "quit":
            break
        elif question.strip().lower().startswith("summarize:"):
            text_to_summarize = question.split(":", 1)[1].strip()
            summary = summarize_text(text_to_summarize)
            print(f"StudyMate (summary): {summary}")
        else:
            history.append({"role": "user", "parts": [{"text": question}]})
            answer = ask_ai(history)
            print(f"StudyMate: {answer}")
            if not answer.startswith("Error:"):
                history.append({"role": "model", "parts": [{"text": answer}]})