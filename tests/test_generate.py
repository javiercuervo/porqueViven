"""Tests para generate.py."""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from generate import (
    Element,
    _trunc,
    deduplicate_elements,
    generate_firebase_config,
    generate_pdf,
    generate_site,
    parse_csv,
    print_summary,
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


# ─── _trunc ──────────────────────────────────────────────────────────────────


class TestTrunc:
    def test_short_string_unchanged(self):
        assert _trunc("Hello", 30) == "Hello"

    def test_empty_string(self):
        assert _trunc("", 30) == ""

    def test_none_returns_empty(self):
        assert _trunc(None, 30) == ""

    def test_exact_length(self):
        assert _trunc("A" * 30, 30) == "A" * 30

    def test_one_over_truncates(self):
        result = _trunc("A" * 31, 30)
        assert result == "A" * 28 + ".."
        assert len(result) == 30

    def test_very_long_string(self):
        result = _trunc("X" * 200, 30)
        assert len(result) == 30
        assert result.endswith("..")

    def test_default_n_is_30(self):
        assert _trunc("A" * 31) == "A" * 28 + ".."

    def test_custom_n(self):
        result = _trunc("Hello World", 5)
        assert result == "Hel.."
        assert len(result) == 5


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
        assert "\u00b0" in elements[0].name
        assert "\u00b1" in elements[0].nombre_tipo

    def test_file_not_found(self):
        with pytest.raises(ValueError, match="Error al leer"):
            parse_csv("/nonexistent/path.csv")

    def test_alternative_column_names(self, csv_alt_column_names):
        """Verifica resolucion COLUMN_MAP para aliases en ingles."""
        elements = parse_csv(csv_alt_column_names)
        assert len(elements) == 1
        assert elements[0].marca == "DA001"
        assert elements[0].ifc_guid == "GUID_ALT1"

    def test_nan_values_filtered(self, csv_with_nan_values):
        """Filas con nan en GUID o marca se descartan."""
        elements = parse_csv(csv_with_nan_values)
        assert len(elements) == 1
        assert elements[0].marca == "PN001"

    def test_all_optional_fields_empty(self, csv_all_empty_optional):
        """Elemento con campos opcionales vacios se parsea correctamente."""
        elements = parse_csv(csv_all_empty_optional)
        assert len(elements) == 1
        el = elements[0]
        assert el.marca == "EB001"
        assert el.nombre_tipo == ""
        assert el.operacion == ""
        assert el.ifc_class == ""
        assert el.category == ""

    def test_long_name_preserved(self, csv_long_name):
        """Nombres muy largos se preservan completos."""
        elements = parse_csv(csv_long_name)
        assert len(elements) == 1
        assert len(elements[0].name) == 250


# ─── deduplicate_elements ───────────────────────────────────────────────────


class TestDeduplicateElements:
    def test_no_duplicates(self, sample_csv):
        elements = parse_csv(sample_csv)
        result = deduplicate_elements(elements)
        assert len(result) == 3

    def test_removes_duplicates(self, sample_csv_duplicates):
        elements = parse_csv(sample_csv_duplicates)
        result = deduplicate_elements(elements)
        assert len(result) == 2
        assert result[0].name == "Puerta A"

    def test_empty_list(self):
        assert deduplicate_elements([]) == []


# ─── generate_firebase_config ────────────────────────────────────────────────


class TestGenerateFirebaseConfig:
    def test_generates_valid_json(self, tmp_dir, monkeypatch):
        """Verifica que firebase.json es JSON valido con estructura esperada."""
        import json
        monkeypatch.chdir(tmp_dir)
        generate_firebase_config()
        path = os.path.join(tmp_dir, "firebase.json")
        assert os.path.exists(path)
        with open(path) as f:
            config = json.load(f)
        assert "hosting" in config
        assert config["hosting"]["public"] == "output/site"
        assert config["hosting"]["cleanUrls"] is True


# ─── print_summary ───────────────────────────────────────────────────────────


class TestPrintSummary:
    def test_prints_discipline_counts(self, capsys):
        """Verifica que imprime desglose por disciplina."""
        elements = [
            Element(ifc_guid="G1", name="A", marca="M1", discipline="Arquitectura"),
            Element(ifc_guid="G2", name="B", marca="M2", discipline="Arquitectura"),
            Element(ifc_guid="G3", name="C", marca="M3", discipline="Estructura"),
        ]
        print_summary(elements)
        captured = capsys.readouterr()
        assert "Arquitectura: 2" in captured.out
        assert "Estructura: 1" in captured.out
        assert "TOTAL: 3" in captured.out

    def test_empty_list(self, capsys):
        """Resumen con lista vacia."""
        print_summary([])
        captured = capsys.readouterr()
        assert "TOTAL: 0" in captured.out


# ─── generate_site ───────────────────────────────────────────────────────────


class TestGenerateSite:
    def _setup(self, tmp_dir, monkeypatch):
        from pathlib import Path
        import generate
        monkeypatch.setattr(generate, "SITE_DIR", Path(tmp_dir) / "site")
        monkeypatch.setattr(generate, "TEMPLATE_DIR", Path(os.path.join(os.path.dirname(__file__), "..", "templates")))
        return Path(tmp_dir) / "site"

    def test_generates_html_files(self, sample_csv, tmp_dir, monkeypatch):
        site = self._setup(tmp_dir, monkeypatch)
        elements = parse_csv(sample_csv)
        generate_site(elements, "Test Project")
        assert (site / "index.html").exists()
        assert (site / "e" / "PA001" / "index.html").exists()
        assert (site / "e" / "VE001" / "index.html").exists()
        assert (site / "e" / "PI001" / "index.html").exists()

    def test_html_contains_marca(self, sample_csv, tmp_dir, monkeypatch):
        site = self._setup(tmp_dir, monkeypatch)
        elements = parse_csv(sample_csv)
        generate_site(elements, "Test Project")
        html = (site / "e" / "PA001" / "index.html").read_text()
        assert "PA001" in html
        assert "Test Project" in html
        assert "Puerta 1 hoja" in html

    def test_index_contains_search(self, sample_csv, tmp_dir, monkeypatch):
        site = self._setup(tmp_dir, monkeypatch)
        elements = parse_csv(sample_csv)
        generate_site(elements, "Test Project")
        html = (site / "index.html").read_text()
        assert 'id="search"' in html
        assert "Buscar" in html

    def test_404_page_generated(self, sample_csv, tmp_dir, monkeypatch):
        site = self._setup(tmp_dir, monkeypatch)
        elements = parse_csv(sample_csv)
        generate_site(elements, "Test Project")
        assert (site / "404.html").exists()

    def test_element_html_has_brand_colors(self, sample_csv, tmp_dir, monkeypatch):
        """Verifica que el HTML generado usa los colores de marca."""
        site = self._setup(tmp_dir, monkeypatch)
        elements = parse_csv(sample_csv)
        generate_site(elements, "Test Project")
        html = (site / "e" / "PA001" / "index.html").read_text()
        assert "#0C4DA2" in html
        assert "#770E75" in html
        assert "brand-porque" in html

    def test_index_has_all_elements(self, sample_csv, tmp_dir, monkeypatch):
        """La pagina indice contiene los 3 elementos."""
        site = self._setup(tmp_dir, monkeypatch)
        elements = parse_csv(sample_csv)
        generate_site(elements, "Test Project")
        html = (site / "index.html").read_text()
        assert "PA001" in html
        assert "VE001" in html
        assert "PI001" in html

    def test_site_large_dataset(self, large_csv, tmp_dir, monkeypatch):
        """Generacion con 120 elementos."""
        site = self._setup(tmp_dir, monkeypatch)
        elements = parse_csv(large_csv)
        generate_site(elements, "Large Project")
        assert (site / "index.html").exists()
        assert (site / "e" / "EL0000" / "index.html").exists()
        assert (site / "e" / "EL0119" / "index.html").exists()


# ─── generate_pdf ────────────────────────────────────────────────────────────


class TestGeneratePdf:
    def _setup(self, tmp_dir, monkeypatch):
        from pathlib import Path
        import generate
        monkeypatch.setattr(generate, "PDF_DIR", Path(tmp_dir) / "pdf")

    def test_generates_valid_pdf(self, sample_csv, tmp_dir, monkeypatch):
        self._setup(tmp_dir, monkeypatch)
        elements = parse_csv(sample_csv)
        pdf_path = generate_pdf(elements, "Test Project")
        assert os.path.exists(pdf_path)
        with open(pdf_path, "rb") as f:
            assert f.read(4) == b"%PDF"

    def test_pdf_with_discipline_filter(self, sample_csv, tmp_dir, monkeypatch):
        self._setup(tmp_dir, monkeypatch)
        elements = parse_csv(sample_csv)
        arq = [e for e in elements if e.discipline == "Arquitectura"]
        pdf_path = generate_pdf(arq, "Test Project", discipline="Arquitectura")
        assert os.path.exists(pdf_path)
        assert "Arquitectura" in os.path.basename(pdf_path)

    def test_pdf_file_size_nonzero(self, sample_csv, tmp_dir, monkeypatch):
        """PDF con contenido real (no solo cabecera)."""
        self._setup(tmp_dir, monkeypatch)
        elements = parse_csv(sample_csv)
        pdf_path = generate_pdf(elements, "Test Project")
        assert os.path.getsize(pdf_path) > 1000

    def test_pdf_with_long_names(self, csv_long_name, tmp_dir, monkeypatch):
        """PDF no falla con nombres muy largos."""
        self._setup(tmp_dir, monkeypatch)
        elements = parse_csv(csv_long_name)
        pdf_path = generate_pdf(elements, "Test Project")
        assert os.path.exists(pdf_path)

    def test_pdf_with_all_empty_optional(self, csv_all_empty_optional, tmp_dir, monkeypatch):
        """PDF funciona con datos minimos."""
        self._setup(tmp_dir, monkeypatch)
        elements = parse_csv(csv_all_empty_optional)
        pdf_path = generate_pdf(elements, "Test Project")
        assert os.path.exists(pdf_path)
        with open(pdf_path, "rb") as f:
            assert f.read(4) == b"%PDF"

    def test_pdf_large_dataset(self, large_csv, tmp_dir, monkeypatch):
        """PDF con 120 elementos (multiples paginas)."""
        self._setup(tmp_dir, monkeypatch)
        elements = parse_csv(large_csv)
        assert len(elements) == 120
        pdf_path = generate_pdf(elements, "Large Project")
        assert os.path.exists(pdf_path)
        assert os.path.getsize(pdf_path) > 10000


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


# ─── Integration ─────────────────────────────────────────────────────────────


class TestIntegration:
    """Tests de integracion: CSV -> pipeline completo (HTML + PDF)."""

    def test_full_pipeline_csv(self, sample_csv, tmp_dir, monkeypatch):
        """End-to-end: parsear CSV, generar sitio, generar PDF."""
        from pathlib import Path
        import generate

        monkeypatch.setattr(generate, "SITE_DIR", Path(tmp_dir) / "site")
        monkeypatch.setattr(generate, "PDF_DIR", Path(tmp_dir) / "pdf")
        monkeypatch.setattr(generate, "TEMPLATE_DIR", Path(os.path.join(os.path.dirname(__file__), "..", "templates")))

        elements = parse_csv(sample_csv)
        assert len(elements) == 3
        elements = deduplicate_elements(elements)
        assert len(elements) == 3

        generate_site(elements, "Integration Test")
        site = Path(tmp_dir) / "site"
        assert (site / "index.html").exists()
        for el in elements:
            assert (site / "e" / el.marca / "index.html").exists()

        pdf_path = generate_pdf(elements, "Integration Test")
        assert os.path.exists(pdf_path)
        with open(pdf_path, "rb") as f:
            assert f.read(4) == b"%PDF"

    def test_full_pipeline_large(self, large_csv, tmp_dir, monkeypatch):
        """End-to-end con 120 elementos."""
        from pathlib import Path
        import generate

        monkeypatch.setattr(generate, "SITE_DIR", Path(tmp_dir) / "site")
        monkeypatch.setattr(generate, "PDF_DIR", Path(tmp_dir) / "pdf")
        monkeypatch.setattr(generate, "TEMPLATE_DIR", Path(os.path.join(os.path.dirname(__file__), "..", "templates")))

        elements = parse_csv(large_csv)
        elements = deduplicate_elements(elements)
        generate_site(elements, "Large Integration")
        pdf_path = generate_pdf(elements, "Large Integration")

        assert (Path(tmp_dir) / "site" / "index.html").exists()
        assert os.path.exists(pdf_path)
        assert os.path.getsize(pdf_path) > 10000

    def test_pipeline_with_discipline_filter(self, sample_csv, tmp_dir, monkeypatch):
        """CSV -> filtro por disciplina -> generar."""
        from pathlib import Path
        import generate

        monkeypatch.setattr(generate, "SITE_DIR", Path(tmp_dir) / "site")
        monkeypatch.setattr(generate, "PDF_DIR", Path(tmp_dir) / "pdf")
        monkeypatch.setattr(generate, "TEMPLATE_DIR", Path(os.path.join(os.path.dirname(__file__), "..", "templates")))

        elements = parse_csv(sample_csv)
        arq = [e for e in elements if e.discipline == "Arquitectura"]
        assert len(arq) == 2

        generate_site(arq, "Arq Only")
        pdf_path = generate_pdf(arq, "Arq Only", discipline="Arquitectura")

        site = Path(tmp_dir) / "site"
        assert (site / "e" / "PA001" / "index.html").exists()
        assert (site / "e" / "VE001" / "index.html").exists()
        assert not (site / "e" / "PI001" / "index.html").exists()
        assert os.path.exists(pdf_path)
