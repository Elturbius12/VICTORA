# VICTORA v2 — ¿Cuánto producir mañana?

Aplicación de escritorio (Streamlit, en español) que convierte las ventas diarias de un negocio de comida
perecible en una **decisión óptima de producción**, muestra en soles el ahorro frente a la práctica habitual y
genera un **reporte Excel listo para un artículo científico** (tablas, figuras, pruebas y textos redactados).

Caso de estudio: cafetería La Victoriana (Juliaca, Perú). Funciona para cualquier negocio de comida.

## Instalación

Requiere Python 3.11 o superior.

```bash
cd victora
python -m venv .venv
.venv\Scripts\activate          # Windows  (Linux/Mac: source .venv/bin/activate)
pip install -r requirements.txt
```

## Ejecución

```bash
streamlit run app.py
```

Se abre en `http://localhost:8501`. Una vez instalada funciona **sin internet**, y los datos nunca salen de
la computadora.

## Uso paso a paso

1. **🏠 Inicio**: lee el problema o pulsa **🧪 Probar con datos de demostración** (datos ficticios).
2. **📋 Plantilla y Guía**: descarga `Plantilla_VICTORA_vacia.xlsx` y llénala siguiendo la hoja **LEEME**
   (amarillo = obligatorio, gris = opcional).
3. **📤 Cargar y Validar**: sube tu Excel. El semáforo 🟢/🟡/🔴 lista cada problema con hoja, fila, columna y una
   sugerencia. Si faltan días, indica si estuvo *cerrado* o hubo *venta cero*. Pulsa **▶️ Ejecutar análisis**.
4. **📊 Diagnóstico** y **🔮 Pronóstico**: descriptivos, clasificación de la demanda, modelo ganador por producto.
5. **🏭 Plan de Producción**: cuánto producir los próximos 7 días y lista de compras de insumos.
6. **💰 Impacto**: costo sin VICTORA (P0) frente a con VICTORA (P4), en soles (⚠️ SIMULADO).
7. **📑 Reportes**: descarga `Reporte_VICTORA.xlsx` (20 hojas) y `Plan_Produccion_Semana.xlsx`.
8. **🗑️ Restablecer todo** (en el panel lateral y en Inicio): borra datos, resultados, caché y temporales.

Todo el análisis se calcula **una sola vez** al pulsar *Ejecutar*. Al cambiar de pestaña solo se leen resultados
guardados, por eso el cambio es instantáneo.

## Estructura

```
app.py                 interfaz Streamlit (pestañas)
lanzador.py            arranque para el ejecutable de Windows
.streamlit/config.toml configuración y tema
victora/               plantilla, validador, pipeline, descriptivos, modelos, seleccion, decision,
                       simulacion, estadistica, reporte_excel, textos, graficos, utils
datos_demo/demo_data.py  datos sintéticos (ficticios)
tests/                 pruebas pytest + smoke_test.py
entregables/           plantillas y reporte generados con los datos de demostración
```

## Pruebas

```bash
python -m pytest tests tests/smoke_test.py
python tests/smoke_test.py      # pipeline 10 productos × 21 días < 30 s y determinista
```

## Empaquetar para Windows (PyInstaller)

```bash
pip install pyinstaller
pyinstaller --noconfirm --name VICTORA --onedir ^
  --add-data "app.py;." --add-data "victora;victora" --add-data "datos_demo;datos_demo" ^
  --add-data ".streamlit;.streamlit" ^
  --collect-all streamlit --collect-submodules statsmodels --copy-metadata streamlit ^
  lanzador.py
```

El resultado queda en `dist\VICTORA\VICTORA.exe`: al abrirlo arranca el servidor local y abre el navegador.
Para un **instalador** (.exe con acceso directo), usa Inno Setup y apunta a la carpeta `dist\VICTORA`
(*Files: Source: "dist\VICTORA\*"; Flags: recursesubdirs*). Sin `--onefile`, el programa arranca más rápido.

## Decisiones y desviaciones explícitas

- **Gráficos**: se generan con matplotlib (Agg) y se muestran como PNG en caché con `st.image`, en vez de
  `st.pyplot`. El resultado es el mismo y no se vuelven a dibujar al navegar.
- **Diálogo de confirmación**: usa `st.dialog` nativo de Streamlit, sin iframes ni componentes externos.
- **Series largas**: con más de 38 días, la validación usa los últimos 28 orígenes, para que 3 meses de datos
  sigan corriendo en unos 30 s. El texto de métodos lo declara.
- **Razón crítica** acotada a [0,01; 0,99] para evitar cuantiles extremos cuando el valor de rescate iguala el costo.
- **Combinación (top 3)**: se eligen los 3 mejores sobre el mismo periodo de prueba, lo que da un sesgo optimista.
  Está declarado en las limitaciones.
- **P4 en la simulación** usa solo residuos anteriores a cada día, así no hay fuga de información.
- **Variables de calendario**: con ~3 semanas no se modelan feriados ni eventos (no hay datos suficientes), y se avisa
  en las limitaciones. Los días con `abierto = NO` sí se excluyen de la serie.
