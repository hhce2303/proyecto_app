import customtkinter as ctk
import sys
import os
import urllib3
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
from utils.ui_factory import UIFactory
from controllers.healthcheck_controller import HealthcheckController


class TicketCard(ctk.CTkToplevel):

    def __init__(self, parent, ticket, username):
        self.controller = HealthcheckController(username)
        self.ui_factory = UIFactory(ctk)
        super().__init__(parent)
        self.ticket = ticket  # Guardar ticket como atributo de instancia
        self.title(f"Ticket #{self.ticket.get('id', '')} Details")
        self.geometry("450x360")
        try:
            self._create_header()
            self._create_content()
            self._setup_contents()
        except Exception as e:
            import traceback
            print("[TicketCard ERROR]", e)
            traceback.print_exc()
        self._get_status_color(status=None)
    
    def _get_status_color(self, status):
        if not status:
            return "#888888"
        status = status.lower()
        if status == "open":
            return "#2196F3"  # Azul
        elif status == "onhold":
            return "#F44336"  # Rojo
        elif status == "closed":
            return "#4CAF50"  # Verde
        elif status == "coordinate":
            return "#9C27B0"  # Morado
        else:
            return "#888888"  # Gris

    def _create_header(self):
        self.header_frame = self.ui_factory.frame(self, padding=10, bg_color="#333333")
        self.header_frame.pack(fill="x", side="top")
        # Aquí puedes agregar botones o elementos al toolbar si es necesario

    def _create_content(self):
        self.content_frame = self.ui_factory.frame(self, padding=10)
        self.content_frame.pack(fill="both", expand=True)

    def _setup_contents(self):
        desc_text = self.controller.strip_html(self.ticket.get('description', ''))
        # Agregar etiquetas y valores del ticket
        self.header_label = self.ui_factory.label(self.header_frame, text="Detalles del Ticket", font=("Segoe UI", 16, "bold"), text_color="#fff")
        self.header_label.pack(pady=5)

        


        self.ui_factory.label(self.content_frame, text=f"Ticket #{self.ticket.get('id', '')}", font=("Segoe UI", 18, "bold"), text_color="#2196F3").pack(anchor="w", pady=(0, 5))
        self.ui_factory.label(self.content_frame, text=f"Estado: {self.ticket.get('status', {}).get('name', '')}", font=("Segoe UI", 14, "bold"), text_color=self._get_status_color(self.ticket.get('status', {}).get('name', ''))).pack(anchor="w")
        self.ui_factory.label(self.content_frame, text=f"Asunto: {self.ticket.get('subject', '')}", font=("Segoe UI", 13), text_color="#fff").pack(anchor="w")
        self.ui_factory.label(self.content_frame, text=f"descripción:", font=("Segoe UI", 13), text_color="#fff").pack(anchor="w")
        self.text_box = ctk.CTkTextbox(self.content_frame, font=("Segoe UI", 13), text_color="#fff", width=240, height=80)
        self.text_box.pack(pady=(0, 10), fill="x", padx=5)
        self.text_box.insert("1.0", desc_text)
        self.text_box.configure(state="disabled")
        self.ui_factory.label(self.content_frame, text=f"Sitio: {self.ticket.get('site', {}).get('name', '')}", font=("Segoe UI", 13), text_color="#fff").pack(anchor="w")
        self.ui_factory.label(self.content_frame, text=f"Solicitante: {self.ticket.get('requester', {}).get('name', '')}", font=("Segoe UI", 13), text_color="#fff").pack(anchor="w")
        self.ui_factory.label(self.content_frame, text=f"Técnico: {self.ticket.get('technician', {}).get('name', '')}", font=("Segoe UI", 13), text_color="#fff").pack(anchor="w")
        self.ui_factory.label(self.content_frame, text=f"Creado: {self.ticket.get('created_time', {}).get('display_value', '')}", font=("Segoe UI", 13), text_color="#fff").pack(anchor="w")   


    def on_close_window(self):
        self.protocol("WM_DELETE_WINDOW", self._close_window)
        
    def _close_window(self):
        self.destroy()

if __name__ == "__main__":
    # Create a root window for the parent
    # Simulación de datos de un ticket
    ticket = HealthcheckController("prueba2").obtener_detalles_ticket("/145497")
    app = TicketCard(None, ticket, username="prueba2")
    app.mainloop()