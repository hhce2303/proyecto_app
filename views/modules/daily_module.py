"""
DailyModule - Módulo para gestionar eventos diarios del operador.
Muestra todos los eventos desde el último START SHIFT.

Responsabilidades:
- Mostrar eventos en tksheet
- Permitir edición directa
- Auto-save al editar
- Agregar/Eliminar eventos
- Refrescar datos
"""
import tkinter as tk
from tkinter import messagebox, simpledialog
from tksheet import Sheet
import traceback
from datetime import datetime

from controllers.daily_controller import DailyController
from models.database import get_connection
from utils.ui_factory import UIFactory
from utils.date_formatter import format_friendly_datetime


class DailyModule:
    """
    Módulo Daily - Gestiona eventos diarios del operador.
    """
    
    # Configuración de columnas
    COLUMNS = ["Fecha Hora", "Sitio", "Actividad", "Cantidad", "Camera", "Descripción"]
    COLUMN_WIDTHS = {
        "Fecha Hora": 150,
        "Sitio": 270,
        "Actividad": 170,
        "Cantidad": 80,
        "Camera": 90,
        "Descripción": 320
    }
    
    def __init__(self, parent, username, session_id, role, UI=None):
        """
        Inicializa el módulo Daily
        
        Args:
            parent: Frame contenedor del módulo
            username: Nombre del usuario
            session_id: ID de sesión activa
            role: Rol del usuario
            UI: Módulo CustomTkinter (opcional)
        """
        self.parent = parent
        self.username = username
        self.session_id = session_id
        self.role = role
        self.UI = UI
        self.ui_factory = UIFactory(UI)
        
        # Referencia al blackboard (se establecerá desde OperatorBlackboard)
        self.blackboard = None
        
        # Componentes UI
        self.container = None
        self.toolbar = None
        self.sheet_frame = None
        self.sheet = None
        
        # Estado
        self.row_data_cache = []
        self.row_ids = []
        self.pending_changes = set()
        
        # Controller
        self.controller = DailyController(username)
        
        # Renderizar
        self.render()
    
    def render(self):
        """Renderiza el módulo completo"""
        self._create_container()
        self._create_toolbar()
        self._create_sheet()
        self._setup_bindings()
        self.load_data()
    
    def _create_container(self):
        """Crea el contenedor principal del módulo"""
        self.container = self.ui_factory.frame(self.parent, fg_color="#1e1e1e")
        self.container.pack(fill="both", expand=True)
    
    def _create_toolbar(self):
        """Crea barra de herramientas con botones"""
        self.toolbar = self.ui_factory.frame(self.container, fg_color="#2c2f33")
        self.toolbar.pack(fill="x", padx=10, pady=(10, 5))
        
        # Botón Refrescar
        self.ui_factory.button(
            self.toolbar,
            text="🔄 Refrescar",
            command=self.load_data,
            width=120,
            fg_color="#4D6068",
            hover_color="#27a3e0"
        ).pack(side="left", padx=5, pady=5)
        
        # Botón Eliminar
        self.ui_factory.button(
            self.toolbar,
            text="🗑️ Eliminar",
            command=self._delete_selected,
            width=120,
            fg_color="#d32f2f",
            hover_color="#b71c1c"
        ).pack(side="left", padx=5, pady=5)
        
        
        
        # Label de estado (derecha)
        self.status_label = self.ui_factory.label(
            self.toolbar,
            text="",
            font=("Segoe UI", 10),
            fg="#00bfae"
        )
        self.status_label.pack(side="right", padx=10)
    
    def _create_sheet(self):
        """Crea y configura el tksheet"""
        # Frame para el sheet
        self.sheet_frame = self.ui_factory.frame(self.container, fg_color="#23272a")
        self.sheet_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Crear tksheet
        self.sheet = Sheet(
            self.sheet_frame,
            headers=self.COLUMNS,
            theme="dark blue",
            height=500,
            width=1000,
            show_selected_cells_border=True,
            show_row_index=True,
            show_top_left=False,
            empty_horizontal=0,
            empty_vertical=0
        )
        
        # Habilitar bindings
        self.sheet.enable_bindings([
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
            "copy",
            "cut",
            "paste",
            "delete",
            "undo",
            "edit_cell"
        ])
        
        self.sheet.pack(fill="both", expand=True)
        self.sheet.change_theme("dark blue")
        
        # Aplicar anchos de columnas
        self._apply_column_widths()
    
    def _apply_column_widths(self):
        """Aplica anchos personalizados a las columnas"""
        for idx, col_name in enumerate(self.COLUMNS):
            if col_name in self.COLUMN_WIDTHS:
                self.sheet.column_width(column=idx, width=self.COLUMN_WIDTHS[col_name])
        self.sheet.redraw()
    
    def _setup_bindings(self):
        """Configura eventos del sheet"""
        # Edición de celda
        self.sheet.bind("<<SheetModified>>", self._on_cell_edit, add=True)
        
        # Deselección de celda
        self.sheet.bind("<<SheetSelect>>", self._on_cell_deselect, add=True)
        
        # Doble click para abrir pickers
        self.sheet.bind("<Double-Button-1>", self._on_double_click, add=True)
        
        # Click derecho para menú contextual
        self.sheet.bind("<Button-3>", self._show_context_menu, add=True)
    
    def load_data(self):
        """Carga datos desde el último START SHIFT"""
        try:
            # Obtener último START SHIFT
            last_shift_time = self._get_last_shift_start()
            if last_shift_time is None:
                data = [["No hay START SHIFT registrado. Inicia un turno primero."] + [""] * (len(self.COLUMNS)-1)]
                self.sheet.set_sheet_data(data)
                self._apply_column_widths()
                self.row_data_cache.clear()
                self.row_ids.clear()
                self.pending_changes.clear()
                self._update_status("Sin turno activo")
                return
            
            # Obtener eventos desde la BD
            conn = get_connection()
            if not conn:
                messagebox.showerror("Error", "No se pudo conectar a la base de datos")
                return
            
            cur = conn.cursor()
            
            # Query para obtener eventos del usuario
            cur.execute("""
                SELECT 
                    e.ID_Eventos,
                    e.FechaHora,
                    e.ID_Sitio,
                    e.Nombre_Actividad,
                    e.Cantidad,
                    e.Camera,
                    e.Descripcion
                FROM Eventos e
                INNER JOIN user u ON e.ID_Usuario = u.ID_Usuario
                WHERE u.Nombre_Usuario = %s AND e.FechaHora >= %s
                ORDER BY e.FechaHora ASC
            """, (self.username, last_shift_time))
            
            eventos = cur.fetchall()
            
            # Procesar eventos
            self.row_data_cache.clear()
            self.row_ids.clear()
            display_rows = []
            
            for evento in eventos:
                id_evento, fecha_hora, id_sitio, nombre_actividad, cantidad, camera, descripcion = evento
                
                # Resolver nombre de sitio
                nombre_sitio = self._get_site_name(cur, id_sitio)
                
                # Formatear fecha/hora de forma amigable
                fecha_str = format_friendly_datetime(fecha_hora, show_seconds=False) if fecha_hora else ""
                
                # Fila para mostrar (formato consistente con Specials)
                display_row = [
                    fecha_str,
                    nombre_sitio,
                    nombre_actividad or "",
                    str(cantidad) if cantidad is not None else "0",
                    camera or "",
                    descripcion or ""
                ]
                
                display_rows.append(display_row)
                
                # Guardar en cache
                self.row_data_cache.append({
                    'id': id_evento,
                    'fecha_hora': fecha_hora,
                    'id_sitio': id_sitio,
                    'nombre_actividad': nombre_actividad,
                    'cantidad': cantidad,
                    'camera': camera,
                    'descripcion': descripcion
                })
                self.row_ids.append(id_evento)
            
            cur.close()
            conn.close()
            
            # Mostrar datos
            if not display_rows:
                display_rows = [["No hay eventos en este turno"] + [""] * (len(self.COLUMNS)-1)]
                self.row_data_cache.clear()
                self.row_ids.clear()
            
            self.sheet.set_sheet_data(display_rows)
            self.sheet.dehighlight_all()
            self._apply_column_widths()
            self.pending_changes.clear()
            
            # Actualizar estado
            self._update_status(f"{len(self.row_ids)} eventos cargados")
            
            print(f"[DEBUG] Loaded {len(self.row_ids)} events for {self.username}")
            
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo cargar eventos:\n{e}")
            print(f"[ERROR] load_data: {e}")
            traceback.print_exc()
    
    def _get_last_shift_start(self):
        """Obtiene la última hora de inicio de shift del usuario"""
        try:
            conn = get_connection()
            if not conn:
                return None
            
            cur = conn.cursor()
            cur.execute("""
                SELECT e.FechaHora 
                FROM Eventos e
                INNER JOIN user u ON e.ID_Usuario = u.ID_Usuario
                WHERE u.Nombre_Usuario = %s AND e.Nombre_Actividad = %s
                ORDER BY e.FechaHora DESC
                LIMIT 1
            """, (self.username, "START SHIFT"))
            
            row = cur.fetchone()
            cur.close()
            conn.close()
            
            return row[0] if row and row[0] else None
        except Exception as e:
            print(f"[ERROR] _get_last_shift_start: {e}")
            return None
    
    def _get_site_name(self, cur, id_sitio):
        """Obtiene el nombre del sitio formateado"""
        if not id_sitio:
            return "Sin sitio"
        
        try:
            cur.execute("SELECT Nombre_Sitio FROM Sitios WHERE ID_Sitio = %s", (id_sitio,))
            row = cur.fetchone()
            if row and row[0]:
                # Formato: "Nombre (ID)" - consistente con Specials
                return f"{row[0]} ({id_sitio})"
            else:
                return f"ID: {id_sitio}"
        except Exception as e:
            print(f"[ERROR] _get_site_name: {e}")
            return f"ID: {id_sitio}"
    
    def _on_cell_edit(self, event):
        """Handler cuando se edita una celda"""
        try:
            selected = self.sheet.get_currently_selected()
            if selected and selected.row is not None:
                row_idx = selected.row
                if row_idx < len(self.row_data_cache):
                    self.pending_changes.add(row_idx)
                    print(f"[DEBUG] Cell edited - row {row_idx} marked for save")
                    # Auto-save después de un breve delay
                    self.parent.after(500, self._auto_save_pending)
        except Exception as e:
            print(f"[DEBUG] _on_cell_edit error: {e}")
    
    def _on_cell_deselect(self, event):
        """Handler cuando se deselecciona una celda"""
        try:
            selected = self.sheet.get_currently_selected()
            if selected and selected.row is not None and selected.row < len(self.row_data_cache):
                self.pending_changes.add(selected.row)
        except Exception as e:
            print(f"[DEBUG] _on_cell_deselect error: {e}")
    
    def _on_double_click(self, event):
        """Handler de doble click en celdas"""
        from datetime import datetime
        
        try:
            # Obtener celda seleccionada
            selection = self.sheet.get_currently_selected()
            if not selection:
                return
            
            row = selection.row if hasattr(selection, 'row') else selection[0]
            col = selection.column if hasattr(selection, 'column') else selection[1]
            
            # Columna 0: Fecha Hora
            if col == 0:
                self._show_datetime_picker_for_cell(row, col)
            
            # Columna 1: Sitio
            elif col == 1:
                self._show_site_picker(row)
            
            # Columna 2: Actividad
            elif col == 2:
                self._show_activity_picker(row)
        
        except Exception as e:
            print(f"[ERROR] Error en doble click: {e}")
    
    def _show_datetime_picker_for_cell(self, row, col):
        """Muestra datetime picker para la celda especificada"""
        from datetime import datetime
        
        # Obtener valor actual
        current_value = self.sheet.get_cell_data(row, col)
        
        # Parsear fecha actual o usar now()
        try:
            initial_dt = datetime.strptime(current_value, "%Y-%m-%d %H:%M:%S")
        except:
            initial_dt = datetime.now()
        
        # Usar referencia directa al blackboard
        if self.blackboard and hasattr(self.blackboard, '_show_datetime_picker'):
            # Callback para actualizar la celda
            def update_cell(dt):
                self.sheet.set_cell_data(row, col, format_friendly_datetime(dt, show_seconds=False))
                self.sheet.redraw()
                # Marcar cambio pendiente
                if row < len(self.row_ids):
                    self.pending_changes.add(row)
                    # Guardar después del cambio
                    self.parent.after(500, self._auto_save_pending)
            
            self.blackboard._show_datetime_picker(
                callback=update_cell,
                initial_datetime=initial_dt
            )
        else:
            print("[DEBUG] No se encontró blackboard con _show_datetime_picker")
    
    def _show_site_picker(self, row):
        """Muestra picker de sitios para la celda especificada"""
        import tkinter as tk
        from tkinter import messagebox
        
        if not self.blackboard or not hasattr(self.blackboard, 'controller'):
            messagebox.showerror("Error", "No se puede acceder a los datos de sitios")
            return
        
        # Obtener sitios del controller
        sites = self.blackboard.controller.get_sites()
        site_options = [f"{row[1]} ({row[0]})" for row in sites]
        
        # Crear ventana modal
        if self.UI is not None:
            picker_win = self.UI.CTkToplevel(self.container)
            picker_win.title("Seleccionar Sitio")
            picker_win.geometry("500x250")
            picker_win.transient(self.container)
            picker_win.grab_set()
            
            # Header
            header = self.UI.CTkFrame(picker_win, fg_color="#1a1a1a", corner_radius=0, height=60)
            header.pack(fill="x")
            header.pack_propagate(False)
            
            self.UI.CTkLabel(
                header,
                text="🏢 Seleccionar Sitio",
                font=("Segoe UI", 20, "bold"),
                text_color="#4a90e2"
            ).pack(pady=15)
            
            # Contenido
            content = self.UI.CTkFrame(picker_win, fg_color="transparent")
            content.pack(fill="both", expand=True, padx=20, pady=20)
            
            self.UI.CTkLabel(
                content,
                text="Buscar y seleccionar un sitio:",
                font=("Segoe UI", 12),
                text_color="#e0e0e0"
            ).pack(anchor="w", pady=(0, 10))
            
            # FilteredCombobox
            from under_super import FilteredCombobox
            combo_var = tk.StringVar()
            combo = FilteredCombobox(
                content,
                textvariable=combo_var,
                values=site_options,
                font=("Segoe UI", 11),
                width=50,
                background='#2b2b2b',
                foreground='#ffffff',
                fieldbackground='#2b2b2b',
                bordercolor='#5ab4ff',
                arrowcolor='#ffffff',
                borderwidth=3
            )
            combo.pack(fill="x", pady=(0, 20))
            combo.focus_set()
            
            # Botones
            btn_frame = self.UI.CTkFrame(content, fg_color="transparent")
            btn_frame.pack(pady=10)
            
            def accept():
                selected = combo_var.get().strip()
                if selected:
                    self.sheet.set_cell_data(row, 1, selected)
                    self.sheet.redraw()
                    self.pending_changes.add(row)
                    picker_win.destroy()
                    # Guardar después del cambio
                    self.parent.after(500, self._auto_save_pending)
                else:
                    messagebox.showwarning("Advertencia", "Selecciona un sitio", parent=picker_win)
            
            self.UI.CTkButton(
                btn_frame,
                text="✅ Aceptar",
                command=accept,
                fg_color="#00c853",
                hover_color="#00a043",
                font=("Segoe UI", 12, "bold"),
                width=120,
                height=40
            ).pack(side="left", padx=10)
            
            self.UI.CTkButton(
                btn_frame,
                text="❌ Cancelar",
                command=picker_win.destroy,
                fg_color="#666666",
                hover_color="#555555",
                font=("Segoe UI", 12),
                width=120,
                height=40
            ).pack(side="left", padx=10)
        else:
            # Fallback sin CustomTkinter
            picker_win = tk.Toplevel(self.container)
            picker_win.title("Seleccionar Sitio")
            picker_win.geometry("450x200")
            picker_win.configure(bg="#2c2f33")
            picker_win.transient(self.container)
            picker_win.grab_set()
            
            tk.Label(
                picker_win,
                text="🏢 Seleccionar Sitio",
                bg="#2c2f33",
                fg="#4a90e2",
                font=("Segoe UI", 16, "bold")
            ).pack(pady=15)
            
            from under_super import FilteredCombobox
            combo_var = tk.StringVar()
            combo = FilteredCombobox(
                picker_win,
                textvariable=combo_var,
                values=site_options,
                font=("Segoe UI", 10),
                width=50
            )
            combo.pack(pady=10, fill="x", padx=20)
            combo.focus_set()
            
            def accept():
                selected = combo_var.get().strip()
                if selected:
                    self.sheet.set_cell_data(row, 1, selected)
                    self.sheet.redraw()
                    self.pending_changes.add(row)
                    picker_win.destroy()
                    # Guardar después del cambio
                    self.parent.after(500, self._auto_save_pending)
                else:
                    messagebox.showwarning("Advertencia", "Selecciona un sitio", parent=picker_win)
            
            btn_frame = tk.Frame(picker_win, bg="#2c2f33")
            btn_frame.pack(pady=15)
            
            tk.Button(
                btn_frame,
                text="✅ Aceptar",
                command=accept,
                bg="#00c853",
                fg="white",
                width=12
            ).pack(side="left", padx=10)
            
            tk.Button(
                btn_frame,
                text="❌ Cancelar",
                command=picker_win.destroy,
                bg="#666666",
                fg="white",
                width=12
            ).pack(side="left", padx=10)
    
    def _show_activity_picker(self, row):
        """Muestra picker de actividades para la celda especificada"""
        import tkinter as tk
        from tkinter import messagebox
        
        if not self.blackboard or not hasattr(self.blackboard, 'controller'):
            messagebox.showerror("Error", "No se puede acceder a los datos de actividades")
            return
        
        # Obtener actividades del controller
        activities = self.blackboard.controller.get_activities()
        activity_options = [row[0] for row in activities]
        
        # Crear ventana modal
        if self.UI is not None:
            picker_win = self.UI.CTkToplevel(self.container)
            picker_win.title("Seleccionar Actividad")
            picker_win.geometry("500x250")
            picker_win.transient(self.container)
            picker_win.grab_set()
            
            # Header
            header = self.UI.CTkFrame(picker_win, fg_color="#1a1a1a", corner_radius=0, height=60)
            header.pack(fill="x")
            header.pack_propagate(False)
            
            self.UI.CTkLabel(
                header,
                text="📋 Seleccionar Actividad",
                font=("Segoe UI", 20, "bold"),
                text_color="#4a90e2"
            ).pack(pady=15)
            
            # Contenido
            content = self.UI.CTkFrame(picker_win, fg_color="transparent")
            content.pack(fill="both", expand=True, padx=20, pady=20)
            
            self.UI.CTkLabel(
                content,
                text="Buscar y seleccionar una actividad:",
                font=("Segoe UI", 12),
                text_color="#e0e0e0"
            ).pack(anchor="w", pady=(0, 10))
            
            # FilteredCombobox
            from under_super import FilteredCombobox
            combo_var = tk.StringVar()
            combo = FilteredCombobox(
                content,
                textvariable=combo_var,
                values=activity_options,
                font=("Segoe UI", 11),
                width=50,
                background='#2b2b2b',
                foreground='#ffffff',
                fieldbackground='#2b2b2b',
                bordercolor='#5ab4ff',
                arrowcolor='#ffffff',
                borderwidth=3
            )
            combo.pack(fill="x", pady=(0, 20))
            combo.focus_set()
            
            # Botones
            btn_frame = self.UI.CTkFrame(content, fg_color="transparent")
            btn_frame.pack(pady=10)
            
            def accept():
                selected = combo_var.get().strip()
                if selected:
                    self.sheet.set_cell_data(row, 2, selected)
                    self.sheet.redraw()
                    self.pending_changes.add(row)
                    picker_win.destroy()
                    # Guardar después del cambio
                    self.parent.after(500, self._auto_save_pending)
                else:
                    messagebox.showwarning("Advertencia", "Selecciona una actividad", parent=picker_win)
            
            self.UI.CTkButton(
                btn_frame,
                text="✅ Aceptar",
                command=accept,
                fg_color="#00c853",
                hover_color="#00a043",
                font=("Segoe UI", 12, "bold"),
                width=120,
                height=40
            ).pack(side="left", padx=10)
            
            self.UI.CTkButton(
                btn_frame,
                text="❌ Cancelar",
                command=picker_win.destroy,
                fg_color="#666666",
                hover_color="#555555",
                font=("Segoe UI", 12),
                width=120,
                height=40
            ).pack(side="left", padx=10)
        else:
            # Fallback sin CustomTkinter
            picker_win = tk.Toplevel(self.container)
            picker_win.title("Seleccionar Actividad")
            picker_win.geometry("450x200")
            picker_win.configure(bg="#2c2f33")
            picker_win.transient(self.container)
            picker_win.grab_set()
            
            tk.Label(
                picker_win,
                text="📋 Seleccionar Actividad",
                bg="#2c2f33",
                fg="#4a90e2",
                font=("Segoe UI", 16, "bold")
            ).pack(pady=15)
            
            from under_super import FilteredCombobox
            combo_var = tk.StringVar()
            combo = FilteredCombobox(
                picker_win,
                textvariable=combo_var,
                values=activity_options,
                font=("Segoe UI", 10),
                width=50
            )
            combo.pack(pady=10, fill="x", padx=20)
            combo.focus_set()
            
            def accept():
                selected = combo_var.get().strip()
                if selected:
                    self.sheet.set_cell_data(row, 2, selected)
                    self.sheet.redraw()
                    self.pending_changes.add(row)
                    picker_win.destroy()
                    # Guardar después del cambio
                    self.parent.after(500, self._auto_save_pending)
                else:
                    messagebox.showwarning("Advertencia", "Selecciona una actividad", parent=picker_win)
            
            btn_frame = tk.Frame(picker_win, bg="#2c2f33")
            btn_frame.pack(pady=15)
            
            tk.Button(
                btn_frame,
                text="✅ Aceptar",
                command=accept,
                bg="#00c853",
                fg="white",
                width=12
            ).pack(side="left", padx=10)
            
            tk.Button(
                btn_frame,
                text="❌ Cancelar",
                command=picker_win.destroy,
                bg="#666666",
                fg="white",
                width=12
            ).pack(side="left", padx=10)
    
    def _show_context_menu(self, event):
        """Muestra menú contextual con opciones de edición"""
        import tkinter as tk
        
        try:
            # Obtener celda seleccionada
            selection = self.sheet.get_currently_selected()
            if not selection:
                return
            
            row = selection.row if hasattr(selection, 'row') else selection[0]
            
            # Crear menú contextual
            context_menu = tk.Menu(
                self.container,
                tearoff=0,
                bg="#2c2f33",
                fg="#e0e0e0",
                activebackground="#4a90e2",
                activeforeground="#ffffff",
                font=("Segoe UI", 10)
            )
            
            # Opciones de edición rápida
            context_menu.add_command(
                label="⌚ Seleccionar Fecha/Hora",
                command=lambda: self._show_datetime_picker_for_cell(row, 0)
            )
            context_menu.add_command(
                label="🏢 Seleccionar Sitio",
                command=lambda: self._show_site_picker(row)
            )
            context_menu.add_command(
                label="📋 Seleccionar Actividad",
                command=lambda: self._show_activity_picker(row)
            )
            context_menu.add_separator()
            context_menu.add_command(
                label="🗑️ Eliminar Fila",
                command=lambda: self._delete_row(row)
            )
            
            try:
                context_menu.tk_popup(event.x_root, event.y_root)
            finally:
                context_menu.grab_release()
        
        except Exception as e:
            print(f"[ERROR] Error mostrando menú contextual: {e}")
    
    def _delete_row(self, row):
        """Elimina una fila del sheet y la base de datos"""
        from tkinter import messagebox
        
        if row >= len(self.row_ids):
            return
        
        if not messagebox.askyesno(
            "Confirmar eliminación",
            "¿Estás seguro de eliminar este evento?",
            parent=self.container
        ):
            return
        
        try:
            event_id = self.row_ids[row]
            
            # Eliminar de la base de datos
            conn = get_connection()
            if conn:
                cur = conn.cursor()
                cur.execute("DELETE FROM Eventos WHERE ID_Eventos = %s", (event_id,))
                conn.commit()
                cur.close()
                conn.close()
            
            # Recargar datos
            self.load_data()
            
            print(f"[DEBUG] Evento {event_id} eliminado")
        
        except Exception as e:
            messagebox.showerror(
                "Error",
                f"No se pudo eliminar el evento:\n{e}",
                parent=self.container
            )
            print(f"[ERROR] Error eliminando evento: {e}")
    
    def _auto_save_pending(self):
        """Guarda automáticamente los cambios pendientes"""
        if not self.pending_changes:
            return
        
        try:
            conn = get_connection()
            if not conn:
                return
            
            cur = conn.cursor()
            
            # Obtener ID_Usuario
            cur.execute("SELECT ID_Usuario FROM user WHERE Nombre_Usuario=%s", (self.username,))
            user_row = cur.fetchone()
            if not user_row:
                cur.close()
                conn.close()
                return
            
            user_id = int(user_row[0])
            
            for idx in list(self.pending_changes):
                try:
                    if idx >= len(self.row_data_cache):
                        continue
                    
                    cached = self.row_data_cache[idx]
                    event_id = cached.get('id')
                    
                    if not event_id:
                        continue
                    
                    # Obtener valores actuales del sheet
                    row_data = self.sheet.get_row_data(idx)
                    
                    # Extraer valores (índices según COLUMNS)
                    # ["Fecha Hora", "Sitio", "Actividad", "Cantidad", "Camera", "Descripción"]
                    fecha_str = row_data[0] if len(row_data) > 0 else None
                    sitio_str = row_data[1] if len(row_data) > 1 else None
                    actividad = row_data[2] if len(row_data) > 2 else None
                    cantidad = row_data[3] if len(row_data) > 3 else None
                    camera = row_data[4] if len(row_data) > 4 else None
                    descripcion = row_data[5] if len(row_data) > 5 else None
                    
                    # Parsear fecha
                    fecha_hora = None
                    if fecha_str:
                        try:
                            fecha_hora = datetime.strptime(fecha_str, "%Y-%m-%d %H:%M:%S")
                        except:
                            fecha_hora = cached.get('fecha_hora')
                    
                    # Extraer ID_Sitio de formato "Nombre (ID)"
                    id_sitio = None
                    if sitio_str:
                        try:
                            if '(' in sitio_str and ')' in sitio_str:
                                id_sitio = int(sitio_str.split('(')[1].split(')')[0])
                            else:
                                id_sitio = cached.get('id_sitio')
                        except:
                            id_sitio = cached.get('id_sitio')
                    
                    # UPDATE en BD
                    cur.execute("""
                        UPDATE Eventos
                        SET FechaHora = %s,
                            ID_Sitio = %s,
                            Nombre_Actividad = %s,
                            Cantidad = %s,
                            Camera = %s,
                            Descripcion = %s
                        WHERE ID_Eventos = %s
                    """, (fecha_hora, id_sitio, actividad, cantidad, camera, descripcion, event_id))
                    
                    print(f"[DEBUG] Auto-saved event ID={event_id}")
                    
                except Exception as e:
                    print(f"[ERROR] Auto-save row {idx}: {e}")
            
            conn.commit()
            cur.close()
            conn.close()
            
            self.pending_changes.clear()
            self._update_status("Cambios guardados automáticamente")
            
        except Exception as e:
            print(f"[ERROR] _auto_save_pending: {e}")
    
    def _delete_selected(self):
        """Elimina el evento seleccionado"""
        selected = self.sheet.get_currently_selected()
        if not selected or selected.row is None:
            messagebox.showwarning("Advertencia", "No hay fila seleccionada")
            return
        
        row_idx = selected.row
        
        if row_idx >= len(self.row_data_cache):
            messagebox.showwarning("Advertencia", "Índice de fila inválido")
            return
        
        cached_data = self.row_data_cache[row_idx]
        event_id = cached_data.get('id')
        
        if not event_id:
            messagebox.showwarning("Advertencia", "No se puede eliminar fila sin ID")
            return
        
        # Confirmación
        actividad = cached_data.get('nombre_actividad', '')
        if not messagebox.askyesno("Confirmar Eliminación", 
                                    f"¿Eliminar evento '{actividad}'?\n\n"
                                    "Será movido a la papelera."):
            return
        
        # Pedir razón
        reason = simpledialog.askstring("Razón de Eliminación", 
                                        "Ingresa la razón de eliminación:")
        if not reason:
            reason = "Eliminación manual desde Daily Module"
        
        try:
            # Usar safe_delete (si existe) o DELETE directo
            from backend_super import safe_delete
            safe_delete("Eventos", "ID_Eventos", event_id, self.username, reason)
            
            # Recargar datos
            self.load_data()
            self._update_status(f"Evento eliminado: {actividad}")
            
        except ImportError:
            # Fallback: DELETE directo
            try:
                conn = get_connection()
                cur = conn.cursor()
                cur.execute("DELETE FROM Eventos WHERE ID_Eventos = %s", (event_id,))
                conn.commit()
                cur.close()
                conn.close()
                
                self.load_data()
                self._update_status(f"Evento eliminado: {actividad}")
                
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo eliminar:\n{e}")
                print(f"[ERROR] _delete_selected: {e}")
        
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo eliminar:\n{e}")
            print(f"[ERROR] _delete_selected: {e}")
    
    def _update_status(self, message):
        """Actualiza el label de estado"""
        if hasattr(self, 'status_label') and self.status_label:
            if self.UI:
                self.status_label.configure(text=message)
            else:
                self.status_label.configure(text=message)
