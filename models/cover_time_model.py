from models.database import get_connection
from datetime import datetime


def get_cover_users_list():
    """Obtiene lista única de usuarios que han realizado covers
    
    Returns:
        list: Lista de nombres de usuario incluyendo 'Todos'
    """
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            "SELECT DISTINCT Nombre_usuarios FROM covers_realizados "
            "WHERE Nombre_usuarios IS NOT NULL ORDER BY Nombre_usuarios"
        )
        users = [r[0] for r in cur.fetchall()]
        cur.close()
        conn.close()
        return ["Todos"] + users
    except Exception as e:
        print(f"[ERROR] get_cover_users_list: {e}")
        return ["Todos"]


def load_covers_programados():
    """Carga todos los covers programados desde la BD
    
    Returns:
        tuple: (nombres_columnas, filas)
    """
    try:
        conn = get_connection()
        cur = conn.cursor()
        query = "SELECT * FROM covers_programados WHERE is_Active = '1' ORDER BY Time_request ASC"
        cur.execute(query)
        rows = cur.fetchall()
        col_names = [desc[0] for desc in cur.description]
        cur.close()
        conn.close()
        return col_names, rows
    except Exception as e:
        print(f"[ERROR] load_covers_programados: {e}")
        return [], []


def load_covers_realizados(user_filter=None, fecha_desde=None, fecha_hasta=None):
    """Carga covers realizados con filtros opcionales
    
    Args:
        user_filter (str): Nombre de usuario o None para todos
        fecha_desde (str): Fecha inicio formato YYYY-MM-DD o None
        fecha_hasta (str): Fecha fin formato YYYY-MM-DD o None
        
    Returns:
        tuple: (nombres_columnas, filas)
    """
    try:
        conn = get_connection()
        cur = conn.cursor()
        
        sql = "SELECT * FROM covers_realizados WHERE 1=1"
        params = []
        
        if user_filter and user_filter != "Todos":
            sql += " AND Nombre_usuarios = %s"
            params.append(user_filter)
        
        if fecha_desde:
            sql += " AND DATE(Cover_in) >= %s"
            params.append(fecha_desde)
        
        if fecha_hasta:
            sql += " AND DATE(Cover_in) <= %s"
            params.append(fecha_hasta)
        
        sql += " ORDER BY Cover_in DESC"
        
        cur.execute(sql, params)
        rows = cur.fetchall()
        col_names = [desc[0] for desc in cur.description]
        cur.close()
        conn.close()
        return col_names, rows
    except Exception as e:
        print(f"[ERROR] load_covers_realizados: {e}")
        return [], []
