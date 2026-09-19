import requests

response = requests.post("http://127.0.0.1:5000/add_note", json={"text":"Newton's second law states that force equals mass times acceleration."})
print(response.json())