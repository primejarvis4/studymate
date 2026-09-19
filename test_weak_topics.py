import pandas as pd
from quiz import build_training_data
from weak_topics import train_model, find_weak_topics

df = pd.DataFrame(build_training_data())
print("Plain accuracy per subject:")
print(df.groupby("subject")["correct"].mean().round(2))

print("\nTraining:", train_model())

print("\nWeak topics (weakest first):")
for subject, chance in find_weak_topics():
    print(f" {subject}: {chance * 100:.0f}% chance of answering correctly")



