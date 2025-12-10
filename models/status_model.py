from models.database import get_connection


def get_user_status_bd(username):
    """Obtiene el status numérico del usuario desde la BD"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT Statuses FROM sesion 
            WHERE ID_user = %s 
            ORDER BY ID DESC 
            LIMIT 1
        """, (username,))
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        
        # Retornar el valor numérico o None si no existe
        return result[0] if result else None
    except Exception as e:
        print(f"[ERROR] get_user_status_bd: {e}")
        return None


def set_new_status(new_value, username):
    """Actualiza el status del usuario en la BD"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE sesion 
            SET Statuses = %s 
            WHERE ID_user = %s 
            ORDER BY ID DESC 
            LIMIT 1
        """, (new_value, username))
        conn.commit()
        affected_rows = cursor.rowcount
        cursor.close()
        conn.close()
        return affected_rows > 0
    except Exception as e:
        print(f"[ERROR] set_new_status: {e}")
        return False