"""
🔑 AUTHENTICATION CONTROLLER

Controlador para autenticación y gestión de sesiones.

Responsabilidades:
- Validar credenciales de login
- Crear y gestionar sesiones
- Verificar permisos según rol
- Logout

TODO: Migrar lógica desde login.py
"""

from models.user_model import UserModel


class AuthController:
    """Controlador de autenticación"""
    
    def __init__(self, view=None):
        """
        Inicializa el controlador
        
        Args:
            view: Vista asociada (LoginView)
        """
        self.view = view
        self.user_model = UserModel()
        self.current_user = None
        self.current_session = None
    
    def login(self, username: str, password: str, station: int) -> bool:
        """
        Procesa el inicio de sesión
        
        Args:
            username: Nombre de usuario
            password: Contraseña
            station: Número de estación
            
        Returns:
            True si el login fue exitoso
        """
        # TODO: Implementar lógica de login
        # 1. Validar inputs
        # 2. Autenticar con UserModel
        # 3. Crear sesión
        # 4. Abrir ventana correspondiente según rol
        pass
    
    def logout(self):
        """Cierra la sesión actual"""
        # TODO: Implementar
        pass
    
    def get_current_user(self):
        """Obtiene el usuario actual"""
        return self.current_user
