import io

import openpyxl

from victora.plantilla import ESQUEMA, plantilla_ejemplo, plantilla_vacia


def test_hojas_y_columnas_exactas():
    for contenido in (plantilla_vacia(), plantilla_ejemplo()):
        wb = openpyxl.load_workbook(io.BytesIO(contenido))
        assert wb.sheetnames == ["LEEME", *ESQUEMA]
        for hoja, cols in ESQUEMA.items():
            enc = [c.value for c in wb[hoja][1]][:len(cols)]
            assert enc == [c for c, _, _ in cols]
            assert wb[hoja].freeze_panes == "A2"


def test_colores_y_validaciones():
    wb = openpyxl.load_workbook(io.BytesIO(plantilla_vacia()))
    ws = wb["Productos"]
    assert ws["A1"].fill.fgColor.rgb.endswith("FFE58F")  # obligatoria = amarillo
    assert ws["C1"].fill.fgColor.rgb.endswith("D9D9D9")  # opcional = gris
    assert len(ws.data_validations.dataValidation) >= 5


def test_ejemplo_tiene_datos_ficticios():
    wb = openpyxl.load_workbook(io.BytesIO(plantilla_ejemplo()))
    assert wb["Ventas"].max_row == 1 + 21 * 10
    assert any("FICTICIOS" in str(c.value) for c in wb["LEEME"]["A"])
