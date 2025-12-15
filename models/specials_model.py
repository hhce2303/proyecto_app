"""
Modelo para Specials - Acceso a datos de specials
Responsabilidad: Solo consultas a la base de datos
Arquitectura: MVC - Capa de Modelo (Data Access Layer)
"""

from models.database import get_connection
from datetime import datetime, timedelta
import re


# Grupos especiales constantes
GRUPOS_ESPECIALES = ("AS", "KG", "HUD", "PE", "SCH", "WAG", "LT", "DT")


def load_specials_by_supervisor(username):
    """
    Carga specials del supervisor excluyendo los marcados como 'done'
    Usa LEFT JOIN para obtener nombres de sitios en una sola consulta
    
    Args:
        username (str): Nombre del supervisor
    
    Returns:
        list: Lista de tuplas con datos de specials y sitios:
            (ID_special, FechaHora, ID_Sitio, Nombre_Sitio, Time_Zone_Sitio,
             Nombre_Actividad, Cantidad, Camera, Descripcion, Usuario, 
             Time_Zone_Special, marked_status, marked_by, marked_at)
    """
    try:
        conn = get_connection()
        cur = conn.cursor()
        
        # ⭐ SQL OPTIMIZADA CON LEFT JOIN
        sql = """
            SELECT 
                s.ID_special, 
                s.FechaHora, 
                s.ID_Sitio, 
                sit.Nombre_Sitio,
                sit.Time_Zone AS Time_Zone_Sitio,
                s.Nombre_Actividad, 
                s.Cantidad, 
                s.Camera,
                s.Descripcion, 
                s.Usuario, 
                s.Time_Zone AS Time_Zone_Special,
                s.marked_status, 
                s.marked_by, 
                s.marked_at
            FROM specials s
            LEFT JOIN Sitios sit ON s.ID_Sitio = sit.ID_Sitio
            WHERE s.Supervisor = %s 
            AND (s.marked_status IS NULL OR s.marked_status = '' OR s.marked_status = 'flagged')
            ORDER BY s.FechaHora DESC
        """
        cur.execute(sql, (username,))
        
        rows = cur.fetchall()
        cur.close()
        conn.close()
        
        return rows
        
    except Exception as e:
        print(f"[ERROR] specials_model.load_specials_by_supervisor: {e}")
        import traceback
        traceback.print_exc()
        return []


