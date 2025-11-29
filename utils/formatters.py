"""
🎨 FORMATTERS

Funciones de formateo de datos.

TODO: Centralizar formateos dispersos en el código
"""

from datetime import datetime


class Formatters:
    """Formateadores de datos"""
    
    @staticmethod
    def format_datetime(dt: datetime, format: str = "%Y-%m-%d %H:%M:%S") -> str:
        """Formatea un datetime a string"""
        return dt.strftime(format) if dt else ""
    
    @staticmethod
    def format_site(site_id: int, site_name: str) -> str:
        """Formatea sitio como 'Nombre (ID)'"""
        return f"{site_name} ({site_id})"
    
    @staticmethod
    def parse_site_id(site_str: str) -> int:
        """Extrae el ID de un string con formato 'Nombre (ID)'"""
        import re
        match = re.search(r'\((\d+)\)$', site_str)
        return int(match.group(1)) if match else 0
    
    @staticmethod
    def format_number(value: float, decimals: int = 2) -> str:
        """Formatea un número con decimales"""
        return f"{value:.{decimals}f}"
