import tkinter as tk
from tkinter import messagebox
import login
from utils.ui_factory import UIFactory
from views.blackboard import Blackboard
from views.modules.admin_modules.dashboard_module import DashboardModule
from views.modules.admin_modules.healthcheck_admin_module import AdminHCModules
from views.modules.healthcheck_module import HealthcheckModule






class AdminBlackboard(Blackboard):
    """Clase que representa el tablero de administración, hereda de Blackboard."""
    
    def __init__(self, username, role, session_id=None, station=None, root=None):

        self.current_tab = "Dashboard"
        self.tab_buttons = {}
        self.tab_frames = {}

        super().__init__(username, role, session_id, station, root)

    def _build(self):
        """Sobrescribe _build para inicializar estado de shift después de construir"""
        # Llamar al build del padre
        super()._build()

        # Iniciar auto-refresh
        self._start_auto_refresh()

    def _setup_header(self, parent):
        """Header de Admin: Usuario, Rol, Estación, Sesión"""
        header = self.ui_factory.frame(parent, fg_color="#2C2F33", height=50)
        header.pack(fill="x")

        title_label = self.ui_factory.label(
            parent,
            text=f"🔐 Panel de Administración - {self.username}",
            font=("Arial", 20, "bold")
        )
        title_label.pack(side='left', padx=20, pady=15)

    def _setup_tabs_content(self, parent):
        """Tabs de Admin: Dashboard, Users, Sessions, Reports, Settings"""
        # Tabs (izquierda)
        tabs = [
            ("📶Dashboard", "Dashboard"),
            ("👥Users", "Users"),
            ("📋Sessions", "Sessions"),
            ("📊HealthCheck", "HealthCheck"),
            ("⚙️Settings", "Settings")
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


    def _setup_content(self, parent):
        """Contenido de Admin: Área dinámica según tab seleccionado"""

        self.main_container = self.ui_factory.frame(parent, fg_color="#000000")
        self.main_container.pack(fill="both", expand=True)

        self.blackframe_bg = self.ui_factory.frame(self.main_container, fg_color="#000000")
        self.blackframe_bg.pack(fill="both", expand=True, padx=10, pady=10)
    
        dashboard_frame = self.ui_factory.frame(self.blackframe_bg, fg_color="#000000")
        try:
            self.dashboard_module = DashboardModule(
                container=dashboard_frame,
                username=self.username,
                ui_factory=self.ui_factory,
                UI=self.UI
            )
        except Exception as e:
            print(f"[ERROR] No se pudo cargar el módulo Dashboard: {e}")

        self.tab_frames["Dashboard"] = dashboard_frame

        healthcheck_frame = self.ui_factory.frame(self.blackframe_bg, fg_color="#000000")

        try:
            
            self.healthcheck_module = AdminHCModules(
                container=healthcheck_frame,
                username=self.username,
                ui_factory=self.ui_factory,
                UI=self.UI
            )
        except Exception as e:
            print(f"[ERROR] No se pudo cargar el módulo HealthCheck: {e}")

        self.tab_frames["HealthCheck"] = healthcheck_frame
    
    def _switch_tab(self, tab_name):
        """Cambia entre tabs y recarga datos"""
        if self.current_tab != tab_name:
            self.current_tab = tab_name
            self._show_current_tab()
            self._update_tab_buttons()
            
            # Recargar datos del módulo al cambiar de tab
            if tab_name == "Dashboard" and hasattr(self, 'dashboard_module'):
                self.dashboard_module.refresh_dashboard()


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

    def _start_auto_refresh(self):
        """Inicia el auto-refresh de controles cada 60 segundos"""
        self._auto_refresh_cycle()

    def _stop_auto_refresh(self):
        """Detiene el auto-refresh"""
        if self.refresh_job:
            try:
                self.window.after_cancel(self.refresh_job)
                self.refresh_job = None
            except Exception as e:
                print(f"[ERROR] _stop_auto_refresh: {e}")

    def _auto_refresh_cycle(self):
        """Ciclo de auto-refresh recursivo"""
        try:
            # Programar próxima actualización en 60 segundos
            if self.window and self.window.winfo_exists():
                self.refresh_job = self.window.after(60000, self._auto_refresh_cycle)
        
        except Exception as e:
            print(f"[ERROR] _auto_refresh_cycle: {e}")
            # Reintentar de todos modos
            if self.window and self.window.winfo_exists():
                self.refresh_job = self.window.after(60000, self._auto_refresh_cycle)

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

def open_admin_blackboard(username, session_id, station, root=None):
    """
    Función de entrada para abrir el blackboard de administrador.
    
    Args:
        username (str): Nombre del usuario autenticado
        session_id (int): ID de la sesión activa
        station (str): Estación asignada al usuario
        root: Ventana padre (opcional)
    """
    AdminBlackboard(
        username=username,
        role="Admin",
        session_id=session_id,
        station=station,
        root=root
    )