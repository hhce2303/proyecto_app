from logging import root
from tkinter import messagebox
import backend_super
import os
import  csv
import tkinter as tk
from tkinter import ttk
from datetime import datetime, date, timedelta
from mysql.connector import Error
import pymysql
from pathlib import Path
# al inicio del .spec
from PyInstaller.utils.hooks import collect_all
from PyInstaller.building.build_main import Analysis

import login

now = datetime.now()

ICON_PATH = r"\\192.168.7.12\Data SIG\Central Station SLC-COLOMBIA\1. Daily Logs - Operators\DataBase\icons"
import pyodbc

ACCESS_DB_PATH = r"\\192.168.7.12\Data SIG\Central Station SLC-COLOMBIA\1. Daily Logs - Operators\DataBase\Base de Datos\Daily_log1.accdb"
# 📂 Ruta compartida para el archivo de configuración
CONFIG_PATH = Path=r"\\192.168.7.12\Data SIG\Central Station SLC-COLOMBIA\1. Daily Logs - Operators\DataBase\Base de Datos\roles_config.json"




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
            database="daily",
            port=3306
        )
        print("✅ Conexión exitosa")
    except pymysql.Error as e:
        print("❌ Error de conexión:", e)
        return None
    return conn
    
def get_station(username):
    conn = get_connection()
    station = None
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT ID_estacion
            FROM sesion
            WHERE ID_user = %s
            """,
            (username,)
        )
        result = cursor.fetchone()
        print(f"[DEBUG] al obtener estación: {station}")
        if result:
            station = result[0]
    except pymysql.Error as e:
        print(f"[ERROR] al obtener estación: {e}")
    finally:
        cursor.close()
        conn.close()
    return station

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
        messagebox.showinfo("Solicitud Exitosa", f"Cover solicitado correctamente. ID Cover: {ID_cover}")

    except pymysql.Error as e:
        print(f"[ERROR] al solicitar cover: {e}")
    finally:
        cursor.close()
        conn.close() 
    return ID_cover

def insertar_cover(username, Covered_by, Motivo, session_id, station):
    ID_cover = None
    Cover_in = (now + timedelta(minutes=2)).strftime("%Y-%m-%d %H:%M:%S")
    Activo = False
    Cover_Out= None
    if ID_cover is None:
        try:
            conn = get_connection()
        
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT cp.ID_Cover
                FROM covers_programados cp
                WHERE cp.ID_user = %s
                AND cp.Approved = 1
                ORDER BY cp.ID_Cover DESC
                LIMIT 1
                """,
                (username)
            )
            result = cursor.fetchone()
            if result is not None:
                ID_cover = result[0]
                print(f"[DEBUG] al obtener ID_cover: {ID_cover}")
                
            else:
                print("[DEBUG] No se encontró ningún ID_cover aprobado para este usuario.")
        except pymysql.Error as e:
            print(f"[ERROR] al obtener ID_cover: {e}")
    
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
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute(
                        """UPDATE covers_programados SET is_Active = 0 WHERE is_Active = 1 AND ID_user = %s""",
                        (username,)
                    )
            conn.commit()
            

            print(f"[DEBUG] is_Active actualizado correctamente")

        except pymysql.Error as e:
            print(f"[ERROR] al actualizar is_Active: {e}")

        print("[DEBUG] Cover realizado correctamente ✅")

        # 🔹 Obtener último ID insertado
        cursor.execute("SELECT LAST_INSERT_ID()")
        ID_cover = cursor.fetchone()[0]

    except pymysql.Error as e:
        print(f"[ERROR] al realizar cover: {e}")
    finally:
        cursor.close()
        conn.close()
        login.logout_silent(session_id, station)


def set_new_status(new_value, username):
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("UPDATE sesion SET Active = %s WHERE ID_user = %s ORDER BY ID DESC LIMIT 1",
                            (new_value, username))
            conn.commit()
            cursor.close()
            conn.close()
            return print("Status updated")

def get_user_status_bd(username):
    conn = get_connection()
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
        if not result:
            return "Usuario no encontrado"
        status_value = result[0]
    except pymysql.Error as e:
        print(f"[ERROR] Error al consultar el estado: {e}")
        
    finally:
        cursor.close()
        conn.close()   

        return status_value

def get_events():
    print("events")

    return 

def single_window(name, func):
        if name in opened_windows and opened_windows[name].winfo_exists():
            opened_windows[name].focus()
            return
        win = func()
        opened_windows[name] = win

        opened_windows = {}  # Para controlar ventanas abiertas

# 🔄 CACHE CON AUTO-REFRESH para Sitios y Actividades
_sites_cache = {'data': None, 'last_update': None}
_activities_cache = {'data': None, 'last_update': None}
CACHE_DURATION = 120  # 2 minutos en segundos

