"""
✅ VALIDATORS

Funciones de validación de datos.

TODO: Centralizar validaciones dispersas en el código
"""

import re
from datetime import datetime


class Validators:
    """Validadores de datos"""
    
    @staticmethod
    def validate_username(username: str) -> bool:
        """Valida que el username no esté vacío"""
        return bool(username and username.strip())
    
    @staticmethod
    def validate_password(password: str) -> bool:
        """Valida que la password no esté vacía"""
        return bool(password and password.strip())
    
    @staticmethod
    def validate_station(station: str) -> bool:
        """Valida que la estación sea un número válido"""
        return station.isdigit() and int(station) > 0
    
    @staticmethod
    def validate_datetime(datetime_str: str) -> bool:
        """Valida formato de fecha/hora"""
        try:
            datetime.strptime(datetime_str, "%Y-%m-%d %H:%M:%S")
            return True
        except ValueError:
            return False
    
    @staticmethod
    def validate_number(value: str) -> bool:
        """Valida que sea un número"""
        try:
            float(value)
            return True
        except ValueError:
            return False
