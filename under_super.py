import backend_super
import os
import  csv
import tkinter as tk
from tkinter import ttk
from datetime import datetime, date
from mysql.connector import Error
import pymysql
from pathlib import Path
# al inicio del .spec
from PyInstaller.utils.hooks import collect_all
from PyInstaller.building.build_main import Analysis



ICON_PATH = r"\\192.168.7.12\Data SIG\Central Station SLC-COLOMBIA\1. Daily Logs - Operators\DataBase\icons"
import pyodbc

ACCESS_DB_PATH = r"\\192.168.7.12\Data SIG\Central Station SLC-COLOMBIA\1. Daily Logs - Operators\DataBase\Base de Datos\Daily_log1.accdb"
# 📂 Ruta compartida para el archivo de configuración
CONFIG_PATH = Path=r"\\192.168.7.12\Data SIG\Central Station SLC-COLOMBIA\1. Daily Logs - Operators\DataBase\Base de Datos\roles_config.json"

class FilteredCombobox(ttk.Combobox):
    def __init__(self, master=None, **kwargs):
        # Extraer parámetros personalizados para el borde
        bordercolor = kwargs.pop('bordercolor', '#5ab4ff')
        borderwidth = kwargs.pop('borderwidth', 3)
        background = kwargs.pop('background', '#2b2b2b')
        foreground = kwargs.pop('foreground', '#ffffff')
        fieldbackground = kwargs.pop('fieldbackground', '#2b2b2b')
        arrowcolor = kwargs.pop('arrowcolor', '#ffffff')
        
        # Crear estilo único para este widget
        style = ttk.Style()
        style_name = f"Bordered.TCombobox.{id(self)}"
        
        # Configurar el estilo con borde prominente
        style.configure(style_name,
            fieldbackground=fieldbackground,
            background=background,
            foreground=foreground,
            arrowcolor=arrowcolor,
            bordercolor=bordercolor,
            lightcolor=bordercolor,
            darkcolor=bordercolor,
            borderwidth=borderwidth,
            relief='solid'
        )
        
        style.map(style_name,
            fieldbackground=[('readonly', fieldbackground), ('disabled', '#1a1a1a')],
            foreground=[('readonly', foreground), ('disabled', '#666666')],
            bordercolor=[('focus', bordercolor), ('!focus', bordercolor)],
            lightcolor=[('focus', bordercolor), ('!focus', bordercolor)],
            darkcolor=[('focus', bordercolor), ('!focus', bordercolor)]
        )
        
        # Aplicar el estilo
        kwargs['style'] = style_name
        
        super().__init__(master, **kwargs)
        self.original_values = self['values']
        self.bind('<KeyRelease>', self.check_key)
        
        # Configurar colores del Entry interno
        try:
            self.configure(foreground=foreground)
        except:
            pass

    def check_key(self, event):
        value = self.get()
        if value == '':
            self['values'] = self.original_values
        else:
            filtered = [item for item in self.original_values if value.lower() in str(item).lower()]
            self['values'] = filtered
    

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

def get_sites():
    """Obtiene la lista de sitios de la tabla Sitios"""
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
        print(f"[DEBUG] Sitios cargados")  # debug
        return sites

    except Exception as e:
        print(f"[ERROR] get_sites: {e}")
        return []
    finally:
        try:
            cursor.close()
            conn.close()
        except:
            pass

def get_activities():
    """Obtiene la lista de actividades de la tabla Actividades"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""SELECT Nombre_Actividad FROM Actividades ORDER BY Nombre_Actividad""")
        
        activities = [row[0] for row in cursor.fetchall()]
        print(f"[DEBUG] Actividades cargadas")  # debug
        return activities
    except Exception as e:
        print(f"[ERROR] get_activities: {e}")
        return []
    finally:
        try:
            cursor.close()
            conn.close()
        except:
            pass

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

def add_cover(station_id, username, new_user, cover_reason):
    conn = get_connection()
    cursor = conn.cursor()

    try:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("""
            INSERT INTO Eventos (FechaHora, Nombre_Actividad, Cantidad, Camera, Descripcion, ID_Usuario)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            now,                  # FechaHora → datetime válido
            f"{username} - Covered by {new_user}",              # Nombre_Actividad → texto                    # Cantidad → número
            f"Station: {station_id}",           # Camera o Station → número si la columna es Number
            cover_reason,
            0,                                  # Descripcion → texto
            10                     # ID_Usuario → ajusta a un id real existente
        ))
        conn.commit()
        print("[DEBUG] Evento insertado correctamente")
    except Exception as e:
        print("[ERROR]", e)
    finally:
        cursor.close()
        conn.close()



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
        
        # Crear estilo para el Combobox interno (SIN layout personalizado)
        style = ttk.Style()
        style_name = f"Dark.TCombobox"
        
        # Solo configurar si no existe ya
        try:
            style.configure(style_name,
                fieldbackground=fieldbackground,
                background=background,
                foreground=foreground,
                arrowcolor=arrowcolor,
                borderwidth=0,
                relief='flat'
            )
            
            style.map(style_name,
                fieldbackground=[('readonly', fieldbackground), ('disabled', '#1a1a1a')],
                foreground=[('readonly', foreground), ('disabled', '#666666')]
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
