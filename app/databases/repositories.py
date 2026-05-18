"""
Repositorios para operaciones de base de datos.

Cada repositorio encapsula las operaciones CRUD para una entidad específica.
"""

import unicodedata
import re
from typing import Optional
from datetime import datetime


def _normalize_theme(name: str) -> str:
    """Normaliza un nombre de tema para comparación tolerante a variaciones del LLM.
    Minúsculas, sin tildes, solo alfanumérico y espacios, espacios colapsados."""
    nfkd = unicodedata.normalize("NFKD", name)
    ascii_str = nfkd.encode("ascii", "ignore").decode("ascii")
    cleaned = re.sub(r"[^a-z0-9\s]", "", ascii_str.lower())
    return re.sub(r"\s+", " ", cleaned).strip()

from app.databases.mongodb_client import (
    get_feedback_collection,
    get_analysis_runs_collection,
    get_insights_collection,
    get_actions_collection,
)
from app.schemas import (
    FeedbackInDB,
    InsightInDB,
    ActionItemInDB,
    AnalysisRunInDB,
)


class FeedbackRepository:
    """Repositorio para operaciones con Feedback"""
    
    @staticmethod
    async def insert_one(feedback: FeedbackInDB) -> str:
        """
        Inserta un feedback en la base de datos.
        
        Args:
            feedback: Feedback a insertar
            
        Returns:
            str: ID del feedback insertado
        """
        collection = get_feedback_collection()
        feedback_dict = feedback.model_dump()
        
        result = await collection.insert_one(feedback_dict)
        return feedback.feedback_id
    
    @staticmethod
    async def insert_many(feedbacks: list[FeedbackInDB]) -> int:
        """
        Inserta múltiples feedbacks en lote.
        
        Args:
            feedbacks: Lista de feedbacks a insertar
            
        Returns:
            int: Número de feedbacks insertados
        """
        if not feedbacks:
            return 0
        
        collection = get_feedback_collection()
        feedback_dicts = [f.model_dump() for f in feedbacks]
        
        result = await collection.insert_many(feedback_dicts)
        return len(result.inserted_ids)
    
    @staticmethod
    async def find_all(limit: int = 100, skip: int = 0) -> list[dict]:
        """
        Obtiene todos los feedbacks con paginación.
        
        Args:
            limit: Número máximo de resultados
            skip: Número de resultados a saltar
            
        Returns:
            list[dict]: Lista de feedbacks
        """
        collection = get_feedback_collection()
        cursor = collection.find().skip(skip).limit(limit).sort("ingested_at", -1)
        return await cursor.to_list(length=limit)
    
    @staticmethod
    async def find_recent(days: int = 7, limit: int = 100) -> list[dict]:
        """
        Obtiene feedback reciente de los últimos N días.
        
        Args:
            days: Número de días hacia atrás
            limit: Número máximo de resultados
            
        Returns:
            list[dict]: Lista de feedbacks recientes
        """
        collection = get_feedback_collection()
        
        # Calcular fecha límite
        from datetime import timedelta
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        cursor = collection.find(
            {"ingested_at": {"$gte": cutoff_date}}
        ).limit(limit).sort("ingested_at", -1)
        
        return await cursor.to_list(length=limit)
    
    @staticmethod
    async def count_all() -> int:
        """
        Cuenta el total de feedbacks.
        
        Returns:
            int: Número total de feedbacks
        """
        collection = get_feedback_collection()
        return await collection.count_documents({})
    
    @staticmethod
    async def find_by_platform(platform: str, limit: int = 100) -> list[dict]:
        """
        Obtiene feedbacks filtrados por plataforma.
        
        Args:
            platform: Nombre de la plataforma
            limit: Número máximo de resultados
            
        Returns:
            list[dict]: Lista de feedbacks de la plataforma
        """
        collection = get_feedback_collection()
        cursor = collection.find(
            {"platform": platform}
        ).limit(limit).sort("ingested_at", -1)
        
        return await cursor.to_list(length=limit)


