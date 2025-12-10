from models.database import get_connection


def get_user_id_by_name(username):
    """Obtiene el ID de usuario por su nombre
    
    Args:
        username (str): Nombre del usuario
        
    Returns:
        int: ID del usuario o None si no existe
    """
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT ID_Usuario FROM user WHERE Nombre_Usuario = %s", (username,))
        result = cur.fetchone()
        cur.close()
        conn.close()
        return result[0] if result else None
    except Exception as e:
        print(f"[ERROR] get_user_id_by_name: {e}")
        return None


def add_break_to_db(user_covered_id, user_covering_id, datetime_cover):
    """Agrega un nuevo break programado a la base de datos
    
    Args:
        user_covered_id (int): ID del usuario a cubrir
        user_covering_id (int): ID del usuario que cubre
        datetime_cover (str): Fecha y hora completa en formato 'YYYY-MM-DD HH:MM:SS'
        
    Returns:
        bool: True si éxito, False si falla
    """
    try:
        conn = get_connection()
        cur = conn.cursor()
        query = """
            INSERT INTO gestion_breaks_programados (User_covered, User_covering, Fecha_hora_cover, is_Active)
            VALUES (%s, %s, %s, 1)
        """
        cur.execute(query, (user_covered_id, user_covering_id, datetime_cover))
        conn.commit()
        cur.close()
        conn.close()
        return True
    except Exception as e:
        print(f"[ERROR] add_break_to_db: {e}")
        return False


def delete_break_from_db(break_id):
    """Elimina un break programado por ID
    
    Args:
        break_id (int): ID del break a eliminar
        
    Returns:
        bool: True si éxito, False si falla
    """
    try:
        conn = get_connection()
        cur = conn.cursor()
        query = """
            DELETE FROM gestion_breaks_programados  
            WHERE ID_break_programado = %s
        """
        cur.execute(query, (break_id,))
        conn.commit()
        affected = cur.rowcount
        cur.close()
        conn.close()
        return affected > 0
    except Exception as e:
        print(f"[ERROR] delete_break_from_db: {e}")
        return False


def load_covers_from_db():
    """Carga covers activos desde gestion_breaks_programados
    
    Returns:
        list: Lista de tuplas con (ID, usuario_cubierto, usuario_cubre, hora, estado, aprobacion)
    """
    try:
        conn = get_connection()
        cur = conn.cursor()
        query = """
            SELECT 
                gestion_breaks_programados.ID_break_programado,
                u_covered.Nombre_Usuario as usuario_cubierto,
                u_covering.Nombre_Usuario as usuario_cubre,
                TIME(gestion_breaks_programados.Fecha_hora_cover) as hora,
                CASE 
                    WHEN gestion_breaks_programados.is_Active = 1 THEN 'Activo'
                    ELSE 'Inactivo'
                END as estado,
                CASE
                    WHEN gestion_breaks_programados.Approved_by IS NOT NULL THEN CONCAT('✓ ', gestion_breaks_programados.Approved_by)
                    ELSE 'Pendiente'
                END as aprobacion
            FROM gestion_breaks_programados
            INNER JOIN user u_covered ON gestion_breaks_programados.User_covered = u_covered.ID_Usuario
            INNER JOIN user u_covering ON gestion_breaks_programados.User_covering = u_covering.ID_Usuario
            WHERE gestion_breaks_programados.is_Active = 1
            ORDER BY gestion_breaks_programados.Fecha_hora_cover
        """
        cur.execute(query)
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return rows
    except Exception as e:
        print(f"[ERROR] load_covers_from_db: {e}")
        return [] 