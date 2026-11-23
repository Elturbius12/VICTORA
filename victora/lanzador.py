"""Lanzador para el ejecutable de Windows (PyInstaller): arranca Streamlit y abre el navegador."""
import os
import sys
import threading
import webbrowser

PUERTO = 8501


def ruta(rel):
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, rel)


if __name__ == "__main__":
    from streamlit.web import cli as stcli

    threading.Timer(3, lambda: webbrowser.open(f"http://localhost:{PUERTO}")).start()
    sys.argv = ["streamlit", "run", ruta("app.py"), "--global.developmentMode=false",
                "--server.headless=true", f"--server.port={PUERTO}", "--browser.gatherUsageStats=false"]
    sys.exit(stcli.main())
