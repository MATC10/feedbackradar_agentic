"""
Tests para la capa de ingesta de feedback.
"""

import pytest
from pathlib import Path

from app.ingestion.csv_reader import CSVReader
from app.ingestion.normalizer import FeedbackNormalizer
from app.ingestion.ingestion_service import IngestionService, IngestionResult
from app.schemas import FeedbackCreate, FeedbackInDB


class TestCSVReader:
    """Tests para CSVReader"""
    
    def test_validate_csv_structure_valid(self, tmp_path):
        """Verifica que valida correctamente un CSV con estructura válida"""
        # Crear CSV temporal válido
        csv_file = tmp_path / "test.csv"
        csv_file.write_text(
            "nombre,fecha,reseña,plataforma\n"
            "Test User,2026-05-10,Test feedback,Reviews\n",
            encoding="utf-8"
        )
        
        # Debe validar sin errores
        assert CSVReader.validate_csv_structure(csv_file) is True
    
    def test_validate_csv_structure_missing_columns(self, tmp_path):
        """Verifica que falla con columnas faltantes"""
        # Crear CSV sin columna 'plataforma'
        csv_file = tmp_path / "test.csv"
        csv_file.write_text(
            "nombre,fecha,reseña\n"
            "Test User,2026-05-10,Test feedback\n",
            encoding="utf-8"
        )
        
        with pytest.raises(ValueError) as exc_info:
            CSVReader.validate_csv_structure(csv_file)
        
        assert "plataforma" in str(exc_info.value).lower()
    
    def test_validate_csv_structure_file_not_found(self):
        """Verifica que falla si el archivo no existe"""
        with pytest.raises(FileNotFoundError):
            CSVReader.validate_csv_structure("nonexistent.csv")
    
    def test_read_csv_valid(self, tmp_path):
        """Verifica que lee correctamente un CSV válido"""
        csv_file = tmp_path / "test.csv"
        csv_file.write_text(
            "nombre,fecha,reseña,plataforma\n"
            "Laura Gómez,2026-05-10,Test feedback,Reviews\n"
            "Carlos Ruiz,2026-05-11,Another feedback,Email\n",
            encoding="utf-8"
        )
        
        rows = list(CSVReader.read_csv(csv_file))
        
        assert len(rows) == 2
        assert rows[0]['nombre'] == 'Laura Gómez'
        assert rows[0]['_row_number'] == 2  # Primera fila de datos
        assert rows[0]['_source_file'] == 'test.csv'
        assert rows[1]['nombre'] == 'Carlos Ruiz'
        assert rows[1]['_row_number'] == 3
    
    def test_read_csv_batch(self, tmp_path):
        """Verifica que read_csv_batch carga todo en memoria"""
        csv_file = tmp_path / "test.csv"
        csv_file.write_text(
            "nombre,fecha,reseña,plataforma\n"
            "User 1,2026-05-10,Feedback 1,Reviews\n"
            "User 2,2026-05-11,Feedback 2,Email\n",
            encoding="utf-8"
        )
        
        rows = CSVReader.read_csv_batch(csv_file)
        
        assert isinstance(rows, list)
        assert len(rows) == 2


