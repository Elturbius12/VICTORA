# La Victoriana – Sistema de Pronóstico de Demanda

Sistema de escritorio para pizzería/snack bar que registra las ventas diarias de
cada producto, compite varios modelos de pronóstico por producto y te dice cuánto
vas a vender mañana (y cuánto conviene preparar o comprar).

## Requisitos

- **Python 3.10 o superior** — [Descargar](https://python.org/downloads)
  - Al instalar, marcar **"Add Python to PATH"**
- Windows 10/11 (también funciona en macOS/Linux ejecutando desde el código fuente)

## Opción A — Instalador de Windows (recomendado para entregar a otra persona)

Si ya tienes `LaVictoriana_Setup.exe` (generado con `compilar.bat` + Inno Setup,
ver más abajo), solo hay que ejecutarlo y seguir el asistente. No necesita tener
Python instalado.

## Opción B — Ejecutar desde el código fuente

1. Descomprima este ZIP en una carpeta (ej: `C:\LaVictoriana\`)
2. Doble clic en **`instalar.bat`**
3. El instalador:
   - Verifica que Python esté instalado
   - Instala las dependencias automáticamente (`requirements.txt`)
   - Crea un acceso directo en el escritorio
4. Para iniciar: doble clic en el acceso directo "La Victoriana", o ejecute
   `python app.py` desde la carpeta del proyecto.

### Instalación manual

```bash
pip install -r requirements.txt
python app.py
```

## Generar el instalador .exe (para desarrolladores)

Esto debe hacerse en una PC con **Windows**, no funciona en Linux/macOS:

1. Doble clic en **`compilar.bat`** — instala PyInstaller y genera
   `dist\LaVictoriana\LaVictoriana.exe` usando `LaVictoriana.spec`
2. (Opcional, para un instalador profesional) instale
   [Inno Setup](https://jrsoftware.org/isdl.php) y abra `instalador.iss`,
   luego presione "Compile". Esto genera
   `instalador_output\LaVictoriana_Setup.exe`, listo para compartir.

## Estructura del programa

```
victora/
├── app.py                  ← Punto de entrada
├── requirements.txt        ← Dependencias
├── LaVictoriana.spec       ← Config. de PyInstaller (fuente de verdad del build)
├── compilar.bat            ← Genera el .exe con PyInstaller
├── instalador.iss          ← Script de Inno Setup (instalador profesional)
├── instalar.bat            ← Instala dependencias y crea acceso directo
├── data/
│   └── ventas_victoriana.csv   ← Datos de ejemplo (importables desde "Registro")
├── core/
│   ├── models.py            ← 12+ modelos de pronóstico
│   ├── selection.py         ← Backtesting y selección del mejor modelo
│   ├── optimizer.py         ← Modelo newsvendor (cantidad óptima)
│   ├── database.py          ← Base de datos SQLite, catálogo, calendario especial
│   ├── reportes.py          ← Recomendaciones, seguimiento, exportación, comanda
│   └── educativo.py         ← Explicaciones educativas de cada modelo
└── gui/
    ├── main_window.py       ← Ventana principal con sidebar
    ├── registro.py          ← Registro diario de ventas e importación de catálogo/CSV
    ├── pronostico.py        ← Motor de pronóstico por producto
    ├── resumen.py           ← Recomendaciones para todos los productos a la vez
    ├── seguimiento.py       ← Tabla pronosticado vs. real, errores, tendencia
    ├── configuracion.py     ← Copias de seguridad, comanda imprimible, feriados
    ├── educativo_gui.py     ← Módulo educativo
    ├── dashboard.py         ← Gráficos de tendencia y patrones
    └── tema.py              ← Colores y estilos
```

## Módulos

### 1. Registro de Ventas
Registre las ventas diarias de cada producto (o márquelo como "local cerrado").
Puede importar catálogo y ventas desde Excel/CSV. Muestra retroalimentación
rápida: "ayer el sistema pronosticó X, tú vendiste Y".

### 2. Motor de Pronóstico
Seleccione un producto y ejecute la competencia de 12+ modelos. El sistema:
- Clasifica el patrón de demanda (Syntetos-Boylan)
- Ejecuta backtesting con origen rodante, excluyendo feriados/fechas especiales
  del promedio normal por día de semana
- Selecciona el mejor modelo por MAE
- Separa el **pronóstico honesto** (lo que probablemente se va a vender) de la
  **cantidad sugerida** a preparar/comprar (con margen de seguridad newsvendor)
- Para productos nuevos o con poco historial, estima con el promedio de su
  categoría mientras junta datos propios

### 3. Resumen (todos los productos)
Recomendación de todos los productos agrupada por categoría, con semáforo de
confianza 🟢🟡🔴, aviso de próxima fecha especial y de copia de seguridad atrasada.

### 4. Seguimiento
Tabla día | venta real | pronosticado | error, con observaciones, resaltado de
errores grandes, resumen de precisión, tendencia semanal y exportación a Excel.

### 5. Configuración
Copias de seguridad de la base de datos, generación de la "comanda" imprimible
para cocina, y administración del calendario de feriados/fechas especiales 2026
(se pueden agregar fechas propias del negocio).

### 6. Módulo Educativo
Explicaciones sencillas de cada modelo con fórmulas y ejemplos paso a paso.

### 7. Dashboard
Gráficos de tendencia, top productos, patrones por día de semana y clasificación
de demanda.

## Datos

La base de datos SQLite se crea automáticamente en `data/victoriana.db` la
primera vez que se ejecuta el programa (tablas vacías, sin datos de ejemplo).
`data/ventas_victoriana.csv` son datos reales de referencia que puede importar
manualmente desde el módulo de Registro si quiere partir con historial.

## Pruebas

```bash
pip install pytest
pytest tests/ -v
```

## Autor

Desarrollado para La Victoriana – pizzería/snack bar, Juliaca, Perú.
