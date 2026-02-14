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


@pytest.fixture
def csv_alt_column_names(tmp_dir):
    """CSV con nombres de columna alternativos (ingles)."""
    path = os.path.join(tmp_dir, "alt_cols.csv")
    rows = [
        ["GlobalId", "name", "Mark", "Type Name", "discipline", "IfcClass", "category", "Operation"],
        ["GUID_ALT1", "Door Standard", "DA001", "80x210", "Arquitectura", "IfcDoor", "Puertas", "Swing"],
    ]
    with open(path, "w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerows(rows)
    return path


@pytest.fixture
def csv_with_nan_values(tmp_dir):
    """CSV con valores nan en GUID, marca y campos opcionales."""
    path = os.path.join(tmp_dir, "nan_vals.csv")
    rows = [
        ["IfcGUID", "Name", "Marca", "Nombre de tipo", "Disciplina", "IFC Class", "Category", "Operacion"],
        ["GUID_N1", "Puerta normal", "PN001", "nan", "Arquitectura", "IfcDoor", "Puertas", "nan"],
        ["nan", "Sin GUID", "PN002", "tipo", "Arquitectura", "IfcDoor", "Puertas", ""],
        ["GUID_N3", "Otra", "nan", "tipo", "Arquitectura", "IfcDoor", "Puertas", ""],
    ]
    with open(path, "w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerows(rows)
    return path


@pytest.fixture
def csv_all_empty_optional(tmp_dir):
    """CSV con elemento que tiene todos los campos opcionales vacios."""
    path = os.path.join(tmp_dir, "empty_optional.csv")
    rows = [
        ["IfcGUID", "Name", "Marca", "Nombre de tipo", "Disciplina", "IFC Class", "Category", "Operacion"],
        ["GUID_EO1", "Elemento basico", "EB001", "", "Arquitectura", "", "", ""],
    ]
    with open(path, "w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerows(rows)
    return path


@pytest.fixture
def csv_long_name(tmp_dir):
    """CSV con elemento de nombre muy largo (250 caracteres)."""
    path = os.path.join(tmp_dir, "long_name.csv")
    long_name = "A" * 250
    rows = [
        ["IfcGUID", "Name", "Marca", "Nombre de tipo", "Disciplina", "IFC Class", "Category", "Operacion"],
        ["GUID_LN1", long_name, "LN001", "Tipo largo " + "B" * 100, "Arquitectura", "IfcDoor", "Puertas", "Abatible"],
    ]
    with open(path, "w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerows(rows)
    return path


@pytest.fixture
def large_csv(tmp_dir):
    """CSV con 120 elementos para tests de dataset grande."""
    path = os.path.join(tmp_dir, "large.csv")
    header = ["IfcGUID", "Name", "Marca", "Nombre de tipo", "Disciplina", "IFC Class", "Category", "Operacion"]
    disciplines = ["Arquitectura", "Estructura", "Saneamiento-Fontaneria-Geotermia",
                    "Climatizacion-Ventilacion", "Electricidad", "PCI-Gases Medicinales"]
    rows_data = []
    for i in range(120):
        disc = disciplines[i % len(disciplines)]
        rows_data.append([
            f"GUID_{i:04d}", f"Elemento {i}", f"EL{i:04d}",
            f"Tipo {i}", disc, "IfcWall", "Muros", ""
        ])
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows_data)
    return path
