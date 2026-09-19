import requests

response = requests.post("http://127.0.0.1:5000/generate_quiz", json={"subject": "BIology", "difficulty": "medium", "num_questions": 3})
quiz = response.json()
print(quiz)

questions = quiz["questions"]
answers = [q["correct_answer"] for q in questions]

response2 = requests.post("http://127.0.0.1:5000/submit_quiz", json={"questions": questions, "user_answers": answers, "subject": "BIology", "difficulty": "medium"})
print(response2.json())