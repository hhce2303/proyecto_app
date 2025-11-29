"""
📋 CONSTANTS

Constantes globales de la aplicación.

TODO: Centralizar constantes dispersas en el código
"""


class Constants:
    """Constantes de la aplicación"""
    
    # Roles de usuario
    ROLE_USER = "Usuario"
    ROLE_SUPERVISOR = "Supervisor"
    ROLE_LEAD_SUPERVISOR = "Lead Supervisor"
    
    # Estados de marcado
    STATUS_DONE = "done"
    STATUS_FLAGGED = "flagged"
    STATUS_UNASSIGNED = None
    
    # Actividades especiales
    ACTIVITY_START_SHIFT = "START SHIFT"
    ACTIVITY_END_SHIFT = "END OF SHIFT"
    
    # Grupos especiales
    SPECIAL_GROUPS = ["AS", "KG", "HUD", "PE", "SCH", "WAG", "LT", "DT"]
    
    # Mensajes
    MSG_LOGIN_SUCCESS = "Inicio de sesión exitoso"
    MSG_LOGIN_FAILED = "Credenciales inválidas"
    MSG_NO_PERMISSION = "No tienes permisos para realizar esta acción"
    MSG_SAVE_SUCCESS = "Cambios guardados correctamente"
    MSG_DELETE_SUCCESS = "Registro eliminado correctamente"
    
    # Códigos de error
    ERR_DB_CONNECTION = 1001
    ERR_INVALID_CREDENTIALS = 1002
    ERR_PERMISSION_DENIED = 1003
