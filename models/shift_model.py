"""
⏰ SHIFT MODEL

Modelo para la gestión de turnos (START SHIFT / END OF SHIFT).

Responsabilidades:
- Detectar si un usuario tiene turno activo
- Obtener última hora de START SHIFT
- Crear eventos de START/END SHIFT

TODO: Migrar funciones desde backend_super.py
"""

from typing import Optional
from datetime import datetime
from .database import DatabaseManager


class ShiftModel:
    """Modelo para gestión de turnos"""
    
    @staticmethod
    def get_last_shift_start(username: str) -> Optional[datetime]:
        """
        Obtiene la última hora de START SHIFT de un usuario
        
        Returns:
            Datetime del último START SHIFT o None
        """
        # TODO: Implementar
        pass
    
    @staticmethod
    def is_shift_active(username: str) -> bool:
        """
        Verifica si un usuario tiene un turno activo
        (START SHIFT sin END OF SHIFT posterior)
        
        Returns:
            True si el turno está activo
        """
        # TODO: Implementar Dinamic_button_Shift()
        pass
    
    @staticmethod
    def start_shift(username: str, user_id: int, station: int) -> int:
        """
        Crea un evento START SHIFT
        
        Returns:
            ID del evento creado
        """
        # TODO: Implementar
        pass
    
    @staticmethod
    def end_shift(username: str, user_id: int, station: int) -> int:
        """
        Crea un evento END OF SHIFT
        
        Returns:
            ID del evento creado
        """
        # TODO: Implementar
        pass
