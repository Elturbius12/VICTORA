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

Se abre en `http://localhost:8501`. Funciona sin internet y los datos no salen de la computadora.

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

## Streamlit Cloud

1. Usa este repositorio de GitHub (el archivo principal es `app.py`, en la raíz).
2. En share.streamlit.io elige el repositorio, la rama y `app.py`; en *Advanced settings* elige **Python 3.12 o superior**.
3. `requirements.txt` se instala solo. No hay recursos externos (CDN, fuentes) que puedan dejar la pantalla en blanco.

> No pude probar el despliegue en Streamlit Cloud desde aquí; las versiones fijadas funcionan localmente.

## Despliegue en Render

El repositorio ya está listo: `requirements.txt` (con `streamlit` en la primera línea), `.python-version`
(3.12) y `render.yaml` están en la raíz. `.streamlit/config.toml` **no** fija el puerto.

**Opción A — Blueprint (automático):** en Render, *New → Blueprint*, elige este repositorio y acepta;
`render.yaml` crea el servicio con todo configurado.

**Opción B — manual:**

1. *New → Web Service*, conectado al repositorio de GitHub (rama `main`).
2. Environment: **Python 3**. Root Directory: vacío (la raíz del repo).
3. Build Command: `pip install -r requirements.txt`
4. Start Command: `streamlit run app.py --server.port $PORT --server.address 0.0.0.0`
5. No se necesita declarar ninguna variable de entorno propia (opcional: `PYTHON_VERSION=3.12.8` si Render no lee `.python-version`).
6. Plan: Free (o el que elijas).

El plan gratuito «duerme» tras inactividad; el primer acceso tarda en despertar. Todo el estado vive en
`st.session_state`, nada depende del disco entre reinicios.

## Empaquetar para Windows (PyInstaller)

```bash
pip install pyinstaller
pyinstaller --noconfirm --name VICTORA --onedir ^
  --add-data "app.py;." --add-data "victora;victora" --add-data "datos_demo;datos_demo" ^
  --add-data ".streamlit;.streamlit" ^
  --collect-all streamlit --collect-submodules statsmodels --copy-metadata streamlit ^
  lanzador.py
```

El resultado queda en `dist\VICTORA\VICTORA.exe` (abre el servidor local y el navegador). Para un instalador,
usa Inno Setup apuntando a `dist\VICTORA\*`. No probé el empaquetado.

## Desviaciones explícitas respecto al prompt

- **Gráficos**: matplotlib (Agg) renderizado a PNG, cacheado y mostrado con `st.image` en lugar de `st.pyplot`
  (se dibuja una vez por producto y no en cada interacción). Se ve igual y es más rápido.
- **Un solo gráfico por selector**: los gráficos por producto están detrás de un selector (máximo 3–4 visibles a la vez).
- **Series largas**: con más de 35 días la validación usa los últimos 28 orígenes para mantener el tiempo bajo control.
- **`Produccion_real`**: se usa `unidades_producidas` como P0; el sobrante se recalcula contra la venta.
- **Calendario**: con pocas semanas no se modelan feriados ni eventos (solo se excluyen los días cerrados).
- **Razón crítica** acotada a [0,01; 0,99] para evitar cuantiles extremos.
- **ZIP de figuras**: contiene las 9 figuras globales (300 dpi). Las de cada producto se generan a pedido (botón en 📑 Reportes).
