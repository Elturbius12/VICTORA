# -*- mode: python ; coding: utf-8 -*-
# Construir:  pyinstaller --noconfirm VICTORA.spec   (o ejecutar construir_exe.bat)
from PyInstaller.utils.hooks import collect_all, collect_submodules, copy_metadata

datas = [("app.py", "."), ("victora", "victora"), ("datos_demo", "datos_demo"), (".streamlit", ".streamlit")]
binaries, hiddenimports = [], []
for paquete in ("streamlit",):  # incluye streamlit.testing para --autotest
    d, b, h = collect_all(paquete)
    datas += d; binaries += b; hiddenimports += h
datas += copy_metadata("streamlit")
hiddenimports += collect_submodules("statsmodels.tsa") + collect_submodules("victora")
hiddenimports += ["docx", "scipy.special._cdflib", "openpyxl", "xlsxwriter", "matplotlib.backends.backend_agg"]

excluir = ["tkinter", "IPython", "jupyter", "notebook", "pytest", "torch", "tensorflow", "PyQt5", "PyQt6",
           "PySide2", "PySide6", "psycopg", "sphinx", "streamlit_drawable_canvas", "matplotlib.tests",
           "numpy.tests", "scipy.tests", "pandas.tests", "statsmodels.tests", "sklearn", "numba", "llvmlite",
           "pyarrow.tests", "PIL.ImageQt", "cv2", "sympy"]

a = Analysis(["lanzador.py"], pathex=["."], binaries=binaries, datas=datas, hiddenimports=hiddenimports,
             excludes=excluir, noarchive=False)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name="VICTORA", console=True, upx=False)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name="VICTORA")
