import datetime
import tkinter as tk
from tkinter import ttk
import sys
from pathlib import Path
import re
import sys

import under_super
sys.path.append(r"C:\Users\hcruz.SIG\OneDrive - SIG Systems, Inc\Desktop\proyecto_app")
from Other_Scripts.testeos import test2
from under_super import get_connection
import customtkinter as ctk
import re

# Importar tksheet
try:
    from tksheet import Sheet
    USE_SHEET = True
except ImportError:
    USE_SHEET = False
    print("[WARN] tksheet no está instalado. Instala con: pip install tksheet")

def test_menu_de_covers_break_ctk():
    
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")
    
    root = ctk.CTk()
    root.geometry("1100x600")
    root.title("Menú de Covers de Break")

    # Frame principal
    main_frame = ctk.CTkFrame(root, fg_color="#1e1e1e")
    main_frame.pack(fill="both", expand=True, padx=20, pady=20)
    
    # Título
    title_label = ctk.CTkLabel(main_frame, text="📋 Covers de Break", 
                               font=ctk.CTkFont(size=24, weight="bold"),
                               text_color="#4aa3ff")
    title_label.pack(pady=(10, 20))

    # Frame para controles (comboboxes y botones)
    controls_frame = ctk.CTkFrame(main_frame, fg_color="#2b2b2b")
    controls_frame.pack(fill="x", padx=10, pady=(0, 10))
    
    # Obtener lista de usuarios desde la base de datos
    user_list = under_super.get_all_users()
    users_list = [user['Nombre_Usuario'] for user in user_list] if user_list else []
    
    
    local_covers_data = []
    
    # Variables para comboboxes
    usuario_a_cubrir_var = tk.StringVar()
    cubierto_por_var = tk.StringVar()
    hora_var = tk.StringVar()
    
    # Primera fila: Usuario a cubrir
    row1_frame = ctk.CTkFrame(controls_frame, fg_color="transparent")
    row1_frame.pack(fill="x", padx=20, pady=(15, 5))
    
    ctk.CTkLabel(row1_frame, text="👤 Usuario a Cubrir:", 
                font=ctk.CTkFont(size=14, weight="bold"),
                text_color="#ffffff").pack(side="left", padx=(0, 10))
    
    usuario_combo = ctk.CTkComboBox(row1_frame, 
                                    variable=usuario_a_cubrir_var,
                                    values=users_list,
                                    width=200,
                                    font=ctk.CTkFont(size=13),
                                    state="readonly")
    usuario_combo.pack(side="left", padx=5)
    usuario_combo.set("Seleccionar...")
    
    # Segunda fila: Cubierto por
    row2_frame = ctk.CTkFrame(controls_frame, fg_color="transparent")
    row2_frame.pack(fill="x", padx=20, pady=5)
    
    ctk.CTkLabel(row2_frame, text="🔄 Cubierto Por:", 
                font=ctk.CTkFont(size=14, weight="bold"),
                text_color="#ffffff").pack(side="left", padx=(0, 10))
    
    cover_by_combo = ctk.CTkComboBox(row2_frame, 
                                     variable=cubierto_por_var,
                                     values=users_list,
                                     width=200,
                                     font=ctk.CTkFont(size=13),
                                     state="readonly")
    cover_by_combo.pack(side="left", padx=5)
    cover_by_combo.set("Seleccionar...")
    
    # Tercera fila: Hora
    row3_frame = ctk.CTkFrame(controls_frame, fg_color="transparent")
    row3_frame.pack(fill="x", padx=20, pady=5)
    
    ctk.CTkLabel(row3_frame, text="🕐 Hora Programada:", 
                font=ctk.CTkFont(size=14, weight="bold"),
                text_color="#ffffff").pack(side="left", padx=(0, 10))
    
    hora_entry = ctk.CTkEntry(row3_frame, 
                              textvariable=hora_var,
                              width=200,
                              font=ctk.CTkFont(size=13),
                              placeholder_text="14:00:00")
    hora_entry.pack(side="left", padx=5)
    
    # Cuarta fila: Botones
    row4_frame = ctk.CTkFrame(controls_frame, fg_color="transparent")
    row4_frame.pack(fill="x", padx=20, pady=(5, 15))
    
    def cargar_datos_agrupados():
        """Carga datos agrupados por quien cubre (covered_by como columnas)"""
        try:
            # Usar los datos locales
            rows = [(usuario, covered_by, hora) for usuario, covered_by, hora in local_covers_data]
            
            # Obtener lista única de "Cubierto Por" para las columnas
            covered_by_set = sorted(set(row[1] for row in rows if row[1]))
            
            # Headers: hora primero + columnas de personas que cubren
            headers = ["Hora Programada"]
            for cb in covered_by_set:
                headers.append(cb)
            
            # Agrupar por hora - solo el PRIMER usuario por covered_by y hora
            horas_dict = {}
            for row in rows:
                usuario = row[0]
                covered_by = row[1]
                hora = row[2]  # Ya es string en formato HH:MM:SS
                
                if hora not in horas_dict:
                    horas_dict[hora] = {cb: "" for cb in covered_by_set}
                
                # Solo asignar si la celda está vacía (un usuario por celda)
                if covered_by in horas_dict[hora] and not horas_dict[hora][covered_by]:
                    horas_dict[hora][covered_by] = usuario
            
            # Convertir a lista de filas para el sheet
            data = []
            for hora in sorted(horas_dict.keys()):
                fila = [hora]
                for covered_by in covered_by_set:
                    fila.append(horas_dict[hora][covered_by])
                data.append(fila)
            
            return headers, data
            
        except Exception as e:
            print(f"[ERROR] cargar_datos_agrupados: {e}")
            import traceback
            traceback.print_exc()
            return ["Hora Programada"], []
    
    def agregar_cover():
        usuario = usuario_a_cubrir_var.get()
        cover = cubierto_por_var.get()
        hora = hora_var.get()
        
        if usuario == "Seleccionar..." or cover == "Seleccionar..." or not hora:
            print("[WARN] Debe completar todos los campos")
            return
        
        # Validar formato de hora (HH:MM:SS)
        if not re.match(r'^([0-1][0-9]|2[0-3]):[0-5][0-9]:[0-5][0-9]$', hora):
            print("[WARN] Formato de hora inválido. Use HH:MM:SS (ej: 14:00:00)")
            return
        
        # Validar que no exista ya un cover asignado para esa hora y covered_by
        for u, c, h in local_covers_data:
            if h == hora and c == cover:
                print(f"[WARN] ⚠️ Ya existe un cover asignado a {cover} a las {hora}. Solo se permite un usuario por celda.")
                return
        
        # Agregar a la lista local
        local_covers_data.append((usuario, cover, hora))
        print(f"[INFO] ✅ Cover agregado: {usuario} cubierto por {cover} a las {hora}")
        
        # Limpiar formulario y refrescar tabla
        limpiar()
        refrescar_tabla()
    
    def limpiar():
        usuario_combo.set("Seleccionar...")
        cover_by_combo.set("Seleccionar...")
        hora_var.set("")
    
    btn_agregar = ctk.CTkButton(row4_frame, text="➕ Agregar",
                                command=agregar_cover,
                                fg_color="#28a745", hover_color="#218838",
                                font=ctk.CTkFont(size=13, weight="bold"),
                                width=150)
    btn_agregar.pack(side="left", padx=5)
    
    btn_limpiar = ctk.CTkButton(row4_frame, text="🔄 Limpiar",
                                command=limpiar,
                                fg_color="#6c757d", hover_color="#5a6268",
                                font=ctk.CTkFont(size=13),
                                width=120)
    btn_limpiar.pack(side="left", padx=5)

    # Frame para tksheet
    tksheet_frame = ctk.CTkFrame(main_frame, fg_color="#2c2f33")
    tksheet_frame.pack(fill="both", expand=True, padx=10, pady=10)
    
    if USE_SHEET:
        headers, data = cargar_datos_agrupados()
        
        sheet = Sheet(tksheet_frame,
                      headers=headers,
                      theme="dark blue",
                      width=1050,
                      height=350)
        sheet.enable_bindings([
            "single_select",
            "drag_select",
            "row_select",
            "column_select",
            "column_width_resize",
            "double_click_column_resize",
            "arrowkeys",
            "copy",
            "select_all"
        ])
        sheet.pack(fill="both", expand=True)
        
        sheet.set_sheet_data(data)
        sheet.change_theme("dark blue")
        
        # Ajustar anchos de columnas
        for i in range(len(headers)):
            sheet.column_width(column=i, width=200)
        
        def eliminar_cover():
            selected_cols = sheet.get_selected_columns()
            selected_cells = sheet.get_selected_cells()
            
            # Caso 1: Se seleccionó una columna completa
            if selected_cols:
                col = list(selected_cols)[0]  # Convertir set a lista
                if col == 0:
                    print("[WARN] No se puede eliminar la columna de Hora.")
                    return
                
                covered_by = sheet.headers()[col]
                
                # Eliminar todos los covers de esa persona
                covers_eliminados = []
                for entrada in local_covers_data[:]:  # Iterar sobre una copia
                    usuario, c_by, h = entrada
                    if c_by == covered_by:
                        covers_eliminados.append(entrada)
                        local_covers_data.remove(entrada)
                        print(f"[INFO] ✅ Cover eliminado: {usuario} cubierto por {c_by} a las {h}")
                
                if covers_eliminados:
                    print(f"[INFO] Total de covers eliminados: {len(covers_eliminados)}")
                    refrescar_tabla()
                else:
                    print("[WARN] No se encontraron covers para eliminar en esa columna.")
                return
            
            # Caso 2: Se seleccionó una celda específica
            if selected_cells:
                row, col = selected_cells[0]
                
                if col == 0:
                    print("[WARN] No se puede eliminar desde la columna de Hora.")
                    return
                
                hora = sheet.get_cell_data(row, 0)  # Hora en la primera columna
                covered_by = sheet.headers()[col]    # Nombre del covered_by
                
                # Buscar y eliminar de la lista local
                for entrada in local_covers_data[:]:
                    usuario, c_by, h = entrada
                    if h == hora and c_by == covered_by:
                        local_covers_data.remove(entrada)
                        print(f"[INFO] ✅ Cover eliminado: {usuario} cubierto por {c_by} a las {h}")
                        refrescar_tabla()
                        return
                
                print("[WARN] No se encontró el cover para eliminar.")
                return
            
            print("[WARN] Seleccione una celda o columna para eliminar el cover.")
        
        btn_eliminar = ctk.CTkButton(controls_frame, text="🗑️ Eliminar Cover Seleccionado",
                                     command=eliminar_cover,
                                     fg_color="#dc3545", hover_color="#c82333",
                                     font=ctk.CTkFont(size=13),
                                     width=220)
        btn_eliminar.pack(side="left", padx=5)
        
        def refrescar_tabla():
            headers, data = cargar_datos_agrupados()
            sheet.headers(headers)
            sheet.set_sheet_data(data)
            # Reajustar anchos después de refrescar
            for i in range(len(headers)):
                sheet.column_width(column=i, width=200)
            sheet.redraw()
        
    else:
        no_sheet_label = ctk.CTkLabel(tksheet_frame, 
                                      text="⚠️ tksheet no instalado", 
                                      font=ctk.CTkFont(size=16),
                                      text_color="#ff6b6b")
        no_sheet_label.pack(pady=20)

    root.mainloop()

# Para probar:
if __name__ == "__main__":
    test_menu_de_covers_break_ctk()
# fin del .spec
