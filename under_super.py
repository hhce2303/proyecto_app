from tkinter import messagebox
import traceback
from unittest import result
import backend_super
import tkinter as tk
from tkinter import ttk
from datetime import datetime, date, timedelta
from mysql.connector import Error
import pymysql
from pathlib import Path
# al inicio del .spec
from PyInstaller.utils.hooks import collect_all
from PyInstaller.building.build_main import Analysis

import login

now = datetime.now()

ICON_PATH = r"\\192.168.7.12\Data SIG\Central Station SLC-COLOMBIA\1. Daily Logs - Operators\DataBase\icons"
import pyodbc

# 📂 Ruta compartida para el archivo de configuración
CONFIG_PATH = Path=r"\\192.168.7.12\Data SIG\Central Station SLC-COLOMBIA\1. Daily Logs - Operators\DataBase\Base de Datos\roles_config.json"




def get_connection():
    """
    Establece una conexión segura con la base de datos MySQL.
    Lanza errores claros en caso de fallo (credenciales, servidor, etc.).
    """
    try:
        conn = pymysql.connect(
            host="192.168.101.135",
            user="app_user",
            password="1234",
            database="daily",
            port=3306
        )
        print("✅ Conexión exitosa")
    except pymysql.Error as e:
        print("❌ Error de conexión:", e)
        return None
    return conn
    
def get_station(username):
    conn = get_connection()
    station = None
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT ID_estacion
            FROM sesion
            WHERE ID_user = %s
            """,
            (username,)
        )
        result = cursor.fetchone()
        print(f"[DEBUG] al obtener estación: {station}")
        if result:
            station = result[0]
    except pymysql.Error as e:
        print(f"[ERROR] al obtener estación: {e}")
    finally:
        cursor.close()
        conn.close()
    return station

# Cargar usuarios desde la base de datos
def load_users():
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT Nombre_Usuario FROM user ORDER BY Nombre_Usuario")
        users = [row[0] for row in cursor.fetchall()]
        cursor.close()
        conn.close()
        return users
    except Exception as e:
        print(f"[ERROR] load_users: {e}")
        return ["Ana", "Carlos", "Diego", "Elena", "Juan", "Luis", "Maria", "Miguel", "Pedro", "Sofia"]

users_list = load_users()

# implementacion de covers...:

# - solicita un cover para el usuario dado. desde la ui principal de operador
def request_covers(username, time_request, reason, aprvoved):

    confirmed = messagebox.askyesno("Esta seguro", "¿Está seguro de solicitar el cover?")
    
    if not confirmed:
        print("[DEBUG] Solicitud de cover cancelada por el usuario")
        return None
#Solicita un cover para el usuario dado.
    
    #Args:
        #username: Nombre de usuario que solicita el cover
        #cover_type: Tipo de cover (e.g., "break", "lunch")
        #reason: Razón para la solicitud del cover
    conn = get_connection()
    ID_cover = None
    try:
        cursor = conn.cursor()
        
        # ⭐ VERIFICAR SI YA TIENE UN COVER ACTIVO (is_Active = 1)
        cursor.execute(
            """
            SELECT ID_Cover, Time_request, is_Active
            FROM covers_programados
            WHERE ID_user = %s
            AND is_Active = 1
            ORDER BY Time_request DESC
            LIMIT 1
            """,
            (username,)
        )
        active_cover = cursor.fetchone()
        
        if active_cover:
            # Ya tiene un cover activo pendiente, no puede solicitar otro
            messagebox.showwarning(
                "Cover Activo Pendiente", 
                f"Ya tienes un cover activo solicitado a las {active_cover[1].strftime('%H:%M:%S')}.\n\n"
                f"No puedes solicitar otro cover hasta que este sea procesado o cancelado.\n\n"
                f"Estado: Pendiente de aprobación/ejecución"
            )
            print(f"[DEBUG] Solicitud rechazada: cover activo existente (ID: {active_cover[0]})")
            cursor.close()
            conn.close()
            return None
        
        # ⭐ VERIFICAR LÍMITE DE TIEMPO: 10 minutos entre solicitudes (solo del día actual)
        hoy_inicio = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        
        cursor.execute(
            """
            SELECT Time_request, is_Active
            FROM covers_programados
            WHERE ID_user = %s
            AND DATE(Time_request) = CURDATE()
            ORDER BY Time_request DESC
            LIMIT 1
            """,
            (username,)
        )
        last_request = cursor.fetchone()
        
        if last_request and last_request[0]:
            now = datetime.now()
            time_diff = now - last_request[0]
            minutes_diff = time_diff.total_seconds() / 60
            
            print(f"[DEBUG] Última solicitud: {last_request[0]}, Ahora: {now}, Diferencia: {minutes_diff:.1f} min, is_Active: {last_request[1]}")
            
            if minutes_diff < 10:
                remaining_minutes = 10 - minutes_diff
                messagebox.showwarning(
                    "Espera requerida", 
                    f"Debes esperar {remaining_minutes:.1f} minutos más antes de solicitar otro cover.\n\n"
                    f"Última solicitud: {last_request[0].strftime('%Y-%m-%d %H:%M:%S')}\n"
                    f"Próxima solicitud disponible: {(last_request[0] + timedelta(minutes=10)).strftime('%H:%M:%S')}"
                )
                print(f"[DEBUG] Solicitud rechazada: faltan {remaining_minutes:.1f} minutos")
                cursor.close()
                conn.close()
                return None

        cursor.execute(
            """
            SELECT ID_estacion
            FROM sesion
            WHERE ID_user = %s
            ORDER BY ID DESC
            LIMIT 1
            """,
            (username,)
        )
        station = cursor.fetchone()

        print(f"[DEBUG] Estación obtenida: {station}")
        cursor.execute(
            """
            INSERT INTO covers_programados (ID_user, Time_request, Station, Reason, Approved, is_Active)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (username, time_request, station, reason, aprvoved, 1)
        )
        conn.commit()
        print("[DEBUG] Cover solicitado correctamente ✅")
        # 🔹 Obtener último ID insertado
        cursor.execute("SELECT LAST_INSERT_ID()")
        ID_cover = cursor.fetchone()[0]
        print(f"[DEBUG] Nuevo ID_cover generado: {ID_cover}")
        messagebox.showinfo("Solicitud Exitosa", f"Cover solicitado correctamente.")

    except pymysql.Error as e:
        print(f"[ERROR] al solicitar cover: {e}")
    finally:
        cursor.close()
        conn.close() 
    return ID_cover

