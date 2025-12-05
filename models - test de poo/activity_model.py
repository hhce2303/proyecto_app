"""
🎯 ACTIVITY MODEL

Modelo para la gestión de actividades.

Tabla: Actividad (o similar)

TODO: Migrar funciones desde under_super.py
"""

from typing import List, Dict, Optional
from .database import DatabaseManager


class ActivityModel:
    """Modelo para gestión de actividades"""
    
    @staticmethod
    def get_all_activities() -> List[str]:
        """
        Obtiene lista de todas las actividades
        
        Returns:
            Lista de nombres de actividades
        """
        # TODO: Migrar desde under_super.get_activities()
        pass
    
    @staticmethod
    def get_activity_by_name(name: str) -> Optional[Dict]:
        """
        Obtiene una actividad por su nombre
        
        Returns:
            Dict con datos de la actividad o None
        """
        # TODO: Implementar
        pass
