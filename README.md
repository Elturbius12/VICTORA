# VICTORA v3 — ¿Cuánto producir mañana?

Aplicación Streamlit (en español) que convierte las ventas diarias de un negocio de comida perecible en una
**decisión concreta de producción**, muestra en soles cuánto cuesta decidir sin pronóstico y genera un
**reporte Excel listo para un artículo científico** (tablas, figuras, pruebas y textos redactados).

Caso de estudio: cafetería La Victoriana (Juliaca, Perú). El nombre del negocio, la ciudad y el nombre del
software se pueden cambiar en la app (**📤 Cargar Datos → Configuración**) y se insertan en los textos.

## Instalación y ejecución

Requiere Python 3.11 o superior (las versiones fijadas se probaron en Python 3.14).

```bash
cd VICTORA
python -m venv .venv
.venv\Scripts\activate          # Windows  (Linux/Mac: source .venv/bin/activate)
pip install -r requirements.txt
python -m streamlit run app.py
```

Se abre en `http://localhost:8501`. Las ventas registradas se guardan en `data/victoriana.db` (SQLite local).

## Dos secciones en una sola app

Arriba de la app hay un selector:

- **🏪 Mi negocio (día a día)** — la app de escritorio **🍗 La Victoriana** («Vende lo justo, no más, no menos»),
  con su paleta dorado/azul oscuro y su menú lateral de 7 pantallas, en el mismo orden que el original:
  🏠 Resumen del día (qué preparar/comprar hoy, reporte Excel, comanda PDF, copia de seguridad) · 📋 Registro de
  Ventas (ventas diarias, precios, «Local cerrado hoy», nuevo producto, importar catálogo/ventas; además edición
  avanzada de productos y recetas) · 🔮 Motor de Pronóstico (competencia de modelos por producto) · 📈 Seguimiento
  (pronóstico vs. venta real, observaciones, historial completo) · 📚 Módulo Educativo · 📊 Dashboard ·
  ⚙️ Configuración (copia de seguridad y restauración, comanda, feriados).
  Los datos se guardan en la base de datos y se conservan entre visitas.
- **🔬 Análisis completo y artículo** — el análisis v3 (decisión newsvendor, impacto, estadística, reporte de
  20 hojas). En **📤 Cargar Datos** puedes usar **«📋 Usar mis ventas registradas»** (toma lo de «Mi negocio») o
  subir un Excel con la plantilla.

## Tutorial, manual y diseño

- **Tutorial de bienvenida** (6 pasos): aparece la primera vez que se abre VICTORA en una PC; se repite con
  **Ver tutorial** en la barra lateral (`victora/tutorial.py`).
- **Manual de usuario (.docx)**: botón **Manual** en la barra lateral; se genera con el mismo contenido del tutorial.
- **Panel gerencial** en ✅ Decisión: veredicto en semáforo (adoptar / piloto / mantener) basado en el intervalo de
  confianza bootstrap del ahorro, y tabla «Dónde actuar primero» con el ahorro por producto.
- Identidad visual en `.streamlit/config.toml` y `victora/estilo.py` (sin recursos de internet).

## Uso paso a paso

1. **🏠 El Problema**: descarga la plantilla de datos y la **guía de recetas**, o pulsa
   **🧪 Probar con datos de demostración** (32 productos ficticios).
2. **📤 Cargar Datos**: sube tu Excel. El semáforo 🟢/🟡/🔴 lista cada problema con hoja, fila, columna y sugerencia.
   Indica cómo tratar los días sin registro y pulsa **▶️ Ejecutar análisis** (barra de progreso).
3. **✅ Decisión** (se abre sola al terminar): tabla *Producto · Producir mañana · Mínimo · Máximo · Modelo*,
   ahorro estimado y botón del plan de cocina. Abajo: gráfico por producto, plan de 7 días e insumos a comprar.
