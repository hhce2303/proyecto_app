"""
OperatorBlackboard - Contenedor de tabs para operadores.
Hereda de Blackboard y personaliza para operador.

ENFOQUE ACTUAL: Daily + Specials con módulos MVC
PENDIENTES: Covers

IMPORTANTE: 
- DAILY = OPERADOR (crear eventos) - ✅ FUNCIONANDO
- SPECIALS = OPERADOR (eventos especiales con timezone) - ✅ FUNCIONANDO
- COVERS = OPERADOR (solicitar covers) - ⏳ Pendiente
"""
from views.blackboard import Blackboard
from views.modules.daily_module import DailyModule
from views.modules.specials_module import SpecialsModule
from controllers.daily_controller import DailyController
from under_super import FilteredCombobox
import tkinter as tk
from datetime import datetime
try:
    import tkcalendar
except ImportError:
    tkcalendar = None

class OperatorBlackboard(Blackboard):
    """
    Blackboard para Operadores.
    Tab activo: Daily con DailyModule
    Tabs pendientes: Specials, Covers
    """
    
    def __init__(self, username, role, session_id=None, station=None, root=None):
        """Inicializa blackboard de operador"""
        self.current_tab = "Daily"
        self.tab_buttons = {}
        self.tab_frames = {}
        
        # Inicializar controller
        self.controller = DailyController(username)
        
        super().__init__(username, role, session_id, station, root)
        
        # Botón de logout
        #self.ui_factory.button(
            #parent,
            #text="🚪 Logout",
            #command=self._on_logout,
            #width=100,
            #fg_color="#d32f2f",
            #hover_color="#b71c1c"
        #).pack(side="right", padx=10)
    
    def _setup_tabs_content(self, parent):
        """Tabs de Operador: Daily, Specials, Covers"""
        tabs = [
            ("📝 Daily", "Daily"),
            ("⭐ Specials", "Specials"),
            ("🔄 Covers", "Covers")
        ]
        
        for text, tab_name in tabs:
            btn = self.ui_factory.button(
                parent,
                text=text,
                command=lambda t=tab_name: self._switch_tab(t),
                width=120,
                fg_color="#4D6068"
            )
            btn.pack(side="left", padx=5, pady=10)
            self.tab_buttons[tab_name] = btn
        
        self._update_tab_buttons()
    
    def _setup_content(self, parent):
        """Contenido para tabs de operador"""
        
        # ========== TAB DAILY (EXCLUSIVO DE OPERADORES) ==========
        daily_frame = self.ui_factory.frame(parent, fg_color="#1e1e1e")
        
        # DailyModule primero
        try:
            self.daily_module = DailyModule(
                parent=daily_frame,
                username=self.username,
                session_id=self.session_id,
                role=self.role,
                UI=self.UI
            )
            # Establecer referencia al blackboard para acceder a _show_datetime_picker
            self.daily_module.blackboard = self
            print(f"[DEBUG] DailyModule inicializado para OPERADOR: {self.username}")
        except Exception as e:
            print(f"[ERROR] No se pudo inicializar DailyModule: {e}")
            self.ui_factory.label(
                daily_frame,
                text=f"Error al cargar Daily: {e}",
                font=("Segoe UI", 12),
                fg="#ff4444"
            ).pack(pady=20)
        
        # Formulario ABAJO del tksheet
        form_frame = self.ui_factory.frame(daily_frame, fg_color="#2b2b2b")
        form_frame.pack(fill="x", padx=10, pady=(0, 10))
        
        self._create_event_form(form_frame)
        
        self.tab_frames["Daily"] = daily_frame
        
        # ========== TAB SPECIALS (OPERADOR - EVENTOS ESPECIALES) ==========
        specials_frame = self.ui_factory.frame(parent, fg_color="#1e1e1e")
        
        # SpecialsModule para mostrar eventos de grupos especiales
        try:
            self.specials_module = SpecialsModule(
                container=specials_frame,
                username=self.username,
                ui_factory=self.ui_factory,
                UI=self.UI
            )
            # Establecer referencia al blackboard
            self.specials_module.blackboard = self
            print(f"[DEBUG] SpecialsModule inicializado para OPERADOR: {self.username}")
        except Exception as e:
            print(f"[ERROR] No se pudo inicializar SpecialsModule: {e}")
            import traceback
            traceback.print_exc()
            self.ui_factory.label(
                specials_frame,
                text=f"Error al cargar Specials: {e}",
                font=("Segoe UI", 12),
                fg="#ff4444"
            ).pack(pady=20)
        
        # Toolbar para acciones de Specials
        specials_toolbar = self.ui_factory.frame(specials_frame, fg_color="#2b2b2b")
        specials_toolbar.pack(fill="x", padx=10, pady=(0, 10))
        
        self.ui_factory.button(
            specials_toolbar,
            text="📤 Enviar Seleccionados",
            command=self._send_selected_specials,
            width=180,
            fg_color="#4CAF50",
            hover_color="#45a049"
        ).pack(side="left", padx=5, pady=5)
        
        self.ui_factory.button(
            specials_toolbar,
            text="📤 Enviar Todos",
            command=self._send_all_specials,
            width=150,
            fg_color="#2196F3",
            hover_color="#1976D2"
        ).pack(side="left", padx=5, pady=5)
        
        self.tab_frames["Specials"] = specials_frame
        
        # ========== TAB COVERS (placeholder) ==========
        covers_frame = self.ui_factory.frame(parent, fg_color="#23272a")
        self.ui_factory.label(
            covers_frame,
            text="Contenido de Covers",
            font=("Segoe UI", 18, "bold"),
            fg="#00bfae"
        ).pack(pady=20)
        self.ui_factory.label(
            covers_frame,
            text="Próximo módulo a implementar",
            font=("Segoe UI", 12),
            fg="#999999"
        ).pack(pady=10)
        self.tab_frames["Covers"] = covers_frame
        
        self._show_current_tab()
    
    def _switch_tab(self, tab_name):
        """Cambia entre tabs y recarga datos"""
        if self.current_tab != tab_name:
            self.current_tab = tab_name
            self._show_current_tab()
            self._update_tab_buttons()
            
            # Recargar datos del módulo al cambiar de tab
            if tab_name == "Daily" and hasattr(self, 'daily_module'):
                self.daily_module.load_data()
            elif tab_name == "Specials" and hasattr(self, 'specials_module'):
                self.specials_module.load_data()
    
    def _show_current_tab(self):
        """Muestra el frame del tab actual"""
        for tab_name, frame in self.tab_frames.items():
            if tab_name == self.current_tab:
                frame.pack(fill="both", expand=True)
            else:
                frame.pack_forget()
    
    def _update_tab_buttons(self):
        """Actualiza estilo de botones"""
        for tab_name, btn in self.tab_buttons.items():
            if tab_name == self.current_tab:
                self.ui_factory.set_widget_color(btn, fg_color="#4a90e2")
            else:
                self.ui_factory.set_widget_color(btn, fg_color="#4D6068")
    
    def _on_logout(self):
        """Handler de logout"""
        from tkinter import messagebox
        if messagebox.askyesno("Logout", "¿Cerrar sesión?", parent=self.window):
            self.window.destroy()
    
    def _on_close(self):
        """Handler de cierre"""
        from tkinter import messagebox
        if messagebox.askokcancel("Cerrar", "¿Cerrar ventana?", parent=self.window):
            self.window.destroy()
    
    def _create_event_form(self, parent):
        """Crea el formulario horizontal alineado con columnas del tksheet"""
        # Contenedor interno para alineación
        inner_frame = tk.Frame(parent, bg="#2b2b2b")
        inner_frame.pack(fill="x", padx=(0, 10), pady=5)
        
        # Botón Agregar (lado izquierdo, como row index)
        add_btn = self.ui_factory.button(
            inner_frame,
            text="➕",
            command=self._add_event,
            width=30,
            fg_color="#4CAF50",
            hover_color="#45a049"
        )
        add_btn.pack(side="left", padx=(2, 12))

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
        entry_wrapper = tk.Frame(datetime_container, bg="#333333", highlightthickness=0)
        entry_wrapper.pack(side="top")
        
        self.datetime_entry = tk.Entry(
            entry_wrapper,
            width=15,
            font=("Segoe UI", 10),
            bg="#333333",
            fg="#ffffff",
            insertbackground="#ffffff",
            readonlybackground="#333333",
            state="readonly",
            relief="flat",
            borderwidth=0
        )
        self.datetime_entry.pack(side="left", padx=(3, 0), pady=2)
        
        # Botón dentro del entry (lado derecho)
        datetime_btn = self.ui_factory.button(
            entry_wrapper,
            text="📅",
            command=lambda: self._show_datetime_picker(
                callback=lambda dt: self._set_datetime_value(dt)
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
            width=40,
            values=self._get_sites()
        )
        self.site_combo.pack(side="top")
        
        # Campo Actividad
        activity_container = tk.Frame(inner_frame, bg="#2b2b2b")
        activity_container.pack(side="left", padx=0)
        
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
        quantity_container.pack(side="left", padx=0)
        
        tk.Label(
            quantity_container,
            text="Cantidad:",
            font=("Segoe UI", 9),
            fg="#ffffff",
            bg="#2b2b2b",
            justify="center"
        ).pack(side="top")
        
        self.quantity_entry = tk.Entry(
            quantity_container,
            width=10,
            font=("Segoe UI", 10),
            bg="#333333",
            fg="#ffffff",
            insertbackground="#ffffff",
            justify="center"
        )
        self.quantity_entry.insert(0, "0")
        self.quantity_entry.pack(side="top")
        
        # Campo Camera
        camera_container = tk.Frame(inner_frame, bg="#2b2b2b")
        camera_container.pack(side="left", padx=0)
        
        tk.Label(
            camera_container,
            text="Camera:",
            font=("Segoe UI", 9),
            fg="#ffffff",
            bg="#2b2b2b",
            justify="center"
        ).pack(side="top")
        
        self.camera_entry = tk.Entry(
            camera_container,
            width=12,
            font=("Segoe UI", 10),
            bg="#333333",
            fg="#ffffff",
            insertbackground="#ffffff",
            justify="center"
        )
        self.camera_entry.pack(side="top")
        
        # Campo Descripción
        description_container = tk.Frame(inner_frame, bg="#2b2b2b")
        description_container.pack(side="left", padx=0)
        
        tk.Label(
            description_container,
            text="Descripción:",
            font=("Segoe UI", 9),
            fg="#ffffff",
            bg="#2b2b2b",
            justify="center"
        ).pack(side="top")
        
        self.description_entry = tk.Entry(
            description_container,
            width=45,
            font=("Segoe UI", 10),
            bg="#333333",
            fg="#ffffff",
            insertbackground="#ffffff"
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
        
        # Llamar al controller para crear evento (MVC)
        success, message = self.controller.create_event(
            site_id,
            activity,
            quantity_val,
            camera,
            description
        )
        
        if success:
            # Limpiar campos
            self.site_combo.set("")
            self.activity_combo.set("")
            self.quantity_entry.delete(0, "end")
            self.quantity_entry.insert(0, "0")
            self.camera_entry.delete(0, "end")
            self.description_entry.delete(0, "end")
            
            # Refrescar DailyModule
            if hasattr(self, 'daily_module'):
                self.daily_module.load_data()
            
            print(f"[DEBUG] {message}")
        else:
            messagebox.showerror(
                "Error",
                f"No se pudo agregar el evento:\n{message}",
                parent=self.window
            )
    
    def _set_datetime_value(self, dt):
        """Actualiza el entry de fecha/hora con el datetime seleccionado"""
        self.datetime_entry.configure(state="normal")
        self.datetime_entry.delete(0, "end")
        self.datetime_entry.insert(0, dt.strftime("%Y-%m-%d %H:%M:%S"))
        self.datetime_entry.configure(state="readonly")
    
    def _show_datetime_picker(self, callback, initial_datetime=None):
        """
        Muestra un selector de fecha/hora moderno y reutilizable.
        
        Args:
            callback: Función que recibe el datetime seleccionado
            initial_datetime: datetime inicial (por defecto datetime.now())
        
        Ejemplo de uso:
            self._show_datetime_picker(callback=lambda dt: print(dt))
        """
        from tkinter import messagebox
        
        if tkcalendar is None:
            messagebox.showerror(
                "Error",
                "El módulo tkcalendar no está instalado.\nInstálalo con: pip install tkcalendar",
                parent=self.window
            )
            return
        
        # Fecha/hora inicial
        now = initial_datetime if initial_datetime else datetime.now()
        
        # Crear ventana modal
        if self.UI is not None:
            picker_win = self.UI.CTkToplevel(self.window)
            picker_win.title("Seleccionar Fecha y Hora")
            picker_win.geometry("500x450")
            picker_win.resizable(False, False)
            picker_win.transient(self.window)
            picker_win.grab_set()
            
            # Header
            header = self.UI.CTkFrame(picker_win, fg_color="#1a1a1a", corner_radius=0, height=60)
            header.pack(fill="x", padx=0, pady=0)
            header.pack_propagate(False)
            
            self.UI.CTkLabel(
                header, 
                text="📅 Seleccionar Fecha y Hora",
                font=("Segoe UI", 20, "bold"),
                text_color="#4a90e2"
            ).pack(pady=15)
            
            # Contenido principal
            content = self.UI.CTkFrame(picker_win, fg_color="transparent")
            content.pack(fill="both", expand=True, padx=20, pady=20)
            
            # Sección de Fecha
            date_section = self.UI.CTkFrame(content, fg_color="#2b2b2b", corner_radius=10)
            date_section.pack(fill="x", pady=(0, 15))
            
            self.UI.CTkLabel(
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
            time_section = self.UI.CTkFrame(content, fg_color="#2b2b2b", corner_radius=10)
            time_section.pack(fill="x", pady=(0, 15))
            
            self.UI.CTkLabel(
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
            
            self.UI.CTkButton(
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
            btn_frame = self.UI.CTkFrame(content, fg_color="transparent")
            btn_frame.pack(pady=10)
            
            def accept():
                try:
                    selected_date = cal.get_date()
                    selected_time = datetime.strptime(
                        f"{selected_date} {hour_var.get():02d}:{minute_var.get():02d}:{second_var.get():02d}",
                        "%Y-%m-%d %H:%M:%S"
                    )
                    callback(selected_time)
                    picker_win.destroy()
                except Exception as e:
                    messagebox.showerror(
                        "Error",
                        f"Error al establecer fecha/hora:\n{e}",
                        parent=picker_win
                    )
            
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
            picker_win = tk.Toplevel(self.window)
            picker_win.title("Seleccionar Fecha y Hora")
            picker_win.geometry("400x400")
            picker_win.transient(self.window)
            picker_win.grab_set()
            
            content = tk.Frame(picker_win, bg="#2b2b2b")
            content.pack(fill="both", expand=True, padx=20, pady=20)
            
            tk.Label(
                content,
                text="Fecha:",
                bg="#2b2b2b",
                fg="#ffffff",
                font=("Segoe UI", 12, "bold")
            ).pack(anchor="w", pady=(10, 5))
            
            cal = tkcalendar.DateEntry(
                content,
                width=25,
                background='#4a90e2',
                foreground='white',
                borderwidth=2,
                year=now.year,
                month=now.month,
                day=now.day
            )
            cal.pack(pady=5, fill="x")
            
            tk.Label(
                content,
                text="Hora:",
                bg="#2b2b2b",
                fg="#ffffff",
                font=("Segoe UI", 12, "bold")
            ).pack(anchor="w", pady=(20, 5))
            
            time_frame = tk.Frame(content, bg="#2b2b2b")
            time_frame.pack(fill="x", pady=5)
            
            hour_var = tk.IntVar(value=now.hour)
            minute_var = tk.IntVar(value=now.minute)
            second_var = tk.IntVar(value=now.second)
            
            hour_spin = tk.Spinbox(time_frame, from_=0, to=23, textvariable=hour_var, width=8)
            hour_spin.pack(side="left", padx=5)
            
            minute_spin = tk.Spinbox(time_frame, from_=0, to=59, textvariable=minute_var, width=8)
            minute_spin.pack(side="left", padx=5)
            
            second_spin = tk.Spinbox(time_frame, from_=0, to=59, textvariable=second_var, width=8)
            second_spin.pack(side="left", padx=5)
            
            def accept():
                try:
                    selected_date = cal.get_date()
                    selected_time = datetime.strptime(
                        f"{selected_date} {hour_var.get():02d}:{minute_var.get():02d}:{second_var.get():02d}",
                        "%Y-%m-%d %H:%M:%S"
                    )
                    callback(selected_time)
                    picker_win.destroy()
                except Exception as e:
                    messagebox.showerror("Error", f"Error al establecer fecha/hora:\n{e}", parent=picker_win)
            
            btn_frame = tk.Frame(content, bg="#2b2b2b")
            btn_frame.pack(side="bottom", pady=20)
            
            tk.Button(
                btn_frame,
                text="Aceptar",
                command=accept,
                bg="#00c853",
                fg="white",
                width=10
            ).pack(side="left", padx=5)
            
            tk.Button(
                btn_frame,
                text="Cancelar",
                command=picker_win.destroy,
                bg="#666666",
                fg="white",
                width=10
            ).pack(side="left", padx=5)
    
    def _send_selected_specials(self):
        """Envía eventos especiales seleccionados a un supervisor"""
        if not hasattr(self, 'specials_module'):
            return
        
        # Obtener filas seleccionadas del módulo
        selected_rows = self.specials_module.get_selected_rows()
        
        if not selected_rows:
            from tkinter import messagebox
            messagebox.showwarning(
                "Sin selección",
                "No hay filas seleccionadas",
                parent=self.window
            )
            return
        
        # Obtener IDs de eventos seleccionados
        evento_ids = self.specials_module.get_evento_ids_for_rows(selected_rows)
        
        if not evento_ids:
            from tkinter import messagebox
            messagebox.showwarning(
                "Error",
                "No se pudieron obtener los IDs de eventos",
                parent=self.window
            )
            return
        
        # Mostrar selector de supervisor
        self._show_supervisor_selector(evento_ids)
    
    def _send_all_specials(self):
        """Envía todos los eventos especiales visibles a un supervisor"""
        if not hasattr(self, 'specials_module'):
            return
        
        # Obtener todas las filas
        total_rows = self.specials_module.get_total_rows()
        
        if total_rows == 0:
            from tkinter import messagebox
            messagebox.showinfo(
                "Sin datos",
                "No hay eventos para enviar",
                parent=self.window
            )
            return
        
        # Obtener IDs de todos los eventos
        all_rows = list(range(total_rows))
        evento_ids = self.specials_module.get_evento_ids_for_rows(all_rows)
        
        if not evento_ids:
            from tkinter import messagebox
            messagebox.showwarning(
                "Error",
                "No se pudieron obtener los IDs de eventos",
                parent=self.window
            )
            return
        
        # Mostrar selector de supervisor
        self._show_supervisor_selector(evento_ids)
    
    def _show_supervisor_selector(self, evento_ids):
        """
        Muestra ventana modal para seleccionar supervisor y enviar eventos.
        
        Args:
            evento_ids (list): Lista de IDs de eventos a enviar
        """
        from tkinter import messagebox
        
        # Obtener lista de supervisores activos a través del controller
        controller = self.specials_module.controller
        supervisores = controller.get_active_supervisors()
        
        if not supervisores:
            messagebox.showwarning(
                "Sin supervisores",
                "No hay supervisores activos disponibles",
                parent=self.window
            )
            return
        
        # Crear ventana modal
        if self.UI is not None:
            supervisor_win = self.UI.CTkToplevel(self.window)
            supervisor_win.configure(fg_color="#2c2f33")
        else:
            supervisor_win = tk.Toplevel(self.window)
            supervisor_win.configure(bg="#2c2f33")
        
        supervisor_win.title("Selecciona un Supervisor")
        supervisor_win.geometry("360x220")
        supervisor_win.resizable(False, False)
        supervisor_win.transient(self.window)
        supervisor_win.grab_set()
        supervisor_win.focus_set()
        
        # Header
        if self.UI is not None:
            self.UI.CTkLabel(
                supervisor_win,
                text="Supervisores disponibles:",
                text_color="#00bfae",
                font=("Segoe UI", 16, "bold")
            ).pack(pady=(18, 8))
            
            container = self.UI.CTkFrame(supervisor_win, fg_color="#2c2f33")
            container.pack(fill="both", expand=True, padx=16, pady=(0, 12))
        else:
            tk.Label(
                supervisor_win,
                text="Supervisores disponibles:",
                bg="#2c2f33",
                fg="#00bfae",
                font=("Segoe UI", 13, "bold")
            ).pack(pady=(18, 4))
            
            container = tk.Frame(supervisor_win, bg="#2c2f33")
            container.pack(fill="both", expand=True, padx=14, pady=(4, 16))
        
        # Control de selección
        sup_var = tk.StringVar()
        
        if self.UI is not None:
            opt = self.UI.CTkOptionMenu(
                container,
                variable=sup_var,
                values=supervisores,
                fg_color="#262a31",
                button_color="#14414e",
                text_color="#00bfae"
            )
            sup_var.set(supervisores[0])
            opt.pack(fill="x", padx=6, pady=6)
        else:
            yscroll_sup = tk.Scrollbar(container, orient="vertical")
            yscroll_sup.pack(side="right", fill="y")
            
            sup_listbox = tk.Listbox(
                container,
                height=10,
                selectmode="browse",
                bg="#262a31",
                fg="#00bfae",
                font=("Segoe UI", 12),
                yscrollcommand=yscroll_sup.set,
                activestyle="dotbox",
                selectbackground="#14414e"
            )
            sup_listbox.pack(side="left", fill="both", expand=True)
            yscroll_sup.config(command=sup_listbox.yview)
            
            for sup in supervisores:
                sup_listbox.insert("end", sup)
            
            if supervisores:
                sup_listbox.selection_set(0)
        
        def aceptar_supervisor():
            """Procesa el envío de eventos al supervisor seleccionado"""
            # Obtener supervisor seleccionado
            if self.UI is not None:
                supervisor = (sup_var.get() or "").strip()
                if not supervisor:
                    messagebox.showwarning(
                        "Sin supervisor",
                        "Debes seleccionar un supervisor",
                        parent=supervisor_win
                    )
                    return
            else:
                selected_indices = sup_listbox.curselection()
                if not selected_indices:
                    messagebox.showwarning(
                        "Sin supervisor",
                        "Debes seleccionar un supervisor",
                        parent=supervisor_win
                    )
                    return
                supervisor = sup_listbox.get(selected_indices[0])
            
            # Llamar al controller para enviar (MVC)
            success, message, stats = controller.send_to_supervisor(evento_ids, supervisor)
            
            supervisor_win.destroy()
            
            if success:
                messagebox.showinfo(
                    "Éxito",
                    message,
                    parent=self.window
                )
                # Recargar datos
                self.specials_module.load_data()
            else:
                messagebox.showerror(
                    "Error",
                    f"No se pudo enviar eventos:\n{message}",
                    parent=self.window
                )
        
        # Botones Aceptar/Cancelar
        if self.UI is not None:
            btn_frame = self.UI.CTkFrame(supervisor_win, fg_color="transparent")
            btn_frame.pack(pady=(8, 16))
            
            self.UI.CTkButton(
                btn_frame,
                text="✅ Aceptar",
                command=aceptar_supervisor,
                fg_color="#00c853",
                hover_color="#00a043",
                font=("Segoe UI", 12, "bold"),
                width=120,
                height=36
            ).pack(side="left", padx=10)
            
            self.UI.CTkButton(
                btn_frame,
                text="❌ Cancelar",
                command=supervisor_win.destroy,
                fg_color="#666666",
                hover_color="#555555",
                font=("Segoe UI", 12),
                width=120,
                height=36
            ).pack(side="left", padx=10)
        else:
            btn_frame = tk.Frame(supervisor_win, bg="#2c2f33")
            btn_frame.pack(pady=(8, 16))
            
            tk.Button(
                btn_frame,
                text="✅ Aceptar",
                command=aceptar_supervisor,
                bg="#00c853",
                fg="white",
                relief="flat",
                width=12,
                font=("Segoe UI", 11, "bold")
            ).pack(side="left", padx=10)
            
            tk.Button(
                btn_frame,
                text="❌ Cancelar",
                command=supervisor_win.destroy,
                bg="#666666",
                fg="white",
                relief="flat",
                width=12,
                font=("Segoe UI", 11)
            ).pack(side="left", padx=10)
