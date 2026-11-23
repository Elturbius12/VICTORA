"""Test de humo: pipeline completo con 32 productos × 21 días en < 30 s, determinista, y app sin excepciones.

Ejecutar:  python tests/smoke_test.py   (o: pytest tests/smoke_test.py)
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from victora.pipeline import ejecutar  # noqa: E402
from victora.plantilla import plantilla_ejemplo  # noqa: E402
from victora.validador import validar  # noqa: E402


def test_app_demo_sin_excepciones():
    """Importa la app, pulsa «Probar con datos de demostración» y recorre las pestañas."""
    from streamlit.testing.v1 import AppTest
    at = AppTest.from_file(os.path.join(os.path.dirname(__file__), "..", "app.py"), default_timeout=120).run()
    assert not at.exception
    at.button(key="demo_btn").click().run()
    assert not at.exception
    assert at.session_state["R"]["n_productos"] == 32
    for tab in ["💰 Impacto", "📊 Análisis", "📑 Reportes", "📖 Metodología", "✅ Decisión"]:
        at.session_state["tabs_main"] = tab
        at.run()
        assert not at.exception, tab
    at.button(key="reset_sidebar").click().run()
    at.button(key="reset_si").click().run()
    assert "R" not in at.session_state


def test_smoke_pipeline():
    r = validar(plantilla_ejemplo())
    assert r.semaforo != "rojo"
    t = time.perf_counter()
    R1 = ejecutar(r.datos)
    seg = time.perf_counter() - t
    assert R1["n_productos"] == 32 and R1["n_dias"] == 21
    assert seg < 30, f"Pipeline tardó {seg:.1f} s"
    R2 = ejecutar(r.datos)
    for k in ["res_pol", "plan", "ranking", "wilcoxon", "sens_col", "sens_mar"]:
        assert R1[k].equals(R2[k]), k
    assert R1["boot"] == R2["boot"]
    assert R1["texto_resultados"] == R2["texto_resultados"]
    print(f"OK: pipeline 32×21 en {seg:.1f} s; dos ejecuciones idénticas.")


if __name__ == "__main__":
    test_app_demo_sin_excepciones()
    test_smoke_pipeline()
