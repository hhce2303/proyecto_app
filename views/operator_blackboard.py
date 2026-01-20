"""
OperatorBlackboard - Contenedor de tabs para operadores.
Hereda de Blackboard y personaliza para operador.

ENFOQUE ACTUAL: Daily + Specials + Covers con módulos MVC

IMPORTANTE: 
- DAILY = OPERADOR (crear eventos) - ✅ FUNCIONANDO
- SPECIALS = OPERADOR (eventos especiales con timezone) - ✅ FUNCIONANDO
- COVERS = OPERADOR (solicitar/visualizar covers) - ✅ IMPLEMENTADO
"""
from controllers.news_controller import NewsController
from views.blackboard import Blackboard
from views.modules.daily_module import DailyModule
from views.modules.specials_module import SpecialsModule
from views.modules.covers_module import CoversModule
from views.modules.operator_modules.lateral_panel_content import LateralPanelContent
from controllers.daily_controller import DailyController
from tkinter import messagebox
import login
import backend_super
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
        self.controller = DailyController(username, window=root, current_tab=self.current_tab)
        self.news_controller = NewsController(username)
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
        self.night_alert_job = None  # Job para alertas nocturnas
        
        super().__init__(username, role, session_id, station, root)
    
    def _build(self):
        """Sobrescribe _build para inicializar estado de shift después de construir"""
        # Llamar al build del padre
        super()._build()
        
        # Inicializar estado de controles según shift activo
        self._update_shift_controls()
        
        # Iniciar auto-refresh
        self._start_auto_refresh()
        
        # Iniciar sistema de alertas nocturnas
        self._start_night_alerts()
    
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
            text="🏁 Finalizar Turno",
            command=self._end_shift,
            width=130,
            fg_color="#d32f2f",
            hover_color="#b71c1c"
        )
        self.end_shift_btn.pack(side="right", padx=(5, 10), pady=10)
        
        # Botón Start Shift (derecha)
        self.start_shift_btn = self.ui_factory.button(
            parent,
            text="🚀 Iniciar Turno",
            command=self._start_shift,
            width=130,
            fg_color="#087c38",
            hover_color="#096e33"
        )
        self.start_shift_btn.pack(side="right", padx=(10, 5), pady=10)
        
        # Botón Registrar Cover
        self.registrar_cover_btn = self.ui_factory.button(
            parent,
            text="✍️ Registrar Cover",
            command=self._register_cover,
            width=150,
            fg_color="#4D6068",
            hover_color="#0d679b"
        )
        self.registrar_cover_btn.pack(side="right", padx=(5, 10), pady=10)
        
        # Botón Solicitar Cover
        self.solicitar_cover_btn = self.ui_factory.button(
            parent,
            text="🙋 Solicitar Cover",
            command=self._request_cover,
            width=150,
            fg_color="#4D6068",
            hover_color="#0d679b"
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
        """Crea el layout horizontal: panel lateral + área principal de contenido"""
        # Frame contenedor horizontal
        content_container = self.ui_factory.frame(parent, fg_color="transparent")
        content_container.pack(fill="both", expand=True)

        # Área principal de contenido (tabs)
        main_content = self.ui_factory.frame(content_container, fg_color="#1e1e1e")
        main_content.pack(side="left", fill="both", expand=True)
        
        # ========== TAB DAILY (EXCLUSIVO DE OPERADORES) ==========
        daily_frame = self.ui_factory.frame(main_content, fg_color="#1e1e1e")

        self.lateral_panel = self.ui_factory.frame(content_container, fg_color="#2c2f33", width=60)
        self.lateral_panel.pack(side="right", fill="y", padx=(10, 0), pady=5)
        self.lateral_panel.pack_propagate(False)  # Mantener ancho fijo


        # --- Expansión/colapso con eventos de mouse ---
        self.lateral_panel.configure(width=60)
        self._lateral_expanded_width = 220
        self._lateral_collapsed_width = 60
        self._lateral_collapse_job = None  # Job ID para el collapse con delay
        self._lateral_is_expanded = False  # Estado actual

        def _expand_panel(event):
            # Cancelar cualquier collapse pendiente
            if self._lateral_collapse_job:
                try:
                    (self.root or self.window).after_cancel(self._lateral_collapse_job)
                    self._lateral_collapse_job = None
                except:
                    pass
            
            # Solo expandir si no está ya expandido
            if not self._lateral_is_expanded:
                self._lateral_is_expanded = True
                self.lateral_panel.configure(width=self._lateral_expanded_width)

        def _collapse_panel(event):
            # Cancelar cualquier collapse pendiente anterior
            if self._lateral_collapse_job:
                try:
                    (self.root or self.window).after_cancel(self._lateral_collapse_job)
                except:
                    pass
            
            # Programar collapse con delay de 200ms
            def do_collapse():
                try:
                    # Verificar si el mouse está fuera del panel
                    x, y = self.lateral_panel.winfo_pointerxy()
                    abs_x = self.lateral_panel.winfo_rootx()
                    abs_y = self.lateral_panel.winfo_rooty()
                    
                    # Solo colapsar si el mouse está realmente fuera
                    if not (abs_x <= x <= abs_x + self.lateral_panel.winfo_width() and 
                            abs_y <= y <= abs_y + self.lateral_panel.winfo_height()):
                        self._lateral_is_expanded = False
                        self.lateral_panel.configure(width=self._lateral_collapsed_width)
                    
                    self._lateral_collapse_job = None
                except:
                    pass
            
            # Programar el collapse con delay
            self._lateral_collapse_job = (self.root or self.window).after(200, do_collapse)

        self.lateral_panel.bind("<Enter>", _expand_panel)
        self.lateral_panel.bind("<Leave>", _collapse_panel)

        # Función para vincular eventos recursivamente
        def bind_hover_to_children(widget):
            """Vincula eventos de hover a un widget y todos sus hijos recursivamente"""
            try:
                widget.bind("<Enter>", _expand_panel)
                widget.bind("<Leave>", _collapse_panel)
                # Recursión en todos los hijos
                for child in widget.winfo_children():
                    bind_hover_to_children(child)
            except:
                pass

        # Panel para mostrar varios frames con información
        try:
            self.lateral_panel_content = LateralPanelContent(
                parent=self.lateral_panel,
                username=self.username,
                ui_factory=self.ui_factory,
                UI=self.UI
            )
            self.lateral_panel_content.blackboard = self
            
            # Guardar referencia a la función para que pueda ser llamada después
            self._bind_lateral_hover = lambda: [bind_hover_to_children(child) for child in self.lateral_panel.winfo_children()]
            
            # Aplicar a todos los hijos del lateral_panel inicialmente
            self._bind_lateral_hover()

            print(f"[DEBUG] LateralPanelContent inicializado para OPERADOR: {self.username}")
            
        except Exception as e:
            print(f"[ERROR] No se pudo inicializar LateralPanelContent: {e}")


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

        

        # ========= DailyModule (tabla de eventos) ==========

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
        
        self.tab_frames["Daily"] = daily_frame
        
        # ========== TAB SPECIALS (OPERADOR - EVENTOS ESPECIALES) ==========
        specials_frame = self.ui_factory.frame(main_content, fg_color="#1e1e1e")
        
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
        
        self.tab_frames["Specials"] = specials_frame
        
        # ========== TAB COVERS (MVC COMPLETO) ==========
        covers_frame = self.ui_factory.frame(main_content, fg_color="#23272a")
        
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
        covers_list_frame = self.ui_factory.frame(main_content, fg_color="#23272a")
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
        try:
            self.controller.request_cover(
                username=self.username)

        except Exception as e:
            messagebox.showerror(
                "Error",
                f"No se pudo solicitar el cover:\n{e}",
            )
            print(f"[ERROR] _request_cover: {e}")
            import traceback
            traceback.print_exc()
    
    def _register_cover(self):
        self.controller.register_covers(
            username=self.username,
            window=self.window,
            ui_factory=self.ui_factory,
            station=self.station,
            UI=self.UI if hasattr(self, 'UI') else None
        )
        
    def _on_logout(self):
        """Handler de logout"""

        if messagebox.askyesno("Logout", "¿Cerrar sesión?", parent=self.window):
            self.window.destroy()
    
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
                    hours_remaining = 9.0 - hours_elapsed
                    
                    messagebox.showwarning(
                        "Turno Incompleto",
                        f"Debes completar al menos 9 horas de turno.\n\n"
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
                login.do_logout(session_id=self.session_id, root=self.window, station=self.station)
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
    
    def _start_night_alerts(self):
        """Inicia el sistema de alertas nocturnas cada 30 minutos"""
        # Esperar 2 segundos para asegurar que la ventana está completamente inicializada
        window = self.root or self.window
        if window and window.winfo_exists():
            window.after(2000, self._schedule_next_night_alert)
            print("[DEBUG] Sistema de alertas nocturnas iniciado")
    
    def _schedule_next_night_alert(self):
        """Calcula y programa la próxima alerta nocturna"""
        try:
            from datetime import datetime, timedelta
            
            now = datetime.now()
            current_hour = now.hour
            current_minute = now.minute
            
            # Calcular próxima alerta a las :37 o :57
            if current_minute < 37:
                next_alert_minute = 37
                next_alert_hour = current_hour
            elif current_minute < 57:
                next_alert_minute = 57
                next_alert_hour = current_hour
            else:
                next_alert_minute = 37
                next_alert_hour = (current_hour + 1) % 24
            
            # Crear datetime de la próxima alerta
            next_alert = now.replace(
                hour=next_alert_hour,
                minute=next_alert_minute,
                second=0,
                microsecond=0
            )
            
            # Si la hora calculada es menor que la actual, es del día siguiente
            if next_alert <= now:
                next_alert += timedelta(days=1)
            
            # Calcular milisegundos hasta la próxima alerta
            time_until_alert = (next_alert - now).total_seconds() * 1000
            
            print(f"[DEBUG] Próxima alerta programada para: {next_alert.strftime('%Y-%m-%d %H:%M:%S')} (en {time_until_alert/1000:.1f} segundos)")
            
            # Programar la alerta
            window = self.root or self.window
            if window and window.winfo_exists():
                self.night_alert_job = window.after(
                    int(time_until_alert),
                    self._check_and_show_night_alert
                )
                print(f"[DEBUG] Alert job programado con ID: {self.night_alert_job}")
        
        except Exception as e:
            print(f"[ERROR] _schedule_next_night_alert: {e}")
    
    def _check_and_show_night_alert(self):
        """Verifica si es horario nocturno y muestra la alerta"""
        try:
            from datetime import datetime
            
            now = datetime.now()
            current_hour = now.hour
            
            # Verificar si estamos en horario nocturno (21:00-08:00)
            # 21:00 = 9 PM, 08:00 = 8 AM
            is_night_time = current_hour >= 21 or current_hour < 8
            
            if is_night_time:
                print(f"[DEBUG] Mostrando alerta nocturna a las {now.strftime('%H:%M:%S')}")
                self._show_night_alert_popup()
            else:
                print(f"[DEBUG] Fuera de horario nocturno ({now.strftime('%H:%M:%S')}), alerta omitida")
            
            # Programar siguiente alerta (cada 30 minutos)
            self._schedule_next_night_alert()
        
        except Exception as e:
            print(f"[ERROR] _check_and_show_night_alert: {e}")
            # Reprogramar de todos modos
            self._schedule_next_night_alert()
    
    def _show_night_alert_popup(self):
        """Muestra popup de alerta nocturna"""
        try:
            from datetime import datetime
       
        # Crear ventana de alerta
            alert_win = self.ui_factory.toplevel(self.window)
            alert_win.configure(fg_color="#1a1a1a")

            alert_win.title("⏰ Recordatorio")
            alert_win.geometry("500x280")
            alert_win.resizable(False, False)
            alert_win.transient(self.window)
            alert_win.grab_set()
            
            # Centrar ventana
            alert_win.update_idletasks()
            x = (alert_win.winfo_screenwidth() // 2) - (500 // 2)
            y = (alert_win.winfo_screenheight() // 2) - (280 // 2)
            alert_win.geometry(f"500x280+{x}+{y}")
            
            # Forzar que la ventana esté al frente y centrada respecto a la principal
            alert_win.lift()
            alert_win.attributes('-topmost', True)
            alert_win.focus_force()
            # Centrar respecto a la ventana principal (no solo pantalla)
            parent = self.window
            parent.update_idletasks()
            x = parent.winfo_x() + (parent.winfo_width() // 2) - (500 // 2)
            y = parent.winfo_y() + (parent.winfo_height() // 2) - (280 // 2)
            alert_win.geometry(f"500x280+{x}+{y}")
            
            # Contenido
  
            # Header con ícono y hora actual
            header = self.ui_factory.frame(alert_win, fg_color="#ff6b35", corner_radius=0, height=80)
            header.pack(fill="x")
            header.pack_propagate(False)
            
            self.ui_factory.label(
                header,
                text="⏰",
                font=("Segoe UI", 48)
            ).pack(pady=10)
            
            # Mensaje principal
            content = self.UI.CTkFrame(alert_win, fg_color="transparent")
            content.pack(fill="both", expand=True, padx=30, pady=20)
            
            current_time = datetime.now().strftime("%I:%M %p")
                
            self.ui_factory.label(
                    content,
                    text=f"Son las {current_time}",
                    font=("Segoe UI", 20, "bold"),
                    text_color="#ffffff"
                ).pack(pady=(10, 5))
                
            self.ui_factory.label(
                content,
                text="Tours",
                font=("Segoe UI", 14),
                text_color="#b0b0b0"
            ).pack(pady=(0, 20))
                
            # Botón cerrar
            self.ui_factory.button(
                content,
                text="✅ Entendido",
                command=alert_win.destroy,
                fg_color="#00c853",
                hover_color="#00a043",
                font=("Segoe UI", 14, "bold"),
                width=200,
                height=45
            ).pack(pady=10)
            
            # Auto-cerrar después de 10 segundos
            alert_win.after(40000, lambda: alert_win.destroy() if alert_win.winfo_exists() else None)
            
        except Exception as e:
            print(f"[ERROR] _show_night_alert_popup: {e}")
    
    def _stop_night_alerts(self):
        """Detiene el sistema de alertas nocturnas"""
        if self.night_alert_job:
            try:
                self.window.after_cancel(self.night_alert_job)
                self.night_alert_job = None
                print("[DEBUG] Sistema de alertas nocturnas detenido")
            except Exception as e:
                print(f"[ERROR] _stop_night_alerts: {e}")
    
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
                # Detener alertas nocturnas
                self._stop_night_alerts()
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
