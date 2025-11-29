import mysql.connector
from mysql.connector import Error
import tkinter as tk
import pymysql

def create_connection():
    try:
        conn = pymysql.connect(
            host="192.168.101.129",
            user="app_user",
            password="1234",
            database="daily",
            port=3306
        )
        print("✅ Conexión exitosa")
    except pymysql.Error as e:
        print("❌ Error de conexión:", e)
        return None
    return conn
# --- Función del formulario ---
def open_form(option):
    form_win = tk.Tk()
    form_win.title(f"Formulario {option}")
    form_win.configure(bg="#2c2f33")
    form_win.geometry("300x220")
    form_win.resizable(False, False)

    if option == "Sitio":
        # Labels + Entradas
        tk.Label(form_win, text="ID Sitio:", bg="#2c2f33", fg="white", font=("Segoe UI", 10)).place(x=20, y=20)
        id_sitio = tk.Entry(form_win, font=("Segoe UI", 10))
        id_sitio.place(x=120, y=20, width=150)
        id_sitio.insert(0, "141")  # valor de prueba

        tk.Label(form_win, text="ID Grupo:", bg="#2c2f33", fg="white", font=("Segoe UI", 10)).place(x=20, y=60)
        id_grupo = tk.Entry(form_win, font=("Segoe UI", 10))
        id_grupo.place(x=120, y=60, width=150)
        id_grupo.insert(0, "AS")  # valor de prueba

        tk.Label(form_win, text="Nombre:", bg="#2c2f33", fg="white", font=("Segoe UI", 10)).place(x=20, y=100)
        nombre = tk.Entry(form_win, font=("Segoe UI", 10))
        nombre.place(x=120, y=100, width=150)
        nombre.insert(0, "As Plaza Audi")  # valor de prueba

        tk.Label(form_win, text="Time Zone:", bg="#2c2f33", fg="white", font=("Segoe UI", 10)).place(x=20, y=140)
        time_zone = tk.Entry(form_win, font=("Segoe UI", 10))
        time_zone.place(x=120, y=140, width=150)
        time_zone.insert(0, "ET")  # valor de prueba

        # --- Botón guardar ---
        def guardar():
            try:
                conn = create_connection()
                if conn is None:
                    raise Exception("No se pudo conectar a MySQL")

                cursor = conn.cursor()

                # ✅ Consulta adaptada a MySQL
                query = """
                INSERT INTO Sitios (ID_Sitio, ID_Grupo, Nombre_Sitio, Time_Zone)
                VALUES (%s, %s, %s, %s)
                """
                values = (
                    id_sitio.get(),
                    id_grupo.get(),
                    nombre.get(),
                    time_zone.get()
                )

                cursor.execute(query, values)
                conn.commit()
                conn.close()

                print("✅ Sitio guardado en MySQL correctamente")

                tk.Label(
                    form_win, text="✔ Guardado exitosamente",
                    bg="#2c2f33", fg="#a3f9c5",
                    font=("Segoe UI", 9, "bold")
                ).place(x=80, y=190)

            except Exception as e:
                print("⚠ Error al guardar:", e)
                tk.Label(
                    form_win, text=f"⚠ Error: {e}",
                    bg="#2c2f33", fg="#f9a3a3",
                    font=("Segoe UI", 9, "bold")
                ).place(x=20, y=190)

        tk.Button(
            form_win, text="Guardar",
            bg="#314052", fg="white",
            font=("Segoe UI", 10, "bold"),
            command=guardar
        ).place(x=100, y=180, width=100, height=30)

    form_win.mainloop()


# --- Ejecución ---
if __name__ == "__main__":
    open_form("Sitio")