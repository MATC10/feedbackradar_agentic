import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

async def verify_mongodb():
    # Conectar a MongoDB
    client = AsyncIOMotorClient("mongodb://localhost:27017")
    db = client["feedbackradar"]
    collection = db["feedback"]
    
    # Contar documentos
    count = await collection.count_documents({})
    print(f"\n✅ Total de documentos en MongoDB: {count}")
    
    # Obtener algunos documentos
    cursor = collection.find().limit(5)
    documents = await cursor.to_list(length=5)
    
    print(f"\n📄 Primeros {len(documents)} documentos:")
    for i, doc in enumerate(documents, 1):
        print(f"\n{i}. ID: {doc['feedback_id']}")
        print(f"   Autor: {doc['author_name']}")
        print(f"   Fecha: {doc['date']}")
        print(f"   Plataforma: {doc['platform']}")
        print(f"   Texto: {doc['text'][:60]}...")
        print(f"   Archivo: {doc['source_file']}")
        print(f"   Ingesta: {doc['ingested_at']}")
    
    client.close()

if __name__ == "__main__":
    asyncio.run(verify_mongodb())