"""
🎯 CONTROLADOR PRINCIPAL - MVC Pattern
Recibe credenciales de login.py y redirecciona a la función de rol correspondiente.
NO genera UI propia - delega todo a backend_super.py
"""

import backend_super


def open_main_window(username, station, role, session_id):
    """
    Controlador principal que redirecciona según el rol del usuario.
    
    Args:
        username (str): Nombre del usuario autenticado
        station (str): Estación asignada al usuario
        role (str): Rol del usuario (Operator, Supervisor, Lead Supervisor, etc.)
        session_id (int): ID de la sesión activa
    """
    # Inicializar tablas de backup al inicio de la aplicación
    try:
        backend_super.create_backup_tables()
        print(f"✅ Tablas de backup inicializadas correctamente")
    except Exception as e:
        print(f"⚠️ Error al inicializar tablas de backup: {e}")
    
    # 🎯 Router: Redirigir según rol
    print(f"🚀 Iniciando sesión para: {username} | Rol: {role} | Estación: {station} | Session ID: {session_id}")
    
    if role == "Operador":
        # Operador: Ventana híbrida con registro de eventos y covers
        import operator_window
        operator_window.open_hybrid_events(
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
            session_id=session_id,
            station=station,
            root=None
        )
    
    elif role == "Lead Supervisor":
        # Lead Supervisor: Ventana completa con permisos administrativos
        import lead_supervisor_window
        lead_supervisor_window.open_hybrid_events_lead_supervisor(
            username=username,
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
