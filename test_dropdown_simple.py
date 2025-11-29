"""
Test para investigar cómo funcionan los dropdowns de tksheet

Según la documentación de tksheet v7+:
- dropdown() crea un "span" que convierte celdas en dropdowns
- Puede requerir configuración adicional o eventos específicos
"""

import tkinter as tk
from tksheet import Sheet

root = tk.Tk()
root.title("Dropdown Investigation")
root.geometry("900x500")

info = tk.Label(root, text="Probando diferentes formas de activar dropdowns", 
               bg="#2c2f33", fg="white", font=("Segoe UI", 12, "bold"), pady=10)
info.pack(fill="x")

frame = tk.Frame(root)
frame.pack(fill="both", expand=True, padx=10, pady=10)

sheet = Sheet(frame, headers=["ID", "Sitio", "Actividad", "Notas"])
sheet.enable_bindings()
sheet.pack(fill="both", expand=True)

# Datos
sheet.set_sheet_data([
    ["1", "", "", ""],
    ["2", "", "", ""],
    ["3", "", "", ""],
])

sites = ["Site A", "Site B", "Site C"]
activities = ["Call", "Meeting", "Break"]

# Probar diferentes configuraciones
print("\n=== PROBANDO DIFERENTES CONFIGURACIONES ===\n")

# Configuración 1: Con edit_data=True
span1 = sheet.dropdown(0, 1, 10, 1, values=sites, edit_data=True, state="normal")
print(f"Config 1 - edit_data=True, state=normal")
print(f"  Span: {span1}")
print(f"  Type: {type(span1)}")

# Configuración 2: Con diferentes opciones
span2 = sheet.dropdown(0, 2, 10, 2, values=activities, edit_data=True, state="normal", redraw=True)
print(f"\nConfig 2 - Con redraw=True")
print(f"  Span: {span2}")

# Información adicional
print(f"\n=== INFORMACIÓN DE SHEET ===")
print(f"Total rows: {sheet.total_rows()}")
print(f"Total columns: {sheet.total_columns()}")

# Instrucciones
instructions = """
CÓMO PROBAR:
1. Click simple en celda de columna "Sitio" o "Actividad"
2. Doble-click en la celda
3. Presiona F2 (editar)
4. Presiona Enter
5. Click derecho
6. Comienza a escribir directamente

¿Qué observas? ¿Aparece algún dropdown/combobox?
"""

inst_label = tk.Label(root, text=instructions, bg="#1e1e1e", fg="#00ff00", 
                     font=("Consolas", 9), justify="left", pady=10)
inst_label.pack(fill="x")

# Detectar eventos
def on_cell_select(event):
    sel = sheet.get_currently_selected()
    if sel and sel.row is not None and sel.column is not None:
        print(f"\n>>> CELDA SELECCIONADA: Row={sel.row}, Col={sel.column}, Columna='{sheet.headers()[sel.column]}'")

def on_edit_cell(event):
    sel = sheet.get_currently_selected()
    if sel and sel.row is not None and sel.column is not None:
        val = sheet.get_cell_data(sel.row, sel.column)
        print(f">>> CELDA EDITADA: ({sel.row}, {sel.column}) = '{val}'")

sheet.bind("<<SheetSelect>>", on_cell_select)
sheet.bind("<<SheetModified>>", on_edit_cell)

root.mainloop()
