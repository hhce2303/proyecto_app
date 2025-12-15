"""
OperatorDashboard - Dashboard específico para operadores.
Hereda de Dashboard y personaliza para acceso limitado.

IMPORTANTE: 
- DAILY = OPERADOR (crear y gestionar eventos regulares)
- SPECIALS = OPERADOR (crear eventos especiales)
- Supervisores solo REVISAN Specials, NO los crean
"""
from views.dashboard import Dashboard
from views.modules.daily_module import DailyModule


class OperatorDashboard(Dashboard):
    """
    Dashboard para Operadores.
    Incluye acceso a: Daily (crear eventos), Specials (crear eventos especiales), Covers
    """
    
    def __init__(self, username, role, session_id=None, station=None, root=None):
        """Inicializa dashboard de operador"""
        self.current_tab = "Daily"
        self.tab_buttons = {}
        self.tab_frames = {}
        
        super().__init__(username, role, session_id, station, root)
    
    def _get_window_title(self):
        """Título específico para operadores"""
        return f"👷 Operator - {self.username}"
    
    def _setup_header_content(self, parent):
        """Header simplificado para operadores"""
        header_text = f"👤 {self.username}"
        if self.station:
            header_text += f" | 🖥️ {self.station}"
        
        self.ui_factory.label(
            parent,
            text=header_text,
            font=("Segoe UI", 14, "bold"),
            fg="#00bfae"
        ).pack(side="left", padx=10)
        
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
        try:
            self.daily_module = DailyModule(
                parent=daily_frame,
                username=self.username,
                session_id=self.session_id,
                role=self.role,
                UI=self.UI
            )
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
        
        # ========== TAB SPECIALS (OPERADOR CREA EVENTOS ESPECIALES) ==========
        specials_frame = self.ui_factory.frame(parent, fg_color="#23272a")
        self.ui_factory.label(
            specials_frame,
            text="Contenido de Specials",
            font=("Segoe UI", 18, "bold"),
            fg="#ffa500"
        ).pack(pady=20)
        self.ui_factory.label(
            specials_frame,
            text="Operador crea eventos especiales aquí (SpecialsModule pendiente)",
            font=("Segoe UI", 12),
            fg="#999999"
        ).pack(pady=10)
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
        """Cambia entre tabs"""
        if self.current_tab != tab_name:
            self.current_tab = tab_name
            self._show_current_tab()
            self._update_tab_buttons()
    
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