# - inserta un cover realizado para el usuario dado. desde la ui principal de operador, usando el ID del 
# cover programado.
def insertar_cover(username, Covered_by, Motivo, session_id, station):
    ID_cover = None
    Cover_in = (now + timedelta(minutes=2)).strftime("%Y-%m-%d %H:%M:%S")
    Activo = False
    Cover_Out= None
    tiene_cover_programado = False
    
    # ⭐ VERIFICAR SI TIENE COVER PROGRAMADO (covers_programados O gestion_breaks_programados)
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # 1. Buscar en covers_programados (sistema antiguo)
        cursor.execute(
            """
            SELECT cp.ID_Cover
            FROM covers_programados cp
            WHERE cp.ID_user = %s
            AND cp.Approved = 1
            AND cp.is_Active = 1
            ORDER BY cp.ID_Cover DESC
            LIMIT 1
            """,
            (username,)
        )
        result = cursor.fetchone()
        
        if result is not None:
            ID_cover = result[0]
            tiene_cover_programado = True
            print(f"[DEBUG] Cover programado encontrado en covers_programados - ID_cover: {ID_cover}")
        else:
            # 2. Buscar en gestion_breaks_programados (breaks programados por supervisor)
            # Necesitamos ID_Usuario para buscar
            cursor.execute("SELECT ID_Usuario FROM user WHERE Nombre_Usuario = %s", (username,))
            user_row = cursor.fetchone()
            
            if user_row:
                id_usuario = user_row[0]
                
                # Buscar break programado activo en una ventana de +/- 5 minutos de la hora actual
                cursor.execute(
                    """
                    SELECT gbp.ID_cover
                    FROM gestion_breaks_programados gbp
                    WHERE gbp.User_covered = %s
                    AND gbp.is_Active = 1
                    AND ABS(TIMESTAMPDIFF(MINUTE, gbp.Fecha_hora_cover, NOW())) <= 5
                    ORDER BY ABS(TIMESTAMPDIFF(MINUTE, gbp.Fecha_hora_cover, NOW())) ASC
                    LIMIT 1
                    """,
                    (id_usuario,)
                )
                break_result = cursor.fetchone()
                
                if break_result is not None:
                    ID_cover = break_result[0]
                    tiene_cover_programado = True
                    print(f"[DEBUG] Break programado encontrado en gestion_breaks_programados - ID_cover: {ID_cover}")
        
        # Si no se encontró ningún cover programado, preguntar si es emergencia
        if not tiene_cover_programado:
            print("[DEBUG] No se encontró cover/break programado. Registrando como cover de emergencia...")
            # Preguntar al usuario si desea registrar cover de emergencia
            confirmacion = messagebox.askyesno(
                "Cover de Emergencia",
                "No tienes un cover programado aprobado.\n\n"
                "¿Deseas registrar este cover como EMERGENCIA?\n\n"
                "Nota: Los covers de emergencia quedan registrados sin ID de programación."
            )
            if not confirmacion:
                print("[DEBUG] Usuario canceló el registro de cover de emergencia")
                cursor.close()
                conn.close()
                return None
            
            # ID_cover queda como None para covers de emergencia
            tiene_cover_programado = False
        
        cursor.close()
        conn.close()
        
    except pymysql.Error as e:
        print(f"[ERROR] al verificar cover programado: {e}")
        messagebox.showerror("Error", f"Error al verificar cover programado: {e}")
        return None
    
    # ⭐ INSERTAR COVER REALIZADO (con o sin ID_programacion_covers)
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO covers_realizados (Nombre_Usuarios, ID_programacion_covers, Cover_in, Cover_Out, Covered_by, Motivo)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (username, ID_cover, Cover_in, Cover_Out, Covered_by, Motivo)
        )
        conn.commit()
        
        # ⭐ SOLO actualizar covers_programados SI tiene cover programado
        if tiene_cover_programado and ID_cover is not None:
            try:
                cursor.execute(
                    """UPDATE covers_programados SET is_Active = 0 WHERE ID_Cover = %s""",
                    (ID_cover,)
                )
                conn.commit()
                print(f"[DEBUG] is_Active actualizado correctamente en covers_programados para ID_Cover: {ID_cover}")
            except pymysql.Error as e:
                print(f"[ERROR] al actualizar is_Active en covers_programados: {e}")
        else:
            print(f"[DEBUG] Cover de emergencia registrado SIN actualizar covers_programados")
        
        # Si el motivo es "Break", también actualizar gestion_breaks_programados
        if Motivo and Motivo.strip().lower() == "break":
            try:
                conn2 = get_connection()
                cursor2 = conn2.cursor()
                
                # Obtener ID_Usuario del username
                cursor2.execute("SELECT ID_Usuario FROM user WHERE Nombre_Usuario = %s", (username,))
                result = cursor2.fetchone()
                
                if result:
                    id_usuario = result[0]
                    cursor2.execute(
                        """UPDATE gestion_breaks_programados SET is_Active = 0 
                           WHERE User_covered = %s AND is_Active = 1""",
                        (id_usuario,)
                    )
                    rows_affected = cursor2.rowcount
                    conn2.commit()
                    print(f"[DEBUG] is_Active actualizado en gestion_breaks_programados ({rows_affected} rows)")
                else:
                    print(f"[WARN] Usuario {username} no encontrado para actualizar gestion_breaks_programados")
                
                cursor2.close()
                conn2.close()
                
            except pymysql.Error as e:
                print(f"[ERROR] al actualizar is_Active en gestion_breaks_programados: {e}")

        print("[DEBUG] Cover realizado correctamente ✅")
        
        # Obtener último ID insertado
        cursor.execute("SELECT LAST_INSERT_ID()")
        ID_cover_realizado = cursor.fetchone()[0]
        
        # Mensaje de confirmación diferenciado
        if tiene_cover_programado:
            messagebox.showinfo("Cover Registrado", "Cover registrado exitosamente.")
        else:
            messagebox.showwarning(
                "Cover de Emergencia Registrado", 
                "⚠️ Cover de EMERGENCIA registrado.\n\n"
                "Este cover no estaba programado previamente.\n"
                "Será revisado por supervisión."
            )

    except pymysql.Error as e:
        print(f"[ERROR] al insertar cover realizado: {e}")
        messagebox.showerror("Error", f"Error al registrar cover: {e}")
    finally:
        cursor.close()
        conn.close()
        login.logout_silent(session_id, station)

