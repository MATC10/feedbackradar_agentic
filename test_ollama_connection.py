import httpx

# Probar conexión directa a Ollama en el puerto 11435
url = "http://localhost:11435/api/embeddings"
payload = {
    "model": "nomic-embed-text",
    "prompt": "test"
}

try:
    with httpx.Client(timeout=10.0) as client:
        response = client.post(url, json=payload)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
except Exception as e:
    print(f"Error: {e}")