def get_sites(force_refresh=False):
    """
    Obtiene la lista de sitios de la tabla Sitios con cache de 2 minutos
    
    Args:
        force_refresh: Si es True, fuerza actualización ignorando cache
        
    Returns:
        Lista de sitios en formato "Nombre_Sitio (ID)"
    """
    global _sites_cache
    
    # Verificar si necesita actualización
    now = datetime.now()
    needs_update = (
        force_refresh or 
        _sites_cache['data'] is None or 
        _sites_cache['last_update'] is None or
        (now - _sites_cache['last_update']).total_seconds() > CACHE_DURATION
    )
    
    if not needs_update:
        print(f"[DEBUG] Usando cache de sitios (edad: {int((now - _sites_cache['last_update']).total_seconds())}s)")
        return _sites_cache['data']
    
    try:
        conn = get_connection()
        cursor = conn.cursor()

        # Formato modernizado: "Nombre_Sitio (ID)" para permitir búsqueda por ID y por nombre
        cursor.execute("""
            SELECT CONCAT(Nombre_Sitio, ' (', ID_Sitio, ')') AS Sitio
            FROM Sitios
            ORDER BY Nombre_Sitio
        """)

        sites = [row[0] for row in cursor.fetchall()]
        
        # Actualizar cache
        _sites_cache['data'] = sites
        _sites_cache['last_update'] = now
        
        print(f"[DEBUG] Sitios cargados y cache actualizado ({len(sites)} sitios)")
        return sites

    except Exception as e:
        print(f"[ERROR] get_sites: {e}")
        # Si hay error pero tenemos cache, devolverlo
        if _sites_cache['data']:
            print(f"[WARN] Usando cache antiguo de sitios por error de BD")
            return _sites_cache['data']
        return []
    finally:
        try:
            cursor.close()
            conn.close()
        except:
            pass

