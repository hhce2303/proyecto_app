import tkinter as tk
from datetime import datetime, timedelta
import json
from pathlib import Path
import re
from tkinter import ttk, messagebox, simpledialog, filedialog
import login
import json
import re
import traceback
import pandas as pd
#
import under_super

from models.database import get_connection
from models.user_model import get_user_status_bd

#
from tkinter import font as tkfont
import pymysql
from tksheet import Sheet


# Global flag for tksheet availability
USE_SHEET = False
try:
    from tksheet import Sheet as _SheetTest
    USE_SHEET = True
except Exception:
    USE_SHEET = False

opened_windows = {}

# Variables globales para sesión actual y cover
prev_user = None
prev_session_id = None
cover_state_active = False

now = datetime.now()

# --- Helpers para ventanas únicas (singleton por función) ---
def _focus_singleton(key):
    """Si existe una ventana registrada con 'key', traerla al frente y devolverla; si no, None."""
    win = opened_windows.get(key)
    try:
        if win is not None and win.winfo_exists():
            try:
                win.deiconify()
            except Exception:
                pass
            try:
                win.lift()
            except Exception:
                pass
            try:
                win.focus_force()
            except Exception:
                pass
            # Generar evento personalizado para que la ventana recargue datos
            try:
                win.event_generate("<<WindowRefocused>>", when="tail")
            except Exception:
                pass
            return win
    except Exception:
        pass
    return None

def _register_singleton(key, win):
    """Registra la ventana bajo una clave para evitar duplicados."""
    opened_windows[key] = win


# --- Time zone config (JSON-backed) ---------------------------------
# Nombre del archivo de configuración de TZ
TZ_CONFIG_FILENAME = "tz_config.json"
# Directorio explícito solicitado para almacenar el archivo de TZ
TZ_CONFIG_DIR = Path(r"\\192.168.7.12\Data SIG\Central Station SLC-COLOMBIA\1. Daily Logs - Operators\DataBase\Base de Datos")

def Dinamic_button_Shift(username):
    """Determina el estado del botón de turno (Start/End) sin limitar por día.

    Regla:
    - Si el último evento de turno para el usuario es 'START SHIFT' => hay turno activo => mostrar 'End of Shift' => retorna False.
    - Si el último evento es 'END OF SHIFT' o no hay eventos => no hay turno activo => mostrar 'Start Shift' => retorna True.
    """
    try:
        conn = get_connection()
        cur = conn.cursor()

        # Buscar el último evento de turno en toda la historia (sin recortar por día)
        cur.execute(
            """
            SELECT e.Nombre_Actividad, e.FechaHora
            FROM Eventos e
            INNER JOIN user u ON e.ID_Usuario = u.ID_Usuario
            WHERE u.Nombre_Usuario = %s
              AND e.Nombre_Actividad IN ('START SHIFT', 'END OF SHIFT')
            ORDER BY e.FechaHora DESC
            LIMIT 1
            """,
            (username,),
        )

        row = cur.fetchone()
        cur.close()
        conn.close()

        # Si no hay eventos de turno, permitir iniciar
        if not row:
            print(f"[DEBUG] Dinamic_button_Shift({username}): No hay eventos de turno -> retorna True (Start Shift)")
            return True

        ultimo_evento = (row[0] or '').strip().upper()
        fecha_evento = row[1]
        print(f"[DEBUG] Dinamic_button_Shift({username}): Último evento = '{ultimo_evento}' en {fecha_evento}")
        
        if ultimo_evento == 'START SHIFT':
            # Último fue START => turno abierto => NO permitir nuevo start
            print(f"[DEBUG] Dinamic_button_Shift({username}): Turno activo -> retorna False (End of Shift)")
            return False
        # Último fue END OF SHIFT => permitir iniciar
        print(f"[DEBUG] Dinamic_button_Shift({username}): Sin turno activo -> retorna True (Start Shift)")
        return True

    except Exception as e:
        print(f"[ERROR] Dinamic_button_Shift: {e}")
        traceback.print_exc()
        # En caso de error, ser conservadores y no romper el flujo; permitir Start
        return True

def update_event_button(username):
    """Devuelve True si el botón debe mostrar 'Start Shift', False si debe mostrar 'End of Shift'.

    Simplificado para ser una consulta única (sin bucles), usando la misma lógica que Dinamic_button_Shift.
    """
    try:
        return Dinamic_button_Shift(username)
    except Exception as e:
        print(f"[ERROR] update_event_button: {e}")
        return True

