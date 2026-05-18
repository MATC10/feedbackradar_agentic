#!/bin/bash

# Ejemplo de uso del endpoint POST /feedback/upload
# 
# Asegúrate de que:
# 1. Los servicios Docker están corriendo: docker-compose up -d
# 2. La API FastAPI está corriendo: uvicorn app.main:app --reload
# 3. Tienes archivos CSV en data/raw/

echo "==================================================="
echo "Ejemplo de upload de feedback via API"
echo "==================================================="
echo ""

# URL de la API
API_URL="http://localhost:8000"

# 1. Verificar que la API está corriendo
echo "1. Verificando health de la API..."
curl -s "${API_URL}/health" | python -m json.tool
echo ""
echo ""

# 2. Subir un archivo CSV
echo "2. Subiendo archivo CSV de ejemplo..."
curl -X POST "${API_URL}/feedback/upload" \
  -H "accept: application/json" \
  -F "files=@data/raw/ejemplo_feedback.csv" \
  | python -m json.tool
echo ""
echo ""

# 3. Subir múltiples archivos (si existen)
# echo "3. Subiendo múltiples archivos..."
# curl -X POST "${API_URL}/feedback/upload" \
#   -H "accept: application/json" \
#   -F "files=@data/raw/archivo1.csv" \
#   -F "files=@data/raw/archivo2.csv" \
#   | python -m json.tool

echo "==================================================="
echo "Ejemplo completado"
echo "==================================================="
echo ""
echo "Para ver la documentación interactiva:"
echo "  http://localhost:8000/docs"