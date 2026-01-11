


from controllers.breaks_controller import BreaksController


class BreaksPanelContent:

    def __init__(self, parent, username, ui_factory, UI):
        """
        Contenido del panel lateral colapsable.
        
        Args:
            parent: Frame contenedor (el lateral_panel)
            username: Usuario actual
            ui_factory: Factory para crear widgets
            UI: Módulo CustomTkinter
        """
        self.container = parent
        self.username = username
        self.ui_factory = ui_factory
        self.UI = UI
        self.breaks_controller = BreaksController()  # Sin parámetros
        self.blackboard = None
        
        # Auto-refresh
        self._refresh_job = None


        self.render()
        
        # Iniciar auto-refresh cada 2 minutos
        self._start_auto_refresh()

    def render(self):
        """Renderiza el contenido del panel lateral"""
        self._create_header()
        self._create_breaks_container()
        self.load_breaks()

    
    def _start_auto_refresh(self):
        """Inicia el auto-refresh periódico de breaks"""
        def refresh_cycle():
            try:
                print("[DEBUG] Auto-refresh de breaks...")
                self.load_breaks(auto_refresh=True)
                # Programar siguiente refresh en 0.3 minutos (18000 ms)
                self._refresh_job = self.container.after(18000, refresh_cycle)
            except Exception as e:
                print(f"[ERROR] refresh_cycle: {e}")
        
        # Iniciar primer ciclo después de 0.3 minutos
        self._refresh_job = self.container.after(18000, refresh_cycle)

    def _create_header(self):
        """Crea el header del panel con título"""
        header_frame = self.ui_factory.frame(self.container, fg_color="#23272a", height=35)
        header_frame.pack(fill="x", padx=2, pady=(2, 2))
        header_frame.pack_propagate(False)  # Mantener altura fija
        
        title_label = self.ui_factory.label(
            header_frame,
            text="⏸️ Breaks",
            font=("Arial", 11, "bold"),
            text_color="#ffffff"
        )
        title_label.pack(pady=5)

    def _create_breaks_container(self):
         # Frame scrollable para las news
        self.breaks_scroll_frame = self.ui_factory.scrollable_frame(
            self.container,
            fg_color="transparent"
        )
        self.breaks_scroll_frame.pack(fill="both", expand=True, padx=5, pady=5)

    def _load_breaks(self, auto_refresh=False):
        """Carga TODOS los breaks del operador: sus breaks y los que cubre"""
        try:
            # Obtener ambos tipos de breaks
            my_breaks = self.breaks_controller.get_operator_breaks(self.username)
            covering_breaks = self.breaks_controller.get_operator_covering_breaks(self.username)
            
            # Limpiar contenido previo
            for widget in self.breaks_scroll_frame.winfo_children():
                widget.destroy()

            has_content = False
            
            # Mostrar MIS BREAKS (donde yo soy cubierto)
            if my_breaks:
                has_content = True
                # Encabezado de sección
                section_label = self.ui_factory.label(
                    self.breaks_scroll_frame,
                    text="🛑 Tus Breaks",
                    font=("Arial", 10, "bold"),
                    text_color="#5865f2"
                )
                section_label.pack(pady=(5, 5))
                
                for brk in my_breaks:
                    self._create_break_label(brk)
            
            # Mostrar BREAKS QUE CUBRO (donde yo cubro a otros)
            if covering_breaks:
                has_content = True
                # Encabezado de sección
                section_label = self.ui_factory.label(
                    self.breaks_scroll_frame,
                    text="👤 Cubrirás",
                    font=("Arial", 10, "bold"),
                    text_color="#faa81a"
                )
                section_label.pack(pady=(10, 5))
                
                for brk in covering_breaks:
                    self._create_covering_label(brk)
            
            # Si no hay ningún tipo de break
            if not has_content:
                no_breaks_label = self.ui_factory.label(
                    self.breaks_scroll_frame,
                    text="No hay breaks activos.",
                    font=("Arial", 10),
                    text_color="#bbbbbb"
                )
                no_breaks_label.pack(pady=10)
        
        except Exception as e:
            print(f"[ERROR] _load_breaks: {e}")

    def _create_break_label(self, break_data):
        """Crea un card estético para un break específico
        
        Args:
            break_data (tuple): Datos del break (ID, usuario_cubierto, usuario_cubre, hora, estado, aprobacion)
        """
        from datetime import datetime
        
        brk_id, user_covered, user_covering, break_time_str, status, approval = break_data
        
        # Parsear hora
        try:
            break_time = datetime.strptime(break_time_str, "%Y-%m-%d %H:%M:%S").strftime("%I:%M %p")
        except Exception:
            break_time = break_time_str  # Usar tal cual si falla el parseo
        
        # Card container
        card_frame = self.ui_factory.frame(
            self.breaks_scroll_frame,
            fg_color="#2b2d31",
            corner_radius=8
        )
        card_frame.pack(fill="x", pady=4, padx=3)
        
        # Hora con ícono grande
        time_label = self.ui_factory.label(
            card_frame,
            text=f"🕒 {break_time}",
            font=("Arial", 14, "bold"),
            text_color="#5865f2"
        )
        time_label.pack(pady=(8, 2))
        
        # Quién cubre
        covering_label = self.ui_factory.label(
            card_frame,
            text=f"Cubierto por: {user_covering}",
            font=("Arial", 13),
            text_color="#b5bac1"
        )
        covering_label.pack(pady=(0, 2))
        
        # Estado de aprobación
        approval_color = "#3ba55d" if "✓" in approval else "#faa81a"
        approval_label = self.ui_factory.label(
            card_frame,
            text=approval,
            font=("Arial", 12),
            text_color=approval_color
        )
        approval_label.pack(pady=(0, 8))

        return card_frame
    
    def _create_covering_label(self, break_data):
        """crea un label para cards donde el operador es el que cubre"""
        from datetime import datetime
        brk_id, user_covered, user_covering, break_cover_time_str, status, approval = break_data
        # Parsear hora
        try:
            break_cover_time = datetime.strptime(break_cover_time_str, "%Y-%m-%d %H:%M:%S").strftime("%I:%M %p")
        except Exception:
            break_cover_time = break_cover_time_str  # Usar tal cual si falla el parseo
        
        # Card container
        card_break_frame = self.ui_factory.frame(
            self.breaks_scroll_frame,
            fg_color="#2b2d31",
            corner_radius=8
        )
        card_break_frame.pack(fill="x", pady=4, padx=3)
        
        # Hora con ícono grande
        time_label = self.ui_factory.label(
            card_break_frame,
            text=f"🕒 {break_cover_time}",
            font=("Arial", 14, "bold"),
            text_color="#5865f2"
        )
        time_label.pack(pady=(8, 2))
        
        # A quién cubre
        covering_label = self.ui_factory.label(
            card_break_frame,
            text=f"Cubrirás a: {user_covered}",
            font=("Arial", 13),
            text_color="#b5bac1"
        )
        covering_label.pack(pady=(0, 2))
        
        # Estado de aprobación
        approval_color = "#3ba55d" if "✓" in approval else "#faa81a"
        approval_label = self.ui_factory.label(
            card_break_frame,
            text=approval,
            font=("Arial", 12),
            text_color=approval_color
        )
        approval_label.pack(pady=(0, 8))

        return card_break_frame
        
    
    def load_breaks(self, auto_refresh=False):
        """Carga los breaks activos desde el controlador y los muestra
        
        Args:
            auto_refresh (bool): Indica si es una carga automática periódica
        """
        self._load_breaks(auto_refresh=auto_refresh)

    def refresh_breaks(self):
        """Refresca los breaks desde la BD"""
        self.load_breaks()

    def destroy(self):
        """Cleanup al destruir el módulo"""
        # Cancelar auto-refresh
        if self._refresh_job:
            try:
                self.container.after_cancel(self._refresh_job)
            except:
                pass
        
        # Destruir labels
        for label in self.break_labels:
            try:
                label.destroy()
            except:
                pass
    