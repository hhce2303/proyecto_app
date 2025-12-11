"""
Modelo para Audit - Acceso a datos de eventos
Responsabilidad: Solo consultas a la base de datos
"""

from models.database import get_connection


def get_users_list():
    """
    Obtiene lista de usuarios ordenados por nombre
    
    Returns:
        list: Lista de nombres de usuario
    """
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT `Nombre_Usuario` FROM `user` ORDER BY `Nombre_Usuario`")
        users = [r[0] for r in cur.fetchall()]
        cur.close()
        conn.close()
        return users
    except Exception as e:
        print(f"[ERROR] audit_model.get_users_list: {e}")
        return []


def get_sites_list():
    """
    Obtiene lista de sitios en formato 'Nombre_Sitio (ID_Sitio)'
    
    Returns:
        list: Lista de sitios formateados
    """
    try:
        from models.site_model import get_sites
        return get_sites()
    except Exception as e:
        print(f"[ERROR] audit_model.get_sites_list: {e}")
        return []


def load_eventos(user_filter=None, site_filter=None, fecha_filter=None):
    """
    Carga eventos de la tabla Eventos con filtros opcionales
    
    Args:
        user_filter (str, optional): Nombre de usuario para filtrar
        site_filter (str, optional): Filtro de sitio en formato "Nombre (ID)" o solo nombre
        fecha_filter (str, optional): Fecha en formato YYYY-MM-DD
    
    Returns:
        list: Lista de tuplas con datos de eventos
            (ID_Eventos, FechaHora, Nombre_Sitio, Nombre_Actividad, 
             Cantidad, Camera, Descripcion, Nombre_Usuario)
    """
    try:
        conn = get_connection()
        cur = conn.cursor()
        
        sql = """
            SELECT e.ID_Eventos, e.FechaHora, s.Nombre_Sitio, e.Nombre_Actividad, 
                   e.Cantidad, e.Camera, e.Descripcion, u.Nombre_Usuario
            FROM Eventos e
            LEFT JOIN Sitios s ON e.ID_Sitio = s.ID_Sitio
            LEFT JOIN user u ON e.ID_Usuario = u.ID_Usuario
            WHERE 1=1
        """
        params = []
        
        # Filtro por usuario
        if user_filter:
            sql += " AND u.Nombre_Usuario = %s"
            params.append(user_filter)
        
        # Filtro por sitio
        if site_filter:
            # Parsear formato "Nombre (ID)" usando helper de under_super
            # Si no hay paréntesis, buscar por nombre directamente
            if '(' in site_filter and ')' in site_filter:
                # Formato "Nombre (ID)"
                try:
                    site_name = site_filter[:site_filter.rfind('(')].strip()
                    site_id = site_filter[site_filter.rfind('(')+1:site_filter.rfind(')')].strip()
                    
                    if site_name and site_id:
                        sql += " AND s.Nombre_Sitio = %s"
                        params.append(site_name)
                    elif site_id:
                        sql += " AND s.ID_Sitio = %s"
                        params.append(site_id)
                    elif site_name:
                        sql += " AND s.Nombre_Sitio = %s"
                        params.append(site_name)
                except Exception:
                    # Si falla el parsing, buscar por nombre completo
                    sql += " AND s.Nombre_Sitio = %s"
                    params.append(site_filter)
            else:
                # Buscar por nombre directamente
                sql += " AND s.Nombre_Sitio = %s"
                params.append(site_filter)
        
        # Filtro por fecha
        if fecha_filter:
            sql += " AND DATE(e.FechaHora) = %s"
            params.append(fecha_filter)
        
        sql += " ORDER BY e.FechaHora DESC LIMIT 500"
        
        cur.execute(sql, params)
        rows = cur.fetchall()
        cur.close()
        conn.close()
        
        return rows
        
    except Exception as e:
        print(f"[ERROR] audit_model.load_eventos: {e}")
        import traceback
        traceback.print_exc()
        return []