def get_supervisor_shift_start(username):
    """
    Obtiene la última hora de inicio de shift del supervisor
    
    Args:
        username (str): Nombre del supervisor
    
    Returns:
        datetime: Fecha/hora del último START SHIFT, o None si no existe
    """
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT e.FechaHora 
            FROM Eventos e
            INNER JOIN user u ON e.ID_Usuario = u.ID_Usuario
            WHERE u.Nombre_Usuario = %s AND e.Nombre_Actividad = %s
            ORDER BY e.FechaHora DESC
            LIMIT 1
        """, (username, "START SHIFT"))
        row = cur.fetchone()
        cur.close()
        conn.close()
        return row[0] if row and row[0] else None
    except Exception as e:
        print(f"[ERROR] specials_model.get_supervisor_shift_start: {e}")
        return None


def update_special_status(special_id, status, marked_by):
    """
    Actualiza el estado de marca de un special
    
    Args:
        special_id (int): ID del special
        status (str): Estado ('done', 'flagged', o None para desmarcar)
        marked_by (str): Usuario que realiza la marca
    
    Returns:
        bool: True si exitoso, False si error
    """
    try:
        conn = get_connection()
        cur = conn.cursor()
        
        if status is None:
            # Desmarcar
            cur.execute("""
                UPDATE specials 
                SET marked_status = NULL, marked_at = NULL, marked_by = NULL
                WHERE ID_special = %s
            """, (special_id,))
        else:
            # Marcar con estado
            cur.execute("""
                UPDATE specials 
                SET marked_status = %s, marked_at = NOW(), marked_by = %s
                WHERE ID_special = %s
            """, (status, marked_by, special_id))
        
        conn.commit()
        cur.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"[ERROR] specials_model.update_special_status: {e}")
        import traceback
        traceback.print_exc()
        return False


def delete_special(special_id):
    """
    Elimina un special de la base de datos
    
    Args:
        special_id (int): ID del special a eliminar
    
    Returns:
        bool: True si exitoso, False si error
    """
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM specials WHERE ID_special = %s", (special_id,))
        conn.commit()
        cur.close()
        conn.close()
        return True
    except Exception as e:
        print(f"[ERROR] specials_model.delete_special: {e}")
        import traceback
        traceback.print_exc()
        return False


def transfer_specials_to_supervisor(special_ids, new_supervisor):
    """
    Transfiere specials a otro supervisor
    
    Args:
        special_ids (list): Lista de IDs de specials
        new_supervisor (str): Nombre del nuevo supervisor
    
    Returns:
        bool: True si exitoso, False si error
    """
    try:
        conn = get_connection()
        cur = conn.cursor()
        
        for special_id in special_ids:
            cur.execute(
                "UPDATE specials SET Supervisor = %s WHERE ID_special = %s", 
                (new_supervisor, special_id)
            )
        
        conn.commit()
        cur.close()
        conn.close()
        return True
    except Exception as e:
        print(f"[ERROR] specials_model.transfer_specials_to_supervisor: {e}")
        import traceback
        traceback.print_exc()
        return False


def load_specials_by_supervisor_since(username, since_datetime):
    """
    Carga todos los specials de un supervisor desde una fecha específica
    (Para la funcionalidad de "Otros Specials")
    
    Args:
        username (str): Nombre del supervisor
        since_datetime (datetime): Fecha desde la cual cargar specials
    
    Returns:
        list: Lista de tuplas con datos de specials
    """
    try:
        conn = get_connection()
        cur = conn.cursor()
        
        sql = """
            SELECT 
                s.ID_special, 
                s.FechaHora, 
                s.ID_Sitio, 
                sit.Nombre_Sitio,
                sit.Time_Zone AS Time_Zone_Sitio,
                s.Nombre_Actividad, 
                s.Cantidad, 
                s.Camera,
                s.Descripcion, 
                s.Usuario, 
                s.Time_Zone AS Time_Zone_Special,
                s.marked_status, 
                s.marked_by
            FROM specials s
            LEFT JOIN Sitios sit ON s.ID_Sitio = sit.ID_Sitio
            WHERE s.Supervisor = %s AND s.FechaHora >= %s
            ORDER BY s.FechaHora DESC
        """
        cur.execute(sql, (username, since_datetime))
        
        rows = cur.fetchall()
        cur.close()
        conn.close()
        
        return rows
        
    except Exception as e:
        print(f"[ERROR] specials_model.load_specials_by_supervisor_since: {e}")
        import traceback
        traceback.print_exc()
        return []


def get_all_supervisors():
    """
    Obtiene lista de todos los supervisores
    
    Returns:
        list: Lista de nombres de supervisores
    """
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            "SELECT Nombre_Usuario FROM user WHERE Rol = %s ORDER BY Nombre_Usuario", 
            ("Supervisor",)
        )
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return [row[0] for row in rows]
        
    except Exception as e:
        print(f"[ERROR] specials_model.get_all_supervisors: {e}")
        return []


# ========== FUNCIONES PARA OPERADORES (NUEVO) ==========


def get_specials_eventos(username, last_shift_time):
    """
    Obtiene eventos de grupos especiales desde el último START SHIFT.
    PARA OPERADORES: Muestra eventos que pertenecen a grupos especiales.
    
    Args:
        username (str): Nombre del operador
        last_shift_time (datetime): Timestamp del último START SHIFT
        
    Returns:
        list: Lista de tuplas con datos de eventos especiales
    """
    try:
        conn = get_connection()
        if not conn:
            return []
        
        cursor = conn.cursor()
        
        # Query: EVENTOS de grupos especiales desde START SHIFT
        query = """
            SELECT
                e.ID_Eventos,
                e.FechaHora,
                e.ID_Sitio,
                e.Nombre_Actividad,
                e.Cantidad,
                e.Camera,
                e.Descripcion,
                u.Nombre_Usuario
            FROM Eventos AS e
            INNER JOIN user u ON e.ID_Usuario = u.ID_Usuario
            WHERE u.Nombre_Usuario = %s
            AND e.ID_Sitio IN (
                SELECT st.ID_Sitio
                FROM Sitios st
                WHERE st.ID_Grupo IN (%s, %s, %s, %s, %s, %s, %s, %s)
            )
            AND e.FechaHora >= %s
            ORDER BY e.FechaHora ASC
        """
        
        cursor.execute(query, (username, *GRUPOS_ESPECIALES, last_shift_time))
        rows = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return rows
        
    except Exception as e:
        print(f"[ERROR] get_specials_eventos: {e}")
        return []


def get_site_info(site_id):
    """
    Obtiene información del sitio (Nombre y Time_Zone).
    
    Args:
        site_id (int): ID del sitio
        
    Returns:
        tuple: (nombre_sitio, time_zone) o (None, None) si no existe
    """
    try:
        conn = get_connection()
        if not conn:
            return None, None
        
        cursor = conn.cursor()
        cursor.execute(
            "SELECT Nombre_Sitio, Time_Zone FROM Sitios WHERE ID_Sitio = %s",
            (site_id,)
        )
        result = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        if result:
            return result[0], result[1]
        return None, None
        
    except Exception as e:
        print(f"[ERROR] get_site_info: {e}")
        return None, None


def get_special_by_evento_id(evento_id):
    """
    Obtiene el registro de specials asociado a un evento.
    NUEVO: Busca por ID_Eventos (columna agregada en BD).
    
    Args:
        evento_id (int): ID del evento en tabla Eventos
        
    Returns:
        tuple: Datos del special o None si no existe
    """
    try:
        conn = get_connection()
        if not conn:
            return None
        
        cursor = conn.cursor()
        
        # Query: Buscar special por ID_Eventos (FK)
        query = """
            SELECT 
                ID_Special,
                FechaHora,
                ID_Sitio,
                Nombre_Actividad,
                Cantidad,
                Camera,
                Descripcion,
                Supervisor,
                Time_Zone,
                marked_status,
                marked_by,
                marked_at
            FROM specials
            WHERE ID_Eventos = %s
            LIMIT 1
        """
        
        cursor.execute(query, (evento_id,))
        result = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        return result
        
    except Exception as e:
        # Si la columna ID_Eventos no existe o hay error SQL, mostrar mensaje detallado
        print(f"[ERROR] get_special_by_evento_id: {e}")
        import traceback
        traceback.print_exc()
        return None


def load_tz_config():
    """
    Carga configuración de ajuste de zona horaria.
    
    Returns:
        dict: Diccionario {timezone: offset_hours}
    """
    try:
        conn = get_connection()
        if not conn:
            return {}
        
        cursor = conn.cursor()
        cursor.execute("SELECT Time_Zone, Offset_Hours FROM time_zone_config")
        rows = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        # Convertir a diccionario
        tz_dict = {}
        for row in rows:
            tz_name = row[0].upper() if row[0] else ""
            offset = int(row[1]) if row[1] is not None else 0
            tz_dict[tz_name] = offset
        
        return tz_dict
        
    except Exception as e:
        print(f"[ERROR] load_tz_config: {e}")
        return {}


def get_last_shift_start(username):
    """
    Obtiene el timestamp del último START SHIFT del usuario.
    
    Args:
        username (str): Nombre del usuario
        
    Returns:
        datetime: Timestamp del último START SHIFT o None
    """
    try:
        conn = get_connection()
        if not conn:
            return None
        
        cursor = conn.cursor()
        
        # Buscar último START SHIFT
        cursor.execute("""
            SELECT MAX(FechaHora)
            FROM Eventos
            WHERE ID_Usuario = (SELECT ID_Usuario FROM user WHERE Nombre_Usuario = %s)
            AND Nombre_Actividad = 'START SHIFT'
        """, (username,))
        
        result = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        return result[0] if result and result[0] else None
        
    except Exception as e:
        print(f"[ERROR] get_last_shift_start: {e}")
        return None


def get_active_supervisors():
    """
    Obtiene lista de supervisores activos (Active IN (1, 2)).
    
    Returns:
        list: Lista de nombres de supervisores activos
    """
    try:
        conn = get_connection()
        if not conn:
            return []
        
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT u.Nombre_Usuario 
            FROM user u
            WHERE u.Rol IN (%s, %s)
            AND EXISTS (
                SELECT 1 
                FROM sesion s 
                WHERE s.ID_user = u.Nombre_Usuario 
                AND s.Active IN (1, 2)
                ORDER BY s.ID DESC 
                LIMIT 1
            )
            AND (
                SELECT s2.Active
                FROM sesion s2
                WHERE s2.ID_user = u.Nombre_Usuario
                ORDER BY s2.ID DESC
                LIMIT 1
            ) <> 0
            ORDER BY u.Nombre_Usuario
        """, ("Supervisor", "Lead Supervisor"))
        
        rows = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return [row[0] for row in rows]
        
    except Exception as e:
        print(f"[ERROR] get_active_supervisors: {e}")
        return []


