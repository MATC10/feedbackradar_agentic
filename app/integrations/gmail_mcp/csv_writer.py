"""
CSV Writer para Gmail MCP Collector

Escribe emails obtenidos via Gmail MCP en formato CSV compatible con FeedbackRadar.
Maneja deduplicación mediante archivo .ids para evitar duplicados.
"""

import csv
import logging
import os
from pathlib import Path
from typing import Optional

from app.core.config import settings

logger = logging.getLogger(__name__)

# Header exacto del CSV compatible con FeedbackRadar
CSV_HEADER = ["nombre", "fecha", "reseña", "plataforma"]


def append_new_gmail_mcp_feedback(
    emails: list[dict],
    csv_path: Optional[str] = None
) -> tuple[int, list[dict]]:
    """
    Añade emails nuevos al CSV de FeedbackRadar, evitando duplicados.

    Args:
        emails: Lista de emails con formato:
            {
                "id": str,
                "nombre": str,
                "fecha": str (YYYY-MM-DD),
                "reseña": str,
                "plataforma": str
            }
        csv_path: Ruta del CSV de salida (usa settings si None)

    Returns:
        tuple[int, list[dict]]: (número de emails escritos, lista de emails nuevos)

    Raises:
        OSError: Si hay error al crear directorios o escribir archivos
    """
    # Usar path de configuración si no se proporciona
    if csv_path is None:
        csv_path = settings.gmail_mcp_output_csv
    
    logger.info(f"Iniciando escritura de {len(emails)} emails a {csv_path}")
    
    # Si no hay emails, retornar 0
    if not emails:
        logger.info("No hay emails para escribir")
        return 0, []
    
    # Crear directorio si no existe
    csv_file = Path(csv_path)
    csv_file.parent.mkdir(parents=True, exist_ok=True)
    logger.debug(f"Directorio asegurado: {csv_file.parent}")
    
    # Cargar IDs ya guardados
    saved_ids = _load_saved_ids(csv_path)
    logger.debug(f"IDs ya guardados: {len(saved_ids)}")
    
    # Filtrar emails nuevos y válidos
    new_emails = []
    for email in emails:
        # Validar que tenga ID
        if "id" not in email or not email["id"]:
            logger.warning(f"Email sin ID válido, ignorando: {email.get('nombre', 'unknown')}")
            continue
        
        # Verificar si es nuevo
        if email["id"] not in saved_ids:
            new_emails.append(email)
        else:
            logger.debug(f"Email duplicado ignorado: {email['id']}")
    
    logger.info(f"Emails nuevos a escribir: {len(new_emails)}")

    if not new_emails:
        return 0, []
    
    # Determinar si necesitamos escribir header
    write_header = not csv_file.exists()
    
    # Escribir emails al CSV
    try:
        with open(csv_file, mode='a', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=CSV_HEADER)
            
            # Escribir header si es archivo nuevo
            if write_header:
                writer.writeheader()
                logger.debug("Header CSV escrito")
            
            # Escribir emails (solo campos del header, no 'id')
            for email in new_emails:
                row = {
                    "nombre": email.get("nombre", ""),
                    "fecha": email.get("fecha", ""),
                    "reseña": email.get("reseña", ""),
                    "plataforma": email.get("plataforma", "Email")
                }
                writer.writerow(row)
        
        logger.info(f"Escritos {len(new_emails)} emails nuevos en {csv_path}")

        # Actualizar archivo de IDs
        new_ids = {email["id"] for email in new_emails}
        saved_ids.update(new_ids)
        _save_ids(csv_path, saved_ids)

        return len(new_emails), new_emails

    except Exception as e:
        logger.error(f"Error al escribir CSV: {e}")
        raise


def _ids_file_path(csv_path: str) -> str:
    """
    Obtiene la ruta del archivo .ids asociado al CSV.
    
    Args:
        csv_path: Ruta del archivo CSV
        
    Returns:
        str: Ruta del archivo .ids (csv_path + '.ids')
    """
    return f"{csv_path}.ids"


def _load_saved_ids(csv_path: str) -> set[str]:
    """
    Carga los IDs de emails ya guardados desde el archivo .ids.
    
    Args:
        csv_path: Ruta del archivo CSV
        
    Returns:
        set[str]: Conjunto de IDs ya guardados (vacío si no existe el archivo)
    """
    ids_file = _ids_file_path(csv_path)
    
    if not os.path.exists(ids_file):
        logger.debug(f"Archivo .ids no existe: {ids_file}")
        return set()
    
    try:
        with open(ids_file, 'r', encoding='utf-8') as f:
            ids = {line.strip() for line in f if line.strip()}
        logger.debug(f"Cargados {len(ids)} IDs desde {ids_file}")
        return ids
    except Exception as e:
        logger.warning(f"Error al cargar IDs desde {ids_file}: {e}")
        return set()


def _save_ids(csv_path: str, ids: set[str]) -> None:
    """
    Guarda los IDs de emails en el archivo .ids.
    
    Args:
        csv_path: Ruta del archivo CSV
        ids: Conjunto de IDs a guardar
        
    Raises:
        OSError: Si hay error al escribir el archivo
    """
    ids_file = _ids_file_path(csv_path)
    
    try:
        with open(ids_file, 'w', encoding='utf-8') as f:
            for id_ in sorted(ids):  # Ordenar para consistencia
                f.write(f"{id_}\n")
        logger.debug(f"Guardados {len(ids)} IDs en {ids_file}")
    except Exception as e:
        logger.error(f"Error al guardar IDs en {ids_file}: {e}")
        raise


# Función auxiliar para obtener información del writer
def get_writer_info() -> dict:
    """
    Devuelve información sobre la configuración del CSV writer.
    
    Returns:
        dict: Configuración actual del writer
    """
    return {
        "csv_output_path": settings.gmail_mcp_output_csv,
        "csv_header": CSV_HEADER,
        "ids_file_suffix": ".ids",
    }