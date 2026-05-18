import requests

# Verificar qué configuración está usando el backend
response = requests.get("http://localhost:8000/")
print("Backend respondiendo:", response.json())

# Intentar ver si hay algún endpoint de debug
try:
    # Probar si podemos ver la configuración
    import httpx
    print("\nProbando conexión directa a Ollama desde aquí:")
    print("Puerto 11434:", end=" ")
    try:
        r = httpx.get("http://localhost:11434/api/tags", timeout=2)
        print(f"OK - {len(r.json()['models'])} modelos")
    except:
        print("FALLO")
    
    print("Puerto 11435:", end=" ")
    try:
        r = httpx.get("http://localhost:11435/api/tags", timeout=2)
        models = r.json()['models']
        print(f"OK - {len(models)} modelos: {[m['name'] for m in models]}")
    except:
        print("FALLO")
except Exception as e:
    print(f"Error: {e}")