"""
Views package - Vistas de la aplicación usando patrón Dashboard

Arquitectura:
    Dashboard (clase base super general)
        ↓ hereda
    OperatorDashboard / SupervisorDashboard / AdminDashboard
        ↓ usa
    Módulos específicos (daily, specials, covers, etc.)
- NO contener lógica de negocio

Archivos:
- login_view.py: Ventana de inicio de sesión
- main_view.py: Ventana principal para usuarios regulares
- supervisor_view.py: Ventana para supervisores
- lead_supervisor_view.py: Ventana para lead supervisors
- hybrid_events_view.py: Vista híbrida de eventos
- specials_view.py: Vista de specials
- covers_view.py: Vista de covers
- admin_view.py: Panel administrativo

Subcarpeta components/:
- Componentes reutilizables de UI
"""

# Importaciones de vistas cuando estén disponibles
# from .login_view import LoginView
# from .main_view import MainView
# from .supervisor_view import SupervisorView
# from .lead_supervisor_view import LeadSupervisorView