class AnalysisRunRepository:
    """Repositorio para operaciones con AnalysisRun"""
    
    @staticmethod
    async def insert_one(analysis_run: AnalysisRunInDB) -> str:
        """
        Inserta un análisis en la base de datos.
        
        Args:
            analysis_run: Análisis a insertar
            
        Returns:
            str: ID del análisis insertado
        """
        collection = get_analysis_runs_collection()
        analysis_dict = analysis_run.model_dump()
        
        await collection.insert_one(analysis_dict)
        return analysis_run.run_id
    
    @staticmethod
    async def find_by_id(run_id: str) -> Optional[dict]:
        """
        Busca un análisis por su ID.
        
        Args:
            run_id: ID del análisis
            
        Returns:
            Optional[dict]: Análisis encontrado o None
        """
        collection = get_analysis_runs_collection()
        return await collection.find_one({"run_id": run_id})
    
    @staticmethod
    async def find_latest() -> Optional[dict]:
        """
        Obtiene el análisis más reciente.
        
        Returns:
            Optional[dict]: Último análisis o None
        """
        collection = get_analysis_runs_collection()
        cursor = collection.find().sort("created_at", -1).limit(1)
        results = await cursor.to_list(length=1)
        return results[0] if results else None
    
    @staticmethod
    async def find_all(limit: int = 10, skip: int = 0) -> list[dict]:
        """
        Obtiene todos los análisis con paginación.
        
        Args:
            limit: Número máximo de resultados
            skip: Número de resultados a saltar
            
        Returns:
            list[dict]: Lista de análisis
        """
        collection = get_analysis_runs_collection()
        cursor = collection.find().skip(skip).limit(limit).sort("created_at", -1)
        return await cursor.to_list(length=limit)
    
    @staticmethod
    async def update_status(run_id: str, status: str, error_message: Optional[str] = None) -> bool:
        """
        Actualiza el estado de un análisis.
        
        Args:
            run_id: ID del análisis
            status: Nuevo estado
            error_message: Mensaje de error opcional
            
        Returns:
            bool: True si se actualizó correctamente
        """
        collection = get_analysis_runs_collection()
        
        update_data = {"status": status}
        if status == "Completado":
            update_data["completed_at"] = datetime.utcnow()
        if error_message:
            update_data["error_message"] = error_message
        
        result = await collection.update_one(
            {"run_id": run_id},
            {"$set": update_data}
        )
        return result.modified_count > 0


class InsightRepository:
    """Repositorio para operaciones con Insights"""
    
    @staticmethod
    async def insert_one(insight: InsightInDB) -> str:
        """
        Inserta un insight en la base de datos.
        
        Args:
            insight: Insight a insertar
            
        Returns:
            str: ID del insight insertado
        """
        collection = get_insights_collection()
        insight_dict = insight.model_dump()
        
        await collection.insert_one(insight_dict)
        return insight.insight_id
    
    @staticmethod
    async def insert_many(insights: list[InsightInDB]) -> int:
        """
        Inserta múltiples insights en lote.
        
        Args:
            insights: Lista de insights a insertar
            
        Returns:
            int: Número de insights insertados
        """
        if not insights:
            return 0
        
        collection = get_insights_collection()
        insight_dicts = [i.model_dump() for i in insights]
        
        result = await collection.insert_many(insight_dicts)
        return len(result.inserted_ids)
    
    @staticmethod
    async def find_by_analysis_run(analysis_run_id: str) -> list[dict]:
        """
        Obtiene todos los insights de un análisis.
        
        Args:
            analysis_run_id: ID del análisis
            
        Returns:
            list[dict]: Lista de insights
        """
        collection = get_insights_collection()
        cursor = collection.find({"analysis_run_id": analysis_run_id})
        return await cursor.to_list(length=None)
    
    @staticmethod
    async def find_all(limit: int = 100, skip: int = 0) -> list[dict]:
        """
        Obtiene todos los insights con paginación.

        Args:
            limit: Número máximo de resultados
            skip: Número de resultados a saltar

        Returns:
            list[dict]: Lista de insights
        """
        collection = get_insights_collection()
        cursor = collection.find().skip(skip).limit(limit)
        return await cursor.to_list(length=limit)

    @staticmethod
    async def find_latest_per_theme(limit: int = 100) -> list[dict]:
        """Devuelve el insight más reciente por tema, deduplicando ejecuciones anteriores.
        Usa normalización de nombre para agrupar variaciones del LLM del mismo tema."""
        collection = get_insights_collection()
        # Traer todos ordenados del más reciente al más antiguo
        cursor = collection.find().sort("created_at", -1)
        all_insights = await cursor.to_list(length=5000)

        seen: set = set()
        result: list = []
        for insight in all_insights:
            key = _normalize_theme(insight.get("theme", ""))
            if key not in seen:
                seen.add(key)
                result.append(insight)
            if len(result) >= limit:
                break
        return result
    
    @staticmethod
    async def count_all() -> int:
        """
        Cuenta el total de insights.
        
        Returns:
            int: Número total de insights
        """
        collection = get_insights_collection()
        return await collection.count_documents({})


