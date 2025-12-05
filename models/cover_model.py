# - solicita un cover para el usuario dado. desde la ui principal de operador

from tkinter import messagebox
from datetime import datetime, timedelta
import pymysql  
from models.database import get_connection
import tkinter as tk
import under_super

import login
now = datetime.now()

def request_covers(username, time_request, reason, aprvoved):

    confirmed = messagebox.askyesno("Esta seguro", "¿Está seguro de solicitar el cover?")
    
    if not confirmed:
        print("[DEBUG] Solicitud de cover cancelada por el usuario")
        return None
#Solicita un cover para el usuario dado.
    
    #Args:
        #username: Nombre de usuario que solicita el cover
        #cover_type: Tipo de cover (e.g., "break", "lunch")
        #reason: Razón para la solicitud del cover
    conn = get_connection()
    ID_cover = None
    try:
        cursor = conn.cursor()
        
        # ⭐ VERIFICAR SI YA TIENE UN COVER ACTIVO (is_Active = 1)
        cursor.execute(
            """
            SELECT ID_Cover, Time_request, is_Active
            FROM covers_programados
            WHERE ID_user = %s
            AND is_Active = 1
            ORDER BY Time_request DESC
            LIMIT 1
            """,
            (username,)
        )
        active_cover = cursor.fetchone()
        
        if active_cover:
            # Ya tiene un cover activo pendiente, no puede solicitar otro
            messagebox.showwarning(
                "Cover Activo Pendiente", 
                f"Ya tienes un cover activo solicitado a las {active_cover[1].strftime('%H:%M:%S')}.\n\n"
                f"No puedes solicitar otro cover hasta que este sea procesado o cancelado.\n\n"
                f"Estado: Pendiente de aprobación/ejecución"
            )
            print(f"[DEBUG] Solicitud rechazada: cover activo existente (ID: {active_cover[0]})")
            cursor.close()
            conn.close()
            return None
        
        # ⭐ VERIFICAR LÍMITE DE TIEMPO: 10 minutos entre solicitudes (solo del día actual)
        hoy_inicio = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        
        cursor.execute(
            """
            SELECT Time_request, is_Active
            FROM covers_programados
            WHERE ID_user = %s
            AND DATE(Time_request) = CURDATE()
            ORDER BY Time_request DESC
            LIMIT 1
            """,
            (username,)
        )
        last_request = cursor.fetchone()
        
        if last_request and last_request[0]:
            now = datetime.now()
            time_diff = now - last_request[0]
            minutes_diff = time_diff.total_seconds() / 60
            
            print(f"[DEBUG] Última solicitud: {last_request[0]}, Ahora: {now}, Diferencia: {minutes_diff:.1f} min, is_Active: {last_request[1]}")
            
            if minutes_diff < 10:
                remaining_minutes = 10 - minutes_diff
                messagebox.showwarning(
                    "Espera requerida", 
                    f"Debes esperar {remaining_minutes:.1f} minutos más antes de solicitar otro cover.\n\n"
                    f"Última solicitud: {last_request[0].strftime('%Y-%m-%d %H:%M:%S')}\n"
                    f"Próxima solicitud disponible: {(last_request[0] + timedelta(minutes=10)).strftime('%H:%M:%S')}"
                )
                print(f"[DEBUG] Solicitud rechazada: faltan {remaining_minutes:.1f} minutos")
                cursor.close()
                conn.close()
                return None

        cursor.execute(
            """
            SELECT ID_estacion
            FROM sesion
            WHERE ID_user = %s
            ORDER BY ID DESC
            LIMIT 1
            """,
            (username,)
        )
        station = cursor.fetchone()

        print(f"[DEBUG] Estación obtenida: {station}")
        cursor.execute(
            """
            INSERT INTO covers_programados (ID_user, Time_request, Station, Reason, Approved, is_Active)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (username, time_request, station, reason, aprvoved, 1)
        )
        conn.commit()
        print("[DEBUG] Cover solicitado correctamente ✅")
        # 🔹 Obtener último ID insertado
        cursor.execute("SELECT LAST_INSERT_ID()")
        ID_cover = cursor.fetchone()[0]
        print(f"[DEBUG] Nuevo ID_cover generado: {ID_cover}")
        messagebox.showinfo("Solicitud Exitosa", f"Cover solicitado correctamente.")

    except pymysql.Error as e:
        print(f"[ERROR] al solicitar cover: {e}")
    finally:
        cursor.close()
        conn.close() 
    return ID_cover

# cover programado.
def insertar_cover(username, Covered_by, Motivo, session_id, station):
    ID_cover = None
    Cover_in = (now + timedelta(minutes=2)).strftime("%Y-%m-%d %H:%M:%S")
    Activo = False
    Cover_Out= None
    tiene_cover_programado = False
    
    # ⭐ VERIFICAR SI TIENE COVER PROGRAMADO (covers_programados O gestion_breaks_programados)
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # 1. Buscar en covers_programados (sistema antiguo)
        cursor.execute(
            """
            SELECT cp.ID_Cover
            FROM covers_programados cp
            WHERE cp.ID_user = %s
            AND cp.Approved = 1
            AND cp.is_Active = 1
            ORDER BY cp.ID_Cover DESC
            LIMIT 1
            """,
            (username,)
        )
        result = cursor.fetchone()
        
        if result is not None:
            ID_cover = result[0]
            tiene_cover_programado = True
            print(f"[DEBUG] Cover programado encontrado en covers_programados - ID_cover: {ID_cover}")
        else:
            # 2. Buscar en gestion_breaks_programados (breaks programados por supervisor)
            # Necesitamos ID_Usuario para buscar
            cursor.execute("SELECT ID_Usuario FROM user WHERE Nombre_Usuario = %s", (username,))
            user_row = cursor.fetchone()
            
            if user_row:
                id_usuario = user_row[0]
                
                # Buscar break programado activo en una ventana de +/- 5 minutos de la hora actual
                cursor.execute(
                    """
                    SELECT gbp.ID_cover
                    FROM gestion_breaks_programados gbp
                    WHERE gbp.User_covered = %s
                    AND gbp.is_Active = 1
                    AND ABS(TIMESTAMPDIFF(MINUTE, gbp.Fecha_hora_cover, NOW())) <= 5
                    ORDER BY ABS(TIMESTAMPDIFF(MINUTE, gbp.Fecha_hora_cover, NOW())) ASC
                    LIMIT 1
                    """,
                    (id_usuario,)
                )
                break_result = cursor.fetchone()
                
                if break_result is not None:
                    ID_cover = break_result[0]
                    tiene_cover_programado = True
                    print(f"[DEBUG] Break programado encontrado en gestion_breaks_programados - ID_cover: {ID_cover}")
        
        # Si no se encontró ningún cover programado, preguntar si es emergencia
        if not tiene_cover_programado:
            print("[DEBUG] No se encontró cover/break programado. Registrando como cover de emergencia...")
            # Preguntar al usuario si desea registrar cover de emergencia
            confirmacion = messagebox.askyesno(
                "Cover de Emergencia",
                "No tienes un cover programado aprobado.\n\n"
                "¿Deseas registrar este cover como EMERGENCIA?\n\n"
                "Nota: Los covers de emergencia quedan registrados sin ID de programación."
            )
            if not confirmacion:
                print("[DEBUG] Usuario canceló el registro de cover de emergencia")
                cursor.close()
                conn.close()
                return None
            
            # ID_cover queda como None para covers de emergencia
            tiene_cover_programado = False
        
        cursor.close()
        conn.close()
        
    except pymysql.Error as e:
        print(f"[ERROR] al verificar cover programado: {e}")
        messagebox.showerror("Error", f"Error al verificar cover programado: {e}")
        return None
    
    # ⭐ INSERTAR COVER REALIZADO (con o sin ID_programacion_covers)
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO covers_realizados (Nombre_Usuarios, ID_programacion_covers, Cover_in, Cover_Out, Covered_by, Motivo)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (username, ID_cover, Cover_in, Cover_Out, Covered_by, Motivo)
        )
        conn.commit()
        
        # ⭐ SOLO actualizar covers_programados SI tiene cover programado
        if tiene_cover_programado and ID_cover is not None:
            try:
                cursor.execute(
                    """UPDATE covers_programados SET is_Active = 0 WHERE ID_Cover = %s""",
                    (ID_cover,)
                )
                conn.commit()
                print(f"[DEBUG] is_Active actualizado correctamente en covers_programados para ID_Cover: {ID_cover}")
            except pymysql.Error as e:
                print(f"[ERROR] al actualizar is_Active en covers_programados: {e}")
        else:
            print(f"[DEBUG] Cover de emergencia registrado SIN actualizar covers_programados")
        
        # Si el motivo es "Break", también actualizar gestion_breaks_programados
        if Motivo and Motivo.strip().lower() == "break":
            try:
                conn2 = get_connection()
                cursor2 = conn2.cursor()
                
                # Obtener ID_Usuario del username
                cursor2.execute("SELECT ID_Usuario FROM user WHERE Nombre_Usuario = %s", (username,))
                result = cursor2.fetchone()
                
                if result:
                    id_usuario = result[0]
                    cursor2.execute(
                        """UPDATE gestion_breaks_programados SET is_Active = 0 
                           WHERE User_covered = %s AND is_Active = 1""",
                        (id_usuario,)
                    )
                    rows_affected = cursor2.rowcount
                    conn2.commit()
                    print(f"[DEBUG] is_Active actualizado en gestion_breaks_programados ({rows_affected} rows)")
                else:
                    print(f"[WARN] Usuario {username} no encontrado para actualizar gestion_breaks_programados")
                
                cursor2.close()
                conn2.close()
                
            except pymysql.Error as e:
                print(f"[ERROR] al actualizar is_Active en gestion_breaks_programados: {e}")

        print("[DEBUG] Cover realizado correctamente ✅")
        
        # Obtener último ID insertado
        cursor.execute("SELECT LAST_INSERT_ID()")
        ID_cover_realizado = cursor.fetchone()[0]
        
        # Mensaje de confirmación diferenciado
        if tiene_cover_programado:
            messagebox.showinfo("Cover Registrado", "Cover registrado exitosamente.")
        else:
            messagebox.showwarning(
                "Cover de Emergencia Registrado", 
                "⚠️ Cover de EMERGENCIA registrado.\n\n"
                "Este cover no estaba programado previamente.\n"
                "Será revisado por supervisión."
            )

    except pymysql.Error as e:
        print(f"[ERROR] al insertar cover realizado: {e}")
        messagebox.showerror("Error", f"Error al registrar cover: {e}")
    finally:
        cursor.close()
        conn.close()
        login.logout_silent(session_id, station)

