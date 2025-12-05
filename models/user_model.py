
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
