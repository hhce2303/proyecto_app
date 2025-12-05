# models/session_model.py
from models.database import get_connection
from datetime import datetime
from tkinter import ttk, messagebox, simpledialog, filedialog

import main_super

_preserved_statuses_state = {}

def logout_silent(session_id, station):
    """Logout without showing login UI; updates Sesiones and frees Estaciones.
    Preserva el estado Statuses si es Operador con Statuses=2."""
    global _preserved_statuses_state
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Obtener username de la sesión actual
        cursor.execute(
            """
            SELECT s.ID_user
            FROM sesion s
            WHERE s.ID = %s
            """,
            (int(session_id),)
        )
        sesion_data = cursor.fetchone()
        
        if sesion_data:
            username = sesion_data[0]
            
            # Buscar la última sesión de este usuario para verificar Statuses
            cursor.execute(
                """
                SELECT s.Statuses, u.Rol
                FROM sesion s
                INNER JOIN user u ON s.ID_user = u.Nombre_Usuario
                WHERE s.ID_user = %s
                ORDER BY s.ID DESC
                LIMIT 1
                """,
                (username,)
            )
            last_session = cursor.fetchone()
            
            if last_session:
                statuses_state, rol = last_session
                # Preservar Statuses=2 solo para Operadores
                # Nota: Statuses puede ser NULL(normal) o 2(operador con acceso covers)
                if rol == "Operador" and statuses_state == 2:
                    _preserved_statuses_state[username] = 2
                    print(f"[DEBUG] logout_silent - Preservando Statuses=2 para {username}")
                elif username in _preserved_statuses_state:
                    # Limpiar si ya no es Statuses=2
                    del _preserved_statuses_state[username]
        
        log_out_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute(
            """
            UPDATE sesion 
            SET Log_Out = %s, Active = '0'
            WHERE ID = %s
            """,
            (log_out_time, int(session_id))
        )
        cursor.execute(
            """
            UPDATE Estaciones
            SET User_Logged = NULL
            WHERE Station_Number=%s
            """,
            (station,)
        )
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"[ERROR] logout_silent: {e}")
        return False

def auto_login(username, station, password="1234", parent=None, silent=True):
    """Perform login programmatically and open main window, without showing login UI.

    Returns (ok, session_id, role) and opens main_super.open_main_window on success.
    """
    try:
        # Validate station
        if isinstance(station, str):
            if not station.isdigit():
                raise ValueError("Station must be numeric")
            station = int(station)

        conn = get_connection()
        cursor = conn.cursor()

        # Validate user
        cursor.execute(
            "SELECT Contraseña, Rol FROM user WHERE Nombre_Usuario=%s",
            (username,)
        )
        result = cursor.fetchone()
        if not result:
            raise ValueError("Usuario no encontrado")
        db_password, role = result
        if db_password != password:
            raise ValueError("Contraseña incorrecta")

        # Start session - Verificar si el usuario tenía Statuses=2 en su última sesión
        global _preserved_statuses_state
        initial_active = "1"  # Siempre 1 para sesión activa
        initial_statuses = None  # Por defecto NULL
        
        # Si es Operador, buscar Statuses=2 en su última sesión O en el diccionario preservado
        if role == "Operador":
            print(f"[DEBUG] auto_login - Es Operador: {username}")
            print(f"[DEBUG] auto_login - Diccionario preservado: {_preserved_statuses_state}")
            
            # Primero verificar diccionario (más reciente)
            if username in _preserved_statuses_state:
                if _preserved_statuses_state[username] == 2:
                    initial_statuses = 2
                    print(f"[DEBUG] auto_login - Restaurando Statuses=2 para {username} (desde diccionario)")
                del _preserved_statuses_state[username]
            else:
                # Si no está en diccionario, buscar en BD la última sesión CERRADA
                print(f"[DEBUG] auto_login - Buscando última sesión cerrada en BD para {username}")
                cursor.execute(
                    """
                    SELECT Statuses
                    FROM sesion
                    WHERE ID_user = %s AND Active = 0
                    ORDER BY ID DESC
                    LIMIT 1
                    """,
                    (username,)
                )
                last_status = cursor.fetchone()
                print(f"[DEBUG] auto_login - Última sesión cerrada encontrada: {last_status}")
                if last_status and last_status[0] == 2:
                    initial_statuses = 2
                    print(f"[DEBUG] auto_login - Restaurando Statuses=2 para {username} (desde BD)")
        
        print(f"[DEBUG] auto_login - Insertando sesión con Active={initial_active}, Statuses={initial_statuses}")
        cursor.execute(
            """
            INSERT INTO sesion (ID_user, Log_in, ID_estacion, Log_out, Active, Statuses)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (username, datetime.now(), station, None, initial_active, initial_statuses)
        )
        cursor.execute("SELECT LAST_INSERT_ID()")
        session_id = cursor.fetchone()[0]

        # Check station availability
        cursor.execute("SELECT User_Logged FROM Estaciones WHERE Station_Number=%s", (station,))
        row = cursor.fetchone()
        if row and row[0]:
            # Occupied
            conn.commit(); conn.close()
            raise RuntimeError(f"La estación {station} ya está siendo usada por {row[0]}")

        # Update station status (insert as in UI flow)
        cursor.execute(
            """INSERT INTO estaciones (User_Logged, Station_Number)
            VALUES (%s, %s)
            """,
            (username, station)
        )
        conn.commit(); conn.close()

        # If a previous main window exists (parent), destroy it before opening the new session UI
        try:
            if parent is not None and hasattr(parent, 'winfo_exists') and parent.winfo_exists():
                parent.destroy()
                # Ensure Tk will create a fresh root for the next window
                try:
                    import tkinter as _tk
                    _tk._default_root = None
                except Exception:
                    pass
        except Exception as e:
            print(f"[WARN] no se pudo destruir la ventana anterior: {e}")

        # Open main window
        try:
            if not silent:
                messagebox.showinfo("Login", f"Bienvenido {username} ({role})")
        except Exception:
            pass

        # 🎯 Redirigir SIEMPRE a través del router main_super (patrón MVC)
        print(f"[DEBUG] auto_login - Redirigiendo a main_super.open_main_window | Usuario: {username} | Rol: {role}")
        main_super.open_main_window(username, station, role, session_id)
        
        return True, session_id, role
    except Exception as e:
        print(f"[ERROR] auto_login: {e}")
        try:
            messagebox.showerror("Auto Login", str(e), parent=parent)
        except Exception:
            pass
        return False, None, None