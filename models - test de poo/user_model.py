"""
👤 USER MODEL

Modelo para la gestión de usuarios y autenticación.

Tabla: user
Campos:
- ID_Usuario
- Nombre_Usuario
- Contraseña
- Rol (Usuario, Supervisor, Lead Supervisor)
- etc.

TODO: Migrar funciones desde login.py y backend_super.py
"""

from typing import Optional, List, Dict
from .database import DatabaseManager


class UserModel:
    """Modelo para gestión de usuarios"""
    
    @staticmethod
    def authenticate(username: str, password: str) -> Optional[Dict]:
        """
        Autentica un usuario
        
        Args:
            username: Nombre de usuario
            password: Contraseña
            
        Returns:
            Dict con datos del usuario si es válido, None si no
        """
        # TODO: Implementar lógica de autenticación
        pass
    
    @staticmethod
    def get_by_username(username: str) -> Optional[Dict]:
        """
        Obtiene un usuario por su nombre de usuario
        
        Args:
            username: Nombre de usuario
            
        Returns:
            Dict con datos del usuario o None
        """
        # TODO: Implementar
        pass
    
    @staticmethod
    def get_all_users() -> List[str]:
        """
        Obtiene lista de todos los nombres de usuario
        
        Returns:
            Lista de nombres de usuario
        """
        # TODO: Implementar
        pass
    
    @staticmethod
    def create_user(username: str, password: str, role: str) -> int:
        """
        Crea un nuevo usuario
        
        Args:
            username: Nombre de usuario
            password: Contraseña
            role: Rol del usuario
            
        Returns:
            ID del usuario creado
        """
        # TODO: Implementar
        pass
