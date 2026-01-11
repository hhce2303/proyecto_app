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
import tkcalendar
from tksheet import Sheet
import traceback
from datetime import datetime
import backend_super
from under_super import FilteredCombobox
from controllers.daily_controller import DailyController
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
        self.window = parent  # Asegura que self.window esté definido para diálogos y pickers
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
        self._create_event_form()
    
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
        
        # Habilitar bindings (solo navegación, selección y undo)
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
            "undo",  # Solo mantener UNDO (Ctrl+Z)
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
        """Carga datos desde el controlador y los muestra en el sheet"""
        try:
            eventos = self.controller.load_daily()
            
            # Procesar datos para el sheet
            display_rows = []
            self.row_data_cache = []
            self.row_ids = []
            
            for evento in eventos:
                (
                    id_evento,
                    fecha_hora,
                    sitio_concatenado,
                    nombre_actividad,
                    cantidad,
                    camera,
                    descripcion,
                    id_usuario
                ) = evento

                # Formatear fecha/hora
                fecha_str = format_friendly_datetime(fecha_hora)

                # El sitio ya viene concatenado como "ID - Nombre"
                sitio_str = sitio_concatenado

                row = [
                    fecha_str,
                    sitio_str,
                    nombre_actividad,
                    cantidad,
                    camera,
                    descripcion
                ]

                display_rows.append(row)

                # Cachear datos completos para edición futura
                self.row_data_cache.append({
                    'id': id_evento,
                    'fecha_hora': fecha_hora,
                    'sitio': sitio_concatenado,
                    'nombre_actividad': nombre_actividad,
                    'cantidad': cantidad,
                    'camera': camera,
                    'descripcion': descripcion,
                    'id_usuario': id_usuario
                })

                self.row_ids.append(id_evento)
            
            # Cargar datos en el sheet
            self.sheet.set_sheet_data(display_rows, reset_highlights=True)
            self._apply_column_widths()
            self._update_status(f"{len(display_rows)} eventos cargados")
        
        except Exception as e:
            traceback.print_exc()
            messagebox.showerror("Error", f"No se pudieron cargar los datos:\n{e}")
            print(f"[ERROR] load_data: {e}")

    def _create_event_form(self):
        """Crea el formulario horizontal alineado con columnas del tksheet"""
        # Contenedor interno para alineación
        inner_frame = tk.Frame(self.container, bg="#2b2b2b")
        inner_frame.pack(fill="x", padx=(0, 10), pady=5)
        
        # Botón Agregar (lado izquierdo, como row index)
        self.add_event_btn = self.ui_factory.button(
            inner_frame,
            text="➕",
            command=self._add_event,
            width=30,
            fg_color="#4CAF50",
            hover_color="#45a049"
        )
        self.add_event_btn.pack(side="left", padx=(2, 12))

        # Campo Fecha/Hora - ancho 150px
        datetime_container = tk.Frame(inner_frame, bg="#2b2b2b")
        datetime_container.pack(side="left", padx=(0, 10))
        
        tk.Label(
            datetime_container,
            text="Fecha/Hora:",
            font=("Segoe UI", 9),
            fg="#ffffff",
            bg="#2b2b2b",
            justify="center"
        ).pack(side="top")
        
        # Frame para entry con botón integrado
        entry_wrapper = tk.Frame(datetime_container, bg="#2b2b2b", highlightthickness=0)
        entry_wrapper.pack(side="top")
        
        # Usar CTkEntry de customtkinter para borde y colores personalizados

        self.datetime_entry = self.ui_factory.entry(
            entry_wrapper,
            width=120,  # Ajustar ancho visual
            font=("Segoe UI", 10),
            fg_color="#333333",
            text_color="#ffffff",
            border_width=3,
            border_color="#4a90e2"
        )
        self.datetime_entry.pack(side="left", padx=(3, 0), pady=2)
        
        # Botón dentro del entry (lado derecho)
        datetime_btn = self.ui_factory.button(
            entry_wrapper,
            text="📅",
            command=lambda: self._show_datetime_picker_for_cell(
                None, None, callback=lambda dt: self._set_datetime_value(dt)
            ),
            width=25,
            height=22,
            fg_color="#4a90e2",
            hover_color="#3a7bc2"
        )
        datetime_btn.pack(side="left", padx=(2, 2), pady=2)
        
        # Campo Sitio
        site_container = tk.Frame(inner_frame, bg="#2b2b2b")
        site_container.pack(side="left", padx=0)
        
        tk.Label(
            site_container,
            text="Sitio:",
            font=("Segoe UI", 9),
            fg="#ffffff",
            bg="#2b2b2b",
            justify="center"
        ).pack(side="top")
        
        self.site_combo = FilteredCombobox(
            site_container,
            width=36,
            height=5,
            values=self._get_sites()
        )
        self.site_combo.pack(side="top")
        
        # Campo Actividad
        activity_container = tk.Frame(inner_frame, bg="#2b2b2b")
        activity_container.pack(side="left", padx=3)
        
        tk.Label(
            activity_container,
            text="Actividad:",
            font=("Segoe UI", 9),
            fg="#ffffff",
            bg="#2b2b2b",
            justify="center"
        ).pack(side="top")
        
        self.activity_combo = FilteredCombobox(
            activity_container,
            width=25,
            values=self._get_activities()
        )
        self.activity_combo.pack(side="top")
        
        # Campo Cantidad
        quantity_container = tk.Frame(inner_frame, bg="#2b2b2b")
        quantity_container.pack(side="left", padx=3)
        
        tk.Label(
            quantity_container,
            text="Cantidad:",
            font=("Segoe UI", 9),
            fg="#ffffff",
            bg="#2b2b2b",
            justify="center"
        ).pack(side="top")
        
        self.quantity_entry = self.ui_factory.entry(
            quantity_container,
            width=60,
            font=("Segoe UI", 10),
            fg_color="#333333",
            text_color="#ffffff",
            border_width=3,
            border_color="#4a90e2",
            justify="center"
        )
        self.quantity_entry.insert(0, "0")
        self.quantity_entry.pack(side="top")
        
        # Campo Camera
        camera_container = tk.Frame(inner_frame, bg="#2b2b2b")
        camera_container.pack(side="left", padx=3)
        
        tk.Label(
            camera_container,
            text="Camera:",
            font=("Segoe UI", 9),
            fg="#ffffff",
            bg="#2b2b2b",
            justify="center"
        ).pack(side="top")
        
        self.camera_entry = self.ui_factory.entry(
            camera_container,
            width=80,
            font=("Segoe UI", 10),
            fg_color="#333333",
            text_color="#ffffff",
            border_width=3,
            border_color="#4a90e2",
            justify="center"
        )
        self.camera_entry.pack(side="top")
        
        # Campo Descripción
        description_container = tk.Frame(inner_frame, bg="#2b2b2b")
        description_container.pack(side="left", padx=3)
        
        tk.Label(
            description_container,
            text="Descripción:",
            font=("Segoe UI", 9),
            fg="#ffffff",
            bg="#2b2b2b",
            justify="center"
        ).pack(side="top")
        
        self.description_entry = self.ui_factory.entry(
            description_container,
            width=290,
            font=("Segoe UI", 10),
            fg_color="#333333",
            text_color="#ffffff",
            border_width=3,
            border_color="#4a90e2"
        )
        self.description_entry.pack(side="top")
        
        # Vincular Enter en todos los campos para ejecutar _add_event
        self._bind_enter_to_submit()
        
        # Focus inicial en Sitio
        self.site_combo.focus_set()
    
    def _bind_enter_to_submit(self):
        """Vincula la tecla Enter a todos los campos del formulario"""
        fields = [
            self.datetime_entry,
            self.site_combo,
            self.activity_combo,
            self.quantity_entry,
            self.camera_entry,
            self.description_entry
        ]
        
        for field in fields:
            field.bind("<Return>", self._on_form_enter)
            field.bind("<KP_Enter>", self._on_form_enter)
    
    def _on_form_enter(self, event):
        """Handler para la tecla Enter en el formulario"""
        self._add_event()
        return "break"
    
    def _get_sites(self):
        """Obtiene lista de sitios a través del controller (MVC)"""
        sites = self.controller.get_sites()
        return [f"{row[1]} ({row[0]})" for row in sites]
    
    def _get_activities(self):
        """Obtiene lista de actividades a través del controller (MVC)"""
        activities = self.controller.get_activities()
        return [row[0] for row in activities]
    
    def _add_event(self):
        """Agrega un nuevo evento usando arquitectura MVC"""
        from tkinter import messagebox
        
        # ⭐ VALIDAR QUE HAY TURNO ACTIVO
        if not backend_super.has_active_shift(self.username):
            messagebox.showwarning(
                "Sin Turno Activo",
                "⚠️ Debes iniciar tu turno antes de registrar eventos.\n\n"
                "Haz clic en el botón '🚀 Start Shift' en la esquina superior derecha.",
                parent=self.window
            )
            return
        
        # Obtener valores del formulario
        site_text = self.site_combo.get()
        activity = self.activity_combo.get()
        quantity = self.quantity_entry.get()
        camera = self.camera_entry.get()
        description = self.description_entry.get()
        
        # Validar campos obligatorios
        if not site_text or not activity:
            messagebox.showwarning(
                "Campos requeridos",
                "Sitio y Actividad son obligatorios",
                parent=self.window
            )
            return
        
        # Extraer ID del sitio
        try:
            site_id = int(site_text.split("(")[-1].split(")")[0])
        except:
            messagebox.showerror("Error", "Formato de sitio inválido", parent=self.window)
            return
        
        # Validar cantidad
        try:
            quantity_val = int(quantity) if quantity else 0
        except:
            messagebox.showerror("Error", "Cantidad debe ser un número", parent=self.window)
            return
        
        # Obtener fecha/hora del datetime_entry
        fecha_hora_str = self.datetime_entry.get().strip()
        fecha_hora = None
        if fecha_hora_str:
            try:
                from datetime import datetime
                fecha_hora = datetime.strptime(fecha_hora_str, "%Y-%m-%d %H:%M:%S")
            except Exception as e:
                print(f"[WARNING] No se pudo parsear fecha del formulario: {fecha_hora_str}, usando datetime.now(). Error: {e}")
                fecha_hora = None
        
        # Llamar al controller para crear evento (MVC)
        success, message = self.controller.create_event(
            site_id,
            activity,
            quantity_val,
            camera,
            description,
            fecha_hora  # Pasar fecha/hora desde el formulario
        )
        
        if success:
            # Limpiar campos
            self.site_combo.set("")
            self.activity_combo.set("")
            self.quantity_entry.delete(0, "end")
            self.quantity_entry.insert(0, "0")
            self.camera_entry.delete(0, "end")
            self.description_entry.delete(0, "end")
            # Limpiar campo de fecha/hora
            self.datetime_entry.configure(state="normal")
            self.datetime_entry.delete(0, "end")
            self.datetime_entry.configure(state="readonly")
            self.load_data()
            print(f"[DEBUG] {message}")
        else:
            messagebox.showerror(
                "Error",
                f"No se pudo agregar el evento: Recuerda no agregar numeros en el campo de actividad.",
                parent=self.window
            )
    
    def _set_datetime_value(self, dt):
        """Actualiza el entry de fecha/hora con el datetime seleccionado"""
        self.datetime_entry.configure(state="normal")
        self.datetime_entry.delete(0, "end")
        self.datetime_entry.insert(0, dt.strftime("%Y-%m-%d %H:%M:%S"))
        self.datetime_entry.configure(state="readonly")
    
    def _on_cell_edit(self, event):
        """Handler cuando se edita una celda"""
        try:
            self.auto_save_pending_changes()
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
                # El picker ya espera y devuelve el string en formato 'ID - Nombre'
                self._show_site_picker(row)

            # Columna 2: Actividad
            elif col == 2:
                self._show_activity_picker(row)

        except Exception as e:
            print(f"[ERROR] Error en doble click: {e}")

    
    def _show_datetime_picker_for_cell(self, row, col, initial_datetime=None, callback=None):
        """
        Muestra un selector de fecha/hora moderno y reutilizable.
        
        Args:
            row: Fila de la celda
            col: Columna de la celda
            initial_datetime: datetime inicial (por defecto datetime.now())
            callback: función a llamar con el datetime seleccionado
        """
        
        # Fecha/hora inicial
        now = initial_datetime if initial_datetime else datetime.now()
        
        # Crear ventana modal

        picker_win = self.ui_factory.toplevel(self.window)
        picker_win.title("Seleccionar Fecha y Hora")
        picker_win.geometry("500x450")
        picker_win.resizable(False, False)
        picker_win.transient(self.window)
        picker_win.grab_set()
            
        # Header
        header = self.ui_factory.frame(picker_win, fg_color="#1a1a1a", corner_radius=0, height=60)
        header.pack(fill="x", padx=0, pady=0)
        header.pack_propagate(False)
            
        self.ui_factory.label(
            header, 
            text="📅 Seleccionar Fecha y Hora",
            font=("Segoe UI", 20, "bold"),
            text_color="#4a90e2"
        ).pack(pady=15)
            
        # Contenido principal
        content = self.ui_factory.frame(picker_win, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=20, pady=20)
            
        # Sección de Fecha
        date_section = self.ui_factory.frame(content, fg_color="#2b2b2b", corner_radius=10)
        date_section.pack(fill="x", pady=(0, 15))
            
        self.ui_factory.label(
            date_section,
            text="📅 Fecha:",
                font=("Segoe UI", 14, "bold"),
                text_color="#e0e0e0"
            ).pack(anchor="w", padx=15, pady=(15, 10))
            
        # Calendario
        cal_wrapper = tk.Frame(date_section, bg="#2b2b2b")
        cal_wrapper.pack(padx=15, pady=(0, 15))
            
        cal = tkcalendar.DateEntry(
            cal_wrapper,
            width=30,
            background='#4a90e2',
            foreground='white',
            borderwidth=2,
            year=now.year,
            month=now.month,
            day=now.day,
            date_pattern='yyyy-mm-dd',
            font=("Segoe UI", 11)
        )
        cal.pack()
            
        # Sección de Hora
        time_section = self.ui_factory.frame(content, fg_color="#2b2b2b", corner_radius=10)
        time_section.pack(fill="x", pady=(0, 15))
        
        self.ui_factory.label(
            time_section,
            text="🕐 Hora:",
            font=("Segoe UI", 14, "bold"),
            text_color="#e0e0e0"
        ).pack(anchor="w", padx=15, pady=(15, 10))
            
        # Variables para hora
        hour_var = tk.IntVar(value=now.hour)
        minute_var = tk.IntVar(value=now.minute)
        second_var = tk.IntVar(value=now.second)
        
        # Frame para spinboxes
        spinbox_container = tk.Frame(time_section, bg="#2b2b2b")
        spinbox_container.pack(padx=15, pady=(0, 10))
            
        # Hora
        tk.Label(
            spinbox_container,
            text="Hora:",
            bg="#2b2b2b",
            fg="#a3c9f9",
            font=("Segoe UI", 11)
        ).grid(row=0, column=0, padx=5, pady=5)
        
        hour_spin = tk.Spinbox(
            spinbox_container,
            from_=0,
            to=23,
            textvariable=hour_var,
            width=8,
            font=("Segoe UI", 12),
            justify="center"
        )
        hour_spin.grid(row=0, column=1, padx=5, pady=5)
        
        # Minuto
        tk.Label(
            spinbox_container,
            text="Min:",
            bg="#2b2b2b",
            fg="#a3c9f9",
            font=("Segoe UI", 11)
        ).grid(row=0, column=2, padx=5, pady=5)
        
        minute_spin = tk.Spinbox(
            spinbox_container,
            from_=0,
            to=59,
            textvariable=minute_var,
            width=8,
            font=("Segoe UI", 12),
            justify="center"
        )
        minute_spin.grid(row=0, column=3, padx=5, pady=5)
        
        # Segundo
        tk.Label(
            spinbox_container,
            text="Seg:",
            bg="#2b2b2b",
            fg="#a3c9f9",
            font=("Segoe UI", 11)
        ).grid(row=0, column=4, padx=5, pady=5)
        
        second_spin = tk.Spinbox(
            spinbox_container,
            from_=0,
            to=59,
            textvariable=second_var,
            width=8,
            font=("Segoe UI", 12),
            justify="center"
        )
        second_spin.grid(row=0, column=5, padx=5, pady=5)
            
        # Botón "Ahora"
        def set_now():
            current = datetime.now()
            cal.set_date(current.date())
            hour_var.set(current.hour)
            minute_var.set(current.minute)
            second_var.set(current.second)
        
        self.ui_factory.button(
            time_section,
            text="⏰ Establecer Hora Actual",
            command=set_now,
            fg_color="#4a90e2",
            hover_color="#3a7bc2",
            font=("Segoe UI", 11),
            width=200,
            height=35
        ).pack(pady=(5, 15))
        
        # Botones Aceptar/Cancelar
        btn_frame = self.ui_factory.frame(content, fg_color="transparent")
        btn_frame.pack(pady=10)
        
        def accept():
            try:
                selected_date = cal.get_date()
                selected_time = datetime.strptime(
                    f"{selected_date} {hour_var.get():02d}:{minute_var.get():02d}:{second_var.get():02d}",
                    "%Y-%m-%d %H:%M:%S"
                )
                picker_win.destroy()
                if row is not None and col is not None and row < len(self.row_data_cache):
                    # Actualizar la celda de fecha/hora en el sheet con el formato correcto
                    fecha_str = selected_time.strftime("%Y-%m-%d %H:%M:%S")
                    self.sheet.set_cell_data(row, 0, fecha_str)
                    self.sheet.redraw()
                    row_data = self.sheet.get_row_data(row)
                    id_evento = self.row_data_cache[row]['id']
                    evento = (
                        id_evento,
                        fecha_str,  # fecha_hora en formato correcto
                        row_data[1],  # sitio_concatenado
                        row_data[2],  # nombre_actividad
                        row_data[3],  # cantidad
                        row_data[4],  # camera
                        row_data[5],  # descripcion
                    )
                    self.auto_save_pending_changes(evento)
                else:
                    self.auto_save_pending_changes(None)
                 # Llamar al callback si se proporcionó
                 

                if callback:
                    callback(selected_time)

            except Exception as e:
                messagebox.showerror(
                    "Error",
                    f"Error al establecer fecha/hora:\n{e}",
                    parent=picker_win
                )
            
        self.ui_factory.button(
            btn_frame,
            text="✅ Aceptar",
            command=accept,
            fg_color="#00c853",
            hover_color="#00a043",
            font=("Segoe UI", 12, "bold"),
            width=120,
            height=40
        ).pack(side="left", padx=10)
            
        self.ui_factory.button(
            btn_frame,
            text="❌ Cancelar",
            command=picker_win.destroy,
                fg_color="#666666",
                hover_color="#555555",
                font=("Segoe UI", 12),
                width=120,
                height=40
            ).pack(side="left", padx=10)

    
    def _show_site_picker(self, row):
        """Muestra picker de sitios para la celda especificada"""
        import tkinter as tk
        from tkinter import messagebox
        
        if not self.blackboard or not hasattr(self.blackboard, 'controller'):
            messagebox.showerror("Error", "No se puede acceder a los datos de sitios")
            return
        
        # Obtener sitios del controller
        sites = self.blackboard.controller.get_sites()
        # Nuevo formato: 'ID - Nombre'
        site_options = [f"{row[0]} - {row[1]}" for row in sites]
        
        # Crear ventana modal

        picker_win = self.ui_factory.toplevel(self.container)
        picker_win.title("Seleccionar Sitio")
        picker_win.geometry("500x250")
        picker_win.transient(self.container)
        picker_win.grab_set()
        
        # Header
        header = self.ui_factory.frame(picker_win, fg_color="#1a1a1a", corner_radius=0, height=60)
        header.pack(fill="x")
        header.pack_propagate(False)
        
        self.ui_factory.label(
            header,
            text="🏢 Seleccionar Sitio",
            font=("Segoe UI", 20, "bold"),
            text_color="#4a90e2"
        ).pack(pady=15)
        
        # Contenido
        content = self.ui_factory.frame(picker_win, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=20, pady=20)
        
        self.ui_factory.label(
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
        btn_frame = self.ui_factory.frame(content, fg_color="transparent")
        btn_frame.pack(pady=10)
        
        def accept():
            selected = combo_var.get().strip()
            if selected:
                self.sheet.set_cell_data(row, 1, selected)
                self.sheet.redraw()
                self.pending_changes.add(row)
                picker_win.destroy()
                if row is not None and row < len(self.row_data_cache):
                    row_data = self.sheet.get_row_data(row)
                    id_evento = self.row_data_cache[row]['id']
                    evento = (
                        id_evento,
                        row_data[0],  # fecha_hora
                        row_data[1],  # sitio_concatenado
                        row_data[2],  # nombre_actividad
                        row_data[3],  # cantidad
                        row_data[4],  # camera
                        row_data[5],  # descripcion
                    )
                    self.auto_save_pending_changes(evento)

                else:
                    self.auto_save_pending_changes(None)
                
        self.ui_factory.button(
            btn_frame,
            text="✅ Aceptar",
            command=accept,
            fg_color="#00c853",
            hover_color="#00a043",
            font=("Segoe UI", 12, "bold"),
            width=120,
            height=40
        ).pack(side="left", padx=10)
        
        self.ui_factory.button(
            btn_frame,
            text="❌ Cancelar",
            command=picker_win.destroy,
            fg_color="#666666",
            hover_color="#555555",
            font=("Segoe UI", 12),
            width=120,
            height=40
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

        picker_win = self.ui_factory.toplevel(self.container)
        picker_win.title("Seleccionar Actividad")
        picker_win.geometry("500x250")
        picker_win.transient(self.container)
        picker_win.grab_set()
        
        # Header
        header = self.ui_factory.frame(picker_win, fg_color="#1a1a1a", corner_radius=0, height=60)
        header.pack(fill="x")
        header.pack_propagate(False)
        
        self.ui_factory.label(
            header,
            text="📋 Seleccionar Actividad",
            font=("Segoe UI", 20, "bold"),
            text_color="#4a90e2"
        ).pack(pady=15)
        
        # Contenido
        content = self.ui_factory.frame(picker_win, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=20, pady=20)
        
        self.ui_factory.label(
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
        btn_frame = self.ui_factory.frame(content, fg_color="transparent")
        btn_frame.pack(pady=10)
        
        def accept():
            selected = combo_var.get().strip()
            if selected:
                self.sheet.set_cell_data(row, 2, selected)
                self.sheet.redraw()
                self.pending_changes.add(row)
                picker_win.destroy()

            if row < len(self.row_data_cache):
                self.pending_changes.add(row)
                # Obtener la tupla completa del evento (igual que en _on_cell_edit)
                row_data = self.sheet.get_row_data(row)
                id_evento = self.row_data_cache[row]['id']
                evento = (
                    id_evento,
                    row_data[0],  # fecha_hora
                    row_data[1],  # sitio_concatenado
                    row_data[2],  # nombre_actividad
                    row_data[3],  # cantidad
                    row_data[4],  # camera
                    row_data[5],  # descripcion
                )
                # Guardar después del cambio
                self.parent.after(500, lambda: self.controller.auto_save_pending_event(evento))
            else:
                messagebox.showwarning("Advertencia", "Selecciona una actividad", parent=picker_win)
        
        self.ui_factory.button(
            btn_frame,
            text="✅ Aceptar",
            command=accept,
            fg_color="#00c853",
            hover_color="#00a043",
            font=("Segoe UI", 12, "bold"),
            width=120,
            height=40
        ).pack(side="left", padx=10)
        
        self.ui_factory.button(
            btn_frame,
            text="❌ Cancelar",
            command=picker_win.destroy,
            fg_color="#666666",
            hover_color="#555555",
            font=("Segoe UI", 12),
            width=120,
            height=40
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
                command=lambda: self._delete_selected()
            )
            
            try:
                context_menu.tk_popup(event.x_root, event.y_root)
            finally:
                context_menu.grab_release()
        
        except Exception as e:
            print(f"[ERROR] Error mostrando menú contextual: {e}")
    
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
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo eliminar el evento:\n{e}")

    def auto_save_pending_changes(self, evento=None):
        """Guarda automáticamente los cambios pendientes o un evento específico"""
        try:
            if evento is not None:
                # Si se pasa un evento explícito, enviarlo directamente al controlador
                self.controller.auto_save_pending_event(evento)
                print(f"[DEBUG] Auto-saved evento único: {evento}")
                return
            if not self.pending_changes:
                return
            rows_to_save = list(self.pending_changes)
            for row_idx in rows_to_save:
                if row_idx < len(self.row_data_cache):
                    # Obtener los valores actuales de la fila
                    row_data = self.sheet.get_row_data(row_idx)
                    # Obtener el id_evento original
                    id_evento = self.row_data_cache[row_idx]['id']
                    # Empaquetar la tupla para el controlador
                    evento = (
                        id_evento,
                        # Asegúrate de mapear los valores en el orden esperado por el controlador/modelo
                        row_data[0],  # fecha_hora
                        row_data[1],  # sitio_concatenado
                        row_data[2],  # nombre_actividad
                        row_data[3],  # cantidad
                        row_data[4],  # camera
                        row_data[5],  # descripcion
                    )
                    # Llamar al controlador con la tupla

                    self.controller.auto_save_pending_event(evento)
                    print(f"[DEBUG] Auto-saved row {row_idx}")
            # Limpiar conjunto de pendientes después de guardar
            self.pending_changes.clear()
        except Exception as e:
            print(f"[ERROR] auto_save_pending_changes: {e}")
    
    def _update_status(self, message):
        """Actualiza el label de estado"""
        if hasattr(self, 'status_label') and self.status_label:
            if self.UI:
                self.status_label.configure(text=message)
            else:
                self.status_label.configure(text=message)
