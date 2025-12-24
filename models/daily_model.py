from models.database import get_connection
import backend_super

def get_last_shift_start(username):
    """Obtiene la hora de inicio del último turno del usuario"""
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT MAX(FechaHora) 
            FROM eventos e
            INNER JOIN user u ON e.ID_Usuario = u.ID_Usuario
            WHERE u.Nombre_Usuario = %s and e.Nombre_Actividad = 'START SHIFT'
        """, (username,))
        row = cur.fetchone()
        conn.close()
        return row[0] if row else None
    except Exception as e:
        print(f"[ERROR] get_last_shift_start: {e}")
        return None


def load_daily(username):
    """Carga datos diarios desde el último START SHIFT (MODO DAILY)"""
    try:
        last_shift_time = get_last_shift_start(username)
        conn = get_connection()
        cur = conn.cursor()
        
        # Obtener eventos del usuario desde el último shift

        cur.execute("""
            SELECT 
                e.ID_Eventos,
                e.FechaHora,
                CONCAT(s.ID_Sitio, ' - ', s.Nombre_Sitio) AS Nombre_Sitio,
                e.Nombre_Actividad,
                e.Cantidad,
                e.Camera,
                e.Descripcion,
                e.ID_Usuario
            FROM Eventos e
            INNER JOIN user u ON e.ID_Usuario = u.ID_Usuario
            INNER JOIN Sitios s ON e.ID_Sitio = s.ID_Sitio
            WHERE u.Nombre_Usuario = %s AND e.FechaHora >= %s
            ORDER BY e.FechaHora ASC
        """, (username, last_shift_time))

        eventos = cur.fetchall()[1:]
        display_rows = []
        return eventos
    except Exception as e:
        print(f"[ERROR] load_daily: {e}")
        return []

def auto_save_pending_events_bd(username,fecha_hora, id_sitio, actividad, cantidad, camera, descripcion, event_id):
    """Guarda automáticamente eventos pendientes en backend_super"""

    try:
        conn = get_connection()
        cur = conn.cursor()
            # UPDATE en BD
        cur.execute("""
            UPDATE Eventos
            SET FechaHora = %s,
                ID_Sitio = %s,
                Nombre_Actividad = %s,
                Cantidad = %s,
                Camera = %s,
                Descripcion = %s
            WHERE ID_Eventos = %s
        """, (fecha_hora, id_sitio, actividad, cantidad, camera, descripcion, event_id))
            
        print(f"[DEBUG] Auto-saved event ID={event_id}")
            
    except Exception as e:
        print(f"[ERROR] Auto-save row: {e}")
    
    conn.commit()
    cur.close()
    conn.close()

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


def create_event(username, site_id, activity, quantity, camera, description, fecha_hora=None):
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
        
        # Usar fecha_hora proporcionada o datetime.now()
        if fecha_hora is None:
            fecha_hora = datetime.now()
        
        # Si fecha_hora es datetime, convertir a string
        if isinstance(fecha_hora, datetime):
            fecha_hora_str = fecha_hora.strftime("%Y-%m-%d %H:%M:%S")
        else:
            fecha_hora_str = fecha_hora
        cursor.execute("""
            INSERT INTO Eventos 
            (FechaHora, ID_Sitio, ID_Usuario, Nombre_Actividad, Cantidad, Camera, Descripcion)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (fecha_hora_str, site_id, user_id, activity, quantity, camera, description))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return True, "Evento creado exitosamente"
        
    except Exception as e:
        print(f"[ERROR] create_event: {e}")
        return False, str(e)
    

