"""
⭐ SPECIAL CONTROLLER

Controlador para operaciones de specials.

TODO: Migrar lógica desde backend_super.py
"""

from models.special_model import SpecialModel


class SpecialController:
    """Controlador de specials"""
    
    def __init__(self, view=None):
        self.view = view
        self.special_model = SpecialModel()
    
    def send_to_supervisor(self, events: list, supervisor: str):
        """Envía eventos a un supervisor como specials"""
        # TODO: Implementar lógica de envío
        pass
    
    def mark_special(self, special_id: int, status: str, marked_by: str):
        """Marca un special como done/flagged"""
        # TODO: Implementar
        pass
    
    def load_specials(self, supervisor: str, shift_start):
        """Carga specials de un supervisor"""
        # TODO: Implementar
        pass
