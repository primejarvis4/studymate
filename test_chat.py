import requests

history = [{"role": "user", "parts": [{"text": "How do plants get energy?"}]}]
response = requests.post("http://127.0.0.1:5000/chat", json={"history": history})
print(response.json())



