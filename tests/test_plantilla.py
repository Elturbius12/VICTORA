import io

import openpyxl

from victora.plantilla import ESQUEMA, plantilla_ejemplo, plantilla_recetas, plantilla_vacia


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
    assert ws["A1"].fill.fgColor.rgb.endswith("FFFFCC")  # obligatoria = amarillo claro
    assert ws["C1"].fill.fgColor.rgb.endswith("E0E0E0")  # opcional = gris claro
    assert len(ws.data_validations.dataValidation) >= 5


def test_ejemplo_32_productos_ficticios():
    wb = openpyxl.load_workbook(io.BytesIO(plantilla_ejemplo()))
    assert wb["Ventas"].max_row == 1 + 21 * 32
    assert wb["Productos"].max_row == 33
    assert any("FICTICIOS" in str(c.value) for c in wb["LEEME"]["A"])


def test_plantilla_recetas_guia():
    wb = openpyxl.load_workbook(io.BytesIO(plantilla_recetas()))
    assert wb.sheetnames == ["GUIA_RECETAS", "Recetas"]
    ws = wb["Recetas"]
    assert [c.value for c in ws[1]][:6] == [c for c, _, _ in ESQUEMA["Recetas"]]
    assert [ws.cell(r, 3).value for r in (2, 3, 4)] == ["Harina preparada", "Queso mozzarella", "Salsa de tomate"]
    assert ws["D2"].value == 250 and ws["E3"].value == "g"
    texto = " ".join(str(c.value) for c in wb["GUIA_RECETAS"]["A"] if c.value)
    assert "UN insumo de UN producto" in texto and "1000 g" in " ".join(
        str(c.value) for row in wb["GUIA_RECETAS"].iter_rows() for c in row if c.value)
