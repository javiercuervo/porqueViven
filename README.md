# porqueViven BIM QR

Generador de codigos QR para elementos BIM del proyecto CAPPI de [porqueviven.org](https://porqueviven.org).

Lee datos de elementos constructivos desde archivos **CSV/Excel** o **IFC** (Revit) y genera:

- **PDF imprimible** con etiquetas QR organizadas por disciplina (3x6, 18 por pagina A4)
- **Sitio estatico** con una ficha HTML por cada elemento, pensada para escanear con el movil

Las fichas se despliegan en [bim.porqueviven.org](https://bim.porqueviven.org) mediante Firebase Hosting.

## Requisitos

- Python 3.10 o superior
- (Opcional) [IfcOpenShell](https://ifcopenshell.org/) para parsear archivos IFC

## Instalacion

```bash
git clone https://github.com/javiercuervo/porqueViven.git
cd porqueViven
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Para desarrollo (incluye pytest):

```bash
pip install -r requirements-dev.txt
```

## Uso rapido

```bash
# Desde CSV
python generate.py data/ejemplo_cappi.csv -p "CAPPI Edificio Principal"

# Filtrar por disciplina
python generate.py data/ejemplo_cappi.csv -p "CAPPI" -d Arquitectura

# Desde archivo IFC
python generate.py modelo.ifc -p "CAPPI Edificio Principal"

# Solo generar sitio (sin PDF)
python generate.py data/ejemplo_cappi.csv -p "CAPPI" --no-pdf

# Ver disciplinas disponibles
python generate.py --list-disciplines
```

## Estructura del proyecto

```
porqueViven/
  generate.py          # Script principal
  templates/
    element.html       # Ficha del elemento (movil)
    index.html         # Indice con buscador y filtros
    404.html           # Pagina de error
  data/
    ejemplo_cappi.csv  # Datos de ejemplo
  output/              # Generado (gitignored)
    site/              # HTML estatico para Firebase
    pdf/               # PDFs con etiquetas QR
  tests/
    test_generate.py   # Tests
  firebase.json        # Config Firebase (auto-generado)
```

## Formato del CSV de entrada

El CSV debe tener estas columnas (los nombres son flexibles):

| Campo | Nombres aceptados | Requerido |
|-------|-------------------|-----------|
| IfcGUID | `IfcGUID`, `ifc_guid`, `GlobalId`, `GUID` | Si |
| Nombre | `Name`, `name`, `Nombre` | Si |
| Marca | `Marca`, `marca`, `Mark` | Si |
| Disciplina | `Discipline`, `Disciplina` | Si |
| Nombre de tipo | `Nombre de tipo`, `Type Name` | No |
| Clase IFC | `IFC Class`, `Clase IFC` | No |
| Categoria | `Category`, `Categoria` | No |
| Operacion | `Operacion`, `Operation` | No |

## Despliegue en Firebase Hosting

```bash
# Primera vez
npm install -g firebase-tools
firebase login
firebase init hosting  # Seleccionar output/site como directorio publico

# Desplegar
firebase deploy --only hosting
```

El script genera automaticamente `firebase.json` con la configuracion correcta.

## Tests

```bash
python -m pytest tests/ -v
```

## Licencia

MIT - ver [LICENSE](LICENSE)
