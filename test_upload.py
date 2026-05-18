import requests

# URL del endpoint
url = "http://localhost:8000/feedback/upload?enable_embeddings=true"

# Archivo a subir
files = {
    'files': ('integration_test.csv', open('data/raw/integration_test.csv', 'rb'), 'text/csv')
}

# Realizar la petición
print("Subiendo archivo CSV...")
response = requests.post(url, files=files)

# Mostrar resultado
print(f"\nStatus Code: {response.status_code}")
print(f"\nRespuesta:")
print(response.json())