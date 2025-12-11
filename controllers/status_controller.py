
import sys
from pathlib import Path

# Agregar el directorio raíz del proyecto al path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from models.status_model import get_user_status_bd, set_new_status


class StatusController:
    """Controlador para gestionar el status de usuarios"""
    
    def __init__(self, username):
        self.username = username
    
    def get_current_status(self):
        """Obtiene el status numérico actual del usuario"""
        return get_user_status_bd(self.username)
    
    def update_status(self, new_status_value):
        """Actualiza el status del usuario
        
        Args:
            new_status_value (int): 0=Disponible, 1=Ocupado, -1=No disponible
            
        Returns:
            bool: True si se actualizó correctamente
        """
        if new_status_value not in [0, 1, -1]:
            print(f"[WARNING] Valor de status inválido: {new_status_value}")
            return False
        
        success = set_new_status(new_status_value, self.username)
        return success


# ==================== HELPER PARA VISTAS ====================
# La vista debería usar estas funciones para mapear valores a texto visual

def get_status_display_text(status_value):
    """Convierte valor numérico a texto con emoji (para usar en vistas)
    
    Args:
        status_value (int): 0, 1 o -1
        
    Returns:
        str: Texto formateado con emoji
    """
    if status_value == 0:
        return "🟢 Disponible"
    elif status_value == 1:
        return "🟡 Ocupado"
    elif status_value == -1:
        return "🔴 No disponible"
    else:
        return "⚪ Desconocido"