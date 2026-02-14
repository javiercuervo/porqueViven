"""Fixtures compartidas para tests."""
import csv
import os
import tempfile

import pytest


@pytest.fixture
def tmp_dir():
    """Directorio temporal que se limpia al terminar."""
    with tempfile.TemporaryDirectory() as d:
        yield d


@pytest.fixture
def sample_csv(tmp_dir):
    """Crea un CSV de ejemplo y devuelve su path."""
    path = os.path.join(tmp_dir, "test.csv")
    rows = [
        ["IfcGUID", "Name", "Marca", "Nombre de tipo", "Disciplina", "IFC Class", "Category", "Operacion"],
        ["GUID001", "Puerta 1 hoja", "PA001", "210x120", "Arquitectura", "IfcDoor", "Puertas", "Abatible"],
        ["GUID002", "Ventana fija", "VE001", "120x150", "Arquitectura", "IfcWindow", "Ventanas", "Fija"],
        ["GUID003", "Pilar HEB200", "PI001", "HEB200", "Estructura", "IfcColumn", "Pilares", ""],
    ]
    with open(path, "w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerows(rows)
    return path


@pytest.fixture
def sample_csv_duplicates(tmp_dir):
    """CSV con marcas duplicadas."""
    path = os.path.join(tmp_dir, "dupes.csv")
    rows = [
        ["IfcGUID", "Name", "Marca", "Nombre de tipo", "Disciplina", "IFC Class", "Category", "Operacion"],
        ["GUID001", "Puerta A", "PA001", "210x120", "Arquitectura", "IfcDoor", "Puertas", ""],
        ["GUID002", "Puerta B", "PA001", "210x120", "Arquitectura", "IfcDoor", "Puertas", ""],
        ["GUID003", "Ventana A", "VE001", "120x150", "Arquitectura", "IfcWindow", "Ventanas", ""],
    ]
    with open(path, "w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerows(rows)
    return path


@pytest.fixture
def empty_csv(tmp_dir):
    """CSV con solo cabeceras."""
    path = os.path.join(tmp_dir, "empty.csv")
    with open(path, "w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow(
            ["IfcGUID", "Name", "Marca", "Nombre de tipo", "Disciplina", "IFC Class", "Category", "Operacion"]
        )
    return path


@pytest.fixture
def csv_missing_cols(tmp_dir):
    """CSV sin columnas requeridas."""
    path = os.path.join(tmp_dir, "bad.csv")
    with open(path, "w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerows([
            ["Foo", "Bar"],
            ["a", "b"],
        ])
    return path


@pytest.fixture
def csv_special_chars(tmp_dir):
    """CSV con caracteres especiales (acentos, grados)."""
    path = os.path.join(tmp_dir, "special.csv")
    rows = [
        ["IfcGUID", "Name", "Marca", "Nombre de tipo", "Disciplina", "IFC Class", "Category", "Operacion"],
        ["GUID010", "Tuberia DN50 a 90\u00b0", "TB001", "DN50 \u00b1 2mm", "Saneamiento-Fontaneria-Geotermia", "IfcPipeSegment", "Tuberias", ""],
    ]
    with open(path, "w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerows(rows)
    return path
