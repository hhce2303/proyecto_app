from controllers.news_controller import NewsController
import customtkinter as ctk
import traceback

class LateralPanelContent:

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
        self.news_cards = []
        self.news_controller = NewsController(username)
        self.blackboard = None
        
        # Auto-refresh
        self._refresh_job = None
        self._last_high_urgency_count = 0  # Para evitar alertas repetidas

        self.render()
        
        # Iniciar auto-refresh cada 2 minutos
        self._start_auto_refresh()

    def render(self):
        """Renderiza el contenido del panel lateral"""
        self._create_header()
        self._create_news_container()
        self.load_news()
    
    def _start_auto_refresh(self):
        """Inicia el auto-refresh periódico de news"""
        def refresh_cycle():
            try:
                print("[DEBUG] Auto-refresh de noticias...")
                self.load_news(auto_refresh=True)
                # Programar siguiente refresh en 2 minutos (120000 ms)
                self._refresh_job = self.container.after(120000, refresh_cycle)
            except Exception as e:
                print(f"[ERROR] refresh_cycle: {e}")
        
        # Iniciar primer ciclo después de 2 minutos
        self._refresh_job = self.container.after(80000, refresh_cycle)

    def _create_header(self):
        """Crea el header del panel con título"""
        header_frame = self.ui_factory.frame(self.container, fg_color="#23272a", height=35)
        header_frame.pack(fill="x", padx=2, pady=(2, 2))
        header_frame.pack_propagate(False)  # Mantener altura fija
        
        title_label = self.ui_factory.label(
            header_frame,
            text="📰 Noticias",
            font=("Arial", 11, "bold"),
            text_color="#ffffff"
        )
        title_label.pack(pady=5)

    def _create_news_container(self):
        """Crea el contenedor scrollable para las news"""
        # Frame scrollable para las news
        self.news_scroll_frame = self.ui_factory.scrollable_frame(
            self.container,
            fg_color="transparent"
        )
        self.news_scroll_frame.pack(fill="both", expand=True, padx=5, pady=5)

    def load_news(self, auto_refresh=False):
        """Carga y renderiza las news activas desde la BD
        
        Args:
            auto_refresh: Si es True, indica que se llamó desde el auto-refresh
        """
        try:
            print(f"[DEBUG] Cargando news para {self.username}...")
            
            # Limpiar cards existentes
            for card in self.news_cards:
                card.destroy()
            self.news_cards.clear()
            
            # Obtener news desde controller
            news_data = self.news_controller.cargar_news_activas()
            
            if not news_data:
                # Mensaje cuando no hay news
                no_news_label = self.ui_factory.label(
                    self.news_scroll_frame,
                    text="📭 Sin noticias",
                    font=("Arial", 11),
                    text_color="#888888"
                )
                no_news_label.pack(pady=20)
                return
            
            # Ordenar news por urgencia (ALTA->MEDIA->BAJA) y luego por fecha
            def get_urgency_value(news):
                """Convierte urgencia a valor numérico para ordenar"""
                urgency_raw = news[3]
                if isinstance(urgency_raw, int):
                    return urgency_raw
                else:
                    urgency_map = {
                        'LOW': 1, 'MEDIUM': 2, 'HIGH': 3,
                        '1': 1, '2': 2, '3': 3
                    }
                    return urgency_map.get(str(urgency_raw).upper(), 1)
            
            # Ordenar: primero por urgencia descendente (3, 2, 1), luego por fecha descendente
            news_data_sorted = sorted(
                news_data,
                key=lambda x: (-get_urgency_value(x), x[5]),  # -urgency para descendente, fecha
                reverse=False
            )
            
            # Contar noticias de urgencia ALTA
            high_urgency_count = sum(1 for news in news_data_sorted if get_urgency_value(news) == 3)
            
            # Renderizar cada news como card
            for news in news_data_sorted:
                card = self._create_news_card(news)
                if card:
                    self.news_cards.append(card)
            
            print(f"[DEBUG] {len(self.news_cards)} news cards renderizadas (ordenadas por urgencia)")
            
            # Re-vincular eventos de hover después de crear las cards
            if self.blackboard and hasattr(self.blackboard, '_bind_lateral_hover'):
                self.blackboard._bind_lateral_hover()
            
            # Mostrar alerta si hay noticias de urgencia ALTA (solo en auto-refresh)
            if auto_refresh and high_urgency_count > 0 and high_urgency_count != self._last_high_urgency_count:
                self._show_high_urgency_alert(high_urgency_count)
                self._last_high_urgency_count = high_urgency_count
            elif not auto_refresh:
                # Actualizar contador en carga manual
                self._last_high_urgency_count = high_urgency_count
            
        except Exception as e:
            print(f"[ERROR] load_news: {e}")
            traceback.print_exc()
    
    def _show_high_urgency_alert(self, count):
        """Muestra alerta cuando hay noticias de urgencia ALTA"""
        try:
            from tkinter import messagebox
            
            message = f"🚨 ATENCIÓN: Hay {count} noticia{'s' if count > 1 else ''} de URGENCIA ALTA\n\n"
            message += "Revisa el panel lateral para más detalles."
            
            # Obtener ventana padre si existe
            parent = None
            if self.blackboard and hasattr(self.blackboard, 'window'):
                parent = self.blackboard.window
            
            messagebox.showwarning(
                "Noticias Urgentes",
                message,
                parent=parent
            )
            
            print(f"[DEBUG] Alerta mostrada: {count} noticias de urgencia ALTA")
            
        except Exception as e:
            print(f"[ERROR] _show_high_urgency_alert: {e}")
            traceback.print_exc()

    def _create_news_card(self, news_data):
        """
        Crea una card individual para mostrar una noticia.
        
        Args:
            news_data: Tupla con datos de la noticia desde BD
                (ID_information, info_type, name_info, urgency, publish_by, fechahora_in, fechahora_out, is_Active)
        """
        try:
            # Extraer datos
            id_info = news_data[0]
            info_type = news_data[1]
            title = news_data[2]
            urgency_raw = news_data[3]
            published_by = news_data[4]
            fecha_in = news_data[5]
            
            # Convertir urgency (puede venir como int o string)
            if isinstance(urgency_raw, int):
                urgency = urgency_raw
            else:
                # Mapear strings antiguos a números
                urgency_map = {
                    'LOW': 1,
                    'MEDIUM': 2,
                    'HIGH': 3,
                    '1': 1,
                    '2': 2,
                    '3': 3
                }
                urgency = urgency_map.get(str(urgency_raw).upper(), 1)
            
            # Definir color según urgencia
            urgency_colors = {
                1: "#2ecc71",  # Baja - Verde
                2: "#f39c12",  # Media - Naranja
                3: "#e74c3c"   # Alta - Rojo
            }
            color = urgency_colors.get(urgency, "#95a5a6")
            
            # Iconos según urgencia
            urgency_icons = {
                1: "ℹ️",
                2: "⚠️",
                3: "🚨"
            }
            icon = urgency_icons.get(urgency, "📌")
            
            # Crear card
            card = NewsCard(
                parent=self.news_scroll_frame,
                ui_factory=self.ui_factory,
                title=title,
                urgency=urgency,
                published_by=published_by,
                icon=icon,
                color=color,
                height=80  # Altura fija
            )
            card.pack(fill="x", padx=5, pady=3)
            card.pack_propagate(False)  # Mantener altura fija
            
            return card
            
        except Exception as e:
            print(f"[ERROR] _create_news_card: {e}")
            traceback.print_exc()
            return None

    def refresh_news(self):
        """Refresca las news desde la BD"""
        self.load_news()
    
    def destroy(self):
        """Cleanup al destruir el módulo"""
        # Cancelar auto-refresh
        if self._refresh_job:
            try:
                self.container.after_cancel(self._refresh_job)
            except:
                pass
        
        # Destruir cards
        for card in self.news_cards:
            try:
                card.destroy()
            except:
                pass

