# Core - Configuración y Utilidades

## 📋 Configuración (`config.py`)

### Uso básico

```python
from app.core.config import settings

# Acceder a configuración
print(settings.mongodb_uri)
print(settings.elasticsearch_url)
print(settings.ollama_base_url)
```

### Uso con inyección de dependencias (FastAPI)

```python
from fastapi import Depends
from app.core.config import Settings, get_settings

@app.get("/info")
async def info(config: Settings = Depends(get_settings)):
    return {
        "app_name": config.app_name,
        "environment": config.app_env
    }
```

### Variables de entorno requeridas

Las siguientes variables **deben** estar definidas en `.env`:

- `MONGODB_URI`: URI de conexión a MongoDB
- `ELASTICSEARCH_URL`: URL completa de Elasticsearch
- `OLLAMA_BASE_URL`: URL base del servicio Ollama

### Variables con valores por defecto

Estas variables tienen valores por defecto seguros:

- `APP_NAME`: "FeedbackRadar Agentic"
- `APP_ENV`: "development"
- `MONGODB_DB_NAME`: "feedbackradar"
- `ELASTICSEARCH_INDEX`: "feedback"
- `OLLAMA_EMBEDDING_MODEL`: "nomic-embed-text"
- `OLLAMA_CHAT_MODEL`: "llama3.2"

### Verificar configuración

Ejecuta el script de prueba:

```bash
python test_config.py
```

### Características

✅ **Singleton**: Una única instancia durante toda la ejecución  
✅ **Type-safe**: Validación automática con Pydantic  
✅ **Carga automática**: Lee `.env` y variables de entorno del sistema  
✅ **Seguro**: No expone credenciales en logs o representaciones  
✅ **Fail-fast**: Falla al inicio si faltan variables críticas

### Ejemplo de error

Si falta una variable requerida:

```
ValidationError: 1 validation error for Settings
mongodb_uri
  Field required [type=missing, input_value={}, input_type=dict]
```

Esto asegura que la aplicación no arranque con configuración incompleta.