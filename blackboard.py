import tkinter as tk
from tkinter import messagebox
from utils.ui_factory import UIFactory



class Blackboard:

    """
    Clase base abstracta para todas las vistas de la aplicación.
    Define la estructura general y ubicación de componentes.
    
    Estructura:
        window
        ├── header_frame     (información del usuario)
        ├── tabs_frame       (navegación entre secciones)
        └── content_area     (contenido dinámico)
    
    Las subclases sobrescriben:
        - _get_window_title()
        - _setup_header_content()
        - _setup_tabs_content()
        - _setup_content()
    """
    
    def __init__(self, username, role, session_id=None, station=None, root=None):
        """
        Inicializa el dashboard base
        
        Args:
            username: Nombre del usuario
            role: Rol del usuario
            session_id: ID de sesión activa
            station: Estación de trabajo
            root: Ventana raíz de tkinter (opcional)
        """
        self.username = username
        self.role = role
        self.session_id = session_id
        self.station = station
        self.root = root
        
        # Setup UI libraries
        self.UI = self._setup_ui_library()
        self.SheetClass = self._setup_sheet_library()
        self.ui_factory = UIFactory(self.UI)
        
        # Estructura común (TODOS los dashboards tienen estos componentes)
        self.window = None
        self.header_frame = None
        self.tabs_frame = None
        self.content_area = None
        
        # Build UI usando template method
        self._build()
    
    def _setup_ui_library(self):
        """Detecta y configura CustomTkinter o retorna None para tkinter"""
        try:
            import importlib
            ctk = importlib.import_module('customtkinter')
            try:
                ctk.set_appearance_mode("dark")
                ctk.set_default_color_theme("dark-blue")
            except:
                pass
            return ctk
        except:
            return None
    
    def _setup_sheet_library(self):
        """Carga tksheet library o muestra error"""
        try:
            from tksheet import Sheet
            return Sheet
        except:
            messagebox.showerror("Error", "tksheet no está instalado.\nInstala con: pip install tksheet")
            return None
    
    # ========== TEMPLATE METHOD - Define el flujo general ==========
    
    def _build(self):
        """
        Template method - define el flujo de construcción del dashboard.
        Este método NO se sobrescribe en subclases.
        """
        self.window = self._create_window()
        self.header_frame = self._create_header()
        self.tabs_frame = self._create_tabs()
        self.content_area = self._create_content_area()
        self._configure_close_handler()
    
    # ========== MÉTODOS GENERALES (misma implementación para todos) ==========
    
    def _create_window(self):
        """Crea ventana toplevel con configuración básica"""
        win = self.ui_factory.toplevel(parent=self.root, bg="#1e1e1e")
        win.title(self._get_window_title())
        win.geometry(self._get_window_geometry())
        win.resizable(True, True)
        return win
    
    def _create_header(self):
        """Crea frame de header - las subclases lo llenan"""
        frame = self.ui_factory.frame(self.window, fg_color="#2c2f33")
        frame.pack(fill="x", padx=10, pady=(10, 5))
        self._setup_header_content(frame)  # Hook para subclases
        return frame
    

    
    def _create_tabs(self):
        """Crea frame de tabs - las subclases lo llenan"""
        frame = self.ui_factory.frame(self.window, fg_color="#23272a")
        frame.pack(fill="x", padx=10, pady=5)
        self._setup_tabs_content(frame)  # Hook para subclases
        return frame
    
    def _create_content_area(self):
        """Crea área de contenido con panel lateral y contenido principal"""
        content_area = self.ui_factory.frame(self.window, fg_color="#1e1e1e")
        content_area.pack(fill="both", expand=True, padx=10, pady=5)

        # Panel lateral (izquierda o derecha)
        lateral_panel = self.ui_factory.frame(content_area, fg_color="#2c2f33", width=60)
        lateral_panel.pack(side="right", fill="y", padx=(10, 0), pady=5)
        self._setup_lateral_panel_content(lateral_panel)

        # Frame principal de contenido
        main_content = self.ui_factory.frame(content_area, fg_color="#1e1e1e")
        main_content.pack(side="left", fill="both", expand=True)
        self._setup_content(main_content)  # Hook para subclases

        return content_area
    
    def _configure_close_handler(self):
        """Configura el handler de cierre de ventana"""
        self.window.protocol("WM_DELETE_WINDOW", self._on_close)
    
    # ========== HOOKS ABSTRACTOS (las subclases DEBEN/PUEDEN implementar) ==========
    
    def _get_window_title(self):
        """
        Sobrescribir en subclases para personalizar título.
        
        Returns:
            str: Título de la ventana
        """
        return f"{self.role} - {self.username}"
    
    def _get_window_geometry(self):
        """
        Sobrescribir en subclases para personalizar tamaño.
        
        Returns:
            str: Geometría de ventana (e.g., "1320x800")
        """
        return "1500x800"
    
    def _setup_header_content(self, parent):
        """
        Sobrescribir en subclases para personalizar header.
        
        Args:
            parent: Frame contenedor del header
        """
        # Implementación por defecto: label simple con usuario
        self.ui_factory.label(
            parent,
            text=f"👤 {self.username}",
            font=("Segoe UI", 14, "bold"),
            fg="#00bfae"
        ).pack(side="left", padx=10)
    
    def _setup_tabs_content(self, parent):
        """
        Sobrescribir en subclases para personalizar tabs.
        
        Args:
            parent: Frame contenedor de los tabs
        """
        # Implementación por defecto: ningún tab
        pass
    
    def _setup_content(self, parent):
        """
        Sobrescribir en subclases para personalizar contenido.
        
        Args:
            parent: Frame contenedor del contenido principal
        """
        # Implementación por defecto: label informativo
        self.ui_factory.label(
            parent,
            text="Dashboard Base - Sobrescribir _setup_content()",
            font=("Segoe UI", 16)
        ).pack(expand=True)
    
    def _on_close(self):
        """
        Sobrescribir en subclases para personalizar cierre.
        Por defecto: confirmación simple.
        """
        if messagebox.askokcancel("Cerrar", "¿Deseas cerrar la ventana?", parent=self.window):
            self.window.destroy()
    
    # ========== MÉTODOS PÚBLICOS (para usar desde fuera) ==========
    
    def show(self):
        """Muestra la ventana del dashboard"""
        if self.window:
            self.window.deiconify()
    
    def hide(self):
        """Oculta la ventana del dashboard"""
        if self.window:
            self.window.withdraw()
    
    def destroy(self):
        """Destruye la ventana del dashboard"""
        if self.window:
            self.window.destroy()
