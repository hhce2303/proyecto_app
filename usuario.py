


class User:
    def __init__(self, user_id, username, role, status):
        self.user_id = user_id
        self.username = username
        self.role = role
        self.status = status

    """
    Clase base abstracta para todas las vistas de la aplicación."""

    def __init__(self, root=None):
        self.root = root
        # Setup UI libraries
        self.UI = self._setup_ui_library()
        self.ui_factory = UIFactory(self.UI)
        # Estructura común (TODOS los dashboards tienen estos componentes)
        self.window = None
    
    
def open_dashboard(username: str, role: str, session_id: int = None, station: int = None):
    """Abre la ventana principal según el rol del usuario.
     Args:
         username (str): Nombre del usuario autenticado
         role (str): Rol del usuario (Operador, Supervisor, Lead Supervisor, Admin, etc.)
         session_id (int): ID de la sesión activa
         station (int): Estación asignada al usuario
     """  
     # 🎯 Router: Redirigir según rol
    print(f"🚀 Iniciando sesión para: {username} | Rol: {role} | Estación: {station} | Session ID: {session_id}")
    import blackboard
    if role == "Operador":
        # Operador: Ventana híbrida con registro de eventos y covers
        blackboard(
            username=username,
            session_id=session_id,
            station=station,
            root=None
        )
    
    elif role == "Supervisor":
        # Supervisor: Ventana de specials con gestión de marcas y breaks
        import supervisor_window
        supervisor_window.open_hybrid_events_supervisor(
            username=username,
            role="Supervisor",
            session_id=session_id,
            station=station,
            root=None
        )
    
    elif role == "Lead Supervisor":
        # Lead Supervisor: Usa la misma ventana de Supervisor con containers adicionales
        import supervisor_window
        supervisor_window.open_hybrid_events_supervisor(
            username=username,
            role="Lead Supervisor",
            session_id=session_id,
            station=station,
            root=None
        )
    
    elif role == "Admin":
        # Admin: Panel administrativo con Dashboard en tiempo real
        import admin_window
        admin_window.open_admin_panel(
            username=username,
            session_id=session_id,
            station=station,
            parent=None
        )
    
    else:
        # Rol no reconocido - mostrar error
        print(f"❌ ERROR: Rol '{role}' no reconocido")
        import tkinter as tk
        from tkinter import messagebox
        
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror(
            "Rol no válido",
            f"El rol '{role}' no está configurado en el sistema.\n\nContacta al administrador."
        )
        root.destroy()
        
        # Intentar volver al login
        try:
            import login
            login.show_login()
        except Exception as e:
            print(f"⚠️ No se pudo retornar al login: {e}")




