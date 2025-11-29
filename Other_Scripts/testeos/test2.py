import pymysql
from daily_log_db import get_connection
#from under_super import get_connection  
import tkinter as tk
import datetime
now = datetime.datetime.now()

# logica para solicitud de covers
username = "prueba2"
user_covering = "prueba"
user_covered = "hector"
fecha_hora_cover = now.strftime("%Y-%m-%d %H:%M:%S")
is_active = 1
fecha_creacion = now.strftime("%Y-%m-%d %H:%M:%S")



def select_covered_by(username):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cover_to_query = """
        INSERT INTO gestion_breaks_programados (User_covering, User_covered, Fecha_hora_cover, is_Active, Supervisor, Fecha_creacion)
        VALUES (%s, %s, %s, %s, %s, %s)
        """
        
        cursor.execute(cover_to_query, (user_covering, user_covered, fecha_hora_cover, is_active, username, fecha_creacion))
        conn.commit()
        
        print("el cover fue designado correctamente")
        cursor.close()
        conn.close()

    except Exception as e:
        print("Error al designar el cover:", e)
    return
    

if __name__ == "__main__":
    select_covered_by(username)


    