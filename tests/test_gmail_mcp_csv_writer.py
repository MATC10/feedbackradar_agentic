"""
Tests para Gmail MCP CSV Writer
"""

import pytest
import os
from pathlib import Path
from unittest.mock import patch

from app.integrations.gmail_mcp.csv_writer import (
    append_new_gmail_mcp_feedback,
    get_writer_info,
    CSV_HEADER,
    _ids_file_path,
    _load_saved_ids,
    _save_ids,
)


class TestAppendNewGmailMCPFeedback:
    """Tests para la función principal de escritura de CSV."""
    
    def test_crea_csv_si_no_existe(self, tmp_path):
        """Test que crea el CSV si no existe."""
        csv_path = tmp_path / "test_output.csv"
        
        emails = [
            {
                "id": "msg1",
                "nombre": "Juan Perez",
                "fecha": "2024-01-15",
                "reseña": "Contenido del email",
                "plataforma": "Email"
            }
        ]
        
        count = append_new_gmail_mcp_feedback(emails, str(csv_path))
        
        assert count == 1
        assert csv_path.exists()
    
    def test_header_exacto(self, tmp_path):
        """Test que el header es exactamente: nombre,fecha,reseña,plataforma."""
        csv_path = tmp_path / "test_output.csv"
        
        emails = [
            {
                "id": "msg1",
                "nombre": "Test User",
                "fecha": "2024-01-01",
                "reseña": "Test content",
                "plataforma": "Email"
            }
        ]
        
        append_new_gmail_mcp_feedback(emails, str(csv_path))
        
        # Leer primera línea (header)
        with open(csv_path, 'r', encoding='utf-8') as f:
            header_line = f.readline().strip()
        
        assert header_line == "nombre,fecha,reseña,plataforma"
    
    def test_escribe_emails_nuevos_correctamente(self, tmp_path):
        """Test que escribe emails nuevos con el formato correcto."""
        csv_path = tmp_path / "test_output.csv"
        
        emails = [
            {
                "id": "msg1",
                "nombre": "Juan Perez",
                "fecha": "2024-01-15",
                "reseña": "Contenido del email 1",
                "plataforma": "Email"
            },
            {
                "id": "msg2",
                "nombre": "Maria Garcia",
                "fecha": "2024-01-16",
                "reseña": "Contenido del email 2",
                "plataforma": "Email"
            }
        ]
        
        count = append_new_gmail_mcp_feedback(emails, str(csv_path))
        
        assert count == 2
        
        # Verificar contenido
        with open(csv_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        assert len(lines) == 3  # header + 2 emails
        assert "Juan Perez" in lines[1]
        assert "Maria Garcia" in lines[2]
    
    def test_no_incluye_id_en_csv(self, tmp_path):
        """Test que el CSV NO incluye la columna 'id'."""
        csv_path = tmp_path / "test_output.csv"
        
        emails = [
            {
                "id": "msg123",
                "nombre": "Test User",
                "fecha": "2024-01-01",
                "reseña": "Test",
                "plataforma": "Email"
            }
        ]
        
        append_new_gmail_mcp_feedback(emails, str(csv_path))
        
        with open(csv_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Verificar que 'id' no aparece como columna en el header
        lines = content.split('\n')
        assert "id" not in lines[0].lower()
    
    def test_crea_archivo_ids(self, tmp_path):
        """Test que crea el archivo .ids."""
        csv_path = tmp_path / "test_output.csv"
        ids_file = Path(f"{csv_path}.ids")
        
        emails = [
            {
                "id": "msg1",
                "nombre": "Test",
                "fecha": "2024-01-01",
                "reseña": "Content",
                "plataforma": "Email"
            }
        ]
        
        append_new_gmail_mcp_feedback(emails, str(csv_path))
        
        assert ids_file.exists()
        
        # Verificar contenido del archivo .ids
        with open(ids_file, 'r', encoding='utf-8') as f:
            ids = f.read().strip().split('\n')
        
        assert "msg1" in ids
    
    def test_no_duplica_emails_ya_escritos(self, tmp_path):
        """Test que no duplica emails que ya fueron escritos."""
        csv_path = tmp_path / "test_output.csv"
        
        emails = [
            {
                "id": "msg1",
                "nombre": "Juan Perez",
                "fecha": "2024-01-15",
                "reseña": "Contenido 1",
                "plataforma": "Email"
            }
        ]
        
        # Primera escritura
        count1 = append_new_gmail_mcp_feedback(emails, str(csv_path))
        assert count1 == 1
        
        # Segunda escritura con el mismo email
        count2 = append_new_gmail_mcp_feedback(emails, str(csv_path))
        assert count2 == 0  # No debe escribir duplicados
        
        # Verificar que solo hay 2 líneas (header + 1 email)
        with open(csv_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        assert len(lines) == 2
    
    def test_crea_directorios_intermedios(self, tmp_path):
        """Test que crea directorios intermedios si no existen."""
        csv_path = tmp_path / "subdir1" / "subdir2" / "test_output.csv"
        
        emails = [
            {
                "id": "msg1",
                "nombre": "Test",
                "fecha": "2024-01-01",
                "reseña": "Content",
                "plataforma": "Email"
            }
        ]
        
        count = append_new_gmail_mcp_feedback(emails, str(csv_path))
        
        assert count == 1
        assert csv_path.exists()
        assert csv_path.parent.exists()
    
    def test_devuelve_cero_con_lista_vacia(self, tmp_path):
        """Test que devuelve 0 cuando la lista de emails está vacía."""
        csv_path = tmp_path / "test_output.csv"
        
        count = append_new_gmail_mcp_feedback([], str(csv_path))
        
        assert count == 0
    
    def test_maneja_email_sin_id_sin_romper(self, tmp_path):
        """Test que maneja emails sin ID sin romper la escritura."""
        csv_path = tmp_path / "test_output.csv"
        
        emails = [
            {
                "id": "msg1",
                "nombre": "Valid User",
                "fecha": "2024-01-01",
                "reseña": "Valid content",
                "plataforma": "Email"
            },
            {
                # Email sin ID
                "nombre": "Invalid User",
                "fecha": "2024-01-02",
                "reseña": "Invalid content",
                "plataforma": "Email"
            },
            {
                "id": "msg2",
                "nombre": "Another Valid",
                "fecha": "2024-01-03",
                "reseña": "More content",
                "plataforma": "Email"
            }
        ]
        
        # Debe escribir solo los 2 válidos, ignorando el sin ID
        count = append_new_gmail_mcp_feedback(emails, str(csv_path))
        
        assert count == 2
        
        # Verificar que solo se escribieron los válidos
        with open(csv_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        assert len(lines) == 3  # header + 2 emails válidos
        assert "Valid User" in lines[1]
        assert "Another Valid" in lines[2]
    
    def test_usa_settings_por_defecto(self, tmp_path):
        """Test que usa settings.gmail_mcp_output_csv por defecto."""
        with patch('app.integrations.gmail_mcp.csv_writer.settings') as mock_settings:
            mock_settings.gmail_mcp_output_csv = str(tmp_path / "default_output.csv")
            
            emails = [
                {
                    "id": "msg1",
                    "nombre": "Test",
                    "fecha": "2024-01-01",
                    "reseña": "Content",
                    "plataforma": "Email"
                }
            ]
            
            # Llamar sin csv_path
            count = append_new_gmail_mcp_feedback(emails)
            
            assert count == 1
            assert Path(mock_settings.gmail_mcp_output_csv).exists()


class TestHelperFunctions:
    """Tests para funciones auxiliares."""
    
    def test_ids_file_path(self):
        """Test que genera correctamente la ruta del archivo .ids."""
        csv_path = "/path/to/file.csv"
        ids_path = _ids_file_path(csv_path)
        
        assert ids_path == "/path/to/file.csv.ids"
    
    def test_load_saved_ids_archivo_no_existe(self, tmp_path):
        """Test carga de IDs cuando el archivo no existe."""
        csv_path = tmp_path / "nonexistent.csv"
        
        ids = _load_saved_ids(str(csv_path))
        
        assert ids == set()
    
    def test_load_saved_ids_archivo_existe(self, tmp_path):
        """Test carga de IDs desde archivo existente."""
        csv_path = tmp_path / "test.csv"
        ids_file = Path(f"{csv_path}.ids")
        
        # Crear archivo .ids con algunos IDs
        with open(ids_file, 'w', encoding='utf-8') as f:
            f.write("msg1\n")
            f.write("msg2\n")
            f.write("msg3\n")
        
        ids = _load_saved_ids(str(csv_path))
        
        assert ids == {"msg1", "msg2", "msg3"}
    
    def test_save_ids(self, tmp_path):
        """Test guardado de IDs en archivo."""
        csv_path = tmp_path / "test.csv"
        ids_to_save = {"msg1", "msg2", "msg3"}
        
        _save_ids(str(csv_path), ids_to_save)
        
        ids_file = Path(f"{csv_path}.ids")
        assert ids_file.exists()
        
        # Verificar contenido
        with open(ids_file, 'r', encoding='utf-8') as f:
            saved_ids = {line.strip() for line in f}
        
        assert saved_ids == ids_to_save


class TestGetWriterInfo:
    """Tests para información del writer."""
    
    @patch('app.integrations.gmail_mcp.csv_writer.settings')
    def test_get_writer_info(self, mock_settings):
        """Test que devuelve información correcta."""
        mock_settings.gmail_mcp_output_csv = "data/raw/test.csv"
        
        info = get_writer_info()
        
        assert info["csv_output_path"] == "data/raw/test.csv"
        assert info["csv_header"] == ["nombre", "fecha", "reseña", "plataforma"]
        assert info["ids_file_suffix"] == ".ids"


class TestCSVHeader:
    """Tests para verificación del header CSV."""
    
    def test_csv_header_constante(self):
        """Test que el header tiene los campos correctos."""
        assert CSV_HEADER == ["nombre", "fecha", "reseña", "plataforma"]
        assert len(CSV_HEADER) == 4
        assert "id" not in CSV_HEADER