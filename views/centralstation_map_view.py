"""
Vista para el mapa de Central Station.

RESTRICCIONES:
- Solo lectura del contrato WorkspaceState
- Sin lógica de negocio
- Sin acceso a BD
- Sin mutación de datos
- Solo renderizado visual

Responsabilidades:
- Renderizar SVG
- Aplicar estilos a estaciones
- Mostrar eventos efímeros
- Animar transiciones
"""

from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QGraphicsView, QGraphicsScene, QGraphicsItem
from PySide6.QtSvgWidgets import QGraphicsSvgItem
from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, QPointF, Property
from PySide6.QtGui import QColor, QPainter, QFont
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtXml import QDomDocument
from typing import Dict, List, Any, Optional
import os


# ========== CONFIGURACIÓN VISUAL ==========

COLORS = {
    "idle": QColor("#1e1e1e"),           # Gris oscuro
    "active": QColor("#00ff00"),         # Verde brillante (TEMPORAL para debug)
    "break": QColor("#ffff00"),          # Amarillo brillante
    "alert": QColor("#ff0000"),          # Rojo brillante
}

STROKE_COLORS = {
    "idle": QColor("#5f6368"),
    "active": QColor("#00ff00"),         # Verde brillante
    "break": QColor("#ffff00"),          # Amarillo brillante
    "alert": QColor("#ff0000"),          # Rojo brillante
}

EVENT_COLORS = {
    "info": QColor("#2196f3"),
    "warning": QColor("#ff9800"),
    "critical": QColor("#f44336"),
}


# ========== VISTA PRINCIPAL ==========

