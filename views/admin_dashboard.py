"""
AdminDashboard - Dashboard específico para administradores.
Hereda de Dashboard con acceso completo a todas las funcionalidades.
"""
from views.dashboard import Dashboard


class AdminDashboard(Dashboard):
    """
    Dashboard para Administradores.
    Incluye acceso a: Users, Sites, Activities, Reports, Config
    """
    
    def __init__(self, username, role, session_id=None, station=None, root=None):
        """Inicializa dashboard de admin"""
        self.current_tab = "Users"
        self.tab_buttons = {}
        self.tab_frames = {}
        
        super().__init__(username, role, session_id, station, root)
    
    def _get_window_title(self):
        """Título específico para admins"""
        return f"👑 Admin Panel - {self.username}"
    
    def _get_window_geometry(self):
        """Ventana más grande para admins"""
        return "1400x900"
    
    def _setup_header_content(self, parent):
        """Header con permisos totales"""
        self.ui_factory.label(
            parent,
            text=f"👑 Administrator: {self.username}",
            font=("Segoe UI", 14, "bold"),
            fg="#ffd700"  # Dorado para admin
        ).pack(side="left", padx=10)
        
        # Botón de logout
        self.ui_factory.button(
            parent,
            text="🚪 Logout",
            command=self._on_logout,
            width=100,
            fg_color="#d32f2f",
            hover_color="#b71c1c"
        ).pack(side="right", padx=10)
    
    def _setup_tabs_content(self, parent):
        """Tabs completos para admin"""
        tabs = [
            ("👥 Users", "Users"),
            ("📍 Sites", "Sites"),
            ("📋 Activities", "Activities"),
            ("📊 Reports", "Reports"),
            ("⚙️ Config", "Config")
        ]
        
        for text, tab_name in tabs:
            btn = self.ui_factory.button(
                parent,
                text=text,
                command=lambda t=tab_name: self._switch_tab(t),
                width=120,
                fg_color="#4D6068"
            )
            btn.pack(side="left", padx=5)
            self.tab_buttons[tab_name] = btn
        
        self._update_tab_buttons()
    
    def _setup_content(self, parent):
        """Contenido administrativo"""
        tabs = ["Users", "Sites", "Activities", "Reports", "Config"]
        
        for tab_name in tabs:
            frame = self.ui_factory.frame(parent, fg_color="#23272a")
            
            self.ui_factory.label(
                frame,
                text=f"Panel de {tab_name}",
                font=("Segoe UI", 18, "bold"),
                fg="#ffd700"
            ).pack(pady=20)
            
            self.ui_factory.label(
                frame,
                text="Aquí irá la gestión administrativa",
                font=("Segoe UI", 12),
                fg="#999999"
            ).pack(pady=10)
            
            self.tab_frames[tab_name] = frame
        
        self._show_current_tab()
    
    def _switch_tab(self, tab_name):
        """Cambia entre tabs"""
        if self.current_tab != tab_name:
            self.current_tab = tab_name
            self._show_current_tab()
            self._update_tab_buttons()
    
    def _show_current_tab(self):
        """Muestra tab actual"""
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
        if messagebox.askyesno("Logout", "¿Cerrar sesión de admin?", parent=self.window):
            self.window.destroy()
    
    def _on_close(self):
        """Handler de cierre"""
        from tkinter import messagebox
        if messagebox.askokcancel("Cerrar", "¿Cerrar panel de administración?", parent=self.window):
            self.window.destroy()
