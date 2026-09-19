from db import get_all_notes

notes=get_all_notes()
for n in notes:
    print(f"id={n[0]}, subject='{n[3]}'")