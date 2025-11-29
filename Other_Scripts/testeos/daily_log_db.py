from tkinter import ttk
from datetime import datetime, date
from mysql.connector import Error
import pymysql
from pathlib import Path

def get_connection():
    """
    Establece una conexión segura con la base de datos MySQL.
    Lanza errores claros en caso de fallo (credenciales, servidor, etc.).
    """
    try:
        conn = pymysql.connect(
            host="192.168.101.135",
            user="app_user",
            password="1234",
            database="daily_log",
            port=3306
        )
        print("✅ Conexión exitosa")
    except pymysql.Error as e:
        print("❌ Error de conexión:", e)
        return None
    return conn

if __name__ == "__main__":
    # Prueba de conexión
    connection = get_connection()
    if connection:
        connection.close()