"""
Supervisor Window - Ventana principal de supervisores

Arquitectura MVC:
- Clase SupervisorWindow maneja la ventana y navegación entre módulos
- Cada módulo (Specials, Audit, Breaks, etc.) tiene su propio MVC
- UIFactory abstrae la creación de widgets UI/Tkinter
"""

import tkinter as tk
from tkinter import messagebox
import traceback

# Backend core
import backend_super
import login
from backend_super import (
    Dinamic_button_Shift,
    on_start_shift,
    on_end_shift,
    _focus_singleton,
    get_user_status
)

# Views
from views.specials_view import render_specials_container
from views.audit_view import render_audit_container
from views.breaks_view import render_breaks_container
from views.cover_time_view import render_cover_time_container
from views.rol_cover_view import render_rol_cover_container
from views.news_view import render_news_container
from views import status_views

# Controllers
from controllers.status_controller import StatusController
from controllers.news_controller import NewsController

# Utils
from utils.ui_factory import UIFactory
import under_super






class SupervisorWindow:
    """
    Ventana principal de supervisores con arquitectura MVC
    
    Maneja la navegación entre módulos (Specials, Audit, Breaks, etc.)
    y delega la lógica de negocio a los controladores correspondientes.
    """
    
    def __init__(self, username, session_id=None, station=None, root=None):
        """
        Inicializa la ventana de supervisor
        
        Args:
            username: Nombre del supervisor
            session_id: ID de sesión (para logout)
            station: Estación de trabajo
            root: Ventana root (opcional)
        """
        self.username = username
        self.session_id = session_id
        self.station = station
        self.root = root
        
        # Setup UI libraries
        self.UI = self._setup_ui_library()
        self.SheetClass = self._setup_sheet_library()
        self.ui_factory = UIFactory(self.UI)
        
        # Crear ventana
        self.window = self._create_window()
        
        # Contenedores de módulos
        self.containers = {}
        self.current_mode = 'specials'
        self.mode_buttons = {}
        
        # Referencias a widgets y funciones
        self.specials_load_data = None
        
        # Setup UI
        self._setup_header()
        self._setup_mode_selector()
        self._init_all_containers()
        self._configure_close_handler()
    
    def _setup_ui_library(self):
        """Detecta y configura CustomTkinter o retorna None para Tkinter"""
        try:
            import importlib
            ctk = importlib.import_module('customtkinter')
            try:
                ctk.set_appearance_mode("dark")
                ctk.set_default_color_theme("dark-blue")
            except Exception:
                pass
            return ctk
        except Exception:
            return None
    
    def _setup_sheet_library(self):
        """Verifica e importa tksheet"""
        try:
            from tksheet import Sheet as _Sheet
            return _Sheet
        except Exception:
            messagebox.showerror("Error", "tksheet no está instalado.\nInstala con: pip install tksheet")
            return None
    
    def _create_window(self):
        """Crea la ventana principal Toplevel"""
        if self.UI:
            win = self.UI.CTkToplevel()
            win.configure(fg_color="#1e1e1e")
        else:
            win = tk.Toplevel()
            win.configure(bg="#1e1e1e")
        
        win.title(f"📊 Specials - {self.username}")
        win.geometry("1320x800")
        win.resizable(True, True)
        
        return win
    
    def _setup_header(self):
        """Configura el header con botones de acción y status"""
        header = self.ui_factory.frame(self.window, bg="#23272a")
        header.pack(fill="x", padx=0, pady=0)
        
        # Botón Refrescar
        refresh_btn = self.ui_factory.button(
            header,
            "🔄  Refrescar",
            self._refresh_current_mode,
            bg="#4D6068",
            hover="#27a3e0",
            width=120,
            height=40,
            font=("Segoe UI", 12, "bold")
        )
        refresh_btn.pack(side="left", padx=(20, 5), pady=15)
        
        # Botón Eliminar
        delete_btn = self.ui_factory.button(
            header,
            "🗑️ Eliminar",
            self._delete_selected,
            bg="#d32f2f",
            hover="#b71c1c",
            width=120,
            height=40,
            font=("Segoe UI", 12, "bold")
        )
        delete_btn.pack(side="left", padx=5, pady=15)
        
        # Indicador de status
        status_views.render_status_header(
            parent_frame=header,
            username=self.username,
            controller=None,
            UI=self.UI
        )
    
    def _setup_mode_selector(self):
        """Configura los botones de selección de modo (tabs)"""
        mode_frame = self.ui_factory.frame(self.window, bg="#23272a", height=50)
        mode_frame.pack(fill="x", padx=0, pady=0)
        mode_frame.pack_propagate(False)
        
        # Definir modos
        modes = [
            ('specials', '📋 Specials', 130),
            ('audit', '📊 Audit', 130),
            ('cover_time', '⏱️ Cover Time', 140),
            ('breaks', '☕ Breaks', 130),
            ('rol_cover', '🎭 Rol de Cover', 150),
            ('news', '📰 News', 130)
        ]
        
        # Crear botones
        for mode_id, label, width in modes:
            btn = self.ui_factory.button(
                mode_frame,
                label,
                lambda m=mode_id: self.switch_mode(m),
                bg="#4a90e2" if mode_id == 'specials' else "#3b4754",
                hover="#357ABD" if mode_id == 'specials' else "#4a5560",
                width=width,
                height=35,
                font=("Segoe UI", 12, "bold")
            )
            btn.pack(side="left", padx=(20, 5) if mode_id == 'specials' else 5, pady=8)
            self.mode_buttons[mode_id] = btn
    
    def _init_all_containers(self):
        """Inicializa todos los contenedores de módulos con sus vistas MVC"""
        # Specials
        specials_widgets = render_specials_container(
            parent=self.window,
            username=self.username,
            UI=self.UI,
            SheetClass=self.SheetClass
        )
        self.containers['specials'] = specials_widgets
        self.specials_load_data = specials_widgets['refresh']
        
        # Agregar botón "Otros Specials"
        self._add_otros_specials_button(
            specials_widgets['marks_frame'],
            specials_widgets['controller']
        )
        
        # Audit
        audit_widgets = render_audit_container(
            parent=self.window,
            UI=self.UI,
            SheetClass=self.SheetClass
        )
        self.containers['audit'] = audit_widgets
        
        # Breaks
        breaks_widgets = render_breaks_container(
            parent=self.window,
            username=self.username,
            UI=self.UI,
            SheetClass=self.SheetClass,
            under_super=under_super
        )
        self.containers['breaks'] = breaks_widgets
        
        # Cover Time
        cover_time_widgets = render_cover_time_container(
            parent=self.window,
            UI=self.UI,
            SheetClass=self.SheetClass
        )
        self.containers['cover_time'] = cover_time_widgets
        
        # Rol de Cover
        rol_cover_widgets = render_rol_cover_container(
            parent=self.window,
            UI=self.UI
        )
        self.containers['rol_cover'] = rol_cover_widgets
        
        # News
        news_controller = NewsController(self.username)
        news_widgets = render_news_container(
            top=self.window,
            username=self.username,
            controller=news_controller,
            UI=self.UI
        )
        self.containers['news'] = news_widgets
    
    def _add_otros_specials_button(self, marks_frame, specials_controller):
        """Agrega el botón de 'Otros Specials' al frame de marcas"""
        from views.otros_specials_view import open_otros_specials_window
        
        btn = self.ui_factory.button(
            marks_frame,
            "📋 Otros Specials",
            lambda: open_otros_specials_window(
                self.window,
                self.username,
                specials_controller,
                self.UI,
                self.SheetClass,
                self.specials_load_data
            ),
            bg="#4a5f7a",
            hover="#3a4f6a",
            width=150,
            height=35,
            font=("Segoe UI", 11, "bold")
        )
        btn.pack(side="left", padx=5, pady=10)
    
    def switch_mode(self, new_mode):
        """
        Cambia entre modos ocultando/mostrando containers
        
        Args:
            new_mode: ID del modo ('specials', 'audit', etc.)
        """
        self.current_mode = new_mode
        
        # Ocultar todos los containers
        for mode_id, widgets in self.containers.items():
            widgets['container'].pack_forget()
        
        # Resetear colores de botones
        inactive_color = "#3b4754"
        inactive_hover = "#4a5560"
        active_color = "#4a90e2"
        active_hover = "#357ABD"
        
        for mode_id, btn in self.mode_buttons.items():
            if self.UI:
                btn.configure(
                    fg_color=active_color if mode_id == new_mode else inactive_color,
                    hover_color=active_hover if mode_id == new_mode else inactive_hover
                )
            else:
                btn.configure(
                    bg=active_color if mode_id == new_mode else inactive_color,
                    activebackground=active_hover if mode_id == new_mode else inactive_hover
                )
        
        # Mostrar container activo
        self.containers[new_mode]['container'].pack(fill="both", expand=True, padx=10, pady=10)
        
        # Cargar datos si es Specials
        if new_mode == 'specials' and self.specials_load_data:
            self.specials_load_data()
    
    def _refresh_current_mode(self):
        """Refresca los datos del modo actual"""
        if self.current_mode == 'specials' and self.specials_load_data:
            self.specials_load_data()
        elif 'refresh' in self.containers.get(self.current_mode, {}):
            self.containers[self.current_mode]['refresh']()
    
    def _delete_selected(self):
        """Elimina elementos seleccionados en el modo actual"""
        # Delegar a backend_super que ya tiene la lógica
        backend_super.safe_delete()
    
    def _configure_close_handler(self):
        """Configura el handler de cierre de ventana"""
        def on_close():
            try:
                if self.session_id and self.station:
                    login.do_logout(self.session_id, self.station, self.window)
                if not self.session_id:
                    try:
                        login.show_login()
                        self.window.destroy()
                    except Exception as e:
                        print(f"[ERROR] Error during logout: {e}")
            except Exception as e:
                print(f"[ERROR] Error destroying window: {e}")
        
        self.window.protocol("WM_DELETE_WINDOW", on_close)
    
    def show(self):
        """
        Muestra la ventana e inicia en modo Specials
        
        Returns:
            Referencia a la ventana Toplevel
        """
        self.switch_mode('specials')
        return self.window


def open_hybrid_events_supervisor(username, session_id=None, station=None, root=None):
    """
    Función de entrada para abrir la ventana de supervisor
    
    Mantiene backward compatibility con código existente.
    Ahora delega a la clase SupervisorWindow.
    
    Args:
        username: Nombre del supervisor
        session_id: ID de sesión (para logout)
        station: Estación de trabajo
        root: Ventana root (opcional)
        
    Returns:
        Referencia a la ventana Toplevel creada
    """
    # Singleton check
    ex = _focus_singleton('hybrid_events_supervisor')
    if ex:
        return ex
    
    # Crear instancia de la clase y mostrar ventana
    window = SupervisorWindow(username, session_id, station, root)
    return window.show()

