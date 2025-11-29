"""
📅 EVENT MODEL

Modelo para la gestión de eventos (tabla Eventos).

Tabla: Eventos
Campos:
- ID_Eventos
- FechaHora
- ID_Sitio
- Nombre_Actividad
- Cantidad
- Camera
- Descripcion
- ID_Usuario
- etc.

TODO: Migrar funciones desde backend_super.py y main.py
"""

from typing import Optional, List, Dict
from datetime import datetime
from .database import DatabaseManager


class EventModel:
    """Modelo para gestión de eventos"""
    
    @staticmethod
    def create_event(user_id: int, fecha_hora: datetime, sitio_id: int, 
                    actividad: str, cantidad: int, camera: str, 
                    descripcion: str) -> int:
        """
        Crea un nuevo evento
        
        Returns:
            ID del evento creado
        """
        # TODO: Implementar
        pass
    
    @staticmethod
    def get_events_by_user_shift(user_id: int, shift_start: datetime) -> List[Dict]:
        """
        Obtiene eventos de un usuario desde el inicio de su turno
        
        Args:
            user_id: ID del usuario
            shift_start: Fecha/hora de inicio del turno
            
        Returns:
            Lista de eventos
        """
        # TODO: Implementar
        pass
    
    @staticmethod
    def update_event(event_id: int, **kwargs) -> bool:
        """
        Actualiza un evento existente
        
        Returns:
            True si se actualizó correctamente
        """
        # TODO: Implementar
        pass
    
    @staticmethod
    def delete_event(event_id: int, username: str, reason: str) -> bool:
        """
        Mueve un evento a la papelera (soft delete)
        
        Returns:
            True si se eliminó correctamente
        """
        # TODO: Implementar usando safe_delete
        pass
