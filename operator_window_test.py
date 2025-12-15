
import backend_super
from views import status_views
from tkinter import messagebox


from utils.ui_factory import UIFactory


class OperatorWindowTest:
    def __init__(self, username, role="Operador", session_id=None, station=None, root=None):
        """
        Inicializa la ventana de Operador
        
        Args:
            username (str): Nombre del usuario
            role (str): Rol del usuario
            session_id (int): ID de sesión
            station (int): Estación asignada
            root: Ventana raíz de Tkinter
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
        self.current_mode = 'Daily'  # Modo inicial
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
        title_prefix = "👔" if self.role == "Operador" else "📊"
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
        
        # Botón Eliminar
        self.delete_btn = self.ui_factory.button(
            header, "🗑️ Eliminar",
            lambda: backend_super.safe_delete(),
            bg="#d32f2f", hover="#b71c1c",
            width=120, height=40,
            font=("Segoe UI", 12, "bold")
        )
        self.delete_btn.pack(side="left", padx=5, pady=15)
        
        # Status indicator
        status_views.render_status_header(
            parent_frame=header,
            username=self.username,
            controller=None,
            UI=self.UI
        )

    def _setup_mode_selector(self):
        """Configura el selector de modo (Daily, Specials, Covers)"""
        modes = ["Daily", "Specials", "Covers"]
        mode_frame = self.ui_factory.frame(self.window, bg="#2c2f33", corner_radius=0)
        mode_frame.pack(fill="x", padx=0, pady=0)
        
        for mode in modes:
            btn = self.ui_factory.button(
                mode_frame, mode,
                lambda m=mode: self._switch_mode(m),
                bg="#4D6068", hover="#27a3e0",
                width=120, height=40,
                font=("Segoe UI", 12, "bold")
            )
            btn.pack(side="left", padx=10, pady=10)
            self.mode_buttons[mode] = btn

    def _init_all_containers(self):
        """Inicializa todos los containers pero muestra solo el actual"""
        modes = ["Daily", "Specials", "Covers"]
        for mode in modes:
            container = self.ui_factory.frame(self.window, bg="#36393f", corner_radius=0)
            container.pack(fill="both", expand=True)
            self.containers[mode] = container
            if mode == self.current_mode:
                container.lift()
            else:
                container.lower()
        
        # Inicializar contenido de cada container
        self._init_daily_container()
        self._init_specials_container()
        self._init_covers_container()


if __name__ == "__main__":
    # Prueba de la ventana de operador
    test_window = OperatorWindowTest(
        username="prueba",
        role="Operador",
        session_id=12345,
        station=1,
        root=None
    )