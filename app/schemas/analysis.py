# -*- coding: utf-8 -*-
"""
app/schemas/analysis.py

Schemas Pydantic para análisis de feedback por agentes.
"""

from typing import List, Optional
from pydantic import BaseModel, Field, field_validator


class DetectedTheme(BaseModel):
    """
    Tema detectado durante el análisis de feedback.
    
    Representa una categoría o patrón recurrente identificado
    en el conjunto de feedback analizado.
    """
    name: str = Field(..., min_length=1, description="Nombre del tema detectado")
    description: str = Field(..., min_length=1, description="Descripción detallada del tema")
    
    @field_validator('name', 'description')
    @classmethod
    def validate_not_empty(cls, v: str) -> str:
        """Valida que los campos no estén vacíos después de strip."""
        if not v.strip():
            raise ValueError("El campo no puede estar vacío")
        return v.strip()
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "Pagos fallidos",
                "description": "Usuarios que no consiguen completar el checkout debido a errores en el proceso de pago"
            }
        }


class ThemeDiscoveryResponse(BaseModel):
    """
    Respuesta estructurada del Theme Discovery Agent.
    
    Contiene la lista de temas detectados en el análisis de feedback.
    """
    themes: List[DetectedTheme] = Field(
        default_factory=list,
        description="Lista de temas detectados en el feedback"
    )
    
    @field_validator('themes')
    @classmethod
    def validate_themes_limit(cls, v: List[DetectedTheme]) -> List[DetectedTheme]:
        """Valida que el número de temas esté en un rango razonable."""
        if len(v) > 10:
            raise ValueError("No se pueden detectar más de 10 temas")
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "themes": [
                    {
                        "name": "Pagos fallidos",
                        "description": "Problemas recurrentes con el proceso de checkout"
                    },
                    {
                        "name": "Lentitud del sistema",
                        "description": "Quejas sobre tiempos de respuesta lentos"
                    }
                ]
            }
        }


class Evidence(BaseModel):
    """
    Evidencia de feedback que soporta un tema.
    
    Representa un fragmento de feedback concreto que justifica
    la existencia de un tema detectado.
    """
    feedback_id: str = Field(..., description="ID del feedback")
    text: str = Field(..., description="Texto del feedback")
    score: float = Field(..., ge=0.0, le=1.0, description="Score de relevancia")
    platform: Optional[str] = Field(None, description="Plataforma de origen")
    date: Optional[str] = Field(None, description="Fecha del feedback")
    
    class Config:
        json_schema_extra = {
            "example": {
                "feedback_id": "fb_123",
                "text": "No pude completar mi compra, el sistema falló",
                "score": 0.95,
                "platform": "Email"
            }
        }


class PrioritizedTheme(BaseModel):
    """
    Tema priorizado con su nivel de importancia.
    
    Extiende DetectedTheme con información de priorización
    basada en evidencias y análisis.
    """
    name: str = Field(..., description="Nombre del tema")
    description: str = Field(..., description="Descripción del tema")
    priority: str = Field(..., description="Prioridad: Crítica, Alta, Media, Baja")
    evidence_count: int = Field(..., ge=0, description="Número de evidencias")
    reasoning: str = Field(..., description="Razonamiento de la priorización")
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "Pagos fallidos",
                "description": "Problemas con checkout",
                "priority": "Crítica",
                "evidence_count": 15,
                "reasoning": "Alto volumen de quejas y impacto directo en conversión"
            }
        }


class Recommendation(BaseModel):
    """
    Recomendación de acción basada en análisis.
    
    Representa una acción concreta recomendada para abordar
    los temas detectados y priorizados.
    """
    title: str = Field(..., description="Título de la recomendación")
    description: str = Field(..., description="Descripción detallada")
    priority: str = Field(..., description="Prioridad de la acción")
    related_themes: List[str] = Field(..., description="Temas relacionados")
    expected_impact: str = Field(..., description="Impacto esperado")
    
    class Config:
        json_schema_extra = {
            "example": {
                "title": "Optimizar proceso de pago",
                "description": "Implementar retry automático y mejorar mensajes de error",
                "priority": "Alta",
                "related_themes": ["Pagos fallidos"],
                "expected_impact": "Reducción del 30% en abandono de checkout"
            }
        }