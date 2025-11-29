"""
⚙️ CONFIGURACIÓN GLOBAL

Archivo de configuración central de la aplicación.

TODO: Centralizar configuraciones dispersas en el código
"""


class Config:
    """Configuración global de la aplicación"""
    
    # Base de datos
    DB_HOST = "localhost"
    DB_USER = "root"
    DB_PASSWORD = ""
    DB_NAME = "dailylog"
    DB_PORT = 3306
    
    # Aplicación
    APP_NAME = "Daily Log System"
    APP_VERSION = "2.0.0"
    
    # UI
    THEME = "dark"
    DEFAULT_FONT = ("Segoe UI", 10)
    TITLE_FONT = ("Segoe UI", 14, "bold")
    
    # Colores
    COLOR_PRIMARY = "#4a90e2"
    COLOR_SUCCESS = "#00c853"
    COLOR_WARNING = "#f5a623"
    COLOR_DANGER = "#d32f2f"
    COLOR_BG_DARK = "#1e1e1e"
    COLOR_BG_MEDIUM = "#2c2f33"
    COLOR_BG_LIGHT = "#2b2b2b"
    
    # Paths
    BACKUP_DIR = "backups/"
    LOG_DIR = "logs/"
    ICONS_DIR = "icons/"
    
    @classmethod
    def load_from_file(cls, config_path: str):
        """Carga configuración desde archivo INI"""
        # TODO: Implementar lectura de config.ini
        pass
