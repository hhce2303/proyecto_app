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


def add_break_to_db(user_covered_id, user_covering_id, datetime_cover, supervisor_id):
    """Agrega un nuevo break programado a la base de datos
    
    Args:
        user_covered_id (int): ID del usuario a cubrir
        user_covering_id (int): ID del usuario que cubre
        datetime_cover (str): Fecha y hora completa en formato 'YYYY-MM-DD HH:MM:SS'
        supervisor_id (int): ID del supervisor que aprueba
        
    Returns:
        bool: True si éxito, False si falla
    """
    try:
        conn = get_connection()
        cur = conn.cursor()
        query = """
            INSERT INTO gestion_breaks_programados (User_covered, User_covering, Fecha_hora_cover, is_Active, Supervisor, Fecha_creacion)
            VALUES (%s, %s, %s, 1, %s, NOW())
        """
        cur.execute(query, (user_covered_id, user_covering_id, datetime_cover, supervisor_id))
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
            WHERE ID_cover = %s
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
                gbp.ID_cover,
                TIME(gbp.Fecha_hora_cover) as hora,
                u_covered.Nombre_Usuario as usuario_covered,
                u_covering.Nombre_Usuario as usuario_covering,
                CASE 
                    WHEN gbp.is_Active = 1 THEN 'Activo'
                    ELSE 'Inactivo'
                END as estado,
                CASE
                    WHEN gbp.Supervisor IS NOT NULL THEN CONCAT('✓ ', u_supervisor.Nombre_Usuario)
                    ELSE 'Pendiente'
                END as aprobacion
            FROM gestion_breaks_programados gbp
            INNER JOIN user u_covered ON gbp.User_covered = u_covered.ID_Usuario
            INNER JOIN user u_covering ON gbp.User_covering = u_covering.ID_Usuario
            LEFT JOIN user u_supervisor ON gbp.Supervisor = u_supervisor.ID_Usuario
            WHERE gbp.is_Active in (1,0,-1)
            ORDER BY gbp.Fecha_hora_cover
        """
        cur.execute(query)
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return rows
    except Exception as e:
        print(f"[ERROR] load_covers_from_db: {e}")
        return [] 
    
def Load_user_breaks_from_db(username):
    """Carga breaks programados para un usuario específico
    
    Args:
        username (str): Nombre del usuario
        
    Returns:
        list: Lista de tuplas con (ID_cover, Nombre_covered, Nombre_covering, Fecha_hora, Estado, Aprobacion)
    """
    try:
        conn = get_connection()
        cur = conn.cursor()
        query = """
            SELECT 
                gbp.ID_cover,
                u_covered.Nombre_Usuario as covered_name,
                u_covering.Nombre_Usuario as covering_name,
                gbp.Fecha_hora_cover,
                CASE 
                    WHEN gbp.is_Active = 1 THEN 'Activo'
                    WHEN gbp.is_Active = 0 THEN 'Completado'
                    ELSE 'Cancelado'
                END as estado,
                CASE
                    WHEN gbp.Supervisor IS NOT NULL THEN CONCAT('✓ ', u_supervisor.Nombre_Usuario)
                    ELSE 'Pendiente'
                END as aprobacion
            FROM gestion_breaks_programados gbp
            INNER JOIN user u_covered ON gbp.User_covered = u_covered.ID_Usuario
            INNER JOIN user u_covering ON gbp.User_covering = u_covering.ID_Usuario
            LEFT JOIN user u_supervisor ON gbp.Supervisor = u_supervisor.ID_Usuario
            WHERE u_covered.Nombre_Usuario = %s 
            AND gbp.is_Active = 1
            ORDER BY 
                CASE 
                    WHEN gbp.Fecha_hora_cover >= NOW() THEN 0
                    ELSE 1
                END,
                ABS(TIMESTAMPDIFF(MINUTE, gbp.Fecha_hora_cover, NOW())) ASC
            LIMIT 1
        """
        cur.execute(query, (username,))
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return rows
    except Exception as e:
        print(f"[ERROR] Load_user_breaks_from_db: {e}")
        return []
    
def Load_user_covering_breaks(username):
    """Carga breaks donde el usuario es el que cubre
    
    Args:
        username (str): Nombre del usuario
        
    Returns:
        list: Lista de tuplas con (ID_cover, Nombre_covered, Nombre_covering, Fecha_hora, Estado, Aprobacion)
    """
    try:
        conn = get_connection()
        cur = conn.cursor()
        query = """
            SELECT 
                gbp.ID_cover,
                u_covered.Nombre_Usuario as covered_name,
                u_covering.Nombre_Usuario as covering_name,
                gbp.Fecha_hora_cover,
                CASE 
                    WHEN gbp.is_Active = 1 THEN 'Activo'
                    WHEN gbp.is_Active = 0 THEN 'Completado'
                    ELSE 'Cancelado'
                END as estado,
                CASE
                    WHEN gbp.Supervisor IS NOT NULL THEN CONCAT('✓ ', u_supervisor.Nombre_Usuario)
                    ELSE 'Pendiente'
                END as aprobacion
            FROM gestion_breaks_programados gbp
            INNER JOIN user u_covered ON gbp.User_covered = u_covered.ID_Usuario
            INNER JOIN user u_covering ON gbp.User_covering = u_covering.ID_Usuario
            LEFT JOIN user u_supervisor ON gbp.Supervisor = u_supervisor.ID_Usuario
            WHERE u_covering.Nombre_Usuario = %s 
            AND gbp.is_Active = 1
            ORDER BY 
                CASE 
                    WHEN gbp.Fecha_hora_cover >= NOW() THEN 0
                    ELSE 1
                END,
                ABS(TIMESTAMPDIFF(MINUTE, gbp.Fecha_hora_cover, NOW())) ASC
            LIMIT 10
        """
        cur.execute(query, (username,))
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return rows
    except Exception as e:
        print(f"[ERROR] Load_user_covering_breaks: {e}")
        return []