def get_activities(force_refresh=False):
    """
    Obtiene la lista de actividades de la tabla Actividades con cache de 2 minutos
    
    Args:
        force_refresh: Si es True, fuerza actualización ignorando cache
        
    Returns:
        Lista de nombres de actividades
    """
    global _activities_cache
    
    # Verificar si necesita actualización
    now = datetime.now()
    needs_update = (
        force_refresh or
        _activities_cache['data'] is None or 
        _activities_cache['last_update'] is None or
        (now - _activities_cache['last_update']).total_seconds() > CACHE_DURATION
    )
    
    if not needs_update:
        print(f"[DEBUG] Usando cache de actividades (edad: {int((now - _activities_cache['last_update']).total_seconds())}s)")
        return _activities_cache['data']
    
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""SELECT Nombre_Actividad FROM Actividades ORDER BY Nombre_Actividad""")
        
        activities = [row[0] for row in cursor.fetchall()]
        
        # Actualizar cache
        _activities_cache['data'] = activities
        _activities_cache['last_update'] = now
        
        print(f"[DEBUG] Actividades cargadas y cache actualizado ({len(activities)} actividades)")
        return activities
        
    except Exception as e:
        print(f"[ERROR] get_activities: {e}")
        # Si hay error pero tenemos cache, devolverlo
        if _activities_cache['data']:
            print(f"[WARN] Usando cache antiguo de actividades por error de BD")
            return _activities_cache['data']
        return []
    finally:
        try:
            cursor.close()
            conn.close()
        except:
            pass

def parse_site_filter(site_display):
    """
    🔧 HELPER: Deconstruye el formato "Nombre_Sitio (ID)" del FilteredCombobox
    
    Permite búsqueda flexible por:
    - Formato completo: "Site Name (123)" -> retorna (nombre, id)
    - Solo ID: "123" -> retorna (None, id)
    - Solo nombre: "Site Name" -> retorna (nombre, None)
    
    Args:
        site_display: String del FilteredCombobox (ej: "CARULLA CALLE 79 (305)")
        
    Returns:
        tuple: (site_name, site_id) donde cada uno puede ser None
        
    Ejemplos:
        >>> parse_site_filter("CARULLA CALLE 79 (305)")
        ("CARULLA CALLE 79", "305")
        
        >>> parse_site_filter("305")
        (None, "305")
        
        >>> parse_site_filter("CARULLA CALLE 79")
        ("CARULLA CALLE 79", None)
    """
    import re
    
    if not site_display or not site_display.strip():
        return None, None
    
    site_display = site_display.strip()
    
    # Patrón: "Nombre (123)" -> extraer nombre e ID
    match = re.match(r'^(.+?)\s*\((\d+)\)$', site_display)
    if match:
        site_name = match.group(1).strip()
        site_id = match.group(2).strip()
        return site_name, site_id
    
    # Si es solo un número, asumir que es un ID
    if site_display.isdigit():
        return None, site_display
    
    # Si no coincide con el patrón, asumir que es solo el nombre
    return site_display, None

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

def admin_mode():
     print("admin mode")

# ------------------------------
# Combobox filtrable con borde visible
# ------------------------------
class FilteredCombobox(tk.Frame):
    """FilteredCombobox envuelto en un Frame con borde azul prominente"""
    def __init__(self, master=None, **kwargs):
        # Extraer parámetros de borde y colores
        bordercolor = kwargs.pop('bordercolor', '#5ab4ff')
        borderwidth = kwargs.pop('borderwidth', 3)
        background = kwargs.pop('background', '#2b2b2b')
        foreground = kwargs.pop('foreground', '#ffffff')
        fieldbackground = kwargs.pop('fieldbackground', '#2b2b2b')
        arrowcolor = kwargs.pop('arrowcolor', '#ffffff')
        
        # Crear Frame con borde prominente
        super().__init__(master, bg=bordercolor, bd=0, highlightthickness=borderwidth, 
                        highlightbackground=bordercolor, highlightcolor=bordercolor)
        
        # Filtrar opciones válidas para ttk.Combobox
        valid_options = {
            'textvariable', 'values', 'font', 'height', 'width', 'state',
            'exportselection', 'justify', 'postcommand', 'validate', 'validatecommand'
        }
        
        combobox_kwargs = {k: v for k, v in kwargs.items() if k in valid_options}
        
        # Crear estilo único para el Combobox interno
        style = ttk.Style()
        style_name = f"Custom{id(self)}.TCombobox"  # Único por widget
        
        try:
            # Usar 'clam' theme para mejor personalización
            try:
                style.theme_use('clam')
            except:
                pass
            
            style.configure(style_name,
                fieldbackground=fieldbackground,
                background=background,
                foreground=foreground,
                arrowcolor=arrowcolor,
                borderwidth=0,
                relief='flat',
                insertcolor=foreground,
                selectbackground='#4a90e2',
                selectforeground='#ffffff'
            )
            
            style.map(style_name,
                fieldbackground=[
                    ('readonly', fieldbackground),
                    ('!readonly', fieldbackground),
                    ('disabled', '#1a1a1a'),
                    ('focus', fieldbackground),
                    ('!focus', fieldbackground)
                ],
                background=[
                    ('readonly', background),
                    ('!readonly', background),
                    ('active', background)
                ],
                foreground=[
                    ('readonly', foreground),
                    ('!readonly', foreground),
                    ('disabled', '#666666'),
                    ('focus', foreground)
                ]
            )
        except Exception as e:
            print(f"[DEBUG] Style config error (non-critical): {e}")
        
        # Crear el Combobox interno
        self._combobox = ttk.Combobox(self, style=style_name, **combobox_kwargs)
        self._combobox.pack(fill='both', expand=True, padx=0, pady=0)
        
        # Guardar valores originales para filtrado
        vals = self._combobox['values']
        try:
            self.original_values = tuple(vals) if vals is not None else ()
        except Exception:
            try:
                self.original_values = tuple([vals])
            except Exception:
                self.original_values = ()
        
        # Vincular evento de teclado para filtrado
        self._suppress_clear = True
        self._combobox.bind('<KeyRelease>', self.check_key)
        
        # Inicializar valor si existe
        try:
            init_val = self._combobox.get()
            if init_val:
                self._combobox.set(init_val)
                if init_val in self.original_values:
                    try:
                        self._combobox.current(self.original_values.index(init_val))
                    except Exception:
                        pass
        finally:
            try:
                self.after(50, lambda: setattr(self, '_suppress_clear', False))
            except Exception:
                self._suppress_clear = False
    
    def check_key(self, event):
        """Filtrar valores según tecleo"""
        if getattr(self, '_suppress_clear', False):
            return
        
        value = self._combobox.get()
        if value == '':
            try:
                self._combobox['values'] = self.original_values
            except Exception:
                self._combobox.configure(values=self.original_values)
        else:
            filtered = [item for item in self.original_values if value.lower() in str(item).lower()]
            try:
                self._combobox['values'] = filtered
            except Exception:
                self._combobox.configure(values=tuple(filtered))
    
    # Métodos proxy para que funcione como un Combobox normal
    def get(self):
        return self._combobox.get()
    
    def set(self, value):
        return self._combobox.set(value)
    
    def current(self, index=None):
        if index is None:
            return self._combobox.current()
        return self._combobox.current(index)
    
    def bind(self, sequence=None, func=None, add=None):
        return self._combobox.bind(sequence, func, add)
    
    def focus_set(self):
        return self._combobox.focus_set()
    
    def configure(self, **kwargs):
        # Redirigir configuración al combobox interno
        return self._combobox.configure(**kwargs)
    
    def config(self, **kwargs):
        return self.configure(**kwargs)
    
    def __getitem__(self, key):
        return self._combobox[key]
    
    def __setitem__(self, key, value):
        self._combobox[key] = value
