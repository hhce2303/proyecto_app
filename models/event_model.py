





from datetime import datetime
from models.database import get_connection


def add_event(username, site, activity, quantity, camera, desc, hour, minute, second):
    """
    Inserta un nuevo evento en la tabla Eventos en MySQL con tipos correctos.
    """
    conn = get_connection()
    if conn is None:
        print("❌ No se pudo conectar a la base de datos")
        return

    try:
        cursor = conn.cursor()

        # 🔹 Obtener ID_Usuario
        cursor.execute("SELECT ID_Usuario FROM user WHERE Nombre_Usuario=%s", (username,))
        row = cursor.fetchone()
        if not row:
            raise Exception(f"Usuario '{username}' no encontrado")
        user_id = int(row[0])

        # 🔹 Obtener ID_Sitio desde el site_value (ej: "NombreSitio 305")
        try:
            site_id = int(site.split()[-1])
        except Exception:
            raise Exception(f"No se pudo obtener el ID del sitio desde '{site}'")

        # 🔹 Construir datetime editable
        event_time = datetime.now().replace(hour=hour, minute=minute, second=second, microsecond=0)

        # 🔹 Convertir cantidad a número
        try:
            quantity_val = float(quantity)  # o int(quantity) si siempre es entero
        except Exception:
            quantity_val = 0  # fallback

        # 🔹 Insertar en tabla Eventos
        cursor.execute("""
            INSERT INTO Eventos (FechaHora, ID_Sitio, Nombre_Actividad, Cantidad, Camera, Descripcion, ID_Usuario)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (event_time, site_id, str(activity), quantity_val, str(camera), str(desc), user_id))

        conn.commit()
        print(f"[DEBUG] Evento registrado correctamente por {username}")

    except Exception as e:
        print(f"[ERROR] add_event: {e}")

    finally:
        try:
            cursor.close()
            conn.close()
        except:
            pass




