from db import init_db, save_note, get_all_notes
from embeddings import get_embedding

init_db()

text = "Photosynthesis is the process that plants use."
embedding = get_embedding(text)
save_note(text, embedding)

notes = get_all_notes()
for id, content, emb in notes:
    print(id, content, "-embedding length:", len(emb))