class ActionRepository:
    """Repositorio para operaciones con Actions"""
    
    @staticmethod
    async def insert_one(action: ActionItemInDB) -> str:
        """
        Inserta una acción en la base de datos.
        
        Args:
            action: Acción a insertar
            
        Returns:
            str: ID de la acción insertada
        """
        collection = get_actions_collection()
        action_dict = action.model_dump()
        
        await collection.insert_one(action_dict)
        return action.action_id
    
    @staticmethod
    async def insert_many(actions: list[ActionItemInDB]) -> int:
        """
        Inserta múltiples acciones en lote.
        
        Args:
            actions: Lista de acciones a insertar
            
        Returns:
            int: Número de acciones insertadas
        """
        if not actions:
            return 0
        
        collection = get_actions_collection()
        action_dicts = [a.model_dump() for a in actions]
        
        result = await collection.insert_many(action_dicts)
        return len(result.inserted_ids)
    
    @staticmethod
    async def find_by_analysis_run(analysis_run_id: str) -> list[dict]:
        """
        Obtiene todas las acciones de un análisis.
        
        Args:
            analysis_run_id: ID del análisis
            
        Returns:
            list[dict]: Lista de acciones
        """
        collection = get_actions_collection()
        cursor = collection.find({"analysis_run_id": analysis_run_id})
        return await cursor.to_list(length=None)
    
    @staticmethod
    async def find_all(limit: int = 100, skip: int = 0) -> list[dict]:
        """
        Obtiene todas las acciones con paginación.
        
        Args:
            limit: Número máximo de resultados
            skip: Número de resultados a saltar
            
        Returns:
            list[dict]: Lista de acciones
        """
        collection = get_actions_collection()
        cursor = collection.find().skip(skip).limit(limit).sort("created_at", -1)
        return await cursor.to_list(length=limit)
    
    @staticmethod
    async def update_status(action_id: str, status: str) -> bool:
        """
        Actualiza el estado de una acción.
        
        Args:
            action_id: ID de la acción
            status: Nuevo estado
            
        Returns:
            bool: True si se actualizó correctamente
        """
        collection = get_actions_collection()
        
        result = await collection.update_one(
            {"action_id": action_id},
            {"$set": {"status": status}}
        )
        return result.modified_count > 0
    
    @staticmethod
    async def count_all() -> int:
        """
        Cuenta el total de acciones.

        Returns:
            int: Número total de acciones
        """
        collection = get_actions_collection()
        return await collection.count_documents({})

    @staticmethod
    async def find_by_title_recent(title: str) -> Optional[dict]:
        """Busca la acción más reciente con ese título."""
        collection = get_actions_collection()
        cursor = collection.find({"title": title}).sort("created_at", -1).limit(1)
        results = await cursor.to_list(length=1)
        return results[0] if results else None

    @staticmethod
    async def update_jira_fields(
        action_id: str,
        theme_name: str,
        jira_issue_key: Optional[str],
        jira_issue_url: Optional[str],
        jira_sync_status: str,
    ) -> bool:
        """Actualiza los campos Jira de una acción."""
        collection = get_actions_collection()
        result = await collection.update_one(
            {"action_id": action_id},
            {"$set": {
                "theme_name": theme_name,
                "theme_name_normalized": _normalize_theme(theme_name),
                "jira_issue_key": jira_issue_key,
                "jira_issue_url": jira_issue_url,
                "jira_created_at": datetime.utcnow() if jira_sync_status == "created" else None,
                "jira_sync_status": jira_sync_status,
            }}
        )
        return result.modified_count > 0

    @staticmethod
    async def find_recent_jira_by_theme(theme_name: str, days: int = 7) -> Optional[dict]:
        """Busca un ticket Jira reciente para el mismo tema usando nombre normalizado.
        Tolerante a variaciones del LLM: mayúsculas, tildes, reformulaciones menores."""
        from datetime import timedelta
        collection = get_actions_collection()
        cutoff = datetime.utcnow() - timedelta(days=days)
        return await collection.find_one({
            "theme_name_normalized": _normalize_theme(theme_name),
            "jira_sync_status": "created",
            "jira_created_at": {"$gte": cutoff},
        })

    @staticmethod
    async def find_by_status(status: str, limit: int = 100) -> list[dict]:
        """
        Obtiene acciones filtradas por estado.
        
        Args:
            status: Estado de las acciones
            limit: Número máximo de resultados
            
        Returns:
            list[dict]: Lista de acciones
        """
        collection = get_actions_collection()
        cursor = collection.find(
            {"status": status}
        ).limit(limit).sort("created_at", -1)
        
        return await cursor.to_list(length=limit)