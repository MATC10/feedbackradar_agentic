"""
Cliente de MongoDB para FeedbackRadar Agentic.
"""

from typing import Optional
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo.errors import ConnectionFailure

from app.core.config import settings


class MongoDBClient:
    """Cliente singleton para MongoDB"""
    
    _client: Optional[AsyncIOMotorClient] = None
    _db: Optional[AsyncIOMotorDatabase] = None
    
    @classmethod
    async def connect(cls) -> None:
        """Conecta al servidor MongoDB"""
        if cls._client is None:
            try:
                cls._client = AsyncIOMotorClient(settings.mongodb_uri)
                cls._db = cls._client[settings.mongodb_db_name]
                
                # Verificar conexión
                await cls._client.admin.command('ping')
                print(f"[OK] Conectado a MongoDB: {settings.mongodb_db_name}")

            except ConnectionFailure as e:
                print(f"[ERROR] Error conectando a MongoDB: {e}")
                raise
    
    @classmethod
    async def disconnect(cls) -> None:
        """Cierra la conexión a MongoDB"""
        if cls._client is not None:
            cls._client.close()
            cls._client = None
            cls._db = None
            print("[OK] Desconectado de MongoDB")
    
    @classmethod
    def get_database(cls) -> AsyncIOMotorDatabase:
        """
        Obtiene la instancia de la base de datos.
        
        Returns:
            AsyncIOMotorDatabase: Base de datos configurada
            
        Raises:
            RuntimeError: Si no está conectado
        """
        if cls._db is None:
            raise RuntimeError(
                "MongoDB no está conectado. Llama a MongoDBClient.connect() primero."
            )
        return cls._db
    
    @classmethod
    def get_collection(cls, collection_name: str):
        """
        Obtiene una colección específica.
        
        Args:
            collection_name: Nombre de la colección
            
        Returns:
            AsyncIOMotorCollection: Colección solicitada
        """
        db = cls.get_database()
        return db[collection_name]


# Nombres de colecciones como constantes
class Collections:
    """Nombres de las colecciones en MongoDB"""
    FEEDBACK = "feedback"
    ANALYSIS_RUNS = "analysis_runs"
    INSIGHTS = "insights"
    ACTIONS = "actions"


# Funciones helper para obtener colecciones
def get_feedback_collection():
    """Obtiene la colección de feedback"""
    return MongoDBClient.get_collection(Collections.FEEDBACK)


def get_analysis_runs_collection():
    """Obtiene la colección de analysis_runs"""
    return MongoDBClient.get_collection(Collections.ANALYSIS_RUNS)


def get_insights_collection():
    """Obtiene la colección de insights"""
    return MongoDBClient.get_collection(Collections.INSIGHTS)


def get_actions_collection():
    """Obtiene la colección de actions"""
    return MongoDBClient.get_collection(Collections.ACTIONS)


# Dependencia para FastAPI
async def get_db() -> AsyncIOMotorDatabase:
    """
    Dependencia de FastAPI para obtener la base de datos.
    
    Uso:
        @app.get("/endpoint")
        async def endpoint(db: AsyncIOMotorDatabase = Depends(get_db)):
            ...
    """
    return MongoDBClient.get_database()