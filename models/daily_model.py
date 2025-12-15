

from models.database import get_connection
import backend_super


def load_daily(username):
    """Carga datos diarios desde el último START SHIFT (MODO DAILY)"""
    try:
        data = backend_super.get_daily_data_since_last_shift()
        last_shift_time = backend_super.get_last_shift_start(username)
        conn = get_connection()
        cur = conn.cursor()
        
        # Obtener eventos del usuario desde el último shift
        cur.execute("""
            SELECT 
                e.ID_Eventos,
                e.FechaHora,
                e.ID_Sitio,
                e.Nombre_Actividad,
                e.Cantidad,
                e.Camera,
                e.Descripcion
            FROM Eventos e
            INNER JOIN user u ON e.ID_Usuario = u.ID_Usuario
            WHERE u.Nombre_Usuario = %s AND e.FechaHora >= %s
            ORDER BY e.FechaHora ASC
        """, (username, last_shift_time))

        eventos = cur.fetchall()
        display_rows = []
    except Exception as e:
        print(f"[ERROR] load_daily: {e}")
        return []


def obtain_site_name(cur, id_sitio):
    cur.execute("SELECT Nombre_Sitio FROM Sitios WHERE ID_Sitio = %s", (id_sitio,))
    sit_row = cur.fetchone()
    return sit_row


def get_sites():
    """Obtiene lista de sitios"""
    try:
        conn = get_connection()
        if not conn:
            return []
        cursor = conn.cursor()
        cursor.execute("SELECT ID_Sitio, Nombre_sitio FROM sitios ORDER BY Nombre_sitio")
        sites = cursor.fetchall()
        cursor.close()
        conn.close()
        return sites
    except Exception as e:
        print(f"[ERROR] get_sites: {e}")
        return []


def get_activities():
    """Obtiene lista de actividades"""
    try:
        conn = get_connection()
        if not conn:
            return []
        cursor = conn.cursor()
        cursor.execute("SELECT Nombre_Actividad FROM actividades ORDER BY Nombre_Actividad")
        activities = cursor.fetchall()
        cursor.close()
        conn.close()
        return activities
    except Exception as e:
        print(f"[ERROR] get_activities: {e}")
        return []


def create_event(username, site_id, activity, quantity, camera, description):
    """Crea un nuevo evento"""
    from datetime import datetime
    
    try:
        conn = get_connection()
        if not conn:
            return False, "No hay conexión a la base de datos"
        
        cursor = conn.cursor()
        
        # Obtener ID del usuario
        cursor.execute("SELECT ID_Usuario FROM user WHERE Nombre_Usuario = %s", (username,))
        user_row = cursor.fetchone()
        if not user_row:
            cursor.close()
            conn.close()
            return False, "Usuario no encontrado"
        
        user_id = user_row[0]
        
        # Insertar evento
        fecha_hora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("""
            INSERT INTO Eventos 
            (FechaHora, ID_Sitio, ID_Usuario, Nombre_Actividad, Cantidad, Camera, Descripcion)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (fecha_hora, site_id, user_id, activity, quantity, camera, description))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return True, "Evento creado exitosamente"
        
    except Exception as e:
        print(f"[ERROR] create_event: {e}")
        return False, str(e)
