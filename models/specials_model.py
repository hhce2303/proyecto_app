"""
Modelo para Specials - Acceso a datos de specials
Responsabilidad: Solo consultas a la base de datos
"""

from models.database import get_connection


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
        supervisors = [r[0] for r in cur.fetchall()]
        cur.close()
        conn.close()
        return supervisors
    except Exception as e:
        print(f"[ERROR] specials_model.get_all_supervisors: {e}")
        return []