"""
Ejemplo de uso del endpoint POST /feedback/upload usando Python.

Demuestra cómo subir archivos CSV a la API de FeedbackRadar.
"""

import requests
from pathlib import Path


def upload_feedback_files(api_url: str, file_paths: list[str], enable_embeddings: bool = True):
    """
    Sube archivos CSV a la API de feedback.
    
    Args:
        api_url: URL base de la API (ej: http://localhost:8000)
        file_paths: Lista de rutas a archivos CSV
        enable_embeddings: Si True, genera embeddings
        
    Returns:
        Respuesta JSON de la API
    """
    endpoint = f"{api_url}/feedback/upload"
    
    # Preparar archivos para upload
    files = []
    for file_path in file_paths:
        path = Path(file_path)
        if not path.exists():
            print(f"⚠️  Archivo no encontrado: {file_path}")
            continue
        
        files.append(
            ('files', (path.name, open(path, 'rb'), 'text/csv'))
        )
    
    if not files:
        print("❌ No hay archivos para subir")
        return None
    
    # Parámetros
    params = {
        'enable_embeddings': enable_embeddings
    }
    
    print(f"📤 Subiendo {len(files)} archivo(s) a {endpoint}...")
    
    try:
        response = requests.post(endpoint, files=files, params=params)
        response.raise_for_status()
        
        result = response.json()
        
        print("\n✅ Upload completado!")
        print(f"   Archivos procesados: {result['files_processed']}")
        print(f"   Total filas: {result['total_rows']}")
        print(f"   Filas válidas: {result['valid_rows']}")
        print(f"   Filas inválidas: {result['invalid_rows']}")
        print(f"   Insertadas en MongoDB: {result['inserted_rows']}")
        print(f"   Indexadas en Elasticsearch: {result['indexed_rows']}")
        
        if result['errors']:
            print(f"\n⚠️  Errores encontrados ({len(result['errors'])}):")
            for error in result['errors'][:5]:  # Mostrar solo los primeros 5
                print(f"   - {error}")
            if len(result['errors']) > 5:
                print(f"   ... y {len(result['errors']) - 5} más")
        
        return result
        
    except requests.exceptions.ConnectionError:
        print("❌ Error: No se pudo conectar con la API")
        print("   Asegúrate de que la API está corriendo:")
        print("   uvicorn app.main:app --reload")
        return None
        
    except requests.exceptions.HTTPError as e:
        print(f"❌ Error HTTP {e.response.status_code}: {e.response.text}")
        return None
        
    except Exception as e:
        print(f"❌ Error inesperado: {str(e)}")
        return None
    
    finally:
        # Cerrar archivos
        for _, file_tuple in files:
            file_tuple[1].close()


def check_api_health(api_url: str):
    """Verifica el estado de salud de la API."""
    try:
        response = requests.get(f"{api_url}/health")
        response.raise_for_status()
        
        health = response.json()
        print(f"🏥 Estado de la API: {health['status']}")
        print(f"   - API: {health['api']}")
        print(f"   - MongoDB: {health['mongodb']}")
        print(f"   - Elasticsearch: {health['elasticsearch']}")
        
        return health['status'] == 'healthy'
        
    except Exception as e:
        print(f"❌ Error verificando health: {str(e)}")
        return False


def main():
    """Ejemplo principal."""
    API_URL = "http://localhost:8000"
    
    print("="*60)
    print("Ejemplo de Upload de Feedback via API")
    print("="*60)
    print()
    
    # 1. Verificar health
    print("1. Verificando estado de la API...")
    if not check_api_health(API_URL):
        print("\n❌ La API no está disponible. Abortando.")
        return
    print()
    
    # 2. Subir archivos
    print("2. Subiendo archivos CSV...")
    files_to_upload = [
        "data/raw/ejemplo_feedback.csv",
        # Añade más archivos si los tienes
    ]
    
    result = upload_feedback_files(
        api_url=API_URL,
        file_paths=files_to_upload,
        enable_embeddings=True
    )
    
    if result:
        print("\n✅ Proceso completado exitosamente")
    else:
        print("\n❌ El proceso falló")
    
    print()
    print("="*60)
    print("Para ver la documentación interactiva:")
    print(f"  {API_URL}/docs")
    print("="*60)


if __name__ == "__main__":
    main()