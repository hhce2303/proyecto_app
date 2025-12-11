"""
Modelo para Specials Sin Asignar (Unassigned Specials)
Maneja todas las operaciones SQL relacionadas con specials sin marcar
"""

from models.database import get_connection


def get_last_shift_start(username):
    """
    Obtiene la fecha/hora del último START SHIFT del usuario
    
    Args:
        username: Nombre del usuario (Lead Supervisor)
        
    Returns:
        datetime o None si no hay shift activo
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT e.FechaHora 
            FROM Eventos e
            INNER JOIN user u ON e.ID_Usuario = u.ID_Usuario
            WHERE u.Nombre_Usuario = %s AND e.Nombre_Actividad = 'START SHIFT'
            ORDER BY e.FechaHora DESC
            LIMIT 1
        """, (username,))
        
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        
        return result[0] if result else None
        
    except Exception as e:
        print(f"[ERROR] get_last_shift_start: {e}")
        return None


def load_unassigned_specials_data(fecha_inicio):
    """
    Carga specials sin marcar (marked_status vacío) desde una fecha de inicio
    
    Args:
        fecha_inicio: Fecha/hora desde la cual buscar specials
        
    Returns:
        Lista de tuplas con los datos de specials sin asignar
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Query: Specials sin marcar (marked_status IS NULL o vacío)
        sql = """
            SELECT 
                s.ID_special,
                s.FechaHora,
                s.ID_Sitio,
                s.Nombre_Actividad,
                s.Cantidad,
                s.Camera,
                s.Descripcion,
                s.Usuario,
                s.Time_Zone,
                s.Supervisor
            FROM specials s
            WHERE (s.marked_status IS NULL OR s.marked_status = '')
              AND s.FechaHora >= %s
            ORDER BY s.FechaHora ASC
        """
        
        cursor.execute(sql, (fecha_inicio,))
        rows = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return rows
        
    except Exception as e:
        print(f"[ERROR] load_unassigned_specials_data: {e}")
        raise


def get_site_name(sitio_id):
    """
    Obtiene el nombre de un sitio por su ID
    
    Args:
        sitio_id: ID del sitio
        
    Returns:
        str: Nombre del sitio o cadena vacía si no existe
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT Nombre_Sitio FROM Sitios WHERE ID_Sitio = %s", (sitio_id,))
        result = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        return result[0] if result else ""
        
    except Exception:
        return ""


def get_supervisors_list():
    """
    Obtiene lista de supervisores disponibles (Supervisor y Lead Supervisor)
    
    Returns:
        Lista de nombres de supervisores
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT Nombre_Usuario FROM user WHERE Rol IN ('Supervisor', 'Lead Supervisor') ORDER BY Nombre_Usuario")
        supervisores = [row[0] for row in cursor.fetchall()]
        
        cursor.close()
        conn.close()
        
        return supervisores
        
    except Exception as e:
        print(f"[ERROR] get_supervisors_list: {e}")
        return []


def assign_supervisor(special_ids, supervisor_name):
    """
    Asigna un supervisor a múltiples specials
    
    Args:
        special_ids: Lista de IDs de specials a actualizar
        supervisor_name: Nombre del supervisor a asignar
        
    Returns:
        Tupla (éxito: bool, cantidad_actualizada: int, mensaje_error: str)
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        updated_count = 0
        for special_id in special_ids:
            try:
                cursor.execute(
                    "UPDATE specials SET Supervisor = %s WHERE ID_special = %s",
                    (supervisor_name, special_id)
                )
                updated_count += 1
            except Exception as e:
                print(f"[ERROR] No se pudo asignar supervisor al special {special_id}: {e}")
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return True, updated_count, ""
        
    except Exception as e:
        error_msg = f"Error al asignar supervisor: {str(e)}"
        print(f"[ERROR] assign_supervisor: {e}")
        return False, 0, error_msg
