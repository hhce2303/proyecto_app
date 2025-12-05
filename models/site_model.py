# site_model.py
from models.database import get_connection
from datetime import datetime
CACHE_DURATION = 120  # Duración de la cache en segundos

_activities_cache = {
    'data': None,
    'last_update': None
}
_sites_cache = {
    'data': None,
    'last_update': None
}


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

