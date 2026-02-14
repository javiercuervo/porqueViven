"""Tests para generate.py."""
import os
import sys

import pytest

# Asegurar que el directorio raiz esta en el path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from generate import (
    Element,
    deduplicate_elements,
    parse_csv,
    sanitize_marca,
    validate_base_url,
)


# ─── sanitize_marca ─────────────────────────────────────────────────────────


class TestSanitizeMarca:
    def test_valid_marca(self):
        assert sanitize_marca("PA107") == "PA107"

    def test_valid_marca_with_dash(self):
        assert sanitize_marca("PA-107") == "PA-107"

    def test_strips_whitespace(self):
        assert sanitize_marca("  PA107  ") == "PA107"

    def test_empty_string(self):
        assert sanitize_marca("") is None

    def test_nan_string(self):
        assert sanitize_marca("nan") is None

    def test_path_traversal(self):
        assert sanitize_marca("../etc/passwd") is None

    def test_slash(self):
        assert sanitize_marca("PA/107") is None

    def test_backslash(self):
        assert sanitize_marca("PA\\107") is None

    def test_special_chars(self):
        assert sanitize_marca('PA<107>') is None
        assert sanitize_marca('PA"107') is None
        assert sanitize_marca("PA:107") is None
        assert sanitize_marca("PA|107") is None
        assert sanitize_marca("PA?107") is None
        assert sanitize_marca("PA*107") is None

    def test_accented_chars_allowed(self):
        assert sanitize_marca("Tuberia-1") == "Tuberia-1"


# ─── validate_base_url ──────────────────────────────────────────────────────


class TestValidateBaseUrl:
    def test_valid_https(self):
        assert validate_base_url("https://bim.porqueviven.org") == "https://bim.porqueviven.org"

    def test_valid_http(self):
        assert validate_base_url("http://localhost:8090") == "http://localhost:8090"

    def test_strips_trailing_slash(self):
        assert validate_base_url("https://bim.porqueviven.org/") == "https://bim.porqueviven.org"

    def test_invalid_url_exits(self):
        with pytest.raises(SystemExit):
            validate_base_url("ftp://example.com")

    def test_no_protocol_exits(self):
        with pytest.raises(SystemExit):
            validate_base_url("bim.porqueviven.org")


# ─── parse_csv ───────────────────────────────────────────────────────────────


class TestParseCsv:
    def test_parse_sample(self, sample_csv):
        elements = parse_csv(sample_csv)
        assert len(elements) == 3
        assert elements[0].marca == "PA001"
        assert elements[0].discipline == "Arquitectura"
        assert elements[0].ifc_class == "IfcDoor"

    def test_parse_empty_csv(self, empty_csv):
        elements = parse_csv(empty_csv)
        assert len(elements) == 0

    def test_missing_columns_raises(self, csv_missing_cols):
        with pytest.raises(ValueError, match="Columnas requeridas"):
            parse_csv(csv_missing_cols)

    def test_special_characters(self, csv_special_chars):
        elements = parse_csv(csv_special_chars)
        assert len(elements) == 1
        assert "\u00b0" in elements[0].name  # grado
        assert "\u00b1" in elements[0].nombre_tipo  # mas-menos

    def test_file_not_found(self):
        with pytest.raises(ValueError, match="Error al leer"):
            parse_csv("/nonexistent/path.csv")


# ─── deduplicate_elements ───────────────────────────────────────────────────


class TestDeduplicateElements:
    def test_no_duplicates(self, sample_csv):
        elements = parse_csv(sample_csv)
        result = deduplicate_elements(elements)
        assert len(result) == 3

    def test_removes_duplicates(self, sample_csv_duplicates):
        elements = parse_csv(sample_csv_duplicates)
        result = deduplicate_elements(elements)
        assert len(result) == 2  # PA001 (primera), VE001
        assert result[0].name == "Puerta A"  # mantiene la primera

    def test_empty_list(self):
        assert deduplicate_elements([]) == []


# ─── generate_site ───────────────────────────────────────────────────────────