# - desaprueba el cover activo más reciente para el usuario dado. desde la ui principal de supervisor
def desaprobar_cover(username, session_id, station):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE covers_programados
            SET Approved = 0
            WHERE ID_user = %s AND is_Active = 1
            ORDER BY ID_Cover DESC
            LIMIT 1
            """,
            (username,)
        )
        conn.commit()
        print(f"[DEBUG] Cover desaprobado correctamente para {username}")
        messagebox.showinfo("Cover Desaprobado", f"Cover desaprobado correctamente para {username}.")
    except pymysql.Error as e:
        print(f"[ERROR] al desaprobar cover: {e}")
    finally:
        cursor.close()
        conn.close()
        login.logout_silent(session_id, station)

# - Seleciona un usuario [agrega un cover programado] para el usuario dado. desde la ui principal de Supervisor
def select_user_to_cover(username):
    conn = get_connection()
    station= None
    hora_programada = "2025-01-01 00:00:00"
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO covers_programados (ID_user, Time_request, Station, Reason, Approved, is_Active)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (username, hora_programada, station, "Break programado", 1, 1)
        )
        conn.commit()
        # Obtener el último ID insertado
        cursor.execute("SELECT LAST_INSERT_ID()")
        result = cursor.fetchone()
        ID_Cover = result[0] if result else None
        print(f"[DEBUG] usuario seleccionado para cover de break: {username}, ID_Cover: {ID_Cover}")
    except pymysql.Error as e:
        print(f"[ERROR] no se habilito al usuario {e}")
        ID_Cover = None
    finally:
        cursor.close()
        conn.close()
    return ID_Cover


# - designa un cover para el usuario dado y quien realiza ese cover. desde la ui principal de supervisor
# - nuevo agregar_cover_breaks remplazo del del backend_super.py
def select_covered_by(username,hora,cover,usuario):

    try:
        # Combinar fecha de hoy con la hora proporcionada
        from datetime import datetime
        hoy = datetime.now().strftime("%Y-%m-%d")
        
        # Asegurar formato HH:MM:SS
        if len(hora.split(':')) == 2:  # Si es HH:MM
            hora = hora + ":00"
        
        fecha_hora_cover = f"{hoy} {hora}"
        user_covering = usuario
        user_covered = cover
        fecha_creacion = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        is_active = 1

        conn = get_connection()
        cursor = conn.cursor()

        # Obtener ID del usuario que cubre (user_covering)
        cursor.execute("SELECT ID_Usuario FROM user WHERE Nombre_Usuario = %s", (user_covering,))
        result_covering = cursor.fetchone()
        if result_covering:
            id_user_covering = result_covering[0]
            print(f"[DEBUG] ID del usuario que cubre: {id_user_covering}")
        else:
            messagebox.showerror("Error", f"Usuario '{user_covering}' no encontrado")
            return

        # Obtener ID del usuario a cubrir (user_covered)
        cursor.execute("SELECT ID_Usuario FROM user WHERE Nombre_Usuario = %s", (user_covered,))
        result_covered = cursor.fetchone()
        if result_covered:
            id_user_covered = result_covered[0]
            print(f"[DEBUG] ID del usuario a cubrir: {id_user_covered}")
        else:
            messagebox.showerror("Error", f"Usuario '{user_covered}' no encontrado")
            return

        # Obtener ID del supervisor (username)
        cursor.execute("SELECT ID_Usuario FROM user WHERE Nombre_Usuario = %s", (username,))
        result_supervisor = cursor.fetchone()
        if result_supervisor:
            id_supervisor = result_supervisor[0]
            print(f"[DEBUG] ID del supervisor: {id_supervisor}")
        else:
            messagebox.showerror("Error", f"Supervisor '{username}' no encontrado")
            return

        # Insertar con los IDs
        cover_to_query = """
        INSERT INTO gestion_breaks_programados (User_covering, User_covered, Fecha_hora_cover, is_Active, Supervisor, Fecha_creacion)
        VALUES (%s, %s, %s, %s, %s, %s)
        """
        
        cursor.execute(cover_to_query, (id_user_covering, id_user_covered, fecha_hora_cover, is_active, id_supervisor, fecha_creacion))
        conn.commit()
        
        cursor.close()
        conn.close()
        
        messagebox.showinfo("Éxito", "Cover agregado correctamente")
        print(f"[INFO] ✅ Cover agregado: {user_covered} cubierto por {user_covering} a las {hora}")

        
        
        # Limpiar formulario y refrescar tabla
        try:
            backend_super.limpiar_breaks()
            backend_super.refrescar_tabla_breaks()
        except Exception as e:
            print(f"[WARN] No se pudo refrescar la tabla: {e}")
            
    except Exception as e:
        print(f"[ERROR] agregar_cover_breaks: {e}")
        traceback.print_exc()
        messagebox.showerror("Error", f"Error al agregar cover: {e}")
        try:
            cursor.close()
            conn.close()
        except:
            pass
    return

def actualizar_cover_breaks(username, hora_actual, covered_by_actual, usuario_actual, nuevo_usuario):
    """
    Actualiza un cover de break existente en la base de datos mediante UPDATE.
    
    Args:
        username: Nombre del supervisor que realiza el cambio
        hora_actual: Hora del cover en formato HH:MM:SS
        covered_by_actual: Usuario que cubre (el que hace el cover)
        usuario_actual: Usuario cubierto anterior
        nuevo_usuario: Nuevo usuario cubierto
    
    Returns:
        True si la operación fue exitosa, False en caso contrario
    """
    try:
        if not nuevo_usuario or not nuevo_usuario.strip():
            print("[ERROR] Nuevo usuario vacío")
            return False
        
        if not usuario_actual or not usuario_actual.strip():
            print("[ERROR] Usuario actual vacío")
            return False
        
        conn = get_connection()
        cur = conn.cursor()
        
        # Convertir nombres a IDs
        cur.execute("SELECT ID_Usuario FROM user WHERE Nombre_Usuario = %s", (covered_by_actual,))
        result_covering = cur.fetchone()
        cur.execute("SELECT ID_Usuario FROM user WHERE Nombre_Usuario = %s", (usuario_actual,))
        result_covered_old = cur.fetchone()
        cur.execute("SELECT ID_Usuario FROM user WHERE Nombre_Usuario = %s", (nuevo_usuario,))
        result_covered_new = cur.fetchone()
        
        if not result_covering or not result_covered_old or not result_covered_new:
            print(f"[ERROR] Usuario no encontrado: covering={covered_by_actual}, old={usuario_actual}, new={nuevo_usuario}")
            cur.close()
            conn.close()
            return False
        
        id_covering = result_covering[0]
        id_covered_old = result_covered_old[0]
        id_covered_new = result_covered_new[0]
        
        # Debug: Buscar el cover antes de actualizar
        debug_query = """
            SELECT User_covering, User_covered, TIME_FORMAT(Fecha_hora_cover, '%%H:%%i:%%s') as hora, is_Active
            FROM gestion_breaks_programados
            WHERE User_covering = %s AND User_covered = %s AND is_Active = 1
        """
        cur.execute(debug_query, (id_covering, id_covered_old))
        debug_results = cur.fetchall()
        print(f"[DEBUG] Covers encontrados para covering={id_covering}, covered={id_covered_old}:")
        for row in debug_results:
            print(f"  covering={row[0]}, covered={row[1]}, hora={row[2]}, is_Active={row[3]}")
        
        # Asegurar formato HH:MM:SS con zero-padding
        if len(hora_actual.split(':')) == 2:  # Si es HH:MM
            hora_actual = hora_actual + ":00"
        
        # Normalizar formato: asegurar que las horas tengan 2 dígitos (07:00:00 no 7:00:00)
        parts = hora_actual.split(':')
        if len(parts) == 3:
            hora_actual = f"{int(parts[0]):02d}:{parts[1]}:{parts[2]}"
        
        # UPDATE directo: cambiar User_covered del cover existente
        # Usar TIME_FORMAT para comparar solo la hora sin fecha
        update_query = """
            UPDATE gestion_breaks_programados
            SET User_covered = %s
            WHERE User_covering = %s 
            AND User_covered = %s 
            AND TIME_FORMAT(Fecha_hora_cover, '%%H:%%i:%%s') = %s 
            AND is_Active = 1
        """
        cur.execute(update_query, (id_covered_new, id_covering, id_covered_old, hora_actual))
        rows_affected = cur.rowcount
        
        if rows_affected == 0:
            print(f"[WARN] No se encontró cover para actualizar: covering={covered_by_actual}(ID:{id_covering}), covered={usuario_actual}(ID:{id_covered_old}), hora={hora_actual}")
            print(f"[DEBUG] Query ejecutado: UPDATE con hora={hora_actual}")
            cur.close()
            conn.close()
            return False
        
        conn.commit()
        cur.close()
        conn.close()
        
        print(f"[INFO] ✅ Cover actualizado: {usuario_actual} → {nuevo_usuario} (cubierto por {covered_by_actual} a las {hora_actual})")
        return True
        
    except Exception as e:
        print(f"[ERROR] actualizar_cover_breaks: {e}")
        traceback.print_exc()
        return False

# Función para eliminar cover
def eliminar_cover_breaks(breaks_sheet, parent_window=None):
    """
    Elimina covers de breaks programados (soft delete en gestion_breaks_programados).
    
    Args:
        breaks_sheet: El tksheet widget con los datos de breaks
        parent_window: Ventana padre para los messagebox
    
    Returns:
        tuple: (success: bool, mensaje: str, rows_affected: int)
    """
    if not breaks_sheet:
        return False, "No se proporcionó el sheet de breaks", 0
        
    selected_cols = breaks_sheet.get_selected_columns()
    selected_cells = breaks_sheet.get_selected_cells()
    
    # Caso 1: Se seleccionó una columna completa
    if selected_cols:
        col = list(selected_cols)[0]
        if col == 0:
            messagebox.showwarning("Advertencia", "No se puede eliminar la columna de Hora.", parent=parent_window)
            return False, "Columna de hora no se puede eliminar", 0
        
        covered_by = breaks_sheet.headers()[col]
        
        if not messagebox.askyesno("Confirmar", 
            f"¿Eliminar todos los covers de {covered_by}?", parent=parent_window):
            return False, "Cancelado por el usuario", 0
        
        # Eliminar todos los covers de esa persona (soft delete)
        try:
            conn = get_connection()
            cur = conn.cursor()
            
            # Convertir nombre a ID
            cur.execute("SELECT ID_Usuario FROM user WHERE Nombre_Usuario = %s", (covered_by,))
            result = cur.fetchone()
            if not result:
                messagebox.showerror("Error", f"Usuario '{covered_by}' no encontrado", parent=parent_window)
                cur.close()
                conn.close()
                return False, f"Usuario '{covered_by}' no encontrado", 0
            id_covering = result[0]
            
            update_query = """
                UPDATE gestion_breaks_programados
                SET is_Active = 0
                WHERE User_covering = %s AND is_Active = 1
            """
            cur.execute(update_query, (id_covering,))
            rows_affected = cur.rowcount
            conn.commit()
            cur.close()
            conn.close()
            
            print(f"[INFO] ✅ {rows_affected} covers eliminados para {covered_by}")
            messagebox.showinfo("Éxito", f"{rows_affected} covers eliminados", parent=parent_window)
            return True, f"{rows_affected} covers eliminados", rows_affected
            
        except Exception as e:
            print(f"[ERROR] eliminar_cover_breaks (columna): {e}")
            traceback.print_exc()
            messagebox.showerror("Error", f"Error al eliminar: {e}", parent=parent_window)
            return False, f"Error: {e}", 0
    
    # Caso 2: Se seleccionó una celda específica
    if selected_cells:
        row, col = selected_cells[0]
        
        if col == 0:
            messagebox.showwarning("Advertencia", "No se puede eliminar desde la columna de Hora.", parent=parent_window)
            return False, "Columna de hora no se puede eliminar", 0
        
        hora = breaks_sheet.get_cell_data(row, 0)
        covered_by = breaks_sheet.headers()[col]
        usuario = breaks_sheet.get_cell_data(row, col)
        
        if not usuario:
            messagebox.showwarning("Advertencia", "La celda seleccionada está vacía.", parent=parent_window)
            return False, "Celda vacía", 0
        
        if not messagebox.askyesno("Confirmar", 
            f"¿Eliminar cover de {usuario} cubierto por {covered_by} a las {hora}?", parent=parent_window):
            return False, "Cancelado por el usuario", 0
        
        # Eliminar cover específico (soft delete)
        try:
            conn = get_connection()
            cur = conn.cursor()
            
            # Convertir nombres a IDs
            cur.execute("SELECT ID_Usuario FROM user WHERE Nombre_Usuario = %s", (covered_by,))
            result_covering = cur.fetchone()
            cur.execute("SELECT ID_Usuario FROM user WHERE Nombre_Usuario = %s", (usuario,))
            result_covered = cur.fetchone()
            
            if not result_covering or not result_covered:
                messagebox.showerror("Error", "Usuario no encontrado", parent=parent_window)
                cur.close()
                conn.close()
                return False, "Usuario no encontrado", 0
            
            id_covering = result_covering[0]
            id_covered = result_covered[0]
            
            update_query = """
                UPDATE gestion_breaks_programados
                SET is_Active = 0
                WHERE User_covering = %s AND User_covered = %s AND TIME(Fecha_hora_cover) = %s AND is_Active = 1
            """
            cur.execute(update_query, (id_covering, id_covered, hora))
            rows_affected = cur.rowcount
            conn.commit()
            cur.close()
            conn.close()
            
            print(f"[INFO] ✅ Cover eliminado: {usuario} cubierto por {covered_by} a las {hora}")
            messagebox.showinfo("Éxito", "Cover eliminado exitosamente", parent=parent_window)
            return True, "Cover eliminado exitosamente", rows_affected
            
        except Exception as e:
            print(f"[ERROR] eliminar_cover_breaks (celda): {e}")
            traceback.print_exc()
            messagebox.showerror("Error", f"Error al eliminar: {e}", parent=parent_window)
            return False, f"Error: {e}", 0
    
    messagebox.showwarning("Advertencia", "Seleccione una celda o columna para eliminar el cover.", parent=parent_window)
    return False, "No hay selección válida", 0

# ==================== COVERS REALIZADOS ====================
# TODO: Implementar complete_break_cover cuando se necesite registrar covers completados
# def complete_break_cover(username, ID_cover, covered_by):
#     """Completa un cover de break registrándolo en covers_realizados"""
#     pass


def load_combined_covers():
    """
    Carga datos combinados de covers_programados y covers_realizados
    usando LEFT JOIN para mostrar TODOS los covers programados
    (realizados o pendientes)
    """
    try:
        conn = get_connection()
        cur = conn.cursor()
        
        # Query con LEFT JOIN para incluir covers programados sin realizar
        query = """
            SELECT 
                cp.ID_Cover,
                cp.ID_user AS Usuario,
                cp.Time_request AS Hora_Programada,
                cp.Station AS Estacion,
                cp.Reason AS Razon_Solicitud,
                CASE 
                    WHEN cp.Approved = 1 THEN 'Sí'
                    WHEN cp.Approved = 0 THEN 'No'
                    ELSE 'N/A'
                END AS Aprobado,
                CASE 
                    WHEN cp.is_Active = 1 THEN 'Activo'
                    WHEN cp.is_Active = 0 THEN 'Inactivo'
                    ELSE 'N/A'
                END AS Activo,
                cr.Cover_in AS Cover_Inicio,
                cr.Cover_Out AS Cover_Fin,
                cr.Covered_by AS Cubierto_Por,
                cr.Motivo AS Motivo_Real,
                CASE 
                    WHEN cr.Cover_in IS NOT NULL THEN 'Completado'
                    WHEN cp.Approved = 1 THEN 'Aprobado - Pendiente'
                    WHEN cp.Approved = 0 THEN 'Pendiente Aprobación'
                    ELSE 'Desconocido'
                END AS Estado
            FROM covers_programados cp
            LEFT JOIN covers_realizados cr 
                ON cp.ID_Cover = cr.ID_programacion_covers
            ORDER BY cp.Time_request DESC
        """
        
        cur.execute(query)
        rows = cur.fetchall()
        col_names = [desc[0] for desc in cur.description]
        
        cur.close()
        conn.close()
        
        print(f"[DEBUG] Covers cargados: {len(rows)} registros")
        return col_names, rows
        
    except Exception as e:
        print(f"[ERROR] load_combined_covers: {e}")
        import traceback
        traceback.print_exc()
        return [], []

# fin de la implentacion de covers.

def set_new_status(new_value, username):
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("UPDATE sesion SET Statuses = %s WHERE ID_user = %s ORDER BY ID DESC LIMIT 1",
                            (new_value, username))
            conn.commit()
            cursor.close()
            conn.close()
            return print("Status updated")

def get_user_status_bd(username):
    conn = get_connection()
    if not conn:
        return "Error de conexión"
    
    try:
        cursor = conn.cursor()
        # Ejecutar query
        cursor.execute("""
            SELECT Statuses FROM sesion 
            WHERE ID_user = %s 
            ORDER BY ID DESC 
            LIMIT 1
        """, (username,))
        result = cursor.fetchone()
        if not result:
            return "Usuario no encontrado"
        status_value = result[0]
    except pymysql.Error as e:
        print(f"[ERROR] Error al consultar el estado: {e}")
        
    finally:
        cursor.close()
        conn.close()   

        return status_value

def get_events():
    print("events")

    return 

def single_window(name, func):
        if name in opened_windows and opened_windows[name].winfo_exists():
            opened_windows[name].focus()
            return
        win = func()
        opened_windows[name] = win

        opened_windows = {}  # Para controlar ventanas abiertas

# 🔄 CACHE CON AUTO-REFRESH para Sitios y Actividades
_sites_cache = {'data': None, 'last_update': None}
_activities_cache = {'data': None, 'last_update': None}
CACHE_DURATION = 120  # 2 minutos en segundos

def get_sites(force_refresh=False):
    """
    Obtiene la lista de sitios de la tabla Sitios con cache de 2 minutos
    
    Args:
        force_refresh: Si es True, fuerza actualización ignorando cache
        
    Returns:
        Lista de sitios en formato "Nombre_Sitio (ID)"
    """
    global _sites_cache
    
    # Verificar si necesita actualización
    now = datetime.now()
    needs_update = (
        force_refresh or 
        _sites_cache['data'] is None or 
        _sites_cache['last_update'] is None or
        (now - _sites_cache['last_update']).total_seconds() > CACHE_DURATION
    )
    
    if not needs_update:
        print(f"[DEBUG] Usando cache de sitios (edad: {int((now - _sites_cache['last_update']).total_seconds())}s)")
        return _sites_cache['data']
    
    try:
        conn = get_connection()
        cursor = conn.cursor()

        # Formato modernizado: "Nombre_Sitio (ID)" para permitir búsqueda por ID y por nombre
        cursor.execute("""
            SELECT CONCAT(Nombre_Sitio, ' (', ID_Sitio, ')') AS Sitio
            FROM Sitios
            ORDER BY Nombre_Sitio
        """)

        sites = [row[0] for row in cursor.fetchall()]
        
        # Actualizar cache
        _sites_cache['data'] = sites
        _sites_cache['last_update'] = now
        
        print(f"[DEBUG] Sitios cargados y cache actualizado ({len(sites)} sitios)")
        return sites

    except Exception as e:
        print(f"[ERROR] get_sites: {e}")
        # Si hay error pero tenemos cache, devolverlo
        if _sites_cache['data']:
            print(f"[WARN] Usando cache antiguo de sitios por error de BD")
            return _sites_cache['data']
        return []
    finally:
        try:
            cursor.close()
            conn.close()
        except:
            pass

def get_activities(force_refresh=False):
    """
    Obtiene la lista de actividades de la tabla Actividades con cache de 2 minutos
    
    Args:
        force_refresh: Si es True, fuerza actualización ignorando cache
        
    Returns:
        Lista de nombres de actividades
    """
    global _activities_cache
    
    # Verificar si necesita actualización
    now = datetime.now()
    needs_update = (
        force_refresh or
        _activities_cache['data'] is None or 
        _activities_cache['last_update'] is None or
        (now - _activities_cache['last_update']).total_seconds() > CACHE_DURATION
    )
    
    if not needs_update:
        print(f"[DEBUG] Usando cache de actividades (edad: {int((now - _activities_cache['last_update']).total_seconds())}s)")
        return _activities_cache['data']
    
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""SELECT Nombre_Actividad FROM Actividades ORDER BY Nombre_Actividad""")
        
        activities = [row[0] for row in cursor.fetchall()]
        
        # Actualizar cache
        _activities_cache['data'] = activities
        _activities_cache['last_update'] = now
        
        print(f"[DEBUG] Actividades cargadas y cache actualizado ({len(activities)} actividades)")
        return activities
        
    except Exception as e:
        print(f"[ERROR] get_activities: {e}")
        # Si hay error pero tenemos cache, devolverlo
        if _activities_cache['data']:
            print(f"[WARN] Usando cache antiguo de actividades por error de BD")
            return _activities_cache['data']
        return []
    finally:
        try:
            cursor.close()
            conn.close()
        except:
            pass

