#!/usr/bin/env python3
"""
Generador de QR para elementos BIM - porqueViven.org

Uso:
    python generate.py data/elementos.csv --project "CAPPI Edificio"
    python generate.py data/modelo.ifc --project "CAPPI Edificio"
    python generate.py data/elementos.csv -p "CAPPI" -d Arquitectura
    python generate.py --list-disciplines

Genera:
    output/pdf/  - PDFs con etiquetas QR para imprimir
    output/site/ - Páginas HTML estáticas para Firebase Hosting
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import jinja2
import pandas as pd
from reportlab.graphics.barcode.qr import QrCodeWidget
from reportlab.graphics.shapes import Drawing
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

BASE_URL = os.environ.get("BASE_URL", "https://bim.porqueviven.org")
OUTPUT_DIR = Path("output")
SITE_DIR = OUTPUT_DIR / "site"
PDF_DIR = OUTPUT_DIR / "pdf"
TEMPLATE_DIR = Path("templates")


# ─── Data model ───────────────────────────────────────────────────────────────


@dataclass
class Element:
    ifc_guid: str
    name: str
    marca: str
    discipline: str
    nombre_tipo: str = ""
    tipo_ifc_guid: str = ""
    operacion: str = ""
    ifc_class: str = ""
    category: str = ""
    custom_properties: dict = field(default_factory=dict)


# ─── Validación ───────────────────────────────────────────────────────────────

# Caracteres prohibidos en marca (usada como nombre de directorio)
_MARCA_INVALID = re.compile(r'[/\\<>:"|?*\x00-\x1f]')


def sanitize_marca(marca: str) -> str | None:
    """Valida y limpia una marca. Retorna None si es inválida."""
    marca = marca.strip()
    if not marca or marca == "nan":
        return None
    if ".." in marca:
        return None
    if _MARCA_INVALID.search(marca):
        return None
    return marca


def validate_base_url(url: str) -> str:
    """Valida que la URL base tenga formato correcto."""
    url = url.strip().rstrip("/")
    if not url.startswith(("http://", "https://")):
        print(f"ERROR: BASE_URL debe empezar por http:// o https://: {url}")
        sys.exit(1)
    return url


def deduplicate_elements(elements: list["Element"]) -> list["Element"]:
    """Elimina elementos con marca duplicada, mantiene el primero. Reporta duplicados."""
    seen = {}
    unique = []
    duplicates = []
    for el in elements:
        if el.marca in seen:
            duplicates.append(el.marca)
        else:
            seen[el.marca] = True
            unique.append(el)
    if duplicates:
        print(f"  AVISO: {len(duplicates)} marcas duplicadas encontradas (se mantiene la primera):")
        for m in sorted(set(duplicates))[:10]:
            print(f"    - {m}")
        if len(set(duplicates)) > 10:
            print(f"    ... y {len(set(duplicates)) - 10} más")
    return unique


# ─── Parsers ──────────────────────────────────────────────────────────────────

COLUMN_MAP = {
    "ifc_guid": ["IfcGUID", "ifc_guid", "ifcguid", "GlobalId", "GUID"],
    "name": ["Name", "name", "Nombre", "nombre"],
    "marca": ["Marca", "marca", "Mark", "mark"],
    "nombre_tipo": ["Nombre de tipo", "nombre_tipo", "Type Name", "NombreTipo"],
    "tipo_ifc_guid": ["Tipo IfcGUID", "tipo_ifc_guid", "Type IfcGUID"],
    "operacion": ["Operacion", "operacion", "Operación", "Operation"],
    "discipline": ["Discipline", "discipline", "Disciplina", "disciplina"],
    "ifc_class": ["IFC Class", "ifc_class", "IfcClass", "Clase IFC"],
    "category": ["Category", "category", "Categoría", "categoria"],
}

DISCIPLINE_IFC = {
    "Arquitectura": [
        "IfcWall", "IfcWallStandardCase", "IfcDoor", "IfcWindow", "IfcSlab",
        "IfcRoof", "IfcStair", "IfcStairFlight", "IfcRailing", "IfcCovering",
        "IfcCurtainWall",
    ],
    "Estructura": [
        "IfcBeam", "IfcColumn", "IfcFooting", "IfcPile", "IfcReinforcingBar",
    ],
    "Saneamiento-Fontaneria-Geotermia": [
        "IfcPipeSegment", "IfcPipeFitting", "IfcSanitaryTerminal", "IfcValve",
        "IfcPump",
    ],
    "Climatizacion-Ventilacion": [
        "IfcDuctSegment", "IfcDuctFitting", "IfcAirTerminal", "IfcFan", "IfcCoil",
    ],
    "PCI-Gases Medicinales": [
        "IfcFireSuppressionTerminal", "IfcAlarm", "IfcDetector",
    ],
    "Electricidad": [
        "IfcCableSegment", "IfcCableFitting", "IfcElectricDistributionBoard",
        "IfcLightFixture", "IfcOutlet", "IfcSwitchingDevice",
    ],
}

CATEGORY_IFC = {
    "IfcWall": "Muros", "IfcWallStandardCase": "Muros", "IfcDoor": "Puertas",
    "IfcWindow": "Ventanas", "IfcSlab": "Forjados", "IfcRoof": "Cubiertas",
    "IfcStair": "Escaleras", "IfcRailing": "Barandillas",
    "IfcCovering": "Revestimientos", "IfcCurtainWall": "Muros cortina",
    "IfcBeam": "Vigas", "IfcColumn": "Pilares", "IfcFooting": "Cimentaciones",
    "IfcPipeSegment": "Tuberías", "IfcSanitaryTerminal": "Aparatos sanitarios",
    "IfcValve": "Válvulas", "IfcDuctSegment": "Conductos",
    "IfcAirTerminal": "Difusores", "IfcLightFixture": "Luminarias",
    "IfcOutlet": "Tomas de corriente", "IfcSwitchingDevice": "Interruptores",
    "IfcFireSuppressionTerminal": "Rociadores",
}

_CLASS_DISC = {}
for _d, _classes in DISCIPLINE_IFC.items():
    for _c in _classes:
        _CLASS_DISC[_c] = _d


def _resolve_col(df, field_name):
    for alias in COLUMN_MAP.get(field_name, []):
        if alias in df.columns:
            return alias
    return None


def parse_csv(path: str) -> list[Element]:
    """Parsea un archivo CSV o Excel y devuelve lista de elementos."""
    try:
        if path.endswith((".xlsx", ".xls")):
            df = pd.read_excel(path)
        else:
            for enc in ["utf-8", "latin-1", "cp1252"]:
                try:
                    df = pd.read_csv(path, encoding=enc)
                    break
                except UnicodeDecodeError:
                    continue
            else:
                raise ValueError(
                    "No se pudo decodificar el CSV. "
                    "Pruebe a guardar el archivo con codificación UTF-8."
                )
    except Exception as e:
        raise ValueError(f"Error al leer el archivo: {e}")

    df.columns = df.columns.str.strip()
    cols = {f: _resolve_col(df, f) for f in COLUMN_MAP}

    required = ["ifc_guid", "name", "marca", "discipline"]
    missing = [r for r in required if not cols[r]]
    if missing:
        aliases = {r: COLUMN_MAP[r] for r in missing}
        raise ValueError(
            f"Columnas requeridas no encontradas: {missing}\n"
            f"  Nombres aceptados: {aliases}\n"
            f"  Columnas en el archivo: {list(df.columns)}"
        )

    elements = []
    skipped_marca = 0
    for _, row in df.iterrows():
        guid = str(row[cols["ifc_guid"]]).strip()
        if not guid or guid == "nan":
            continue

        def get(field_name):
            c = cols.get(field_name)
            if c and pd.notna(row[c]):
                return str(row[c]).strip()
            return ""

        raw_marca = get("marca")
        marca = sanitize_marca(raw_marca)
        if not marca:
            skipped_marca += 1
            continue

        elements.append(Element(
            ifc_guid=guid,
            name=get("name"),
            marca=marca,
            discipline=get("discipline") or "Sin clasificar",
            nombre_tipo=get("nombre_tipo"),
            tipo_ifc_guid=get("tipo_ifc_guid"),
            operacion=get("operacion"),
            ifc_class=get("ifc_class"),
            category=get("category"),
        ))

    print(f"  CSV: {len(elements)} elementos leídos", end="")
    if skipped_marca:
        print(f" ({skipped_marca} descartados por marca vacía/inválida)")
    else:
        print()
    return elements


def parse_ifc(path: str, discipline_override: str = None) -> list[Element]:
    """Parsea un archivo IFC usando IfcOpenShell."""
    try:
        import ifcopenshell
        import ifcopenshell.util.element
    except ImportError:
        print("ERROR: ifcopenshell no está instalado.")
        print("  Instálalo con: pip install ifcopenshell")
        sys.exit(1)

    try:
        ifc = ifcopenshell.open(path)
    except Exception as e:
        raise ValueError(f"Error al abrir archivo IFC: {e}")

    elements = []
    skip_types = {"IfcBuilding", "IfcBuildingStorey", "IfcSite", "IfcSpace", "IfcProject"}
    skipped_no_marca = 0
    skipped_bad_marca = 0

    for product in ifc.by_type("IfcProduct"):
        if product.is_a() in skip_types:
            continue

        try:
            psets = ifcopenshell.util.element.get_psets(product)
        except Exception:
            psets = {}

        raw_marca = None
        for props in psets.values():
            if isinstance(props, dict):
                raw_marca = props.get("Marca") or props.get("Mark") or props.get("marca")
                if raw_marca:
                    raw_marca = str(raw_marca).strip()
                    break

        if not raw_marca:
            skipped_no_marca += 1
            continue

        marca = sanitize_marca(raw_marca)
        if not marca:
            skipped_bad_marca += 1
            continue

        cls = product.is_a()
        disc = discipline_override or _CLASS_DISC.get(cls, "Sin clasificar")

        try:
            etype = ifcopenshell.util.element.get_type(product)
        except Exception:
            etype = None

        operacion = ""
        for props in psets.values():
            if isinstance(props, dict):
                op = (props.get("Operacion") or props.get("Operación")
                      or props.get("Operation Type"))
                if op:
                    operacion = str(op).strip()
                    break

        custom = {}
        skip_keys = {
            "id", "Marca", "Mark", "marca", "Operacion", "Operación",
            "Operation Type",
        }
        for props in psets.values():
            if isinstance(props, dict):
                for k, v in props.items():
                    if k not in skip_keys and v and str(v).strip():
                        custom[k] = str(v).strip()

        elements.append(Element(
            ifc_guid=product.GlobalId,
            name=product.Name or "",
            marca=marca,
            discipline=disc,
            nombre_tipo=etype.Name if etype else "",
            tipo_ifc_guid=etype.GlobalId if etype else "",
            operacion=operacion,
            ifc_class=cls,
            category=CATEGORY_IFC.get(cls, cls.replace("Ifc", "")),
            custom_properties=custom,
        ))

    print(f"  IFC: {len(elements)} elementos extraídos", end="")
    info = []
    if skipped_no_marca:
        info.append(f"{skipped_no_marca} sin marca")
    if skipped_bad_marca:
        info.append(f"{skipped_bad_marca} con marca inválida")
    if info:
        print(f" ({', '.join(info)})")
    else:
        print()
    return elements


# ─── HTML generation ──────────────────────────────────────────────────────────


def generate_site(elements: list[Element], project_name: str):
    """Genera páginas HTML estáticas para cada elemento."""
    if not TEMPLATE_DIR.exists():
        raise FileNotFoundError(
            f"Directorio de plantillas no encontrado: {TEMPLATE_DIR}\n"
            f"  Asegúrese de ejecutar el script desde el directorio del proyecto."
        )

    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(str(TEMPLATE_DIR)),
        autoescape=jinja2.select_autoescape(["html"]),
    )

    try:
        tpl = env.get_template("element.html")
        idx_tpl = env.get_template("index.html")
    except jinja2.TemplateNotFound as e:
        raise FileNotFoundError(f"Plantilla no encontrada: {e}")

    # Individual element pages
    for el in elements:
        el_dir = SITE_DIR / "e" / el.marca
        el_dir.mkdir(parents=True, exist_ok=True)
        html = tpl.render(element=el, project_name=project_name)
        (el_dir / "index.html").write_text(html, encoding="utf-8")

    # 404 page
    try:
        tpl_404 = env.get_template("404.html")
        html_404 = tpl_404.render(project_name=project_name)
        (SITE_DIR / "404.html").write_text(html_404, encoding="utf-8")
    except jinja2.TemplateNotFound:
        pass  # 404 template is optional

    # Index page
    disc_counts = {}
    for el in elements:
        disc_counts[el.discipline] = disc_counts.get(el.discipline, 0) + 1

    sorted_elements = sorted(elements, key=lambda e: (e.discipline, e.marca))
    html = idx_tpl.render(
        elements=sorted_elements,
        project_name=project_name,
        discipline_counts=dict(sorted(disc_counts.items())),
    )
    (SITE_DIR / "index.html").write_text(html, encoding="utf-8")

    print(f"  HTML: {len(elements)} páginas generadas en {SITE_DIR}/")


# ─── PDF generation ───────────────────────────────────────────────────────────

PAGE_W, PAGE_H = A4
MARGIN = 15 * mm
COLS = 3
ROWS = 6
CELL_W = (PAGE_W - 2 * MARGIN) / COLS
CELL_H = 42 * mm
QR_SZ = 25 * mm

S_MARCA = ParagraphStyle("m", fontSize=11, fontName="Helvetica-Bold", alignment=TA_CENTER, leading=13)
S_NAME = ParagraphStyle("n", fontSize=7, fontName="Helvetica", alignment=TA_CENTER, leading=9, textColor=colors.HexColor("#333"))
S_TYPE = ParagraphStyle("t", fontSize=6.5, fontName="Helvetica", alignment=TA_CENTER, leading=8, textColor=colors.HexColor("#666"))
S_HEAD = ParagraphStyle("h", fontSize=14, fontName="Helvetica-Bold")
S_SUB = ParagraphStyle("s", fontSize=10, fontName="Helvetica", textColor=colors.HexColor("#666"))
S_TITLE = ParagraphStyle("T", fontSize=24, fontName="Helvetica-Bold", alignment=TA_CENTER, spaceAfter=10 * mm)
S_COVER = ParagraphStyle("C", fontSize=14, fontName="Helvetica", alignment=TA_CENTER, textColor=colors.HexColor("#444"), spaceAfter=5 * mm)


def _qr_draw(url):
    qr = QrCodeWidget(url)
    qr.barWidth = QR_SZ
    qr.barHeight = QR_SZ
    d = Drawing(QR_SZ, QR_SZ)
    d.add(qr)
    return d


def _trunc(t, n=30):
    return t[:n - 2] + ".." if t and len(t) > n else (t or "")


def _label_cell(el, base_url):
    url = f"{base_url}/e/{el.marca}/"
    parts = [
        [_qr_draw(url)],
        [Paragraph(el.marca, S_MARCA)],
        [Paragraph(_trunc(el.name, 35), S_NAME)],
    ]
    if el.nombre_tipo:
        parts.append([Paragraph(_trunc(el.nombre_tipo, 30), S_TYPE)])
    if el.operacion:
        parts.append([Paragraph(_trunc(el.operacion, 25), S_TYPE)])

    t = Table(parts, colWidths=[CELL_W - 4 * mm])
    t.setStyle(TableStyle([
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 1),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
    ]))
    return t


def _label_grid(elements, base_url):
    rows = []
    for i in range(0, len(elements), COLS):
        row = [_label_cell(e, base_url) for e in elements[i:i + COLS]]
        while len(row) < COLS:
            row.append("")
        rows.append(row)

    t = Table(rows, colWidths=[CELL_W] * COLS, rowHeights=[CELL_H] * len(rows))
    t.setStyle(TableStyle([
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#DDD")),
        ("TOPPADDING", (0, 0), (-1, -1), 2 * mm),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2 * mm),
    ]))
    return t


def generate_pdf(elements: list[Element], project_name: str, discipline: str = None):
    """Genera PDF con etiquetas QR para imprimir."""
    disc_label = discipline or "Todas"
    filename = f"QR_{disc_label}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    pdf_path = PDF_DIR / filename
    PDF_DIR.mkdir(parents=True, exist_ok=True)

    doc = SimpleDocTemplate(
        str(pdf_path), pagesize=A4,
        leftMargin=MARGIN, rightMargin=MARGIN,
        topMargin=MARGIN, bottomMargin=MARGIN,
    )
    story = []

    # Cover
    story.append(Spacer(1, 40 * mm))
    story.append(Paragraph(project_name, S_TITLE))
    story.append(Paragraph("porqueViven.org", S_COVER))
    story.append(Spacer(1, 10 * mm))
    story.append(Paragraph(f"Disciplina: {disc_label}", S_COVER))
    story.append(Paragraph(f"Elementos: {len(elements)}", S_COVER))
    story.append(Paragraph(f"Generado: {datetime.now().strftime('%d/%m/%Y %H:%M')}", S_COVER))

    # Contents summary
    story.append(Spacer(1, 15 * mm))
    story.append(Paragraph("Contenido", S_HEAD))
    story.append(Spacer(1, 5 * mm))
    grouped = {}
    for el in elements:
        grouped.setdefault(el.discipline, {})
        cat = el.category or "Otros"
        grouped[el.discipline][cat] = grouped[el.discipline].get(cat, 0) + 1
    for d, cats in sorted(grouped.items()):
        story.append(Paragraph(f"<b>{d}</b>", S_SUB))
        for c, n in sorted(cats.items()):
            story.append(Paragraph(f"&nbsp;&nbsp;&nbsp;{c}: {n}", S_SUB))
    story.append(PageBreak())

    # Label pages grouped by discipline
    sorted_els = sorted(elements, key=lambda e: (e.discipline, e.category or "", e.marca))
    current_disc = None
    page_buf = []

    for el in sorted_els:
        if el.discipline != current_disc:
            if page_buf:
                story.append(_label_grid(page_buf, BASE_URL))
                story.append(PageBreak())
                page_buf = []
            current_disc = el.discipline
            story.append(Paragraph(current_disc, S_HEAD))
            story.append(Spacer(1, 3 * mm))

        page_buf.append(el)
        if len(page_buf) == COLS * ROWS:
            story.append(_label_grid(page_buf, BASE_URL))
            story.append(PageBreak())
            page_buf = []

    if page_buf:
        story.append(_label_grid(page_buf, BASE_URL))

    # Index
    story.append(PageBreak())
    story.append(Paragraph("Índice de marcas", S_HEAD))
    story.append(Spacer(1, 5 * mm))
    idx = [["Marca", "Nombre", "Disciplina", "Categoría"]]
    for el in sorted(elements, key=lambda e: e.marca):
        idx.append([el.marca, _trunc(el.name, 40), el.discipline, el.category or ""])

    if len(idx) > 1:
        it = Table(idx, colWidths=[25 * mm, 65 * mm, 45 * mm, 35 * mm], repeatRows=1)
        it.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 7),
            ("LEADING", (0, 0), (-1, -1), 9),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CCC")),
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F0F0F0")),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 2),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ]))
        story.append(it)

    try:
        doc.build(story)
    except Exception as e:
        raise RuntimeError(f"Error al generar PDF: {e}")

    print(f"  PDF: {pdf_path} ({len(elements)} etiquetas)")
    return pdf_path


# ─── Firebase config ──────────────────────────────────────────────────────────


def generate_firebase_config():
    """Genera firebase.json para hosting."""
    config = """{
  "hosting": {
    "public": "output/site",
    "ignore": ["firebase.json", "**/.*"],
    "cleanUrls": true,
    "headers": [
      {
        "source": "**/*.html",
        "headers": [{ "key": "Cache-Control", "value": "max-age=3600" }]
      }
    ]
  }
}"""
    Path("firebase.json").write_text(config, encoding="utf-8")
    print("  firebase.json generado")


# ─── Resumen ──────────────────────────────────────────────────────────────────


def print_summary(elements: list[Element]):
    """Imprime resumen de estadísticas por disciplina."""
    disc_counts = {}
    for el in elements:
        disc_counts[el.discipline] = disc_counts.get(el.discipline, 0) + 1
    print("\n  Resumen por disciplina:")
    for d, n in sorted(disc_counts.items()):
        print(f"    {d}: {n}")
    print(f"    TOTAL: {len(elements)}")


# ─── Main ─────────────────────────────────────────────────────────────────────


def main():
    global BASE_URL

    parser = argparse.ArgumentParser(
        description="Generador de QR para elementos BIM - porqueViven.org",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Ejemplos:
  python generate.py data/elementos.csv -p "CAPPI Edificio"
  python generate.py data/modelo.ifc -p "CAPPI" -d Arquitectura
  python generate.py --list-disciplines""",
    )
    parser.add_argument("input", nargs="?", help="Archivo CSV, Excel (.xlsx) o IFC")
    parser.add_argument("--project", "-p", help="Nombre del proyecto")
    parser.add_argument("--discipline", "-d", help="Filtrar por disciplina")
    parser.add_argument("--base-url", help=f"URL base (default: {BASE_URL})")
    parser.add_argument("--no-pdf", action="store_true", help="No generar PDF")
    parser.add_argument("--no-site", action="store_true", help="No generar sitio estático")
    parser.add_argument("--list-disciplines", action="store_true", help="Mostrar disciplinas disponibles")
    args = parser.parse_args()

    # List disciplines and exit
    if args.list_disciplines:
        print("Disciplinas disponibles:")
        for d, classes in sorted(DISCIPLINE_IFC.items()):
            print(f"  {d}")
            for c in classes:
                cat = CATEGORY_IFC.get(c, c.replace("Ifc", ""))
                print(f"    {c} → {cat}")
        return

    # Validate required args
    if not args.input:
        parser.error("Se requiere un archivo de entrada (CSV, Excel o IFC)")
    if not args.project:
        parser.error("Se requiere el nombre del proyecto (-p / --project)")

    # Validate base URL
    if args.base_url:
        BASE_URL = validate_base_url(args.base_url)

    input_path = args.input
    if not os.path.exists(input_path):
        print(f"ERROR: Archivo no encontrado: {input_path}")
        sys.exit(1)

    # Parse input
    print(f"\n1. Leyendo {input_path}...")
    ext = os.path.splitext(input_path)[1].lower()
    try:
        if ext in (".csv", ".xlsx", ".xls"):
            elements = parse_csv(input_path)
        elif ext == ".ifc":
            elements = parse_ifc(input_path, discipline_override=args.discipline)
        else:
            print(f"ERROR: Formato no soportado: {ext}")
            print("  Formatos aceptados: .csv, .xlsx, .xls, .ifc")
            sys.exit(1)
    except ValueError as e:
        print(f"ERROR: {e}")
        sys.exit(1)

    if not elements:
        print("ERROR: No se encontraron elementos válidos.")
        print("  Verifique que el archivo tiene datos y las columnas requeridas:")
        print("  IfcGUID, Name, Marca, Disciplina")
        sys.exit(1)

    # Deduplicate
    elements = deduplicate_elements(elements)

    # Filter by discipline if specified (for CSV)
    if args.discipline and ext != ".ifc":
        before = len(elements)
        elements = [e for e in elements if e.discipline == args.discipline]
        print(f"  Filtrado por '{args.discipline}': {before} → {len(elements)} elementos")
        if not elements:
            print(f"ERROR: Ningún elemento coincide con la disciplina '{args.discipline}'")
            print(f"  Disciplinas en el archivo: {sorted(set(e.discipline for e in deduplicate_elements(parse_csv(input_path))))}")
            sys.exit(1)

    print_summary(elements)

    # Generate site
    if not args.no_site:
        print("\n2. Generando sitio estático...")
        try:
            generate_site(elements, args.project)
        except (FileNotFoundError, jinja2.TemplateError) as e:
            print(f"ERROR generando HTML: {e}")
            sys.exit(1)

    # Generate PDF
    if not args.no_pdf:
        print("\n3. Generando PDF con etiquetas QR...")
        try:
            generate_pdf(elements, args.project, discipline=args.discipline)
        except RuntimeError as e:
            print(f"ERROR generando PDF: {e}")
            sys.exit(1)

    # Firebase config
    generate_firebase_config()

    print(f"\n{'='*50}")
    print(f"  LISTO")
    print(f"{'='*50}")
    print(f"  Sitio: {SITE_DIR}/ ({len(elements)} páginas)")
    print(f"  PDFs:  {PDF_DIR}/")
    print(f"\n  Desplegar en Firebase Hosting:")
    print(f"    firebase init hosting  (primera vez)")
    print(f"    firebase deploy --only hosting")
    print(f"\n  URLs de los QR: {BASE_URL}/e/{{marca}}/")


if __name__ == "__main__":
    main()
