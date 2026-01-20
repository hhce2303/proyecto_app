from controllers.healthcheck_controller import HealthcheckController
from utils.ui_factory import UIFactory

class AdminHCModules:

    def __init__(self, container, username, ui_factory, UI=None):

        self.container = container
        self.username = username
        self.ui_factory = ui_factory
        self.UI = UI

        self.controller = HealthcheckController(username)
        self.render_module()

    def render_module(self):
        self._create_header()
        self._create_container()
        self._load_console()

    def _create_header(self):
        """Crea el encabezado del módulo"""
        header_frame = self.ui_factory.frame(self.container)
        header_frame.pack(fill='x', side='top', pady=5)

        title_label = self.ui_factory.label(
            header_frame,
            text="HealthCheck Administration Module",
            font=("Arial", 16, "bold"),
            text_color="#ffffff"
        )
        title_label.pack(side='left', padx=10)

    def _create_container(self):
        """Crea el contenedor principal del módulo"""
        console_frame = self.ui_factory.frame(self.container)
        console_frame.pack(fill='both', expand=True, padx=10, pady=10)

    def _load_console(self):
        """Carga la consola de administración de HealthCheck"""

        console_frame = self.ui_factory.frame(self.container)
        console_frame.pack(fill='both', expand=True, padx=10, pady=10)

        console_label = self.ui_factory.label(
            console_frame,
            text="Admin Console Placeholder",
            font=("Arial", 14),
            text_color="#ffffff"
        )
        console_label.pack(pady=20)

        load_btn = self.ui_factory.button(
            console_frame,
            text="Load json data",
            command=lambda: self.controller.sync_healthcheck_data_optimized(),
            width=150,
            fg_color="#238636"
        )
        load_btn.pack(pady=10)




