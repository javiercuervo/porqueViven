# porqueViven BIM QR

Generador de codigos QR para elementos BIM del proyecto CAPPI (porqueviven.org).
Lee un CSV exportado de Revit, genera un PDF imprimible con etiquetas QR y un sitio estatico para escanear desde movil.

## Comandos

```bash
# Ejecutar (genera HTML + PDF en output/)
/Library/Developer/CommandLineTools/usr/bin/python3 generate.py data/ejemplo_cappi.csv -p "CAPPI Edificio Principal"

# Tests (56 tests, ~4s)
/Library/Developer/CommandLineTools/usr/bin/python3 -m pytest tests/ -v

# Desplegar (NO hacer sin confirmacion del usuario)
firebase deploy --only hosting
```

## Arquitectura

```
generate.py          # Script unico: parsing, generacion HTML/PDF, CLI
templates/
  element.html       # Ficha movil de un elemento (Jinja2)
  index.html         # Indice con buscador y filtros (Jinja2)
  404.html           # Pagina de error
tests/
  conftest.py        # 11 fixtures (CSVs variados)
  test_generate.py   # 56 tests (10 clases)
data/
  ejemplo_cappi.csv  # CSV de ejemplo con 12 elementos
output/
  site/              # HTML generado (Firebase Hosting public dir)
  pdf/               # PDFs generados
```

## Convenciones

- Python >=3.10 (en local: 3.9.6 Xcode — funciona con `from __future__ import annotations`)
- Idioma del codigo y docs: espanol
- Un solo script (`generate.py`), sin modulos separados
- Templates Jinja2 con autoescape
- Tests con pytest, fixtures en conftest.py
- CI: GitHub Actions (Python 3.10 + 3.12)

## Branding porqueViven

| Token | Valor |
|-------|-------|
| Azul principal | `#0C4DA2` |
| Purpura acento | `#770E75` |
| Texto oscuro | `#2D2D2D` |
| Texto secundario | `#555555` |
| Fondo claro | `#E5EDF3` |
| Bordes | `#C8D6E0` |
| Cabeceras | `#EDF2F7` |
| Tipografia | Lato (Google Fonts) |

## Estado actual (v1.0.0)

- 56 tests pasando, CI verde
- Branding porqueViven aplicado a HTML y PDF
- NO desplegado en la nube (pendiente Firebase Hosting en bim.porqueviven.org)
- Repo: github.com/javiercuervo/porqueViven (publico)
