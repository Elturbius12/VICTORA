"""Lanzador del ejecutable de Windows (PyInstaller).

* Guarda los datos de cada usuario en %LOCALAPPDATA%\\VICTORA (la carpeta del programa se puede
  compartir/copiar sin llevarse los datos de nadie y no necesita permisos de escritura).
* Busca un puerto libre, arranca Streamlit en este mismo proceso y abre el navegador en cuanto
  el servidor responde (no con un tiempo fijo).
* Si VICTORA ya está abierto, solo abre otra pestaña del navegador.
"""
import os
import socket
import sys
import threading
import time
import urllib.request
import webbrowser

PUERTO_BASE = 8501


def ruta(rel):
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, rel)


def _carpeta_datos():
    base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
    d = os.path.join(base, "VICTORA")
    os.makedirs(d, exist_ok=True)
    return d


def _es_victora(puerto):
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{puerto}/_stcore/health", timeout=1) as r:
            return r.status == 200
    except Exception:  # noqa: BLE001
        return False


def _libre(puerto):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("127.0.0.1", puerto)) != 0


def _abrir_cuando_listo(url, puerto):
    for _ in range(240):            # hasta 60 s
        if _es_victora(puerto):
            webbrowser.open(url)
            return
        time.sleep(0.25)
    webbrowser.open(url)


def _autotest():
    """VICTORA.exe --autotest : recorre la app con datos de demostración y genera el reporte."""
    import tempfile
    os.environ["VICTORA_SQLITE"] = os.path.join(tempfile.mkdtemp(), "prueba.db")
    sys.path.insert(0, ruta("."))
    from streamlit.testing.v1 import AppTest
    t = time.perf_counter()
    at = AppTest.from_file(ruta("app.py"), default_timeout=180).run()
    assert not at.exception, at.exception
    at.button(key="tuto_sig").click().run()
    at.button(key="tuto_saltar").click().run()
    assert not at.exception, at.exception
    from victora.tutorial import manual_docx
    assert len(manual_docx()) > 20000
    from victora.negocio_ui import TABS as TABS_NEG
    for tab in TABS_NEG:  # las 7 pantallas de «Mi negocio» (La Victoriana), en el orden del original
        at.session_state["tabs_neg"] = tab
        at.run()
        assert not at.exception, (tab, at.exception)
        assert not at.error, (tab, [e.value for e in at.error])
    at.session_state["tabs_neg"] = "🔮 Motor de Pronóstico"
    at.run()
    at.button(key="neg_pron_uno").click().run()          # Motor de Pronóstico: calcular un producto
    assert not at.exception, at.exception
    at.button(key="neg_pron_todo").click().run()         # … y calcular todo
    assert not at.exception, at.exception
    at.session_state["modo"] = "🔬 Análisis completo y artículo"
    at.run()
    at.button(key="demo_btn").click().run()
    assert not at.exception, at.exception
    for tab in ["💰 Impacto", "📊 Análisis", "📑 Reportes", "📖 Metodología", "✅ Decisión"]:
        at.session_state["tabs_main"] = tab
        at.run()
        assert not at.exception, (tab, at.exception)
    from victora.reporte_excel import reporte_completo
    assert len(reporte_completo(at.session_state["R"])) > 10000
    print(f"AUTOTEST OK ({time.perf_counter() - t:.1f} s)")


if __name__ == "__main__":
    if "--autotest" in sys.argv:
        _autotest()
        sys.exit(0)
    datos = _carpeta_datos()
    if getattr(sys, "frozen", False):
        os.environ.setdefault("VICTORA_SQLITE", os.path.join(datos, "victoriana.db"))
    os.environ.setdefault("MPLCONFIGDIR", os.path.join(datos, "mpl"))

    # ¿Ya hay un VICTORA abierto? Reutilizarlo.
    for p in range(PUERTO_BASE, PUERTO_BASE + 10):
        if not _libre(p) and _es_victora(p):
            webbrowser.open(f"http://localhost:{p}")
            sys.exit(0)

    puerto = next((p for p in range(PUERTO_BASE, PUERTO_BASE + 50) if _libre(p)), PUERTO_BASE)
    url = f"http://localhost:{puerto}"
    print("=" * 60)
    print(f"  VICTORA se está abriendo en su navegador: {url}")
    print("  Deje esta ventana abierta mientras usa el programa.")
    print("  Para cerrar VICTORA, cierre esta ventana.")
    print(f"  Sus datos se guardan en: {datos}")
    print("=" * 60)
    threading.Thread(target=_abrir_cuando_listo, args=(url, puerto), daemon=True).start()

    from streamlit.web import cli as stcli

    sys.argv = ["streamlit", "run", ruta("app.py"),
                "--global.developmentMode=false",
                "--server.headless=true",
                "--server.address=127.0.0.1",
                f"--server.port={puerto}",
                "--server.fileWatcherType=none",
                "--server.runOnSave=false",
                "--browser.gatherUsageStats=false",
                "--client.toolbarMode=minimal"]
    sys.exit(stcli.main())
