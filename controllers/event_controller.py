"""
📅 EVENT CONTROLLER

Controlador para operaciones CRUD de eventos.

TODO: Migrar lógica desde backend_super.py y main.py
"""

from models.event_model import EventModel


class EventController:
    """Controlador de eventos"""
    
    def __init__(self, view=None):
        self.view = view
        self.event_model = EventModel()
    
    def create_event(self, **kwargs):
        """Crea un nuevo evento"""
        # TODO: Implementar
        pass
    
    def update_event(self, event_id: int, **kwargs):
        """Actualiza un evento existente"""
        # TODO: Implementar
        pass
    
    def delete_event(self, event_id: int, username: str, reason: str):
        """Elimina un evento (soft delete)"""
        # TODO: Implementar
        pass
    
    def load_events(self, user_id: int, shift_start):
        """Carga eventos de un usuario"""
        # TODO: Implementar
        pass