def on_start_shift(username, parent_window=None):
    """Acción al presionar Start Shift con selector de fecha/hora
    
    Returns:
        bool: True si se registró el START SHIFT exitosamente, False si se canceló o hubo error
    """
    print(f"DEBUG: Start Shift presionado por {username}")
    
    # ⭐ VERIFICAR SI YA HAY UN TURNO ACTIVO ANTES DE ABRIR EL PICKER
    try:
        conn = get_connection()
        cur = conn.cursor()
        
        cur.execute("""
            SELECT e.Nombre_Actividad, e.FechaHora
            FROM Eventos e
            INNER JOIN user u ON e.ID_Usuario = u.ID_Usuario
            WHERE u.Nombre_Usuario = %s
              AND e.Nombre_Actividad IN ('START SHIFT', 'END OF SHIFT')
            ORDER BY e.FechaHora DESC
            LIMIT 1
        """, (username,))
        
        row = cur.fetchone()
        cur.close()
        conn.close()
        
        if row:
            ultimo_evento = (row[0] or '').strip().upper()
            if ultimo_evento == 'START SHIFT':
                messagebox.showwarning("Turno activo", 
                                      f"Ya tienes un turno activo desde {row[1]}.\n\nDebes finalizar el turno antes de iniciar uno nuevo.",
                                      parent=parent_window)
                print(f"[DEBUG] Intento de iniciar turno cuando ya hay uno activo desde {row[1]}")
                return False
    except Exception as e:
        print(f"[ERROR] Verificación de turno activo: {e}")
        traceback.print_exc()
    
    # Variable para rastrear si se completó
    shift_registered = [False]  # Usar lista para poder modificar en closure
    
    # Importar módulos necesarios
    try:
        import tkcalendar
    except ImportError:
        messagebox.showerror("Error", "tkcalendar no está instalado.\nInstala con: pip install tkcalendar")
        return False
    
    try:
        import customtkinter as ctk
        UI = ctk
    except:
        UI = None
    
    # Crear ventana de selección de fecha/hora
    if UI is not None:
        picker_win = UI.CTkToplevel(parent_window)
        picker_win.title("Seleccionar Fecha y Hora - Start Shift")
        picker_win.geometry("500x450")
        picker_win.resizable(False, False)
        picker_win.configure(fg_color="#1e1e1e")
        if parent_window:
            picker_win.transient(parent_window)
        picker_win.grab_set()
        
        # Header
        header = UI.CTkFrame(picker_win, fg_color="#1a1a1a", corner_radius=0, height=60)
        header.pack(fill="x", padx=0, pady=0)
        header.pack_propagate(False)
        
        UI.CTkLabel(header, text="🚀 Start Shift", 
                   font=("Segoe UI", 20, "bold"),
                   text_color="#00c853").pack(pady=15)
        
        # Contenido principal
        content = UI.CTkFrame(picker_win, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Sección de Fecha
        date_section = UI.CTkFrame(content, fg_color="#2b2b2b", corner_radius=10)
        date_section.pack(fill="x", pady=(0, 15))
        
        UI.CTkLabel(date_section, text="📅 Fecha:", 
                   font=("Segoe UI", 14, "bold"),
                   text_color="#e0e0e0").pack(anchor="w", padx=15, pady=(15, 10))
        
        # Frame para calendario
        cal_wrapper = tk.Frame(date_section, bg="#2b2b2b")
        cal_wrapper.pack(padx=15, pady=(0, 15))
        
        now = datetime.now()
        cal = tkcalendar.DateEntry(cal_wrapper, width=30, background='#00c853',
                                   foreground='white', borderwidth=2,
                                   year=now.year, month=now.month, day=now.day,
                                   date_pattern='yyyy-mm-dd',
                                   font=("Segoe UI", 11))
        cal.pack()
        
        # Sección de Hora
        time_section = UI.CTkFrame(content, fg_color="#2b2b2b", corner_radius=10)
        time_section.pack(fill="x", pady=(0, 15))
        
        UI.CTkLabel(time_section, text="🕐 Hora:", 
                   font=("Segoe UI", 14, "bold"),
                   text_color="#e0e0e0").pack(anchor="w", padx=15, pady=(15, 10))
        
        # Variables para hora
        hour_var = tk.IntVar(value=now.hour)
        minute_var = tk.IntVar(value=now.minute)
        second_var = tk.IntVar(value=now.second)
        
        # Frame para spinboxes
        spinbox_container = tk.Frame(time_section, bg="#2b2b2b")
        spinbox_container.pack(padx=15, pady=(0, 10))
        
        # Hora
        tk.Label(spinbox_container, text="Hora:", bg="#2b2b2b", fg="#a3c9f9",
                font=("Segoe UI", 11)).grid(row=0, column=0, padx=5, pady=5)
        hour_spin = tk.Spinbox(spinbox_container, from_=0, to=23, textvariable=hour_var,
                              width=8, font=("Segoe UI", 12), justify="center")
        hour_spin.grid(row=0, column=1, padx=5, pady=5)
        
        # Minuto
        tk.Label(spinbox_container, text="Min:", bg="#2b2b2b", fg="#a3c9f9",
                font=("Segoe UI", 11)).grid(row=0, column=2, padx=5, pady=5)
        minute_spin = tk.Spinbox(spinbox_container, from_=0, to=59, textvariable=minute_var,
                                width=8, font=("Segoe UI", 12), justify="center")
        minute_spin.grid(row=0, column=3, padx=5, pady=5)
        
        # Segundo
        tk.Label(spinbox_container, text="Seg:", bg="#2b2b2b", fg="#a3c9f9",
                font=("Segoe UI", 11)).grid(row=0, column=4, padx=5, pady=5)
        second_spin = tk.Spinbox(spinbox_container, from_=0, to=59, textvariable=second_var,
                                width=8, font=("Segoe UI", 12), justify="center")
        second_spin.grid(row=0, column=5, padx=5, pady=5)
        
        # Botón "Ahora"
        def set_now():
            ahora = datetime.now()
            cal.set_date(ahora.date())
            hour_var.set(ahora.hour)
            minute_var.set(ahora.minute)
            second_var.set(ahora.second)
        
        UI.CTkButton(time_section, text="⏰ Establecer Hora Actual", command=set_now,
                    fg_color="#4a90e2", hover_color="#3a7bc2",
                    font=("Segoe UI", 11),
                    width=200, height=35).pack(pady=(5, 15))
        
        # Botones Aceptar/Cancelar
        btn_frame = UI.CTkFrame(content, fg_color="transparent")
        btn_frame.pack(pady=10)
        
        def accept_ctk():
            try:
                fecha = cal.get_date()
                hora = hour_var.get()
                minuto = minute_var.get()
                segundo = second_var.get()
                
                # Construir datetime
                fecha_hora = datetime.combine(fecha, datetime.min.time()).replace(
                    hour=hora, minute=minuto, second=segundo
                )
                
                # Insertar en BD
                conn = get_connection()
                cur = conn.cursor()
                
                # Obtener ID_Usuario
                cur.execute("SELECT ID_Usuario FROM user WHERE Nombre_Usuario = %s", (username,))
                row = cur.fetchone()
                if not row:
                    messagebox.showerror("Error", f"Usuario {username} no encontrado", parent=picker_win)
                    cur.close()
                    conn.close()
                    return
                
                ID_Usuario = row[0]
                
                # Insertar START SHIFT con fecha/hora seleccionada
                cur.execute("""
                    INSERT INTO Eventos (FechaHora, ID_Sitio, Nombre_Actividad, Cantidad, Camera, Descripcion, ID_Usuario)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (fecha_hora, 291, 'START SHIFT', 0, '', 'Do Not Edit - No Editar', ID_Usuario))
                
                conn.commit()
                cur.close()
                conn.close()
                
                print(f"[DEBUG] START SHIFT registrado: {fecha_hora} para {username}")
                shift_registered[0] = True
                picker_win.destroy()
                
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo registrar START SHIFT:\n{e}", parent=picker_win)
                print(f"[ERROR] on_start_shift accept_ctk: {e}")
                traceback.print_exc()
        
        UI.CTkButton(btn_frame, text="✅ Aceptar", command=accept_ctk,
                    fg_color="#00c853", hover_color="#00a043",
                    font=("Segoe UI", 12, "bold"),
                    width=120, height=40).pack(side="left", padx=10)
        
        UI.CTkButton(btn_frame, text="❌ Cancelar", command=picker_win.destroy,
                    fg_color="#666666", hover_color="#555555",
                    font=("Segoe UI", 12),
                    width=120, height=40).pack(side="left", padx=10)
        
    else:
        # Fallback sin CustomTkinter
        picker_win = tk.Toplevel(parent_window)
        picker_win.title("Seleccionar Fecha y Hora - Start Shift")
        picker_win.geometry("400x400")
        picker_win.configure(bg="#2b2b2b")
        if parent_window:
            picker_win.transient(parent_window)
        picker_win.grab_set()
        
        content = tk.Frame(picker_win, bg="#2b2b2b")
        content.pack(fill="both", expand=True, padx=20, pady=20)
        
        tk.Label(content, text="Fecha:", bg="#2b2b2b", fg="#ffffff",
                font=("Segoe UI", 12, "bold")).pack(anchor="w", pady=(10,5))
        
        now = datetime.now()
        cal = tkcalendar.DateEntry(content, width=25, background='#00c853',
                                  foreground='white', borderwidth=2,
                                  year=now.year, month=now.month, day=now.day)
        cal.pack(pady=5, fill="x")
        
        tk.Label(content, text="Hora:", bg="#2b2b2b", fg="#ffffff",
                font=("Segoe UI", 12, "bold")).pack(anchor="w", pady=(20,5))
        
        time_frame = tk.Frame(content, bg="#2b2b2b")
        time_frame.pack(fill="x", pady=5)
        
        hour_var = tk.IntVar(value=now.hour)
        minute_var = tk.IntVar(value=now.minute)
        second_var = tk.IntVar(value=now.second)
        
        hour_spin = tk.Spinbox(time_frame, from_=0, to=23, textvariable=hour_var, width=8)
        hour_spin.pack(side="left", padx=5)
        minute_spin = tk.Spinbox(time_frame, from_=0, to=59, textvariable=minute_var, width=8)
        minute_spin.pack(side="left", padx=5)
        second_spin = tk.Spinbox(time_frame, from_=0, to=59, textvariable=second_var, width=8)
        second_spin.pack(side="left", padx=5)
        
        def accept_tk():
            try:
                fecha = cal.get_date()
                hora = hour_var.get()
                minuto = minute_var.get()
                segundo = second_var.get()
                
                fecha_hora = datetime.combine(fecha, datetime.min.time()).replace(
                    hour=hora, minute=minuto, second=segundo
                )
                
                conn = get_connection()
                cur = conn.cursor()
                
                cur.execute("SELECT ID_Usuario FROM user WHERE Nombre_Usuario = %s", (username,))
                row = cur.fetchone()
                if not row:
                    messagebox.showerror("Error", f"Usuario {username} no encontrado", parent=picker_win)
                    cur.close()
                    conn.close()
                    return
                
                ID_Usuario = row[0]
                
                cur.execute("""
                    INSERT INTO Eventos (FechaHora, ID_Sitio, Nombre_Actividad, Cantidad, Camera, Descripcion, ID_Usuario)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (fecha_hora, 291, 'START SHIFT', 0, '', 'Do Not Edit - No Editar', ID_Usuario))
                
                conn.commit()
                cur.close()
                conn.close()
                
                print(f"[DEBUG] START SHIFT registrado: {fecha_hora} para {username}")
                shift_registered[0] = True
                picker_win.destroy()
                
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo registrar START SHIFT:\n{e}", parent=picker_win)
                print(f"[ERROR] on_start_shift accept_tk: {e}")
                traceback.print_exc()
        
        btn_frame = tk.Frame(content, bg="#2b2b2b")
        btn_frame.pack(side="bottom", pady=20)
        tk.Button(btn_frame, text="Aceptar", command=accept_tk, bg="#00c853", fg="white", width=10).pack(side="left", padx=5)
        tk.Button(btn_frame, text="Cancelar", command=picker_win.destroy, bg="#666666", fg="white", width=10).pack(side="left", padx=5)


    
    # Esperar a que la ventana se cierre (wait_window hace esto)
    try:
        if UI is not None:
            picker_win.wait_window()
        else:
            picker_win.wait_window()
    except:
        pass
    
    return shift_registered[0]

def on_end_shift(username):
    """Acción al presionar End of Shift"""
    print(f"DEBUG: End of Shift presionado por {username}")
    # Aquí irá la lógica real de fin de turno
    try:
        conn = get_connection()
        cur = conn.cursor()
        
        # Obtener el ID_Usuario a partir del username
        cur.execute("""
            SELECT ID_Usuario 
            FROM user 
            WHERE Nombre_Usuario = %s
        """, (username,))
        
        row = cur.fetchone()
        if not row:
            print(f"[ERROR] Usuario {username} no encontrado en la base de datos")
            cur.close()
            conn.close()
            return
        
        ID_Usuario = row[0]
        
        # Insertar el evento END OF SHIFT
        cur.execute("""
            INSERT INTO Eventos (FechaHora, ID_Sitio, Nombre_Actividad, Cantidad, Camera, Descripcion, ID_Usuario)
            VALUES (NOW(), %s, %s, %s, %s, %s, %s)
            """, (291, 'END OF SHIFT', 0, '', 'Do Not Edit - No Editar', ID_Usuario))
        
        conn.commit()
        cur.close()
        conn.close()
        
        print(f"[DEBUG] End of Shift registrado correctamente para {username}")
        
    except Exception as e:
        print(f"[ERROR] on_end_shift: {e}")



def _get_tz_config_path():
    """Devuelve la ruta completa del archivo tz_config.json.

    Prioridad:
    1) Directorio UNC fijo solicitado (TZ_CONFIG_DIR)
    2) Directorio definido por under_super.CONFIG_PATH (si fuera necesario en el futuro)
    3) Carpeta del módulo actual (fallback)
    """
    # 1) Directorio UNC solicitado
    try:
        if TZ_CONFIG_DIR:
            return TZ_CONFIG_DIR / TZ_CONFIG_FILENAME
    except Exception:
        pass

    # 2) Intentar usar el directorio de CONFIG_PATH si existiera (fallback)
    try:
        cfg = getattr(under_super, 'CONFIG_PATH', None)
        if cfg:
            p = Path(cfg)
            base = p.parent if p.suffix else p
            return base / TZ_CONFIG_FILENAME
    except Exception:
        pass

    # 3) Fallback: carpeta del módulo
    try:
        base = Path(__file__).parent
    except Exception:
        base = Path('.')
    return base / TZ_CONFIG_FILENAME

def load_tz_config():
    """Load timezone adjustment mapping from JSON file.

    Returns a dict mapping timezone code -> integer offset hours.
    If the file doesn't exist, returns a sensible default.
    """
    path = _get_tz_config_path()
    if not path.exists():
        # sensible defaults
        return {"ET": 1, "CT": 0, "MT": -1, "MST": -2, "PT": -2}
    try:
        with path.open('r', encoding='utf-8') as f:
            data = json.load(f)
            # ensure ints
            return {k: int(v) for k, v in (data or {}).items()}
    except Exception:
        # On error, fallback to defaults
        return {"ET": 1, "CT": 0, "MT": -1, "MST": -2, "PT": -2}

def save_tz_config(tz_map):
    """Save tz_map (dict) to the JSON config file."""
    path = _get_tz_config_path()
    try:
        # Asegurar que exista el directorio
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass
        with path.open('w', encoding='utf-8') as f:
            json.dump(tz_map, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"[ERROR] saving tz config: {e}")
        return False

def open_tz_editor(username, station, role, session_id, parent=None):
    """Small editor window to view/edit timezone offsets stored in JSON."""
    ex = _focus_singleton('tz')
    if ex:
        return ex
    win = tk.Toplevel(parent or tk._default_root)
    win.title("Editar Configuración de Time Zones")
    win.geometry("420x360")
    win.configure(bg="#23272b")

    tz_map = load_tz_config()

    frame = tk.Frame(win, bg="#23272b")
    frame.pack(fill="both", expand=True, padx=8, pady=8)

    cols = ("Zone", "Offset")
    tv = ttk.Treeview(frame, columns=cols, show='headings', height=10)
    for c in cols:
        tv.heading(c, text=c)
        tv.column(c, width=180, anchor='w')
    tv.pack(side='top', fill='both', expand=True)

    # populate
    for k, v in sorted(tz_map.items()):
        tv.insert('', 'end', iid=k, values=(k, str(v)))

    entry_frame = tk.Frame(frame, bg=frame['bg'])
    entry_frame.pack(fill='x', pady=(8,0))
    tk.Label(entry_frame, text="Zona:", bg=frame['bg'], fg="#e0e0e0").pack(side='left')
    zone_var = tk.StringVar()
    off_var = tk.StringVar()
    zentry = tk.Entry(entry_frame, textvariable=zone_var, width=12)
    zentry.pack(side='left', padx=(6,8))
    tk.Label(entry_frame, text="Offset:", bg=frame['bg'], fg="#e0e0e0").pack(side='left')
    oentry = tk.Entry(entry_frame, textvariable=off_var, width=6)
    oentry.pack(side='left', padx=(6,8))

    def on_add_or_update():
        z = zone_var.get().strip().upper()
        if not z:
            messagebox.showwarning("Atención", "Zona vacía", parent=win)
            return
        try:
            off = int(off_var.get().strip())
        except Exception:
            messagebox.showwarning("Atención", "Offset debe ser un número entero", parent=win)
            return
        tz_map[z] = off
        if tv.exists(z):
            tv.item(z, values=(z, str(off)))
        else:
            tv.insert('', 'end', iid=z, values=(z, str(off)))
        zone_var.set('')
        off_var.set('')

    def on_delete():
        sel = tv.selection()
        if not sel:
            return
        for iid in sel:
            try:
                del tz_map[iid]
            except Exception:
                pass
            try:
                tv.delete(iid)
            except Exception:
                pass

    def on_save():
        ok = save_tz_config(tz_map)
        if ok:
            messagebox.showinfo("Guardado", "Configuración de zonas horarias guardada.", parent=win)
            win.destroy()
        else:
            messagebox.showerror("Error", "No se pudo guardar el archivo JSON.", parent=win)

    btn_frame = tk.Frame(frame, bg=frame['bg'])
    btn_frame.pack(fill='x', pady=(8,0))
    tk.Button(btn_frame, text="Agregar/Actualizar", command=on_add_or_update, bg="#13988e", fg="#fff").pack(side='left', padx=6)
    tk.Button(btn_frame, text="Eliminar", command=on_delete, bg="#f59b9b", fg="#111").pack(side='left', padx=6)
    tk.Button(btn_frame, text="Guardar", command=on_save, bg="#3e8e7e", fg="#fff").pack(side='right', padx=6)
    tk.Button(btn_frame, text="Cerrar", command=win.destroy, bg="#a3a3a3", fg="#111").pack(side='right', padx=6)

    win.transient(parent)
    win.grab_set()
    win.focus_force()
    _register_singleton('tz', win)

def show_info():
    # Mostrar un pequeño manual de usuario en una ventana modal
    try:
        # Ventana única por función
        ex = _focus_singleton('info')
        if ex:
            return ex
        win = tk.Toplevel()
        win.title("Manual rápido de la aplicación")
        win.configure(bg="#23272b")
        win.resizable(False, False)
        win.geometry("560x420")

        # Encabezado
        tk.Label(win, text="Manual rápido - Uso de la aplicación", bg="#23272b", fg="#a3c9f9",
                 font=("Segoe UI", 12, "bold")).pack(pady=(12, 6))

        # Frame para texto + scrollbar
        frame = tk.Frame(win, bg="#23272b")
        frame.pack(expand=True, fill="both", padx=10, pady=(0,8))

        scrollbar = tk.Scrollbar(frame)
        scrollbar.pack(side="right", fill="y")

        txt = tk.Text(frame, wrap="word", yscrollcommand=scrollbar.set,
                      bg="#2c2f33", fg="#e0e0e0", insertbackground="#e0e0e0",
                      font=("Segoe UI", 10), padx=8, pady=6, borderwidth=0)
        scrollbar.config(command=txt.yview)
        txt.pack(side="left", fill="both", expand=True)

        manual = (
            "Bienvenido — Manual rápido\n\n"
            "1) Login:\n"
            "   - Introduce tu usuario, contraseña y número de estación.\n"
            "   - Si crees que la estación está ocupada, verifica el mensaje de error.\n\n"
            "2) Panel Principal:\n"
            "   - Botones disponibles dependen de tu rol (operador / supervisor / admin).\n"
            "   - Exportar Excel: exporta eventos al folder configurado.\n\n"
            "3) Registrar Evento:\n"
            "   - Rellena Sitio, Actividad, Cantidad, Cámara y Descripción.\n"
            "   - Puedes ajustar la hora editable antes de guardar.\n\n"
            "4) Mostrar Eventos (Event):\n"
            "   - Lista eventos del usuario en el turno.\n"
            "   - Selecciona un registro y pulsa Editar para modificarlo o Eliminar para borrarlo.\n\n"
            "5) Report / Specials:\n"
            "   - Report muestra eventos filtrados por grupos especiales.\n"
            "   - Desde el reporte puedes seleccionar filas y asignarles un supervisor (se insertan en 'specials').\n\n"
            "6) Cover Mode:\n"
            "   - Usa Cover para indicar una ausencia temporal (Break, Cover Daily, etc.).\n\n"
            "7) Administración / View:\n"
            "   - Admin permite editar Sitios/Actividades/Usuarios si tu rol lo permite.\n"
            "   - View ofrece tablas para inspeccionar y borrar registros.\n\n"
            "Consejos rápidos:\n"
            " - Si la UI cambia de aspecto al abrir una ventana, cierra y abre la app; las ventanas usan estilos locales.\n"
            " - Si añades manualmente un timestamp al campo Descripción desde el editor, el reporte aplicará el ajuste de zona horaria.\n"
            " - Para soporte, comparte los mensajes de consola (líneas que empiezan por [DEBUG]).\n\n"
            "Atajos:\n"
            " - Refrescar listas: usa el botón 'Refrescar' en cada ventana.\n"
            " - Copiar datos: selecciona texto en la vista y copialo (o usa el botón Copiar abajo).\n\n"
            "Gracias por usar la app..\n\n"
            "by Hector Cruz and Yonier Angulo (sus amigos y vecinos IT specialists)"
        )

        txt.insert("1.0", manual)
        txt.config(state="disabled")

        # Botones inferior: Copiar y Cerrar
        btn_frame = tk.Frame(win, bg="#23272b")
        btn_frame.pack(fill="x", pady=(0,10))

        def copy_to_clipboard():
            try:
                win.clipboard_clear()
                win.clipboard_append(manual)
                messagebox.showinfo("Copiado", "Manual copiado al portapapeles.", parent=win)
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo copiar:\n{e}", parent=win)

        tk.Button(btn_frame, text="Copiar manual", command=copy_to_clipboard, bg="#13988e", fg="#fff", relief="flat").pack(side="left", padx=12)
        tk.Button(btn_frame, text="Cerrar", command=win.destroy, bg="#a3a3a3", fg="#111", relief="flat").pack(side="right", padx=12)

        # Hacer la ventana modal-like
        win.transient()
        win.grab_set()
        win.focus_force()

        _register_singleton('info', win)
    except Exception as e:
        print(f"[ERROR] show_info: {e}")

#implementacion de Covers, en rol de supervisor completado


# nueva implementacion: status de supervisores
# fin de la implementaicon de statuses 
# modificable y con efecto en operadores


def get_user_status(username):
    try:
        
        status_value = get_user_status_bd(username)
        results = status_value    
        if results:
            
            # Mapear el valor del status
            if status_value == 1:
                status_text = "🟢 Disponible"
            elif status_value == 2:
                status_text = "🟡 Ocupado"
            elif status_value == -1:
                status_text = "🔴 No disponible"
            else:
                status_text = f"⚪ Estado desconocido ({status_value})"
            
            print(f"[DEBUG] Usuario: {username}, Status DB: {status_value}, Texto: {status_text}")
            return status_text
        else:
            print(f"[WARN] Usuario '{username}' no encontrado")
            return "❌ Usuario no encontrado"
            
    except pymysql.Error as e:
        print(f"[ERROR] Error al consultar el estado: {e}")
        return f"Error: {e}"

# Botón para refrescar
def refresh_status(label_status, username):
    new_status = get_user_status(username)
    label_status.config(text=f"Status: {new_status}")
    return new_status


# fin de la implementacion

# implementacion de modelo de gestion de breaks por supervisores.

#def menu_de_covers_break_ctk(username):
    try:
        import customtkinter as ctk
    except ImportError:
        messagebox.showerror("Error", "customtkinter no está instalado.\nInstala con: pip install customtkinter")
        return
    
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")
   
    root = ctk.CTk()
    root.geometry("1100x600")
    root.title("Menú de Covers de Break")

    # Frame principal
    main_frame = ctk.CTkFrame(root, fg_color="#1e1e1e")
    main_frame.pack(fill="both", expand=True, padx=20, pady=20)
    
    # Título
    title_label = ctk.CTkLabel(main_frame, text="📋 Covers de Break", 
                               font=ctk.CTkFont(size=24, weight="bold"),
                               text_color="#4aa3ff")
    title_label.pack(pady=(10, 20))

    # Frame para controles (comboboxes y botones)
    controls_frame = ctk.CTkFrame(main_frame, fg_color="#2b2b2b")
    controls_frame.pack(fill="x", padx=10, pady=(0, 10))
    
    # Obtener lista de usuarios desde la base de datos
    user_list = under_super.get_all_users()
    users_list = [user['Nombre_Usuario'] for user in user_list] if user_list else []
    
    
    # Datos locales de covers (lista que se irá actualizando)
    # Solo un usuario por celda (hora + covered_by)
    local_covers_data = []
    
    # Variables para comboboxes
    usuario_a_cubrir_var = tk.StringVar()
    cubierto_por_var = tk.StringVar()
    hora_var = tk.StringVar()
    
    # Primera fila: Usuario a cubrir
    row1_frame = ctk.CTkFrame(controls_frame, fg_color="transparent")
    row1_frame.pack(fill="x", padx=20, pady=(15, 5))
    
    ctk.CTkLabel(row1_frame, text="👤 Usuario a Cubrir:", 
                font=ctk.CTkFont(size=14, weight="bold"),
                text_color="#ffffff").pack(side="left", padx=(0, 10))
    
    usuario_combo = ctk.CTkComboBox(row1_frame, 
                                    variable=usuario_a_cubrir_var,
                                    values=users_list,
                                    width=200,
                                    font=ctk.CTkFont(size=13),
                                    state="readonly")
    usuario_combo.pack(side="left", padx=5)
    usuario_combo.set("Seleccionar...")
    
    # Segunda fila: Cubierto por
    row2_frame = ctk.CTkFrame(controls_frame, fg_color="transparent")
    row2_frame.pack(fill="x", padx=20, pady=5)
    
    ctk.CTkLabel(row2_frame, text="🔄 Cubierto Por:", 
                font=ctk.CTkFont(size=14, weight="bold"),
                text_color="#ffffff").pack(side="left", padx=(0, 10))
    
    cover_by_combo = ctk.CTkComboBox(row2_frame, 
                                     variable=cubierto_por_var,
                                     values=users_list,
                                     width=200,
                                     font=ctk.CTkFont(size=13),
                                     state="readonly")
    cover_by_combo.pack(side="left", padx=5)
    cover_by_combo.set("Seleccionar...")
    
    # Tercera fila: Hora
    row3_frame = ctk.CTkFrame(controls_frame, fg_color="transparent")
    row3_frame.pack(fill="x", padx=20, pady=5)
    
    ctk.CTkLabel(row3_frame, text="🕐 Hora Programada:", 
                font=ctk.CTkFont(size=14, weight="bold"),
                text_color="#ffffff").pack(side="left", padx=(0, 10))
    
    # Generar lista de horas en formato HH:00:00 (cada hora del día)
    horas_disponibles = [f"{h:02d}:00:00" for h in range(24)]

    hora_combo = under_super.Fil(row3_frame,
                                  variable=hora_var,
                                  values=horas_disponibles,
                                  width=200,
                                  font=ctk.CTkFont(size=13),
                                  state="readonly")
    hora_combo.pack(side="left", padx=5)
    hora_combo.set("14:00:00")  # Valor por defecto
    
    # Cuarta fila: Botones
    row4_frame = ctk.CTkFrame(controls_frame, fg_color="transparent")
    row4_frame.pack(fill="x", padx=20, pady=(5, 15))
    
    def cargar_datos_agrupados():
        """Carga datos agrupados por quien cubre (covered_by como columnas)"""
        try:
            # Usar los datos locales
            rows = [(usuario, covered_by, hora) for usuario, covered_by, hora in local_covers_data]
            
            # Obtener lista única de "Cubierto Por" para las columnas
            covered_by_set = sorted(set(row[1] for row in rows if row[1]))
            
            # Headers: hora primero + columnas de personas que cubren
            headers = ["Hora Programada"]
            for cb in covered_by_set:
                headers.append(cb)
            
            # Agrupar por hora - solo el PRIMER usuario por covered_by y hora
            horas_dict = {}
            for row in rows:
                usuario = row[0]
                covered_by = row[1]
                hora = row[2]  # Ya es string en formato HH:MM:SS
                
                if hora not in horas_dict:
                    horas_dict[hora] = {cb: "" for cb in covered_by_set}
                
                # Solo asignar si la celda está vacía (un usuario por celda)
                if covered_by in horas_dict[hora] and not horas_dict[hora][covered_by]:
                    horas_dict[hora][covered_by] = usuario
            
            # Convertir a lista de filas para el sheet
            data = []
            for hora in sorted(horas_dict.keys()):
                fila = [hora]
                for covered_by in covered_by_set:
                    fila.append(horas_dict[hora][covered_by])
                data.append(fila)
            
            return headers, data
            
        except Exception as e:
            print(f"[ERROR] cargar_datos_agrupados: {e}")
            import traceback
            traceback.print_exc()
            return ["Hora Programada"], []
    
    #def agregar_cover():
        usuario = usuario_a_cubrir_var.get()
        cover = cubierto_por_var.get()
        hora = hora_var.get()
        
        if usuario == "Seleccionar..." or cover == "Seleccionar..." or not hora:
            print("[WARN] Debe completar todos los campos")
            return
        
        # Validar formato de hora (HH:MM:SS)
        if not re.match(r'^([0-1][0-9]|2[0-3]):[0-5][0-9]:[0-5][0-9]$', hora):
            print("[WARN] Formato de hora inválido. Use HH:MM:SS (ej: 14:00:00)")
            return
        
        # Validar que no exista ya un cover asignado para esa hora y covered_by
        for u, c, h in local_covers_data:
            if h == hora and c == cover:
                print(f"[WARN] ⚠️ Ya existe un cover asignado a {cover} a las {hora}. Solo se permite un usuario por celda.")
                return
        
        # Agregar a la lista local
        local_covers_data.append((usuario, cover, hora))
        print(f"[INFO] ✅ Cover agregado: {usuario} cubierto por {cover} a las {hora}")
        
        # Limpiar formulario y refrescar tabla
        limpiar()
        refrescar_tabla()
    
    def limpiar():
        usuario_combo.set("Seleccionar...")
        cover_by_combo.set("Seleccionar...")
        hora_var.set("")
    
    btn_agregar = ctk.CTkButton(row4_frame, text="➕ Agregar",
                                command=lambda: under_super.select_covered_by(username, 
                                                                              hora=hora_var.get(), 
                                                                              cover=cubierto_por_var.get(), 
                                                                              usuario=usuario_a_cubrir_var.get()
                                                                              ),
                                fg_color="#28a745", hover_color="#218838",
                                font=ctk.CTkFont(size=13, weight="bold"),
                                width=150)
    btn_agregar.pack(side="left", padx=5)
    
    btn_limpiar = ctk.CTkButton(row4_frame, text="🔄 Limpiar",
                                command=limpiar,
                                fg_color="#6c757d", hover_color="#5a6268",
                                font=ctk.CTkFont(size=13),
                                width=120)
    btn_limpiar.pack(side="left", padx=5)

    # Frame para tksheet
    tksheet_frame = ctk.CTkFrame(main_frame, fg_color="#2c2f33")
    tksheet_frame.pack(fill="both", expand=True, padx=10, pady=10)
    
    if USE_SHEET:
        # Use Sheet functionality
        headers, data = cargar_datos_agrupados()
        
        sheet = Sheet(tksheet_frame,
                      headers=headers,
                      theme="dark blue",
                      width=1050,
                      height=350)
        sheet.enable_bindings([
            "single_select",
            "drag_select",
            "row_select",
            "column_select",
            "column_width_resize",
            "double_click_column_resize",
            "arrowkeys",
            "copy",
            "select_all"
        ])
        sheet.pack(fill="both", expand=True)
        
        sheet.set_sheet_data(data)
        sheet.change_theme("dark blue")
        
        # Ajustar anchos de columnas
        for i in range(len(headers)):
            sheet.column_width(column=i, width=200)
        
        def eliminar_cover():
            selected_cols = sheet.get_selected_columns()
            selected_cells = sheet.get_selected_cells()
            
            # Caso 1: Se seleccionó una columna completa
            if selected_cols:
                col = list(selected_cols)[0]  # Convertir set a lista
                if col == 0:
                    print("[WARN] No se puede eliminar la columna de Hora.")
                    return
                
                covered_by = sheet.headers()[col]
                
                # Eliminar todos los covers de esa persona
                covers_eliminados = []
                for entrada in local_covers_data[:]:  # Iterar sobre una copia
                    usuario, c_by, h = entrada
                    if c_by == covered_by:
                        covers_eliminados.append(entrada)
                        local_covers_data.remove(entrada)
                        print(f"[INFO] ✅ Cover eliminado: {usuario} cubierto por {c_by} a las {h}")
                
                if covers_eliminados:
                    print(f"[INFO] Total de covers eliminados: {len(covers_eliminados)}")
                    refrescar_tabla()
                else:
                    print("[WARN] No se encontraron covers para eliminar en esa columna.")
                return
            
            # Caso 2: Se seleccionó una celda específica
            if selected_cells:
                row, col = selected_cells[0]
                
                if col == 0:
                    print("[WARN] No se puede eliminar desde la columna de Hora.")
                    return
                
                hora = sheet.get_cell_data(row, 0)  # Hora en la primera columna
                covered_by = sheet.headers()[col]    # Nombre del covered_by
                
                # Buscar y eliminar de la lista local
                for entrada in local_covers_data[:]:
                    usuario, c_by, h = entrada
                    if h == hora and c_by == covered_by:
                        local_covers_data.remove(entrada)
                        print(f"[INFO] ✅ Cover eliminado: {usuario} cubierto por {c_by} a las {h}")
                        refrescar_tabla()
                        return
                
                print("[WARN] No se encontró el cover para eliminar.")
                return
            
            print("[WARN] Seleccione una celda o columna para eliminar el cover.")
        
        btn_eliminar = ctk.CTkButton(controls_frame, text="🗑️ Eliminar Cover Seleccionado",
                                     command=eliminar_cover,
                                     fg_color="#dc3545", hover_color="#c82333",
                                     font=ctk.CTkFont(size=13),
                                     width=220)
        btn_eliminar.pack(side="left", padx=5)
        
        def refrescar_tabla():
            headers, data = cargar_datos_agrupados()
            sheet.headers(headers)
            sheet.set_sheet_data(data)
            # Reajustar anchos después de refrescar
            for i in range(len(headers)):
                sheet.column_width(column=i, width=200)
            sheet.redraw()
        
    else:
        no_sheet_label = ctk.CTkLabel(tksheet_frame, 
                                      text="⚠️ tksheet no instalado", 
                                      font=ctk.CTkFont(size=16),
                                      text_color="#ff6b6b")
        no_sheet_label.pack(pady=20)

# fin de la implemetacion de gestion de breaks


def show_covers_programados_panel(parent_top, parent_ui, username):
    """
    📋 PANEL INTEGRADO DE LISTA DE COVERS PROGRAMADOS
    
    Muestra todos los covers programados activos de TODOS los usuarios con:
    - Visualización en tksheet (solo lectura) integrada en la ventana principal
    - Información detallada: Usuario, Hora solicitud, Estación, Razón, Estado aprobación
    - Botón de refrescar y cerrar
    - Filtrado automático: solo muestra covers con is_Active = 1
    - Resalta la fila del usuario actual en verde
    
    Args:
        parent_top: Ventana principal (top) donde se creará el panel
        parent_ui: Módulo UI (CustomTkinter o None para tkinter)
        username: Usuario actual para resaltar su fila
    """
    # tksheet setup
    SheetClass = None
    try:
        from tksheet import Sheet as _Sheet
        SheetClass = _Sheet
    except Exception:
        messagebox.showerror("Error", "tksheet no está instalado.\nInstala con: pip install tksheet", parent=parent_top)
        return
    
    # Crear frame principal como overlay
    if parent_ui is not None:
        panel_frame = parent_ui.CTkFrame(parent_top, fg_color="#1e1e1e", corner_radius=0)
    else:
        panel_frame = tk.Frame(parent_top, bg="#1e1e1e")
    panel_frame.place(x=0, y=0, relwidth=1, relheight=1)
    
    # Header
    if parent_ui is not None:
        header = parent_ui.CTkFrame(panel_frame, fg_color="#23272a", corner_radius=0, height=70)
    else:
        header = tk.Frame(panel_frame, bg="#23272a", height=70)
    header.pack(fill="x", padx=0, pady=0)
    header.pack_propagate(False)
    
    # Variable para rastrear modo actual (covers, daily, specials)
    current_view_mode = ['covers']  # Lista mutable para usar en closures
    
    # Título y botones
    if parent_ui is not None:
        title_label = parent_ui.CTkLabel(header, text="📋 Lista de Covers Programados", 
                   font=("Segoe UI", 20, "bold"),
                   text_color="#4a90e2")
        title_label.pack(side="left", padx=20, pady=20)
        
        parent_ui.CTkButton(header, text="❌ Cerrar", 
                    command=lambda: close_panel(),
                    fg_color="#d32f2f", hover_color="#b71c1c", 
                    width=100, height=40,
                    font=("Segoe UI", 12, "bold")).pack(side="right", padx=10, pady=15)
        
        refresh_btn = parent_ui.CTkButton(header, text="🔄 Refrescar", 
                    command=lambda: refresh_current_view(),
                    fg_color="#4D6068", hover_color="#27a3e0", 
                    width=120, height=40,
                    font=("Segoe UI", 12, "bold"))
        refresh_btn.pack(side="right", padx=10, pady=15)
        
        # Botón Ver Covers (para volver)
        covers_btn = parent_ui.CTkButton(header, text="📋 Ver Covers", 
                    command=lambda: switch_to_covers(),
                    fg_color="#00796b", hover_color="#009688", 
                    width=140, height=40,
                    font=("Segoe UI", 12, "bold"))
        covers_btn.pack(side="right", padx=5, pady=15)
        covers_btn.pack_forget()  # Inicialmente oculto
    else:
        title_label = tk.Label(header, text="📋 Lista de Covers Programados", bg="#23272a", fg="#4a90e2",
                font=("Segoe UI", 18, "bold"))
        title_label.pack(side="left", padx=20, pady=20)
        
        tk.Button(header, text="❌ Cerrar", command=lambda: close_panel(),
                 bg="#d32f2f", fg="white", font=("Segoe UI", 12, "bold"), 
                 relief="flat", width=10).pack(side="right", padx=10, pady=15)
        
        refresh_btn = tk.Button(header, text="🔄 Refrescar", command=lambda: refresh_current_view(),
                 bg="#666666", fg="white", font=("Segoe UI", 12, "bold"), 
                 relief="flat", width=12)
        refresh_btn.pack(side="right", padx=10, pady=15)
        
        # Botón Ver Specials
        specials_btn = tk.Button(header, text="⭐ Ver Specials", 
                    command=lambda: switch_to_specials(),
                    bg="#7b1fa2", fg="white", 
                    relief="flat", width=14,
                    font=("Segoe UI", 10, "bold"))
        specials_btn.pack(side="right", padx=5, pady=15)
        
        # Botón Ver Daily
        daily_btn = tk.Button(header, text="📝 Ver Daily", 
                    command=lambda: switch_to_daily(),
                    bg="#1976d2", fg="white", 
                    relief="flat", width=14,
                    font=("Segoe UI", 10, "bold"))
        daily_btn.pack(side="right", padx=5, pady=15)
        
        # Botón Ver Covers (para volver)
        covers_btn = tk.Button(header, text="📋 Ver Covers", 
                    command=lambda: switch_to_covers(),
                    bg="#00796b", fg="white", 
                    relief="flat", width=14,
                    font=("Segoe UI", 10, "bold"))
        covers_btn.pack(side="right", padx=5, pady=15)
        covers_btn.pack_forget()  # Inicialmente oculto
    
    # Separador
    try:
        ttk.Separator(panel_frame, orient="horizontal").pack(fill="x")
    except Exception:
        pass
    
    # Container principal
    if parent_ui is not None:
        container = parent_ui.CTkFrame(panel_frame, fg_color="#2c2f33")
    else:
        container = tk.Frame(panel_frame, bg="#2c2f33")
    container.pack(fill="both", expand=True, padx=10, pady=(0, 10))
    
    # Frame para tksheet
    if parent_ui is not None:
        sheet_frame = parent_ui.CTkFrame(container, fg_color="#2c2f33")
    else:
        sheet_frame = tk.Frame(container, bg="#2c2f33")
    sheet_frame.pack(fill="both", expand=True, padx=10, pady=10)
    
    # Columnas (agregamos # para mostrar posición)
    columns = ["#", "Usuario", "Hora Solicitud", "Estación", "Razón", "Aprobado"]
    
    # Crear tksheet
    sheet = SheetClass(
        sheet_frame,
        headers=columns,
        theme="dark blue",
        height=500,
        width=1050,
        show_selected_cells_border=True,
        show_row_index=False,
        show_top_left=False,
        empty_horizontal=0,
        empty_vertical=0
    )
    
    # Configurar bindings (solo lectura)
    sheet.enable_bindings([
        "single_select",
        "drag_select",
        "row_select",
        "column_select",
        "column_width_resize",
        "double_click_column_resize",
        "arrowkeys",
        "copy",
        "select_all"
    ])
    
    sheet.pack(fill="both", expand=True)
    sheet.change_theme("dark blue")
    
    # Anchos de columna personalizados
    sheet.column_width(column=0, width=50)   # #
    sheet.column_width(column=1, width=150)  # Usuario
    sheet.column_width(column=2, width=180)  # Hora Solicitud
    sheet.column_width(column=3, width=100)  # Estación
    sheet.column_width(column=4, width=350)  # Razón
    sheet.column_width(column=5, width=100)  # Aprobado
    
    def load_covers_data():
        """Carga TODOS los covers programados activos (is_Active = 1) de todos los usuarios"""
        try:
            conn = get_connection()
            cur = conn.cursor()
            
            # Obtener TODOS los covers programados activos (is_Active = 1)
            cur.execute("""
                SELECT ID_user, Time_request, Station, Reason, Approved
                FROM covers_programados
                WHERE is_Active = 1
                ORDER BY Time_request ASC
            """)
            
            rows = cur.fetchall()
            cur.close()
            conn.close()
            
            # Preparar datos para mostrar
            data = []
            user_row_index = None
            for idx, row in enumerate(rows, start=1):
                id_user = row[0] if row[0] else ""
                time_request = str(row[1]) if row[1] else ""
                station = str(row[2]) if row[2] else ""
                reason = row[3] if row[3] else ""
                approved = "✅ Sí" if row[4] == 1 else "❌ No"
                
                data.append([str(idx), id_user, time_request, station, reason, approved])
                
                # Guardar índice si es el usuario actual
                if id_user == username:
                    user_row_index = idx - 1  # 0-indexed para tksheet
            
            if not data:
                data = [["No hay covers programados activos"] + [""] * 5]
            
            sheet.set_sheet_data(data)
            
            # Resaltar fila del usuario actual en verde
            if user_row_index is not None:
                try:
                    sheet.highlight_rows([user_row_index], bg="#2e7d32", fg="white")
                except Exception as e:
                    print(f"[WARNING] Could not highlight user row: {e}")
            
            sheet.redraw()
            
            print(f"[DEBUG] Loaded {len(rows)} active covers (all users)")
            if user_row_index is not None:
                print(f"[DEBUG] Current user '{username}' is at position #{user_row_index + 1}")
            
        except Exception as e:
            messagebox.showerror("Error", f"Error cargando covers:\n{e}", parent=parent_top)
            print(f"[ERROR] load_covers_data: {e}")
            traceback.print_exc()
    
    def load_daily_events():
        """Carga eventos del turno actual del usuario (modo Daily)"""
        try:
            conn = get_connection()
            cur = conn.cursor()
            
            # Obtener eventos del día actual del usuario
            cur.execute("""
                SELECT e.FechaHora, s.Nombre_Sitio, e.Nombre_Actividad, 
                       e.Cantidad, e.Camera, e.Descripcion
                FROM Eventos e
                LEFT JOIN Sitios s ON e.ID_Sitio = s.ID_Sitio
                LEFT JOIN user u ON e.ID_Usuario = u.ID_Usuario
                WHERE u.Nombre_Usuario = %s 
                  AND DATE(e.FechaHora) = CURDATE()
                ORDER BY e.FechaHora DESC
            """, (username,))
            
            rows = cur.fetchall()
            cur.close()
            conn.close()
            
            # Preparar datos
            data = []
            for idx, row in enumerate(rows, start=1):
                fecha_hora = str(row[0]) if row[0] else ""
                sitio = row[1] if row[1] else ""
                actividad = row[2] if row[2] else ""
                cantidad = str(row[3]) if row[3] else ""
                camera = row[4] if row[4] else ""
                descripcion = row[5] if row[5] else ""
                
                data.append([str(idx), fecha_hora, sitio, actividad, cantidad, camera, descripcion])
            
            if not data:
                data = [["No hay eventos registrados hoy"] + [""] * 6]
            
            sheet.set_sheet_data(data)
            sheet.redraw()
            
            print(f"[DEBUG] Loaded {len(rows)} daily events for {username}")
            
        except Exception as e:
            messagebox.showerror("Error", f"Error cargando eventos daily:\n{e}", parent=parent_top)
            print(f"[ERROR] load_daily_events: {e}")
            traceback.print_exc()
    
    def load_specials_events():
        """Carga eventos especiales del turno actual del usuario (modo Specials)"""
        try:
            conn = get_connection()
            cur = conn.cursor()
            
            # Obtener eventos especiales del día actual del usuario
            cur.execute("""
                SELECT e.FechaHora, s.Nombre_Sitio, e.Nombre_Actividad, 
                       e.Cantidad, e.Camera, e.Descripcion, e.Marks
                FROM Eventos e
                LEFT JOIN Sitios s ON e.ID_Sitio = s.ID_Sitio
                LEFT JOIN user u ON e.ID_Usuario = u.ID_Usuario
                WHERE u.Nombre_Usuario = %s 
                  AND DATE(e.FechaHora) = CURDATE()
                  AND e.Marks IS NOT NULL AND e.Marks != ''
                ORDER BY e.FechaHora DESC
            """, (username,))
            
            rows = cur.fetchall()
            cur.close()
            conn.close()
            
            # Preparar datos
            data = []
            for idx, row in enumerate(rows, start=1):
                fecha_hora = str(row[0]) if row[0] else ""
                sitio = row[1] if row[1] else ""
                actividad = row[2] if row[2] else ""
                cantidad = str(row[3]) if row[3] else ""
                camera = row[4] if row[4] else ""
                descripcion = row[5] if row[5] else ""
                marks = row[6] if row[6] else ""
                
                data.append([str(idx), fecha_hora, sitio, actividad, cantidad, camera, descripcion, marks])
            
            if not data:
                data = [["No hay eventos especiales registrados hoy"] + [""] * 7]
            
            sheet.set_sheet_data(data)
            sheet.redraw()
            
            print(f"[DEBUG] Loaded {len(rows)} special events for {username}")
            
        except Exception as e:
            messagebox.showerror("Error", f"Error cargando eventos specials:\n{e}", parent=parent_top)
            print(f"[ERROR] load_specials_events: {e}")
            traceback.print_exc()
    
    def switch_to_daily():
        """Cambia la vista a Daily mode"""
        current_view_mode[0] = 'daily'
        
        # Actualizar título
        if parent_ui is not None:
            title_label.configure(text="📝 Eventos Daily - Hoy")
        else:
            title_label.configure(text="📝 Eventos Daily - Hoy")
        
        # Actualizar columnas del sheet
        daily_columns = ["#", "Fecha/Hora", "Sitio", "Actividad", "Cantidad", "Cámara", "Descripción"]
        sheet.headers(daily_columns)
        sheet.redraw()
        
        # Ajustar anchos de columna (7 columnas: índices 0-6)
        try:
            sheet.column_width(column=0, width=50)
            sheet.column_width(column=1, width=150)
            sheet.column_width(column=2, width=180)
            sheet.column_width(column=3, width=120)
            sheet.column_width(column=4, width=80)
            sheet.column_width(column=5, width=100)
            sheet.column_width(column=6, width=250)
        except Exception as e:
            print(f"[WARNING] Error setting column widths: {e}")
        
        # Mostrar botón "Ver Covers", ocultar "Ver Daily"
        if parent_ui is not None:
            covers_btn.pack(side="right", padx=5, pady=15, before=refresh_btn)
            daily_btn.pack_forget()
        else:
            covers_btn.pack(side="right", padx=5, pady=15, before=refresh_btn)
            daily_btn.pack_forget()
        
        # Cargar datos
        load_daily_events()
        
        print("[DEBUG] Switched to Daily view")
    
    def switch_to_specials():
        """Cambia la vista a Specials mode"""
        current_view_mode[0] = 'specials'
        
        # Actualizar título
        if parent_ui is not None:
            title_label.configure(text="⭐ Eventos Specials - Hoy")
        else:
            title_label.configure(text="⭐ Eventos Specials - Hoy")
        
        # Actualizar columnas del sheet
        specials_columns = ["#", "Fecha/Hora", "Sitio", "Actividad", "Cantidad", "Cámara", "Descripción", "Marks"]
        sheet.headers(specials_columns)
        sheet.redraw()
        
        # Ajustar anchos de columna (8 columnas: índices 0-7)
        try:
            sheet.column_width(column=0, width=50)
            sheet.column_width(column=1, width=140)
            sheet.column_width(column=2, width=150)
            sheet.column_width(column=3, width=120)
            sheet.column_width(column=4, width=70)
            sheet.column_width(column=5, width=90)
            sheet.column_width(column=6, width=200)
            sheet.column_width(column=7, width=100)
        except Exception as e:
            print(f"[WARNING] Error setting column widths: {e}")
        
        # Mostrar botón "Ver Covers", ocultar "Ver Specials"
        if parent_ui is not None:
            covers_btn.pack(side="right", padx=5, pady=15, before=refresh_btn)
            specials_btn.pack_forget()
        else:
            covers_btn.pack(side="right", padx=5, pady=15, before=refresh_btn)
            specials_btn.pack_forget()
        
        # Cargar datos
        load_specials_events()
        
        print("[DEBUG] Switched to Specials view")
    
    def switch_to_covers():
        """Cambia la vista de vuelta a Covers mode"""
        current_view_mode[0] = 'covers'
        
        # Actualizar título
        if parent_ui is not None:
            title_label.configure(text="📋 Lista de Covers Programados")
        else:
            title_label.configure(text="📋 Lista de Covers Programados")
        
        # Actualizar columnas del sheet
        covers_columns = ["#", "Usuario", "Hora Solicitud", "Estación", "Razón", "Aprobado"]
        sheet.headers(covers_columns)
        sheet.redraw()
        
        # Ajustar anchos de columna (6 columnas: índices 0-5)
        try:
            sheet.column_width(column=0, width=50)
            sheet.column_width(column=1, width=150)
            sheet.column_width(column=2, width=180)
            sheet.column_width(column=3, width=100)
            sheet.column_width(column=4, width=350)
            sheet.column_width(column=5, width=100)
        except Exception as e:
            print(f"[WARNING] Error setting column widths: {e}")
        
        # Ocultar botón "Ver Covers" y mostrar Daily/Specials
        if parent_ui is not None:
            covers_btn.pack_forget()
            daily_btn.pack(side="right", padx=5, pady=15, before=refresh_btn)
            specials_btn.pack(side="right", padx=5, pady=15, before=refresh_btn)
        else:
            covers_btn.pack_forget()
            daily_btn.pack(side="right", padx=5, pady=15, before=refresh_btn)
            specials_btn.pack(side="right", padx=5, pady=15, before=refresh_btn)
        
        # Cargar datos
        load_covers_data()
        
        print("[DEBUG] Switched to Covers view")
    
    def refresh_current_view():
        """Refresca la vista actual según el modo activo"""
        mode = current_view_mode[0]
        if mode == 'daily':
            load_daily_events()
        elif mode == 'specials':
            load_specials_events()
        else:  # covers
            load_covers_data()
        
        print(f"[DEBUG] Refreshed {mode} view")
    
    # Variable para almacenar el ID del job de auto-refresh
    refresh_job = [None]
    
    def auto_refresh():
        """Refresca automáticamente los datos cada 10 segundos según modo actual"""
        try:
            refresh_current_view()
        except Exception as e:
            print(f"[ERROR] auto_refresh: {e}")
        
        # Programar siguiente refresh
        refresh_job[0] = parent_top.after(10000, auto_refresh)
    
    def close_panel():
        """Cierra el panel y cancela el auto-refresh"""
        try:
            # Cancelar job de auto-refresh si existe
            if refresh_job[0] is not None:
                parent_top.after_cancel(refresh_job[0])
                refresh_job[0] = None
            
            # Destruir el panel
            panel_frame.destroy()
            print("[DEBUG] Covers panel closed")
        except Exception as e:
            print(f"[ERROR] close_panel: {e}")
    
    # Cargar datos inicialmente
    load_covers_data()
    
    # Iniciar auto-refresh
    auto_refresh()
    
    print(f"[DEBUG] Covers programados panel opened for {username}")


def prompt_exit_active_cover(username, root):
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT ID_Covers FROM covers_realizados
            WHERE Nombre_usuarios = %s AND Cover_out IS NULL
            ORDER BY ID_Covers DESC
            LIMIT 1
            """,
            (username,)
        )
        row = cur.fetchone()
    finally:
        try: cur.close()
        except: pass
        try: conn.close()
        except: pass

    if row:
        messagebox.showinfo(
            "Cover activo",
            "Tienes un cover activo. Se cerrará automáticamente.",
            parent=root
        )
        exit_cover(username)

def cover_mode(username, session_id, station, root=None):
    # Ventana única por función
    ex = _focus_singleton('cover_mode')
    if ex:
        return ex

    # Intentar usar CustomTkinter para modernizar la UI (fallback a Tk)
    UI = None
    try:
        import importlib
        ctk = importlib.import_module('customtkinter')
        try:
            ctk.set_appearance_mode("dark")
            ctk.set_default_color_theme("dark-blue")
        except Exception:
            pass
        UI = ctk
    except Exception:
        UI = None

    # Crear ventana Cover como Toplevel (CTk si está disponible)
    if UI is not None:
        cover_form = UI.CTkToplevel(root)
        try:
            cover_form.configure(fg_color="#2c2f33")
        except Exception:
            pass
    else:
        cover_form = tk.Toplevel(root)
        cover_form.configure(bg="#2c2f33")
    cover_form.title("Registrar Evento")
    cover_form.geometry("360x240")
    cover_form.resizable(False, False)

    # Forzar que la ventana quede al frente y con foco
    try:
        cover_form.update_idletasks()
        cover_form.deiconify()
    except Exception:
        pass
    try:
        # Mantener relación con la ventana principal
        cover_form.transient(root)
    except Exception:
        pass
    try:
        cover_form.lift()
    except Exception:
        pass
    try:
        # Ponerla temporalmente como 'topmost' para que aparezca delante y luego revertir
        cover_form.attributes("-topmost", True)
        cover_form.after(200, lambda: cover_form.attributes("-topmost", False))
    except Exception:
        pass
    try:
        cover_form.focus_force()
    except Exception:
        pass
    try:
        # Evitar que quede detrás al interactuar con otras ventanas
        cover_form.grab_set()
    except Exception:
        pass

    # Encabezado
    if UI is not None:
        UI.CTkLabel(
            cover_form,
            text="Modo de Cover",
            text_color="#e0e0e0",
            font=("Segoe UI", 16, "bold"),
            anchor="w",
        ).place(x=20, y=12)
        UI.CTkLabel(
            cover_form,
            text="Motivo*:",
            text_color="#a3c9f9",
            font=("Segoe UI", 12, "bold"),
            anchor="w",
        ).place(x=20, y=58)
    else:
        tk.Label(
            cover_form,
            text="Modo de Cover",
            bg="#2c2f33",
            fg="#d0d0d0",
            font=("Segoe UI", 13, "bold"),
        ).place(x=30, y=10)
        tk.Label(
            cover_form,
            text="Motivo*:",
            bg="#2c2f33",
            fg="#d0d0d0",
            font=("Segoe UI", 11, "bold"),
        ).place(x=30, y=70)

    cover_form_var = tk.StringVar()
    if UI is not None:
        try:
            cover_form_menu = under_super.FilteredCombobox(
                cover_form,
                textvariable=cover_form_var,
                values=("Cover Baño", "Cover Daily", "Break", "Trainning", "Otro"),
                font=("Segoe UI", 10),
            )
        except Exception:
            pass
    cover_form_menu.place(x=150, y=50)

    if UI is not None:
        UI.CTkLabel(
            cover_form,
            text="Covered By:",
            text_color="#a3c9f9",
            font=("Segoe UI", 12, "bold"),
            anchor="w",
        ).place(x=20, y=102)
    else:
        tk.Label(
            cover_form,
            text="Covered By:",
            bg="#2c2f33",
            fg="#d0d0d0",
            font=("Segoe UI", 11, "bold"),
        ).place(x=30, y=100)

    covered_by_var = tk.StringVar()
    
    # Obtener usuarios con rol Operador y Supervisor
    covered_by_users = []
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            "SELECT Nombre_Usuario FROM user WHERE Rol = %s ORDER BY Nombre_Usuario",
            ("Operador",)
        )
        covered_by_users = [row[0] for row in cur.fetchall()]
        cur.close()
        conn.close()
    except Exception as e:
        print(f"[ERROR] al cargar usuarios para Covered By: {e}")
    
    if UI is not None:
        try:
            covered_by_combo = under_super.FilteredCombobox(
                    cover_form,
                    textvariable=covered_by_var,
                    values=covered_by_users,
                    font=("Segoe UI", 10)
            )
        except Exception:
            pass
    
    covered_by_combo.place(x=150, y=100)

    # Preferencia: cerrar sesión al guardar (para reducir clicks)
    logout_after_var = tk.BooleanVar(value=True)
    if UI is not None:
        try:
            UI.CTkCheckBox(
                cover_form,
                text="Cerrar sesión automáticamente",
                variable=logout_after_var,
                text_color="#e0e0e0",
            ).place(x=20, y=140)
        except Exception:
            pass
    
    def on_registrar_cover():
        try:
            under_super.insertar_cover(username, covered_by_var.get(), cover_form_var.get(), session_id, station)
            print("[DEBUG] Cover registrado correctamente.")
            print("[DEBUG] logout_after_var.get():", logout_after_var.get())
            if logout_after_var.get():
                try:
                    login.logout_silent(session_id, station)
                except Exception as e:
                    print(f"[WARN] logout_silent falló: {e}")
                target_user = (covered_by_var.get() or '').strip()
                if not target_user:
                    messagebox.showwarning("Cover", "Debes indicar 'Covered By' para continuar al main.")
                    return  # Mantener el formulario abierto para que el usuario complete el campo
                ok, sid2, role2 = login.auto_login(target_user, station, password="1234", parent=root, silent=True)
                if not ok:
                    # Mantener el formulario abierto si el login automático falla
                    messagebox.showerror("Auto Login", "No fue posible hacer login automático.")
                    return

            # Cerrar el formulario (flujo normal o cuando el auto-login ya abrió el main)
            try:
                cover_form.destroy()
            except Exception:
                pass

        except Exception as e:
            print("[ERROR] insert cover:", e)

    

    
    # Registrar Cover (se cerrará sesión automáticamente al insertar)
    if UI is not None:
        UI.CTkButton(
            cover_form,
            text="Registrar Cover",
            command=lambda: on_registrar_cover(),
            fg_color="#4a90e2",
            hover_color="#357ABD",
            width=160,
    ).place(x=150, y=180)
    else:
        cover_form_btn = tk.Button(cover_form, text="Registrar Cover", command=lambda: on_registrar_cover())
        cover_form_btn.place(x=30, y=160, width=120)

    _register_singleton('cover_mode', cover_form)
    # No mainloop aquí; es un Toplevel dentro de la app



def exit_cover(username):
    """Cierra el cover abierto (pone Cover_out a now) y desactiva el modo_cover."""
    now = datetime.now()
    conn = get_connection()
    cur = conn.cursor()
    
    # Obtener el último ID de Covers para el usuario con Activo = -1
    try:
        cur.execute(
            """
        SELECT ID_Covers
        FROM covers_realizados
        WHERE Nombre_usuarios = %s
        ORDER BY ID_Covers DESC
        LIMIT 1
        """,
        (username,)
        )
        conn.commit()
        

        result = cur.fetchone()
        ID_cover = result[0] if result else None
        print(f"[DEBUG] ID_cover obtenido: {ID_cover}")
    
    except pymysql.Error as e:
        print(f"[ERROR] al obtener ID_cover: {e}")
        return ID_cover

    try:
        # Usar el último ID insertado (current_cover_id) y el username para actualizar Activo a 0
        cur.execute(
            """
            UPDATE covers_realizados
            SET Cover_out = %s
            WHERE ID_Covers = %s AND Nombre_usuarios = %s
            """,
            (now, ID_cover, username)
        )
        conn.commit()
        print("[DEBUG] Cover actualizado correctamente")
    except Exception as e:
        print("[ERROR]", e)
    finally:
        cur.close()
        conn.close()




def audit_view(parent=None):
    """Ventana para auditar eventos con filtros básicos y avanzados.
    Campos básicos: Usuario, Sitio, Fecha (texto simple).
    Botón 'Búsqueda avanzada' despliega campos adicionales: rango de fechas (start/end),
    filtros por día/mes/año y por ID_Grupo de Sitios.
    Los resultados se muestran en un Treeview.
    """
    # Ventana
    ex = _focus_singleton('audit')
    if ex:
        return ex
    # Intentar usar CustomTkinter para una UI más moderna (gradual)
    UI = None
    try:
        import importlib
        ctk = importlib.import_module('customtkinter')
        try:
            ctk.set_appearance_mode("dark")
            ctk.set_default_color_theme("dark-blue")
        except Exception:
            pass
        UI = ctk
    except Exception:
        UI = None

    win = (UI.CTkToplevel(parent if parent is not None else None)
           if UI is not None else tk.Toplevel(parent if parent is not None else None))
    win.title("Audit - Buscar Eventos")
    win.geometry("1000x600")
    try:
        win.configure(bg="#2c2f33")
    except Exception:
        pass
    win.resizable(True, True)

    # Header
    try:
        if UI is not None:
            UI.CTkLabel(win, text="Audit - Buscar Eventos", font=("Segoe UI", 18, "bold"), text_color="#e0e0e0").pack(pady=(12,6))
        else:
            tk.Label(win, text="Audit - Buscar Eventos", bg="#2c2f33", fg="#e0e0e0", font=("Segoe UI", 16, "bold")).pack(pady=(12,6))
    except Exception:
        tk.Label(win, text="Audit - Buscar Eventos", bg="#2c2f33", fg="#e0e0e0", font=("Segoe UI", 16, "bold")).pack(pady=(12,6))
    try:
        ttk.Separator(win, orient="horizontal").pack(fill="x", padx=12, pady=(0,8))
    except Exception:
        pass

    # Estilos locales para esta ventana (dark theme coherente)
    style = ttk.Style()
    audit_style = f"AuditStyle_{id(win)}"
    try:
        style.configure(
            f"{audit_style}.Treeview",
            background="#23272a",
            foreground="#e0e0e0",
            fieldbackground="#23272a",
            rowheight=26,
            bordercolor="#23272a",
            borderwidth=0,
        )
        style.configure(
            f"{audit_style}.Treeview.Heading",
            background="#23272a",
            foreground="#a3c9f9",
            font=("Segoe UI", 10, "bold"),
        )
        style.map(
            f"{audit_style}.Treeview",
            background=[("selected", "#4a90e2")],
            foreground=[("selected", "#ffffff")],
        )

        style.configure(
            f"{audit_style}.TButton",
            background="#314052",
            foreground="#e0e0e0",
            padding=7,
            borderwidth=0,
            focusthickness=3,
            focuscolor="#4a90e2",
        )
        style.map(
            f"{audit_style}.TButton",
            background=[("active", "#4a90e2")],
            foreground=[("active", "#ffffff")],
        )
    except Exception:
        pass

    # Frame para filtros
    filt_frame = tk.Frame(win, bg="#2c2f33")
    filt_frame.pack(fill="x", padx=12, pady=(0,8))

    # Usuario
    tk.Label(filt_frame, text="Usuario:", bg=filt_frame['bg'], fg="#c9d1d9").grid(row=0, column=0, sticky="w", padx=6, pady=6)
    user_var = tk.StringVar()
    # obtener lista de usuarios de la BD
    try:
        conn = get_connection()
        cur = conn.cursor()

        # 🔹 Consulta adaptada a MySQL
        cur.execute("SELECT `Nombre_Usuario` FROM `user` ORDER BY `Nombre_Usuario`")

        # Obtener los resultados como lista
        users = [r[0] for r in cur.fetchall()]

        cur.close()
        conn.close()

    except Exception:
        users = []

    try:
        user_cb = under_super.FilteredCombobox(filt_frame, textvariable=user_var, values=users, width=30)
    except Exception:
        user_cb = ttk.Combobox(filt_frame, textvariable=user_var, values=users, width=30)
    user_cb.grid(row=0, column=1, sticky="w", padx=6)

    # Sitio
    tk.Label(filt_frame, text="Sitio:", bg=filt_frame['bg'], fg="#c9d1d9").grid(row=0, column=2, sticky="w", padx=6, pady=6)
    site_var = tk.StringVar()
    try:
        sites = under_super.get_sites()
    except Exception:
        sites = []
    try:
        site_cb = under_super.FilteredCombobox(filt_frame, textvariable=site_var, values=sites, width=40)
    except Exception:
        site_cb = ttk.Combobox(filt_frame, textvariable=site_var, values=sites, width=40)
    site_cb.grid(row=0, column=3, sticky="w", padx=6)

    # Fecha con selector (tkcalendar) - mantiene formato YYYY-MM-DD
    tk.Label(filt_frame, text="Fecha:", bg=filt_frame['bg'], fg="#c9d1d9").grid(row=1, column=0, sticky="w", padx=6, pady=6)
    try:
        from tkcalendar import DateEntry
        fecha_var = tk.StringVar()
        fecha_entry = DateEntry(
            filt_frame,
            textvariable=fecha_var,
            date_pattern="yyyy-mm-dd",
            width=18
        )
    except Exception:
        # Fallback si no está instalado tkcalendar
        fecha_var = tk.StringVar()
        fecha_entry = tk.Entry(filt_frame, textvariable=fecha_var, width=20)
    fecha_entry.grid(row=1, column=1, sticky="w", padx=6)

    # Botones de acción
    btn_frame = tk.Frame(filt_frame, bg=filt_frame['bg'])
    btn_frame.grid(row=1, column=3, sticky="e", padx=6)

    # Advanced toggle
    adv_shown = {'v': False}
    adv_frame = tk.Frame(win, bg="#2c2f33")

    def toggle_advanced():
        if adv_shown['v']:
            adv_frame.pack_forget()
            adv_shown['v'] = False
            adv_btn.config(text="Búsqueda avanzada ▾")
        else:
            adv_frame.pack(fill="x", padx=12, pady=(0,8))
            adv_shown['v'] = True
            adv_btn.config(text="Búsqueda avanzada ▴")

    try:
        if UI is not None:
            adv_btn = UI.CTkButton(btn_frame, text="Búsqueda avanzada ▾", command=toggle_advanced)
        else:
            adv_btn = ttk.Button(btn_frame, text="Búsqueda avanzada ▾", command=toggle_advanced, style=f"{audit_style}.TButton")
    except Exception:
        adv_btn = tk.Button(btn_frame, text="Búsqueda avanzada ▾", command=toggle_advanced, bg="#314052", fg="#e0e0e0")
    adv_btn.pack(side="left", padx=(0,6))

    # Search and Clear buttons
    def clear_filters():
        user_var.set("")
        site_var.set("")
        fecha_var.set("")
        start_var.set("")
        end_var.set("")
        idgrupo_var.set("")
        tree.delete(*tree.get_children())

    try:
        if UI is not None:
            search_btn = UI.CTkButton(btn_frame, text="Buscar", command=lambda: run_search())
            search_btn.pack(side="left", padx=(0,6))
            clear_btn = UI.CTkButton(btn_frame, text="Limpiar", command=clear_filters)
            clear_btn.pack(side="left")
        else:
            search_btn = ttk.Button(btn_frame, text="Buscar", command=lambda: run_search(), style=f"{audit_style}.TButton")
            search_btn.pack(side="left", padx=(0,6))
            clear_btn = ttk.Button(btn_frame, text="Limpiar", command=clear_filters, style=f"{audit_style}.TButton")
            clear_btn.pack(side="left")
    except Exception:
        search_btn = tk.Button(btn_frame, text="Buscar", bg="#13988e", fg="#fff", command=lambda: run_search())
        search_btn.pack(side="left", padx=(0,6))
        clear_btn = tk.Button(btn_frame, text="Limpiar", bg="#a3a3a3", fg="#111", command=clear_filters)
        clear_btn.pack(side="left")

    # Preparar tabla: intentar tksheet; fallback a Treeview
    use_sheet = False
    sheet = None
    try:
        import importlib
        Sheet = importlib.import_module('tksheet').Sheet
        use_sheet = True
    except Exception:
        use_sheet = False

    # Export button with menu (Excel / PDF)
    def export_selected_to_excel():
        try:
            if use_sheet and sheet is not None:
                # Obtener datos desde tksheet
                try:
                    sel_rows = list(sheet.get_selected_rows())
                except Exception:
                    sel_rows = []
                data = sheet.get_sheet_data()
                if not sel_rows:
                    rows_data = data
                else:
                    rows_data = [data[r] for r in sel_rows if 0 <= r < len(data)]
                rows_dict = []
                for row in rows_data:
                    vals = list(row) + [""] * (len(cols) - len(row))
                    rows_dict.append({cols[i]: vals[i] if i < len(vals) else "" for i in range(len(cols))})
            else:
                sel = tree.selection()
                if not sel:
                    items = tree.get_children()
                else:
                    items = sel
                if not items:
                    messagebox.showinfo("Exportar", "No hay registros para exportar.", parent=win)
                    return
                rows_dict = []
                for it in items:
                    vals = tree.item(it, "values")
                    rows_dict.append({cols[i]: vals[i] if i < len(vals) else "" for i in range(len(cols))})

            df = pd.DataFrame(rows_dict)
            fname = filedialog.asksaveasfilename(parent=win, defaultextension='.xlsx', filetypes=[('Excel files','*.xlsx'), ('All files','*.*')], title='Guardar como')
            if not fname:
                return
            df.to_excel(fname, index=False)
            messagebox.showinfo("Exportar", f"Exportado a Excel: {fname}", parent=win)
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo exportar a Excel:\n{e}", parent=win)

    def export_selected_to_pdf():
        # Try to use reportlab; if not available, show instructions
        try:
            from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
            from reportlab.lib import colors
            from reportlab.lib.pagesizes import letter, landscape
        except Exception:
            messagebox.showerror("PDF no disponible", "La exportación a PDF requiere 'reportlab'.\nInstálalo con: pip install reportlab", parent=win)
            return

        # Construir 'data' con headers + filas según selection/table
        data = [list(cols)]
        if use_sheet and sheet is not None:
            try:
                sel_rows = list(sheet.get_selected_rows())
            except Exception:
                sel_rows = []
            full = sheet.get_sheet_data()
            if not sel_rows:
                rows_src = full
            else:
                rows_src = [full[r] for r in sel_rows if 0 <= r < len(full)]
            for row in rows_src:
                vals = list(row)
                while len(vals) < len(cols):
                    vals.append("")
                data.append(vals)
        else:
            sel = tree.selection()
            if not sel:
                items = tree.get_children()
            else:
                items = sel
            if not items:
                messagebox.showinfo("Exportar", "No hay registros para exportar.", parent=win)
                return
            for it in items:
                vals = list(tree.item(it, 'values'))
                while len(vals) < len(cols):
                    vals.append("")
                data.append(vals)

        fname = filedialog.asksaveasfilename(parent=win, defaultextension='.pdf', filetypes=[('PDF files','*.pdf'), ('All files','*.*')], title='Guardar como PDF')
        if not fname:
            return

        try:
            doc = SimpleDocTemplate(fname, pagesize=landscape(letter))
            table = Table(data)
            style = TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#23272a')),
                ('TEXTCOLOR', (0,0), (-1,0), colors.white),
                ('GRID', (0,0), (-1,-1), 0.25, colors.grey),
                ('BACKGROUND', (0,1), (-1,-1), colors.whitesmoke),
            ])
            table.setStyle(style)
            elems = [table]
            doc.build(elems)
            messagebox.showinfo("Exportar", f"Exportado a PDF: {fname}", parent=win)
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo exportar a PDF:\n{e}", parent=win)

    export_mb = tk.Menubutton(btn_frame, text="Exportar ▾", bg="#3b4754", fg="#e0e0e0", relief="raised")
    export_menu = tk.Menu(export_mb, tearoff=0)
    export_menu.add_command(label="Exportar a Excel", command=export_selected_to_excel)
    export_menu.add_command(label="Exportar a PDF", command=export_selected_to_pdf)
    export_mb.config(menu=export_menu)
    export_mb.pack(side="left", padx=(6,0))

    # Advanced fields inside adv_frame
    tk.Label(adv_frame, text="Rango fechas (YYYY-MM-DD):", bg=adv_frame['bg'], fg="#c9d1d9").grid(row=0, column=0, sticky="w", padx=6, pady=6)
    start_var = tk.StringVar(); end_var = tk.StringVar()
    tk.Entry(adv_frame, textvariable=start_var, width=12).grid(row=0, column=1, sticky="w", padx=6)
    tk.Label(adv_frame, text="a", bg=adv_frame['bg'], fg="#c9d1d9").grid(row=0, column=2)
    tk.Entry(adv_frame, textvariable=end_var, width=12).grid(row=0, column=3, sticky="w", padx=6)

    tk.Label(adv_frame, text="ID_Grupo Sitio:", bg=adv_frame['bg'], fg="#c9d1d9").grid(row=2, column=0, sticky="w", padx=6, pady=6)
    idgrupo_var = tk.StringVar()
    tk.Entry(adv_frame, textvariable=idgrupo_var, width=8).grid(row=2, column=1, sticky="w", padx=6)

    # Resultados: tksheet si está disponible, sino Treeview
    cols = ("ID_Evento", " ", "Nombre_Sitio", "Nombre_Actividad", "Cantidad", "Camera", "Descripcion", "Usuario")
    if use_sheet:
        if UI is not None:
            table_frame = UI.CTkFrame(win)
        else:
            table_frame = tk.Frame(win, bg="#2c2f33")
        table_frame.pack(expand=True, fill="both", padx=12, pady=(6,12))
        sheet = Sheet(table_frame, headers=list(cols))
        sheet.enable_bindings((
            "single_select",
            "row_select",
            "column_select",
            "arrowkeys",
            "right_click_popup_menu",
            "rc_select",
            "copy",
            "select_all",
            "column_width_resize",
            "double_click_column_resize",
            "row_height_resize",
        ))
        sheet.grid(row=0, column=0, sticky="nsew")
        try:
            table_frame.grid_rowconfigure(0, weight=1)
            table_frame.grid_columnconfigure(0, weight=1)
            # Tema oscuro completo para tksheet (headers/índice/grid/texto/selección)
            sheet.set_options(
                header_bg="#23272a",
                header_fg="#a3c9f9",
                header_border_fg="#3a3f44",
                index_bg="#23272a",
                index_fg="#a3c9f9",
                index_border_fg="#3a3f44",
                top_left_bg="#23272a",
                top_left_fg="#a3c9f9",
                table_bg="#2c2f33",
                table_fg="#e0e0e0",
                table_grid_fg="#3a3f44",
                header_selected_cells_bg="#4a90e2",
                header_selected_cells_fg="#ffffff",
                selected_rows_bg="#14414e",
                selected_rows_fg="#ffffff",
                selected_columns_bg="#14414e",
                selected_columns_fg="#ffffff",
            )
        except Exception:
            pass
    else:
        tree_frame = tk.Frame(win, bg="#2c2f33")
        tree_frame.pack(expand=True, fill="both", padx=12, pady=(6,12))
        yscroll = tk.Scrollbar(tree_frame, orient="vertical")
        yscroll.pack(side="right", fill="y")
        xscroll = tk.Scrollbar(tree_frame, orient="horizontal")
        xscroll.pack(side="bottom", fill="x")
        tree = ttk.Treeview(
            tree_frame,
            columns=cols,
            show="headings",
            yscrollcommand=yscroll.set,
            xscrollcommand=xscroll.set,
            selectmode="extended",
            style=f"{audit_style}.Treeview",
        )
        yscroll.config(command=tree.yview); xscroll.config(command=tree.xview)
        for c in cols:
            tree.heading(c, text=c)
            tree.column(c, width=130, anchor="w")
        tree.pack(expand=True, fill="both")
        try:
            tree.tag_configure("oddrow", background="#3a3f44", foreground="#e0e0e0")
            tree.tag_configure("evenrow", background="#2f343a", foreground="#e0e0e0")
        except Exception:
            pass

    def parse_date_flex(s):
        s = (s or "").strip()
        if not s:
            return None
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%Y/%m/%d"):
            try:
                return datetime.strptime(s, fmt)
            except Exception:
                pass
        # try to parse date/time
        try:
            return datetime.fromisoformat(s)
        except Exception:
            return None

    def run_search():
        conn = get_connection()
        cur = conn.cursor()

        base = (
            "SELECT e.`ID_Eventos`, e.` `, s.`Nombre_Sitio`, "
            "e.`Nombre_Actividad`, e.`Cantidad`, e.`Camera`, e.`Descripcion`, "
            "u.`Nombre_Usuario` "
            "FROM `eventos` AS e "
            "LEFT JOIN `sitios` AS s ON e.`ID_Sitio` = s.`ID_Sitio` "
            "LEFT JOIN `user` AS u ON e.`ID_Usuario` = u.`ID_Usuario` "
            "WHERE 1=1"
        )

        params = []

        # Agregas los filtros dinámicos
        uval = user_var.get().strip()
        if uval:
            base += " AND u.`Nombre_Usuario` = %s"
            params.append(uval)

        sval = site_var.get().strip()
        if sval:
            sid = None
            try:
                sid = int(sval.split()[-1])
            except Exception:
                sid = None
            if sid is not None:
                base += " AND e.`ID_Sitio` = %s"
                params.append(sid)
            else:
                base += " AND s.`Nombre_Sitio` LIKE %s"
                params.append(f"%{sval}%")

        # Fecha única
        fval = fecha_var.get().strip()
        if fval:
            dt = parse_date_flex(fval)
            if dt:
                start = datetime(dt.year, dt.month, dt.day)
                end = start + timedelta(days=1)
                base += " AND e.` ` >= %s AND e.` ` < %s"
                params.extend([start, end])

        # Fechas rango
        sstart = parse_date_flex(start_var.get().strip())
        send = parse_date_flex(end_var.get().strip())
        if sstart and send:
            send = datetime(send.year, send.month, send.day) + timedelta(days=1)
            base += " AND e.` ` >= %s AND e.` ` < %s"
            params.extend([sstart, send])

        # Filtro grupo
        gid = idgrupo_var.get().strip()
        if gid:
            try:
                gid_int = int(gid)
                base += " AND e.`ID_Sitio` IN (SELECT `ID_Sitio` FROM `sitios` WHERE `ID_Grupo` = %s)"
                params.append(gid_int)
            except Exception:
                base += " AND EXISTS (SELECT 1 FROM `sitios` st WHERE st.`ID_Sitio` = e.`ID_Sitio` AND st.`ID_Grupo` = %s)"
                params.append(gid)

        # ✅ SOLO AHORA pones el ORDER BY
        base += " ORDER BY e.` ` DESC"

        print(f"[DEBUG] SQL={base} params={params}")

        cur.execute(base, tuple(params))
        rows = cur.fetchall()
        cur.close()
        conn.close()


        # Execute
        try:
            # 🔹 Conexión a la base de datos MySQL
            conn = get_connection()
            cur = conn.cursor()

            print(f"[DEBUG] audit_view.run_search SQL={base} params={params}")

            # Ejecutar la consulta
            cur.execute(base, tuple(params))
            rows = cur.fetchall()

            cur.close()
            conn.close()

        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            print(f"[ERROR] audit_view.run_search exception:\n{tb}")

            # Mostrar mensaje amigable en interfaz
            messagebox.showerror(
                "Error DB",
                f"Error al consultar la base de datos:\n{e}\n\nVer consola para más detalles.",
                parent=win
            )
            return

        # Mostrar resultados
        if use_sheet and sheet is not None:
            try:
                data = []
                for r in rows:
                    vals = ["" if v is None else str(v) for v in r]
                    data.append(vals)
                sheet.set_sheet_data(data)
                sheet.set_headers(list(cols))
            except Exception:
                pass
        else:
            tree.delete(*tree.get_children())
            for idx, r in enumerate(rows):
                vals = [str(v) if v is not None else "" for v in r]
                try:
                    tag = "evenrow" if idx % 2 == 0 else "oddrow"
                    tree.insert("", "end", values=vals, tags=(tag,))
                except Exception:
                    tree.insert("", "end", values=vals)

    # inicialmente oculto advanced
    # pack tree (already done)

    # Atajos de teclado (sin Ctrl+F por solicitud)
    try:
        win.bind("<Control-s>", lambda e: export_selected_to_excel())
        win.bind("<Escape>", lambda e: win.destroy())
    except Exception:
        pass

    # show window
    win.transient()
    win.grab_set()
    win.focus_force()
    _register_singleton('audit', win)
    return win


def open_admin_window(main_win=None):
    ex = _focus_singleton('admin')
    if ex:
        return ex
    admin_win = tk.Toplevel()
    admin_win.title("Edición")
    admin_win.configure(bg="#2c2f33")
    admin_win.geometry(f"260x200+0+{admin_win.winfo_screenheight()-360}")
    admin_win.resizable(False, False)
    _register_singleton('admin', admin_win)

    # Título
    tk.Label(
        admin_win, 
        text="Modo administrador: Edición", 
        bg="#2c2f33", fg="#a3c9f9", 
        font=("Segoe UI", 12, "bold")
    ).place(x=8, y=20)

    # Etiqueta para selección
    tk.Label(
        admin_win, 
        text="Editar:", 
        bg="#2c2f33", fg="#d0d0d0", 
        font=("Segoe UI", 11, "bold")
    ).place(x=10, y=70)

    # Combobox con opciones
    options = ["Sitio", "Actividad", "Usuario"]
    selected_option = tk.StringVar()
    combo = under_super.FilteredCombobox(
        admin_win, 
        textvariable=selected_option, 
        values=options, 
        state="readonly",
        font=("Segoe UI", 10)
    )
    combo.place(x=90, y=70, width=130)
    combo.current(0)

    # ------------------------------
    # Función para abrir formulario
    # ------------------------------
    def open_form(option):
        form_win = tk.Toplevel(admin_win)
        form_win.title(f"Formulario {option}")
        form_win.configure(bg="#2c2f33")
        form_win.geometry("300x220")
        form_win.resizable(False, False)

        if option == "Sitio":
            # Labels + Entradas
            tk.Label(form_win, text="ID Sitio:", bg="#2c2f33", fg="white", font=("Segoe UI", 10)).place(x=20, y=20)
            id_sitio = tk.Entry(form_win, font=("Segoe UI", 10))
            id_sitio.place(x=120, y=20, width=150)

            tk.Label(form_win, text="ID Grupo:", bg="#2c2f33", fg="white", font=("Segoe UI", 10)).place(x=20, y=60)
            id_grupo = tk.Entry(form_win, font=("Segoe UI", 10))
            id_grupo.place(x=120, y=60, width=150)

            tk.Label(form_win, text="Nombre:", bg="#2c2f33", fg="white", font=("Segoe UI", 10)).place(x=20, y=100)
            nombre = tk.Entry(form_win, font=("Segoe UI", 10))
            nombre.place(x=120, y=100, width=150)

            tk.Label(form_win, text="Time Zone:", bg="#2c2f33", fg="white", font=("Segoe UI", 10)).place(x=20, y=140)
            time_zone = tk.Entry(form_win, font=("Segoe UI", 10))
            time_zone.place(x=120, y=140, width=150)

            # Botón guardar
            def guardar():
                try:
                    conn = get_connection()
                    cursor = conn.cursor()
                    cursor.execute(
                        "INSERT INTO Sitios (ID_Sitio, ID_Grupo, Nombre_Sitio, Time_Zone) VALUES (%s, %s, %s, %s)",
                        (id_sitio.get(), id_grupo.get(), nombre.get(), time_zone.get())
                    )
                    conn.commit()
                    conn.close()
                    print("✅ Sitio guardado en MySQL correctamente")

                    # Feedback visual
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

            tk.Button(form_win, text="Guardar", bg="#314052", fg="white", font=("Segoe UI", 10, "bold"), command=guardar)\
                .place(x=100, y=180, width=100, height=30)
            
        elif option == "Usuario":

            tk.Label(
            form_win, 
            text="Modo administrador: Agregar Usuario", 
            bg="#2c2f33", fg="#a3c9f9", 
            font=("Segoe UI", 9, "bold")
        ).place(x=8, y=20)
            
            # Labels + Entradas
            tk.Label(form_win, text="Usuario login:", bg="#2c2f33", fg="white", font=("Segoe UI", 10)).place(x=20, y=50)
            Nombre_usuario = tk.Entry(form_win, font=("Segoe UI", 10))
            Nombre_usuario.place(x=140, y=50, width=130)

            tk.Label(form_win, text="Contraseña:", bg="#2c2f33", fg="white", font=("Segoe UI", 10)).place(x=20, y=90)
            contrasena = tk.Entry(form_win, font=("Segoe UI", 10), show="*")
            contrasena.place(x=140, y=90, width=130)

            tk.Label(form_win, text="Rol:", bg="#2c2f33", fg="white", font=("Segoe UI", 10)).place(x=20, y=130)
            rol = tk.Entry(form_win, font=("Segoe UI", 10))
            rol.place(x=140, y=130, width=130)

            # Botón guardar
            def guardar_usuario():
                try:
                    conn = get_connection()
                    cursor = conn.cursor()
                    cursor.execute(
                        "INSERT INTO user (Nombre_Usuario, Rol, Contraseña) VALUES (%s, %s, %s)",
                        (Nombre_usuario.get(), rol.get(), contrasena.get())
                    )
                    conn.commit()
                    conn.close()
                    print("✅ Usuario guardado en MySQL correctamente")

                    # Feedback visual
                    tk.Label(
                        form_win, text="✔ Guardado exitosamente", 
                        bg="#2c2f33", fg="#a3f9c5", 
                        font=("Segoe UI", 9, "bold")
                    ).place(x=80, y=190)

                except Exception as e:
                    print("⚠ Error al guardar usuario:", e)
                    tk.Label(
                        form_win, text=f"⚠ Error: {e}", 
                        bg="#2c2f33", fg="#f9a3a3", 
                        font=("Segoe UI", 9, "bold")
                    ).place(x=20, y=190)

            tk.Button(form_win, text="Guardar", bg="#314052", fg="white", font=("Segoe UI", 10, "bold"), command=guardar_usuario)\
                .place(x=100, y=165, width=100, height=30)
            
        elif option == "Actividad":
            # Labels + Entradas
            tk.Label(form_win, text="Nombre Actividad:", bg="#2c2f33", fg="white", font=("Segoe UI", 10)).place(x=20, y=30)
            nombre_actividad = tk.Entry(form_win, font=("Segoe UI", 10))
            nombre_actividad.place(x=160, y=30, width=130)

            # Botón guardar
            def guardar_actividad():
                try:
                    conn = get_connection()
                    cursor = conn.cursor()
                    cursor.execute(
                        "INSERT INTO Actividades (Nombre_Actividad) VALUES (%s)",
                        (nombre_actividad.get(),)
                    )
                    conn.commit()
                    conn.close()
                    print("✅ Actividad guardada en Access")

                    # Feedback visual
                    tk.Label(
                        form_win, text="✔ Guardado exitosamente", 
                        bg="#2c2f33", fg="#a3f9c5", 
                        font=("Segoe UI", 9, "bold")
                    ).place(x=80, y=80)

                except Exception as e:
                    print("⚠ Error al guardar actividad:", e)
                    tk.Label(
                        form_win, text=f"⚠ Error: {e}", 
                        bg="#2c2f33", fg="#f9a3a3", 
                        font=("Segoe UI", 9, "bold")
                    ).place(x=20, y=80)

            tk.Button(form_win, text="Guardar", bg="#314052", fg="white", font=("Segoe UI", 10, "bold"), command=guardar_actividad)\
                .place(x=100, y=110, width=100, height=30)
    # ------------------------------
    # Botón Editar
    # ------------------------------
    def editar():
        opcion = selected_option.get()
        open_form(opcion)

    tk.Button(
        admin_win, text="Editar", 
        bg="#4a90e2", fg="white", 
        font=("Segoe UI", 10, "bold"), 
        command=editar
    ).place(x=90, y=120, width=80, height=30)

def get_station_status(tree=None):
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT Stations_ID, User_Logged FROM Estaciones")
        rows = cursor.fetchall()

        print("[DEBUG] Estaciones cargadas:")
        for row in rows:
            # row es una tupla, no un objeto — se accede por índice
            print(f"Station ID: {row[0]}, User Logged: {row[1]}")

        # Llenar el Treeview si se pasó como parámetro
        if tree is not None:
            for item in tree.get_children():
                tree.delete(item)
            for row in rows:
                tree.insert("", tk.END, values=(row[0], row[1]))

        conn.close()


    except Exception as e:
        messagebox.showerror("Error", f"No se pudo obtener el estado de las estaciones:\n{e}")
        print(f"[DEBUG] ERROR get_station_status: {e}")

    except Exception as e:
        messagebox.showerror("Error", f"No se pudo obtener el estado de las estaciones:\n{e}")
        print(f"[DEBUG] ERROR get_station_status: {e}")

def export_events_to_excel_from_db(user_name, conn_str, output_folder):
    conn = conn_str()  # aquí sí se ejecuta la función que retorna la conexión
    try:
        conn = conn_str()
        cur = conn.cursor()

        # --- Último shift (MySQL) ---
        cur.execute("""
            SELECT e.FechaHora FROM Eventos e
            INNER JOIN user u ON e.ID_Usuario = u.ID_Usuario
            WHERE u.Nombre_Usuario = %s AND e.Nombre_Actividad = %s
            ORDER BY e.FechaHora DESC
            LIMIT 1
        """, (user_name, 'START SHIFT'))
        last_start = cur.fetchone()

        cur.execute("""
            SELECT e.FechaHora FROM Eventos e
            INNER JOIN user u ON e.ID_Usuario = u.ID_Usuario
            WHERE u.Nombre_Usuario = %s AND e.Nombre_Actividad = %s
            ORDER BY e.FechaHora DESC
            LIMIT 1
        """, (user_name, 'END OF SHIFT'))
        last_end = cur.fetchone()

        if not last_start or not last_end:
            raise Exception("No se encontraron eventos en el último turno del usuario")

        start_time = last_start[0]
        end_time = last_end[0]

        print(f"🔍 Usuario: {user_name}")
        print(f"   Último Start shift → {last_start}")
        print(f"   Último End of shift → {last_end}")
        print(f"   ⏱️ Rango usado: {start_time} → {end_time}")

        # --- Obtener eventos del turno ---
        cur.execute("""
            SELECT e.ID_Eventos, e. , e.Nombre_Actividad, e.Cantidad, e.Camera, e.Descripcion
            FROM Eventos e
            INNER JOIN user u ON e.ID_Usuario = u.ID_Usuario
            WHERE u.Nombre_Usuario = %s
            AND e.  BETWEEN %s AND %s
            ORDER BY e. 
        """, (user_name, start_time, end_time))

        rows = cur.fetchall()
        if not rows:
            raise Exception("No se encontraron eventos en el rango del turno.")

        print(f"   📂 Eventos encontrados: {len(rows)}")

        # --- Convertir rows a lista de diccionarios ---
        columns = [column[0] for column in cur.description]  # nombres de columnas
        data = [dict(zip(columns, row)) for row in rows]     # lista de dicts

        df = pd.DataFrame(data)

        # --- Exportar ---
        file_path = f"{output_folder}\\{user_name}_{start_time:%Y-%m-%d}.xlsx"
        df.to_excel(file_path, index=False)

        print(f"✅ Exportado en: {file_path}")
        return file_path

    except Exception as e:
        print(f"❌ No se pudo exportar: {e}")
        return None

def get_cover_stats(username=None, fecha=None, station=None, role=None, session_id=None):
    """
    Consulta la tabla 'Covers' en MySQL y retorna estadísticas de covers.

    Args:
        username (str, optional): Nombre del usuario a filtrar.
        fecha (str|datetime, optional): Fecha específica (YYYY-MM-DD) o datetime.
        station (str, optional): Ignorado si se pasa; aceptado para compatibilidad.
        role (str, optional): Ignorado si se pasa; aceptado para compatibilidad.
        session_id (any, optional): Ignorado si se pasa; aceptado para compatibilidad.

    Nota:
        Se aceptan parámetros adicionales (station, role, session_id) únicamente para
        compatibilidad con llamadas existentes desde la UI. No afectan el cálculo.

    Returns:
        dict: {
            'total_covers': int,        # cantidad de veces que salió a cover
            'tiempo_total': timedelta,  # tiempo total acumulado con cover_out
            'detalles': list[dict]      # detalles por cover
        }
    """
    try:
        conn = get_connection()
        cur = conn.cursor()

        query = "SELECT ID_Covers, Nombre_Usuarios, Cover_in, Cover_out, Motivo, Covered_by FROM Covers WHERE 1=1"
        params = []

        if username:
            query += " AND Nombre_Usuarios = %s"
            params.append(username)

        # Filtro por fecha (rango del día de 'fecha' en Cover_in)
        if fecha:
            fecha_dt = None
            if isinstance(fecha, str):
                try:
                    fecha_dt = datetime.strptime(fecha.strip()[:10], "%Y-%m-%d")
                except Exception:
                    try:
                        fecha_dt = datetime.fromisoformat(fecha.strip())
                    except Exception:
                        fecha_dt = None
            elif isinstance(fecha, datetime):
                fecha_dt = fecha

            if fecha_dt:
                inicio = datetime(fecha_dt.year, fecha_dt.month, fecha_dt.day)
                fin = inicio + timedelta(days=1)
                query += " AND Cover_in >= %s AND Cover_in < %s"
                params.extend([inicio, fin])

        query += " ORDER BY Cover_in DESC"

        cur.execute(query, tuple(params))
        rows = cur.fetchall()

        total_covers = len(rows)
        tiempo_total = timedelta()
        detalles = []

        def to_dt(val):
            if isinstance(val, datetime):
                return val
            if isinstance(val, str):
                try:
                    return datetime.strptime(val[:19], "%Y-%m-%d %H:%M:%S")
                except Exception:
                    return None
            return None

        for (id_cover, usuario, cover_in, cover_out, motivo, covered_by) in rows:
            ci = to_dt(cover_in) or cover_in
            co = to_dt(cover_out) or cover_out
            duracion = None
            try:
                if isinstance(ci, datetime) and isinstance(co, datetime):
                    duracion = co - ci
                    tiempo_total += duracion
            except Exception:
                pass

            detalles.append({
                'id': id_cover,
                'usuario': usuario,
                'cover_in': ci,
                'cover_out': co,
                'motivo': motivo,
                'duracion': duracion,
                'covered_by': covered_by
            })

        cur.close()
        conn.close()

        return {
            'total_covers': total_covers,
            'tiempo_total': tiempo_total,
            'detalles': detalles
        }
    except Exception as e:
        print(f"[ERROR] get_cover_stats: {e}")
        traceback.print_exc()
        return {
            'total_covers': 0,
            'tiempo_total': timedelta(),
            'detalles': []
        }


def get_covers_in_range(username, start_dt, end_dt):
    """Obtiene covers para un usuario en el rango [start_dt, end_dt), calculando duración.

    Returns (detalles, total_count, total_duration)
    detalles: list[dict] con claves: id, usuario, cover_in, cover_out, motivo, duracion
    """
    try:
        conn = get_connection()
        cur = conn.cursor()
        sql = (
            "SELECT ID_Covers, Nombre_Usuarios, Cover_in, Cover_out, Motivo, Covered_by "
            "FROM Covers WHERE Nombre_Usuarios = %s AND Cover_in >= %s AND Cover_in < %s "
            "ORDER BY Cover_in ASC"
        )
        cur.execute(sql, (username, start_dt, end_dt))
        rows = cur.fetchall()
        cur.close(); conn.close()

        def to_dt(val):
            if isinstance(val, datetime):
                return val
            if isinstance(val, str):
                for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
                    try:
                        return datetime.strptime(val[:19], fmt)
                    except Exception:
                        pass
            return None

        detalles = []
        total_duration = timedelta()
        for (idc, usr, ci, co, motivo, covered_by) in rows:
            ci_dt = to_dt(ci) or ci
            co_dt = to_dt(co) or co
            dur = None
            if isinstance(ci_dt, datetime) and isinstance(co_dt, datetime):
                try:
                    dur = co_dt - ci_dt
                    if dur.total_seconds() >= 0:
                        total_duration += dur
                except Exception:
                    pass
            detalles.append({
                'id': idc,
                'usuario': usr,
                'cover_in': ci_dt,
                'cover_out': co_dt,
                'motivo': motivo,
                'covered_by': covered_by,
                'duracion': dur,
            })
        return detalles, len(rows), total_duration
    except Exception as e:
        print(f"[ERROR] get_covers_in_range: {e}")
        traceback.print_exc()
        return [], 0, timedelta()


def open_cover_stats_window(parent=None):
    """Ventana para consultar y exportar covers por operador y fecha (día/semana/mes), usando CustomTkinter si está disponible."""
    ex = _focus_singleton('cover_stats')
    if ex:
        return ex

    # Intentar usar CustomTkinter para UI moderna
    UI = None
    try:
        import importlib
        ctk = importlib.import_module('customtkinter')
        try:
            ctk.set_appearance_mode("dark")
            ctk.set_default_color_theme("dark-blue")
        except Exception:
            pass
        UI = ctk
    except Exception:
        UI = None

    win = (UI.CTkToplevel(parent if parent is not None else None)
           if UI is not None else tk.Toplevel(parent if parent is not None else None))
    win.title("Covers - Reporte por Operador")
    win.geometry("860x520")
    try:
        if UI is None:
            win.configure(bg="#2c2f33")
        else:
            win.configure(fg_color="#2c2f33")
    except Exception:
        pass
    win.resizable(True, True)

    # Header
    try:
        if UI is not None:
            UI.CTkLabel(win, text="Covers - Reporte", text_color="#00bfae", font=("Segoe UI", 16, "bold")).pack(pady=(10,6))
        else:
            tk.Label(win, text="Covers - Reporte", bg="#2c2f33", fg="#00bfae", font=("Segoe UI", 16, "bold")).pack(pady=(10,6))
    except Exception:
        pass

    # Filtros
    filt = (UI.CTkFrame(win, fg_color="#2c2f33") if UI is not None else tk.Frame(win, bg="#2c2f33"));
    filt.pack(fill="x", padx=12, pady=(0,8))
    if UI is not None:
        UI.CTkLabel(filt, text="Operador:", text_color="#c9d1d9").grid(row=0, column=0, sticky="w", padx=6, pady=6)
    else:
        tk.Label(filt, text="Operador:", bg=filt['bg'], fg="#c9d1d9").grid(row=0, column=0, sticky="w", padx=6, pady=6)
    user_var = tk.StringVar()
    try:
        conn = get_connection(); cur = conn.cursor()
        cur.execute("SELECT `Nombre_Usuario` FROM `user` ORDER BY `Nombre_Usuario`")
        users = [r[0] for r in cur.fetchall()]
        cur.close(); conn.close()
    except Exception:
        users = []
    try:
        user_cb = under_super.FilteredCombobox(filt, textvariable=user_var, values=users, width=30)
    except Exception:
        user_cb = ttk.Combobox(filt, textvariable=user_var, values=users, width=30)
    user_cb.grid(row=0, column=1, sticky="w", padx=6)

    if UI is not None:
        UI.CTkLabel(filt, text="Fecha:", text_color="#c9d1d9").grid(row=0, column=2, sticky="w", padx=6, pady=6)
    else:
        tk.Label(filt, text="Fecha:", bg=filt['bg'], fg="#c9d1d9").grid(row=0, column=2, sticky="w", padx=6, pady=6)
    # Date picker (tkcalendar) con fallback
    fecha_var = tk.StringVar()
    date_widget = None
    try:
        import importlib
        tkc = importlib.import_module("tkcalendar")
        DateEntry = getattr(tkc, "DateEntry", None)
        if DateEntry is not None:
            date_widget = DateEntry(
                filt, width=14, background="#14414e", foreground="#ffffff",
                borderwidth=0, date_pattern='yyyy-mm-dd'
            )
            date_widget.grid(row=0, column=3, sticky="w", padx=6)
            # Mantener fecha_var sincronizada para compatibilidad
            def _sync_date(*_):
                try:
                    d = date_widget.get_date()
                    fecha_var.set(d.strftime('%Y-%m-%d'))
                except Exception:
                    pass
            date_widget.bind("<<DateEntrySelected>>", _sync_date)
            _sync_date()
    except Exception:
        pass
    if date_widget is None:
        if UI is not None:
            UI.CTkEntry(filt, textvariable=fecha_var, width=120).grid(row=0, column=3, sticky="w", padx=6)
        else:
            tk.Entry(filt, textvariable=fecha_var, width=16).grid(row=0, column=3, sticky="w", padx=6)

    # Botones
    btns = (UI.CTkFrame(filt, fg_color="#2c2f33") if UI is not None else tk.Frame(filt, bg=filt['bg']))
    btns.grid(row=0, column=4, sticky="e", padx=6)
    # Summary
    if UI is not None:
        summary = UI.CTkLabel(win, text="Covers: 0 | Tiempo total: 00:00:00", text_color="#a3c9f9", font=("Segoe UI", 11, "bold"))
    else:
        summary = tk.Label(win, text="Covers: 0 | Tiempo total: 00:00:00", bg="#2c2f33", fg="#a3c9f9", font=("Segoe UI", 11, "bold"))
    summary.pack(pady=(0,6))

    # Estilo moderno
    style = ttk.Style(win)
    style_name = f"CoverStats_{id(win)}"
    style.configure(
        f"{style_name}.Treeview",
        background="#23272a", foreground="#e0e0e0", fieldbackground="#23272a",
        rowheight=26, bordercolor="#23272a", borderwidth=0
    )
    style.configure(
        f"{style_name}.Treeview.Heading",
        background="#23272a", foreground="#a3c9f9",
        font=("Segoe UI", 10, "bold")
    )
    style.map(f"{style_name}.Treeview", background=[("selected", "#4a90e2")], foreground=[("selected", "#fff")])

    # Tabla: intentar tksheet con fallback a Treeview
    cols = ("Cover_in", "Cover_out", "Duración", "Motivo", "Covered_by")
    use_sheet = False
    sheet = None
    try:
        import importlib
        Sheet = importlib.import_module('tksheet').Sheet
        use_sheet = True
    except Exception:
        use_sheet = False

    frame = (UI.CTkFrame(win, fg_color="#2c2f33") if UI is not None else tk.Frame(win, bg="#2c2f33")); frame.pack(expand=True, fill="both", padx=12, pady=(2,10))
    tree = None
    if use_sheet:
        sheet = Sheet(frame, headers=list(cols))
        sheet.enable_bindings((
            "single_select",
            "row_select",
            "column_select",
            "arrowkeys",
            "right_click_popup_menu",
            "rc_select",
            "copy",
            "select_all",
            "column_width_resize",
            "double_click_column_resize",
            "row_height_resize",
        ))
        sheet.grid(row=0, column=0, sticky="nsew")
        try:
            frame.grid_rowconfigure(0, weight=1)
            frame.grid_columnconfigure(0, weight=1)
            sheet.set_options(
                header_bg="#23272a",
                header_fg="#a3c9f9",
                header_border_fg="#3a3f44",
                index_bg="#23272a",
                index_fg="#a3c9f9",
                index_border_fg="#3a3f44",
                top_left_bg="#23272a",
                top_left_fg="#a3c9f9",
                table_bg="#2c2f33",
                table_fg="#e0e0e0",
                table_grid_fg="#3a3f44",
                header_selected_cells_bg="#4a90e2",
                header_selected_cells_fg="#ffffff",
                selected_rows_bg="#14414e",
                selected_rows_fg="#ffffff",
                selected_columns_bg="#14414e",
                selected_columns_fg="#ffffff",
            )
        except Exception:
            pass
    else:
        yscroll = tk.Scrollbar(frame, orient="vertical"); yscroll.pack(side="right", fill="y")
        xscroll = tk.Scrollbar(frame, orient="horizontal"); xscroll.pack(side="bottom", fill="x")
        tree = ttk.Treeview(frame, columns=cols, show="headings", yscrollcommand=yscroll.set, xscrollcommand=xscroll.set, style=f"{style_name}.Treeview")
        yscroll.config(command=tree.yview); xscroll.config(command=tree.xview)
        for c in cols:
            tree.heading(c, text=c)
            default_w = 160
            if c == "Motivo":
                default_w = 220
            if c == "Covered_by":
                default_w = 140
            tree.column(c, width=default_w, anchor="w")
        tree.pack(expand=True, fill="both")

    def parse_date(s):
        s = (s or "").strip()
        if not s:
            return None
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%Y/%m/%d"):
            try:
                return datetime.strptime(s, fmt)
            except Exception:
                pass
        try:
            return datetime.fromisoformat(s)
        except Exception:
            return None

    def fmt_dt(v):
        if isinstance(v, datetime):
            return v.strftime("%Y-%m-%d %H:%M:%S")
        return str(v) if v is not None else ""

    def fmt_td(td):
        if not isinstance(td, timedelta):
            return ""
        total = int(td.total_seconds())
        h = total // 3600; m = (total % 3600) // 60; s = total % 60
        return f"{h:02d}:{m:02d}:{s:02d}"

    def refresh_day():
        uname = user_var.get().strip()
        dt = None
        if date_widget is not None:
            try:
                d = date_widget.get_date()
                dt = datetime(d.year, d.month, d.day)
            except Exception:
                dt = None
        if dt is None:
            dt = parse_date(fecha_var.get())
        if not uname or not dt:
            messagebox.showwarning("Faltan datos", "Seleccione operador y fecha válida (YYYY-MM-DD)", parent=win)
            return
        stats = get_cover_stats(uname, dt)
        if use_sheet and sheet is not None:
            rows = []
            for d in stats['detalles']:
                rows.append([
                    fmt_dt(d['cover_in']),
                    fmt_dt(d['cover_out']),
                    fmt_td(d['duracion']),
                    d['motivo'] or "",
                    d.get('covered_by') or "",
                ])
            try:
                sheet.set_sheet_data(rows)
            except Exception:
                pass
        else:
            tree.delete(*tree.get_children())
            for d in stats['detalles']:
                tree.insert(
                    "", "end",
                    values=(
                        fmt_dt(d['cover_in']),
                        fmt_dt(d['cover_out']),
                        fmt_td(d['duracion']),
                        d['motivo'] or "",
                        d.get('covered_by') or ""
                    )
                )
        # CTk widgets don't implement .config(); use .configure() which works for both Tk and CTk
        try:
            summary.configure(text=f"Covers: {stats['total_covers']} | Tiempo total: {fmt_td(stats['tiempo_total'])}")
        except Exception:
            summary.config(text=f"Covers: {stats['total_covers']} | Tiempo total: {fmt_td(stats['tiempo_total'])}")

    def ask_save_default(default_name):
        return filedialog.asksaveasfilename(parent=win, defaultextension='.xlsx', initialfile=default_name,
                                            filetypes=[('Excel files','*.xlsx'), ('All files','*.*')],
                                            title='Guardar reporte')

    def export_range(kind):
        # kind in ("day","week","month")
        uname = user_var.get().strip()
        dt = parse_date(fecha_var.get())
        if not uname or not dt:
            messagebox.showwarning("Faltan datos", "Seleccione operador y fecha válida (YYYY-MM-DD)", parent=win)
            return
        if kind == "day":
            start = datetime(dt.year, dt.month, dt.day); end = start + timedelta(days=1)
            default_name = f"covers_{uname}_{start:%Y-%m-%d}.xlsx"
        elif kind == "week":
            monday = dt - timedelta(days=dt.weekday())
            start = datetime(monday.year, monday.month, monday.day)
            end = start + timedelta(days=7)
            default_name = f"covers_{uname}_week_{start:%Y-%m-%d}.xlsx"
        else:  # month
            first = datetime(dt.year, dt.month, 1)
            if dt.month == 12:
                next_first = datetime(dt.year + 1, 1, 1)
            else:
                next_first = datetime(dt.year, dt.month + 1, 1)
            start, end = first, next_first
            default_name = f"covers_{uname}_{start:%Y-%m}.xlsx"

        detalles, total_count, total_dur = get_covers_in_range(uname, start, end)
        # Convertir a DataFrame y exportar
        try:
            import pandas as pd
        except Exception as e:
            messagebox.showerror("Dependencia faltante", f"Se requiere pandas para exportar a Excel.\n{e}", parent=win)
            return

        rows = []
        for d in detalles:
            rows.append({
                "Usuario": d['usuario'],
                "Cover_in": fmt_dt(d['cover_in']),
                "Cover_out": fmt_dt(d['cover_out']),
                "Duracion": fmt_td(d['duracion']),
                "Motivo": d['motivo'] or "",
                "Covered_by": d.get('covered_by') or "",
            })
        df = pd.DataFrame(rows)

        fname = ask_save_default(default_name)
        if not fname:
            return
        try:
            with pd.ExcelWriter(fname) as writer:
                df.to_excel(writer, index=False, sheet_name="Covers")
                # Hoja Resumen
                res = pd.DataFrame([
                    {"Usuario": uname, "Desde": start.strftime('%Y-%m-%d %H:%M:%S'), "Hasta": end.strftime('%Y-%m-%d %H:%M:%S'),
                     "Total registros": total_count, "Tiempo total": fmt_td(total_dur)}
                ])
                res.to_excel(writer, index=False, sheet_name="Resumen")
            messagebox.showinfo("Exportar", f"Reporte guardado en\n{fname}", parent=win)
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo exportar:\n{e}", parent=win)

    # Botones acciones
    if UI is not None:
        UI.CTkButton(btns, text="Buscar", fg_color="#13988e", hover_color="#0f7f76", command=refresh_day).pack(side="left", padx=(0,6))
        UI.CTkButton(btns, text="Reporte (Día)", fg_color="#3b4754", hover_color="#4a5560", command=lambda: export_range("day")).pack(side="left", padx=4)
        UI.CTkButton(btns, text="Reporte Semana", fg_color="#3b4754", hover_color="#4a5560", command=lambda: export_range("week")).pack(side="left", padx=4)
        UI.CTkButton(btns, text="Reporte Mes", fg_color="#3b4754", hover_color="#4a5560", command=lambda: export_range("month")).pack(side="left", padx=4)
    else:
        tk.Button(btns, text="Buscar", bg="#13988e", fg="#fff", command=refresh_day).pack(side="left", padx=(0,6))
        tk.Button(btns, text="Reporte (Día)", bg="#3b4754", fg="#e0e0e0", command=lambda: export_range("day")).pack(side="left", padx=4)
        tk.Button(btns, text="Reporte Semana", bg="#3b4754", fg="#e0e0e0", command=lambda: export_range("week")).pack(side="left", padx=4)
        tk.Button(btns, text="Reporte Mes", bg="#3b4754", fg="#e0e0e0", command=lambda: export_range("month")).pack(side="left", padx=4)

    win.transient(parent)
    win.grab_set()
    try:
        win.focus_force()
    except Exception:
        pass
    _register_singleton('cover_stats', win)
    return win


def show_map():
    """Muestra un mapa en vivo basado en un PDF (en la carpeta de íconos) y superpone
    labels con el usuario logeado en cada estación. Registra movimientos y cambios de cover
    en un log CSV en la misma carpeta.

    Requiere PyMuPDF (fitz) para renderizar el PDF. Si no está disponible, muestra fallback.
    """
    import os
    import re
    from datetime import datetime as dt
    try:
        import importlib
        fitz = importlib.import_module("fitz")  # PyMuPDF
    except Exception:
        fitz = None

    try:
        from PIL import Image, ImageTk
        from tkinter import font as tkfont

    except Exception:
        Image = None
        ImageTk = None

    ex = _focus_singleton('map')
    if ex:
        return ex
    win = tk.Toplevel()
    win.title("Mapa de Estaciones (PDF)")
    win.configure(bg="#2c2f33")

    # Buscar un PDF en la carpeta de íconos definida en under_super.ICON_PATH
    pdf_path = None
    try:
        icon_dir = under_super.ICON_PATH
        pdfs = [f for f in os.listdir(icon_dir) if f.lower().endswith(".pdf")]
        # preferir uno que contenga 'map' en el nombre
        candidates = sorted(pdfs, key=lambda n: ("map" not in n.lower(), n.lower()))
        if candidates:
            pdf_path = os.path.join(icon_dir, candidates[0])
    except Exception:
        pdf_path = None

    frame = tk.Frame(win, bg="#2c2f33")
    frame.pack(expand=True, fill="both")
    canvas = tk.Canvas(frame, highlightthickness=0, bg="#23272a")
    canvas.pack(expand=True, fill="both")

    if fitz is None or Image is None or ImageTk is None or not pdf_path or not os.path.exists(pdf_path):
        tk.Label(win, text=(
            "No se pudo cargar el mapa PDF.\n"
            "Instala 'PyMuPDF' (fitz) y 'Pillow', o verifica el PDF en la carpeta de íconos."
        ), bg="#2c2f33", fg="#f9a3a3").pack(padx=12, pady=12)
        return

    # Renderizar la primera página del PDF a imagen
    try:
        doc = fitz.open(pdf_path)
        page = doc[0]
        zoom = 2.0
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat, alpha=False)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

        # Escalar imagen para que quepa en pantalla (sin exceder márgenes)
        try:
            sw = win.winfo_screenwidth(); sh = win.winfo_screenheight()
        except Exception:
            sw, sh = 1366, 768
        # Márgenes (pixeles) para no pegar a los bordes y dejar espacio a título/bordes
        margin_w, margin_h = 80, 160
        max_w = max(320, int(sw - margin_w))
        max_h = max(240, int(sh - margin_h))
        scale_img = min(max_w / pix.width, max_h / pix.height, 1.0)

        disp_w = int(pix.width * scale_img)
        disp_h = int(pix.height * scale_img)

        if scale_img < 1.0:
            img_disp = img.resize((disp_w, disp_h), Image.LANCZOS)
        else:
            img_disp = img

        bg_img = ImageTk.PhotoImage(img_disp)
        bg_item = canvas.create_image(0, 0, anchor="nw", image=bg_img)
        canvas.bg_img_ref = bg_img  # evitar GC
        canvas.config(width=disp_w, height=disp_h, scrollregion=(0,0,disp_w,disp_h))
        # Sugerir tamaño de ventana acorde (sin exceder pantalla)
        try:
            win.geometry(f"{min(disp_w+20, max_w)}x{min(disp_h+80, max_h)}")
        except Exception:
            pass
    except Exception as e:
        tk.Label(win, text=f"Error al renderizar PDF: {e}", bg="#2c2f33", fg="#f9a3a3").pack(padx=12, pady=12)
        return

    # Extraer posiciones de texto de estaciones desde el PDF
    station_pos = {}  # id_estacion(int) -> (x_px, y_px)
    try:
        text_dict = page.get_text("dict")
        num_re = re.compile(r"^\d{1,3}$")
        for block in text_dict.get("blocks", []):
            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    txt = (span.get("text") or "").strip()
                    if num_re.match(txt):
                        sid = int(txt)
                        x0, y0, x1, y1 = span.get("bbox", (0,0,0,0))
                        # convertir puntos a pixeles aplicando el mismo zoom
                        cx = ((x0 + x1) / 2.0) * zoom
                        cy = ((y0 + y1) / 2.0) * zoom
                        # Registrar la primera ocurrencia del número como ancla
                        if sid not in station_pos:
                            station_pos[sid] = (cx, cy)
    except Exception:
        station_pos = {}

    # Fallback si no se detectaron posiciones desde el PDF
    if not station_pos:
        # Usar un conjunto mínimo de posiciones relativas como respaldo
        station_pos = {
            1: (90, 620), 2: (140, 620), 3: (190, 620), 11: (240, 550),
            12:(190, 550), 13:(140, 550), 14:(90, 550), 15:(40, 550),
            25:(500, 200), 26:(550, 200), 27:(500, 260), 28:(550, 260),
            29:(600, 260), 30:(650, 200), 31:(700, 200), 32:(750, 200),
            33:(700, 260), 34:(750, 260), 35:(800, 260), 36:(850, 200),
            37:(1000, 550), 38:(1050, 550), 39:(1100, 550), 40:(1150, 550),
            41:(1100, 620), 42:(1050, 620), 43:(1000, 620), 44:(950, 620),
            9:(850, 100), 10:(900, 100),
        }

    # Factor de escala aplicado a la imagen para ajustar posiciones de labels
    try:
        final_scale = scale_img
    except Exception:
        final_scale = 1.0

    # Crear labels en posiciones detectadas
    labels = {}
    for sid, (x, y) in station_pos.items():
        # Ajustar por la escala de visualización
        dx = int(x * final_scale)
        dy = int(y * final_scale)
        lbl = tk.Label(win, text="Libre", bg="#f0f0f0", fg="#5f6a75", font=("Segoe UI", 9, "bold"))
        lbl.place(x=dx, y=dy)
        labels[sid] = lbl

    # Archivo de log
    log_path = os.path.join(under_super.ICON_PATH, "station_activity_log.csv")
    if not os.path.exists(log_path):
        try:
            with open(log_path, "w", encoding="utf-8") as f:
                f.write("timestamp,event,user,from_station,to_station,details\n")
        except Exception:
            pass

    # Estado previo para detectar movimientos y cambios de cover
    prev_user_station = {}   # user -> station_id
    prev_cover_users = set() # usuarios actualmente en cover

    def write_log(event, user, from_st, to_st, details=""):
        try:
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(f"{dt.now().isoformat(timespec='seconds')},{event},{user},{from_st},{to_st},{details}\n")
        except Exception:
            pass

    def fetch_status():
        """Obtiene mapeo station_id->user y set de usuarios en cover (Activo=-1)."""
        station_map = {}
        cover_set = set()
        try:
            conn =  get_connection()
            cur = conn.cursor()
            cur.execute("SELECT Station_Number, User_Logged FROM Estaciones")
            for sid, user in cur.fetchall():
                try:
                    sid_int = int(sid)
                except Exception:
                    continue
                station_map[sid_int] = user
            # usuarios en cover activos
            try:
                cur.execute("SELECT Nombre_Usuarios FROM Covers WHERE Activo = -1")
                cover_set = {r[0] for r in cur.fetchall()}
            except Exception:
                cover_set = set()
            cur.close(); conn.close()
        except Exception:
            pass
        return station_map, cover_set

    def refrescar():
        nonlocal prev_user_station, prev_cover_users
        station_map, cover_set = fetch_status()

        # Actualizar labels por estación
        for sid, lbl in labels.items():
            user = station_map.get(sid)
            if user and str(user).strip():
                # color especial si está en cover
                in_cover = user in cover_set
                lbl.config(text=str(user), fg=("#f0ad4e" if in_cover else "#12c48b"), bg="#23272a")
            else:
                lbl.config(text="Libre", fg="#68727e", bg="#2c2f33")

        # Detectar movimientos (cambios de estación por usuario)
        current_user_station = {}
        for s, u in station_map.items():
            if u and str(u).strip():
                current_user_station[u] = s

        # Movimientos
        for user, new_s in current_user_station.items():
            old_s = prev_user_station.get(user)
            if old_s is not None and old_s != new_s:
                write_log("move", user, old_s, new_s, "user moved station")
        # Covers in/out
        entered_cover = cover_set - prev_cover_users
        exited_cover = prev_cover_users - cover_set
        for u in entered_cover:
            s = current_user_station.get(u, prev_user_station.get(u, ""))
            write_log("cover_in", u, s, s, "usuario entró a cover")
        for u in exited_cover:
            s = current_user_station.get(u, prev_user_station.get(u, ""))
            write_log("cover_out", u, s, s, "usuario salió de cover")

        prev_user_station = current_user_station
        prev_cover_users = cover_set

        win.after(4000, refrescar)

    _register_singleton('map', win)


# ============================================================================
# SISTEMA DE BACKUP/RESTAURACIÓN (PAPELERA)
# ============================================================================
# IMPORTANTE: Si tienes FOREIGN KEYS en la BD, ejecuta este SQL primero:
# 
# -- Para permitir borrados seguros (mover a papelera sin romper FKs)
# ALTER TABLE Eventos DROP FOREIGN KEY IF EXISTS fk_eventos_sitio;
# ALTER TABLE Eventos DROP FOREIGN KEY IF EXISTS fk_eventos_usuario;
# ALTER TABLE Eventos DROP FOREIGN KEY IF EXISTS fk_eventos_actividad;
# ALTER TABLE Covers DROP FOREIGN KEY IF EXISTS fk_covers_usuario;
# ALTER TABLE Covers DROP FOREIGN KEY IF EXISTS fk_covers_motivo;
# ALTER TABLE Sesiones DROP FOREIGN KEY IF EXISTS fk_sesiones_usuario;
# ALTER TABLE specials DROP FOREIGN KEY IF EXISTS fk_specials_sitio;
#
# O alternativamente, cambiar a ON DELETE CASCADE:
# ALTER TABLE Eventos 
#   ADD CONSTRAINT fk_eventos_sitio 
#   FOREIGN KEY (ID_Sitio) REFERENCES Sitios(ID_Sitio) 
#   ON DELETE SET NULL ON UPDATE CASCADE;
# ============================================================================

def create_backup_tables():
    """Crea tablas de respaldo para cada tabla principal con sufijo _deleted"""
    try:
        conn = get_connection()
        cur = conn.cursor()
        
        # Tablas a respaldar
        tables = ['Eventos', 'Covers', 'Sesiones', 'Estaciones', 'specials']
        
        for table in tables:
            # Crear tabla de respaldo si no existe (copia estructura)
            cur.execute(f"CREATE TABLE IF NOT EXISTS `{table}_deleted` LIKE `{table}`")
            
            # Agregar columnas de auditoría si no existen
            try:
                cur.execute(f"""
                    ALTER TABLE `{table}_deleted`
                    ADD COLUMN `deleted_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    ADD COLUMN `deleted_by` VARCHAR(100),
                    ADD COLUMN `deletion_reason` TEXT
                """)
            except Exception:
                # Columnas ya existen, continuar
                pass
        
        conn.commit()
        cur.close()
        conn.close()
        print("✅ Tablas de backup creadas correctamente")
        return True
    except Exception as e:
        print(f"❌ create_backup_tables: {e}")
        traceback.print_exc()
        return False


def safe_delete(table_name, pk_column, pk_value, deleted_by, reason="Manual deletion"):
    """Borra un registro moviéndolo primero a la tabla _deleted
    
    Implementa soft-delete: copia el registro a *_deleted con metadata de auditoría,
    luego elimina el registro original.
    
    Args:
        table_name: Nombre de la tabla (ej: 'Eventos')
        pk_column: Nombre de la columna PK (ej: 'ID_Eventos')
        pk_value: Valor de la PK a borrar
        deleted_by: Usuario que borra
        reason: Motivo del borrado
    
    Returns:
        True si se borró correctamente, False si hubo error
    """
    print("=" * 80)
    print(f"🐛 DEBUG safe_delete()")
    print(f"   Tabla: {table_name}")
    print(f"   PK: {pk_column} = {pk_value}")
    print(f"   Usuario: {deleted_by}")
    print(f"   Razón: {reason}")
    print("=" * 80)
    
    try:
        conn = get_connection()
        cur = conn.cursor()
        
        # PASO 1: Verificar que el registro existe
        print(f"🔍 Verificando que existe el registro en {table_name}...")
        cur.execute(f"SELECT COUNT(*) FROM `{table_name}` WHERE `{pk_column}` = %s", (pk_value,))
        count = cur.fetchone()[0]
        print(f"   Registros encontrados: {count}")
        
        if count == 0:
            print(f"❌ El registro {pk_value} NO existe en {table_name}")
            cur.close()
            conn.close()
            return False
        
        # PASO 2: Copiar registro a tabla _deleted con metadatos
        print(f"📋 Copiando registro a {table_name}_deleted...")
        sql_insert = f"""
            INSERT INTO `{table_name}_deleted`
            SELECT *, NOW(), %s, %s
            FROM `{table_name}`
            WHERE `{pk_column}` = %s
        """
        print(f"   SQL: {sql_insert}")
        print(f"   Params: ({deleted_by}, {reason}, {pk_value})")
        
        cur.execute(sql_insert, (deleted_by, reason, pk_value))
        rows_inserted = cur.rowcount
        print(f"   ✅ Filas insertadas en {table_name}_deleted: {rows_inserted}")
        
        # PASO 3: Eliminar registro original
        print(f"🗑️ Eliminando registro original de {table_name}...")
        cur.execute(f"DELETE FROM `{table_name}` WHERE `{pk_column}` = %s", (pk_value,))
        rows_deleted = cur.rowcount
        print(f"   ✅ Filas eliminadas: {rows_deleted}")
        
        conn.commit()
        
        # PASO 4: Verificar que se insertó correctamente
        print(f"✅ Verificando inserción en {table_name}_deleted...")
        cur.execute(f"""
            SELECT {pk_column}, deleted_at, deleted_by, deletion_reason 
            FROM `{table_name}_deleted` 
            WHERE `{pk_column}` = %s
            ORDER BY deleted_at DESC LIMIT 1
        """, (pk_value,))
        
        backup_row = cur.fetchone()
        if backup_row:
            print(f"   ✅ BACKUP CONFIRMADO:")
            print(f"      PK: {backup_row[0]}")
            print(f"      Fecha: {backup_row[1]}")
            print(f"      Usuario: {backup_row[2]}")
            print(f"      Razón: {backup_row[3]}")
        else:
            print(f"   ❌ ERROR: No se encontró el backup en {table_name}_deleted")
        
        cur.close()
        conn.close()
        
        print(f"✅ Registro movido a Papelera correctamente")
        print(f"   Backup: {table_name}_deleted")
        print(f"   Original: ELIMINADO de {table_name}")
        print("=" * 80)
        return True
        
    except Exception as e:
        print(f"❌ ERROR en safe_delete: {e}")
        traceback.print_exc()
        try:
            conn.rollback()
        except:
            pass
        print("=" * 80)
        return False


def restore_deleted(table_name, pk_column, pk_value):
    """Restaura un registro desde la tabla _deleted
    
    Returns:
        True si se restauró, False si hubo error
    """
    try:
        conn = get_connection()
        cur = conn.cursor()
        
        # 1. Obtener columnas de la tabla original (sin las de audit)
        cur.execute(f"SHOW COLUMNS FROM `{table_name}`")
        original_cols = [row[0] for row in cur.fetchall()]
        cols_str = ", ".join(f"`{c}`" for c in original_cols)
        
        # 2. Copiar de _deleted a tabla original
        cur.execute(f"""
            INSERT INTO `{table_name}` ({cols_str})
            SELECT {cols_str}
            FROM `{table_name}_deleted`
            WHERE `{pk_column}` = %s
        """, (pk_value,))
        
        # 3. Borrar de _deleted
        cur.execute(f"DELETE FROM `{table_name}_deleted` WHERE `{pk_column}` = %s", (pk_value,))
        
        conn.commit()
        cur.close()
        conn.close()
        print(f"✅ Registro {pk_value} restaurado en {table_name}")
        return True
    except Exception as e:
        print(f"❌ restore_deleted: {e}")
        traceback.print_exc()
        try:
            conn.rollback()
        except:
            pass
        return False


def open_trash_window(parent=None):
    """Ventana para ver y restaurar registros borrados"""
    ex = _focus_singleton('trash')
    if ex:
        return ex
    
    # Intentar UI moderna
    UI = None
    try:
        import importlib

        ctk = importlib.import_module('customtkinter')
        try:
            ctk.set_appearance_mode("dark")
            ctk.set_default_color_theme("dark-blue")
        except Exception:
            pass
        UI = ctk
    except Exception:
        UI = None
    
    win = (UI.CTkToplevel(parent) if UI is not None else tk.Toplevel(parent))
    win.title("Papelera - Registros Borrados")
    win.geometry("1100x500")
    try:
        if UI is None:
            win.configure(bg="#2c2f33")
        else:
            win.configure(fg_color="#2c2f33")
    except:
        pass
    
    # Header
    if UI is not None:
        UI.CTkLabel(win, text="♻️ Papelera de Reciclaje", text_color="#f0ad4e", 
                   font=("Segoe UI", 18, "bold")).pack(pady=12)
    else:
        tk.Label(win, text="♻️ Papelera de Reciclaje", bg="#2c2f33", fg="#f0ad4e", 
                font=("Segoe UI", 16, "bold")).pack(pady=12)
    
    # Selector de tabla
    table_frame = (UI.CTkFrame(win, fg_color="#2c2f33") if UI is not None 
                   else tk.Frame(win, bg="#2c2f33"))
    table_frame.pack(fill="x", padx=12, pady=6)
    
    if UI is not None:
        UI.CTkLabel(table_frame, text="Tabla:", text_color="#e0e0e0").pack(side="left", padx=6)
    else:
        tk.Label(table_frame, text="Tabla:", bg="#2c2f33", fg="#e0e0e0").pack(side="left", padx=6)
    
    table_var = tk.StringVar(value="Eventos_deleted")
    tables = ["Eventos_deleted", "Covers_deleted", "Sesiones_deleted", "specials_deleted", "Estaciones_deleted"]
    
    try:
        table_cb = under_super.FilteredCombobox(table_frame, textvariable=table_var, 
                                               values=tables, state="readonly", width=25)
    except:
        table_cb = ttk.Combobox(table_frame, textvariable=table_var, values=tables, 
                               state="readonly", width=25)
    table_cb.pack(side="left", padx=6)
    
    # Treeview con scroll
    tree_frame = (UI.CTkFrame(win, fg_color="#2c2f33") if UI is not None 
                  else tk.Frame(win, bg="#2c2f33"))
    tree_frame.pack(expand=True, fill="both", padx=12, pady=6)
    
    yscroll = tk.Scrollbar(tree_frame, orient="vertical")
    yscroll.pack(side="right", fill="y")
    xscroll = tk.Scrollbar(tree_frame, orient="horizontal")
    xscroll.pack(side="bottom", fill="x")
    
    # Estilo oscuro
    style = ttk.Style()
    style.configure("Trash.Treeview",
                   background="#23272a", foreground="#e0e0e0",
                   fieldbackground="#23272a", rowheight=26)
    style.configure("Trash.Treeview.Heading",
                   background="#23272a", foreground="#a3c9f9",
                   font=("Segoe UI", 10, "bold"))
    style.map("Trash.Treeview", background=[("selected", "#4a90e2")], 
             foreground=[("selected", "#ffffff")])
    
    tree = ttk.Treeview(tree_frame, show="headings", 
                       yscrollcommand=yscroll.set, xscrollcommand=xscroll.set,
                       style="Trash.Treeview", selectmode="browse")
    yscroll.config(command=tree.yview)
    xscroll.config(command=tree.xview)
    tree.pack(expand=True, fill="both")
    
    def load_trash():
        table = table_var.get()
        tree.delete(*tree.get_children())
        try:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute(f"SELECT * FROM `{table}` ORDER BY deleted_at DESC LIMIT 500")
            rows = cur.fetchall()
            
            if rows:
                # Configurar columnas
                cols = [desc[0] for desc in cur.description]
                tree["columns"] = cols
                for c in cols:
                    tree.heading(c, text=c)
                    tree.column(c, width=120 if c not in ("Descripcion", "deletion_reason") else 200)
                
                # Insertar datos con alternancia de color
                for idx, row in enumerate(rows):
                    vals = [str(v) if v is not None else "" for v in row]
                    tag = "evenrow" if idx % 2 == 0 else "oddrow"
                    tree.insert("", "end", values=vals, tags=(tag,))
                
                tree.tag_configure("evenrow", background="#2f343a")
                tree.tag_configure("oddrow", background="#3a3f44")
            
            cur.close()
            conn.close()
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo cargar papelera:\n{e}", parent=win)
            traceback.print_exc()
    
    def restore_selected():
        sel = tree.selection()
        if not sel:
            messagebox.showwarning("Sin selección", "Selecciona un registro", parent=win)
            return
        
        table = table_var.get().replace("_deleted", "")
        vals = tree.item(sel[0], "values")
        if not vals:
            return
        
        # Determinar PK según tabla
        pk_map = {
            "Eventos": "ID_Eventos",
            "Covers": "ID_Covers",
            "Sesiones": "ID_Sesiones",
            "specials": "ID_special",
            "Estaciones": "Station_Number"
        }
        pk_col = pk_map.get(table, "ID")
        pk_val = vals[0]
        
        if messagebox.askyesno("Restaurar", f"¿Restaurar registro con {pk_col}={pk_val}?", parent=win):
            ok = restore_deleted(table, pk_col, pk_val)
            if ok:
                messagebox.showinfo("Éxito", "✅ Registro restaurado correctamente", parent=win)
                load_trash()
            else:
                messagebox.showerror("Error", "❌ No se pudo restaurar el registro", parent=win)
    
    def delete_permanent():
        sel = tree.selection()
        if not sel:
            messagebox.showwarning("Sin selección", "Selecciona un registro", parent=win)
            return
        
        if not messagebox.askyesno("⚠️ Eliminar permanentemente", 
                                   "Esto borrará el registro de forma IRREVERSIBLE.\n¿Continuar?", 
                                   parent=win):
            return
        
        table = table_var.get()
        vals = tree.item(sel[0], "values")
        pk_val = vals[0]
        
        try:
            conn = get_connection()
            cur = conn.cursor()
            
            # Determinar columna PK
            pk_map = {
                "Eventos_deleted": "ID_Eventos",
                "Covers_deleted": "ID_Covers",
                "Sesiones_deleted": "ID_Sesiones",
                "specials_deleted": "ID_special",
                "Estaciones_deleted": "Station_Number"
            }
            pk_col = pk_map.get(table, "ID")
            
            cur.execute(f"DELETE FROM `{table}` WHERE `{pk_col}` = %s", (pk_val,))
            conn.commit()
            cur.close()
            conn.close()
            
            messagebox.showinfo("Éxito", "Registro eliminado permanentemente", parent=win)
            load_trash()
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo eliminar:\n{e}", parent=win)
    
    # Botones
    btn_frame = (UI.CTkFrame(win, fg_color="#2c2f33") if UI is not None 
                 else tk.Frame(win, bg="#2c2f33"))
    btn_frame.pack(fill="x", padx=12, pady=6)
    
    if UI is not None:
        UI.CTkButton(btn_frame, text="🔄 Refrescar", fg_color="#4a90e2", 
                    command=load_trash).pack(side="left", padx=4)
        UI.CTkButton(btn_frame, text="♻️ Restaurar", fg_color="#5cb85c", 
                    command=restore_selected).pack(side="left", padx=4)
        UI.CTkButton(btn_frame, text="🗑️ Eliminar Permanente", fg_color="#d9534f", 
                    command=delete_permanent).pack(side="left", padx=4)
    else:
        tk.Button(btn_frame, text="🔄 Refrescar", bg="#4a90e2", fg="white", 
                 command=load_trash).pack(side="left", padx=4)
        tk.Button(btn_frame, text="♻️ Restaurar", bg="#5cb85c", fg="white", 
                 command=restore_selected).pack(side="left", padx=4)
        tk.Button(btn_frame, text="🗑️ Eliminar Permanente", bg="#d9534f", fg="white", 
                 command=delete_permanent).pack(side="left", padx=4)
    
    # Bind para cambio de tabla
    table_var.trace_add("write", lambda *_: load_trash())
    
    load_trash()
    _register_singleton('trash', win)
    win.transient(parent)
    win.grab_set()
    win.focus_force()