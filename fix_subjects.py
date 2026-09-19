import shutil
import sqlite3
from datetime import datetime

DB = "studymate.db"
TABLES = ("notes", "quiz_results")


def normalize(subject):
    # same rule the app now uses for new data
    if subject is None:
        return "General"
    cleaned = " ".join(subject.split()).title()
    return cleaned or "General"


def find_changes(cursor, table):
    cursor.execute(f"SELECT id, subject FROM {table}")
    changes = []
    for row_id, subject in cursor.fetchall():
        new_subject = normalize(subject)
        if new_subject != subject:
            changes.append((row_id, subject, new_subject))
    return changes


conn = sqlite3.connect(DB)
cursor = conn.cursor()

all_changes = {}
for table in TABLES:
    all_changes[table] = find_changes(cursor, table)

total = sum(len(rows) for rows in all_changes.values())

if total == 0:
    print("Nothing to fix. All subjects are already clean.")
    conn.close()
else:
    print("These rows will change:\n")
    for table, rows in all_changes.items():
        for row_id, old, new in rows:
            print(f"  {table} #{row_id}: {old!r} -> {new!r}")

    answer = input(f"\nApply {total} change(s)? Type yes or no: ").strip().lower()
    if answer != "yes":
        print("Cancelled. Nothing was changed.")
        conn.close()
    else:
        conn.close()  # close before copying the file
        backup = f"studymate_backup_{datetime.now():%Y%m%d_%H%M%S}.db"
        shutil.copy(DB, backup)
        print(f"Backup saved as {backup}")

        conn = sqlite3.connect(DB)
        cursor = conn.cursor()
        for table, rows in all_changes.items():
            for row_id, old, new in rows:
                cursor.execute(f"UPDATE {table} SET subject = ? WHERE id = ?", (new, row_id))
        conn.commit()
        conn.close()
        print("Done.")