class TestGenerateSite:
    def test_generates_html_files(self, sample_csv, tmp_dir, monkeypatch):
        """Verifica que se crean los archivos HTML esperados."""
        from pathlib import Path

        import generate

        monkeypatch.setattr(generate, "SITE_DIR", Path(tmp_dir) / "site")
        monkeypatch.setattr(generate, "TEMPLATE_DIR", Path(os.path.join(os.path.dirname(__file__), "..", "templates")))

        elements = parse_csv(sample_csv)
        generate.generate_site(elements, "Test Project")

        site = Path(tmp_dir) / "site"
        assert (site / "index.html").exists()
        assert (site / "e" / "PA001" / "index.html").exists()
        assert (site / "e" / "VE001" / "index.html").exists()
        assert (site / "e" / "PI001" / "index.html").exists()

    def test_html_contains_marca(self, sample_csv, tmp_dir, monkeypatch):
        """Verifica que el HTML contiene la marca del elemento."""
        from pathlib import Path

        import generate

        monkeypatch.setattr(generate, "SITE_DIR", Path(tmp_dir) / "site")
        monkeypatch.setattr(generate, "TEMPLATE_DIR", Path(os.path.join(os.path.dirname(__file__), "..", "templates")))

        elements = parse_csv(sample_csv)
        generate.generate_site(elements, "Test Project")

        html = (Path(tmp_dir) / "site" / "e" / "PA001" / "index.html").read_text()
        assert "PA001" in html
        assert "Test Project" in html
        assert "Puerta 1 hoja" in html

    def test_index_contains_search(self, sample_csv, tmp_dir, monkeypatch):
        """Verifica que el indice tiene el buscador."""
        from pathlib import Path

        import generate

        monkeypatch.setattr(generate, "SITE_DIR", Path(tmp_dir) / "site")
        monkeypatch.setattr(generate, "TEMPLATE_DIR", Path(os.path.join(os.path.dirname(__file__), "..", "templates")))

        elements = parse_csv(sample_csv)
        generate.generate_site(elements, "Test Project")

        html = (Path(tmp_dir) / "site" / "index.html").read_text()
        assert 'id="search"' in html
        assert "Buscar" in html

    def test_404_page_generated(self, sample_csv, tmp_dir, monkeypatch):
        """Verifica que se genera la pagina 404."""
        from pathlib import Path

        import generate

        monkeypatch.setattr(generate, "SITE_DIR", Path(tmp_dir) / "site")
        monkeypatch.setattr(generate, "TEMPLATE_DIR", Path(os.path.join(os.path.dirname(__file__), "..", "templates")))

        elements = parse_csv(sample_csv)
        generate.generate_site(elements, "Test Project")

        assert (Path(tmp_dir) / "site" / "404.html").exists()


# ─── generate_pdf ────────────────────────────────────────────────────────────


class TestGeneratePdf:
    def test_generates_valid_pdf(self, sample_csv, tmp_dir, monkeypatch):
        """Verifica que se genera un PDF valido (magic bytes %PDF)."""
        from pathlib import Path

        import generate

        monkeypatch.setattr(generate, "PDF_DIR", Path(tmp_dir) / "pdf")

        elements = parse_csv(sample_csv)
        pdf_path = generate.generate_pdf(elements, "Test Project")

        assert os.path.exists(pdf_path)
        with open(pdf_path, "rb") as f:
            magic = f.read(4)
        assert magic == b"%PDF"

    def test_pdf_with_discipline_filter(self, sample_csv, tmp_dir, monkeypatch):
        """Verifica que se genera PDF con filtro de disciplina."""
        from pathlib import Path

        import generate

        monkeypatch.setattr(generate, "PDF_DIR", Path(tmp_dir) / "pdf")

        elements = parse_csv(sample_csv)
        arq = [e for e in elements if e.discipline == "Arquitectura"]
        pdf_path = generate.generate_pdf(arq, "Test Project", discipline="Arquitectura")

        assert os.path.exists(pdf_path)
        assert "Arquitectura" in os.path.basename(pdf_path)


# ─── Element dataclass ──────────────────────────────────────────────────────


class TestElement:
    def test_default_values(self):
        el = Element(ifc_guid="G1", name="Test", marca="T1", discipline="Arq")
        assert el.nombre_tipo == ""
        assert el.operacion == ""
        assert el.custom_properties == {}

    def test_custom_properties(self):
        el = Element(
            ifc_guid="G1", name="Test", marca="T1", discipline="Arq",
            custom_properties={"Color": "Rojo"},
        )
        assert el.custom_properties["Color"] == "Rojo"
