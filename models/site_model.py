"""
🏢 SITE MODEL

Modelo para la gestión de sitios.

Tabla: Sitios
Campos:
- ID_Sitio
- Nombre_Sitio
- etc.

TODO: Migrar funciones desde under_super.py
"""

from typing import List, Dict, Optional
from .database import DatabaseManager


class SiteModel:
    """Modelo para gestión de sitios"""
    
    @staticmethod
    def get_all_sites() -> List[str]:
        """
        Obtiene lista de todos los sitios en formato "Nombre_Sitio (ID_Sitio)"
        
        Returns:
            Lista de sitios formateados
        """
        # TODO: Migrar desde under_super.get_sites()
        pass
    
    @staticmethod
    def get_site_by_id(site_id: int) -> Optional[Dict]:
        """
        Obtiene un sitio por su ID
        
        Returns:
            Dict con datos del sitio o None
        """
        # TODO: Implementar
        pass
    
    @staticmethod
    def get_site_name(site_id: int) -> Optional[str]:
        """
        Obtiene el nombre de un sitio por su ID
        
        Returns:
            Nombre del sitio o None
        """
        # TODO: Implementar
        pass