def parse_site_filter(site_display):
    """
    🔧 HELPER: Deconstruye el formato "Nombre_Sitio (ID)" del FilteredCombobox
    
    Permite búsqueda flexible por:
    - Formato completo: "Site Name (123)" -> retorna (nombre, id)
    - Solo ID: "123" -> retorna (None, id)
    - Solo nombre: "Site Name" -> retorna (nombre, None)
    
    Args:
        site_display: String del FilteredCombobox (ej: "CARULLA CALLE 79 (305)")
        
    Returns:
        tuple: (site_name, site_id) donde cada uno puede ser None
        
    Ejemplos:
        >>> parse_site_filter("CARULLA CALLE 79 (305)")
        ("CARULLA CALLE 79", "305")
        
        >>> parse_site_filter("305")
        (None, "305")
        
        >>> parse_site_filter("CARULLA CALLE 79")
        ("CARULLA CALLE 79", None)
    """
    import re
    
    if not site_display or not site_display.strip():
        return None, None
    
    site_display = site_display.strip()
    
    # Patrón: "Nombre (123)" -> extraer nombre e ID
    match = re.match(r'^(.+?)\s*\((\d+)\)$', site_display)
    if match:
        site_name = match.group(1).strip()
        site_id = match.group(2).strip()
        return site_name, site_id
    
    # Si es solo un número, asumir que es un ID
    if site_display.isdigit():
        return None, site_display
    
    # Si no coincide con el patrón, asumir que es solo el nombre
    return site_display, None

