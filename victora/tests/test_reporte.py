import io

import openpyxl
import pandas as pd
import pytest

from datos_demo.demo_data import generar
from victora.pipeline import ejecutar
from victora.plantilla import _escribir
from victora.reporte_excel import HOJAS
from victora.validador import validar


@pytest.fixture(scope="module")
def R():
    return ejecutar(validar(_escribir(generar(), True)).datos)


def test_hojas_reporte(R):
    wb = openpyxl.load_workbook(io.BytesIO(R["excel_reporte"]))
    assert wb.sheetnames == list(HOJAS)
    assert "Tabla 1." in str(wb["02_Problema_Ahorro"]["A3"].value)
    metodos = " ".join(str(c.value) for c in wb["14_Texto_Metodos"]["A"] if c.value)
    assert "Cᵤ / (Cᵤ + Cₒ)" in metodos and "MASE" in metodos
    res = " ".join(str(c.value) for c in wb["15_Texto_Resultados"]["A"] if c.value)
    assert f"{R['n_dias']} días" in res
    assert len(wb["17_Figuras"]._images) >= 5


def test_plan_cocina(R):
    wb = openpyxl.load_workbook(io.BytesIO(R["excel_plan"]))
    assert "Producir" in wb.sheetnames and "Compras" in wb.sheetnames


def test_produccion_real_marca_real():
    d = generar()
    v = d["Ventas"]
    d["Produccion_real"] = pd.DataFrame({"fecha": v["fecha"], "producto_id": v["producto_id"],
                                         "unidades_producidas": v["unidades_vendidas"] + 3,
                                         "unidades_sobrantes": 3})
    R = ejecutar(validar(_escribir(d, True)).datos)
    assert R["fuente"] == "REAL"
    assert set(R["det"].loc[R["det"]["politica"] == "P0", "fuente"]) == {"REAL"}
