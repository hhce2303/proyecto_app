
from tkinter import messagebox
from utils.ui_factory import UIFactory
from models.healthcheck_model import cargar_healthcheck_activas, get_ticket_details
import tkinter as tk

from views.healthcheck_view import show_tickets_on_table
from views.modules.healthcheck_module_helpers import SimpleHTMLStripper
UIFactory = ui_factory = UIFactory(tk)



def clear_filters(module):
    """Limpia todos los filtros y recarga datos"""
    module.id_search_var.set("")
    module.site_search_var.set("")
    module.status_search_var.set("")
    module.requester_search_var.set("")
    module.current_page = 1
    module._load_data_paged()


def refresh_data(module):
    """Refresca datos limpiando el cache"""
    from models.healthcheck_model import _CACHE_SUPERVISORES
    _CACHE_SUPERVISORES["tickets"] = []
    _CACHE_SUPERVISORES["timestamp"] = None
    print("[INFO] Cache limpiado, recargando datos...")
    module.current_page = 1
    module._load_data_paged()

class HealthcheckController:

    def __init__(self, username):
        self.username = username
    
    def cargar_healthchecks_activos(self):
        data = cargar_healthcheck_activas()
        tickets = []
        if data and isinstance(data, dict):
            tickets = data.get("requests", [])
        return tickets  # Solo retorna datos
    


    def cargar_tickets_pagina(self, page=1, page_size=50, id=None, site=None, status=None, requester=None):
        """
        Carga tickets de una página específica usando paginación y permite filtrar por site.
        """
        start_index = (page - 1) * page_size + 1
        data = cargar_healthcheck_activas(
            row_size=page_size, 
            min_rows=page_size, 
            start_index=start_index, 
            id=id, 
            site=site, 
            status=status, 
            requester=requester
            )
        tickets = []
        if data and isinstance(data, dict):
            tickets = data.get("requests", [])
        return tickets
    
    def obtener_detalles_ticket(self, ticket_id):
        """Obtiene detalles de un ticket específico"""
        data = get_ticket_details(ticket_id)
        ticket = {}
        if data and isinstance(data, dict):
            ticket = data.get("request", {})
        return ticket
    
    @staticmethod
    def strip_html(html):
        s = SimpleHTMLStripper()
        s.feed(html)
        return s.get_data()
    
