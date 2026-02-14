# Manual de usuario - porqueViven BIM QR

## Que es y para que sirve

**porqueViven BIM QR** es una herramienta que genera codigos QR para los elementos constructivos del proyecto CAPPI. Cada codigo QR enlaza a una ficha digital del elemento que se puede consultar desde el movil.

**Flujo de trabajo:**

1. Exportas los datos de los elementos desde Revit (CSV o IFC)
2. Ejecutas el generador desde la terminal
3. Se genera un PDF con las etiquetas QR para imprimir
4. Se genera un sitio web con las fichas de cada elemento
5. Despliegas el sitio en bim.porqueviven.org
6. Imprimes las etiquetas y las pegas en obra
7. Escaneas el QR con el movil para ver la ficha del elemento

## Paso 1: Preparar los datos desde Revit

### Opcion A: Exportar CSV

Desde Revit, exporta una tabla con estas columnas:

| Columna | Descripcion | Ejemplo |
|---------|-------------|---------|
| **IfcGUID** | Identificador unico IFC | `1nwGt1S_v8gAItvRmxkMMQpf` |
| **Name** | Nombre del elemento | `CIT-Puerta 1 hoja-210x120x4.0 cm` |
| **Marca** | Marca de planos (corta) | `PA107` |
| **Disciplina** | Disciplina del elemento | `Arquitectura` |
| Nombre de tipo | Tipo del elemento | `210x120x4.0 cm` |
| IFC Class | Clase IFC | `IfcDoor` |
| Category | Categoria | `Puertas` |
| Operacion | Tipo de operacion | `Abatible` |

Las columnas en negrita son obligatorias. Las demas son opcionales pero recomendadas.

Guarda el archivo como CSV (codificacion UTF-8) o Excel (.xlsx).

### Opcion B: Usar archivo IFC

Si tienes el modelo IFC exportado desde Revit, puedes usarlo directamente. El script extraera los elementos que tengan la propiedad "Marca" en sus property sets.

> **Nota:** Para usar archivos IFC necesitas instalar IfcOpenShell: `pip install ifcopenshell`

## Paso 2: Instalar la herramienta

### Requisitos previos

- Python 3.10 o superior ([descargar](https://www.python.org/downloads/))
- Terminal (Terminal en Mac, CMD en Windows)

### Instalacion

```bash
# Descargar el proyecto
git clone https://github.com/javiercuervo/porqueViven.git
cd porqueViven

# Crear entorno virtual
python -m venv .venv

# Activar entorno (Mac/Linux)
source .venv/bin/activate

# Activar entorno (Windows)
.venv\Scripts\activate

# Instalar dependencias
pip install -r requirements.txt
```

## Paso 3: Ejecutar el generador

```bash
python generate.py ruta/al/archivo.csv -p "CAPPI Edificio Principal"
```

**Opciones disponibles:**

| Opcion | Descripcion |
|--------|-------------|
| `-p "Nombre"` | Nombre del proyecto (obligatorio) |
| `-d Arquitectura` | Filtrar por disciplina |
| `--no-pdf` | No generar el PDF |
| `--no-site` | No generar el sitio web |
| `--base-url URL` | Cambiar la URL base |
| `--list-disciplines` | Ver disciplinas disponibles |

**Ejemplos:**

```bash
# Generar todo desde CSV
python generate.py data/ejemplo_cappi.csv -p "CAPPI Edificio Principal"

# Solo elementos de Arquitectura
python generate.py data/ejemplo_cappi.csv -p "CAPPI" -d Arquitectura

# Desde archivo IFC
python generate.py modelo.ifc -p "CAPPI Edificio Principal"

# Solo generar sitio web (sin PDF)
python generate.py data/ejemplo_cappi.csv -p "CAPPI" --no-pdf
```

## Paso 4: Revisar lo generado

Despues de ejecutar, encontraras:

```
output/
  pdf/    -> PDF con etiquetas QR para imprimir
  site/   -> Sitio web con fichas de elementos
```

### Revisar el PDF

Abre el PDF en `output/pdf/`. Contiene:
- Portada con nombre del proyecto y resumen
- Paginas con etiquetas QR (18 por pagina, 3 columnas x 6 filas)
- Indice final con todas las marcas

### Revisar el sitio web

Abre `output/site/index.html` en el navegador para ver el indice de elementos. Desde ahi puedes:
- **Buscar** por marca, nombre o categoria
- **Filtrar** haciendo clic en las tarjetas de disciplina
- **Ver la ficha** de cada elemento haciendo clic en su marca

## Paso 5: Desplegar en bim.porqueviven.org

### Primera vez

```bash
# Instalar Firebase CLI
npm install -g firebase-tools

# Iniciar sesion
firebase login

# Inicializar (seleccionar output/site como directorio publico)
firebase init hosting
```

### Desplegar

```bash
firebase deploy --only hosting
```

Tras el despliegue, las fichas estaran disponibles en:
`https://bim.porqueviven.org/e/{marca}/`

Por ejemplo: `https://bim.porqueviven.org/e/PA107/`

## Solucion de problemas

### "Columnas requeridas no encontradas"

El CSV no tiene las columnas necesarias. Verifica que tiene al menos: `IfcGUID`, `Name`, `Marca`, `Disciplina`. Los nombres de columna son flexibles (ver tabla en Paso 1).

### "No se pudo decodificar el CSV"

El archivo no esta en UTF-8. Abre el CSV en Excel y guardalo como "CSV UTF-8".

### "marca vacia/invalida"

Algunos elementos no tienen marca asignada en Revit. Asignales una marca antes de exportar.

### "marcas duplicadas encontradas"

Hay elementos con la misma marca. Revisa en Revit que cada elemento tenga una marca unica. El generador mantiene solo el primer elemento y descarta los duplicados.

### El QR no escanea bien

- Asegurate de imprimir el PDF al 100% (sin ajustar a pagina)
- El tamano minimo recomendado de la etiqueta es 25x42mm
- Usa papel blanco, buen contraste
