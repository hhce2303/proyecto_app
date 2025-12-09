
import traceback
import tkinter as tk
from models.database import get_connection

def crear_news(tipo, nombre, urgencia, username, fecha_out=None):
    """Crea un nuevo registro en la tabla information"""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO information (info_type, name_info, urgency, publish_by, fechahora_in, fechahora_out, is_Active)
        VALUES (%s, %s, %s, %s, NOW(), %s, 1)
    """, (tipo, nombre, urgencia, username, fecha_out))
    conn.commit()
    cur.close()
    conn.close()
    return True


def cargar_news_activas():
    """Retorna lista de news activas (solo datos, sin UI)"""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM information WHERE is_Active = 1")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows

def delete_news_card_model(id_info):
    """Elimina news - retorna success/error"""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM information WHERE ID_information = %s", (id_info,))
    conn.commit()
    cur.close()
    conn.close()
    return True

def deactivate_news_card_model(id_info):
    """Desactiva una news en la base de datos dado su ID"""
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("UPDATE information SET is_Active = 0 WHERE ID_information = %s", (id_info,))
        conn.commit()
        cur.close()
        conn.close()
        print(f"[DEBUG] News ID {id_info} desactivada correctamente.")
        return True
    except Exception as e:
        print(f"[ERROR] deactivate_news_card_model: {e}")
        traceback.print_exc()
        return False
