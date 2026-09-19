from quiz import build_training_data

data = build_training_data()
print (f"Total rows: {len(data)}")
for row in data:
    print(row)