# Ejemplo: Animar y resaltar una workstation en SVG usando PySide6
from PySide6.QtWidgets import QApplication, QGraphicsView, QGraphicsScene
from PySide6.QtSvgWidgets import QGraphicsSvgItem
from PySide6.QtCore import QPropertyAnimation, QRectF, Qt, QEasingCurve
from PySide6.QtGui import QPainter
import sys, os

class SvgAnimationDemo(QGraphicsView):
    def __init__(self, svg_path, ws_id=None):
        super().__init__()
        self.svg_path = svg_path  # Guardar el path para uso posterior
        self.setWindowTitle("Animación SVG - PySide6")
        self.setRenderHint(QPainter.Antialiasing)
        self.setMinimumSize(1200, 700)
        scene = QGraphicsScene(self)
        self.setScene(scene)

        # Cargar el SVG completo
        self.svg_item = QGraphicsSvgItem(svg_path)
        scene.addItem(self.svg_item)
        self.svg_item.setFlags(QGraphicsSvgItem.ItemClipsToShape)
        self.svg_item.setZValue(0)
        scene.setSceneRect(self.svg_item.boundingRect())

        # Si quieres animar una workstation específica (por id)
        if ws_id:
            # Cargar solo el grupo de la workstation como un nuevo QGraphicsSvgItem
            # (esto requiere que el SVG tenga los grupos bien definidos)
            ws_item = QGraphicsSvgItem(svg_path)
            ws_item.setElementId(ws_id)
            ws_item.setZValue(1)
            scene.addItem(ws_item)
            # Animación: cambiar opacidad (parpadeo)
            self.anim = QPropertyAnimation(ws_item, b"opacity")
            self.anim.setStartValue(1.0)
            self.anim.setEndValue(0.2)
            self.anim.setDuration(600)
            self.anim.setLoopCount(-1)
            self.anim.setEasingCurve(QEasingCurve.InOutQuad)
            self.anim.start()

        # Habilitar interacción por clic
        self.setMouseTracking(True)
        self.mousePressEvent = self.on_mouse_press

    def on_mouse_press(self, event):
        # Obtener posición del clic en la vista
        pos = event.position() if hasattr(event, 'position') else event.localPos()
        x, y = int(pos.x()), int(pos.y())
        # Convertir a coordenadas de la escena (SVG)
        scene_pos = self.mapToScene(x, y)
        svg_x, svg_y = int(scene_pos.x()), int(scene_pos.y())
        print(f"Clic en SVG: x={svg_x}, y={svg_y}")
        # --- Mapeo manual de workstations (ejemplo para WS_01 a WS_07) ---
        workstations = [
            {"id": "WS_01", "x": 190, "y": 120, "w": 180, "h": 70},
            {"id": "WS_02", "x": 190, "y": 210, "w": 180, "h": 70},
            {"id": "WS_03", "x": 190, "y": 300, "w": 180, "h": 70},
            {"id": "WS_04", "x": 190, "y": 470, "w": 180, "h": 70},
            {"id": "WS_05", "x": 190, "y": 540, "w": 180, "h": 70},
            {"id": "WS_06", "x": 190, "y": 630, "w": 180, "h": 70},
            {"id": "WS_07", "x": 190, "y": 720, "w": 180, "h": 70},
            # Agrega más workstations según el SVG
        ]
        found = None
        for ws in workstations:
            if ws["x"] <= svg_x <= ws["x"]+ws["w"] and ws["y"] <= svg_y <= ws["y"]+ws["h"]:
                found = ws["id"]
                break
        if found:
            print(f"¡Clic sobre {found}!")
            self.animate_workstation(found)
        else:
            print("Clic fuera de workstations mapeadas")

    def animate_workstation(self, ws_id):
        scene = self.scene()
        # Eliminar animaciones previas
        for item in scene.items():
            if isinstance(item, QGraphicsSvgItem) and item.elementId() != "":
                scene.removeItem(item)
        # Agregar y animar la nueva workstation
        ws_item = QGraphicsSvgItem(self.svg_path)
        ws_item.setElementId(ws_id)
        ws_item.setZValue(1)
        scene.addItem(ws_item)
        self.anim = QPropertyAnimation(ws_item, b"opacity")
        self.anim.setStartValue(1.0)
        self.anim.setEndValue(0.2)
        self.anim.setDuration(600)
        self.anim.setLoopCount(-1)
        self.anim.setEasingCurve(QEasingCurve.InOutQuad)
        self.anim.start()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    svg_path = os.path.join(os.path.dirname(__file__), "workspace_map.svg")
    # Cambia 'WS_01' por el id de la workstation que quieras animar
    window = SvgAnimationDemo(svg_path, ws_id="WS_01")
    window.show()
    sys.exit(app.exec())
