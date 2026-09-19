from embeddings import get_embedding
from similarity import cosine_similarity
from db import get_all_notes


def find_relevant_note(question, user_id=None, threshold=0.65):
    notes = get_all_notes(user_id)  # only this user's notes

    if not notes:
        return None, None

    question_embedding = get_embedding(question)

    best_note = None
    best_score = -1

    for id, content, embedding, subject in notes:
        score = cosine_similarity(question_embedding, embedding)
        if score > best_score:
            best_score = score
            best_note = content

    if best_score < threshold:
        return None, best_score

    return best_note, best_score