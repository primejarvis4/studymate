from quiz import generate_quiz, calculate_score
from db import init_db, save_quiz_result, get_all_quiz_results

init_db()

note = "Photosynthesis is the process plants use to convert sunlight into energy. It occurs in chloroplasts and produces oxygen as a byproduct."
quiz = generate_quiz(note, num_questions=3, difficulty="medium")
questions = quiz["questions"]

correct_answer = questions[0]["correct_answer"]
fake_answers = [correct_answer, "wrong answer", "wrong answer"]

score = calculate_score(questions, fake_answers)
save_quiz_result("Biology", "medium", questions, fake_answers, score, len(questions))

results = get_all_quiz_results()
for r in results:
    print("Score:", r[5], "/", r[6])