class TestFeedbackNormalizer:
    """Tests para FeedbackNormalizer"""
    
    def test_generate_feedback_id(self):
        """Verifica que genera IDs únicos"""
        id1 = FeedbackNormalizer.generate_feedback_id()
        id2 = FeedbackNormalizer.generate_feedback_id()
        
        assert id1.startswith('fb_')
        assert id2.startswith('fb_')
        assert id1 != id2
        assert len(id1) == 15  # 'fb_' + 12 caracteres
    
    def test_normalize_row_valid(self):
        """Verifica que normaliza correctamente una fila válida"""
        row = {
            'nombre': 'Laura Gómez',
            'fecha': '2026-05-10',
            'reseña': 'Test feedback',
            'plataforma': 'Reviews',
            '_source_file': 'test.csv',
            '_row_number': 2
        }
        
        feedback_create, error = FeedbackNormalizer.normalize_row(row)
        
        assert error is None
        assert feedback_create is not None
        assert isinstance(feedback_create, FeedbackCreate)
        assert feedback_create.author_name == 'Laura Gómez'
        assert feedback_create.date == '2026-05-10'
        assert feedback_create.text == 'Test feedback'
        assert feedback_create.platform == 'Reviews'
        assert feedback_create.source_file == 'test.csv'
    
    def test_normalize_row_invalid_date(self):
        """Verifica que falla con fecha inválida"""
        row = {
            'nombre': 'Laura Gómez',
            'fecha': '10/05/2026',  # Formato incorrecto
            'reseña': 'Test feedback',
            'plataforma': 'Reviews',
            '_source_file': 'test.csv',
            '_row_number': 2
        }
        
        feedback_create, error = FeedbackNormalizer.normalize_row(row)
        
        assert feedback_create is None
        assert error is not None
        assert 'fila 2' in error.lower()
        assert 'date' in error.lower()
    
    def test_normalize_row_empty_field(self):
        """Verifica que falla con campo vacío"""
        row = {
            'nombre': 'Laura Gómez',
            'fecha': '2026-05-10',
            'reseña': '',  # Vacío
            'plataforma': 'Reviews',
            '_source_file': 'test.csv',
            '_row_number': 2
        }
        
        feedback_create, error = FeedbackNormalizer.normalize_row(row)
        
        assert feedback_create is None
        assert error is not None
        assert 'fila 2' in error.lower()
        assert 'reseña' in error.lower() or 'vacío' in error.lower()
    
    def test_normalize_row_missing_field(self):
        """Verifica que falla con campo faltante"""
        row = {
            'nombre': 'Laura Gómez',
            'fecha': '2026-05-10',
            # falta 'reseña'
            'plataforma': 'Reviews',
            '_source_file': 'test.csv',
            '_row_number': 2
        }
        
        feedback_create, error = FeedbackNormalizer.normalize_row(row)
        
        assert feedback_create is None
        assert error is not None
        assert 'fila 2' in error.lower()
        assert 'reseña' in error.lower()
    
    def test_create_feedback_in_db(self):
        """Verifica que crea FeedbackInDB correctamente"""
        feedback_create = FeedbackCreate(
            author_name="Test User",
            date="2026-05-10",
            text="Test feedback",
            platform="Reviews",
            source_file="test.csv"
        )
        
        feedback_in_db = FeedbackNormalizer.create_feedback_in_db(feedback_create)
        
        assert isinstance(feedback_in_db, FeedbackInDB)
        assert feedback_in_db.feedback_id.startswith('fb_')
        assert feedback_in_db.author_name == "Test User"
        assert feedback_in_db.ingested_at is not None
    
    def test_normalize_and_prepare(self):
        """Verifica el proceso completo de normalización"""
        row = {
            'nombre': 'Laura Gómez',
            'fecha': '2026-05-10',
            'reseña': 'Test feedback',
            'plataforma': 'Reviews',
            '_source_file': 'test.csv',
            '_row_number': 2
        }
        
        feedback_in_db, error = FeedbackNormalizer.normalize_and_prepare(row)
        
        assert error is None
        assert feedback_in_db is not None
        assert isinstance(feedback_in_db, FeedbackInDB)
        assert feedback_in_db.feedback_id.startswith('fb_')


class TestIngestionService:
    """Tests para IngestionService"""
    
    @pytest.mark.asyncio
    async def test_ingest_csv_without_persist(self, tmp_path):
        """Verifica ingesta sin persistir en BD"""
        # Crear CSV de prueba
        csv_file = tmp_path / "test.csv"
        csv_file.write_text(
            "nombre,fecha,reseña,plataforma\n"
            "Laura Gómez,2026-05-10,Test feedback 1,Reviews\n"
            "Carlos Ruiz,2026-05-11,Test feedback 2,Email\n"
            "Ana Pérez,INVALID_DATE,Test feedback 3,Reviews\n",  # Fecha inválida
            encoding="utf-8"
        )
        
        service = IngestionService()
        result = await service.ingest_csv(csv_file, persist=False)
        
        assert isinstance(result, IngestionResult)
        assert result.total_rows == 3
        assert result.valid_rows == 2
        assert result.invalid_rows == 1
        assert result.inserted_rows == 0  # No se persistió
        assert len(result.errors) == 1
        assert 'fila 4' in result.errors[0].lower()  # Fila 4 (header es 1, datos empiezan en 2)
    
    @pytest.mark.asyncio
    async def test_ingest_csv_all_valid(self, tmp_path):
        """Verifica ingesta con todas las filas válidas"""
        csv_file = tmp_path / "test.csv"
        csv_file.write_text(
            "nombre,fecha,reseña,plataforma\n"
            "Laura Gómez,2026-05-10,Test feedback 1,Reviews\n"
            "Carlos Ruiz,2026-05-11,Test feedback 2,Email\n",
            encoding="utf-8"
        )
        
        service = IngestionService()
        result = await service.ingest_csv(csv_file, persist=False)
        
        assert result.success is True
        assert result.total_rows == 2
        assert result.valid_rows == 2
        assert result.invalid_rows == 0
        assert len(result.errors) == 0
    
    def test_ingestion_result_model(self):
        """Verifica que el modelo IngestionResult funciona correctamente"""
        result = IngestionResult(
            success=True,
            total_rows=100,
            valid_rows=95,
            invalid_rows=5,
            inserted_rows=95,
            errors=["Error 1", "Error 2"],
            source_file="test.csv"
        )
        
        assert result.success is True
        assert result.total_rows == 100
        assert result.valid_rows == 95
        assert len(result.errors) == 2
    
    def test_ingestion_result_validation(self):
        """Verifica validaciones del modelo IngestionResult"""
        with pytest.raises(Exception):  # Pydantic ValidationError
            IngestionResult(
                success=True,
                total_rows=-1,  # No puede ser negativo
                valid_rows=0,
                invalid_rows=0,
                inserted_rows=0,
                errors=[],
                source_file="test.csv"
            )