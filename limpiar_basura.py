"""Script de una sola vez: elimina productos 'basura' que se colaron en la
base de datos porque el catalogo tenia notas de texto en la misma columna
que los nombres de productos.

Uso: colocar este archivo dentro de la carpeta "La Victoriana" y ejecutar:
  python limpiar_basura.py
"""
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "victoriana.db")

conn = sqlite3.connect(DB_PATH)
rows = conn.execute("SELECT id, nombre FROM productos").fetchall()

eliminados = []
for pid, nombre in rows:
    # Un nombre de producto real es corto. Las notas que se colaron son
    # frases largas (mas de 40 caracteres) o empiezan con simbolos de alerta.
    if len(nombre) > 40 or nombre.strip().startswith(("⚠", "Llene", "Luego", "Precios estimados", "Revisa")):
        conn.execute("DELETE FROM ventas WHERE producto_id=?", (pid,))
        conn.execute("DELETE FROM productos WHERE id=?", (pid,))
        eliminados.append(nombre)

conn.commit()
conn.close()

if eliminados:
    print(f"Se eliminaron {len(eliminados)} producto(s) basura:")
    for n in eliminados:
        print(f"  - {n[:60]}...")
else:
    print("No se encontro ningun producto basura. Todo bien.")
