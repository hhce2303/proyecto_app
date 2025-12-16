from tkinter import messagebox
import traceback
from unittest import result
import backend_super
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

from models.database import get_connection
# Obtener estación asignada al usuario desde la base de datos
#     
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



# implementacion de covers...:

# - solicita un cover para el usuario dado. desde la ui principal de operador

# - desaprueba el cover activo más reciente para el usuario dado. desde la ui principal de supervisor
def desaprobar_cover(username, session_id, station):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE covers_programados
            SET Approved = 0
            WHERE ID_user = %s AND is_Active = 1
            ORDER BY ID_Cover DESC
            LIMIT 1
            """,
            (username,)
        )
        conn.commit()
        print(f"[DEBUG] Cover desaprobado correctamente para {username}")
        messagebox.showinfo("Cover Desaprobado", f"Cover desaprobado correctamente para {username}.")
    except pymysql.Error as e:
        print(f"[ERROR] al desaprobar cover: {e}")
    finally:
        cursor.close()
        conn.close()
        login.logout_silent(session_id, station)

# - Seleciona un usuario [agrega un cover programado] para el usuario dado. desde la ui principal de Supervisor
def select_user_to_cover(username):
    conn = get_connection()
    station= None
    hora_programada = "2025-01-01 00:00:00"
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO covers_programados (ID_user, Time_request, Station, Reason, Approved, is_Active)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (username, hora_programada, station, "Break programado", 1, 1)
        )
        conn.commit()
        # Obtener el último ID insertado
        cursor.execute("SELECT LAST_INSERT_ID()")
        result = cursor.fetchone()
        ID_Cover = result[0] if result else None
        print(f"[DEBUG] usuario seleccionado para cover de break: {username}, ID_Cover: {ID_Cover}")
    except pymysql.Error as e:
        print(f"[ERROR] no se habilito al usuario {e}")
        ID_Cover = None
    finally:
        cursor.close()
        conn.close()
    return ID_Cover


# - designa un cover para el usuario dado y quien realiza ese cover. desde la ui principal de supervisor
# - nuevo agregar_cover_breaks remplazo del del backend_super.py
def select_covered_by(username,hora,cover,usuario):

    try:
        # Combinar fecha de hoy con la hora proporcionada
        from datetime import datetime
        hoy = datetime.now().strftime("%Y-%m-%d")
        
        # Asegurar formato HH:MM:SS
        if len(hora.split(':')) == 2:  # Si es HH:MM
            hora = hora + ":00"
        
        fecha_hora_cover = f"{hoy} {hora}"
        user_covering = usuario
        user_covered = cover
        fecha_creacion = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        is_active = 1

        conn = get_connection()
        cursor = conn.cursor()

        # Obtener ID del usuario que cubre (user_covering)
        cursor.execute("SELECT ID_Usuario FROM user WHERE Nombre_Usuario = %s", (user_covering,))
        result_covering = cursor.fetchone()
        if result_covering:
            id_user_covering = result_covering[0]
            print(f"[DEBUG] ID del usuario que cubre: {id_user_covering}")
        else:
            messagebox.showerror("Error", f"Usuario '{user_covering}' no encontrado")
            return

        # Obtener ID del usuario a cubrir (user_covered)
        cursor.execute("SELECT ID_Usuario FROM user WHERE Nombre_Usuario = %s", (user_covered,))
        result_covered = cursor.fetchone()
        if result_covered:
            id_user_covered = result_covered[0]
            print(f"[DEBUG] ID del usuario a cubrir: {id_user_covered}")
        else:
            messagebox.showerror("Error", f"Usuario '{user_covered}' no encontrado")
            return

        # Obtener ID del supervisor (username)
        cursor.execute("SELECT ID_Usuario FROM user WHERE Nombre_Usuario = %s", (username,))
        result_supervisor = cursor.fetchone()
        if result_supervisor:
            id_supervisor = result_supervisor[0]
            print(f"[DEBUG] ID del supervisor: {id_supervisor}")
        else:
            messagebox.showerror("Error", f"Supervisor '{username}' no encontrado")
            return

        # Insertar con los IDs
        cover_to_query = """
        INSERT INTO gestion_breaks_programados (User_covering, User_covered, Fecha_hora_cover, is_Active, Supervisor, Fecha_creacion)
        VALUES (%s, %s, %s, %s, %s, %s)
        """
        
        cursor.execute(cover_to_query, (id_user_covering, id_user_covered, fecha_hora_cover, is_active, id_supervisor, fecha_creacion))
        conn.commit()
        
        cursor.close()
        conn.close()
        
        messagebox.showinfo("Éxito", "Cover agregado correctamente")
        print(f"[INFO] ✅ Cover agregado: {user_covered} cubierto por {user_covering} a las {hora}")

        
        
        # Limpiar formulario y refrescar tabla
        try:
            backend_super.limpiar_breaks()
            backend_super.refrescar_tabla_breaks()
        except Exception as e:
            print(f"[WARN] No se pudo refrescar la tabla: {e}")
            
    except Exception as e:
        print(f"[ERROR] agregar_cover_breaks: {e}")
        traceback.print_exc()
        messagebox.showerror("Error", f"Error al agregar cover: {e}")
        try:
            cursor.close()
            conn.close()
        except:
            pass
    return

def actualizar_cover_breaks(username, hora_actual, covered_by_actual, usuario_actual, nuevo_usuario):
    """
    Actualiza un cover de break existente en la base de datos mediante UPDATE.
    
    Args:
        username: Nombre del supervisor que realiza el cambio
        hora_actual: Hora del cover en formato HH:MM:SS
        covered_by_actual: Usuario que cubre (el que hace el cover)
        usuario_actual: Usuario cubierto anterior
        nuevo_usuario: Nuevo usuario cubierto
    
    Returns:
        True si la operación fue exitosa, False en caso contrario
    """
    try:
        if not nuevo_usuario or not nuevo_usuario.strip():
            print("[ERROR] Nuevo usuario vacío")
            return False
        
        if not usuario_actual or not usuario_actual.strip():
            print("[ERROR] Usuario actual vacío")
            return False
        
        conn = get_connection()
        cur = conn.cursor()
        
        # Convertir nombres a IDs
        cur.execute("SELECT ID_Usuario FROM user WHERE Nombre_Usuario = %s", (covered_by_actual,))
        result_covering = cur.fetchone()
        cur.execute("SELECT ID_Usuario FROM user WHERE Nombre_Usuario = %s", (usuario_actual,))
        result_covered_old = cur.fetchone()
        cur.execute("SELECT ID_Usuario FROM user WHERE Nombre_Usuario = %s", (nuevo_usuario,))
        result_covered_new = cur.fetchone()
        
        if not result_covering or not result_covered_old or not result_covered_new:
            print(f"[ERROR] Usuario no encontrado: covering={covered_by_actual}, old={usuario_actual}, new={nuevo_usuario}")
            cur.close()
            conn.close()
            return False
        
        id_covering = result_covering[0]
        id_covered_old = result_covered_old[0]
        id_covered_new = result_covered_new[0]
        
        # Debug: Buscar el cover antes de actualizar
        debug_query = """
            SELECT User_covering, User_covered, TIME_FORMAT(Fecha_hora_cover, '%%H:%%i:%%s') as hora, is_Active
            FROM gestion_breaks_programados
            WHERE User_covering = %s AND User_covered = %s AND is_Active = 1
        """
        cur.execute(debug_query, (id_covering, id_covered_old))
        debug_results = cur.fetchall()
        print(f"[DEBUG] Covers encontrados para covering={id_covering}, covered={id_covered_old}:")
        for row in debug_results:
            print(f"  covering={row[0]}, covered={row[1]}, hora={row[2]}, is_Active={row[3]}")
        
        # Asegurar formato HH:MM:SS con zero-padding
        if len(hora_actual.split(':')) == 2:  # Si es HH:MM
            hora_actual = hora_actual + ":00"
        
        # Normalizar formato: asegurar que las horas tengan 2 dígitos (07:00:00 no 7:00:00)
        parts = hora_actual.split(':')
        if len(parts) == 3:
            hora_actual = f"{int(parts[0]):02d}:{parts[1]}:{parts[2]}"
        
        # UPDATE directo: cambiar User_covered del cover existente
        # Usar TIME_FORMAT para comparar solo la hora sin fecha
        update_query = """
            UPDATE gestion_breaks_programados
            SET User_covered = %s
            WHERE User_covering = %s 
            AND User_covered = %s 
            AND TIME_FORMAT(Fecha_hora_cover, '%%H:%%i:%%s') = %s 
            AND is_Active = 1
        """
        cur.execute(update_query, (id_covered_new, id_covering, id_covered_old, hora_actual))
        rows_affected = cur.rowcount
        
        if rows_affected == 0:
            print(f"[WARN] No se encontró cover para actualizar: covering={covered_by_actual}(ID:{id_covering}), covered={usuario_actual}(ID:{id_covered_old}), hora={hora_actual}")
            print(f"[DEBUG] Query ejecutado: UPDATE con hora={hora_actual}")
            cur.close()
            conn.close()
            return False
        
        conn.commit()
        cur.close()
        conn.close()
        
        print(f"[INFO] ✅ Cover actualizado: {usuario_actual} → {nuevo_usuario} (cubierto por {covered_by_actual} a las {hora_actual})")
        return True
        
    except Exception as e:
        print(f"[ERROR] actualizar_cover_breaks: {e}")
        traceback.print_exc()
        return False

# Función para eliminar cover
def eliminar_cover_breaks(breaks_sheet, parent_window=None):
    """
    Elimina un cover de breaks desde la tabla breaks_sheet (formato lista).
    Tabla con columnas: ["#", "Usuario a Cubrir", "Cubierto Por", "Hora Programada"]
    
    Args:
        breaks_sheet: El tksheet widget con los datos de breaks
        parent_window: Ventana padre para los messagebox
    
    Returns:
        tuple: (success: bool, mensaje: str, rows_affected: int)
    """
    if not breaks_sheet:
        return False, "No se proporcionó el sheet de breaks", 0
    
    # Obtener selección (fila completa o celda)
    selected_rows = breaks_sheet.get_selected_rows()
    selected_cells = breaks_sheet.get_selected_cells()
    
    row_to_delete = None
    
    # Caso 1: Se seleccionó una fila completa
    if selected_rows:
        row_to_delete = list(selected_rows)[0] if isinstance(selected_rows, set) else selected_rows[0]
    
    # Caso 2: Se seleccionó una celda específica
    elif selected_cells:
        # Convertir set a lista si es necesario
        if isinstance(selected_cells, set):
            selected_cells = list(selected_cells)
        
        if selected_cells:
            cell = selected_cells[0]
            # Extraer el número de fila del objeto de celda
            if hasattr(cell, 'row'):
                row_to_delete = cell.row
            elif isinstance(cell, tuple) and len(cell) >= 1:
                row_to_delete = cell[0]
            else:
                row_to_delete = cell
    
    if row_to_delete is None:
        messagebox.showwarning("Advertencia", "Seleccione una fila para eliminar el cover.", parent=parent_window)
        return False, "No hay selección válida", 0
    
    # Obtener datos de la fila seleccionada
    # Columnas: ["#", "Usuario a Cubrir", "Cubierto Por", "Hora Programada"]
    try:
        usuario_cubierto = breaks_sheet.get_cell_data(row_to_delete, 1)  # Usuario a Cubrir
        usuario_cubre = breaks_sheet.get_cell_data(row_to_delete, 2)     # Cubierto Por
        hora = breaks_sheet.get_cell_data(row_to_delete, 3)              # Hora Programada
        
        if not usuario_cubierto or not usuario_cubre or not hora:
            messagebox.showwarning("Advertencia", "La fila seleccionada no tiene datos completos.", parent=parent_window)
            return False, "Datos incompletos", 0
        
        # Confirmar eliminación
        if not messagebox.askyesno("Confirmar", 
            f"¿Eliminar cover?\n\nUsuario a Cubrir: {usuario_cubierto}\nCubierto Por: {usuario_cubre}\nHora: {hora}", 
            parent=parent_window):
            return False, "Cancelado por el usuario", 0
        
        # Eliminar cover (soft delete)
        conn = get_connection()
        cur = conn.cursor()
        
        # Convertir nombres a IDs
        cur.execute("SELECT ID_Usuario FROM user WHERE Nombre_Usuario = %s", (usuario_cubre,))
        result_covering = cur.fetchone()
        cur.execute("SELECT ID_Usuario FROM user WHERE Nombre_Usuario = %s", (usuario_cubierto,))
        result_covered = cur.fetchone()
        
        if not result_covering or not result_covered:
            messagebox.showerror("Error", f"Usuario no encontrado en la base de datos", parent=parent_window)
            cur.close()
            conn.close()
            return False, "Usuario no encontrado", 0
        
        id_covering = result_covering[0]
        id_covered = result_covered[0]
        
        # Soft delete en la base de datos
        update_query = """
            UPDATE gestion_breaks_programados
            SET is_Active = 0
            WHERE User_covering = %s AND User_covered = %s AND TIME(Fecha_hora_cover) = %s AND is_Active = 1
        """
        cur.execute(update_query, (id_covering, id_covered, hora))
        rows_affected = cur.rowcount
        conn.commit()
        cur.close()
        conn.close()
        
        if rows_affected > 0:
            print(f"[INFO] ✅ Cover eliminado: {usuario_cubierto} cubierto por {usuario_cubre} a las {hora}")
            messagebox.showinfo("Éxito", "Cover eliminado exitosamente", parent=parent_window)
            return True, "Cover eliminado exitosamente", rows_affected
        else:
            messagebox.showwarning("Advertencia", "No se encontró el cover en la base de datos.", parent=parent_window)
            return False, "Cover no encontrado en BD", 0
            
    except Exception as e:
        print(f"[ERROR] eliminar_cover_breaks: {e}")
        traceback.print_exc()
        messagebox.showerror("Error", f"Error al eliminar cover:\n{e}", parent=parent_window)
    return False, "No hay selección válida", 0

# ==================== COVERS REALIZADOS ====================
# TODO: Implementar complete_break_cover cuando se necesite registrar covers completados
# def complete_break_cover(username, ID_cover, covered_by):
#     """Completa un cover de break registrándolo en covers_realizados"""
#     pass


def load_combined_covers():
    """
    Carga datos combinados de covers_programados y covers_realizados
    usando FULL OUTER JOIN para mostrar TODOS los covers (programados y emergencias)
    """
    try:
        conn = get_connection()
        cur = conn.cursor()
        
        # Query con UNION para incluir covers programados Y covers de emergencia (sin ID_programacion_covers)
        query = """
            SELECT 
                cp.ID_Cover,
                cp.ID_user AS Usuario,
                cp.Time_request AS Hora_Programada,
                cp.Station AS Estacion,
                cp.Reason AS Razon_Solicitud,
                CASE 
                    WHEN cp.Approved = 1 THEN 'Sí'
                    WHEN cp.Approved = 0 THEN 'No'
                    ELSE 'N/A'
                END AS Aprobado,
                CASE 
                    WHEN cp.is_Active = 1 THEN 'Activo'
                    WHEN cp.is_Active = 0 THEN 'Inactivo'
                    ELSE 'N/A'
                END AS Activo,
                cr.Cover_in AS Cover_Inicio,
                cr.Cover_Out AS Cover_Fin,
                cr.Covered_by AS Cubierto_Por,
                cr.Motivo AS Motivo_Real,
                CASE 
                    WHEN cr.Cover_in IS NOT NULL THEN 'Completado'
                    WHEN cp.Approved = 1 THEN 'Aprobado - Pendiente'
                    WHEN cp.Approved = 0 THEN 'Pendiente Aprobación'
                    ELSE 'Desconocido'
                END AS Estado
            FROM covers_programados cp
            LEFT JOIN covers_realizados cr 
                ON cp.ID_Cover = cr.ID_programacion_covers
            
            UNION
            
            SELECT 
                cr.ID_Covers AS ID_Cover,
                cr.Nombre_usuarios AS Usuario,
                NULL AS Hora_Programada,
                NULL AS Estacion,
                'Emergencia' AS Razon_Solicitud,
                'N/A' AS Aprobado,
                'N/A' AS Activo,
                cr.Cover_in AS Cover_Inicio,
                cr.Cover_out AS Cover_Fin,
                cr.Covered_by AS Cubierto_Por,
                cr.Motivo AS Motivo_Real,
                'Emergencia' AS Estado
            FROM covers_realizados cr
            WHERE cr.ID_programacion_covers IS NULL 
               OR cr.ID_programacion_covers = 0
            
            ORDER BY Cover_Inicio DESC, Hora_Programada DESC
        """
        
        cur.execute(query)
        rows = cur.fetchall()
        col_names = [desc[0] for desc in cur.description]
        
        cur.close()
        conn.close()
        
        print(f"[DEBUG] Covers cargados (programados + emergencias): {len(rows)} registros")
        return col_names, rows
        
    except Exception as e:
        print(f"[ERROR] load_combined_covers: {e}")
        import traceback
        traceback.print_exc()
        return [], []

# fin de la implentacion de covers.



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
        
        # Crear el Combobox interno con estado NORMAL (editable)
        # Si no se especifica state en kwargs, usar 'normal' por defecto
        if 'state' not in combobox_kwargs:
            combobox_kwargs['state'] = 'normal'
        
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