def add_event(username, site, activity, quantity, camera, desc, hour, minute, second):
    """
    Inserta un nuevo evento en la tabla Eventos en MySQL con tipos correctos.
    """
    conn = get_connection()
    if conn is None:
        print("❌ No se pudo conectar a la base de datos")
        return

    try:
        cursor = conn.cursor()

        # 🔹 Obtener ID_Usuario
        cursor.execute("SELECT ID_Usuario FROM user WHERE Nombre_Usuario=%s", (username,))
        row = cursor.fetchone()
        if not row:
            raise Exception(f"Usuario '{username}' no encontrado")
        user_id = int(row[0])

        # 🔹 Obtener ID_Sitio desde el site_value (ej: "NombreSitio 305")
        try:
            site_id = int(site.split()[-1])
        except Exception:
            raise Exception(f"No se pudo obtener el ID del sitio desde '{site}'")

        # 🔹 Construir datetime editable
        event_time = datetime.now().replace(hour=hour, minute=minute, second=second, microsecond=0)

        # 🔹 Convertir cantidad a número
        try:
            quantity_val = float(quantity)  # o int(quantity) si siempre es entero
        except Exception:
            quantity_val = 0  # fallback

        # 🔹 Insertar en tabla Eventos
        cursor.execute("""
            INSERT INTO Eventos (FechaHora, ID_Sitio, Nombre_Actividad, Cantidad, Camera, Descripcion, ID_Usuario)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (event_time, site_id, str(activity), quantity_val, str(camera), str(desc), user_id))

        conn.commit()
        print(f"[DEBUG] Evento registrado correctamente por {username}")

    except Exception as e:
        print(f"[ERROR] add_event: {e}")

    finally:
        try:
            cursor.close()
            conn.close()
        except:
            pass

def admin_mode():
     print("admin mode")

# ------------------------------
# Combobox filtrable con borde visible
# ------------------------------
class FilteredCombobox(tk.Frame):
    """FilteredCombobox envuelto en un Frame con borde azul prominente"""
    def __init__(self, master=None, **kwargs):
        # Extraer parámetros de borde y colores
        bordercolor = kwargs.pop('bordercolor', '#5ab4ff')
        borderwidth = kwargs.pop('borderwidth', 3)
        background = kwargs.pop('background', '#2b2b2b')
        foreground = kwargs.pop('foreground', '#ffffff')
        fieldbackground = kwargs.pop('fieldbackground', '#2b2b2b')
        arrowcolor = kwargs.pop('arrowcolor', '#ffffff')
        
        # Crear Frame con borde prominente
        super().__init__(master, bg=bordercolor, bd=0, highlightthickness=borderwidth, 
                        highlightbackground=bordercolor, highlightcolor=bordercolor)
        
        # Filtrar opciones válidas para ttk.Combobox
        valid_options = {
            'textvariable', 'values', 'font', 'height', 'width', 'state',
            'exportselection', 'justify', 'postcommand', 'validate', 'validatecommand'
        }
        
        combobox_kwargs = {k: v for k, v in kwargs.items() if k in valid_options}
        
        # Crear estilo único para el Combobox interno
        style = ttk.Style()
        style_name = f"Custom{id(self)}.TCombobox"  # Único por widget
        
        try:
            # Usar 'clam' theme para mejor personalización
            try:
                style.theme_use('clam')
            except:
                pass
            
            style.configure(style_name,
                fieldbackground=fieldbackground,
                background=background,
                foreground=foreground,
                arrowcolor=arrowcolor,
                borderwidth=0,
                relief='flat',
                insertcolor=foreground,
                selectbackground='#4a90e2',
                selectforeground='#ffffff'
            )
            
            style.map(style_name,
                fieldbackground=[
                    ('readonly', fieldbackground),
                    ('!readonly', fieldbackground),
                    ('disabled', '#1a1a1a'),
                    ('focus', fieldbackground),
                    ('!focus', fieldbackground)
                ],
                background=[
                    ('readonly', background),
                    ('!readonly', background),
                    ('active', background)
                ],
                foreground=[
                    ('readonly', foreground),
                    ('!readonly', foreground),
                    ('disabled', '#666666'),
                    ('focus', foreground)
                ]
            )
        except Exception as e:
            print(f"[DEBUG] Style config error (non-critical): {e}")
        
        # Crear el Combobox interno
        self._combobox = ttk.Combobox(self, style=style_name, **combobox_kwargs)
        self._combobox.pack(fill='both', expand=True, padx=0, pady=0)
        
        # Guardar valores originales para filtrado
        vals = self._combobox['values']
        try:
            self.original_values = tuple(vals) if vals is not None else ()
        except Exception:
            try:
                self.original_values = tuple([vals])
            except Exception:
                self.original_values = ()
        
        # Vincular evento de teclado para filtrado
        self._suppress_clear = True
        self._combobox.bind('<KeyRelease>', self.check_key)
        
        # Inicializar valor si existe
        try:
            init_val = self._combobox.get()
            if init_val:
                self._combobox.set(init_val)
                if init_val in self.original_values:
                    try:
                        self._combobox.current(self.original_values.index(init_val))
                    except Exception:
                        pass
        finally:
            try:
                self.after(50, lambda: setattr(self, '_suppress_clear', False))
            except Exception:
                self._suppress_clear = False
    
    def check_key(self, event):
        """Filtrar valores según tecleo"""
        if getattr(self, '_suppress_clear', False):
            return
        
        value = self._combobox.get()
        if value == '':
            try:
                self._combobox['values'] = self.original_values
            except Exception:
                self._combobox.configure(values=self.original_values)
        else:
            filtered = [item for item in self.original_values if value.lower() in str(item).lower()]
            try:
                self._combobox['values'] = filtered
            except Exception:
                self._combobox.configure(values=tuple(filtered))
    
    # Métodos proxy para que funcione como un Combobox normal
    def get(self):
        return self._combobox.get()
    
    def set(self, value):
        return self._combobox.set(value)
    
    def current(self, index=None):
        if index is None:
            return self._combobox.current()
        return self._combobox.current(index)
    
    def bind(self, sequence=None, func=None, add=None):
        return self._combobox.bind(sequence, func, add)
    
    def focus_set(self):
        return self._combobox.focus_set()
    
    def configure(self, **kwargs):
        # Redirigir configuración al combobox interno
        return self._combobox.configure(**kwargs)
    
    def config(self, **kwargs):
        return self.configure(**kwargs)
    
    def __getitem__(self, key):
        return self._combobox[key]
    
    def __setitem__(self, key, value):
        self._combobox[key] = value
