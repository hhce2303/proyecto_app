"""
📊 CAPA DE MODELO (Models Layer)

Este paquete contiene todos los modelos de datos y la lógica de acceso a la base de datos.
Cada modelo representa una tabla o entidad del sistema.

Responsabilidades:
- Acceso y manipulación de datos en la base de datos
- Validaciones a nivel de datos
- Relaciones entre entidades
- Queries SQL encapsuladas

Archivos:
- database.py: Gestión de conexiones a la base de datos
- user_model.py: Gestión de usuarios, roles y autenticación
- event_model.py: Gestión de eventos (tabla Eventos)
- site_model.py: Gestión de sitios y actividades
- cover_model.py: Gestión de covers (programados y realizados)
- session_model.py: Gestión de sesiones (login, logout)
"""

# ==================== DATABASE ====================
from .database import get_connection

# ==================== USER & STATUS ====================
# Las funciones de usuarios están distribuidas en varios modelos
# from .status_model import get_user_status_bd

# ==================== EVENT ====================
from .event_model import add_event

# ==================== SITE & ACTIVITIES ====================
from .site_model import (
    get_sites,
    get_activities
)

# ==================== COVER ====================
from .cover_model import (
    request_covers,
    insertar_cover
)

# ==================== SESSION ====================
from .session_model import (
    auto_login,
    logout_silent
)

__all__ = [
    # Database
    'get_connection',
    
    # User
    'load_users',
    'get_user_status_bd',
    'users_list',
    
    # Event
    'add_event',
    
    # Site & Activities
    'get_sites',
    'get_activities',
    
    # Cover
    'request_covers',
    'insertar_cover',
    
    # Session
    'auto_login',
    'logout_silent',
]
# from .site_model import SiteModel
# from .activity_model import ActivityModel
# from .cover_model import CoverModel
# from .shift_model import ShiftModel
# from .audit_model import AuditModel
# from .backup_model import BackupModel
