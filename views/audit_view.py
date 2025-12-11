"""
Vista para Audit - UI y renderizado de eventos
Responsabilidad: Solo presentación y manejo de eventos UI
"""

import tkinter as tk
from tkinter import ttk, messagebox
import traceback

from controllers.audit_controller import AuditController
from under_super import FilteredCombobox


def render_audit_container(parent, UI, SheetClass):
    """
    Renderiza el contenedor de Audit
    
    Args:
        parent: Widget padre donde se montará el contenedor
        UI: Módulo customtkinter (o None para tkinter estándar)
        SheetClass: Clase tksheet para las tablas
    
    Returns:
        dict: Diccionario con referencias:
            - container: Frame principal
            - sheet: Widget tksheet
            - controller: Instancia del controlador
            - refresh: Función para refrescar datos
    """
    # Crear instancia del controlador
    controller = AuditController()
    
    # Contenedor principal
    if UI is not None:
        audit_container = UI.CTkFrame(parent, fg_color="#2c2f33")
    else:
        audit_container = tk.Frame(parent, bg="#2c2f33")
    
    # Frame de filtros de Audit
    if UI is not None:
        audit_filters = UI.CTkFrame(audit_container, fg_color="#23272a", corner_radius=8)
    else:
        audit_filters = tk.Frame(audit_container, bg="#23272a")
    audit_filters.pack(fill="x", padx=10, pady=10)

    # Fila 1: Usuario y Sitio
    if UI is not None:
        UI.CTkLabel(audit_filters, text="Usuario:", text_color="#c9d1d9", 
                   font=("Segoe UI", 11)).grid(row=0, column=0, sticky="w", padx=(15, 5), pady=10)
    else:
        tk.Label(audit_filters, text="Usuario:", bg="#23272a", fg="#c9d1d9", 
                font=("Segoe UI", 11)).grid(row=0, column=0, sticky="w", padx=(15, 5), pady=10)
    
    audit_user_var = tk.StringVar()
    # Obtener usuarios del controlador
    audit_users = controller.get_users_list()
    
    # Combobox de usuario con búsqueda parcial
    audit_user_cb = FilteredCombobox(
        audit_filters, 
        textvariable=audit_user_var, 
        values=audit_users, 
        width=25
    )
    audit_user_cb.grid(row=0, column=1, sticky="w", padx=5, pady=10)

    if UI is not None:
        UI.CTkLabel(audit_filters, text="Sitio:", text_color="#c9d1d9", 
                   font=("Segoe UI", 11)).grid(row=0, column=2, sticky="w", padx=(15, 5), pady=10)
    else:
        tk.Label(audit_filters, text="Sitio:", bg="#23272a", fg="#c9d1d9", 
                font=("Segoe UI", 11)).grid(row=0, column=2, sticky="w", padx=(15, 5), pady=10)
    
    audit_site_var = tk.StringVar()
    # Obtener sitios del controlador
    audit_sites = controller.get_sites_list()
    
    # Combobox de sitio con búsqueda parcial
    audit_site_cb = FilteredCombobox(
        audit_filters, 
        textvariable=audit_site_var, 
        values=audit_sites, 
        width=35
    )
    audit_site_cb.grid(row=0, column=3, sticky="w", padx=5, pady=10)

    # Fila 2: Fecha y botones
    if UI is not None:
        UI.CTkLabel(audit_filters, text="Fecha:", text_color="#c9d1d9", 
                   font=("Segoe UI", 11)).grid(row=1, column=0, sticky="w", padx=(15, 5), pady=10)
    else:
        tk.Label(audit_filters, text="Fecha:", bg="#23272a", fg="#c9d1d9", 
                font=("Segoe UI", 11)).grid(row=1, column=0, sticky="w", padx=(15, 5), pady=10)
    
    audit_fecha_var = tk.StringVar()
    try:
        from tkcalendar import DateEntry
        audit_fecha_entry = DateEntry(
            audit_filters,
            textvariable=audit_fecha_var,
            date_pattern="yyyy-mm-dd",
            width=23
        )
    except Exception:
        audit_fecha_entry = tk.Entry(audit_filters, textvariable=audit_fecha_var, width=25)
    audit_fecha_entry.grid(row=1, column=1, sticky="w", padx=5, pady=10)

    # Botones de búsqueda y limpiar
    audit_btn_frame = tk.Frame(audit_filters, bg="#23272a")
    audit_btn_frame.grid(row=1, column=2, columnspan=2, sticky="e", padx=(15, 15), pady=10)

    def audit_search():
        """Busca eventos con los filtros especificados"""
        try:
            user_filter = audit_user_var.get().strip() or None
            site_filter = audit_site_var.get().strip() or None
            fecha_filter = audit_fecha_var.get().strip() or None
            
            # Obtener snapshot del controlador
            snapshot = controller.search_audit_data(
                user_filter=user_filter,
                site_filter=site_filter,
                fecha_filter=fecha_filter
            )
            
            # Aplicar datos al sheet
            controller.apply_snapshot_to_sheet(audit_sheet, snapshot)
            
        except Exception as e:
            messagebox.showerror("Error", f"Error en búsqueda:\n{e}", parent=parent)
            traceback.print_exc()

    def audit_clear():
        """Limpia los filtros de búsqueda"""
        controller.clear_filters(audit_user_var, audit_site_var, audit_fecha_var)
        audit_sheet.set_sheet_data([[]])

    if UI is not None:
        UI.CTkButton(
            audit_btn_frame,
            text="� Buscar",
            command=audit_search,
            fg_color="#4a90e2",
            hover_color="#357ABD",
            width=100,
            height=32,
            font=("Segoe UI", 11, "bold")
        ).pack(side="left", padx=(0, 8))
        
        UI.CTkButton(
            audit_btn_frame,
            text="🗑️ Limpiar",
            command=audit_clear,
            fg_color="#3b4754",
            hover_color="#4a5560",
            width=100,
            height=32,
            font=("Segoe UI", 11, "bold")
        ).pack(side="left")
    else:
        tk.Button(
            audit_btn_frame,
            text="🔍 Buscar",
            command=audit_search,
            bg="#4a90e2",
            fg="white",
            activebackground="#357ABD",
            font=("Segoe UI", 11, "bold"),
            relief="flat",
            width=10
        ).pack(side="left", padx=(0, 8))
        
        tk.Button(
            audit_btn_frame,
            text="🗑️ Limpiar",
            command=audit_clear,
            bg="#3b4754",
            fg="white",
            activebackground="#4a5560",
            font=("Segoe UI", 11, "bold"),
            relief="flat",
            width=10
        ).pack(side="left")

    # Frame para tksheet de Audit
    if UI is not None:
        audit_sheet_frame = UI.CTkFrame(audit_container, fg_color="#2c2f33")
    else:
        audit_sheet_frame = tk.Frame(audit_container, bg="#2c2f33")
    audit_sheet_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))

    # Crear tksheet para Audit (inicializar con snapshot vacío)
    initial_snapshot = controller.get_table_snapshot()
    audit_sheet = SheetClass(audit_sheet_frame, data=[[]], headers=initial_snapshot['headers'])
    audit_sheet.enable_bindings([
        "single_select",
        "row_select",
        "column_width_resize",
        "rc_select",
        "copy",
        "select_all"
    ])
    audit_sheet.pack(fill="both", expand=True)
    audit_sheet.change_theme("dark blue")
    
    # Retornar referencias
    return {
        'container': audit_container,
        'sheet': audit_sheet,
        'controller': controller,
        'refresh': audit_search
    }
