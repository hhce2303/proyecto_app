import tkinter as tk
from tkinter import ttk
from datetime import datetime, date
from mysql.connector import Error
import pymysql
from pathlib import Path
# al inicio del .spec
from PyInstaller.utils.hooks import collect_all
from PyInstaller.building.build_main import Analysis


def get_connection():
    """
    Establece una conexión segura con la base de datos MySQL.
    Lanza errores claros en caso de fallo (credenciales, servidor, etc.).
    """
    try:
        conn = pymysql.connect(
            host="ldbonilla.sig.com",
            user="app_user",
            password="1234",
            database="daily_log",
            port=3306
        )
        print("✅ Conexión exitosa")
        return conn
    except pymysql.Error as e:
        print("❌ Error de conexión:", e)
        return None



def test_de_columna_supervisors():
    """Ventana de prueba para mostrar el status del usuario"""
    # Obtener el status antes de crear la ventana
    status_actual = get_user_status("test")
    
    # Crear ventana
    root = tk.Tk()
    root.title("Prueba de Columna Status")
    root.geometry("400x250")
    root.configure(bg="#2c2f33")
    
    # Frame principal
    frame = ttk.Frame(root, padding="20")
    frame.pack(fill=tk.BOTH, expand=True)
    
    # Título
    label_titulo = tk.Label(
        frame, 
        text="Estado del Supervisor", 
        font=("Segoe UI", 16, "bold"),
        bg="#2c2f33",
        fg="#00bfae"
    )
    label_titulo.pack(pady=(10, 20))
    
    # Usuario
    label_user = tk.Label(
        frame,
        text="Usuario: test",
        font=("Segoe UI", 12),
        bg="#2c2f33",
        fg="#e0e0e0"
    )
    label_user.pack(pady=5)
    
    # Status
    label_status = tk.Label(
        frame,
        text=f"Status: {status_actual}",
        font=("Segoe UI", 14, "bold"),
        bg="#2c2f33",
        fg="#ffffff"
    )
    label_status.pack(pady=20)
    
    # Botón para refrescar
    def refresh_status():
        new_status = get_user_status("test")
        label_status.config(text=f"Status: {new_status}")
    
    btn_refresh = tk.Button(
        frame,
        text="🔄 Refrescar Status",
        command=refresh_status,
        bg="#4a90e2",
        fg="white",
        font=("Segoe UI", 11, "bold"),
        relief="flat",
        padx=20,
        pady=10
    )
    btn_refresh.pack(pady=10)
    
    root.mainloop()


if __name__ == "__main__":
    test_de_columna_supervisors()
# fin del .spec
