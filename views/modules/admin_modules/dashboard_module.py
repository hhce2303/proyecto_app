import customtkinter as ctk
from models.admin_model import get_dashboard_metrics
from utils import ui_factory
from utils.ui_factory import UIFactory
import traceback
from datetime import datetime
AUTO_REFRESH_INTERVAL = 30000

class MetricCard(ctk.CTkFrame):
    """Card para mostrar una métrica con valor y etiqueta"""

    def __init__(self, parent, ui_factory, title, value, icon="📊", color="#4a90e2", **kwargs):
        super().__init__(parent, fg_color="#1e1e1e", corner_radius=10, **kwargs)
        self.icon = icon
        self.title = title
        self.color = color
        self.ui_factory = ui_factory
        # Frame superior con color de acento
        accent_frame = ui_factory.frame(self, fg_color=color, height=5, corner_radius=0)
        accent_frame.pack(fill='x', side='top')

        # Contenedor principal
        content_frame = ui_factory.frame(self, fg_color="transparent")
        content_frame.pack(fill='both', expand=True, padx=15, pady=10)

        # Icon y título
        header_frame = ui_factory.frame(content_frame, fg_color="transparent")
        header_frame.pack(fill='x', pady=(0, 10))

        icon_label = ui_factory.label(
            header_frame,
            text=icon,
            font=("Arial", 20)
        )
        icon_label.pack(side='left', padx=(0, 10))

        title_label = ui_factory.label(
            header_frame,
            text=title,
            font=("Arial", 12, "normal"),
            text_color="#aaaaaa"
        )
        title_label.pack(side='left', anchor='w')

        # Valor grande
        self.value_label = ui_factory.label(
            content_frame,
            text=str(value),
            font=("Arial", 36, "bold"),
            text_color="#ffffff"
        )
        self.value_label.pack(anchor='w')
    
    def update_value(self, new_value):
        """Actualiza el valor mostrado"""
        self.value_label.configure(text=str(new_value))

