import io
import zipfile

import openpyxl
import pandas as pd
import pytest

from datos_demo.demo_data import generar
from victora.config import HOJAS_REPORTE
from victora.pipeline import ejecutar
from victora.plantilla import _escribir
from victora.validador import validar


@pytest.fixture(scope="module")
def R():
    return ejecutar(validar(_escribir(generar(), True)).datos)


def test_hojas_reporte(R):
    wb = openpyxl.load_workbook(io.BytesIO(R["excel_reporte"]))
    assert wb.sheetnames == list(HOJAS_REPORTE) and len(wb.sheetnames) == 23
    assert "Tabla 1." in str(wb["02_Problema_Ahorro"]["A3"].value)
    metodos = " ".join(str(c.value) for c in wb["14_Texto_Metodos"]["A"] if c.value)
    assert "Cᵤ / (Cᵤ + Cₒ)" in metodos and "MASE" in metodos and "La Victoriana" in metodos
    res = " ".join(str(c.value) for c in wb["15_Texto_Resultados"]["A"] if c.value)
    assert f"{R['n_dias']} días" in res and "Figuras 1 y 2" in res
    assert len(wb["17_Figuras"]._images) >= 5


def test_contexto_editable():
    d = validar(_escribir(generar(14), True)).datos
    R2 = ejecutar(d, contexto={"caso": "Café Prueba", "ciudad": "Cusco, Perú", "software": "VICTORA"})
    metodos = " ".join(t for _, t in R2["texto_metodos"])
    assert "Café Prueba" in metodos and "Cusco, Perú" in metodos


def test_plan_cocina(R):
    wb = openpyxl.load_workbook(io.BytesIO(R["excel_plan"]))
    assert wb.sheetnames == ["Producir", "Detalle", "Compras"]
    enc = [c.value for c in wb["Producir"][3]]
    assert enc[0] == "Producto" and enc[-1] == "TOTAL SEMANA" and len(enc) == 1 + 1 + 7 + 1
    det = [c.value for c in wb["Detalle"][1]]
    assert det[-3:] == ["RECOMENDADO", "Mínimo", "Máximo"]


def test_zip_figuras(R):
    z = zipfile.ZipFile(io.BytesIO(R["zip_figuras"]))
    nombres = z.namelist()
    assert "Leyendas.txt" in nombres and sum(n.endswith(".png") for n in nombres) >= 8
    assert z.read(nombres[0])[:8] == b"\x89PNG\r\n\x1a\n"


def test_minimo_maximo_coherentes(R):
    p = R["plan"]
    assert (p["intervalo_10"] <= p["producir"]).all() and (p["producir"] <= p["intervalo_90"]).all()


def test_12_dias_32_productos_funciona():
    R12 = ejecutar(validar(_escribir(generar(12), True)).datos)
    assert R12["n_productos"] == 32 and R12["n_dias"] == 12 and R12["n_prueba"] == 5
    assert "Holt-Winters" not in set(R12["ranking"]["modelo"])


def test_produccion_real_marca_real():
    d = generar()
    v = d["Ventas"]
    d["Produccion_real"] = pd.DataFrame({"fecha": v["fecha"], "producto_id": v["producto_id"],
                                         "unidades_producidas": v["unidades_vendidas"] + 3,
                                         "unidades_sobrantes": 3})
    Rr = ejecutar(validar(_escribir(d, True)).datos)
    assert Rr["fuente"] == "REAL"
    assert set(Rr["det"].loc[Rr["det"]["politica"] == "P0", "fuente"]) == {"REAL"}
