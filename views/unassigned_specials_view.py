"""
Vista para Specials Sin Asignar (Unassigned Specials)
Renderiza el container con tksheet y controles para gestionar specials sin marcar
"""

import tkinter as tk
from tkinter import messagebox
from controllers.unassigned_specials_controller import UnassignedSpecialsController


def render_unassigned_specials_container(parent, username, UI, SheetClass):
    """
    Renderiza el container completo de Specials Sin Asignar
    
    Args:
        parent: Widget padre (ventana principal)
        username: Nombre del usuario (Lead Supervisor)
        UI: Módulo CustomTkinter
        SheetClass: Clase tksheet.Sheet
        
    Returns:
        Dict con {"container": frame, "sheet": sheet, "refresh": función}
    """
    
    # Crear controlador
    controller = UnassignedSpecialsController(username)
    
    # Columnas y anchos personalizados
    columns = ["ID", "Fecha Hora", "Sitio", "Actividad", "Cantidad", "Camera", "Descripcion", "Usuario", "TZ", "Supervisor"]
    custom_widths = {
        "ID": 60,
        "Fecha Hora": 150,
        "Sitio": 220,
        "Actividad": 150,
        "Cantidad": 70,
        "Camera": 80,
        "Descripcion": 190,
        "Usuario": 100,
        "TZ": 90,
        "Supervisor": 150
    }
    
    # Container principal
    container = UI.CTkFrame(parent, fg_color="#2c2f33")
    
    # ==================== TOOLBAR DE ACCIONES ====================
    
    actions_frame = UI.CTkFrame(container, fg_color="#23272a", corner_radius=0, height=60)
    actions_frame.pack(fill="x", padx=0, pady=0)
    actions_frame.pack_propagate(False)
    
    UI.CTkLabel(
        actions_frame,
        text="⚠️ Specials Sin Marcar (Pendientes de Revisión)",
        font=("Segoe UI", 14, "bold"),
        text_color="#ffa726"
    ).pack(side="left", padx=20, pady=15)
    
    # ==================== FRAME PARA TKSHEET ====================
    
    sheet_frame = UI.CTkFrame(container, fg_color="#2c2f33")
    sheet_frame.pack(fill="both", expand=True, padx=0, pady=10)
    
    # Crear tksheet
    sheet = SheetClass(
        sheet_frame,
        headers=columns,
        theme="dark blue",
        height=550,
        width=1350,
        show_selected_cells_border=True,
        show_row_index=True,
        show_top_left=False,
        empty_horizontal=0,
        empty_vertical=0,
        auto_resize_columns=False,
        auto_resize_rows=False
    )
    
    sheet.enable_bindings([
        "single_select",
        "drag_select",
        "column_select",
        "row_select",
        "column_width_resize",
        "double_click_column_resize",
        "arrowkeys",
        "copy",
        "select_all"
    ])
    
    sheet.pack(fill="both", expand=True)
    
    # Aplicar anchos personalizados
    for col_idx, col_name in enumerate(columns):
        if col_name in custom_widths:
            sheet.column_width(column=col_idx, width=custom_widths[col_name])
    
    # ==================== FUNCIONES INTERNAS ====================
    
    def load_specials():
        """Carga los specials sin asignar en el sheet"""
        success, data, error_msg = controller.load_data()
        
        if success:
            if not data:
                # Sin datos o sin shift activo
                empty_msg = error_msg if error_msg else "No hay specials sin asignar"
                sheet.set_sheet_data([[empty_msg] + [""] * (len(columns)-1)])
            else:
                sheet.set_sheet_data(data)
                
                # Re-aplicar anchos después de cargar datos
                for col_idx, col_name in enumerate(columns):
                    if col_name in custom_widths:
                        sheet.column_width(column=col_idx, width=custom_widths[col_name])
        else:
            messagebox.showerror("Error", error_msg, parent=container)
            sheet.set_sheet_data([["Error al cargar datos"] + [""] * (len(columns)-1)])
    
    def assign_supervisor():
        """Abre ventana modal para asignar supervisor a filas seleccionadas"""
        selected = sheet.get_selected_rows()
        if not selected:
            messagebox.showwarning("Advertencia", "Selecciona al menos un special para asignar", parent=container)
            return
        
        # Crear ventana modal
        assign_win = UI.CTkToplevel(parent)
        assign_win.configure(fg_color="#2c2f33")
        assign_win.title("Asignar Supervisor")
        assign_win.geometry("400x250")
        assign_win.resizable(False, False)
        assign_win.transient(parent)
        assign_win.grab_set()
        
        # Header
        UI.CTkLabel(
            assign_win,
            text="Selecciona un Supervisor:",
            text_color="#00bfae",
            font=("Segoe UI", 16, "bold")
        ).pack(pady=(20, 10))
        
        # Container para combobox
        combo_container = UI.CTkFrame(assign_win, fg_color="#2c2f33")
        combo_container.pack(fill="both", expand=True, padx=20, pady=(0, 15))
        
        # Obtener lista de supervisores
        supervisores = controller.get_supervisors()
        if not supervisores:
            supervisores = ["No hay supervisores disponibles"]
        
        sup_var = tk.StringVar()
        
        supervisor_combo = UI.CTkOptionMenu(
            combo_container,
            variable=sup_var,
            values=supervisores,
            fg_color="#262a31",
            button_color="#14414e",
            text_color="#00bfae",
            font=("Segoe UI", 13)
        )
        
        if supervisores and supervisores[0] != "No hay supervisores disponibles":
            sup_var.set(supervisores[0])
        
        supervisor_combo.pack(fill="x", padx=10, pady=10)
        
        def confirm_assignment():
            """Confirma y ejecuta la asignación"""
            supervisor_name = sup_var.get()
            
            if not supervisor_name or supervisor_name == "No hay supervisores disponibles":
                messagebox.showwarning("Sin selección", "Selecciona un supervisor válido", parent=assign_win)
                return
            
            # Asignar supervisor
            success, message = controller.assign_supervisor_to_rows(selected, supervisor_name)
            
            if success:
                messagebox.showinfo("Éxito", message, parent=assign_win)
                assign_win.destroy()
                load_specials()  # Recargar datos
            else:
                messagebox.showerror("Error", message, parent=assign_win)
        
        # Frame de botones
        btn_frame = UI.CTkFrame(assign_win, fg_color="#2c2f33")
        btn_frame.pack(fill="x", padx=20, pady=(0, 20))
        
        UI.CTkButton(
            btn_frame,
            text="✅ Asignar",
            command=confirm_assignment,
            fg_color="#00c853",
            hover_color="#00a043",
            font=("Segoe UI", 12, "bold"),
            width=150
        ).pack(side="left", padx=(0, 10))
        
        UI.CTkButton(
            btn_frame,
            text="❌ Cancelar",
            command=assign_win.destroy,
            fg_color="#d32f2f",
            hover_color="#b71c1c",
            font=("Segoe UI", 12, "bold"),
            width=150
        ).pack(side="right")
    
    # ==================== BOTONES DEL TOOLBAR ====================
    
    UI.CTkButton(
        actions_frame,
        text="👤 Asignar Supervisor",
        command=assign_supervisor,
        fg_color="#00c853",
        hover_color="#00a043",
        width=160,
        height=35,
        font=("Segoe UI", 12, "bold")
    ).pack(side="right", padx=(5, 20), pady=12)
    
    UI.CTkButton(
        actions_frame,
        text="🔄 Refrescar",
        command=load_specials,
        fg_color="#4D6068",
        hover_color="#27a3e0",
        width=120,
        height=35,
        font=("Segoe UI", 12, "bold")
    ).pack(side="right", padx=5, pady=12)
    
    # ==================== RETORNAR COMPONENTES ====================
    
    return {
        "container": container,
        "sheet": sheet,
        "refresh": load_specials
    }