class DashboardModule:
    
    def __init__(self, container, username, ui_factory, UI=None):
        """
        Inicializa el módulo dashboard.
        
        Args:
            container: Frame contenedor del módulo
            username: Nombre del usuario
            ui_factory: Factory para crear widgets
            UI: Módulo CustomTkinter (opcional)
        """
        self.metric_cards = {}
        self.container = container
        self.username = username
        self.ui_factory = ui_factory
        self.UI = UI
        
        # Referencia al blackboard (se establecerá desde OperatorBlackboard)
        self.blackboard = None

        # Renderizar
        self.render()
    
    def render(self):
        """Renderiza el módulo completo"""
        self._create_toolbar(self.container)
        self._create_metrics_section(self.container)
        self.refresh_dashboard()
        # Iniciar auto-refresh
        self._start_auto_refresh()
        self._create_graphs_section()


    def _create_toolbar(self, container):
        """Crea la barra de herramientas del módulo"""
        toolbar = self.ui_factory.frame(container, fg_color="#000000", height=40)
        toolbar.pack(fill="x")

        title_label = self.ui_factory.label(
            toolbar,
            text="timestamp",
            font=("Arial", 16, "bold")
        )
        title_label.pack(side='right', padx=20, pady=5)

        refresh_button = self.ui_factory.button(
            toolbar,
            text="🔄 Refresh",
            command=None,
            width=100,
            fg_color="#238636"
        )
        refresh_button.pack(side="right", padx=10, pady=5)

    def _create_metrics_section(self, container):
        """Crea la sección de cards de métricas"""
        metrics_frame = self.ui_factory.frame(container, fg_color="#000000")
        metrics_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        section_title = self.ui_factory.label(
            metrics_frame,
            text="📈 Métricas en Tiempo Real",
            font=("Arial", 18, "bold"),
            text_color="#ffffff"
        )
        section_title.pack(anchor='w', pady=(0, 15))
        
        # Grid de cards
        cards_grid = self.ui_factory.frame(metrics_frame, fg_color="transparent")
        cards_grid.pack(fill='x')  # Usar solo grid para los MetricCard dentro de cards_grid
        
        # Configurar grid 4x2
        for i in range(4):
            cards_grid.grid_columnconfigure(i, weight=1, uniform="col")
        
        # Definir cards
        cards_config = [
            ("Sesiones Activas", 0, "👥", "#4a90e2"),
            ("Covers Pendientes", 0, "⏳", "#f39c12"),
            ("Breaks Activos", 0, "☕", "#27ae60"),
            ("Eventos Hoy", 0, "📝", "#8e44ad"),
            ("Usuarios Conectados", 0, "🟢", "#16a085"),
            ("Covers Completados", 0, "✅", "#2ecc71"),
            ("Ususarios con lista covers", 0, "📋", "#34495e"),
            ("Specials Dia", 0, "⭐", "#e67e22")   
        ]
        
        for idx, (title, value, icon, color) in enumerate(cards_config):
            row = idx // 4
            col = idx % 4
            
            card = MetricCard(
                cards_grid,
                title=title,
                ui_factory=self.ui_factory,
                value=value,
                icon=icon,
                color=color,
                width=200,
                height=120
            )
                # Usar grid SOLO para los MetricCard, y no usar pack en este frame
            card.grid(row=row, column=col, padx=5, pady=5, sticky='nsew')
            
            # Guardar referencia para actualizar
            key = title.lower().replace(' ', '_')
            self.metric_cards[key] = card

    def refresh_dashboard(self):
        """Actualiza todos los datos del dashboard"""
        try:
            print(f"[INFO] 🔄 Refrescando dashboard...")
            
            # 1. Actualizar métricas
            metrics = get_dashboard_metrics()
            
            self.metric_cards['sesiones_activas'].update_value(metrics['sesiones_activas'])
            self.metric_cards['covers_pendientes'].update_value(metrics['covers_pendientes'])
            self.metric_cards['breaks_activos'].update_value(metrics['breaks_activos'])
            self.metric_cards['eventos_hoy'].update_value(metrics['eventos_dia'])
            self.metric_cards['usuarios_conectados'].update_value(metrics['usuarios_conectados'])
            self.metric_cards['covers_completados'].update_value(metrics['covers_completados_hoy'])
            self.metric_cards['ususarios_con_lista_covers'].update_value(metrics['usuarios_lista'])
            self.metric_cards['specials_dia'].update_value(metrics['specials_dia'])
            
            print(f"[INFO] ✅ Dashboard actualizado correctamente")
            
        except Exception as e:
            print(f"[ERROR] refresh_dashboard: {e}")
            traceback.print_exc()

    def _start_auto_refresh(self):
        """Inicia el auto-refresh periódico"""
        self.auto_refresh_job = self.container.after(AUTO_REFRESH_INTERVAL, self._auto_refresh_callback)
    
    def _auto_refresh_callback(self):
        """Callback para auto-refresh"""
        self.refresh_dashboard()
        self._start_auto_refresh()  # Re-agendar

    def destroy(self):
        """Cleanup al destruir"""
        if self.auto_refresh_job:
            self.after_cancel(self.auto_refresh_job)
        super().destroy()

      
    def _create_graphs_section(self):
        """Crea la sección de gráficos"""
        graphs_frame = self.ui_factory.frame(self.container, fg_color="transparent")
        graphs_frame.pack(fill='both', expand=True, pady=(0, 20))
        
        section_title = ctk.CTkLabel(
            graphs_frame,
            text="📊 Análisis Visual",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color="#ffffff"
        )
        section_title.pack(anchor='w', pady=(0, 15))
        
        # Container para gráficos (2 columnas)
        graphs_container = ctk.CTkFrame(graphs_frame, fg_color="transparent")
        graphs_container.pack(fill='both', expand=True)
        
        graphs_container.grid_columnconfigure(0, weight=1)
        graphs_container.grid_columnconfigure(1, weight=1)
        
        # Gráfico 1: Eventos por hora
        self.graph1_frame = ctk.CTkFrame(graphs_container, fg_color="#1e1e1e", corner_radius=10)
        self.graph1_frame.grid(row=0, column=0, padx=5, pady=5, sticky='nsew')
        
        graph1_title = ctk.CTkLabel(
            self.graph1_frame,
            text="📈 Eventos por Hora (Últimas 24h)",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        graph1_title.pack(pady=10)
        
        # Gráfico 2: Distribución de eventos
        self.graph2_frame = ctk.CTkFrame(graphs_container, fg_color="#1e1e1e", corner_radius=10)
        self.graph2_frame.grid(row=0, column=1, padx=5, pady=5, sticky='nsew')
        
        graph2_title = ctk.CTkLabel(
            self.graph2_frame,
            text="🥧 Distribución por Actividad (Hoy)",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        graph2_title.pack(pady=10)
    