from quiz import generate_quiz

note = "Photosynthesis is the process plants use to convert sunlight into energy.It occurs in chloroplasts and produces oxygen as a byproduct."
quiz = generate_quiz(note, num_questions=3, difficulty="medium")
print(quiz)