def insert_special(evento_id, fecha_hora, id_sitio, nombre_actividad, cantidad, 
                   camera, descripcion, usuario, time_zone, supervisor):
    """
    Inserta un nuevo registro en la tabla specials.
    
    Args:
        evento_id (int): ID del evento en tabla Eventos
        fecha_hora (str): Fecha y hora del evento
        id_sitio (int): ID del sitio
        nombre_actividad (str): Nombre de la actividad
        cantidad (int): Cantidad
        camera (str): Camera
        descripcion (str): Descripción
        usuario (str): Usuario que crea el special
        time_zone (str): Zona horaria
        supervisor (str): Supervisor asignado
        
    Returns:
        tuple: (success: bool, message: str, id_special: int or None)
    """
    try:
        conn = get_connection()
        if not conn:
            return False, "No hay conexión a la base de datos", None
        
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO specials
                (ID_Eventos, FechaHora, ID_Sitio, Nombre_Actividad, Cantidad, Camera, 
                 Descripcion, Usuario, Time_Zone, Supervisor, marked_status, marked_by, marked_at)
            VALUES
                (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NULL, NULL, NULL)
        """, (evento_id, fecha_hora, id_sitio, nombre_actividad, cantidad, 
              camera, descripcion, usuario, time_zone, supervisor))
        
        id_special = cursor.lastrowid
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return True, "Special insertado correctamente", id_special
        
    except Exception as e:
        print(f"[ERROR] insert_special: {e}")
        import traceback
        traceback.print_exc()
        return False, str(e), None


def update_special(id_special, fecha_hora, id_sitio, nombre_actividad, cantidad,
                   camera, descripcion, usuario, time_zone, supervisor):
    """
    Actualiza un registro existente en la tabla specials.
    
    Args:
        id_special (int): ID del special a actualizar
        fecha_hora (str): Fecha y hora del evento
        id_sitio (int): ID del sitio
        nombre_actividad (str): Nombre de la actividad
        cantidad (int): Cantidad
        camera (str): Camera
        descripcion (str): Descripción
        usuario (str): Usuario que actualiza
        time_zone (str): Zona horaria
        supervisor (str): Supervisor asignado
        
    Returns:
        tuple: (success: bool, message: str)
    """
    try:
        conn = get_connection()
        if not conn:
            return False, "No hay conexión a la base de datos"
        
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE specials
            SET FechaHora = %s,
                ID_Sitio = %s,
                Nombre_Actividad = %s,
                Cantidad = %s,
                Camera = %s,
                Descripcion = %s,
                Usuario = %s,
                Time_Zone = %s,
                marked_status = NULL,
                marked_at = NULL,
                marked_by = NULL,
                Supervisor = %s
            WHERE ID_Special = %s
        """, (fecha_hora, id_sitio, nombre_actividad, cantidad, camera,
              descripcion, usuario, time_zone, supervisor, id_special))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return True, "Special actualizado correctamente"
        
    except Exception as e:
        print(f"[ERROR] update_special: {e}")
        import traceback
        traceback.print_exc()
        return False, str(e)
        supervisors = [r[0] for r in cur.fetchall()]
        cur.close()
        conn.close()
        return supervisors
    except Exception as e:
        print(f"[ERROR] specials_model.get_all_supervisors: {e}")
        return []