class WorkspaceMapView(QWidget):
    """
    Vista principal del mapa de estaciones.
    
    Consumo del contrato:
    - Recibe WorkspaceState completo
    - No interpreta, solo renderiza
    - No almacena historial
    """
    
    def __init__(self, svg_path: str, parent=None):
        super().__init__(parent)
        
        # Validar SVG
        if not os.path.exists(svg_path):
            raise FileNotFoundError(f"SVG no encontrado: {svg_path}")
        
        self.svg_path = svg_path
        
        # Componentes de la vista
        self.svg_renderer = SVGRenderer(svg_path)
        self.station_styler = StationStyler(self.svg_renderer)
        self.event_overlay_manager = EventOverlayManager(self)
        self.animation_engine = AnimationEngine()
        
        # Layout
        self._setup_ui()
        
        # Estado visual actual (solo para animaciones)
        self._current_visual_state = {}
    
    def _setup_ui(self):
        """Configurar interfaz gráfica"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Graphics View para SVG
        self.graphics_view = QGraphicsView()
        self.graphics_view.setRenderHint(QPainter.Antialiasing)
        self.graphics_view.setRenderHint(QPainter.SmoothPixmapTransform)
        self.graphics_view.setViewportUpdateMode(QGraphicsView.FullViewportUpdate)
        self.graphics_view.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.graphics_view.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        # Scene
        self.scene = QGraphicsScene()
        self.graphics_view.setScene(self.scene)
        
        # Agregar SVG a la escena
        self.svg_item = QGraphicsSvgItem(self.svg_path)
        self.scene.addItem(self.svg_item)
        
        layout.addWidget(self.graphics_view)
        
        # Ajustar vista al contenido
        self.graphics_view.fitInView(self.svg_item, Qt.KeepAspectRatio)
    
    def update_state(self, workspace_state: Dict[str, Any]):
        """
        Actualiza la vista con nuevo estado.
        
        Args:
            workspace_state: Objeto del contrato WorkspaceState
        
        IMPORTANTE:
        - No valida el estado (asume correcto)
        - No compara con estado anterior
        - Solo renderiza lo que recibe
        """
        # 1. Actualizar estaciones
        self._update_stations(workspace_state.get("stations", {}))
        
        # 2. Mostrar eventos
        self._show_events(workspace_state.get("events", []))
        
        # 3. Refrescar el SVG si hubo modificaciones
        if self.station_styler.has_modifications():
            print(f"[DEBUG] Refrescando SVG...")
            self._refresh_svg()
            self.station_styler.reset_modifications()
            print(f"[DEBUG] SVG refrescado")
    
    def _update_stations(self, stations: Dict[str, Dict]):
        """
        Actualiza visualización de estaciones.
        
        Para cada estación:
        - Aplica color según status
        - Muestra/oculta indicador de usuario
        - Anima transición si cambió
        """
        for station_id, station_data in stations.items():
            # Obtener estado visual anterior
            previous_state = self._current_visual_state.get(station_id, {})
            
            # Determinar si cambió
            changed = (
                previous_state.get("occupied") != station_data["occupied"] or
                previous_state.get("status") != station_data["status"]
            )
            
            # Aplicar estilo
            self.station_styler.apply_style(
                station_id=station_id,
                occupied=station_data["occupied"],
                status=station_data["status"],
                user_name=station_data["user"]["name"] if station_data["user"] else None,
                animate=changed
            )
            
            # Actualizar cache visual
            self._current_visual_state[station_id] = {
                "occupied": station_data["occupied"],
                "status": station_data["status"]
            }
    
    def _show_events(self, events: List[Dict]):
        """
        Muestra eventos como overlays temporales.
        
        Cada evento:
        - Se posiciona sobre la estación
        - Se auto-destruye después de ttl
        - Anima entrada/salida
        """
        for event in events:
            self.event_overlay_manager.create_event(
                event_id=event["event_id"],
                station_id=event["station_id"],
                label=event["label"],
                severity=event["severity"],
                ttl=event["ttl"]
            )
    
    def _refresh_svg(self):
        """Recargar el SVG con las modificaciones del DOM"""
        # Obtener el nuevo contenido SVG
        svg_content = self.svg_renderer.get_svg_content()
        
        # DEBUG: Guardar para verificar
        with open("debug_svg_output.svg", "w", encoding="utf-8") as f:
            f.write(svg_content)
        print(f"[DEBUG] SVG guardado en debug_svg_output.svg")
        
        # Crear archivo temporal con el SVG modificado
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.svg', delete=False, encoding='utf-8') as f:
            f.write(svg_content)
            temp_path = f.name
        
        # Remover el item anterior
        if hasattr(self, 'svg_item') and self.svg_item:
            self.scene.removeItem(self.svg_item)
        
        # Cargar el nuevo SVG
        self.svg_item = QGraphicsSvgItem(temp_path)
        self.scene.addItem(self.svg_item)
        
        # Ajustar vista
        self.graphics_view.fitInView(self.svg_item, Qt.KeepAspectRatio)
        
        # Limpiar archivo temporal
        try:
            os.unlink(temp_path)
        except:
            pass
    
    def resizeEvent(self, event):
        """Mantener SVG ajustado al redimensionar"""
        super().resizeEvent(event)
        if hasattr(self, 'svg_item'):
            self.graphics_view.fitInView(self.svg_item, Qt.KeepAspectRatio)


# ========== SVG RENDERER ==========

class SVGRenderer:
    """
    Manipulador del DOM SVG.
    
    Responsabilidad:
    - Leer contenido SVG
    - Parsear con QDomDocument
    - Exponer búsqueda de elementos
    """
    
    def __init__(self, svg_path: str):
        self.svg_path = svg_path
        self.dom = QDomDocument()
        
        # Cargar SVG
        with open(svg_path, 'r', encoding='utf-8') as f:
            svg_content = f.read()
            self.dom.setContent(svg_content)
    
    def get_element_by_id(self, element_id: str) -> Optional[Any]:
        """
        Busca elemento SVG por ID.
        
        Args:
            element_id: ID del elemento (ej: "WS_01")
        
        Returns:
            QDomElement o None si no existe
        """
        root = self.dom.documentElement()
        return self._find_element_recursive(root, element_id)
    
    def _find_element_recursive(self, node, target_id: str):
        """Búsqueda recursiva en el árbol DOM"""
        if node.isElement():
            element = node.toElement()
            if element.attribute("id") == target_id:
                return element
        
        # Buscar en hijos
        child = node.firstChild()
        while not child.isNull():
            result = self._find_element_recursive(child, target_id)
            if result is not None:
                return result
            child = child.nextSibling()
        
        return None
    
    def get_svg_content(self) -> str:
        """Obtiene el contenido SVG como string después de modificaciones"""
        return self.dom.toString()


# ========== STATION STYLER ==========

class StationStyler:
    """
    Aplica estilos visuales a elementos SVG de estaciones.
    
    Responsabilidad:
    - Cambiar colores de relleno/stroke
    - Aplicar filtros (glow)
    - NO decide qué color usar (solo mapea)
    """
    
    def __init__(self, svg_renderer: SVGRenderer):
        self.svg_renderer = svg_renderer
        self._modified = False
        self._modified = False
    
    def apply_style(
        self, 
        station_id: str, 
        occupied: bool, 
        status: str,
        user_name: Optional[str] = None,
        animate: bool = False
    ):
        """
        Aplica estilo visual a una estación.
        
        Args:
            station_id: ID de la estación (ej: "WS_01")
            occupied: Si está ocupada
            status: Estado visual ("idle", "active", "break", "alert")
            user_name: Nombre del usuario (opcional)
            animate: Si debe animar la transición
        
        Nota:
        - No valida status, asume correcto
        - No decide colores, solo los aplica
        """
        element = self.svg_renderer.get_element_by_id(station_id)
        
        if element is None:
            print(f"[WARNING] Estación no encontrada en SVG: {station_id}")
            return
        
        # Determinar color
        if not occupied:
            color = COLORS["idle"]
            stroke = STROKE_COLORS["idle"]
            opacity = "0.5"
            filter_effect = ""
        else:
            color = COLORS.get(status, COLORS["idle"])
            stroke = STROKE_COLORS.get(status, STROKE_COLORS["idle"])
            opacity = "1.0"
            filter_effect = "url(#glow)" if status == "alert" else ""
        
        # Aplicar atributos a TODOS los elementos hijos (rect, circle)
        # porque el SVG usa clases CSS que sobrescriben el fill del padre
        child = element.firstChild()
        while not child.isNull():
            if child.isElement():
                child_element = child.toElement()
                tag_name = child_element.tagName().lower()
                
                # Aplicar color a elementos visuales
                if tag_name in ('rect', 'circle', 'path', 'polygon'):
                    child_element.setAttribute("fill", color.name())
                    child_element.setAttribute("stroke", stroke.name())
                    child_element.setAttribute("opacity", opacity)
            
            child = child.nextSibling()
        
        # Aplicar filtro al grupo si es necesario
        if filter_effect:
            element.setAttribute("filter", filter_effect)
        else:
            element.removeAttribute("filter")
        
        # Agregar o remover nombre del usuario
        self._update_user_label(element, user_name if occupied else None)
        
        # Marcar que se modificó el DOM
        self._modified = True
    
    def _update_user_label(self, station_element, user_name: Optional[str]):
        """
        Agrega o actualiza el label de texto con el nombre del usuario.
        
        Args:
            station_element: Elemento <g> de la estación
            user_name: Nombre del usuario o None para remover
        """
        # Buscar si ya existe un elemento de texto
        existing_text = None
        child = station_element.firstChild()
        while not child.isNull():
            if child.isElement():
                elem = child.toElement()
                if elem.tagName().lower() == 'text' and elem.attribute('class') == 'user-label':
                    existing_text = elem
                    break
            child = child.nextSibling()
        
        if user_name:
            # Detectar posiciones de las sillas para colocar el nombre correctamente
            chair_positions = []
            child_temp = station_element.firstChild()
            while not child_temp.isNull():
                if child_temp.isElement():
                    elem = child_temp.toElement()
                    if elem.tagName().lower() == 'circle' and 'chair' in elem.attribute('class'):
                        cx = float(elem.attribute('cx', '0'))
                        cy = float(elem.attribute('cy', '35'))
                        chair_positions.append((cx, cy))
                child_temp = child_temp.nextSibling()
            
            # Determinar posición del texto basándose en las sillas
            if len(chair_positions) == 1:
                # Una silla: colocar el nombre encima de ella
                text_x = str(int(chair_positions[0][0]))
                text_y = str(int(chair_positions[0][1] - 10))
            elif len(chair_positions) == 2:
                # Dos sillas: colocar en el centro pero ajustado
                chair_positions.sort()  # Ordenar por x
                left_x, left_y = chair_positions[0]
                right_x, right_y = chair_positions[1]
                
                if abs(left_x - right_x) > 100:  # Sillas a los lados
                    # Colocar en el centro horizontal, arriba
                    center_x = (left_x + right_x) / 2
                    text_x = str(int(center_x))
                    text_y = str(int(left_y - 10))
                else:
                    # Sillas una arriba de otra o cercanas
                    text_x = str(int((left_x + right_x) / 2))
                    text_y = str(int(min(left_y, right_y) - 10))
            else:
                # Por defecto: centro
                text_x = '90'
                text_y = '30'
            
            # Crear o actualizar texto
            if existing_text:
                # Actualizar texto y posición
                existing_text.firstChild().setNodeValue(user_name)
                existing_text.setAttribute('x', text_x)
                existing_text.setAttribute('y', text_y)
            else:
                # Crear nuevo elemento de texto
                text_elem = self.svg_renderer.dom.createElement('text')
                text_elem.setAttribute('class', 'user-label')
                text_elem.setAttribute('x', text_x)
                text_elem.setAttribute('y', text_y)
                text_elem.setAttribute('text-anchor', 'middle')
                text_elem.setAttribute('fill', '#ffffff')  # Blanco para mejor contraste
                text_elem.setAttribute('font-size', '16')
                text_elem.setAttribute('font-weight', 'bold')
                text_elem.setAttribute('font-family', 'Arial, sans-serif')
                text_elem.setAttribute('stroke', '#000000')  # Borde negro
                text_elem.setAttribute('stroke-width', '0.5')  # Borde delgado
                # Agregar el texto
                text_node = self.svg_renderer.dom.createTextNode(user_name)
                text_elem.appendChild(text_node)
                
                # Agregar al grupo de la estación
                station_element.appendChild(text_elem)
        else:
            # Remover texto si existe
            if existing_text:
                station_element.removeChild(existing_text)
        
        # TODO: Si animate=True, aplicar QPropertyAnimation
        # (requiere acceso al QGraphicsItem correspondiente)
    
    def has_modifications(self) -> bool:
        """Verifica si hay modificaciones pendientes"""
        return self._modified
    
    def reset_modifications(self):
        """Resetea el flag de modificaciones"""
        self._modified = False


# ========== EVENT OVERLAY MANAGER ==========

class EventOverlayManager:
    """
    Gestiona overlays de eventos efímeros.
    
    Responsabilidad:
    - Crear widgets flotantes sobre estaciones
    - Auto-destruir después de ttl
    - Animar entrada/salida
    """
    
    def __init__(self, parent_widget: QWidget):
        self.parent = parent_widget
        self.active_events = {}  # event_id -> EventOverlay
    
    def create_event(
        self, 
        event_id: str, 
        station_id: str, 
        label: str,
        severity: str,
        ttl: int
    ):
        """
        Crea un overlay de evento.
        
        Args:
            event_id: ID único del evento
            station_id: Estación asociada
            label: Texto a mostrar
            severity: Nivel ("info", "warning", "critical")
            ttl: Tiempo de vida en milisegundos
        """
        # Evitar duplicados
        if event_id in self.active_events:
            return
        
        # Crear overlay
        overlay = EventOverlay(
            label=label,
            severity=severity,
            parent=self.parent
        )
        
        # Posicionar sobre estación
        # TODO: Calcular posición desde coordenadas SVG
        # Por ahora, posición fija para demo
        overlay.move(100, 100)
        overlay.show()
        
        # Animar entrada
        overlay.animate_in()
        
        # Guardar referencia
        self.active_events[event_id] = overlay
        
        # Programar destrucción
        QTimer.singleShot(ttl, lambda: self._destroy_event(event_id))
    
    def _destroy_event(self, event_id: str):
        """Destruye un evento después de ttl"""
        overlay = self.active_events.get(event_id)
        
        if overlay is None:
            return
        
        # Animar salida
        overlay.animate_out()
        
        # Destruir después de animación
        QTimer.singleShot(300, lambda: self._remove_overlay(event_id))
    
    def _remove_overlay(self, event_id: str):
        """Elimina overlay del DOM"""
        overlay = self.active_events.pop(event_id, None)
        if overlay:
            overlay.deleteLater()


# ========== EVENT OVERLAY WIDGET ==========

class EventOverlay(QLabel):
    """
    Widget individual para mostrar un evento.
    
    Responsabilidad:
    - Renderizar label con estilo
    - Soportar animaciones de entrada/salida
    """
    
    def __init__(self, label: str, severity: str, parent=None):
        super().__init__(label, parent)
        
        # Estilo según severity
        bg_color = EVENT_COLORS.get(severity, EVENT_COLORS["info"])
        
        self.setStyleSheet(f"""
            QLabel {{
                background-color: {bg_color.name()};
                color: white;
                padding: 8px 16px;
                border-radius: 6px;
                font-size: 14px;
                font-weight: bold;
            }}
        """)
        
        self.setAlignment(Qt.AlignCenter)
        self.adjustSize()
        
        # Animaciones
        self._opacity = 1.0
    
    def animate_in(self):
        """Animación de entrada (fade in + scale)"""
        self.setWindowOpacity(0.0)
        
        anim = QPropertyAnimation(self, b"windowOpacity")
        anim.setDuration(300)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.OutCubic)
        anim.start()
    
    def animate_out(self):
        """Animación de salida (fade out)"""
        anim = QPropertyAnimation(self, b"windowOpacity")
        anim.setDuration(300)
        anim.setStartValue(1.0)
        anim.setEndValue(0.0)
        anim.setEasingCurve(QEasingCurve.InCubic)
        anim.start()


# ========== ANIMATION ENGINE ==========

class AnimationEngine:
    """
    Motor de animaciones para transiciones suaves.
    
    Responsabilidad:
    - Crear QPropertyAnimation
    - Gestionar easing curves
    - 60 FPS
    """
    
    def __init__(self):
        self.active_animations = []
    
    def fade_transition(
        self, 
        target: QGraphicsItem, 
        duration: int = 300
    ) -> QPropertyAnimation:
        """
        Crea animación de fade.
        
        Args:
            target: Item a animar
            duration: Duración en ms
        
        Returns:
            QPropertyAnimation configurada
        """
        anim = QPropertyAnimation(target, b"opacity")
        anim.setDuration(duration)
        anim.setEasingCurve(QEasingCurve.InOutCubic)
        return anim
    
    def pulse_animation(
        self, 
        target: QGraphicsItem
    ) -> QPropertyAnimation:
        """
        Crea animación de pulso (scale up/down).
        
        Args:
            target: Item a animar
        
        Returns:
            QPropertyAnimation configurada
        """
        anim = QPropertyAnimation(target, b"scale")
        anim.setDuration(500)
        anim.setStartValue(1.0)
        anim.setKeyValueAt(0.5, 1.05)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.InOutSine)
        anim.setLoopCount(1)
        return anim
