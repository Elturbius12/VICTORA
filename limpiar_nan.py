"""Script de una sola vez: corrige productos cuyo precio quedo como NaN
por el bug del importador de catalogo. Los deja en 0 para que puedan
editarse normalmente desde Registro de Ventas.

Uso: colocar este archivo dentro de la carpeta "La Victoriana" y
ejecutar:  python limpiar_nan.py
"""
import sqlite3
import os
import math

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "victoriana.db")

conn = sqlite3.connect(DB_PATH)
rows = conn.execute("SELECT id, nombre, precio FROM productos").fetchall()

corregidos = []
for pid, nombre, precio in rows:
    if precio is None or (isinstance(precio, float) and math.isnan(precio)):
        conn.execute("UPDATE productos SET precio=0 WHERE id=?", (pid,))
        corregidos.append(nombre)

conn.commit()
conn.close()

if corregidos:
    print(f"Se corrigieron {len(corregidos)} producto(s) con precio invalido (NaN -> 0):")
    for n in corregidos:
        print(f"  - {n}")
    print("\nAhora ve a 'Registro de Ventas' y ponles su precio real.")
else:
    print("No se encontro ningun producto con precio invalido. Todo bien.")
