"""
Lector de archivos CSV.

Proporciona funcionalidad para leer CSVs sin usar Pandas,
utilizando el módulo csv estándar de Python.
"""

import csv
import io
from pathlib import Path
from typing import Iterator, Dict, Any, List


class CSVReader:
    """
    Lector de archivos CSV con validación básica.

    Lee archivos CSV y devuelve cada fila como diccionario.
    Soporta: delimitadores variables (,  ;  tab), BOM UTF-8,
    y filas con comillas externas (patrón "campo1,campo2,...").
    """

    EXPECTED_COLUMNS = {"nombre", "fecha", "reseña", "plataforma"}

    # ------------------------------------------------------------------ #
    # Helpers internos                                                     #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _clean_fieldnames(fieldnames: list) -> list:
        """Elimina BOM y espacios sobrantes de los nombres de columna."""
        return [f.strip().lstrip('﻿') if f else f for f in fieldnames]

    @staticmethod
    def _unwrap_rows(lines: list) -> list:
        """
        Elimina comillas externas de filas que tienen el patrón:
            "campo1,campo2,""texto con comas"",campo4"
        dejando la fila como CSV estándar válido.
        El encabezado (primera línea) nunca se toca.
        """
        if not lines:
            return lines
        result = [lines[0]]
        for line in lines[1:]:
            stripped = line.rstrip('\r\n')
            if len(stripped) >= 2 and stripped[0] == '"' and stripped[-1] == '"':
                inner = stripped[1:-1].replace('""', '"')
                result.append(inner + '\n')
            else:
                result.append(line)
        return result

    @staticmethod
    def _detect_delimiter(content: str) -> str:
        """
        Devuelve el delimitador que produce todas las columnas esperadas.
        Fallback: coma.
        """
        for delimiter in [',', ';', '\t', '|']:
            try:
                first_line = content.split('\n')[0]
                cols = set(
                    CSVReader._clean_fieldnames(
                        next(csv.reader([first_line], delimiter=delimiter))
                    )
                )
                if CSVReader.EXPECTED_COLUMNS.issubset(cols):
                    return delimiter
            except Exception:
                continue
        return ','

    @staticmethod
    def _prepare(file_path: Path, encoding: str):
        """
        Lee el archivo, aplica unwrap de filas y devuelve
        (StringIO listo para csv.DictReader, delimitador).
        """
        with open(file_path, mode='r', encoding=encoding, newline='') as f:
            lines = f.readlines()

        lines = CSVReader._unwrap_rows(lines)
        content = ''.join(lines)
        delimiter = CSVReader._detect_delimiter(content)
        return io.StringIO(content), delimiter

    # ------------------------------------------------------------------ #
    # API pública                                                          #
    # ------------------------------------------------------------------ #

    @staticmethod
    def read_csv(file_path: str | Path, encoding: str = "utf-8") -> Iterator[Dict[str, Any]]:
        file_path = Path(file_path)

        if not file_path.exists():
            raise FileNotFoundError(f"Archivo no encontrado: {file_path}")
        if file_path.suffix.lower() != '.csv':
            raise ValueError(f"El archivo debe ser CSV: {file_path}")

        buf, delimiter = CSVReader._prepare(file_path, encoding)
        reader = csv.DictReader(buf, delimiter=delimiter)

        if reader.fieldnames is None:
            raise ValueError(f"El CSV está vacío o mal formado: {file_path}")

        reader.fieldnames = CSVReader._clean_fieldnames(list(reader.fieldnames))
        csv_columns = set(reader.fieldnames)
        missing = CSVReader.EXPECTED_COLUMNS - csv_columns
        if missing:
            raise ValueError(
                f"Columnas faltantes en {file_path.name}: {missing}. "
                f"Encontradas: {csv_columns}"
            )

        for row_number, row in enumerate(reader, start=2):
            row['_row_number'] = row_number
            row['_source_file'] = str(file_path.name)
            yield row

    @staticmethod
    def read_csv_batch(file_path: str | Path, encoding: str = "utf-8") -> List[Dict[str, Any]]:
        return list(CSVReader.read_csv(file_path, encoding))

    @staticmethod
    def validate_csv_structure(file_path: str | Path, encoding: str = "utf-8") -> bool:
        file_path = Path(file_path)

        if not file_path.exists():
            raise FileNotFoundError(f"Archivo no encontrado: {file_path}")

        buf, delimiter = CSVReader._prepare(file_path, encoding)
        reader = csv.DictReader(buf, delimiter=delimiter)

        if reader.fieldnames is None:
            raise ValueError(f"El CSV está vacío o mal formado: {file_path}")

        cols = set(CSVReader._clean_fieldnames(list(reader.fieldnames)))
        missing = CSVReader.EXPECTED_COLUMNS - cols
        if missing:
            raise ValueError(
                f"Columnas faltantes: {missing}. "
                f"Encontradas: {cols}"
            )

        return True
