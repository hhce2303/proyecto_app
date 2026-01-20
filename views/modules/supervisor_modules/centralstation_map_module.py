



from utils.ui_factory import UIFactory
from controllers.centralstation_controller import CentralStationController

class CentralStationMapModule:
    def __init__(self, parent, username, UI=None, SheetClass=None):
        self.current_page = 1
        self.page_size = 50
        self.parent = parent
        self.username = username
        self.UI = UI
        self.ui_factory = UIFactory(UI)

        self.controller = CentralStationController()

        self.render_module()


    def render_module(self):
        """Renderiza el módulo del mapa de la central station"""
        # Aquí iría el código para cargar y mostrar el mapa
        self.load_data()
        self.create_container()
        self.visualize_map()


    def load_data(self):
        """Carga los datos necesarios para el módulo"""
        from controllers.centralstation_controller import CentralStationController

        controller = CentralStationController()
        data = controller.load_central_station_data()
        return data
    
    def create_container(self):
        """Crea el contenedor principal del módulo"""
        container = self.ui_factory.create_frame(self.parent)
        
    def visualize_map(self):
        """Visualiza el mapa de la estación central en un widget compatible con CTk/Tk"""
        import os
        from PIL import Image, ImageTk
        try:
            # Convertir SVG a PNG temporalmente (requiere cairosvg)
            import cairosvg
            svg_path = os.path.join(os.path.dirname(__file__), '../../workspace_map.svg')
            png_path = os.path.join(os.path.dirname(__file__), '../../workspace_map_temp.png')
            cairosvg.svg2png(url=svg_path, write_to=png_path)

            # Cargar la imagen PNG
            image = Image.open(png_path)
            photo = ImageTk.PhotoImage(image)

            # Crear un label compatible con CTk o Tk

            # CustomTkinter
            label = self.ui_factory.label(self.parent, image=photo)
            label.image = photo  # Referencia para evitar garbage collection
            label.pack(fill="both", expand=True)

        except Exception as e:
            print(f"[ERROR] visualize_map: {e}")
            import traceback
            traceback.print_exc()
        
