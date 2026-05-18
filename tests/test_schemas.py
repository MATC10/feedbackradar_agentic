"""
Tests para los schemas de dominio.
"""

import pytest
from datetime import datetime
from pydantic import ValidationError

from app.schemas import (
    FeedbackCreate,
    FeedbackInDB,
    InsightCreate,
    ActionItemCreate,
    AnalysisRunCreate,
    ThemeSummary,
)


class TestFeedbackSchema:
    """Tests para schemas de Feedback"""
    
    def test_feedback_create_valid(self):
        """Verifica que FeedbackCreate acepta datos válidos"""
        feedback = FeedbackCreate(
            author_name="Laura Gómez",
            date="2026-05-10",
            text="No consigo completar el pago desde el móvil",
            platform="Reviews"
        )
        
        assert feedback.author_name == "Laura Gómez"
        assert feedback.date == "2026-05-10"
        assert feedback.text == "No consigo completar el pago desde el móvil"
        assert feedback.platform == "Reviews"
    
    def test_feedback_invalid_date_format(self):
        """Verifica que falla con formato de fecha inválido"""
        with pytest.raises(ValidationError) as exc_info:
            FeedbackCreate(
                author_name="Laura Gómez",
                date="10/05/2026",  # Formato incorrecto
                text="Texto del feedback",
                platform="Reviews"
            )
        
        assert 'date' in str(exc_info.value).lower()
    
    def test_feedback_empty_text(self):
        """Verifica que falla con texto vacío"""
        with pytest.raises(ValidationError) as exc_info:
            FeedbackCreate(
                author_name="Laura Gómez",
                date="2026-05-10",
                text="",  # Vacío
                platform="Reviews"
            )
        
        assert 'text' in str(exc_info.value).lower()
    
    def test_feedback_in_db_with_defaults(self):
        """Verifica que FeedbackInDB genera timestamps automáticamente"""
        feedback = FeedbackInDB(
            feedback_id="fb_001",
            author_name="Laura Gómez",
            date="2026-05-10",
            text="Texto del feedback",
            platform="Reviews"
        )
        
        assert feedback.feedback_id == "fb_001"
        assert isinstance(feedback.ingested_at, datetime)


class TestInsightSchema:
    """Tests para schemas de Insight"""
    
    def test_insight_create_valid(self):
        """Verifica que InsightCreate acepta datos válidos"""
        insight = InsightCreate(
            theme="Pagos fallidos",
            summary="Usuarios reportan fallos en pago móvil",
            priority="Alta",
            reasoning="Bloquea la conversión",
            evidence=["No puedo pagar", "El pago falla"]
        )
        
        assert insight.theme == "Pagos fallidos"
        assert insight.priority == "Alta"
        assert len(insight.evidence) == 2
    
    def test_insight_invalid_priority(self):
        """Verifica que falla con prioridad inválida"""
        with pytest.raises(ValidationError) as exc_info:
            InsightCreate(
                theme="Pagos fallidos",
                summary="Resumen",
                priority="Urgente",  # No es válido
                reasoning="Razón",
                evidence=[]
            )
        
        assert 'priority' in str(exc_info.value).lower()
    
    def test_insight_valid_priorities(self):
        """Verifica que acepta las tres prioridades válidas"""
        for priority in ["Alta", "Media", "Baja"]:
            insight = InsightCreate(
                theme="Tema",
                summary="Resumen",
                priority=priority,
                reasoning="Razón",
                evidence=[]
            )
            assert insight.priority == priority


class TestActionSchema:
    """Tests para schemas de Action"""
    
    def test_action_create_valid(self):
        """Verifica que ActionItemCreate acepta datos válidos"""
        action = ActionItemCreate(
            title="Investigar fallos en pagos",
            description="Revisar el checkout móvil",
            priority="Alta",
            status="Pendiente"
        )
        
        assert action.title == "Investigar fallos en pagos"
        assert action.priority == "Alta"
        assert action.status == "Pendiente"
    
    def test_action_default_status(self):
        """Verifica que el estado por defecto es Pendiente"""
        action = ActionItemCreate(
            title="Título",
            description="Descripción",
            priority="Media"
        )
        
        assert action.status == "Pendiente"
    
    def test_action_invalid_status(self):
        """Verifica que falla con estado inválido"""
        with pytest.raises(ValidationError) as exc_info:
            ActionItemCreate(
                title="Título",
                description="Descripción",
                priority="Alta",
                status="Archivada"  # No es válido
            )
        
        assert 'status' in str(exc_info.value).lower()
    
    def test_action_valid_statuses(self):
        """Verifica que acepta todos los estados válidos"""
        for status in ["Pendiente", "En Progreso", "Completada", "Cancelada"]:
            action = ActionItemCreate(
                title="Título",
                description="Descripción",
                priority="Media",
                status=status
            )
            assert action.status == status


class TestAnalysisSchema:
    """Tests para schemas de Analysis"""
    
    def test_theme_summary_valid(self):
        """Verifica que ThemeSummary acepta datos válidos"""
        theme = ThemeSummary(
            theme="Pagos fallidos",
            priority="Alta",
            evidence_count=15,
            recommendation="Revisar checkout móvil"
        )
        
        assert theme.theme == "Pagos fallidos"
        assert theme.priority == "Alta"
        assert theme.evidence_count == 15
    
    def test_theme_summary_negative_evidence_count(self):
        """Verifica que falla con conteo negativo de evidencias"""
        with pytest.raises(ValidationError) as exc_info:
            ThemeSummary(
                theme="Tema",
                priority="Alta",
                evidence_count=-5,  # Negativo no válido
                recommendation="Recomendación"
            )
        
        assert 'evidence_count' in str(exc_info.value).lower()
    
    def test_analysis_run_create_with_defaults(self):
        """Verifica que AnalysisRunCreate tiene defaults correctos"""
        analysis = AnalysisRunCreate()
        
        assert analysis.feedback_filter == {}
    
    def test_analysis_run_create_with_filter(self):
        """Verifica que AnalysisRunCreate acepta filtros"""
        analysis = AnalysisRunCreate(
            feedback_filter={"platform": "Reviews", "date_from": "2026-05-01"}
        )
        
        assert analysis.feedback_filter["platform"] == "Reviews"
        assert "date_from" in analysis.feedback_filter


class TestSchemasSerialization:
    """Tests para serialización JSON"""
    
    def test_feedback_serialization(self):
        """Verifica que Feedback se serializa correctamente a JSON"""
        feedback = FeedbackCreate(
            author_name="Laura Gómez",
            date="2026-05-10",
            text="Texto del feedback",
            platform="Reviews"
        )
        
        json_data = feedback.model_dump()
        
        assert json_data["author_name"] == "Laura Gómez"
        assert json_data["date"] == "2026-05-10"
        assert isinstance(json_data, dict)
    
    def test_insight_serialization_with_evidence(self):
        """Verifica que Insight con evidencias se serializa correctamente"""
        insight = InsightCreate(
            theme="Tema",
            summary="Resumen",
            priority="Alta",
            reasoning="Razón",
            evidence=["Evidencia 1", "Evidencia 2"]
        )
        
        json_data = insight.model_dump()
        
        assert isinstance(json_data["evidence"], list)
        assert len(json_data["evidence"]) == 2
    
    def test_action_serialization(self):
        """Verifica que Action se serializa correctamente"""
        action = ActionItemCreate(
            title="Título",
            description="Descripción",
            priority="Alta"
        )
        
        json_data = action.model_dump()
        
        assert json_data["status"] == "Pendiente"  # Default
        assert "title" in json_data