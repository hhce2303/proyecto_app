import tkinter as tk
from tkinter import ttk, messagebox
from controllers.breaks_controller import BreaksController


def render_breaks_container(parent, username=None, UI=None, SheetClass=None, under_super=None):
    """Renderiza el container completo de Breaks con controles y tabla
    
    Args:
        parent: Frame padre donde se renderizará
        username: Nombre del supervisor que aprueba los breaks
        UI: Módulo customtkinter o None para tkinter estándar
        SheetClass: Clase tksheet.Sheet o None
        under_super: Módulo con FilteredCombobox
        
    Returns:
        dict: Referencias a widgets y controlador
    """
    # Crear controlador
    controller = BreaksController()
    
    # Container principal
    if UI is not None:
        breaks_container = UI.CTkFrame(parent, fg_color="#2c2f33")
    else:
        breaks_container = tk.Frame(parent, bg="#2c2f33")
    
    # NO hacer pack aquí - lo hace el caller
    
    # Frame de controles
    if UI is not None:
        breaks_controls_frame = UI.CTkFrame(breaks_container, fg_color="#23272a", corner_radius=8)
    else:
        breaks_controls_frame = tk.Frame(breaks_container, bg="#23272a")
    breaks_controls_frame.pack(fill="x", padx=10, pady=10)
    
    # Variables para comboboxes
    usuario_a_cubrir_var = tk.StringVar()
    cubierto_por_var = tk.StringVar()
    hora_var = tk.StringVar()
    
    # Cargar usuarios
    users_list = controller.load_users_list()
    
    # Variable para almacenar el sheet
    breaks_sheet = None
    cell_break_map = {}
    table_state = {
        "row_count": 0,
        "column_count": 0,
        "headers": [],
        "column_keys": [],
    }

    def fetch_table_snapshot():
        """Obtiene la estructura tabular desde el controlador y actualiza el estado local"""
        snapshot = controller.get_table_snapshot()

        headers = snapshot.get("headers") or ["Hora Programada"]
        data = snapshot.get("rows") or []
        cell_map = snapshot.get("cell_map") or {}

        cell_break_map.clear()
        cell_break_map.update(cell_map)

        table_state["row_count"] = snapshot.get("row_count", len(data))
        table_state["column_count"] = snapshot.get("column_count", len(headers))
        table_state["headers"] = headers
        table_state["column_keys"] = snapshot.get("column_keys", [])

        return headers, data
    
    # ==================== FUNCIONES INTERNAS ====================
    
    def refrescar_tabla():
        """Refresca los datos de la tabla"""
        if breaks_sheet is None:
            return
        
        headers, data = fetch_table_snapshot()

        breaks_sheet.headers(headers)
        breaks_sheet.set_sheet_data(data)
        
        # Ajustar anchos
        breaks_sheet.column_width(column=0, width=130)
        for i in range(1, len(headers)):
            breaks_sheet.column_width(column=i, width=150)
        
        breaks_sheet.redraw()
    
    def limpiar_formulario():
        """Limpia los campos del formulario"""
        usuario_a_cubrir_var.set("")
        cubierto_por_var.set("")
        hora_var.set("")
    
    def agregar_break():
        """Agrega un nuevo break usando el controlador"""
        user_covered = usuario_a_cubrir_var.get().strip()
        user_covering = cubierto_por_var.get().strip()
        break_time = hora_var.get().strip()
        
        if not user_covered or not user_covering or not break_time:
            messagebox.showwarning("Agregar Break", "Completa todos los campos", parent=breaks_container)
            return
        
        if user_covered == user_covering:
            messagebox.showwarning("Agregar Break", "Un usuario no puede cubrirse a sí mismo", parent=breaks_container)
            return
        
        success = controller.add_break(user_covered, user_covering, break_time, username or 'Sistema', callback=refrescar_tabla)
        
        if success:
            messagebox.showinfo("Agregar Break", "✅ Break agregado exitosamente", parent=breaks_container)
            limpiar_formulario()
        else:
            messagebox.showerror("Error", "❌ No se pudo agregar el break", parent=breaks_container)
    
    def eliminar_break():
        """Elimina el break seleccionado"""
        if breaks_sheet is None:
            return
        
        # Obtener datos actuales
        selected_ids = set()

        # Selecciones de celdas específicas
        for row_index, col_index in breaks_sheet.get_selected_cells():
            if col_index == 0:
                continue
            selected_ids.update(cell_break_map.get((row_index, col_index), []))

        # Selecciones de filas completas
        for row_index in breaks_sheet.get_selected_rows():
            for col_index in range(1, table_state.get("column_count", 1)):
                selected_ids.update(cell_break_map.get((row_index, col_index), []))

        # Selecciones de columnas completas
        for col_index in breaks_sheet.get_selected_columns():
            if col_index == 0:
                continue
            for row_index in range(table_state.get("row_count", 0)):
                selected_ids.update(cell_break_map.get((row_index, col_index), []))

        # Selección actual (si no se registró en los métodos anteriores)
        if not selected_ids:
            current_selection = breaks_sheet.get_currently_selected(return_tuple=True)
            if current_selection and current_selection[0] == "cell":
                row_index, col_index = current_selection[1], current_selection[2]
                if col_index != 0:
                    selected_ids.update(cell_break_map.get((row_index, col_index), []))

        if not selected_ids:
            messagebox.showwarning(
                "Eliminar Break",
                "Selecciona una celda, fila o columna que contenga breaks válidos",
                parent=breaks_container
            )
            return

        confirm_text = (
            "¿Eliminar el break seleccionado?"
            if len(selected_ids) == 1
            else f"Se eliminarán {len(selected_ids)} breaks. ¿Continuar?"
        )
        if not messagebox.askyesno("Eliminar Break", confirm_text, parent=breaks_container):
            return

        eliminados = 0
        fallidos = []

        for break_id in selected_ids:
            try:
                break_id_int = int(break_id)
            except (TypeError, ValueError):
                break_id_int = break_id

            if controller.delete_break(break_id_int, callback=None):
                eliminados += 1
            else:
                fallidos.append(break_id)

        if eliminados:
            refrescar_tabla()

        if eliminados and not fallidos:
            messagebox.showinfo(
                "Eliminar Break",
                "✅ Se eliminó el break seleccionado" if eliminados == 1 else "✅ Se eliminaron los breaks seleccionados",
                parent=breaks_container
            )
        elif eliminados and fallidos:
            messagebox.showwarning(
                "Eliminar Break",
                "Algunos breaks no se pudieron eliminar: " + ", ".join(map(str, fallidos)),
                parent=breaks_container
            )
        else:
            messagebox.showerror(
                "Eliminar Break",
                "❌ No se pudo eliminar el break seleccionado",
                parent=breaks_container
            )
    
    # ==================== FORMULARIO ====================
    
    # Primera fila: Usuario a cubrir
    row1_frame_breaks = tk.Frame(breaks_controls_frame, bg="#23272a")
    row1_frame_breaks.pack(fill="x", padx=20, pady=(15, 5))
    
    if UI is not None:
        UI.CTkLabel(row1_frame_breaks, text="👤 Usuario a Cubrir:", 
                   text_color="#ffffff", font=("Segoe UI", 14, "bold")).pack(side="left", padx=(0, 10))
    else:
        tk.Label(row1_frame_breaks, text="👤 Usuario a Cubrir:", bg="#23272a", fg="#ffffff", 
                font=("Segoe UI", 14, "bold")).pack(side="left", padx=(0, 10))
    
    if under_super:
        usuario_combo_breaks = under_super.FilteredCombobox(
            row1_frame_breaks, 
            textvariable=usuario_a_cubrir_var,
            values=users_list, 
            width=40,
            font=("Segoe UI", 11)
        )
    else:
        usuario_combo_breaks = ttk.Combobox(
            row1_frame_breaks, 
            textvariable=usuario_a_cubrir_var,
            values=users_list, 
            width=38
        )
    usuario_combo_breaks.set("")
    usuario_combo_breaks.pack(side="left", padx=5)
    
    # Segunda fila: Cubierto por
    row2_frame_breaks = tk.Frame(breaks_controls_frame, bg="#23272a")
    row2_frame_breaks.pack(fill="x", padx=20, pady=5)
    
    if UI is not None:
        UI.CTkLabel(row2_frame_breaks, text="🔄 Cubierto Por:", 
                   text_color="#ffffff", font=("Segoe UI", 14, "bold")).pack(side="left", padx=(0, 10))
    else:
        tk.Label(row2_frame_breaks, text="🔄 Cubierto Por:", bg="#23272a", fg="#ffffff", 
                font=("Segoe UI", 14, "bold")).pack(side="left", padx=(0, 10))
    
    if under_super:
        cover_by_combo_breaks = under_super.FilteredCombobox(
            row2_frame_breaks, 
            textvariable=cubierto_por_var,
            values=users_list, 
            width=40,
            font=("Segoe UI", 11)
        )
    else:
        cover_by_combo_breaks = ttk.Combobox(
            row2_frame_breaks, 
            textvariable=cubierto_por_var,
            values=users_list, 
            width=38
        )
    cover_by_combo_breaks.set("")
    cover_by_combo_breaks.pack(side="left", padx=5)
    
    # Generar lista de horas
    horas_disponibles = [f"{h:02d}:00:00" for h in range(24)]
    
    # Tercera fila: Hora
    row3_frame_breaks = tk.Frame(breaks_controls_frame, bg="#23272a")
    row3_frame_breaks.pack(fill="x", padx=20, pady=5)
    
    if UI is not None:
        UI.CTkLabel(row3_frame_breaks, text="🕐 Hora Programada:", 
                   text_color="#ffffff", font=("Segoe UI", 14, "bold")).pack(side="left", padx=(0, 10))
    else:
        tk.Label(row3_frame_breaks, text="🕐 Hora Programada:", bg="#23272a", fg="#ffffff", 
                font=("Segoe UI", 14, "bold")).pack(side="left", padx=(0, 10))
    
    if under_super:
        hora_combo_breaks = under_super.FilteredCombobox(
            row3_frame_breaks, 
            textvariable=hora_var,
            values=horas_disponibles,
            width=25,
            font=("Segoe UI", 13)
        )
    else:
        hora_combo_breaks = ttk.Combobox(
            row3_frame_breaks, 
            textvariable=hora_var,
            values=horas_disponibles,
            width=23
        )
    hora_combo_breaks.pack(side="left", padx=5)
    
    # Cuarta fila: Botones
    row4_frame_breaks = tk.Frame(breaks_controls_frame, bg="#23272a")
    row4_frame_breaks.pack(fill="x", padx=20, pady=(5, 15))
    
    if UI is not None:
        UI.CTkButton(row4_frame_breaks, text="➕ Agregar",
                    command=agregar_break,
                    fg_color="#28a745", hover_color="#218838",
                    font=("Segoe UI", 13, "bold"),
                    width=150).pack(side="left", padx=5)
        
        UI.CTkButton(row4_frame_breaks, text="🔄 Limpiar",
                    command=limpiar_formulario,
                    fg_color="#6c757d", hover_color="#5a6268",
                    font=("Segoe UI", 13),
                    width=120).pack(side="left", padx=5)
        
        UI.CTkButton(row4_frame_breaks, text="🗑️ Eliminar Seleccionado",
                    command=eliminar_break,
                    fg_color="#dc3545", hover_color="#c82333",
                    font=("Segoe UI", 13),
                    width=200).pack(side="left", padx=5)
    else:
        tk.Button(row4_frame_breaks, text="➕ Agregar",
                 command=agregar_break,
                 bg="#28a745", fg="white",
                 font=("Segoe UI", 11, "bold"),
                 relief="flat", width=12).pack(side="left", padx=5)
        
        tk.Button(row4_frame_breaks, text="🔄 Limpiar",
                 command=limpiar_formulario,
                 bg="#6c757d", fg="white",
                 font=("Segoe UI", 11),
                 relief="flat", width=10).pack(side="left", padx=5)
        
        tk.Button(row4_frame_breaks, text="🗑️ Eliminar",
                 command=eliminar_break,
                 bg="#dc3545", fg="white",
                 font=("Segoe UI", 11),
                 relief="flat", width=15).pack(side="left", padx=5)
    
    # ==================== TABLA (TKSHEET) ====================
    
    if UI is not None:
        breaks_sheet_frame = UI.CTkFrame(breaks_container, fg_color="#2c2f33")
    else:
        breaks_sheet_frame = tk.Frame(breaks_container, bg="#2c2f33")
    breaks_sheet_frame.pack(fill="both", expand=True, padx=10, pady=10)
    
    if SheetClass:
        headers, data = fetch_table_snapshot()
        
        breaks_sheet = SheetClass(
            breaks_sheet_frame,
            headers=headers,
            theme="dark blue",
            width=900,
            height=450,
            show_selected_cells_border=True,
            show_row_index=False,
            show_top_left=False,
            empty_horizontal=0,
            empty_vertical=0
        )
        
        # Bindings (solo lectura)
        breaks_sheet.enable_bindings([
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
        breaks_sheet.pack(fill="both", expand=True)
        
        breaks_sheet.set_sheet_data(data)
        breaks_sheet.change_theme("dark blue")
        
        # Ajustar anchos dinámicamente
        breaks_sheet.column_width(column=0, width=130)  # Hora Programada
        for i in range(1, len(headers)):
            breaks_sheet.column_width(column=i, width=150)
    else:
        if UI is not None:
            UI.CTkLabel(breaks_sheet_frame, text="⚠️ tksheet no instalado", 
                       text_color="#ff6b6b", font=("Segoe UI", 16)).pack(pady=20)
        else:
            tk.Label(breaks_sheet_frame, text="⚠️ tksheet no instalado", 
                    bg="#2c2f33", fg="#ff6b6b", font=("Segoe UI", 16)).pack(pady=20)
    
    # Retornar referencias
    return {
        'container': breaks_container,
        'sheet': breaks_sheet,
        'controller': controller,
        'refresh': refrescar_tabla
    }