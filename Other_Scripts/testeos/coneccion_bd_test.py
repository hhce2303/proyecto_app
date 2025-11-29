import pymysql
import pymysql
import sys
from pathlib import Path

# Agregar el directorio principal al path para importar under_super
proyecto_path = Path(__file__).parent.parent.parent
sys.path.insert(0, str(proyecto_path))

import under_super

def get_user_status_bd(username):
    """
    Obtiene el status del usuario desde la tabla user_test
    
    Returns:
        str: 'Disponible', 'Ocupado', 'No molestar' o 'Desconocido'
    """
    conn = under_super.get_connection()
    if not conn:
        return "Error de conexión"
    
    try:
        cursor = conn.cursor()
        # Ejecutar query
        cursor.execute("""
            SELECT Active FROM sesion 
            WHERE ID_user = %s 
            ORDER BY ID DESC 
            LIMIT 1
        """, (username,))
        result = cursor.fetchone()
        print(f"[DEBUG] Resultado de la consulta para '{username}': {result}")
        if not result:
            return "Usuario no encontrado"
        status_value = result[0]
    except pymysql.Error as e:
        print(f"[ERROR] Error al consultar el estado: {e}")
        
    finally:
        cursor.close()
        conn.close()   

        return status_value