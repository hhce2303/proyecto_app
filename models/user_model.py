

from models.database import get_connection
import pymysql



# Cargar usuarios desde la base de datos
def load_users():
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT Nombre_Usuario FROM user ORDER BY Nombre_Usuario")
        users = [row[0] for row in cursor.fetchall()]
        cursor.close()
        conn.close()
        return users
    except Exception as e:
        print(f"[ERROR] load_users: {e}")
        return ["Error al cargar usuarios"]

users_list = load_users()


def get_user_status_bd(username):
    conn = get_connection()
    if not conn:
        return "Error de conexión"
    
    try:
        cursor = conn.cursor()
        # Ejecutar query
        cursor.execute("""
            SELECT Statuses FROM sesion 
            WHERE ID_user = %s 
            ORDER BY ID DESC 
            LIMIT 1
        """, (username,))
        result = cursor.fetchone()
        if not result:
            return "Usuario no encontrado"
        status_value = result[0]
    except pymysql.Error as e:
        print(f"[ERROR] Error al consultar el estado: {e}")
        
    finally:
        cursor.close()
        conn.close()
        return status_value
    
def get_username_by_id(user_id):
    conn = get_connection()
    if not conn:
        return "Error de conexión"
    
    try:
        cursor = conn.cursor()
        # Ejecutar query
        cursor.execute("""SELECT Nombre_Usuario FROM user WHERE ID_Usuario = %s""", (user_id,))
        result = cursor.fetchone()
        if not result:
            return "Usuario no encontrado"
        username = result[0]
    except pymysql.Error as e:
        print(f"[ERROR] Error al consultar el nombre de usuario: {e}")

    finally:
        cursor.close()
        conn.close()
        return username
    
def get_user_id_by_name(username):
    conn = get_connection()
    if not conn:
        return None
    
    try:
        cursor = conn.cursor()
        # Ejecutar query
        cursor.execute("""SELECT ID_Usuario FROM user WHERE Nombre_Usuario = %s""", (username,))
        result = cursor.fetchone()
        if not result:
            return None
        user_id = result[0]
    except pymysql.Error as e:
        print(f"[ERROR] Error al consultar el ID de usuario: {e}")

    finally:
        cursor.close()
        conn.close()
        return user_id
    
def get_station_id_by_number(station):
    conn = get_connection()
    if not conn:
        return None
    
    try:
        cursor = conn.cursor()
        # Ejecutar query
        cursor.execute("""SELECT ID_station FROM stations_id WHERE nombre_estacion = %s""", (station,))
        result = cursor.fetchone()
        if not result:
            return None
        station_id = result[0]
    except pymysql.Error as e:
        print(f"[ERROR] Error al consultar el ID de estación: {e}")

    finally:
        cursor.close()
        conn.close()
        return station_id
    
def get_station_number_by_id(station_id):
    conn = get_connection()
    if not conn:
        return None
    
    try:
        cursor = conn.cursor()
        # Ejecutar query
        cursor.execute("""SELECT ID_station FROM stations_id WHERE nombre_estacion = %s""", (station_id,))
        result = cursor.fetchone()
        if not result:
            return None
        station_number = result[0]
    except pymysql.Error as e:
        print(f"[ERROR] Error al consultar el número de estación: {e}")

    finally:
        cursor.close()
        conn.close()
        return station_number