4. **💰 Impacto**: costo sin VICTORA (P0) vs. con VICTORA (P4) en soles, etiqueta ⚠️ SIMULADO (o ✅ REAL).
5. **📊 Análisis**: hallazgos clave y 9 secciones; cada tabla (.xlsx) y gráfico (.png) tiene su botón de descarga.
6. **📑 Reportes**: Reporte completo (.xlsx, 20 hojas), Plan de producción (.xlsx) y ZIP de figuras (PNG 300 dpi).
7. **📖 Metodología**: métodos, limitaciones automáticas y cita sugerida.
8. **🗑️ Restablecer todo** (barra lateral y pestaña 1): con confirmación, borra datos, resultados, caché y temporales.

## Por qué es rápida

- Streamlit ejecuta por defecto el cuerpo de **todas** las pestañas en cada interacción. VICTORA usa
  `st.tabs(..., on_change="rerun")` y solo renderiza la pestaña abierta (y las secciones abiertas del análisis).
- El análisis completo se calcula **una sola vez** (≈5–10 s con 32 productos × 21 días) y se guarda en `st.session_state`.
- Los selectores de producto están en `st.fragment`: cambiar de producto no reejecuta la pestaña.
- Gráficos y tablas Excel se cachean; los Excel/ZIP se generan una vez y el botón solo entrega bytes.
- Medido en el servidor real: cambiar de pestaña ≈ 0,15–0,25 s.

## Estructura

```
app.py                  interfaz Streamlit            lanzador.py   arranque para Windows (PyInstaller)
.streamlit/config.toml  tema y servidor
victora/                config, plantilla, validador, pipeline, descriptivos, modelos, seleccion, decision,
                        simulacion, estadistica, reporte_excel, reporte_figuras, textos, graficos, utils
datos_demo/demo_data.py datos sintéticos (32 productos)
tests/                  pytest + smoke_test.py
entregables/            plantillas (3), reporte, plan y figuras generados con datos de demostración
```

## Pruebas

```bash
pip install -r requirements-dev.txt
python -m pytest tests tests/smoke_test.py
python tests/smoke_test.py   # app + pipeline 32 × 21 < 30 s y resultados idénticos en dos ejecuciones
```

## Ejecutable para compartir (Windows, 100 % local)

VICTORA funciona **solo en la computadora**: sin internet, sin servidor y sin base de datos externa.

```bat
construir_exe.bat
```

Genera `dist\VICTORA\VICTORA.exe` y **`dist\VICTORA_Windows.zip`** (esto es lo que se comparte).
El usuario descomprime, hace doble clic en `VICTORA.exe` y el programa se abre en su navegador
(ver `LEEME_USUARIOS.txt`, incluido en el ZIP).

- Los datos de cada usuario se guardan en `%LOCALAPPDATA%\VICTORA\victoriana.db` (no en la carpeta del
  programa): compartir el ZIP nunca comparte datos, y no hace falta permiso de administrador.
- El lanzador busca un puerto libre, abre el navegador apenas el servidor responde (≈ 5–10 s) y, si VICTORA
  ya está abierto, solo abre otra pestaña. Escucha únicamente en `127.0.0.1` (nadie de la red accede).
- Autodiagnóstico: `VICTORA.exe --autotest` recorre todas las pantallas con datos de demostración.
- Pasar datos a otra PC: **⚙️ Configuración → Copia de seguridad** y **Restaurar** en la otra PC.

## Desviaciones explícitas respecto al prompt

- **Gráficos**: matplotlib (Agg) renderizado a PNG, cacheado y mostrado con `st.image` en lugar de `st.pyplot`
  (se dibuja una vez por producto y no en cada interacción). Se ve igual y es más rápido.
- **Un solo gráfico por selector**: los gráficos por producto están detrás de un selector (máximo 3–4 visibles a la vez).
- **Series largas**: con más de 35 días la validación usa los últimos 28 orígenes para mantener el tiempo bajo control.
- **`Produccion_real`**: se usa `unidades_producidas` como P0; el sobrante se recalcula contra la venta.
- **Calendario**: con pocas semanas no se modelan feriados ni eventos (solo se excluyen los días cerrados).
- **Razón crítica** acotada a [0,01; 0,99] para evitar cuantiles extremos.
- **ZIP de figuras**: contiene las 9 figuras globales (300 dpi). Las de cada producto se generan a pedido (botón en 📑 Reportes).
