import tkinter as tk
from tksheet import Sheet

root = tk.Tk()
root.title("Test Dropdown Debug")
root.geometry("1200x600")

# Crear sheet
frame = tk.Frame(root)
frame.pack(fill="both", expand=True, padx=10, pady=10)

sheet = Sheet(
    frame,
    headers=["FechaHora", "Sitio", "Actividad", "Cantidad", "Camera", "Descripción"],
    height=400,
    width=1200
)

# Habilitar bindings
sheet.enable_bindings([
    "single_select",
    "row_select",
    "column_select",
    "arrowkeys",
    "copy",
    "paste",
    "delete",
    "undo",
    "edit_cell"
])

sheet.pack(fill="both", expand=True)
sheet.change_theme("dark blue")

# Datos de prueba
sheet.set_sheet_data([
    ["2025-11-06 10:00", "Site A", "Call", "1", "12", "Test 1"],
    ["2025-11-06 11:00", "Site B", "Meeting", "2", "13", "Test 2"],
    ["", "", "", "0", "", ""],  # Fila vacía para nuevo
])

# Anchos de columna
sheet.column_width(0, 150)
sheet.column_width(1, 220)
sheet.column_width(2, 180)
sheet.column_width(3, 80)
sheet.column_width(4, 100)
sheet.column_width(5, 250)

# Listas de valores
sites = ["Site A", "Site B", "Site C", "Site D", "Site E"]
activities = ["Call", "Call Report", "Meeting", "Training", "Break"]

print("=" * 60)
print("CONFIGURANDO DROPDOWNS")
print("=" * 60)

# Método 1: Configurar dropdown por rango
try:
    result1 = sheet.dropdown(0, 1, 100, 1, values=sites, edit_data=True)
    print(f"✅ Dropdown columna 1 (Sitio): {type(result1)}")
    print(f"   Configurado para filas 0-100, columna 1")
except Exception as e:
    print(f"❌ Error dropdown columna 1: {e}")

try:
    result2 = sheet.dropdown(0, 2, 100, 2, values=activities, edit_data=True)
    print(f"✅ Dropdown columna 2 (Actividad): {type(result2)}")
    print(f"   Configurado para filas 0-100, columna 2")
except Exception as e:
    print(f"❌ Error dropdown columna 2: {e}")

print("\n" + "=" * 60)
print("INSTRUCCIONES")
print("=" * 60)
print("1. Haz clic en una celda de la columna 'Sitio' (segunda columna)")
print("2. Haz clic en una celda de la columna 'Actividad' (tercera columna)")
print("3. Verifica si aparece un dropdown")
print("4. Si no aparece, intenta hacer doble-clic")
print("5. Revisa si hay alguna indicación visual")
print("=" * 60)

# Event binding para debugging
def on_select(event):
    selection = sheet.get_currently_selected()
    if selection:
        print(f"\n[SELECT] Row: {selection.row}, Col: {selection.column}")
        if selection.row is not None and selection.column is not None:
            value = sheet.get_cell_data(selection.row, selection.column)
            print(f"[VALUE] Celda ({selection.row}, {selection.column}): '{value}'")

def on_edit(event):
    print(f"\n[EDIT] Sheet modificado")
    selection = sheet.get_currently_selected()
    if selection and selection.row is not None and selection.column is not None:
        value = sheet.get_cell_data(selection.row, selection.column)
        print(f"[EDIT] Celda ({selection.row}, {selection.column}) = '{value}'")

sheet.bind("<<SheetSelect>>", on_select)
sheet.bind("<<SheetModified>>", on_edit)

# Botón para agregar fila nueva
def add_row():
    current = sheet.get_sheet_data()
    current.append(["", "", "", "0", "", ""])
    sheet.set_sheet_data(current)
    
    # Re-configurar dropdowns después de set_sheet_data
    sheet.dropdown(0, 1, 100, 1, values=sites, edit_data=True)
    sheet.dropdown(0, 2, 100, 2, values=activities, edit_data=True)
    
    # Re-aplicar anchos
    sheet.column_width(0, 150)
    sheet.column_width(1, 220)
    sheet.column_width(2, 180)
    sheet.column_width(3, 80)
    sheet.column_width(4, 100)
    sheet.column_width(5, 250)
    
    sheet.redraw()
    print(f"\n[ADD ROW] Nueva fila agregada, dropdowns reconfigurados")

btn_frame = tk.Frame(root)
btn_frame.pack(pady=5)

tk.Button(btn_frame, text="➕ Agregar Fila Nueva", command=add_row, 
         bg="#00c853", fg="white", font=("Segoe UI", 11, "bold"),
         relief="flat", padx=20, pady=10).pack()

root.mainloop()
