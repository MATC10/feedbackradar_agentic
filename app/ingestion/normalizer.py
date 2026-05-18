"""
Normalizador de datos de feedback.

Transforma datos crudos del CSV al formato interno del modelo Feedback.
"""

import uuid
from datetime import datetime
from typing import Dict, Any, Tuple
from pydantic import ValidationError

from app.schemas import FeedbackCreate, FeedbackInDB


class FeedbackNormalizer:
    """
    Normalizador que transforma datos de CSV a modelos Feedback.
    
    Mapea columnas del CSV al esquema interno y genera IDs únicos.
    """
    
    @staticmethod
    def generate_feedback_id() -> str:
        """
        Genera un ID único para un feedback.
        
        Returns:
            ID único en formato fb_<uuid>
        """
        return f"fb_{uuid.uuid4().hex[:12]}"
    
    @staticmethod
    def normalize_row(row: Dict[str, Any]) -> Tuple[FeedbackCreate | None, str | None]:
        """
        Normaliza una fila del CSV a un modelo FeedbackCreate.
        
        Mapeo de columnas:
        - nombre -> author_name
        - fecha -> date
        - reseña -> text
        - plataforma -> platform
        
        Args:
            row: Diccionario con datos de la fila del CSV
            
        Returns:
            Tupla (FeedbackCreate | None, error_message | None)
            - Si es válido: (FeedbackCreate, None)
            - Si es inválido: (None, mensaje_de_error)
        """
        try:
            # Extraer metadatos
            source_file = row.get('_source_file', 'unknown.csv')
            row_number = row.get('_row_number', 0)
            
            # Validar que los campos obligatorios existan y no estén vacíos
            required_fields = ['nombre', 'fecha', 'reseña', 'plataforma']
            for field in required_fields:
                if field not in row:
                    return None, f"Fila {row_number}: Campo '{field}' no encontrado"

                raw = row[field]
                value = str(raw).strip() if raw is not None else ''
                if not value or value.lower() == 'none':
                    return None, f"Fila {row_number}: Campo '{field}' está vacío"
            
            # Mapear columnas CSV a modelo interno
            feedback_data = {
                'author_name': str(row['nombre']).strip(),
                'date': str(row['fecha']).strip(),
                'text': str(row['reseña']).strip(),
                'platform': str(row['plataforma']).strip(),
                'source_file': source_file,
            }
            
            # Validar con Pydantic
            feedback_create = FeedbackCreate(**feedback_data)
            
            return feedback_create, None
            
        except ValidationError as e:
            # Extraer el primer error de Pydantic
            error_details = e.errors()[0]
            field = error_details['loc'][0] if error_details['loc'] else 'unknown'
            msg = error_details['msg']
            row_number = row.get('_row_number', 0)
            
            return None, f"Fila {row_number}: Error en '{field}': {msg}"
        
        except Exception as e:
            row_number = row.get('_row_number', 0)
            return None, f"Fila {row_number}: Error inesperado: {str(e)}"
    
    @staticmethod
    def create_feedback_in_db(feedback_create: FeedbackCreate) -> FeedbackInDB:
        """
        Convierte un FeedbackCreate a FeedbackInDB con ID y timestamp.
        
        Args:
            feedback_create: Modelo de creación validado
            
        Returns:
            FeedbackInDB listo para persistir
        """
        feedback_dict = feedback_create.model_dump()
        
        # Añadir campos de BD
        feedback_dict['feedback_id'] = FeedbackNormalizer.generate_feedback_id()
        feedback_dict['ingested_at'] = datetime.utcnow()
        
        return FeedbackInDB(**feedback_dict)
    
    @staticmethod
    def normalize_and_prepare(row: Dict[str, Any]) -> Tuple[FeedbackInDB | None, str | None]:
        """
        Normaliza una fila y la prepara para BD en un solo paso.
        
        Args:
            row: Diccionario con datos de la fila del CSV
            
        Returns:
            Tupla (FeedbackInDB | None, error_message | None)
        """
        feedback_create, error = FeedbackNormalizer.normalize_row(row)
        
        if error:
            return None, error
        
        feedback_in_db = FeedbackNormalizer.create_feedback_in_db(feedback_create)
        return feedback_in_db, None