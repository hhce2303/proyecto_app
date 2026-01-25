"""
Ejemplo de integración de WorkspaceMapView con Controller.

Este archivo muestra cómo conectar la Vista con el Controller
respetando la arquitectura MVC.

IMPORTANTE:
- La Vista NO llama directamente al controller
- Un coordinador (ej: ventana principal) hace el polling
- La Vista solo recibe estados y renderiza
"""

import sys
from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget
from PySide6.QtCore import QTimer

# Imports del sistema
from views.centralstation_map_view import WorkspaceMapView
from controllers.centralstation_controller import get_workspace_state


# ========== COORDINADOR (CAPA INTERMEDIA) ==========

class CentralStationWindow(QMainWindow):
    """
    Ventana principal que coordina Vista y Controller.
    
    Responsabilidades:
    - Configurar polling timer
    - Llamar al controller
    - Pasar estado a la vista
    - NO contiene lógica de negocio
    """
    
    def __init__(self, svg_path: str, polling_interval_ms: int = 3000):
        super().__init__()
        
        self.setWindowTitle("Central Station - Workspace Map")
        self.resize(1600, 900)
        
        # Crear vista
        self.map_view = WorkspaceMapView(svg_path)
        
        # Layout
        central_widget = QWidget()
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.map_view)
        self.setCentralWidget(central_widget)
        
        # Timer de polling
        self.polling_timer = QTimer(self)
        self.polling_timer.timeout.connect(self._on_polling_tick)
        self.polling_timer.start(polling_interval_ms)
        
        # Primera actualización inmediata
        self._on_polling_tick()
    
    def _on_polling_tick(self):
        """
        Callback ejecutado cada N segundos.
        
        Flujo MVC:
        1. Llamar al Controller (capa de datos)
        2. Obtener WorkspaceState
        3. Pasar a la Vista (capa de presentación)
        """
        try:
            # Obtener estado del controller
            workspace_state = get_workspace_state()
            
            # Pasar a la vista
            self.map_view.update_state(workspace_state)
            
        except Exception as e:
            print(f"[ERROR] Polling falló: {e}")
            import traceback
            traceback.print_exc()


# ========== ENTRADA DE LA APLICACIÓN ==========

def main():
    """
    Punto de entrada de la aplicación.
    
    Inicializa:
    - QApplication
    - Ventana principal
    - Event loop
    """
    app = QApplication(sys.argv)
    
    # Ruta al SVG
    svg_path = "workspace_map.svg"
    
    # Crear y mostrar ventana
    window = CentralStationWindow(
        svg_path=svg_path,
        polling_interval_ms=3000  # 3 segundos
    )
    window.show()
    
    # Iniciar event loop
    sys.exit(app.exec())


if __name__ == "__main__":
    main()


# ========== NOTAS DE INTEGRACIÓN ==========

"""
ARQUITECTURA FINAL:

┌─────────────────────────────────────────┐
│   CentralStationWindow (Coordinador)    │
│   - QTimer polling                      │
│   - Llama get_workspace_state()         │
│   - Pasa estado a vista                 │
└──────────┬──────────────────────────────┘
           │
           │ workspace_state
           │
┌──────────▼──────────────────────────────┐
│   WorkspaceMapView (Vista)              │
│   - Renderiza SVG                       │
│   - Aplica estilos                      │
│   - Muestra eventos                     │
│   - Anima transiciones                  │
└──────────┬──────────────────────────────┘
           │
           │ SQL queries
           │
┌──────────▼──────────────────────────────┐
│   CentralStationController (Controller) │
│   - Consulta BD                         │
│   - Detecta eventos                     │
│   - Genera WorkspaceState               │
└─────────────────────────────────────────┘


SEPARACIÓN DE RESPONSABILIDADES:

1. Controller:
   - Lógica de negocio
   - Acceso a datos
   - Detección de cambios
   - Generación de eventos

2. Vista:
   - Renderizado SVG
   - Estilos visuales
   - Animaciones
   - Overlays

3. Coordinador:
   - Polling timer
   - Comunicación Controller ↔ Vista
   - Manejo de errores
   - Lifecycle de ventana


FLUJO DE DATOS (UNIDIRECCIONAL):

BD → Controller → Coordinador → Vista → Pantalla
     (read)      (poll)        (render)


NO HAY FLUJO INVERSO:
- La vista NUNCA llama al controller
- La vista NUNCA accede a BD
- La vista NUNCA genera eventos de negocio


POLLING CONFIGURABLE:

Recomendado para TV:
- 2-3 segundos: Actualización suave
- 5 segundos: Menos consumo

Recomendado para monitores:
- 1-2 segundos: Muy responsivo
- 3 segundos: Balance


MANEJO DE ERRORES:

Si el controller falla:
- La vista mantiene último estado válido
- No crashea
- Log de error

Si la vista falla:
- El controller sigue funcionando
- Se puede re-inicializar la vista


PERFORMANCE:

Optimizaciones:
1. Solo re-renderizar estaciones que cambiaron
2. Reutilizar overlays de eventos
3. Limitar animaciones concurrentes
4. Usar QGraphicsView (aceleración por hardware)
5. Cache de elementos SVG parseados


TESTING:

Vista (sin controller):
- Mock de WorkspaceState
- Validar renderizado
- Validar animaciones

Integración:
- Controller real + Vista real
- Validar flujo completo
- Validar polling


EXTENSIBILIDAD:

Fácil agregar:
- Zoom/pan del mapa
- Tooltips con detalles
- Panel lateral de eventos
- Filtros visuales
- Modos de visualización

Sin tocar:
- Controller
- Modelo
- Base de datos
"""
