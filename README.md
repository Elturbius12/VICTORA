# La Victoriana – Sistema de Pronóstico de Demanda

## Requisitos

- **Python 3.10 o superior** — [Descargar](https://python.org/downloads)
  - Al instalar, marcar **"Add Python to PATH"**
- Windows 10/11 (también funciona en macOS/Linux)

## Instalación rápida (Windows)

1. Descomprima este ZIP en una carpeta (ej: `C:\LaVictoriana\`)
2. Copie la carpeta `victoriana_app` (del ZIP de código fuente) dentro de la misma carpeta
3. Doble clic en **`instalar.bat`**
4. El instalador:
   - Verifica que Python esté instalado
   - Instala las dependencias automáticamente
   - Crea un acceso directo en el escritorio

## Instalación manual

```bash
pip install customtkinter numpy pandas scipy matplotlib
cd victoriana_app
python app.py
```

## Estructura del programa

```
victoriana_app/
├── app.py                  ← Punto de entrada
├── requirements.txt        ← Dependencias
├── data/
│   └── ventas_victoriana.csv   ← Datos de ejemplo
├── core/
│   ├── models.py           ← 12 modelos de pronóstico
│   ├── selection.py        ← Backtesting y selección
│   ├── optimizer.py        ← Modelo newsvendor
│   ├── database.py         ← Base de datos SQLite
│   └── educativo.py        ← Explicaciones educativas
└── gui/
    ├── main_window.py      ← Ventana principal con sidebar
    ├── registro.py         ← Módulo 1: Registro de ventas
    ├── pronostico.py       ← Módulo 2: Motor de pronóstico
    ├── educativo_gui.py    ← Módulo 3: Módulo educativo
    ├── dashboard.py        ← Módulo 4: Dashboard
    └── tema.py             ← Colores y estilos
```

## Módulos

### 1. Registro de Ventas
Registre las ventas diarias de cada producto. Puede importar datos desde CSV.

### 2. Motor de Pronóstico
Seleccione un producto y ejecute la competencia de 12+ modelos. El sistema:
- Clasifica el patrón de demanda (Syntetos-Boylan)
- Ejecuta backtesting con origen rodante
- Selecciona el mejor modelo por MAE
- Calcula la cantidad óptima de producción (newsvendor)
- Simula el ahorro vs. el método tradicional

### 3. Módulo Educativo
Explicaciones sencillas de cada modelo con fórmulas y ejemplos paso a paso.

### 4. Dashboard
Gráficos de tendencia, top productos, patrones por día de semana y clasificación de demanda.

## Datos

La base de datos SQLite se crea automáticamente en `data/victoriana.db`. Los datos de ejemplo se importan en el primer inicio.

## Autor

Desarrollado para la cafetería La Victoriana – Juliaca, Perú.
