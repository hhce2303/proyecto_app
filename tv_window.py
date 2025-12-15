



from utils.ui_factory import UIFactory
from views import status_views
from tkinter import messagebox

class TvController:
    def __init__(self, username, role="Supervisor", session_id=None, station=None, root=None):
        """
        Inicializa la ventana de supervisor/lead supervisor
        
        Args:
            username: Nombre del supervisor
            role: Rol del usuario ("Supervisor" o "Lead Supervisor")
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
        if not self.SheetClass:
            return  # No se puede continuar sin tksheet
            
        self.ui_factory = UIFactory(self.UI)
        
        # Variables de estado
        self.current_mode = 'tv'
        self.containers = {}
        self.mode_buttons = {}
        
        # Crear ventana
        self.window = self._create_window()
        
        # Setup componentes
        self._setup_header()
        self._setup_mode_selector()
        self._init_all_containers()
        self._configure_close_handler()
    
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

        def _create_window(self):
            """Crea la ventana principal toplevel"""
            win = self.ui_factory.toplevel(bg="#1e1e1e")
            
            # Título dinámico según rol
            title_prefix =  self.role == "Central Station - SLC 👔"
            win.title(f"{title_prefix} {self.role} - {self.username}")
            
            win.geometry("1320x800")
            win.resizable(True, True)
            return win

        def _setup_header(self):
            """Configura el header con botones y status indicator"""
            header = self.ui_factory.frame(self.window, bg="#23272a", corner_radius=0)
            header.pack(fill="x", padx=0, pady=0)
            
            # Botón Refrescar
            self.refresh_btn = self.ui_factory.button(
                header, "🔄  Refrescar", 
                lambda: self._refresh_current_mode(),
                bg="#4D6068", hover="#27a3e0",
                width=120, height=40,
                font=("Segoe UI", 12, "bold")
            )
            self.refresh_btn.pack(side="left", padx=(20, 5), pady=15)

        def _get_modes_config(self):
            """Retorna la configuración de modos según el rol"""
            base_modes = [

                ('cover_time', '⏱️ Cover Time', 140),
                ('breaks', '☕ Breaks', 130),
                ('news', '📰 News', 130)
                ]

            
            return base_modes

