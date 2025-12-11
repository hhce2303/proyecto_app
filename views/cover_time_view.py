import tkinter as tk
from tkinter import ttk, messagebox
from controllers.cover_time_controller import CoverTimeController


def render_cover_time_container(parent, UI=None, SheetClass=None):
    """Renderiza el contenedor completo de Cover Time con tabs y filtros
    
    Args:
        parent: Frame padre donde se renderizará
        UI: Módulo customtkinter o None para tkinter estándar
        SheetClass: Clase tksheet.Sheet o None
        
    Returns:
        dict: Referencias a widgets y controlador
    """
    # Crear controlador
    controller = CoverTimeController()
    
    # Container principal
    if UI is not None:
        cover_container = UI.CTkFrame(parent, fg_color="#2c2f33")
    else:
        cover_container = tk.Frame(parent, bg="#2c2f33")
    
    # Frame de filtros para covers_realizados
    if UI is not None:
        cover_filters_frame = UI.CTkFrame(cover_container, fg_color="#23272a", corner_radius=8)
    else:
        cover_filters_frame = tk.Frame(cover_container, bg="#23272a")
    cover_filters_frame.pack(fill="x", padx=10, pady=10)
    
    # Variables de filtros
    cover_user_var = tk.StringVar()
    cover_desde_var = tk.StringVar()
    cover_hasta_var = tk.StringVar()
    
    # Referencias a sheets
    programados_sheet_ref = None
    realizados_sheet_ref = None
    
    # ==================== FUNCIONES INTERNAS ====================
    
    def load_programados_tab():
        """Carga datos de covers programados"""
        nonlocal programados_sheet_ref
        
        if programados_sheet_ref is None:
            return
        
        snapshot = controller.get_table_snapshot_programados()
        
        programados_sheet_ref.set_sheet_data(snapshot["rows"])
        
        # Aplicar formato a filas inactivas
        if snapshot.get("inactive_rows"):
            for row_idx in snapshot["inactive_rows"]:
                programados_sheet_ref.highlight_rows([row_idx], bg="#3a3a3a", fg="#808080")
        
        programados_sheet_ref.redraw()
    
    def load_realizados_tab():
        """Carga datos de covers realizados sin filtros"""
        nonlocal realizados_sheet_ref
        
        if realizados_sheet_ref is None:
            return
        
        snapshot = controller.get_table_snapshot_realizados()
        realizados_sheet_ref.set_sheet_data(snapshot["rows"])
        realizados_sheet_ref.redraw()
    
    def apply_filters():
        """Aplica filtros a covers_realizados"""
        nonlocal realizados_sheet_ref
        
        if realizados_sheet_ref is None:
            messagebox.showwarning("Filtrar", "No hay datos cargados", parent=cover_container)
            return
        
        user_filter = cover_user_var.get().strip()
        desde_filter = cover_desde_var.get().strip()
        hasta_filter = cover_hasta_var.get().strip()
        
        snapshot = controller.get_table_snapshot_realizados(
            user_filter if user_filter != "Todos" else None,
            desde_filter if desde_filter else None,
            hasta_filter if hasta_filter else None
        )
        
        realizados_sheet_ref.set_sheet_data(snapshot["rows"])
        realizados_sheet_ref.redraw()
    
    def clear_filters():
        """Limpia los filtros y recarga todos los datos"""
        cover_user_var.set("Todos")
        cover_desde_var.set("")
        cover_hasta_var.set("")
        load_realizados_tab()
    
    # ==================== FILTROS ====================
    
    # Usuario
    if UI is not None:
        UI.CTkLabel(cover_filters_frame, text="Usuario:", text_color="#c9d1d9", 
                   font=("Segoe UI", 11)).grid(row=0, column=0, sticky="w", padx=(15, 5), pady=10)
    else:
        tk.Label(cover_filters_frame, text="Usuario:", bg="#23272a", fg="#c9d1d9", 
                font=("Segoe UI", 11)).grid(row=0, column=0, sticky="w", padx=(15, 5), pady=10)
    
    cover_users = controller.get_users_for_filter()
    cover_user_cb = ttk.Combobox(cover_filters_frame, textvariable=cover_user_var, 
                                 values=cover_users, width=20, state="readonly")
    cover_user_cb.set("Todos")
    cover_user_cb.grid(row=0, column=1, sticky="w", padx=5, pady=10)
    
    # Desde
    if UI is not None:
        UI.CTkLabel(cover_filters_frame, text="Desde:", text_color="#c9d1d9", 
                   font=("Segoe UI", 11)).grid(row=0, column=2, sticky="w", padx=(15, 5), pady=10)
    else:
        tk.Label(cover_filters_frame, text="Desde:", bg="#23272a", fg="#c9d1d9", 
                font=("Segoe UI", 11)).grid(row=0, column=2, sticky="w", padx=(15, 5), pady=10)
    
    try:
        from tkcalendar import DateEntry
        cover_desde_entry = DateEntry(
            cover_filters_frame,
            textvariable=cover_desde_var,
            date_pattern="yyyy-mm-dd",
            width=15
        )
    except Exception:
        cover_desde_entry = tk.Entry(cover_filters_frame, textvariable=cover_desde_var, width=17)
    cover_desde_entry.grid(row=0, column=3, sticky="w", padx=5, pady=10)
    
    # Hasta
    if UI is not None:
        UI.CTkLabel(cover_filters_frame, text="Hasta:", text_color="#c9d1d9", 
                   font=("Segoe UI", 11)).grid(row=0, column=4, sticky="w", padx=(15, 5), pady=10)
    else:
        tk.Label(cover_filters_frame, text="Hasta:", bg="#23272a", fg="#c9d1d9", 
                font=("Segoe UI", 11)).grid(row=0, column=4, sticky="w", padx=(15, 5), pady=10)
    
    try:
        from tkcalendar import DateEntry
        cover_hasta_entry = DateEntry(
            cover_filters_frame,
            textvariable=cover_hasta_var,
            date_pattern="yyyy-mm-dd",
            width=15
        )
    except Exception:
        cover_hasta_entry = tk.Entry(cover_filters_frame, textvariable=cover_hasta_var, width=17)
    cover_hasta_entry.grid(row=0, column=5, sticky="w", padx=5, pady=10)
    
    # Botones
    cover_btn_frame = tk.Frame(cover_filters_frame, bg="#23272a")
    cover_btn_frame.grid(row=0, column=6, sticky="e", padx=(15, 15), pady=10)
    
    if UI is not None:
        UI.CTkButton(
            cover_btn_frame,
            text="🔍 Filtrar",
            command=apply_filters,
            fg_color="#4a90e2",
            hover_color="#357ABD",
            width=100,
            height=32,
            font=("Segoe UI", 11, "bold")
        ).pack(side="left", padx=(0, 8))
        
        UI.CTkButton(
            cover_btn_frame,
            text="🗑️ Limpiar",
            command=clear_filters,
            fg_color="#3b4754",
            hover_color="#4a5560",
            width=100,
            height=32,
            font=("Segoe UI", 11, "bold")
        ).pack(side="left")
    else:
        tk.Button(
            cover_btn_frame,
            text="🔍 Filtrar",
            command=apply_filters,
            bg="#4a90e2",
            fg="white",
            activebackground="#357ABD",
            font=("Segoe UI", 11, "bold"),
            relief="flat",
            width=10
        ).pack(side="left", padx=(0, 8))
        
        tk.Button(
            cover_btn_frame,
            text="🗑️ Limpiar",
            command=clear_filters,
            bg="#3b4754",
            fg="white",
            activebackground="#4a5560",
            font=("Segoe UI", 11, "bold"),
            relief="flat",
            width=10
        ).pack(side="left")
    
    # ==================== TABS ====================
    
    if UI is not None:
        cover_notebook = UI.CTkTabview(cover_container, width=1280, height=650)
    else:
        cover_notebook = ttk.Notebook(cover_container)
    cover_notebook.pack(padx=10, pady=10, fill="both", expand=True)
    
    # ==================== TAB PROGRAMADOS ====================
    
    if UI is not None:
        tab_programados = cover_notebook.add("Lista de Covers")
    else:
        tab_programados = tk.Frame(cover_notebook, bg="#2c2f33")
        cover_notebook.add(tab_programados, text="Lista de Covers")
    
    if UI is not None:
        sheet_frame_programados = UI.CTkFrame(tab_programados, fg_color="#2c2f33")
    else:
        sheet_frame_programados = tk.Frame(tab_programados, bg="#2c2f33")
    sheet_frame_programados.pack(fill="both", expand=True, padx=10, pady=10)
    
    if SheetClass:
        snapshot_prog = controller.get_table_snapshot_programados()
        
        programados_sheet_ref = SheetClass(
            sheet_frame_programados,
            headers=snapshot_prog["headers"],
            theme="dark blue",
            height=550,
            width=1220,
            show_selected_cells_border=True,
            show_row_index=False,
            show_top_left=False,
            empty_horizontal=0,
            empty_vertical=0
        )
        
        programados_sheet_ref.enable_bindings([
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
        
        programados_sheet_ref.pack(fill="both", expand=True)
        programados_sheet_ref.change_theme("dark blue")
        programados_sheet_ref.set_sheet_data(snapshot_prog["rows"])
        
        # Ajustar anchos
        programados_sheet_ref.column_width(column=0, width=50)   # #
        programados_sheet_ref.column_width(column=1, width=150)  # Usuario
        programados_sheet_ref.column_width(column=2, width=180)  # Hora solicitud
        programados_sheet_ref.column_width(column=3, width=100)  # Estación
        programados_sheet_ref.column_width(column=4, width=300)  # Razón
        programados_sheet_ref.column_width(column=5, width=110)  # Aprobación
        programados_sheet_ref.column_width(column=6, width=90)   # Estado
        
        # Aplicar formato a inactivos
        if snapshot_prog.get("inactive_rows"):
            for row_idx in snapshot_prog["inactive_rows"]:
                programados_sheet_ref.highlight_rows([row_idx], bg="#3a3a3a", fg="#808080")
    
    # ==================== TAB REALIZADOS ====================
    
    if UI is not None:
        tab_realizados = cover_notebook.add("Covers Completados")
    else:
        tab_realizados = tk.Frame(cover_notebook, bg="#2c2f33")
        cover_notebook.add(tab_realizados, text="Covers Completados")
    
    if UI is not None:
        sheet_frame_realizados = UI.CTkFrame(tab_realizados, fg_color="#2c2f33")
    else:
        sheet_frame_realizados = tk.Frame(tab_realizados, bg="#2c2f33")
    sheet_frame_realizados.pack(fill="both", expand=True, padx=10, pady=10)
    
    if SheetClass:
        snapshot_real = controller.get_table_snapshot_realizados()
        
        realizados_sheet_ref = SheetClass(
            sheet_frame_realizados,
            headers=snapshot_real["headers"],
            theme="dark blue",
            height=550,
            width=1220,
            show_selected_cells_border=True,
            show_row_index=False,
            show_top_left=False,
            empty_horizontal=0,
            empty_vertical=0
        )
        
        realizados_sheet_ref.enable_bindings([
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
        
        realizados_sheet_ref.pack(fill="both", expand=True)
        realizados_sheet_ref.change_theme("dark blue")
        realizados_sheet_ref.set_sheet_data(snapshot_real["rows"])
        
        # Ajustar anchos
        realizados_sheet_ref.column_width(column=0, width=50)   # #
        realizados_sheet_ref.column_width(column=1, width=150)  # Usuario
        realizados_sheet_ref.column_width(column=2, width=160)  # Inicio Cover
        realizados_sheet_ref.column_width(column=3, width=100)  # Duración
        realizados_sheet_ref.column_width(column=4, width=160)  # Fin Cover
        realizados_sheet_ref.column_width(column=5, width=150)  # Cubierto por
        realizados_sheet_ref.column_width(column=6, width=250)  # Motivo
    
    # Retornar referencias
    return {
        'container': cover_container,
        'programados_sheet': programados_sheet_ref,
        'realizados_sheet': realizados_sheet_ref,
        'controller': controller,
        'refresh_programados': load_programados_tab,
        'refresh_realizados': load_realizados_tab
    }
