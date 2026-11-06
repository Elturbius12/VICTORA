"""La Victoriana – Sistema de Pronóstico de Demanda.
Punto de entrada principal.
"""
import sys
import os

# Asegurar que el directorio de la app esté en el path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.database import init_db
from gui.main_window import MainWindow


def main():
    # Inicializar base de datos (solo crea las tablas si no existen, no mete datos)
    init_db()

    # Lanzar GUI
    app = MainWindow()
    app.mainloop()


if __name__ == "__main__":
    main()
