import io

import openpyxl

from victora.plantilla import plantilla_ejemplo
from victora.validador import ERROR, completar_ventas, validar


def _modificar(fn):
    wb = openpyxl.load_workbook(io.BytesIO(plantilla_ejemplo()))
    fn(wb)
    b = io.BytesIO()
    wb.save(b)
    return b.getvalue()


def _errores(r):
    t = r.tabla()
    return t[t["Nivel"] == ERROR]


def test_ejemplo_pasa():
    r = validar(plantilla_ejemplo())
    assert r.semaforo in ("verde", "amarillo")
    assert r.datos["Ventas"].shape[0] == 21 * 32


def test_detecta_errores_con_hoja_fila_columna():
    def romper(wb):
        wb["Ventas"]["C5"] = -3              # negativo
        wb["Ventas"]["B6"] = "P999"          # producto inexistente
        wb["Ventas"]["A7"] = "cinco de oct"  # fecha inválida
        wb["Productos"]["E3"] = 150          # margen fuera de rango
        wb["Recetas"]["E2"] = "tazas"        # unidad desconocida
    r = validar(_modificar(romper))
    e = _errores(r)
    assert r.semaforo == "rojo"
    claves = set(zip(e["Hoja"], e["Fila"], e["Columna"]))
    assert ("Ventas", "5", "unidades_vendidas") in claves
    assert ("Ventas", "6", "producto_id") in claves
    assert ("Ventas", "7", "fecha") in claves
    assert ("Productos", "3", "margen_esperado_pct") in claves
    assert ("Recetas", "2", "unidad_medida") in claves


def test_falta_hoja():
    r = validar(_modificar(lambda wb: wb.remove(wb["Recetas"])))
    assert r.semaforo == "rojo"
    assert "Recetas" in set(r.tabla()["Hoja"])


def test_huecos_y_tratamiento():
    def quitar_dia(wb):
        ws = wb["Ventas"]
        filas = [row[0].row for row in ws.iter_rows(min_row=2) if str(row[0].value).startswith("2026-10-10")]
        for f in sorted(filas, reverse=True):
            ws.delete_rows(f)
    r = validar(_modificar(quitar_dia))
    assert len(r.huecos) == 1
    m_cero = completar_ventas(r.datos, {r.huecos[0]: "cero"})
    m_cer = completar_ventas(r.datos, {r.huecos[0]: "cerrado"})
    assert len(m_cero) == 21 and len(m_cer) == 20
    assert m_cero.loc[r.huecos[0]].sum() == 0


def test_pocos_dias_bloquea():
    def recortar(wb):
        ws = wb["Ventas"]
        filas = [row[0].row for row in ws.iter_rows(min_row=2) if str(row[0].value) >= "2026-10-11"]
        for f in sorted(filas, reverse=True):
            ws.delete_rows(f)
    r = validar(_modificar(recortar))
    assert r.semaforo == "rojo"
