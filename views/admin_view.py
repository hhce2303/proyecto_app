"""
Admin View - Interfaz de usuario para administración de tablas
Implementa UI pura separada de lógica de negocio
"""
import tkinter as tk
from tkinter import messagebox, ttk
from datetime import datetime
try:
    import customtkinter as ctk
    HAS_CTK = True
except ImportError:
    HAS_CTK = False

try:
    import under_super
except:
    under_super = None

from controllers.admin_controller import AdminController
from utils.ui_factory import UIFactory
import traceback


def render_admin_container_mvc(parent, username, UI, SheetClass):
    """
    Renderiza el contenedor Admin (MVC completo)
    
    Args:
        parent: Widget padre donde montar el container
        username: Nombre de usuario actual
        UI: Módulo CustomTkinter o None para tkinter
        SheetClass: Clase tksheet.Sheet para tabla
    
    Returns:
        dict: {
            "container": Frame principal,
            "sheet": Widget tksheet,
            "controller": Instancia de AdminController,
            "refresh": Función para recargar tabla
        }
    """
    try:
        # Inicializar controller
        controller = AdminController(username)
        
        # Detectar si UI es CustomTkinter o None
        is_ctk = UI is not None
        
        # Container principal
        if is_ctk:
            container = UI.CTkFrame(parent, fg_color="#2c2f33")
        else:
            container = tk.Frame(parent, bg="#2c2f33")
        
        # Frame superior para título
        if is_ctk:
            admin_toolbar = UI.CTkFrame(container, fg_color="#23272a", corner_radius=0, height=100)
        else:
            admin_toolbar = tk.Frame(container, bg="#23272a", height=100)
        admin_toolbar.pack(fill="x", padx=0, pady=0)
        admin_toolbar.pack_propagate(False)
        
        # Título
        if is_ctk:
            UI.CTkLabel(admin_toolbar, text="🔧 Administración de Base de Datos", 
                       font=("Segoe UI", 14, "bold"), text_color="#e0e0e0").pack(side="top", padx=20, pady=(10, 5))
        else:
            tk.Label(admin_toolbar, text="🔧 Administración de Base de Datos", 
                    bg="#23272a", fg="#e0e0e0", font=("Segoe UI", 14, "bold")).pack(side="top", padx=20, pady=(10, 5))
        
        # Frame para controles
        if is_ctk:
            admin_controls = UI.CTkFrame(admin_toolbar, fg_color="transparent")
        else:
            admin_controls = tk.Frame(admin_toolbar, bg="#23272a")
        admin_controls.pack(fill="x", padx=20, pady=5)
        
        # Variables
        tabla_var = tk.StringVar()
        fecha_desde_var = tk.StringVar()
        fecha_hasta_var = tk.StringVar()
        columna_fecha_var = tk.StringVar(value="Auto")
        tipo_evento_var = tk.StringVar(value="Todos")
        
        # Label y selector de tabla
        if is_ctk:
            UI.CTkLabel(admin_controls, text="Tabla:", text_color="#e0e0e0").pack(side="left", padx=5)
            tabla_combo = UI.CTkComboBox(
                admin_controls, variable=tabla_var, 
                values=controller.get_available_tables(),
                font=("Segoe UI", 10), width=200
            )
            tabla_combo.pack(side="left", padx=5)
        else:
            tk.Label(admin_controls, text="Tabla:", bg="#23272a", fg="#e0e0e0").pack(side="left", padx=5)
            if under_super and hasattr(under_super, 'FilteredCombobox'):
                tabla_combo = under_super.FilteredCombobox(
                    admin_controls, textvariable=tabla_var, 
                    values=controller.get_available_tables(),
                    font=("Segoe UI", 10), width=25,
                    background='#2b2b2b', foreground='#ffffff',
                    bordercolor='#4a90e2', arrowcolor='#ffffff'
                )
            else:
                tabla_combo = ttk.Combobox(
                    admin_controls, textvariable=tabla_var,
                    values=controller.get_available_tables(),
                    width=25
                )
            tabla_combo.pack(side="left", padx=5)
        
        # Label y combobox de columna fecha
        if is_ctk:
            UI.CTkLabel(admin_controls, text="Columna Fecha:", text_color="#e0e0e0").pack(side="left", padx=(15, 5))
            columna_fecha_combo = UI.CTkComboBox(
                admin_controls, variable=columna_fecha_var, values=["Auto"],
                font=("Segoe UI", 10), width=150
            )
            columna_fecha_combo.pack(side="left", padx=5)
        else:
            tk.Label(admin_controls, text="Columna Fecha:", bg="#23272a", fg="#e0e0e0").pack(side="left", padx=(15, 5))
            if under_super and hasattr(under_super, 'FilteredCombobox'):
                columna_fecha_combo = under_super.FilteredCombobox(
                    admin_controls, textvariable=columna_fecha_var, values=["Auto"],
                    font=("Segoe UI", 10), width=20,
                    background='#2b2b2b', foreground='#ffffff',
                    bordercolor='#4a90e2', arrowcolor='#ffffff'
                )
            else:
                columna_fecha_combo = ttk.Combobox(
                    admin_controls, textvariable=columna_fecha_var,
                    values=["Auto"], width=15
                )
            columna_fecha_combo.pack(side="left", padx=5)
        
        # Fecha desde
        if is_ctk:
            UI.CTkLabel(admin_controls, text="Desde:", text_color="#e0e0e0").pack(side="left", padx=(15, 5))
            fecha_desde_frame = tk.Frame(admin_controls, bg="#23272a")
            fecha_desde_frame.pack(side="left", padx=5)
        else:
            tk.Label(admin_controls, text="Desde:", bg="#23272a", fg="#e0e0e0").pack(side="left", padx=(15, 5))
            fecha_desde_frame = tk.Frame(admin_controls, bg="#23272a")
            fecha_desde_frame.pack(side="left", padx=5)
        
        # DateEntry o Entry simple
        try:
            import tkcalendar
            fecha_desde_entry = tkcalendar.DateEntry(
                fecha_desde_frame, textvariable=fecha_desde_var,
                date_pattern='yyyy-mm-dd', width=12
            )
            fecha_desde_entry.pack()
        except:
            tk.Entry(fecha_desde_frame, textvariable=fecha_desde_var, width=12).pack()
        
        # Fecha hasta
        if is_ctk:
            UI.CTkLabel(admin_controls, text="Hasta:", text_color="#e0e0e0").pack(side="left", padx=(15, 5))
            fecha_hasta_frame = tk.Frame(admin_controls, bg="#23272a")
            fecha_hasta_frame.pack(side="left", padx=5)
        else:
            tk.Label(admin_controls, text="Hasta:", bg="#23272a", fg="#e0e0e0").pack(side="left", padx=(15, 5))
            fecha_hasta_frame = tk.Frame(admin_controls, bg="#23272a")
            fecha_hasta_frame.pack(side="left", padx=5)
        
        try:
            import tkcalendar
            fecha_hasta_entry = tkcalendar.DateEntry(
                fecha_hasta_frame, textvariable=fecha_hasta_var,
                date_pattern='yyyy-mm-dd', width=12
            )
            fecha_hasta_entry.pack()
        except:
            tk.Entry(fecha_hasta_frame, textvariable=fecha_hasta_var, width=12).pack()
        
        # Tipo Evento (oculto por defecto)
        if is_ctk:
            tipo_evento_label = UI.CTkLabel(admin_controls, text="Tipo Evento:", text_color="#e0e0e0")
            tipo_evento_combo = UI.CTkComboBox(
                admin_controls, variable=tipo_evento_var,
                values=["Todos"],
                font=("Segoe UI", 10), width=150
            )
        else:
            tipo_evento_label = tk.Label(admin_controls, text="Tipo Evento:", bg="#23272a", fg="#e0e0e0")
            if under_super and hasattr(under_super, 'FilteredCombobox'):
                tipo_evento_combo = under_super.FilteredCombobox(
                    admin_controls, textvariable=tipo_evento_var,
                    values=["Todos"],
                    font=("Segoe UI", 10), width=20,
                    background='#2b2b2b', foreground='#ffffff',
                    bordercolor='#4a90e2', arrowcolor='#ffffff'
                )
            else:
                tipo_evento_combo = ttk.Combobox(
                    admin_controls, textvariable=tipo_evento_var,
                    values=["Todos"], width=15
                )
        
        # Botones de acción
        if is_ctk:
            UI.CTkButton(admin_controls, text="🔄 Cargar", command=lambda: load_admin_table(),
                        fg_color="#4a90e2", hover_color="#357ABD",
                        width=100, height=32, font=("Segoe UI", 11, "bold")).pack(side="left", padx=5)
            UI.CTkButton(admin_controls, text="➕ Crear", command=lambda: create_admin_record(),
                        fg_color="#00c853", hover_color="#00a043",
                        width=100, height=32, font=("Segoe UI", 11, "bold")).pack(side="left", padx=5)
            UI.CTkButton(admin_controls, text="✏️ Editar", command=lambda: edit_admin_selected(),
                        fg_color="#f0ad4e", hover_color="#ec971f",
                        width=100, height=32, font=("Segoe UI", 11, "bold")).pack(side="left", padx=5)
            UI.CTkButton(admin_controls, text="🗑️ Eliminar", command=lambda: delete_admin_selected(),
                        fg_color="#d32f2f", hover_color="#b71c1c",
                        width=100, height=32, font=("Segoe UI", 11, "bold")).pack(side="left", padx=5)
        else:
            tk.Button(admin_controls, text="🔄 Cargar", command=lambda: load_admin_table(),
                     bg="#4a90e2", fg="white", font=("Segoe UI", 11, "bold"),
                     relief="flat", width=10).pack(side="left", padx=5)
            tk.Button(admin_controls, text="➕ Crear", command=lambda: create_admin_record(),
                     bg="#00c853", fg="white", font=("Segoe UI", 11, "bold"),
                     relief="flat", width=10).pack(side="left", padx=5)
            tk.Button(admin_controls, text="✏️ Editar", command=lambda: edit_admin_selected(),
                     bg="#f0ad4e", fg="white", font=("Segoe UI", 11, "bold"),
                     relief="flat", width=10).pack(side="left", padx=5)
            tk.Button(admin_controls, text="🗑️ Eliminar", command=lambda: delete_admin_selected(),
                     bg="#d32f2f", fg="white", font=("Segoe UI", 11, "bold"),
                     relief="flat", width=10).pack(side="left", padx=5)
        
        # Frame para tksheet
        if is_ctk:
            admin_sheet_frame = UI.CTkFrame(container, fg_color="#2c2f33")
        else:
            admin_sheet_frame = tk.Frame(container, bg="#2c2f33")
        admin_sheet_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Crear tksheet
        admin_sheet = SheetClass(
            admin_sheet_frame,
            data=[["Seleccione una tabla y presione 'Cargar'"]],
            headers=["Datos"],
            theme="dark blue",
            height=500,
            width=1330,
            show_selected_cells_border=True,
            show_row_index=True,
            show_top_left=False,
            empty_horizontal=0,
            empty_vertical=0,
            auto_resize_columns=False,
            auto_resize_rows=False
        )
        admin_sheet.enable_bindings([
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
        admin_sheet.pack(fill="both", expand=True)
        
        # =========================
        # FUNCIONES INTERNAS
        # =========================
        
        def load_admin_table():
            """Carga la tabla seleccionada con filtros"""
            table_name = tabla_var.get()
            if not table_name:
                messagebox.showwarning("Advertencia", "Seleccione una tabla primero", parent=container)
                return
            
            # Mostrar/ocultar filtro de tipo evento
            if table_name == "eventos":
                tipo_evento_label.pack(side="left", padx=(15, 5))
                tipo_evento_combo.pack(side="left", padx=5)
            else:
                tipo_evento_label.pack_forget()
                tipo_evento_combo.pack_forget()
            
            # Obtener filtros
            fecha_desde = fecha_desde_var.get().strip() or None
            fecha_hasta = fecha_hasta_var.get().strip() or None
            columna_fecha = columna_fecha_var.get() if columna_fecha_var.get() != "Auto" else None
            tipo_evento = tipo_evento_var.get() if tipo_evento_var.get() != "Todos" else None
            
            # Cargar datos
            rows, col_names = controller.load_table(
                table_name,
                fecha_desde=fecha_desde,
                fecha_hasta=fecha_hasta,
                columna_fecha=columna_fecha,
                tipo_evento=tipo_evento
            )
            
            if rows is None:
                messagebox.showerror("Error", "No se pudo cargar la tabla", parent=container)
                return
            
            # Formatear datos para tksheet
            data = []
            for row in rows:
                row_data = []
                for v in row:
                    if v is None:
                        row_data.append("")
                    else:
                        try:
                            if isinstance(v, (bytes, bytearray, memoryview)):
                                row_data.append(v.hex())
                            else:
                                row_data.append(str(v))
                        except Exception:
                            row_data.append(repr(v))
                data.append(row_data)
            
            # Actualizar tksheet
            admin_sheet.set_sheet_data(data if data else [["No hay datos"] + [""] * (len(col_names)-1)])
            admin_sheet.headers(col_names)
            
            # Ajustar anchos
            for col_idx in range(len(col_names)):
                admin_sheet.column_width(column=col_idx, width=150)
            
            admin_sheet.refresh()
            
            # Actualizar columnas de fecha disponibles
            fecha_cols = controller.get_fecha_columns()
            if fecha_cols:
                if is_ctk:
                    columna_fecha_combo.configure(values=["Auto"] + fecha_cols)
                else:
                    columna_fecha_combo['values'] = ["Auto"] + fecha_cols
            
            # Si es eventos, cargar tipos disponibles
            if table_name == "eventos":
                unique_tipos = set()
                for row in rows:
                    if len(row) > 3:
                        unique_tipos.add(str(row[3]))
                if is_ctk:
                    tipo_evento_combo.configure(values=["Todos"] + sorted(unique_tipos))
                else:
                    tipo_evento_combo['values'] = ["Todos"] + sorted(unique_tipos)
            
            print(f"[INFO] Tabla '{table_name}' cargada: {len(rows)} registros")
        
        def edit_admin_selected():
            """Abre ventana de edición para registro seleccionado"""
            selected = admin_sheet.get_selected_rows()
            if not selected:
                messagebox.showwarning("Advertencia", "Seleccione una fila primero", parent=container)
                return
            
            if isinstance(selected, set):
                selected = list(selected)
            
            row_index = selected[0]
            record_data = controller.get_record_for_edit(row_index)
            
            if not record_data:
                messagebox.showerror("Error", "No se pudo cargar el registro", parent=container)
                return
            
            _open_edit_window(record_data, row_index)
        
        def create_admin_record():
            """Abre ventana de creación de nuevo registro"""
            if not controller.current_table:
                messagebox.showwarning("Advertencia", "Cargue una tabla primero", parent=container)
                return
            
            visible_cols = controller.get_fields_for_create()
            if not visible_cols:
                messagebox.showerror("Error", "No se pudo obtener estructura de la tabla", parent=container)
                return
            
            _open_create_window(visible_cols)
        
        def delete_admin_selected():
            """Elimina registro seleccionado"""
            selected = admin_sheet.get_selected_rows()
            if not selected:
                messagebox.showwarning("Advertencia", "Seleccione una fila primero", parent=container)
                return
            
            if isinstance(selected, set):
                selected = list(selected)
            
            confirm = messagebox.askyesno(
                "Confirmar Eliminación",
                "¿Está seguro de eliminar este registro?\n(Se moverá a la papelera)",
                parent=container
            )
            
            if not confirm:
                return
            
            row_index = selected[0]
            success, error_msg = controller.delete_selected(row_index)
            
            if success:
                messagebox.showinfo("Éxito", "Registro eliminado correctamente", parent=container)
                load_admin_table()  # Recargar tabla
            else:
                messagebox.showerror("Error", error_msg, parent=container)
        
        def _open_edit_window(record_data, row_index):
            """
            Abre ventana modal para editar registro
            
            Args:
                record_data: Dict {col_name: value}
                row_index: Índice de la fila
            """
            if is_ctk:
                edit_win = UI.CTkToplevel(parent)
                edit_win.configure(fg_color="#2c2f33")
            else:
                edit_win = tk.Toplevel(parent)
                edit_win.configure(bg="#2c2f33")
            
            edit_win.title(f"Editar Registro - {controller.current_table}")
            
            # Calcular altura dinámica basada en número de campos
            num_fields = len(record_data)
            field_height = 45  # Altura aproximada por campo
            base_height = 120  # Header + botones + padding
            calculated_height = min(base_height + (num_fields * field_height), 700)  # Max 700px
            
            edit_win.geometry(f"600x{calculated_height}")
            edit_win.grab_set()
            
            # Frame scrollable
            if UI == "customtkinter" and HAS_CTK:
                scroll_height = calculated_height - 120
                scroll_frame = ctk.CTkScrollableFrame(edit_win, width=580, height=scroll_height)
                scroll_frame.pack(fill="both", expand=True, padx=10, pady=(10, 5))
            else:
                canvas_container = tk.Frame(edit_win, bg="#2c2f33")
                canvas_container.pack(fill="both", expand=True, padx=10, pady=(10, 5))
                
                canvas = tk.Canvas(canvas_container, bg="#2c2f33", highlightthickness=0)
                scrollbar = tk.Scrollbar(canvas_container, orient="vertical", command=canvas.yview)
                scroll_frame = tk.Frame(canvas, bg="#2c2f33")
                
                canvas.configure(yscrollcommand=scrollbar.set)
                scrollbar.pack(side="right", fill="y")
                canvas.pack(side="left", fill="both", expand=True)
                canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
                scroll_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
            
            # Crear campos
            field_widgets = {}
            col_names = list(record_data.keys())
            
            # Obtener lista de usuarios para comboboxes (si aplica)
            users_list, id_to_name_dict = controller.get_users_for_combobox()
            
            for i, col_name in enumerate(col_names):
                if is_ctk:
                    row_frame = UI.CTkFrame(scroll_frame, fg_color="transparent")
                else:
                    row_frame = tk.Frame(scroll_frame, bg="#2c2f33")
                row_frame.pack(fill="x", pady=5)
                
                if is_ctk:
                    lbl = UI.CTkLabel(row_frame, text=f"{col_name}:", width=200, anchor="w")
                else:
                    lbl = tk.Label(row_frame, text=f"{col_name}:", bg="#2c2f33", fg="#e0e0e0", width=25, anchor="w")
                lbl.pack(side="left", padx=5)
                
                value = record_data[col_name]
                if value is None:
                    value = ""
                
                # Para gestion_breaks_programados, usar comboboxes en campos User_*
                if (controller.current_table == "gestion_breaks_programados" and 
                    col_name in ["User_covering", "User_covered", "Supervisor"]):
                    
                    var = tk.StringVar()
                    if str(value) in id_to_name_dict:
                        var.set(id_to_name_dict[str(value)])
                    else:
                        var.set("")
                    
                    if under_super and hasattr(under_super, 'FilteredCombobox'):
                        widget = under_super.FilteredCombobox(
                            row_frame,
                            textvariable=var,
                            values=users_list,
                            width=30
                        )
                    elif UI == "customtkinter" and HAS_CTK:
                        widget = ctk.CTkComboBox(row_frame, variable=var, values=users_list, width=300)
                    else:
                        widget = tk.ttk.Combobox(row_frame, textvariable=var, values=users_list, width=30)
                    
                    widget.pack(side="left", padx=5, fill="x", expand=True)
                    field_widgets[col_name] = var
                else:
                    # Campo normal
                    var = tk.StringVar(value=str(value))
                    
                    if UI == "customtkinter" and HAS_CTK:
                        widget = ctk.CTkEntry(row_frame, textvariable=var, width=300)
                    else:
                        widget = tk.Entry(row_frame, textvariable=var, width=35, bg="#23272a", fg="#ffffff", insertbackground="#ffffff")
                    
                    widget.pack(side="left", padx=5, fill="x", expand=True)
                    field_widgets[col_name] = var
            
            # Botones
            if is_ctk:
                btn_save_frame = UI.CTkFrame(edit_win, fg_color="transparent")
            else:
                btn_save_frame = tk.Frame(edit_win, bg="#2c2f33")
            btn_save_frame.pack(side="bottom", fill="x", padx=10, pady=(5, 10))
            
            def save_changes():
                field_values = {}
                for col_name, var in field_widgets.items():
                    val = var.get().strip()
                    # Convertir vacíos a None para fechas y FKs
                    if val == "":
                        val = None
                    field_values[col_name] = val
                
                success, error_msg = controller.save_edit(row_index, field_values)
                
                if success:
                    messagebox.showinfo("Éxito", "Registro actualizado correctamente")
                    edit_win.destroy()
                    on_load_table()  # Recargar tabla
                else:
                    messagebox.showerror("Error", error_msg)
            
            if is_ctk:
                btn_save = UI.CTkButton(btn_save_frame, text="💾 Guardar", command=save_changes,
                                       fg_color="#4a90e2", hover_color="#357ABD",
                                       width=120, height=35)
                btn_cancel = UI.CTkButton(btn_save_frame, text="❌ Cancelar", command=edit_win.destroy,
                                         fg_color="#d32f2f", hover_color="#b71c1c",
                                         width=120, height=35)
            else:
                btn_save = tk.Button(btn_save_frame, text="💾 Guardar", command=save_changes,
                                    bg="#4a90e2", fg="white", font=("Segoe UI", 11, "bold"),
                                    relief="flat", width=12)
                btn_cancel = tk.Button(btn_save_frame, text="❌ Cancelar", command=edit_win.destroy,
                                      bg="#d32f2f", fg="white", font=("Segoe UI", 11, "bold"),
                                      relief="flat", width=12)
            
            btn_save.pack(side="left", padx=5)
            btn_cancel.pack(side="left", padx=5)
        
        def _open_create_window(visible_cols):
            """
            Abre ventana modal para crear nuevo registro
            
            Args:
                visible_cols: Lista de columnas visibles (sin IDs autoincrementales)
            """
            if is_ctk:
                create_win = UI.CTkToplevel(parent)
                create_win.configure(fg_color="#2c2f33")
            else:
                create_win = tk.Toplevel(parent)
                create_win.configure(bg="#2c2f33")
            
            create_win.title(f"Crear Registro - {controller.current_table}")
            
            # Calcular altura dinámica basada en número de campos
            num_fields = len(visible_cols)
            field_height = 45  # Altura aproximada por campo
            base_height = 120  # Header + botones + padding
            calculated_height = min(base_height + (num_fields * field_height), 700)  # Max 700px
            
            create_win.geometry(f"600x{calculated_height}")
            create_win.grab_set()
            
            # Frame scrollable
            if UI == "customtkinter" and HAS_CTK:
                scroll_height = calculated_height - 120
                scroll_frame = ctk.CTkScrollableFrame(create_win, width=580, height=scroll_height)
                scroll_frame.pack(fill="both", expand=True, padx=10, pady=(10, 5))
            else:
                canvas_container = tk.Frame(create_win, bg="#2c2f33")
                canvas_container.pack(fill="both", expand=True, padx=10, pady=(10, 5))
                
                canvas = tk.Canvas(canvas_container, bg="#2c2f33", highlightthickness=0)
                scrollbar = tk.Scrollbar(canvas_container, orient="vertical", command=canvas.yview)
                scroll_frame = tk.Frame(canvas, bg="#2c2f33")
                
                canvas.configure(yscrollcommand=scrollbar.set)
                scrollbar.pack(side="right", fill="y")
                canvas.pack(side="left", fill="both", expand=True)
                canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
                scroll_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
            
            # Crear campos
            field_widgets = {}
            
            for col_name in visible_cols:
                if is_ctk:
                    row_frame = UI.CTkFrame(scroll_frame, fg_color="transparent")
                else:
                    row_frame = tk.Frame(scroll_frame, bg="#2c2f33")
                row_frame.pack(fill="x", pady=5)
                
                if is_ctk:
                    lbl = UI.CTkLabel(row_frame, text=f"{col_name}:", width=200, anchor="w")
                else:
                    lbl = tk.Label(row_frame, text=f"{col_name}:", bg="#2c2f33", fg="#e0e0e0", width=25, anchor="w")
                lbl.pack(side="left", padx=5)
                
                var = tk.StringVar()
                
                if UI == "customtkinter" and HAS_CTK:
                    widget = ctk.CTkEntry(row_frame, textvariable=var, width=300)
                else:
                    widget = tk.Entry(row_frame, textvariable=var, width=35, bg="#23272a", fg="#ffffff", insertbackground="#ffffff")
                
                widget.pack(side="left", padx=5, fill="x", expand=True)
                field_widgets[col_name] = var
            
            # Botones
            if is_ctk:
                btn_create_frame = UI.CTkFrame(create_win, fg_color="transparent")
            else:
                btn_create_frame = tk.Frame(create_win, bg="#2c2f33")
            btn_create_frame.pack(side="bottom", fill="x", padx=10, pady=(5, 10))
            
            def save_new():
                field_values = {}
                for col_name, var in field_widgets.items():
                    val = var.get().strip()
                    if val == "":
                        val = None
                    field_values[col_name] = val
                
                success, error_msg = controller.save_create(field_values)
                
                if success:
                    messagebox.showinfo("Éxito", "Registro creado correctamente")
                    create_win.destroy()
                    on_load_table()  # Recargar tabla
                else:
                    messagebox.showerror("Error", error_msg)
            
            if is_ctk:
                btn_save = UI.CTkButton(btn_create_frame, text="💾 Crear", command=save_new,
                                       fg_color="#00c853", hover_color="#00a043",
                                       width=120, height=35)
                btn_cancel = UI.CTkButton(btn_create_frame, text="❌ Cancelar", command=create_win.destroy,
                                         fg_color="#d32f2f", hover_color="#b71c1c",
                                         width=120, height=35)
            else:
                btn_save = tk.Button(btn_create_frame, text="💾 Crear", command=save_new,
                                    bg="#00c853", fg="white", font=("Segoe UI", 11, "bold"),
                                    relief="flat", width=12)
                btn_cancel = tk.Button(btn_create_frame, text="❌ Cancelar", command=create_win.destroy,
                                      bg="#d32f2f", fg="white", font=("Segoe UI", 11, "bold"),
                                      relief="flat", width=12)
            
            btn_save.pack(side="left", padx=5)
            btn_cancel.pack(side="left", padx=5)
        
        # Función de refresh
        def refresh_table():
            """Recarga la tabla actual con filtros actuales"""
            if controller.current_table:
                load_admin_table()
        
        return {
            "container": container,
            "sheet": admin_sheet,
            "controller": controller,
            "refresh": refresh_table
        }
    
    except Exception as e:
        print(f"[ERROR] render_admin_container_mvc: {e}")
        traceback.print_exc()
        
        # Devolver container mínimo en caso de error
        is_ctk = UI is not None
        if is_ctk:
            fallback_frame = UI.CTkFrame(parent)
        else:
            fallback_frame = tk.Frame(parent)
        tk.Label(fallback_frame, text=f"Error al cargar Admin: {e}", fg="red").pack()
        
        return {
            "container": fallback_frame,
            "sheet": None,
            "controller": None,
            "refresh": lambda: None
        }


def render_admin_view(top, username, controller, UI=None):
    """Función legacy - redirige a render_admin_container_mvc"""
    import tksheet
    return render_admin_container_mvc(top, username, UI or "tkinter", tksheet.Sheet)