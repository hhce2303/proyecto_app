"""
⭐ SPECIAL MODEL

Modelo para la gestión de specials (eventos especiales).

Tabla: specials
Campos:
- ID_special
- FechaHora
- ID_Sitio
- Nombre_Actividad
- Cantidad
- Camera
- Descripcion
- Usuario
- Supervisor
- Time_Zone
- marked_status (done, flagged, NULL)
- marked_by
- etc.

TODO: Migrar funciones desde backend_super.py
"""

from typing import Optional, List, Dict
from datetime import datetime
from .database import DatabaseManager


class SpecialModel:
    """Modelo para gestión de specials"""
    
    @staticmethod
    def create_or_update_special(fecha_hora: datetime, usuario: str, 
                                 actividad: str, supervisor: str, **kwargs) -> int:
        """
        Crea o actualiza un special (upsert)
        
        Returns:
            ID del special
        """
        # TODO: Implementar lógica de upsert
        pass
    
    @staticmethod
    def get_specials_by_supervisor(supervisor: str, shift_start: datetime) -> List[Dict]:
        """
        Obtiene specials asignados a un supervisor desde el inicio de su turno
        
        Returns:
            Lista de specials
        """
        # TODO: Implementar
        pass
    
    @staticmethod
    def get_unassigned_specials(shift_start: datetime) -> List[Dict]:
        """
        Obtiene specials sin marcar (marked_status vacío)
        
        Returns:
            Lista de specials sin asignar
        """
        # TODO: Implementar
        pass
    
    @staticmethod
    def mark_special(special_id: int, status: str, marked_by: str) -> bool:
        """
        Marca un special como 'done' o 'flagged'
        
        Args:
            special_id: ID del special
            status: 'done' o 'flagged'
            marked_by: Usuario que marca
            
        Returns:
            True si se marcó correctamente
        """
        # TODO: Implementar
        pass
    
    @staticmethod
    def assign_supervisor(special_id: int, supervisor: str) -> bool:
        """
        Asigna un supervisor a un special
        
        Returns:
            True si se asignó correctamente
        """
        # TODO: Implementar
        pass
