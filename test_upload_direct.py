import requests
import os

# Forzar las variables de entorno antes de importar la app
os.environ['OLLAMA_BASE_URL'] = 'http://localhost:11435'
os.environ['OLLAMA_EMBEDDING_MODEL'] = 'nomic-embed-text'

# URL del endpoint
url = "http://localhost:8000/feedback/upload?enable_embeddings=true"

# Archivo a subir
files = {
    'files': ('integration_test.csv', open('data/raw/integration_test.csv', 'rb'), 'text/csv')
}

# Realizar la petición
print("Subiendo archivo CSV con embeddings habilitados...")
print(f"Ollama configurado en: {os.environ['OLLAMA_BASE_URL']}")
print(f"Modelo: {os.environ['OLLAMA_EMBEDDING_MODEL']}")
print()

response = requests.post(url, files=files)

# Mostrar resultado
print(f"Status Code: {response.status_code}")
print(f"\nRespuesta:")
import json
print(json.dumps(response.json(), indent=2))