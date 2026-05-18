"""
Ejemplo de uso de la capa de ingesta de feedback.

Este script demuestra cómo usar IngestionService para ingestar
feedback desde archivos CSV.
"""

import asyncio
from pathlib import Path

from app.ingestion import IngestionService
from app.databases import MongoDBClient


async def main():
    """Ejemplo principal de ingesta"""
    
    # Inicializar servicio de ingesta
    service = IngestionService()
    
    # Ruta al CSV de ejemplo
    csv_file = Path("data/raw/ejemplo_feedback.csv")
    
    print(f"📁 Ingesta de: {csv_file}")
    print("-" * 60)
    
    # Opción 1: Validar sin persistir (dry-run)
    print("\n1️⃣  Validación sin persistir (dry-run)...")
    result = await service.ingest_csv(csv_file, persist=False)
    
    print(f"   ✅ Total de filas: {result.total_rows}")
    print(f"   ✅ Filas válidas: {result.valid_rows}")
    print(f"   ❌ Filas inválidas: {result.invalid_rows}")
    
    if result.errors:
        print(f"\n   Errores encontrados:")
        for error in result.errors:
            print(f"   - {error}")
    
    # Opción 2: Ingestar y persistir en MongoDB
    print("\n2️⃣  Ingesta con persistencia en MongoDB...")
    print("   (Requiere MongoDB corriendo en docker-compose)")
    
    try:
        # Conectar a MongoDB
        await MongoDBClient.connect()
        
        # Ingestar con persistencia
        result = await service.ingest_csv(csv_file, persist=True)
        
        print(f"   ✅ Total procesado: {result.total_rows}")
        print(f"   ✅ Insertados en BD: {result.inserted_rows}")
        print(f"   ✅ Éxito: {result.success}")
        
        if result.errors:
            print(f"\n   Errores:")
            for error in result.errors:
                print(f"   - {error}")
        
        # Desconectar
        await MongoDBClient.disconnect()
        
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")
        print(f"   💡 Asegúrate de que MongoDB esté corriendo:")
        print(f"      docker-compose up -d mongodb")


if __name__ == "__main__":
    asyncio.run(main())