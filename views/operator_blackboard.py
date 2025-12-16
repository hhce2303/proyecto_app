"""
OperatorBlackboard - Contenedor de tabs para operadores.
Hereda de Blackboard y personaliza para operador.

ENFOQUE ACTUAL: Daily + Specials + Covers con módulos MVC

IMPORTANTE: 
- DAILY = OPERADOR (crear eventos) - ✅ FUNCIONANDO
- SPECIALS = OPERADOR (eventos especiales con timezone) - ✅ FUNCIONANDO
- COVERS = OPERADOR (solicitar/visualizar covers) - ✅ IMPLEMENTADO
"""
from views.blackboard import Blackboard
from views.modules.daily_module import DailyModule
from views.modules.specials_module import SpecialsModule
from views.modules.covers_module import CoversModule
from views.dialogs.request_cover_dialog import RequestCoverDialog
from views.dialogs.register_cover_dialog import RegisterCoverDialog
from controllers.daily_controller import DailyController
from under_super import FilteredCombobox
import tkinter as tk
from datetime import datetime
import login
import backend_super
try:
    import tkcalendar
except ImportError:
    tkcalendar = None

from covers_panel import show_covers_programados_panel
from models.user_model import get_user_status_bd

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
        
        # Variables para control de shift
        self.shift_warning_label = None
        self.start_shift_btn = None
        self.end_shift_btn = None
        self.add_event_btn = None
        self.solicitar_cover_btn = None
        self.registrar_cover_btn = None
        self.send_selected_btn = None
        self.send_all_btn = None
        self.refresh_job = None
        
        super().__init__(username, role, session_id, station, root)
    
    def _build(self):
        """Sobrescribe _build para inicializar estado de shift después de construir"""
        # Llamar al build del padre
        super()._build()
        
        # Inicializar estado de controles según shift activo
        self._update_shift_controls()
        
        # Iniciar auto-refresh
        self._start_auto_refresh()
    
    def _setup_tabs_content(self, parent):
        """Tabs de Operador: Daily, Specials, Covers + Botón Solicitar Cover"""
        # Tabs (izquierda)
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
        
        # Botón End Shift (derecha, primero para que aparezca más a la derecha)
        self.end_shift_btn = self.ui_factory.button(
            parent,
            text="🏁 End Shift",
            command=self._end_shift,
            width=130,
            fg_color="#d32f2f",
            hover_color="#b71c1c"
        )
        self.end_shift_btn.pack(side="right", padx=(5, 10), pady=10)
        
        # Botón Start Shift (derecha)
        self.start_shift_btn = self.ui_factory.button(
            parent,
            text="🚀 Start Shift",
            command=self._start_shift,
            width=130,
            fg_color="#00c853",
            hover_color="#00a043"
        )
        self.start_shift_btn.pack(side="right", padx=(10, 5), pady=10)
        
        # Botón Registrar Cover
        self.registrar_cover_btn = self.ui_factory.button(
            parent,
            text="✍️ Registrar Cover",
            command=self._register_cover,
            width=150,
            fg_color="#ff6f00",
            hover_color="#e65100"
        )
        self.registrar_cover_btn.pack(side="right", padx=(5, 10), pady=10)
        
        # Botón Solicitar Cover
        self.solicitar_cover_btn = self.ui_factory.button(
            parent,
            text="🙋 Solicitar Cover",
            command=self._request_cover,
            width=150,
            fg_color="#2e7d32",
            hover_color="#1b5e20"
        )
        self.solicitar_cover_btn.pack(side="right", padx=(10, 5), pady=10)
        
        # BOTÓN LISTA DE COVERS (solo visible cuando Active = 2)
        self.lista_covers_btn = self.ui_factory.button(
            parent,
            text="📋 Lista de Covers",
            command=lambda: self._switch_tab("Lista Covers"),
            width=160,
            fg_color="#4D6068",
            hover_color="#ffa726"
        )
        self.lista_covers_btn.pack_forget()  # Inicialmente oculto

        def check_and_update_covers_button():
            try:
                active_status = get_user_status_bd(self.username)
                if active_status == 2:
                    if not self.lista_covers_btn.winfo_ismapped():
                        self.lista_covers_btn.pack(side="left", padx=5, pady=10)
                else:
                    if self.lista_covers_btn.winfo_ismapped():
                        self.lista_covers_btn.pack_forget()
            except Exception as e:
                print(f"[ERROR] Error checking covers button visibility: {e}")
            # Programar siguiente verificación (cada 5 segundos)
            (self.root or self.window).after(5000, check_and_update_covers_button)

        # Iniciar verificación periódica
        (self.root or self.window).after(500, check_and_update_covers_button)
        
        self._update_tab_buttons()
    
    def _setup_content(self, parent):
        """Contenido para tabs de operador"""
        
        # ========== TAB DAILY (EXCLUSIVO DE OPERADORES) ==========
        daily_frame = self.ui_factory.frame(parent, fg_color="#1e1e1e")
        
        # Label de advertencia (solo visible cuando NO hay turno activo)
        warning_frame = self.ui_factory.frame(daily_frame, fg_color="#b71c1c", border_width=2, border_color="#ff5252")
        warning_frame.pack(fill="x", padx=10, pady=10)
        
        self.shift_warning_label = self.ui_factory.label(
            warning_frame,
            text="⚠️ INICIA TU TURNO PARA COMENZAR A REGISTRAR EVENTOS ⚠️",
            text_color="#ffffff",
            font=("Segoe UI", 16, "bold")
        )
        self.shift_warning_label.pack(pady=15)
        
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
        
        self.send_selected_btn = self.ui_factory.button(
            specials_toolbar,
            text="📤 Enviar Seleccionados",
            command=self._send_selected_specials,
            width=180,
            fg_color="#4CAF50",
            hover_color="#45a049"
        )
        self.send_selected_btn.pack(side="left", padx=5, pady=5)
        
        self.send_all_btn = self.ui_factory.button(
            specials_toolbar,
            text="📤 Enviar Todos",
            command=self._send_all_specials,
            width=150,
            fg_color="#2196F3",
            hover_color="#1976D2"
        )
        self.send_all_btn.pack(side="left", padx=5, pady=5)
        
        self.tab_frames["Specials"] = specials_frame
        
        # ========== TAB COVERS (MVC COMPLETO) ==========
        covers_frame = self.ui_factory.frame(parent, fg_color="#23272a")
        
        # CoversModule
        try:
            self.covers_module = CoversModule(
                container=covers_frame,
                username=self.username,
                ui_factory=self.ui_factory,
                UI=self.UI
            )
            # Establecer referencia al blackboard
            self.covers_module.blackboard = self
            print(f"[DEBUG] CoversModule inicializado para OPERADOR: {self.username}")
        except Exception as e:
            print(f"[ERROR] No se pudo inicializar CoversModule: {e}")
            import traceback
            traceback.print_exc()
            self.ui_factory.label(
                covers_frame,
                text=f"Error al cargar Covers: {e}",
                font=("Segoe UI", 12),
                fg="#ff4444"
            ).pack(pady=20)
        
        self.tab_frames["Covers"] = covers_frame
        
        # ========== TAB LISTA DE COVERS PROGRAMADOS ========== 
        covers_list_frame = self.ui_factory.frame(parent, fg_color="#23272a")
        try:
            from views.modules.covers_list_module import CoversListModule
            self.covers_list_module = CoversListModule(
                container=covers_list_frame,
                username=self.username,
                ui_factory=self.ui_factory,
                UI=self.UI
            )
            self.covers_list_module.blackboard = self
            print(f"[DEBUG] CoversListModule inicializado para OPERADOR: {self.username}")
        except Exception as e:
            print(f"[ERROR] No se pudo inicializar CoversListModule: {e}")
            import traceback
            traceback.print_exc()
            self.ui_factory.label(
                covers_list_frame,
                text=f"Error al cargar Lista de Covers: {e}",
                font=("Segoe UI", 12),
                fg="#ff4444"
            ).pack(pady=20)
        self.tab_frames["Lista Covers"] = covers_list_frame
        
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
            elif tab_name == "Covers" and hasattr(self, 'covers_module'):
                self.covers_module.load_data()
            elif tab_name == "Lista Covers" and hasattr(self, 'covers_list_module'):
                self.covers_list_module.load_data()

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
    
    def _request_cover(self):
        """
        Solicita un cover directamente con motivo predeterminado.
        Usa cover_model.request_covers() (model) para inserción en BD.
        """
        from tkinter import messagebox
        
        # ⭐ VALIDAR QUE HAY TURNO ACTIVO
        if not backend_super.has_active_shift(self.username):
            messagebox.showwarning(
                "Sin Turno Activo",
                "⚠️ Debes iniciar tu turno antes de solicitar covers.\n\n"
                "Haz clic en el botón '🚀 Start Shift' en la esquina superior derecha.",
                parent=self.window
            )
            return
        
        try:
            # Preparar datos para request_covers()
            from datetime import datetime
            time_request = datetime.now()
            motivo = "Necesito un cover"  # Motivo predeterminado
            approved = 1  # Siempre aprobado
            
            # Llamar al modelo para insertar en BD
            from models import cover_model
            
            cover_id = cover_model.request_covers(
                username=self.username,
                time_request=time_request,
                reason=motivo,
                aprvoved=approved  # Nota: typo en función original
            )
            
            if cover_id:
                print(f"[DEBUG] Cover solicitado exitosamente. ID: {cover_id}")
                # Refrescar módulo de covers si está activo
                if self.current_tab == "Covers" and hasattr(self, 'covers_module'):
                    self.covers_module.load_data()
            else:
                print("[DEBUG] No se generó ID de cover (posible validación fallida)")
        
        except Exception as e:
            from tkinter import messagebox
            messagebox.showerror(
                "Error",
                f"No se pudo solicitar el cover:\n{e}",
                parent=self.window
            )
            print(f"[ERROR] _request_cover: {e}")
            import traceback
            traceback.print_exc()
    
    def _register_cover(self):
        """
        Registra un cover realizado y cambia de sesión al operador que cubre.
        Usa RegisterCoverDialog (view), cover_model.insertar_cover() (model),
        y login.logout_silent + login.auto_login para cambio de sesión.
        """
        from tkinter import messagebox
        
        # ⭐ VALIDAR QUE HAY TURNO ACTIVO
        if not backend_super.has_active_shift(self.username):
            messagebox.showwarning(
                "Sin Turno Activo",
                "⚠️ Debes iniciar tu turno antes de registrar covers.\n\n"
                "Haz clic en el botón '🚀 Start Shift' en la esquina superior derecha.",
                parent=self.window
            )
            return
        
        try:
            # Obtener lista de operadores
            from models.database import get_connection
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT Nombre_Usuario 
                FROM user 
                WHERE Rol = 'Operador'
                ORDER BY Nombre_Usuario
                """
            )
            operadores = [row[0] for row in cursor.fetchall()]
            cursor.close()
            conn.close()
            
            if not operadores:
                from tkinter import messagebox
                messagebox.showwarning(
                    "Sin operadores",
                    "No hay operadores disponibles en el sistema.",
                    parent=self.window
                )
                return
            
            # Mostrar diálogo para capturar datos
            dialog = RegisterCoverDialog(
                parent=self.window,
                ui_factory=self.ui_factory,
                UI=self.UI
            )
            
            result = dialog.show(operadores)
            
            if not result:
                # Usuario canceló
                print("[DEBUG] Registro de cover cancelado por usuario")
                return
            
            # Obtener datos del diálogo
            motivo = result['motivo']
            covered_by = result['covered_by']
            
            print(f"[DEBUG] Registrando cover: {self.username} cubierto por {covered_by}, motivo: {motivo}")
            
            # Llamar al modelo para insertar cover
            # insertar_cover ya hace logout_silent al final
            from models import cover_model
            
            cover_model.insertar_cover(
                username=self.username,
                Covered_by=covered_by,
                Motivo=motivo,
                session_id=self.session_id,
                station=self.station
            )
            
            # Cerrar ventana actual antes de abrir nueva sesión
            self.window.destroy()
            
            # Auto-login del operador que cubre
            # Esto abre automáticamente el blackboard del nuevo usuario
            login.auto_login(
                username=covered_by,
                station=self.station,
                password="1234",
                parent=None,
                silent=True
            )
            
            print(f"[DEBUG] Sesión cambiada exitosamente a {covered_by}")
        
        except Exception as e:
            from tkinter import messagebox
            messagebox.showerror(
                "Error",
                f"No se pudo registrar el cover:\n{e}",
                parent=self.window
            )
            print(f"[ERROR] _register_cover: {e}")
            import traceback
            traceback.print_exc()
    
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
        from tkinter import messagebox
        
        # ⭐ VALIDAR QUE HAY TURNO ACTIVO
        if not backend_super.has_active_shift(self.username):
            messagebox.showwarning(
                "Sin Turno Activo",
                "⚠️ Debes iniciar tu turno antes de enviar eventos.\n\n"
                "Haz clic en el botón '🚀 Start Shift' en la esquina superior derecha.",
                parent=self.window
            )
            return
        
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
        from tkinter import messagebox
        
        # ⭐ VALIDAR QUE HAY TURNO ACTIVO
        if not backend_super.has_active_shift(self.username):
            messagebox.showwarning(
                "Sin Turno Activo",
                "⚠️ Debes iniciar tu turno antes de enviar eventos.\n\n"
                "Haz clic en el botón '🚀 Start Shift' en la esquina superior derecha.",
                parent=self.window
            )
            return
        
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
    
    def _start_shift(self):
        """Inicia el turno del operador"""
        try:
            # Llamar a la función de backend_super que muestra el date/time picker
            success = backend_super.on_start_shift(self.username, self.window)
            
            if success:
                print(f"[DEBUG] START SHIFT registrado exitosamente para {self.username}")
                # Actualizar controles inmediatamente
                self._update_shift_controls()
                # Refrescar módulos
                if hasattr(self, 'daily_module'):
                    self.daily_module.load_data()
                if hasattr(self, 'specials_module'):
                    self.specials_module.load_data()
                if hasattr(self, 'covers_module'):
                    self.covers_module.load_data()
            else:
                print(f"[DEBUG] START SHIFT cancelado o falló para {self.username}")
        
        except Exception as e:
            from tkinter import messagebox
            messagebox.showerror(
                "Error",
                f"No se pudo iniciar turno:\n{e}",
                parent=self.window
            )
            print(f"[ERROR] _start_shift: {e}")
            import traceback
            traceback.print_exc()
    
    def _end_shift(self):
        """Finaliza el turno del operador"""
        from tkinter import messagebox
        
        try:
            # Verificar que han pasado 7 horas
            if not backend_super.can_end_shift(self.username):
                start_time = backend_super.get_shift_start_time(self.username)
                if start_time:
                    from datetime import datetime, timedelta
                    elapsed = datetime.now() - start_time
                    hours_elapsed = elapsed.total_seconds() / 3600
                    hours_remaining = 7.0 - hours_elapsed
                    
                    messagebox.showwarning(
                        "Turno Incompleto",
                        f"Debes completar al menos 7 horas de turno.\n\n"
                        f"Tiempo transcurrido: {hours_elapsed:.1f} horas\n"
                        f"Tiempo restante: {hours_remaining:.1f} horas",
                        parent=self.window
                    )
                else:
                    messagebox.showwarning(
                        "Sin turno activo",
                        "No tienes un turno activo para finalizar.",
                        parent=self.window
                    )
                return
            
            # Confirmar cierre de turno
            if messagebox.askyesno(
                "Confirmar End Shift",
                "¿Deseas finalizar tu turno?\n\nSe registrará el END OF SHIFT.",
                parent=self.window
            ):
                backend_super.on_end_shift(self.username)
                print(f"[DEBUG] END OF SHIFT registrado exitosamente para {self.username}")
                
                # Actualizar controles
                self._update_shift_controls()
                
                # Refrescar módulos
                if hasattr(self, 'daily_module'):
                    self.daily_module.load_data()
                if hasattr(self, 'specials_module'):
                    self.specials_module.load_data()
                if hasattr(self, 'covers_module'):
                    self.covers_module.load_data()
        
        except Exception as e:
            messagebox.showerror(
                "Error",
                f"No se pudo finalizar turno:\n{e}",
                parent=self.window
            )
            print(f"[ERROR] _end_shift: {e}")
            import traceback
            traceback.print_exc()
    
    def _update_shift_controls(self):
        """Actualiza el estado de todos los controles según si hay turno activo"""
        try:
            print(f"[DEBUG] _update_shift_controls: Verificando turno para usuario '{self.username}'")
            has_shift = backend_super.has_active_shift(self.username)
            can_end = backend_super.can_end_shift(self.username)
            
            print(f"[DEBUG] _update_shift_controls: has_shift={has_shift}, can_end={can_end}")
            
            # Estado de botones Start/End Shift
            if has_shift:
                # Hay turno activo
                if self.start_shift_btn:
                    self.start_shift_btn.configure(state='disabled')
                if self.end_shift_btn:
                    if can_end:
                        self.end_shift_btn.configure(state='normal')
                    else:
                        self.end_shift_btn.configure(state='disabled')
                
                # Ocultar label de advertencia
                if self.shift_warning_label:
                    self.shift_warning_label.master.pack_forget()
                
                # Habilitar todos los controles
                if self.add_event_btn:
                    self.add_event_btn.configure(state='normal')
                if self.solicitar_cover_btn:
                    self.solicitar_cover_btn.configure(state='normal')
                if self.registrar_cover_btn:
                    self.registrar_cover_btn.configure(state='normal')
                if self.send_selected_btn:
                    self.send_selected_btn.configure(state='normal')
                if self.send_all_btn:
                    self.send_all_btn.configure(state='normal')
                
                # Habilitar campos del formulario
                self._enable_form_fields(True)
            
            else:
                # NO hay turno activo
                if self.start_shift_btn:
                    self.start_shift_btn.configure(state='normal')
                if self.end_shift_btn:
                    self.end_shift_btn.configure(state='disabled')
                
                # Mostrar label de advertencia
                if self.shift_warning_label:
                    # Encontrar el daily_frame para reinsertar el warning
                    try:
                        daily_frame = self.tab_frames.get("Daily")
                        if daily_frame:
                            self.shift_warning_label.master.pack(fill="x", padx=10, pady=10, before=self.daily_module.parent if hasattr(self, 'daily_module') else None)
                    except:
                        pass
                
                # Deshabilitar todos los controles
                if self.add_event_btn:
                    self.add_event_btn.configure(state='disabled')
                if self.solicitar_cover_btn:
                    self.solicitar_cover_btn.configure(state='disabled')
                if self.registrar_cover_btn:
                    self.registrar_cover_btn.configure(state='disabled')
                if self.send_selected_btn:
                    self.send_selected_btn.configure(state='disabled')
                if self.send_all_btn:
                    self.send_all_btn.configure(state='disabled')
                
                # Deshabilitar campos del formulario
                self._enable_form_fields(False)
        
        except Exception as e:
            print(f"[ERROR] _update_shift_controls: {e}")
            import traceback
            traceback.print_exc()
    
    def _enable_form_fields(self, enable=True):
        """Habilita o deshabilita los campos del formulario"""
        try:
            state = 'normal' if enable else 'disabled'
            
            # Habilitar comboboxes en estado NORMAL (para permitir filtrado por escritura)
            if hasattr(self, 'site_combo'):
                self.site_combo.configure(state='normal' if enable else 'disabled')
            if hasattr(self, 'activity_combo'):
                self.activity_combo.configure(state='normal' if enable else 'disabled')
            
            # Deshabilitar entries
            if hasattr(self, 'quantity_entry'):
                self.quantity_entry.configure(state=state)
            if hasattr(self, 'camera_entry'):
                self.camera_entry.configure(state=state)
            if hasattr(self, 'description_entry'):
                self.description_entry.configure(state=state)
        
        except Exception as e:
            print(f"[ERROR] _enable_form_fields: {e}")
    
    def _start_auto_refresh(self):
        """Inicia el auto-refresh de controles cada 60 segundos"""
        self._auto_refresh_cycle()
    
    def _auto_refresh_cycle(self):
        """Ciclo de auto-refresh recursivo"""
        try:
            # Actualizar controles
            self._update_shift_controls()
            
            # Programar próxima actualización en 60 segundos
            if self.window and self.window.winfo_exists():
                self.refresh_job = self.window.after(60000, self._auto_refresh_cycle)
        
        except Exception as e:
            print(f"[ERROR] _auto_refresh_cycle: {e}")
            # Reintentar de todos modos
            if self.window and self.window.winfo_exists():
                self.refresh_job = self.window.after(60000, self._auto_refresh_cycle)
    
    def _stop_auto_refresh(self):
        """Detiene el auto-refresh"""
        if self.refresh_job:
            try:
                self.window.after_cancel(self.refresh_job)
                self.refresh_job = None
            except Exception as e:
                print(f"[ERROR] _stop_auto_refresh: {e}")
    
    def _on_close(self):
        """
        Handler personalizado para cierre de ventana de operador.
        Ejecuta logout y muestra ventana de login.
        """
        from tkinter import messagebox
        
        if messagebox.askokcancel(
            "Cerrar Sesión",
            f"¿Deseas cerrar sesión de {self.username}?",
            parent=self.window
        ):
            try:
                # Detener auto-refresh
                self._stop_auto_refresh()
                
                # Hacer logout si hay sesión activa
                if self.session_id and self.station:
                    print(f"[DEBUG] Cerrando sesión: {self.username} (ID: {self.session_id})")
                    login.do_logout(self.session_id, self.station, self.window)
                
                # Destruir ventana
                self.window.destroy()
                
                # Mostrar login nuevamente
                try:
                    login.show_login()
                except Exception as e:
                    print(f"[ERROR] Error mostrando login: {e}")
            
            except Exception as e:
                print(f"[ERROR] Error durante cierre: {e}")
                import traceback
                traceback.print_exc()
                # Destruir de todos modos
                try:
                    self.window.destroy()
                except:
                    pass


def open_operator_blackboard(username, session_id, station, root=None):
    """
    Función de entrada para abrir el blackboard de operador.
    
    Args:
        username (str): Nombre del usuario autenticado
        session_id (int): ID de la sesión activa
        station (str): Estación asignada al usuario
        root: Ventana padre (opcional)
    """
    OperatorBlackboard(
        username=username,
        role="Operador",
        session_id=session_id,
        station=station,
        root=root
    )
