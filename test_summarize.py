import requests

response = requests.post(
    "http://127.0.0.1:5000/summarize",
    json={"text": "Photosynthesis is the process plants use to convert sunlight into energy. It occurs in chloroplasts and produces oxygen as a byproduct."}
)
print(response.json()["summary"])
