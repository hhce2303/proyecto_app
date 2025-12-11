"""
Vista para Specials - UI y renderizado de specials del supervisor
Responsabilidad: Solo presentación y manejo de eventos UI
"""

import tkinter as tk
from tkinter import messagebox
import traceback

from controllers.specials_controller import SpecialsController


def render_specials_container(parent, username, UI, SheetClass):
    """
    Renderiza el contenedor de Specials
    
    Args:
        parent: Widget padre donde se montará el contenedor
        username (str): Nombre del supervisor
        UI: Módulo customtkinter (o None para tkinter estándar)
        SheetClass: Clase tksheet para las tablas
    
    Returns:
        dict: Diccionario con referencias:
            - container: Frame principal
            - sheet: Widget tksheet
            - sheet_frame: Frame del sheet
            - marks_frame: Frame de botones de marcado
            - controller: Instancia del controlador
            - refresh: Función para refrescar datos
            - row_ids: Lista de IDs actuales (mutable)
            - refresh_job: Job ID del auto-refresh (mutable)
    """
    # Crear instancia del controlador
    controller = SpecialsController(username)
    
    # Variables de estado (estas necesitan ser accesibles desde closures)
    state = {
        'row_ids': [],
        'refresh_job': None,
        'auto_refresh_active': tk.BooleanVar(value=True)
    }
    
    # Contenedor principal
    if UI is not None:
        specials_container = UI.CTkFrame(parent, fg_color="#2c2f33")
    else:
        specials_container = tk.Frame(parent, bg="#2c2f33")
    
    # Frame para tksheet de Specials
    if UI is not None:
        sheet_frame = UI.CTkFrame(specials_container, fg_color="#2c2f33")
    else:
        sheet_frame = tk.Frame(specials_container, bg="#2c2f33")
    sheet_frame.pack(fill="both", expand=True)

    # Columnas y anchos
    columns = ["ID", "Fecha Hora", "Sitio", "Actividad", "Cantidad", "Camera", 
              "Descripcion", "Usuario", "TZ", "Marca"]
    
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
        "Marca": 180
    }

    # Crear tksheet
    sheet = SheetClass(
        sheet_frame,
        headers=columns,
        theme="dark blue",
        height=600,
        width=1350,
        show_selected_cells_border=True,
        show_row_index=True,
        show_top_left=False,
        empty_horizontal=0,
        empty_vertical=0
    )
    
    # Bindings para tksheet
    sheet.enable_bindings([
        "single_select",
        "drag_select",
        "column_select",
        "row_select",
        "column_width_resize",
        "double_click_column_resize",
        "row_height_resize",
        "arrowkeys",
        "right_click_popup_menu",
        "rc_select",
        "copy"
    ])
    sheet.pack(fill="both", expand=True)
    sheet.change_theme("dark blue")

    # Frame para botones de marcado
    if UI is not None:
        marks_frame = UI.CTkFrame(specials_container, fg_color="#23272a", corner_radius=0)
    else:
        marks_frame = tk.Frame(specials_container, bg="#23272a")
    marks_frame.pack(fill="x", padx=0, pady=(5, 0))

    def apply_sheet_widths():
        """Aplica anchos personalizados a las columnas"""
        for idx, col_name in enumerate(columns):
            if col_name in custom_widths:
                try:
                    sheet.column_width(idx, int(custom_widths[col_name]))
                except Exception:
                    try:
                        sheet.set_column_width(idx, int(custom_widths[col_name]))
                    except Exception:
                        pass
        sheet.redraw()

    def load_data():
        """Carga datos de specials usando el controlador"""
        try:
            # Obtener snapshot del controlador
            snapshot = controller.get_table_snapshot()
            
            # Actualizar estado de IDs
            state['row_ids'] = snapshot['row_ids']
            
            # Aplicar snapshot al sheet
            controller.apply_snapshot_to_sheet(sheet, snapshot, apply_sheet_widths)
            
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo cargar specials:\n{e}", parent=parent)
            traceback.print_exc()
        finally:
            # Programar siguiente refresh si auto-refresh está activo
            if state['auto_refresh_active'].get():
                state['refresh_job'] = parent.after(120000, load_data)  # 2 minutos

    def get_selected_ids():
        """Obtiene los IDs de los registros seleccionados"""
        selected_rows = sheet.get_selected_rows()
        if not selected_rows:
            return []
        ids = []
        for row_idx in selected_rows:
            try:
                if row_idx < len(state['row_ids']):
                    ids.append(state['row_ids'][row_idx])
            except Exception:
                pass
        return ids

    def mark_as_done():
        """Marca los registros seleccionados como 'Registrado'"""
        sel = get_selected_ids()
        if not sel:
            return
        
        try:
            success = controller.mark_specials(sel, 'done')
            if success:
                load_data()
            else:
                messagebox.showerror("Error", "No se pudo marcar como registrado", parent=parent)
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo marcar:\n{e}", parent=parent)
            traceback.print_exc()

    def mark_as_progress():
        """Marca los registros seleccionados como 'En Progreso'"""
        sel = get_selected_ids()
        if not sel:
            messagebox.showinfo("Marcar", "Selecciona uno o más specials para marcar como En Progreso.", parent=parent)
            return
        
        try:
            success = controller.mark_specials(sel, 'flagged')
            if success:
                load_data()
            else:
                messagebox.showerror("Error", "No se pudo marcar como en progreso", parent=parent)
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo marcar:\n{e}", parent=parent)
            traceback.print_exc()

    def unmark_selected():
        """Desmarca los registros seleccionados"""
        sel = get_selected_ids()
        if not sel:
            return
        
        try:
            success = controller.mark_specials(sel, None)
            if success:
                load_data()
            else:
                messagebox.showerror("Error", "No se pudo desmarcar", parent=parent)
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo desmarcar:\n{e}", parent=parent)
            traceback.print_exc()

    def delete_selected():
        """Elimina los registros seleccionados de specials"""
        sel = get_selected_ids()
        if not sel:
            messagebox.showwarning("Eliminar", "Selecciona uno o más specials para eliminar.", parent=parent)
            return
        
        if not messagebox.askyesno("Eliminar", 
                                   f"¿Eliminar {len(sel)} special(s) de la base de datos?",
                                   parent=parent):
            return
        
        try:
            success = controller.delete_specials(sel)
            if success:
                load_data()
            else:
                messagebox.showerror("Error", "No se pudo eliminar", parent=parent)
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo eliminar:\n{e}", parent=parent)
            traceback.print_exc()

    def show_context_menu(event):
        """Muestra menú contextual al hacer clic derecho"""
        context_menu = tk.Menu(parent, tearoff=0, bg="#2c2f33", fg="#e0e0e0", 
                              activebackground="#4a90e2", activeforeground="#ffffff",
                              font=("Segoe UI", 10))
        
        context_menu.add_command(label="✅ Marcar como Registrado", command=mark_as_done)
        context_menu.add_command(label="🔄 Marcar como En Progreso", command=mark_as_progress)
        context_menu.add_separator()
        context_menu.add_command(label="❌ Desmarcar", command=unmark_selected)
        context_menu.add_command(label="🗑️ Eliminar", command=delete_selected)
        
        try:
            context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            context_menu.grab_release()

    def toggle_auto_refresh():
        """Activa/desactiva auto-refresh"""
        if state['auto_refresh_active'].get():
            print("[DEBUG] Auto-refresh activado")
            load_data()
        else:
            print("[DEBUG] Auto-refresh desactivado")
            if state['refresh_job']:
                parent.after_cancel(state['refresh_job'])

    # Botones de marcado
    if UI is not None:
        UI.CTkButton(marks_frame, text="✅ Marcar como Registrado", 
                    command=mark_as_done,
                    fg_color="#00c853", hover_color="#00a043",
                    width=180, height=35,
                    font=("Segoe UI", 11, "bold")).pack(side="left", padx=(15, 5), pady=10)
        
        UI.CTkButton(marks_frame, text="🔄 Marcar como En Progreso", 
                    command=mark_as_progress,
                    fg_color="#f5a623", hover_color="#e69515",
                    width=200, height=35,
                    font=("Segoe UI", 11, "bold")).pack(side="left", padx=5, pady=10)
        
        UI.CTkButton(marks_frame, text="❌ Desmarcar", 
                    command=unmark_selected,
                    fg_color="#3b4754", hover_color="#4a5560",
                    width=120, height=35,
                    font=("Segoe UI", 11, "bold")).pack(side="left", padx=5, pady=10)
        
        # Nota: "Otros Specials" se maneja externamente en supervisor_window
        
        UI.CTkCheckBox(marks_frame, text="Auto-refresh (2 min)", 
                      variable=state['auto_refresh_active'],
                      fg_color="#4a90e2", text_color="#e0e0e0",
                      command=toggle_auto_refresh,
                      font=("Segoe UI", 10)).pack(side="right", padx=(5, 15), pady=10)
    else:
        tk.Button(marks_frame, text="✅ Marcar como Registrado", 
                 command=mark_as_done,
                 bg="#00c853", fg="white",
                 font=("Segoe UI", 11, "bold"), relief="flat",
                 width=20).pack(side="left", padx=(15, 5), pady=10)
        
        tk.Button(marks_frame, text="🔄 Marcar como En Progreso", 
                 command=mark_as_progress,
                 bg="#f5a623", fg="white",
                 font=("Segoe UI", 11, "bold"), relief="flat",
                 width=22).pack(side="left", padx=5, pady=10)
        
        tk.Button(marks_frame, text="❌ Desmarcar", 
                 command=unmark_selected,
                 bg="#3b4754", fg="white",
                 font=("Segoe UI", 11, "bold"), relief="flat",
                 width=12).pack(side="left", padx=5, pady=10)
        
        tk.Checkbutton(marks_frame, text="Auto-refresh (2 min)", 
                      variable=state['auto_refresh_active'],
                      command=toggle_auto_refresh,
                      bg="#23272a", fg="#e0e0e0", selectcolor="#23272a",
                      font=("Segoe UI", 10)).pack(side="right", padx=(5, 15), pady=10)

    # Vincular eventos
    sheet.bind("<Button-3>", show_context_menu)  # Menú contextual
    sheet.bind("<Double-Button-1>", lambda e: mark_as_done())  # Doble-click marca como "Registrado"

    # Retornar referencias
    return {
        'container': specials_container,
        'sheet': sheet,
        'sheet_frame': sheet_frame,
        'marks_frame': marks_frame,
        'controller': controller,
        'refresh': load_data,
        'state': state  # Para acceso a row_ids y refresh_job
    }