class NewsCard(ctk.CTkFrame):
    """Card compacta para mostrar una noticia en el panel lateral"""
    
    def __init__(self, parent, ui_factory, title, urgency, published_by, icon="📰", color="#4a90e2", **kwargs):
        super().__init__(parent, fg_color="#1e1e1e", corner_radius=8, **kwargs)
        
        self.icon = icon
        self.title = title
        self.urgency = urgency
        self.published_by = published_by
        self.color = color
        self.ui_factory = ui_factory
        
        # Variables para animación de texto
        self._scroll_job = None
        self._scroll_position = 0
        self._scroll_direction = 1  # 1 para derecha, -1 para izquierda
        
        self._build_ui()
        
        # Iniciar animación si el título es largo
        if len(self.title) > 25:
            self._start_scroll_animation()
    
    def _build_ui(self):
        """Construye la UI de la card"""
        # Contenedor horizontal para barra lateral + contenido
        main_container = self.ui_factory.frame(self, fg_color="transparent")
        main_container.pack(fill='both', expand=True)
        
        # Barra de color según urgencia (LATERAL IZQUIERDA)
        accent_bar = self.ui_factory.frame(
            main_container, 
            fg_color=self.color, 
            width=6, 
            corner_radius=0
        )
        accent_bar.pack(fill='y', side='left')
        
        # Contenedor principal para el contenido
        content_frame = self.ui_factory.frame(main_container, fg_color="transparent")
        content_frame.pack(fill='both', expand=True, padx=6, pady=4)
        
        # Header con icono
        header_frame = self.ui_factory.frame(content_frame, fg_color="transparent")
        header_frame.pack(fill='x', pady=(0, 3))
        
        icon_label = self.ui_factory.label(
            header_frame,
            text=self.icon,
            font=("Arial", 16)
        )
        icon_label.pack(side='left', padx=(0, 4))
        
        # Etiqueta de urgencia
        urgency_text = ["", "BAJA", "MEDIA", "ALTA"][self.urgency]
        urgency_label = self.ui_factory.label(
            header_frame,
            text=urgency_text,
            font=("Arial", 11, "bold"),
            text_color=self.color
        )
        urgency_label.pack(side='right')
        
        # Título de la noticia con animación
        self.title_label = self.ui_factory.label(
            content_frame,
            text=self.title,
            font=("Arial", 13, "bold"),
            text_color="#ffffff",
            anchor="w",
            justify="left"
        )
        self.title_label.pack(fill='x', pady=(0, 2))
        
        # Publicado por
        author_label = self.ui_factory.label(
            content_frame,
            text=f"Por: {self.published_by}",
            font=("Arial", 12),
            text_color="#888888",
            anchor="w"
        )
        author_label.pack(fill='x')
    
    def _start_scroll_animation(self):
        """Inicia la animación de scroll del título"""
        def animate():
            try:
                if not self.winfo_exists():
                    return
                
                # Añadir espacios para crear efecto de loop
                display_text = self.title + "   ·   " + self.title
                
                # Calcular posición
                max_pos = len(self.title) + 7  # Longitud + espaciado
                self._scroll_position = (self._scroll_position + 1) % max_pos
                
                # Actualizar texto mostrado
                visible_text = display_text[self._scroll_position:self._scroll_position + 25]
                self.title_label.configure(text=visible_text)
                
                # Continuar animación
                self._scroll_job = self.after(200, animate)
            except:
                pass
        
        # Iniciar animación después de 1 segundo
        self.after(1000, animate)
    
    def destroy(self):
        """Detiene la animación al destruir la card"""
        if self._scroll_job:
            try:
                self.after_cancel(self._scroll_job)
            except:
                pass
        super().destroy()
