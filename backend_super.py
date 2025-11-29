import tkinter as tk
import csv
from datetime import datetime, timedelta
import json
from pathlib import Path
import re
from tkinter import ttk, messagebox, simpledialog, filedialog
from PIL import Image, ImageTk
from PIL import Image, ImageTk
import login
import json
import re
import traceback
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
import pandas as pd
import under_super
import tkcalendar
from tkinter import font as tkfont
import pymysql
import time
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
        conn = under_super.get_connection()
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
        conn = under_super.get_connection()
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
                conn = under_super.get_connection()
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
                
                conn = under_super.get_connection()
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
        conn = under_super.get_connection()
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
def open_hybrid_events_supervisor(username, session_id=None, station=None, root=None):
    """
    🚀 VENTANA HÍBRIDA PARA SUPERVISORES: Visualización de Specials
    
    Versión simplificada para supervisores que muestra solo los Specials enviados a ellos:
    - Visualización de specials del turno actual en tksheet
    - Botones: Start/End Shift, Refrescar, Eliminar
    - Marcas persistentes (Registrado, En Progreso)
    - Sin formulario de registro de eventos
    - Sin botones de Cover
    - Modo solo lectura con opciones de marcado
    """
    # Singleton
    ex = _focus_singleton('hybrid_events_supervisor')
    if ex:
        return ex

    # CustomTkinter setup
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

    # tksheet setup
    USE_SHEET = False
    SheetClass = None
    try:
        from tksheet import Sheet as _Sheet
        SheetClass = _Sheet
        USE_SHEET = True
    except Exception:
        messagebox.showerror("Error", "tksheet no está instalado.\nInstala con: pip install tksheet")
        return

    # Crear ventana principal
    if UI is not None:
        top = UI.CTkToplevel()
        top.configure(fg_color="#1e1e1e")
    else:
        top = tk.Toplevel()
        top.configure(bg="#1e1e1e")
    
    top.title(f"📊 Specials - {username}")
    top.geometry("1320x800")
    top.resizable(True, True)

    # Variables de estado
    row_data_cache = []  # Cache de datos
    row_ids = []  # IDs de specials
    auto_refresh_active = tk.BooleanVar(value=True)
    refresh_job = None

    # Columnas para SPECIALS
    columns_specials = ["ID", "Fecha Hora", "Sitio", "Actividad", "Cantidad", "Camera", "Descripcion", "Usuario", "TZ", "Marca"]
    columns = columns_specials
    
    # Anchos personalizados para SPECIALS
    custom_widths_specials = {
        "ID": 60,
        "Fecha Hora": 150,
        "Sitio": 220,
        "Actividad": 150,
        "Cantidad": 70,
        "Camera": 80,
        "Descripcion": 190,
        "Usuario": 100,
        "TZ": 90,
        "Marca": 180
    }
    custom_widths = custom_widths_specials

    # Header
    if UI is not None:
        header = UI.CTkFrame(top, fg_color="#23272a", corner_radius=0)
    else:
        header = tk.Frame(top, bg="#23272a")
    header.pack(fill="x", padx=0, pady=0)

    # ⭐ FUNCIÓN: Manejar Start/End Shift
    def handle_shift_button():
        """Maneja el click en el botón Start/End Shift"""
        try:
            is_start = Dinamic_button_Shift(username)
            
            if is_start:
                success = on_start_shift(username, parent_window=top)
                if success:
                    update_shift_button()
                    load_data()
            else:
                on_end_shift(username)
                update_shift_button()
                load_data()
            
        except Exception as e:
            messagebox.showerror("Error", f"Error al cambiar turno:\n{e}", parent=top)
            print(f"[ERROR] handle_shift_button: {e}")
            traceback.print_exc()
    
    def update_shift_button():
        """Actualiza el texto y color del botón según el estado del turno"""
        try:
            is_start = Dinamic_button_Shift(username)
            
            if is_start:
                if UI is not None:
                    shift_btn.configure(text="🚀 Start Shift", 
                                       fg_color="#00c853", 
                                       hover_color="#00a043")
                else:
                    shift_btn.configure(text="🚀 Start Shift", bg="#00c853")
            else:
                if UI is not None:
                    shift_btn.configure(text="🏁 End of Shift", 
                                       fg_color="#d32f2f", 
                                       hover_color="#b71c1c")
                else:
                    shift_btn.configure(text="🏁 End of Shift", bg="#d32f2f")
        except Exception as e:
            print(f"[ERROR] update_shift_button: {e}")

    if UI is not None:
        # ⭐ Botones Refrescar y Eliminar a la izquierda
        UI.CTkButton(header, text="🔄  Refrescar", command=lambda: load_data(),
                    fg_color="#4D6068", hover_color="#27a3e0", 
                    width=120, height=40,
                    font=("Segoe UI", 12, "bold")).pack(side="left", padx=(20, 5), pady=15)
        
        delete_btn_header = UI.CTkButton(header, text="🗑️ Eliminar", command=lambda: None,
                    fg_color="#d32f2f", hover_color="#b71c1c", 
                    width=120, height=40,
                    font=("Segoe UI", 12, "bold"))
        delete_btn_header.pack(side="left", padx=5, pady=15)
        
        # ⭐ INDICADOR DE STATUS CON DROPDOWN (a la derecha, antes del botón Shift)
        status_frame = UI.CTkFrame(header, fg_color="transparent")
        status_frame.pack(side="right", padx=(5, 10), pady=15)
        
        # Obtener status actual del usuario
        current_status_bd = under_super.get_user_status_bd(username)
        
        # Mapear el status a texto legible
        if current_status_bd == 1:
            status_text = "🟢 Disponible"
        elif current_status_bd == 0:
            status_text = "🟡 Ocupado"
        elif current_status_bd == -1:
            status_text = "🔴 No disponible"
        else:
            status_text = "⚪ Desconocido"
        
        status_label = UI.CTkLabel(status_frame, text=status_text, 
                                   font=("Segoe UI", 12, "bold"))
        status_label.pack(side="left", padx=(0, 8))
        
        btn_emoji_green = "🟢"
        btn_emoji_yellow = "🟡"
        btn_emoji_red = "🔴"
        
        def update_status_label(new_value):
            """Actualiza el label y el status en la BD"""
            under_super.set_new_status(new_value, username)
            # Actualizar el texto del label
            if new_value == 1:
                status_label.configure(text="🟢 Disponible")
            elif new_value == 2:
                status_label.configure(text="🟡 Ocupado")
            elif new_value == -1:
                status_label.configure(text="🔴 No disponible")
        
        status_btn_green = UI.CTkButton(status_frame, text=btn_emoji_green, command=lambda:(update_status_label(1), username),
                    fg_color="#00c853", hover_color="#00a043",
                    width=45, height=38,
                    font=("Segoe UI", 16, "bold"))
        status_btn_green.pack(side="left")    

        status_btn_yellow = UI.CTkButton(status_frame, text=btn_emoji_yellow, command=lambda: (update_status_label(2), username),
                    fg_color="#f5a623", hover_color="#e69515",
                    width=45, height=38,
                    font=("Segoe UI", 16, "bold"))
        status_btn_yellow.pack(side="left")

        status_btn_red = UI.CTkButton(status_frame, text=btn_emoji_red, command=lambda: (update_status_label(-1), username),
                    fg_color="#d32f2f", hover_color="#b71c1c",
                    width=45, height=38,
                    font=("Segoe UI", 16, "bold"))
        status_btn_red.pack(side="left")

        
        # ⭐ Botón Start/End Shift a la derecha
        shift_btn = UI.CTkButton(
            header, 
            text="🚀 Start Shift",
            command=handle_shift_button,
            width=160, 
            height=40,
            font=("Segoe UI", 14, "bold"),
            fg_color="#00c853",
            hover_color="#00a043"
        )
        shift_btn.pack(side="right", padx=(5, 20), pady=15)
    else:
        # Fallback Tkinter
        tk.Button(header, text="🔄 Refrescar", command=lambda: load_data(), 
                 bg="#666666", fg="white",
                 font=("Segoe UI", 12, "bold"), relief="flat",
                 width=12).pack(side="left", padx=(20, 5), pady=15)
        
        delete_btn_header = tk.Button(header, text="🗑️ Eliminar", command=lambda: None,
                 bg="#d32f2f", fg="white",
                 font=("Segoe UI", 12, "bold"), relief="flat",
                 width=12)
        delete_btn_header.pack(side="left", padx=5, pady=15)
        
        # ⭐ INDICADOR DE STATUS CON DROPDOWN (Tkinter fallback)
        status_frame = tk.Frame(header, bg="#23272a")
        status_frame.pack(side="right", padx=(5, 10), pady=15)
        
        current_status_value = get_user_status(username)

    
        
        shift_btn = tk.Button(
            header,
            text="🚀 Start Shift",
            command=handle_shift_button,
            bg="#00c853",
            fg="white",
            font=("Segoe UI", 12, "bold"),
            relief="flat",
            width=15
        )
        shift_btn.pack(side="right", padx=(5, 20), pady=15)
    
    # Actualizar botón al iniciar
    update_shift_button()

    # Separador
    try:
        ttk.Separator(top, orient="horizontal").pack(fill="x")
    except Exception:
        pass

    # ==================== MODO SELECTOR (Specials / Audit / Cover Time / Breaks / Rol de Cover) ====================
    current_mode = {'value': 'specials'}  # 'specials', 'audit', 'cover_time', 'breaks', 'rol_cover'
    
    if UI is not None:
        mode_frame = UI.CTkFrame(top, fg_color="#23272a", corner_radius=0, height=50)
    else:
        mode_frame = tk.Frame(top, bg="#23272a", height=50)
    mode_frame.pack(fill="x", padx=0, pady=0)
    mode_frame.pack_propagate(False)

    def switch_mode(new_mode):
        """Cambia entre modo Specials, Audit, Cover Time, Breaks y Rol de Cover"""
        current_mode['value'] = new_mode
        
        # Ocultar todos los contenedores
        specials_container.pack_forget()
        audit_container.pack_forget()
        cover_container.pack_forget()
        breaks_container.pack_forget()
        rol_cover_container.pack_forget()
        
        
        # Resetear colores de todos los botones
        inactive_color = "#3b4754"
        inactive_hover = "#4a5560"
        active_color = "#4a90e2"
        active_hover = "#357ABD"
        
        if UI is not None:
            btn_specials.configure(fg_color=inactive_color, hover_color=inactive_hover)
            btn_audit.configure(fg_color=inactive_color, hover_color=inactive_hover)
            btn_cover.configure(fg_color=inactive_color, hover_color=inactive_hover)
            btn_breaks.configure(fg_color=inactive_color, hover_color=inactive_hover)
            btn_rol_cover.configure(fg_color=inactive_color, hover_color=inactive_hover)
        else:
            btn_specials.configure(bg=inactive_color, activebackground=inactive_hover)
            btn_audit.configure(bg=inactive_color, activebackground=inactive_hover)
            btn_cover.configure(bg=inactive_color, activebackground=inactive_hover)
            btn_breaks.configure(bg=inactive_color, activebackground=inactive_hover)
            btn_rol_cover.configure(bg=inactive_color, activebackground=inactive_hover)
        
        # Mostrar contenedor activo y resaltar botón
        if new_mode == 'specials':
            specials_container.pack(fill="both", expand=True, padx=10, pady=10)
            if UI is not None:
                btn_specials.configure(fg_color=active_color, hover_color=active_hover)
            else:
                btn_specials.configure(bg=active_color, activebackground=active_hover)
            load_data()
        elif new_mode == 'audit':
            audit_container.pack(fill="both", expand=True, padx=10, pady=10)
            if UI is not None:
                btn_audit.configure(fg_color=active_color, hover_color=active_hover)
            else:
                btn_audit.configure(bg=active_color, activebackground=active_hover)
        elif new_mode == 'cover_time':
            cover_container.pack(fill="both", expand=True, padx=10, pady=10)
            if UI is not None:
                btn_cover.configure(fg_color=active_color, hover_color=active_hover)
            else:
                btn_cover.configure(bg=active_color, activebackground=active_hover)
        elif new_mode == 'breaks':
            breaks_container.pack(fill="both", expand=True, padx=10, pady=10)
            if UI is not None:
                btn_breaks.configure(fg_color=active_color, hover_color=active_hover)
            else:
                btn_breaks.configure(bg=active_color, activebackground=active_hover)
            refrescar_tabla_breaks()
        elif new_mode == 'rol_cover':
            rol_cover_container.pack(fill="both", expand=True, padx=10, pady=10)
            if UI is not None:
                btn_rol_cover.configure(fg_color=active_color, hover_color=active_hover)
            else:
                btn_rol_cover.configure(bg=active_color, activebackground=active_hover)
            refrescar_lista_operadores()

    # Botones de modo
    if UI is not None:
        btn_specials = UI.CTkButton(
            mode_frame, 
            text="📋 Specials", 
            command=lambda: switch_mode('specials'),
            fg_color="#4a90e2",
            hover_color="#357ABD",
            width=130,
            height=35,
            font=("Segoe UI", 12, "bold")
        )
        btn_specials.pack(side="left", padx=(20, 5), pady=8)
        
        btn_audit = UI.CTkButton(
            mode_frame, 
            text="📊 Audit", 
            command=lambda: switch_mode('audit'),
            fg_color="#3b4754",
            hover_color="#4a5560",
            width=130,
            height=35,
            font=("Segoe UI", 12, "bold")
        )
        btn_audit.pack(side="left", padx=5, pady=8)
        
        btn_cover = UI.CTkButton(
            mode_frame, 
            text="⏱️ Cover Time", 
            command=lambda: switch_mode('cover_time'),
            fg_color="#3b4754",
            hover_color="#4a5560",
            width=140,
            height=35,
            font=("Segoe UI", 12, "bold")
        )
        btn_cover.pack(side="left", padx=5, pady=8)
        
        btn_breaks = UI.CTkButton(
            mode_frame, 
            text="☕ Breaks", 
            command=lambda: switch_mode('breaks'),
            fg_color="#3b4754",
            hover_color="#4a5560",
            width=130,
            height=35,
            font=("Segoe UI", 12, "bold")
        )
        btn_breaks.pack(side="left", padx=5, pady=8)
        
        btn_rol_cover = UI.CTkButton(
            mode_frame, 
            text="🎭 Rol de Cover", 
            command=lambda: switch_mode('rol_cover'),
            fg_color="#3b4754",
            hover_color="#4a5560",
            width=150,
            height=35,
            font=("Segoe UI", 12, "bold")
        )
        btn_rol_cover.pack(side="left", padx=5, pady=8)
    else:
        btn_specials = tk.Button(
            mode_frame,
            text="📋 Specials",
            command=lambda: switch_mode('specials'),
            bg="#4a90e2",
            fg="white",
            activebackground="#357ABD",
            font=("Segoe UI", 12, "bold"),
            relief="flat",
            width=11
        )
        btn_specials.pack(side="left", padx=(20, 5), pady=8)
        
        btn_audit = tk.Button(
            mode_frame,
            text="📊 Audit",
            command=lambda: switch_mode('audit'),
            bg="#3b4754",
            fg="white",
            activebackground="#4a5560",
            font=("Segoe UI", 12, "bold"),
            relief="flat",
            width=11
        )
        btn_audit.pack(side="left", padx=5, pady=8)
        
        btn_cover = tk.Button(
            mode_frame,
            text="⏱️ Cover Time",
            command=lambda: switch_mode('cover_time'),
            bg="#3b4754",
            fg="white",
            activebackground="#4a5560",
            font=("Segoe UI", 12, "bold"),
            relief="flat",
            width=13
        )
        btn_cover.pack(side="left", padx=5, pady=8)
        
        btn_breaks = tk.Button(
            mode_frame,
            text="☕ Breaks",
            command=lambda: switch_mode('breaks'),
            bg="#3b4754",
            fg="white",
            activebackground="#4a5560",
            font=("Segoe UI", 12, "bold"),
            relief="flat",
            width=11
        )
        btn_breaks.pack(side="left", padx=5, pady=8)
        
        btn_rol_cover = tk.Button(
            mode_frame,
            text="🎭 Rol de Cover",
            command=lambda: switch_mode('rol_cover'),
            bg="#3b4754",
            fg="white",
            activebackground="#4a5560",
            font=("Segoe UI", 12, "bold"),
            relief="flat",
            width=14
        )
        btn_rol_cover.pack(side="left", padx=5, pady=8)

    # ==================== SPECIALS CONTAINER ====================
    if UI is not None:
        specials_container = UI.CTkFrame(top, fg_color="#2c2f33")
    else:
        specials_container = tk.Frame(top, bg="#2c2f33")
    specials_container.pack(fill="both", expand=True, padx=10, pady=10)

    # Frame para tksheet de Specials
    if UI is not None:
        sheet_frame = UI.CTkFrame(specials_container, fg_color="#2c2f33")
    else:
        sheet_frame = tk.Frame(specials_container, bg="#2c2f33")
    sheet_frame.pack(fill="both", expand=True)

    # Crear tksheet
    sheet = SheetClass(
        sheet_frame,
        headers=columns,
        theme="dark blue",
        height=600,
        width=1350,
        show_selected_cells_border=True,
        show_row_index=True,
        show_top_left=False,
        empty_horizontal=0,
        empty_vertical=0
    )
    # ⭐ DESHABILITAR EDICIÓN - Solo visualización y marcado
    sheet.enable_bindings([
        "single_select",
        "drag_select",
        "column_select",
        "row_select",
        "column_width_resize",
        "double_click_column_resize",
        "row_height_resize",
        "arrowkeys",
        "right_click_popup_menu",
        "rc_select",
        "copy"
    ])
    sheet.pack(fill="both", expand=True)
    sheet.change_theme("dark blue")

    # Frame para botones de marcado (debajo del sheet de Specials)
    if UI is not None:
        marks_frame = UI.CTkFrame(specials_container, fg_color="#23272a", corner_radius=0)
    else:
        marks_frame = tk.Frame(specials_container, bg="#23272a")
    marks_frame.pack(fill="x", padx=0, pady=(5, 0))

    def apply_sheet_widths():
        """Aplica anchos personalizados a las columnas"""
        for idx, col_name in enumerate(columns):
            if col_name in custom_widths:
                try:
                    sheet.column_width(idx, int(custom_widths[col_name]))
                except Exception:
                    try:
                        sheet.set_column_width(idx, int(custom_widths[col_name]))
                    except Exception:
                        pass
        sheet.redraw()

    def get_supervisor_shift_start():
        """Obtiene la última hora de inicio de shift del supervisor"""
        try:
            conn = under_super.get_connection()
            cur = conn.cursor()
            cur.execute("""
                SELECT e.FechaHora 
                FROM Eventos e
                INNER JOIN user u ON e.ID_Usuario = u.ID_Usuario
                WHERE u.Nombre_Usuario = %s AND e.Nombre_Actividad = %s
                ORDER BY e.FechaHora DESC
                LIMIT 1
            """, (username, "START SHIFT"))
            row = cur.fetchone()
            cur.close()
            conn.close()
            return row[0] if row and row[0] else None
        except Exception as e:
            print(f"[ERROR] get_supervisor_shift_start: {e}")
            return None

    def load_data():
        """Carga specials del supervisor desde el último START SHIFT hasta ahora"""
        nonlocal row_data_cache, row_ids, refresh_job
        
        try:
            shift_start = get_supervisor_shift_start()
            if not shift_start:
                data = [["No hay shift activo"] + [""] * (len(columns)-1)]
                sheet.set_sheet_data(data)
                apply_sheet_widths()
                row_data_cache.clear()
                row_ids.clear()
                return

            conn = under_super.get_connection()
            cur = conn.cursor()
            
            # Query: TODOS los specials del supervisor desde START SHIFT hasta AHORA
            sql = """
                SELECT ID_special, FechaHora, ID_Sitio, Nombre_Actividad, Cantidad, Camera,
                       Descripcion, Usuario, Time_Zone, marked_status, marked_by, marked_at
                FROM specials
                WHERE Supervisor = %s 
                AND FechaHora >= %s
                ORDER BY FechaHora DESC
            """
            
            cur.execute(sql, (username, shift_start))
            rows = cur.fetchall()
            
            # Resolver nombres de sitios y zonas horarias
            time_zone_cache = {}
            processed = []
            
            for r in rows:
                id_special = r[0]
                fecha_hora = r[1]
                id_sitio = r[2]
                nombre_actividad = r[3]
                cantidad = r[4]
                camera = r[5]
                descripcion = r[6]
                usuario = r[7]
                time_zone = r[8]
                marked_status = r[9]
                marked_by = r[10]
                marked_at = r[11]
                
                # Resolver nombre de sitio
                nombre_sitio = ""
                tz = time_zone or ""
                if id_sitio is not None and str(id_sitio).strip() != "":
                    if id_sitio in time_zone_cache:
                        nombre_sitio, tz = time_zone_cache[id_sitio]
                    else:
                        try:
                            cur.execute("SELECT Nombre_Sitio, Time_Zone FROM Sitios WHERE ID_Sitio = %s", (id_sitio,))
                            sit = cur.fetchone()
                            nombre_sitio = sit[0] if sit and sit[0] else ""
                            tz = sit[1] if sit and len(sit) > 1 and sit[1] else ""
                        except Exception:
                            nombre_sitio = ""
                            tz = ""
                        time_zone_cache[id_sitio] = (nombre_sitio, tz)
                
                # Formato visual para Sitio (ID + Nombre)
                if id_sitio and nombre_sitio:
                    display_site = f"{id_sitio} {nombre_sitio}"
                elif id_sitio:
                    display_site = str(id_sitio)
                else:
                    display_site = nombre_sitio or ""
                
                # Formato visual para la marca
                if marked_status == 'done':
                    mark_display = f"✅ Registrado ({marked_by})" if marked_by else "✅ Registrado"
                elif marked_status == 'flagged':
                    mark_display = f"🔄 En Progreso ({marked_by})" if marked_by else "🔄 En Progreso"
                else:
                    mark_display = ""
                
                # Formatear fecha
                fecha_str = fecha_hora.strftime("%Y-%m-%d %H:%M:%S") if fecha_hora else ""
                
                # Fila para mostrar
                display_row = [
                    str(id_special),
                    fecha_str,
                    display_site,
                    nombre_actividad or "",
                    str(cantidad) if cantidad is not None else "0",
                    camera or "",
                    descripcion or "",
                    usuario or "",
                    tz,
                    mark_display
                ]
                
                processed.append({
                    'id': id_special,
                    'values': display_row,
                    'marked_status': marked_status
                })
            
            cur.close()
            conn.close()
            
            # Actualizar cache
            row_data_cache = processed
            row_ids = [item['id'] for item in processed]
            
            # Poblar sheet
            if not processed:
                data = [["No hay specials en este turno"] + [""] * (len(columns)-1)]
                sheet.set_sheet_data(data)
            else:
                data = [item['values'] for item in processed]
                sheet.set_sheet_data(data)
                
                # Aplicar anchos personalizados
                apply_sheet_widths()
                
                # Limpiar colores primero
                sheet.dehighlight_all()
                
                # Aplicar colores según marca
                for idx, item in enumerate(processed):
                    if item['marked_status'] == 'done':
                        sheet.highlight_rows([idx], bg="#00c853", fg="#111111")
                    elif item['marked_status'] == 'flagged':
                        sheet.highlight_rows([idx], bg="#f5a623", fg="#111111")
            
            apply_sheet_widths()
            
            print(f"[DEBUG] Loaded {len(row_ids)} specials for {username}")

        except Exception as e:
            messagebox.showerror("Error", f"No se pudo cargar specials:\n{e}", parent=top)
            traceback.print_exc()
        
        # Programar siguiente refresh si auto-refresh está activo
        finally:
            if auto_refresh_active.get():
                refresh_job = top.after(120000, load_data)  # Refresh cada 2 minutos

    def get_selected_ids():
        """Obtiene los IDs de los registros seleccionados"""
        selected_rows = sheet.get_selected_rows()
        if not selected_rows:
            return []
        ids = []
        for row_idx in selected_rows:
            try:
                if row_idx < len(row_ids):
                    ids.append(row_ids[row_idx])
            except Exception:
                pass
        return ids

    def mark_as_done():
        """Marca los registros seleccionados como 'Registrado'"""
        sel = get_selected_ids()
        if not sel:
            return
        
        try:
            conn = under_super.get_connection()
            cur = conn.cursor()
            
            for item_id in sel:
                cur.execute("""
                    UPDATE specials 
                    SET marked_status = 'done', marked_at = NOW(), marked_by = %s
                    WHERE ID_special = %s
                """, (username, item_id))
            
            conn.commit()
            cur.close()
            conn.close()
            
            load_data()

            
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo marcar:\n{e}", parent=top)
            traceback.print_exc()

    def mark_as_progress():
        """Marca los registros seleccionados como 'En Progreso'"""
        sel = get_selected_ids()
        if not sel:
            messagebox.showinfo("Marcar", "Selecciona uno o más specials para marcar como En Progreso.", parent=top)
            return
        
        try:
            conn = under_super.get_connection()
            cur = conn.cursor()
            
            for item_id in sel:
                cur.execute("""
                    UPDATE specials 
                    SET marked_status = 'flagged', marked_at = NOW(), marked_by = %s
                    WHERE ID_special = %s
                """, (username, item_id))
            
            conn.commit()
            cur.close()
            conn.close()
            
            load_data()
            
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo marcar:\n{e}", parent=top)
            traceback.print_exc()

    def unmark_selected():
        """Desmarca los registros seleccionados"""
        sel = get_selected_ids()
        if not sel:
            return
        
        try:
            conn = under_super.get_connection()
            cur = conn.cursor()
            
            for item_id in sel:
                cur.execute("""
                    UPDATE specials 
                    SET marked_status = NULL, marked_at = NULL, marked_by = NULL
                    WHERE ID_special = %s
                """, (item_id,))
            
            conn.commit()
            cur.close()
            conn.close()
            
            load_data()
            
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo desmarcar:\n{e}", parent=top)
            traceback.print_exc()

    def delete_selected():
        """Elimina los registros seleccionados de specials"""
        sel = get_selected_ids()
        if not sel:
            messagebox.showwarning("Eliminar", "Selecciona uno o más specials para eliminar.", parent=top)
            return
        
        if not messagebox.askyesno("Eliminar", 
                                   f"¿Eliminar {len(sel)} special(s) de la base de datos?",
                                   parent=top):
            return
        
        try:
            conn = under_super.get_connection()
            cur = conn.cursor()
            
            for item_id in sel:
                cur.execute("DELETE FROM specials WHERE ID_special = %s", (item_id,))
            
            conn.commit()
            cur.close()
            conn.close()
            
            load_data()

            
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo eliminar:\n{e}", parent=top)
            traceback.print_exc()
    
    # Asignar comando delete_selected al botón del header
    try:
        delete_btn_header.configure(command=delete_selected)
    except:
        pass

    def show_context_menu(event):
        """Muestra menú contextual al hacer clic derecho"""
        context_menu = tk.Menu(top, tearoff=0, bg="#2c2f33", fg="#e0e0e0", 
                              activebackground="#4a90e2", activeforeground="#ffffff",
                              font=("Segoe UI", 10))
        
        context_menu.add_command(label="✅ Marcar como Registrado", command=mark_as_done)
        context_menu.add_command(label="🔄 Marcar como En Progreso", command=mark_as_progress)
        context_menu.add_separator()
        context_menu.add_command(label="❌ Desmarcar", command=unmark_selected)
        context_menu.add_command(label="🗑️ Eliminar", command=delete_selected)
        
        try:
            context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            context_menu.grab_release()

    def toggle_auto_refresh():
        """Activa/desactiva auto-refresh"""
        if auto_refresh_active.get():
            print("[DEBUG] Auto-refresh activado")
            load_data()
        else:
            print("[DEBUG] Auto-refresh desactivado")
            if refresh_job:
                top.after_cancel(refresh_job)

    # ⭐ FUNCIÓN: Abrir ventana de Otros Specials
    def open_otros_specials():
        """Ver y tomar specials de otros supervisores"""
        # Importar función auxiliar para obtener shift start de otros supervisores
        def get_supervisor_shift_start_otros(sup_name):
            """Obtiene la última hora de inicio de shift de un supervisor específico"""
            try:
                conn = under_super.get_connection()
                cur = conn.cursor()
                cur.execute("""
                    SELECT e.FechaHora 
                    FROM Eventos e
                    INNER JOIN user u ON e.ID_Usuario = u.ID_Usuario
                    WHERE u.Nombre_Usuario = %s AND e.Nombre_Actividad = %s
                    ORDER BY e.FechaHora DESC
                    LIMIT 1
                """, (sup_name, "START SHIFT"))
                row = cur.fetchone()
                cur.close()
                conn.close()
                return row[0] if row and row[0] else None
            except Exception as e:
                print(f"[ERROR] get_supervisor_shift_start_otros: {e}")
                return None
        
        # Ventana de selección de supervisor
        if UI is not None:
            sel_win = UI.CTkToplevel(top)
            sel_win.configure(fg_color="#2c2f33")
        else:
            sel_win = tk.Toplevel(top)
            sel_win.configure(bg="#2c2f33")
        
        sel_win.title("Otros Specials - Selecciona Supervisor")
        sel_win.geometry("380x340")
        sel_win.resizable(False, False)

        if UI is not None:
            UI.CTkLabel(sel_win, text="Supervisor (origen):", text_color="#00bfae",
                       font=("Segoe UI", 13, "bold")).pack(pady=(14, 6))
        else:
            tk.Label(sel_win, text="Supervisor (origen):", bg="#2c2f33", fg="#00bfae",
                    font=("Segoe UI", 13, "bold")).pack(pady=(14, 6))

        if UI is not None:
            list_frame = UI.CTkFrame(sel_win, fg_color="#2c2f33")
        else:
            list_frame = tk.Frame(sel_win, bg="#2c2f33")
        list_frame.pack(fill="both", expand=True, padx=14, pady=(4,12))
        
        yscroll_sup = tk.Scrollbar(list_frame, orient="vertical")
        yscroll_sup.pack(side="right", fill="y")
        sup_listbox = tk.Listbox(list_frame, height=10, selectmode="browse",
                                 bg="#262a31", fg="#00bfae", font=("Segoe UI", 12),
                                 yscrollcommand=yscroll_sup.set, activestyle="dotbox",
                                 selectbackground="#14414e")
        sup_listbox.pack(side="left", fill="both", expand=True)
        yscroll_sup.config(command=sup_listbox.yview)

        # Cargar supervisores
        supervisores = []
        try:
            conn = under_super.get_connection()
            cur = conn.cursor()
            cur.execute("SELECT Nombre_Usuario FROM user WHERE Rol = %s ORDER BY Nombre_Usuario", ("Supervisor",))
            supervisores = [r[0] for r in cur.fetchall()]
            cur.close()
            conn.close()
        except Exception as e:
            print(f"[ERROR] otros_specials list: {e}")
        
        if not supervisores:
            sup_listbox.insert("end", "No hay supervisores disponibles")
        else:
            for sup in supervisores:
                sup_listbox.insert("end", sup)

        def abrir_lista_specials():
            idx = sup_listbox.curselection()
            if not idx:
                messagebox.showwarning("Otros Specials", "Selecciona un supervisor.", parent=sel_win)
                return
            old_sup = sup_listbox.get(idx[0])
            if old_sup == "No hay supervisores disponibles":
                return
            
            try:
                sel_win.destroy()
            except Exception:
                pass

            # Ventana de specials del otro supervisor
            if UI is not None:
                lst_win = UI.CTkToplevel(top)
                lst_win.configure(fg_color="#2c2f33")
            else:
                lst_win = tk.Toplevel(top)
                lst_win.configure(bg="#2c2f33")
            
            lst_win.title(f"Otros Specials - {old_sup}")
            lst_win.geometry("1350x600")
            lst_win.resizable(True, True)

            # Variables
            row_ids_otros = []
            
            # Frame para tabla
            if UI is not None:
                frame2 = UI.CTkFrame(lst_win, fg_color="#2c2f33")
            else:
                frame2 = tk.Frame(lst_win, bg="#2c2f33")
            frame2.pack(expand=True, fill="both", padx=12, pady=10)
            
            # Crear tksheet
            cols2 = ["ID", "Fecha_hora", "ID_Sitio", "Nombre_Actividad", "Cantidad", "Camera", 
                    "Descripcion", "Usuario", "Time_Zone", "Marca"]
            
            custom_widths_otros = {
                "ID": 60, "Fecha_hora": 150, "ID_Sitio": 220, "Nombre_Actividad": 150,
                "Cantidad": 70, "Camera": 80, "Descripcion": 190, "Usuario": 100,
                "Time_Zone": 90, "Marca": 180
            }
            
            sheet2 = SheetClass(
                frame2, headers=cols2, theme="dark blue", height=400, width=1160,
                show_selected_cells_border=True, show_row_index=True, show_top_left=False
            )
            sheet2.enable_bindings([
                "single_select", "drag_select", "column_select", "row_select",
                "column_width_resize", "double_click_column_resize", "row_height_resize",
                "arrowkeys", "right_click_popup_menu", "rc_select", "copy"
            ])
            sheet2.pack(fill="both", expand=True)
            sheet2.change_theme("dark blue")
            
            def apply_widths():
                for idx, col in enumerate(cols2):
                    if col in custom_widths_otros:
                        try:
                            sheet2.column_width(idx, custom_widths_otros[col])
                        except:
                            pass
                sheet2.redraw()
            
            def cargar_lista():
                nonlocal row_ids_otros
                try:
                    shift_start = get_supervisor_shift_start_otros(old_sup)
                    if not shift_start:
                        sheet2.set_sheet_data([[f"{old_sup} no tiene shift activo"] + [""] * (len(cols2)-1)])
                        apply_widths()
                        row_ids_otros.clear()
                        return
                    
                    conn = under_super.get_connection()
                    cur = conn.cursor()
                    
                    cur.execute("""
                        SELECT ID_special, FechaHora, ID_Sitio, Nombre_Actividad, Cantidad, Camera,
                               Descripcion, Usuario, Time_Zone, marked_status, marked_by
                        FROM specials
                        WHERE Supervisor = %s AND FechaHora >= %s
                        ORDER BY FechaHora DESC
                    """, (old_sup, shift_start))
                    
                    rows = cur.fetchall()
                    processed = []
                    time_zone_cache = {}
                    
                    for r in rows:
                        id_sitio = r[2]
                        nombre_sitio = ""
                        tz = ""
                        
                        if id_sitio:
                            if id_sitio in time_zone_cache:
                                nombre_sitio, tz = time_zone_cache[id_sitio]
                            else:
                                try:
                                    cur.execute("SELECT Nombre_Sitio, Time_Zone FROM Sitios WHERE ID_Sitio = %s", (id_sitio,))
                                    sit = cur.fetchone()
                                    nombre_sitio = sit[0] if sit else ""
                                    tz = sit[1] if sit and len(sit) > 1 else ""
                                    time_zone_cache[id_sitio] = (nombre_sitio, tz)
                                except:
                                    pass
                        
                        display_site = f"{id_sitio} {nombre_sitio}" if id_sitio and nombre_sitio else str(id_sitio or "")
                        
                        mark_display = ""
                        if r[9] == 'done':
                            mark_display = f"✅ Registrado ({r[10]})" if r[10] else "✅ Registrado"
                        elif r[9] == 'flagged':
                            mark_display = f"🔄 En Progreso ({r[10]})" if r[10] else "🔄 En Progreso"
                        
                        fecha_str = r[1].strftime("%Y-%m-%d %H:%M:%S") if r[1] else ""
                        
                        processed.append({
                            'id': r[0],
                            'values': [str(r[0]), fecha_str, display_site, r[3] or "", 
                                     str(r[4] or 0), r[5] or "", r[6] or "", r[7] or "", 
                                     tz, mark_display],
                            'marked_status': r[9]
                        })
                    
                    cur.close()
                    conn.close()
                    
                    if not processed:
                        sheet2.set_sheet_data([["No hay specials"] + [""] * (len(cols2)-1)])
                        row_ids_otros.clear()
                    else:
                        sheet2.set_sheet_data([p['values'] for p in processed])
                        row_ids_otros[:] = [p['id'] for p in processed]
                        sheet2.dehighlight_all()
                        for idx, p in enumerate(processed):
                            if p['marked_status'] == 'done':
                                sheet2.highlight_rows([idx], bg="#00c853", fg="#111111")
                            elif p['marked_status'] == 'flagged':
                                sheet2.highlight_rows([idx], bg="#f5a623", fg="#111111")
                    
                    apply_widths()
                    
                except Exception as e:
                    messagebox.showerror("Error", f"No se pudo cargar specials:\n{e}", parent=lst_win)
                    traceback.print_exc()
            
            def tomar_specials():
                try:
                    selected = sheet2.get_selected_rows()
                    if not selected:
                        messagebox.showwarning("Tomar Specials", "Selecciona registros.", parent=lst_win)
                        return
                    
                    ids = [row_ids_otros[i] for i in selected if i < len(row_ids_otros)]
                    if not ids:
                        return
                    
                    conn = under_super.get_connection()
                    cur = conn.cursor()
                    for sid in ids:
                        cur.execute("UPDATE specials SET Supervisor = %s WHERE ID_special = %s", (username, sid))
                    conn.commit()
                    cur.close()
                    conn.close()
                    
                    messagebox.showinfo("Tomar Specials", f"✅ {len(ids)} special(s) transferido(s)", parent=lst_win)
                    cargar_lista()
                    load_data()  # Recargar datos principales
                except Exception as e:
                    messagebox.showerror("Error", f"No se pudo tomar specials:\n{e}", parent=lst_win)
                    traceback.print_exc()
            
            # Botones
            if UI is not None:
                btn_frame = UI.CTkFrame(lst_win, fg_color="#23272a")
            else:
                btn_frame = tk.Frame(lst_win, bg="#23272a")
            btn_frame.pack(fill="x", padx=10, pady=10)
            
            if UI is not None:
                UI.CTkButton(btn_frame, text="🔄 Refrescar", command=cargar_lista,
                            fg_color="#4D6068", hover_color="#27a3e0", width=120, height=35,
                            font=("Segoe UI", 11, "bold")).pack(side="left", padx=5)
                UI.CTkButton(btn_frame, text="📥 Tomar Seleccionados", command=tomar_specials,
                            fg_color="#00c853", hover_color="#00a043", width=180, height=35,
                            font=("Segoe UI", 11, "bold")).pack(side="left", padx=5)
            else:
                tk.Button(btn_frame, text="🔄 Refrescar", command=cargar_lista,
                         bg="#4D6068", fg="white", relief="flat", width=12).pack(side="left", padx=5)
                tk.Button(btn_frame, text="📥 Tomar Seleccionados", command=tomar_specials,
                         bg="#00c853", fg="white", relief="flat", width=18).pack(side="left", padx=5)
            
            cargar_lista()
        
        # Botón abrir
        if UI is not None:
            UI.CTkButton(sel_win, text="Abrir", command=abrir_lista_specials,
                        fg_color="#00c853", hover_color="#00a043", width=140, height=35,
                        font=("Segoe UI", 12, "bold")).pack(pady=12)
        else:
            tk.Button(sel_win, text="Abrir", command=abrir_lista_specials,
                     bg="#00c853", fg="white", relief="flat", width=12).pack(pady=12)

    # Botones de marcado
    if UI is not None:
        UI.CTkButton(marks_frame, text="✅ Marcar como Registrado", 
                    command=mark_as_done,
                    fg_color="#00c853", hover_color="#00a043",
                    width=180, height=35,
                    font=("Segoe UI", 11, "bold")).pack(side="left", padx=(15, 5), pady=10)
        
        UI.CTkButton(marks_frame, text="🔄 Marcar como En Progreso", 
                    command=mark_as_progress,
                    fg_color="#f5a623", hover_color="#e69515",
                    width=200, height=35,
                    font=("Segoe UI", 11, "bold")).pack(side="left", padx=5, pady=10)
        
        UI.CTkButton(marks_frame, text="❌ Desmarcar", 
                    command=unmark_selected,
                    fg_color="#3b4754", hover_color="#4a5560",
                    width=120, height=35,
                    font=("Segoe UI", 11, "bold")).pack(side="left", padx=5, pady=10)
        
        UI.CTkButton(marks_frame, text="📋 Otros Specials", 
                    command=open_otros_specials,
                    fg_color="#4a5f7a", hover_color="#3a4f6a",
                    width=150, height=35,
                    font=("Segoe UI", 11, "bold")).pack(side="left", padx=5, pady=10)
        
        UI.CTkCheckBox(marks_frame, text="Auto-refresh (2 min)", 
                      variable=auto_refresh_active,
                      fg_color="#4a90e2", text_color="#e0e0e0",
                      command=toggle_auto_refresh,
                      font=("Segoe UI", 10)).pack(side="right", padx=(5, 15), pady=10)
    else:
        tk.Button(marks_frame, text="✅ Marcar como Registrado", 
                 command=mark_as_done,
                 bg="#00c853", fg="white",
                 font=("Segoe UI", 11, "bold"), relief="flat",
                 width=20).pack(side="left", padx=(15, 5), pady=10)
        
        tk.Button(marks_frame, text="🔄 Marcar como En Progreso", 
                 command=mark_as_progress,
                 bg="#f5a623", fg="white",
                 font=("Segoe UI", 11, "bold"), relief="flat",
                 width=22).pack(side="left", padx=5, pady=10)
        
        tk.Button(marks_frame, text="❌ Desmarcar", 
                 command=unmark_selected,
                 bg="#3b4754", fg="white",
                 font=("Segoe UI", 11, "bold"), relief="flat",
                 width=12).pack(side="left", padx=5, pady=10)
        
        tk.Button(marks_frame, text="📋 Otros Specials", 
                 command=open_otros_specials,
                 bg="#4a5f7a", fg="white",
                 font=("Segoe UI", 11, "bold"), relief="flat",
                 width=15).pack(side="left", padx=5, pady=10)
        
        tk.Checkbutton(marks_frame, text="Auto-refresh (2 min)", 
                      variable=auto_refresh_active,
                      command=toggle_auto_refresh,
                      bg="#23272a", fg="#e0e0e0", selectcolor="#23272a",
                      font=("Segoe UI", 10)).pack(side="right", padx=(5, 15), pady=10)

    # ==================== AUDIT CONTAINER ====================
    if UI is not None:
        audit_container = UI.CTkFrame(top, fg_color="#2c2f33")
    else:
        audit_container = tk.Frame(top, bg="#2c2f33")
    # NO hacer pack() aquí - se mostrará solo cuando se cambie a modo Audit

    # Frame de filtros de Audit
    if UI is not None:
        audit_filters = UI.CTkFrame(audit_container, fg_color="#23272a", corner_radius=8)
    else:
        audit_filters = tk.Frame(audit_container, bg="#23272a")
    audit_filters.pack(fill="x", padx=10, pady=10)

    # Fila 1: Usuario y Sitio
    if UI is not None:
        UI.CTkLabel(audit_filters, text="Usuario:", text_color="#c9d1d9", 
                   font=("Segoe UI", 11)).grid(row=0, column=0, sticky="w", padx=(15, 5), pady=10)
    else:
        tk.Label(audit_filters, text="Usuario:", bg="#23272a", fg="#c9d1d9", 
                font=("Segoe UI", 11)).grid(row=0, column=0, sticky="w", padx=(15, 5), pady=10)
    
    audit_user_var = tk.StringVar()
    # Obtener usuarios
    try:
        conn = under_super.get_connection()
        cur = conn.cursor()
        cur.execute("SELECT `Nombre_Usuario` FROM `user` ORDER BY `Nombre_Usuario`")
        audit_users = [r[0] for r in cur.fetchall()]
        cur.close()
        conn.close()
    except Exception:
        audit_users = []
    
    try:
        audit_user_cb = under_super.FilteredCombobox(audit_filters, textvariable=audit_user_var, 
                                                     values=audit_users, width=25)
    except Exception:
        audit_user_cb = ttk.Combobox(audit_filters, textvariable=audit_user_var, 
                                     values=audit_users, width=25)
    audit_user_cb.grid(row=0, column=1, sticky="w", padx=5, pady=10)

    if UI is not None:
        UI.CTkLabel(audit_filters, text="Sitio:", text_color="#c9d1d9", 
                   font=("Segoe UI", 11)).grid(row=0, column=2, sticky="w", padx=(15, 5), pady=10)
    else:
        tk.Label(audit_filters, text="Sitio:", bg="#23272a", fg="#c9d1d9", 
                font=("Segoe UI", 11)).grid(row=0, column=2, sticky="w", padx=(15, 5), pady=10)
    
    audit_site_var = tk.StringVar()
    try:
        audit_sites = under_super.get_sites()
    except Exception:
        audit_sites = []
    
    try:
        audit_site_cb = under_super.FilteredCombobox(audit_filters, textvariable=audit_site_var, 
                                                     values=audit_sites, width=35)
    except Exception:
        audit_site_cb = ttk.Combobox(audit_filters, textvariable=audit_site_var, 
                                     values=audit_sites, width=35)
    audit_site_cb.grid(row=0, column=3, sticky="w", padx=5, pady=10)

    # Fila 2: Fecha y botones
    if UI is not None:
        UI.CTkLabel(audit_filters, text="Fecha:", text_color="#c9d1d9", 
                   font=("Segoe UI", 11)).grid(row=1, column=0, sticky="w", padx=(15, 5), pady=10)
    else:
        tk.Label(audit_filters, text="Fecha:", bg="#23272a", fg="#c9d1d9", 
                font=("Segoe UI", 11)).grid(row=1, column=0, sticky="w", padx=(15, 5), pady=10)
    
    audit_fecha_var = tk.StringVar()
    try:
        from tkcalendar import DateEntry
        audit_fecha_entry = DateEntry(
            audit_filters,
            textvariable=audit_fecha_var,
            date_pattern="yyyy-mm-dd",
            width=23
        )
    except Exception:
        audit_fecha_entry = tk.Entry(audit_filters, textvariable=audit_fecha_var, width=25)
    audit_fecha_entry.grid(row=1, column=1, sticky="w", padx=5, pady=10)

    # Botones de búsqueda y limpiar
    audit_btn_frame = tk.Frame(audit_filters, bg="#23272a")
    audit_btn_frame.grid(row=1, column=2, columnspan=2, sticky="e", padx=(15, 15), pady=10)

    def audit_search():
        """Busca eventos con los filtros especificados"""
        try:
            user_filter = audit_user_var.get().strip()
            site_filter_raw = audit_site_var.get().strip()
            fecha_filter = audit_fecha_var.get().strip()
            
            conn = under_super.get_connection()
            cur = conn.cursor()
            
            sql = """
                SELECT e.ID_Eventos, e.FechaHora, s.Nombre_Sitio, e.Nombre_Actividad, 
                       e.Cantidad, e.Camera, e.Descripcion, u.Nombre_Usuario
                FROM Eventos e
                LEFT JOIN Sitios s ON e.ID_Sitio = s.ID_Sitio
                LEFT JOIN user u ON e.ID_Usuario = u.ID_Usuario
                WHERE 1=1
            """
            params = []
            
            if user_filter:
                sql += " AND u.Nombre_Usuario = %s"
                params.append(user_filter)
            
            # ⭐ USAR HELPER para deconstruir formato "Nombre (ID)"
            if site_filter_raw:
                site_name, site_id = under_super.parse_site_filter(site_filter_raw)
                
                if site_name and site_id:
                    # Buscar por nombre (más preciso cuando tenemos ambos)
                    sql += " AND s.Nombre_Sitio = %s"
                    params.append(site_name)
                elif site_id:
                    # Buscar solo por ID
                    sql += " AND s.ID_Sitio = %s"
                    params.append(site_id)
                elif site_name:
                    # Buscar solo por nombre
                    sql += " AND s.Nombre_Sitio = %s"
                    params.append(site_name)
            
            if fecha_filter:
                sql += " AND DATE(e.FechaHora) = %s"
                params.append(fecha_filter)
            
            sql += " ORDER BY e.FechaHora DESC LIMIT 500"
            
            cur.execute(sql, params)
            rows = cur.fetchall()
            cur.close()
            conn.close()
            
            # Mostrar resultados en audit_sheet
            data = []
            for r in rows:
                data.append([
                    r[0] or "",  # ID_Eventos
                    str(r[1]) if r[1] else "",  #  
                    r[2] or "",  # Nombre_Sitio
                    r[3] or "",  # Nombre_Actividad
                    r[4] or "",  # Cantidad
                    r[5] or "",  # Camera
                    r[6] or "",  # Descripcion
                    r[7] or ""   # Usuario
                ])
            
            audit_sheet.set_sheet_data(data)
            
            # Aplicar anchos personalizados
            audit_widths = {
                "ID_Evento": 80,
                " ": 150,
                "Nombre_Sitio": 220,
                "Nombre_Actividad": 150,
                "Cantidad": 70,
                "Camera": 70,
                "Descripcion": 200,
                "Usuario": 100
            }
            cols = ["ID_Evento", " ", "Nombre_Sitio", "Nombre_Actividad", 
                   "Cantidad", "Camera", "Descripcion", "Usuario"]
            for idx, col_name in enumerate(cols):
                if col_name in audit_widths:
                    try:
                        audit_sheet.column_width(idx, int(audit_widths[col_name]))
                    except Exception:
                        pass
            audit_sheet.redraw()
            
            print(f"[DEBUG] Audit search returned {len(rows)} results")
            
        except Exception as e:
            messagebox.showerror("Error", f"Error en búsqueda:\n{e}", parent=top)
            traceback.print_exc()

    def audit_clear():
        """Limpia los filtros de búsqueda"""
        audit_user_var.set("")
        audit_site_var.set("")
        audit_fecha_var.set("")
        audit_sheet.set_sheet_data([[]])

    if UI is not None:
        UI.CTkButton(
            audit_btn_frame,
            text="� Buscar",
            command=audit_search,
            fg_color="#4a90e2",
            hover_color="#357ABD",
            width=100,
            height=32,
            font=("Segoe UI", 11, "bold")
        ).pack(side="left", padx=(0, 8))
        
        UI.CTkButton(
            audit_btn_frame,
            text="🗑️ Limpiar",
            command=audit_clear,
            fg_color="#3b4754",
            hover_color="#4a5560",
            width=100,
            height=32,
            font=("Segoe UI", 11, "bold")
        ).pack(side="left")
    else:
        tk.Button(
            audit_btn_frame,
            text="🔍 Buscar",
            command=audit_search,
            bg="#4a90e2",
            fg="white",
            activebackground="#357ABD",
            font=("Segoe UI", 11, "bold"),
            relief="flat",
            width=10
        ).pack(side="left", padx=(0, 8))
        
        tk.Button(
            audit_btn_frame,
            text="🗑️ Limpiar",
            command=audit_clear,
            bg="#3b4754",
            fg="white",
            activebackground="#4a5560",
            font=("Segoe UI", 11, "bold"),
            relief="flat",
            width=10
        ).pack(side="left")

    # Frame para tksheet de Audit
    if UI is not None:
        audit_sheet_frame = UI.CTkFrame(audit_container, fg_color="#2c2f33")
    else:
        audit_sheet_frame = tk.Frame(audit_container, bg="#2c2f33")
    audit_sheet_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))

    # Crear tksheet para Audit
    audit_columns = ["ID_Evento", " ", "Nombre_Sitio", "Nombre_Actividad", 
                    "Cantidad", "Camera", "Descripcion", "Usuario"]
    audit_sheet = SheetClass(audit_sheet_frame, data=[[]], headers=audit_columns)
    audit_sheet.enable_bindings([
        "single_select",
        "row_select",
        "column_width_resize",
        "rc_select",
        "copy",
        "select_all"
    ])
    audit_sheet.pack(fill="both", expand=True)
    audit_sheet.change_theme("dark blue")

    # ==================== BREAKS CONTAINER ====================
    if UI is not None:
        breaks_container = UI.CTkFrame(top, fg_color="#2c2f33")
    else:
        breaks_container = tk.Frame(top, bg="#2c2f33")
    # NO hacer pack() aquí - se mostrará solo cuando se cambie a modo Breaks

    # Frame de controles (comboboxes y botones) para Breaks
    if UI is not None:
        breaks_controls_frame = UI.CTkFrame(breaks_container, fg_color="#23272a", corner_radius=8)
    else:
        breaks_controls_frame = tk.Frame(breaks_container, bg="#23272a")
    breaks_controls_frame.pack(fill="x", padx=10, pady=10)

    # Función para cargar usuarios desde la BD
    def load_users_breaks():
        """Carga lista de usuarios desde la base de datos"""
        try:
            users = under_super.load_users()
            return users if users else []
        except Exception as e:
            print(f"[ERROR] load_users_breaks: {e}")
            traceback.print_exc()
            return []

    # Función para cargar covers desde la BD
    def load_covers_from_db():
        """Carga covers activos desde gestion_breaks_programados con nombres de usuario"""
        try:
            conn = under_super.get_connection()
            cur = conn.cursor()
            query = """
                SELECT 
                    u_covered.Nombre_Usuario as usuario_cubierto,
                    u_covering.Nombre_Usuario as usuario_cubre,
                    TIME(gbp.Fecha_hora_cover) as hora
                FROM gestion_breaks_programados gbp
                INNER JOIN user u_covered ON gbp.User_covered = u_covered.ID_Usuario
                INNER JOIN user u_covering ON gbp.User_covering = u_covering.ID_Usuario
                WHERE gbp.is_Active = 1
                ORDER BY gbp.Fecha_hora_cover
            """
            cur.execute(query)
            rows = cur.fetchall()
            cur.close()
            conn.close()
            
            # Debug: Imprimir los datos cargados
            print(f"[DEBUG] Covers cargados desde BD: {len(rows)} registros")
            for row in rows:
                print(f"[DEBUG] Cover: {row[0]} cubierto por {row[1]} a las {row[2]}")
            
            return rows
        except Exception as e:
            print(f"[ERROR] load_covers_from_db: {e}")
            traceback.print_exc()
            return []

    # Variables para comboboxes
    usuario_a_cubrir_var = tk.StringVar()
    cubierto_por_var = tk.StringVar()
    hora_var = tk.StringVar()

    # Cargar usuarios
    users_list = load_users_breaks()

    # Primera fila: Usuario a cubrir
    row1_frame_breaks = tk.Frame(breaks_controls_frame, bg="#23272a")
    row1_frame_breaks.pack(fill="x", padx=20, pady=(15, 5))

    if UI is not None:
        UI.CTkLabel(row1_frame_breaks, text="👤 Usuario a Cubrir:", 
                   text_color="#ffffff", font=("Segoe UI", 14, "bold")).pack(side="left", padx=(0, 10))
    else:
        tk.Label(row1_frame_breaks, text="👤 Usuario a Cubrir:", bg="#23272a", fg="#ffffff", 
                font=("Segoe UI", 14, "bold")).pack(side="left", padx=(0, 10))

    if UI is not None:
        usuario_combo_breaks = under_super.FilteredCombobox(row1_frame_breaks, textvariable=usuario_a_cubrir_var,
                                                     values=users_list, width=40, state="readonly",
                                                     font=("Segoe UI", 11))
        usuario_combo_breaks.set("")  # Establecer vacío inicialmente
    else:
        usuario_combo_breaks = ttk.Combobox(row1_frame_breaks, textvariable=usuario_a_cubrir_var,
                                           values=users_list, width=25, state="readonly")
    usuario_combo_breaks.pack(side="left", padx=5)

    # Segunda fila: Cubierto por
    row2_frame_breaks = tk.Frame(breaks_controls_frame, bg="#23272a")
    row2_frame_breaks.pack(fill="x", padx=20, pady=5)

    if UI is not None:
        UI.CTkLabel(row2_frame_breaks, text="🔄 Cubierto Por:", 
                   text_color="#ffffff", font=("Segoe UI", 14, "bold")).pack(side="left", padx=(0, 10))
    else:
        tk.Label(row2_frame_breaks, text="🔄 Cubierto Por:", bg="#23272a", fg="#ffffff", 
                font=("Segoe UI", 14, "bold")).pack(side="left", padx=(0, 10))

    if UI is not None:
        cover_by_combo_breaks = under_super.FilteredCombobox(row2_frame_breaks, textvariable=cubierto_por_var,
                                              values=users_list, width=40, state="readonly",
                                              font=("Segoe UI", 11))
        cover_by_combo_breaks.set("")  # Establecer vacío inicialmente
    else:
        cover_by_combo_breaks = ttk.Combobox(row2_frame_breaks, textvariable=cubierto_por_var,
                                            values=users_list, width=25, state="readonly")
    cover_by_combo_breaks.pack(side="left", padx=5)

    # Generar lista de horas en formato HH:00:00 (cada hora del día)
    horas_disponibles = [f"{h:02d}:00:00" for h in range(24)]

    # Tercera fila: Hora
    row3_frame_breaks = tk.Frame(breaks_controls_frame, bg="#23272a")
    row3_frame_breaks.pack(fill="x", padx=20, pady=5)

    if UI is not None:
        UI.CTkLabel(row3_frame_breaks, text="🕐 Hora Programada:", 
                   text_color="#ffffff", font=("Segoe UI", 14, "bold")).pack(side="left", padx=(0, 10))
    else:
        tk.Label(row3_frame_breaks, text="🕐 Hora Programada:", bg="#23272a", fg="#ffffff", 
                font=("Segoe UI", 14, "bold")).pack(side="left", padx=(0, 10))

    if UI is not None:
        hora_combo_breaks = under_super.FilteredCombobox(
            row3_frame_breaks, 
            textvariable=hora_var,
            values=horas_disponibles,
            width=25,
            font=("Segoe UI", 13),
            background='#2b2b2b', 
            foreground='#ffffff',
            bordercolor='#4a90e2', 
            arrowcolor='#ffffff'
        )
        hora_combo_breaks.pack(side="left", padx=5)
    else:
        hora_entry_breaks = tk.Entry(row3_frame_breaks, textvariable=hora_var, width=27)
        hora_entry_breaks.pack(side="left", padx=5)

    # Función para cargar datos agrupados (matriz)
    def cargar_datos_agrupados_breaks():
        """Carga datos agrupados por quien cubre (covered_by como columnas)"""
        try:
            rows = load_covers_from_db()
            
            # Obtener lista única de "Cubierto Por" (nombres) para las columnas
            covered_by_set = sorted(set(row[1] for row in rows if row[1]))
            
            # Headers: hora primero + columnas de personas que cubren (nombres)
            headers = ["Hora Programada"]
            for cb in covered_by_set:
                headers.append(cb)  # Ya son nombres de usuario
            
            # Agrupar por hora - solo el PRIMER usuario por covered_by y hora
            horas_dict = {}
            for row in rows:
                usuario_cubierto = row[0]  # Nombre del usuario a cubrir
                usuario_cubre = row[1]     # Nombre del usuario que cubre
                hora = str(row[2])          # Hora en formato HH:MM:SS
                
                if hora not in horas_dict:
                    horas_dict[hora] = {cb: "" for cb in covered_by_set}
                
                # Solo asignar si la celda está vacía (un usuario por celda)
                if usuario_cubre in horas_dict[hora] and not horas_dict[hora][usuario_cubre]:
                    horas_dict[hora][usuario_cubre] = usuario_cubierto
            
            # Convertir a lista de filas para el sheet
            data = []
            for hora in sorted(horas_dict.keys()):
                fila = [hora]
                for covered_by in covered_by_set:
                    fila.append(horas_dict[hora][covered_by])
                data.append(fila)
            
            print(f"[DEBUG] Headers construidos para breaks: {headers}")
            print(f"[DEBUG] Data construida: {len(data)} filas")
            
            return headers, data
            
        except Exception as e:
            print(f"[ERROR] cargar_datos_agrupados_breaks: {e}")
            traceback.print_exc()
            return ["Hora Programada"], [[]]

    # Función para limpiar formulario
    def limpiar_breaks():
        usuario_combo_breaks.set("")
        cover_by_combo_breaks.set("")
        hora_var.set("")
    
    # Función wrapper para eliminar cover
    def eliminar_cover_breaks():
        """Wrapper que llama a under_super.eliminar_cover_breaks con todos los parámetros necesarios"""
        if not USE_SHEET:
            return
        
        success, mensaje, rows = under_super.eliminar_cover_breaks(
            breaks_sheet=breaks_sheet,
            parent_window=top
        )
        
        # Si fue exitoso, refrescar la tabla
        if success:
            refrescar_tabla_breaks()

    # Función para refrescar tabla
    def refrescar_tabla_breaks():
        if not USE_SHEET:
            return
        headers, data = cargar_datos_agrupados_breaks()
        breaks_sheet.headers(headers)
        breaks_sheet.set_sheet_data(data)
        # Reajustar anchos después de refrescar
        for i in range(len(headers)):
            breaks_sheet.column_width(column=i, width=120)
        breaks_sheet.redraw()

    # Función wrapper para agregar y refrescar
    def agregar_y_refrescar():
        """Agrega un cover y luego refresca la tabla"""
        try:
            under_super.select_covered_by(
                username, 
                hora=hora_var.get(), 
                usuario=cubierto_por_var.get(),
                cover=usuario_a_cubrir_var.get()
            )
            # Refrescar tabla y limpiar formulario después de agregar
            limpiar_breaks()
            refrescar_tabla_breaks()
        except Exception as e:
            print(f"[ERROR] agregar_y_refrescar: {e}")
            traceback.print_exc()

    # Cuarta fila: Botones
    row4_frame_breaks = tk.Frame(breaks_controls_frame, bg="#23272a")
    row4_frame_breaks.pack(fill="x", padx=20, pady=(5, 15))

    if UI is not None:
        UI.CTkButton(row4_frame_breaks, text="➕ Agregar",
                    command=agregar_y_refrescar,
                    fg_color="#28a745", hover_color="#218838",
                    font=("Segoe UI", 13, "bold"),
                    width=150).pack(side="left", padx=5)
        
        UI.CTkButton(row4_frame_breaks, text="🔄 Limpiar",
                    command=limpiar_breaks,
                    fg_color="#6c757d", hover_color="#5a6268",
                    font=("Segoe UI", 13),
                    width=120).pack(side="left", padx=5)
        
        UI.CTkButton(row4_frame_breaks, text="🗑️ Eliminar Cover Seleccionado",
                    command=eliminar_cover_breaks,
                    fg_color="#dc3545", hover_color="#c82333",
                    font=("Segoe UI", 13),
                    width=220).pack(side="left", padx=5)
    else:
        tk.Button(row4_frame_breaks, text="➕ Agregar",
                 command=agregar_y_refrescar,
                 bg="#28a745", fg="white",
                 font=("Segoe UI", 13, "bold"),
                 relief="flat", width=12).pack(side="left", padx=5)
        
        tk.Button(row4_frame_breaks, text="🔄 Limpiar",
                 command=limpiar_breaks,
                 bg="#6c757d", fg="white",
                 font=("Segoe UI", 13),
                 relief="flat", width=10).pack(side="left", padx=5)
        
        tk.Button(row4_frame_breaks, text="🗑️ Eliminar Cover Seleccionado",
                 command=eliminar_cover_breaks,
                 bg="#dc3545", fg="white",
                 font=("Segoe UI", 13),
                 relief="flat", width=24).pack(side="left", padx=5)

    # Frame para tksheet de Breaks
    if UI is not None:
        breaks_sheet_frame = UI.CTkFrame(breaks_container, fg_color="#2c2f33")
    else:
        breaks_sheet_frame = tk.Frame(breaks_container, bg="#2c2f33")
    breaks_sheet_frame.pack(fill="both", expand=True, padx=10, pady=10)

    if USE_SHEET:
        headers, data = cargar_datos_agrupados_breaks()
        
        breaks_sheet = SheetClass(breaks_sheet_frame,
                                 headers=headers,
                                 theme="dark blue",
                                 width=1280,
                                 height=450)
        breaks_sheet.enable_bindings([
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
        breaks_sheet.pack(fill="both", expand=True)
        
        breaks_sheet.set_sheet_data(data)
        breaks_sheet.change_theme("dark blue")
        
        # Ajustar anchos de columnas
        for i in range(len(headers)):
            breaks_sheet.column_width(column=i, width=120)
        
        # Función para editar celda con doble clic
        def editar_celda_breaks(event):
            try:
                # Obtener la celda seleccionada
                selection = breaks_sheet.get_currently_selected()
                if not selection:
                    return
                
                row, col = selection.row, selection.column
                
                # Ignorar primera columna (hora) y primera fila (headers)
                if col == 0 or row < 0:
                    return
                
                # Obtener datos de la celda
                current_data = breaks_sheet.get_sheet_data()
                if row >= len(current_data):
                    return
                
                hora_actual = current_data[row][0]  # Primera columna es la hora
                usuario_cubierto_actual = current_data[row][col] if col < len(current_data[row]) else ""  # El que ESTÁ cubierto
                
                # ⭐ OBTENER HEADERS DEL BREAKS_SHEET DIRECTAMENTE (no usar variable 'headers' que puede ser de otra tabla)
                breaks_headers = breaks_sheet.headers()
                usuario_cubre_actual = breaks_headers[col]  # El header es el usuario que HACE el cover
                
                # Si la celda está vacía, no permitir edición
                if not usuario_cubierto_actual or usuario_cubierto_actual.strip() == "":
                    messagebox.showinfo("Información", 
                                      "No hay cover asignado en esta celda.\n\nUsa el botón 'Añadir' para crear un nuevo cover.",
                                      parent=top)
                    return
                
                # Crear ventana de edición
                if UI is not None:
                    edit_win = UI.CTkToplevel(top)
                    edit_win.title("Editar Cover")
                    edit_win.geometry("500x400")
                    edit_win.configure(fg_color="#2c2f33")
                else:
                    edit_win = tk.Toplevel(top)
                    edit_win.title("Editar Cover")
                    edit_win.geometry("500x400")
                    edit_win.configure(bg="#2c2f33")
                
                edit_win.transient(top)
                edit_win.grab_set()
                
                # Frame principal
                if UI is not None:
                    main_frame = UI.CTkFrame(edit_win, fg_color="#23272a", corner_radius=10)
                else:
                    main_frame = tk.Frame(edit_win, bg="#23272a")
                main_frame.pack(fill="both", expand=True, padx=20, pady=20)
                
                # Título
                if UI is not None:
                    UI.CTkLabel(main_frame, text="✏️ Editar Cover de Break", 
                               font=("Segoe UI", 20, "bold"),
                               text_color="#ffffff").pack(pady=(10, 20))
                else:
                    tk.Label(main_frame, text="✏️ Editar Cover de Break", 
                            font=("Segoe UI", 20, "bold"),
                            bg="#23272a", fg="#ffffff").pack(pady=(10, 20))
                
                # Información del cover con mejor formato
                if UI is not None:
                    info_frame = UI.CTkFrame(main_frame, fg_color="#2c2f33", corner_radius=8)
                else:
                    info_frame = tk.Frame(main_frame, bg="#2c2f33")
                info_frame.pack(fill="x", padx=10, pady=10)
                
                # Fila 1: Hora
                hora_row = tk.Frame(info_frame, bg="#2c2f33")
                hora_row.pack(fill="x", padx=15, pady=8)
                if UI is not None:
                    UI.CTkLabel(hora_row, text="🕐 Hora:", 
                               font=("Segoe UI", 13, "bold"),
                               text_color="#99aab5", width=150).pack(side="left")
                    UI.CTkLabel(hora_row, text=hora_actual, 
                               font=("Segoe UI", 13),
                               text_color="#ffffff").pack(side="left")
                else:
                    tk.Label(hora_row, text="🕐 Hora:", 
                            font=("Segoe UI", 13, "bold"),
                            bg="#2c2f33", fg="#99aab5", width=15, anchor="w").pack(side="left")
                    tk.Label(hora_row, text=hora_actual, 
                            font=("Segoe UI", 13),
                            bg="#2c2f33", fg="#ffffff").pack(side="left")
                
                # Fila 2: Usuario que hace el cover
                covering_row = tk.Frame(info_frame, bg="#2c2f33")
                covering_row.pack(fill="x", padx=15, pady=8)
                if UI is not None:
                    UI.CTkLabel(covering_row, text="👤 Usuario que cubre:", 
                               font=("Segoe UI", 13, "bold"),
                               text_color="#99aab5", width=150).pack(side="left")
                    UI.CTkLabel(covering_row, text=usuario_cubre_actual, 
                               font=("Segoe UI", 13),
                               text_color="#4aa3ff").pack(side="left")
                else:
                    tk.Label(covering_row, text="👤 Usuario que cubre:", 
                            font=("Segoe UI", 13, "bold"),
                            bg="#2c2f33", fg="#99aab5", width=15, anchor="w").pack(side="left")
                    tk.Label(covering_row, text=usuario_cubre_actual, 
                            font=("Segoe UI", 13),
                            bg="#2c2f33", fg="#4aa3ff").pack(side="left")
                
                # Fila 3: Usuario cubierto actual
                actual_row = tk.Frame(info_frame, bg="#2c2f33")
                actual_row.pack(fill="x", padx=15, pady=8)
                if UI is not None:
                    UI.CTkLabel(actual_row, text="📋 Usuario cubierto:", 
                               font=("Segoe UI", 13, "bold"),
                               text_color="#99aab5", width=150).pack(side="left")
                    UI.CTkLabel(actual_row, text=usuario_cubierto_actual, 
                               font=("Segoe UI", 13, "bold"),
                               text_color="#7289da").pack(side="left")
                else:
                    tk.Label(actual_row, text="📋 Usuario cubierto:", 
                            font=("Segoe UI", 13, "bold"),
                            bg="#2c2f33", fg="#99aab5", width=15, anchor="w").pack(side="left")
                    tk.Label(actual_row, text=usuario_cubierto_actual, 
                            font=("Segoe UI", 13, "bold"),
                            bg="#2c2f33", fg="#7289da").pack(side="left")
                
                # Selector de nuevo usuario cubierto
                if UI is not None:
                    UI.CTkLabel(main_frame, text="➡️ Cambiar a (nuevo usuario cubierto):", 
                               font=("Segoe UI", 13, "bold"),
                               text_color="#ffffff").pack(anchor="w", padx=10, pady=(15, 5))
                else:
                    tk.Label(main_frame, text="➡️ Cambiar a (nuevo usuario cubierto):", 
                            font=("Segoe UI", 13, "bold"),
                            bg="#23272a", fg="#ffffff").pack(anchor="w", padx=10, pady=(15, 5))
                
                # Obtener lista de usuarios
                usuarios_disponibles = []
                try:
                    conn = under_super.get_connection()
                    cur = conn.cursor()
                    cur.execute("SELECT Nombre_Usuario FROM user ORDER BY Nombre_Usuario")
                    usuarios_disponibles = [row[0] for row in cur.fetchall()]
                    cur.close()
                    conn.close()
                except Exception as e:
                    print(f"[ERROR] No se pudieron cargar usuarios: {e}")
                
                nuevo_usuario_cubierto_var = tk.StringVar(value=usuario_cubierto_actual)
                
                # Usar FilteredCombobox para mejor búsqueda
                usuario_combo = under_super.FilteredCombobox(
                    main_frame,
                    textvariable=nuevo_usuario_cubierto_var,
                    values=usuarios_disponibles,
                    width=35,
                    font=("Segoe UI", 12),
                    bordercolor="#5ab4ff",
                    borderwidth=2,
                    background="#2b2b2b",
                    foreground="#ffffff",
                    fieldbackground="#2b2b2b"
                )
                usuario_combo.pack(padx=10, pady=5, fill="x")
                
                # Función para guardar cambios
                def guardar_cambios():
                    nuevo_usuario_cubierto = nuevo_usuario_cubierto_var.get().strip()
                    if not nuevo_usuario_cubierto:
                        messagebox.showwarning("Advertencia", "Debe seleccionar un usuario", parent=edit_win)
                        return
                    
                    # Llamar a la función de under_super para actualizar el cover
                    # Parámetros: supervisor, hora, quien_cubre, usuario_cubierto_anterior, nuevo_usuario_cubierto
                    exito = under_super.actualizar_cover_breaks(
                        username=username,
                        hora_actual=hora_actual,
                        covered_by_actual=usuario_cubre_actual,
                        usuario_actual=usuario_cubierto_actual,
                        nuevo_usuario=nuevo_usuario_cubierto
                    )
                    
                    if exito:
                        messagebox.showinfo("Éxito", "Cover actualizado exitosamente", parent=edit_win)
                        edit_win.destroy()
                        refrescar_tabla_breaks()
                    else:
                        messagebox.showerror("Error", "No se pudo actualizar el cover", parent=edit_win)
                
                # Botones
                if UI is not None:
                    buttons_frame = UI.CTkFrame(main_frame, fg_color="transparent")
                else:
                    buttons_frame = tk.Frame(main_frame, bg="#23272a")
                buttons_frame.pack(pady=20)
                
                if UI is not None:
                    UI.CTkButton(buttons_frame, text="💾 Guardar", 
                                command=guardar_cambios,
                                fg_color="#43b581",
                                hover_color="#3ca374",
                                width=120,
                                font=("Segoe UI", 12, "bold")).pack(side="left", padx=5)
                    UI.CTkButton(buttons_frame, text="❌ Cancelar", 
                                command=edit_win.destroy,
                                fg_color="#f04747",
                                hover_color="#d84040",
                                width=120,
                                font=("Segoe UI", 12, "bold")).pack(side="left", padx=5)
                else:
                    tk.Button(buttons_frame, text="💾 Guardar", 
                             command=guardar_cambios,
                             bg="#43b581",
                             fg="white",
                             font=("Segoe UI", 12, "bold"),
                             width=12).pack(side="left", padx=5)
                    tk.Button(buttons_frame, text="❌ Cancelar", 
                             command=edit_win.destroy,
                             bg="#f04747",
                             fg="white",
                             font=("Segoe UI", 12, "bold"),
                             width=12).pack(side="left", padx=5)
                
            except Exception as e:
                print(f"[ERROR] editar_celda_breaks: {e}")
                traceback.print_exc()
                messagebox.showerror("Error", f"Error al editar celda: {e}")
        
        # Vincular evento de doble clic
        breaks_sheet.bind("<Double-Button-1>", editar_celda_breaks)
        
    else:
        if UI is not None:
            UI.CTkLabel(breaks_sheet_frame, text="⚠️ tksheet no instalado", 
                       text_color="#ff6b6b", font=("Segoe UI", 16)).pack(pady=20)
        else:
            tk.Label(breaks_sheet_frame, text="⚠️ tksheet no instalado", 
                    bg="#2c2f33", fg="#ff6b6b", font=("Segoe UI", 16)).pack(pady=20)

    # ==================== ROL DE COVER CONTAINER ====================
    if UI is not None:
        rol_cover_container = UI.CTkFrame(top, fg_color="#2c2f33")
    else:
        rol_cover_container = tk.Frame(top, bg="#2c2f33")
    # NO hacer pack() aquí - se mostrará solo cuando se cambie a modo Rol de Cover

    # Frame de instrucciones
    if UI is not None:
        info_frame_rol = UI.CTkFrame(rol_cover_container, fg_color="#23272a", corner_radius=8)
    else:
        info_frame_rol = tk.Frame(rol_cover_container, bg="#23272a")
    info_frame_rol.pack(fill="x", padx=10, pady=10)

    if UI is not None:
        UI.CTkLabel(info_frame_rol, 
                   text="🎭 Gestión de Rol de Cover - Habilitar operadores que pueden ver la lista de covers",
                   text_color="#00bfae", 
                   font=("Segoe UI", 14, "bold")).pack(pady=15)
    else:
        tk.Label(info_frame_rol, 
                text="🎭 Gestión de Rol de Cover - Habilitar operadores que pueden ver la lista de covers",
                bg="#23272a", fg="#00bfae", 
                font=("Segoe UI", 14, "bold")).pack(pady=15)

    # Frame principal con dos columnas
    if UI is not None:
        main_frame_rol = UI.CTkFrame(rol_cover_container, fg_color="#2c2f33")
    else:
        main_frame_rol = tk.Frame(rol_cover_container, bg="#2c2f33")
    main_frame_rol.pack(fill="both", expand=True, padx=10, pady=10)

    # Columna izquierda: Operadores disponibles (Active = 1)
    if UI is not None:
        left_frame_rol = UI.CTkFrame(main_frame_rol, fg_color="#23272a", corner_radius=8)
    else:
        left_frame_rol = tk.Frame(main_frame_rol, bg="#23272a")
    left_frame_rol.pack(side="left", fill="both", expand=True, padx=(0, 5))

    if UI is not None:
        UI.CTkLabel(left_frame_rol, 
                   text="👤 Operadores Activos (Sin acceso a covers)",
                   text_color="#ffffff", 
                   font=("Segoe UI", 13, "bold")).pack(pady=10)
    else:
        tk.Label(left_frame_rol, 
                text="👤 Operadores Activos (Sin acceso a covers)",
                bg="#23272a", fg="#ffffff", 
                font=("Segoe UI", 13, "bold")).pack(pady=10)

    # Listbox para operadores sin acceso
    list_frame_sin_acceso = tk.Frame(left_frame_rol, bg="#23272a")
    list_frame_sin_acceso.pack(fill="both", expand=True, padx=15, pady=(0, 15))

    scroll_sin_acceso = tk.Scrollbar(list_frame_sin_acceso, orient="vertical")
    scroll_sin_acceso.pack(side="right", fill="y")

    listbox_sin_acceso = tk.Listbox(list_frame_sin_acceso, 
                                    selectmode="extended",
                                    bg="#262a31", 
                                    fg="#ffffff", 
                                    font=("Segoe UI", 11),
                                    yscrollcommand=scroll_sin_acceso.set,
                                    selectbackground="#4a90e2",
                                    height=20)
    listbox_sin_acceso.pack(side="left", fill="both", expand=True)
    scroll_sin_acceso.config(command=listbox_sin_acceso.yview)

    # Columna derecha: Operadores con acceso (Active = 2)
    if UI is not None:
        right_frame_rol = UI.CTkFrame(main_frame_rol, fg_color="#23272a", corner_radius=8)
    else:
        right_frame_rol = tk.Frame(main_frame_rol, bg="#23272a")
    right_frame_rol.pack(side="left", fill="both", expand=True, padx=(5, 0))

    if UI is not None:
        UI.CTkLabel(right_frame_rol, 
                   text="✅ Operadores con Acceso a Covers",
                   text_color="#00c853", 
                   font=("Segoe UI", 13, "bold")).pack(pady=10)
    else:
        tk.Label(right_frame_rol, 
                text="✅ Operadores con Acceso a Covers",
                bg="#23272a", fg="#00c853", 
                font=("Segoe UI", 13, "bold")).pack(pady=10)

    # Listbox para operadores con acceso
    list_frame_con_acceso = tk.Frame(right_frame_rol, bg="#23272a")
    list_frame_con_acceso.pack(fill="both", expand=True, padx=15, pady=(0, 15))

    scroll_con_acceso = tk.Scrollbar(list_frame_con_acceso, orient="vertical")
    scroll_con_acceso.pack(side="right", fill="y")

    listbox_con_acceso = tk.Listbox(list_frame_con_acceso, 
                                    selectmode="extended",
                                    bg="#262a31", 
                                    fg="#00c853", 
                                    font=("Segoe UI", 11),
                                    yscrollcommand=scroll_con_acceso.set,
                                    selectbackground="#4a90e2",
                                    height=20)
    listbox_con_acceso.pack(side="left", fill="both", expand=True)
    scroll_con_acceso.config(command=listbox_con_acceso.yview)

    # Frame de botones entre las dos columnas
    if UI is not None:
        buttons_frame_rol = UI.CTkFrame(rol_cover_container, fg_color="#2c2f33")
    else:
        buttons_frame_rol = tk.Frame(rol_cover_container, bg="#2c2f33")
    buttons_frame_rol.pack(fill="x", padx=10, pady=10)

    def cargar_operadores_rol():
        """Carga operadores separados por su estado Active en sesion"""
        try:
            conn = under_super.get_connection()
            cur = conn.cursor()
            
            # Limpiar listboxes
            listbox_sin_acceso.delete(0, tk.END)
            listbox_con_acceso.delete(0, tk.END)
            
            # Operadores con Active = 1 (sin acceso a covers)
            cur.execute("""
                SELECT DISTINCT s.ID_user 
                FROM sesion s
                INNER JOIN user u ON s.ID_user = u.Nombre_Usuario
                WHERE s.Active = 1 AND u.Rol = 'Operador'
                ORDER BY s.ID_user
            """)
            sin_acceso = cur.fetchall()
            
            for row in sin_acceso:
                listbox_sin_acceso.insert(tk.END, row[0])
            
            # Operadores con Active = 2 (con acceso a covers)
            cur.execute("""
                SELECT DISTINCT s.ID_user 
                FROM sesion s
                INNER JOIN user u ON s.ID_user = u.Nombre_Usuario
                WHERE s.Active = 2 AND u.Rol = 'Operador'
                ORDER BY s.ID_user
            """)
            con_acceso = cur.fetchall()
            
            for row in con_acceso:
                listbox_con_acceso.insert(tk.END, row[0])
            
            cur.close()
            conn.close()
            
            print(f"[DEBUG] Operadores cargados: {len(sin_acceso)} sin acceso, {len(con_acceso)} con acceso")
            
        except Exception as e:
            print(f"[ERROR] cargar_operadores_rol: {e}")
            traceback.print_exc()
            messagebox.showerror("Error", f"Error al cargar operadores:\n{e}", parent=top)

    def habilitar_acceso():
        """Cambia Active de 1 a 2 para los operadores seleccionados (habilitar acceso a covers)"""
        seleccion = listbox_sin_acceso.curselection()
        if not seleccion:
            messagebox.showwarning("Selección", "Selecciona uno o más operadores para habilitar.", parent=top)
            return
        
        operadores = [listbox_sin_acceso.get(i) for i in seleccion]
        
        if not messagebox.askyesno("Confirmar", 
                                   f"¿Habilitar acceso a covers para {len(operadores)} operador(es)?",
                                   parent=top):
            return
        
        try:
            conn = under_super.get_connection()
            cur = conn.cursor()
            
            for operador in operadores:
                cur.execute("""
                    UPDATE sesion 
                    SET Active = 2 
                    WHERE ID_user = %s AND Active = 1
                """, (operador,))
            
            conn.commit()
            cur.close()
            conn.close()
            
            cargar_operadores_rol()
            
        except Exception as e:
            print(f"[ERROR] habilitar_acceso: {e}")
            traceback.print_exc()
            messagebox.showerror("Error", f"Error al habilitar acceso:\n{e}", parent=top)

    def deshabilitar_acceso():
        """Cambia Active de 2 a 1 para los operadores seleccionados (quitar acceso a covers)"""
        seleccion = listbox_con_acceso.curselection()
        if not seleccion:
            messagebox.showwarning("Selección", "Selecciona uno o más operadores para deshabilitar.", parent=top)
            return
        
        operadores = [listbox_con_acceso.get(i) for i in seleccion]
        
        if not messagebox.askyesno("Confirmar", 
                                   f"¿Quitar acceso a covers para {len(operadores)} operador(es)?",
                                   parent=top):
            return
        
        try:
            conn = under_super.get_connection()
            cur = conn.cursor()
            
            for operador in operadores:
                cur.execute("""
                    UPDATE sesion 
                    SET Active = 1 
                    WHERE ID_user = %s AND Active = 2
                """, (operador,))
            
            conn.commit()
            cur.close()
            conn.close()
            
            cargar_operadores_rol()
            
        except Exception as e:
            print(f"[ERROR] deshabilitar_acceso: {e}")
            traceback.print_exc()
            messagebox.showerror("Error", f"Error al deshabilitar acceso:\n{e}", parent=top)

    def refrescar_lista_operadores():
        """Wrapper para refrescar la lista"""
        cargar_operadores_rol()

    # Botones de acción
    if UI is not None:
        UI.CTkButton(buttons_frame_rol, 
                    text="➡️ Habilitar Acceso a Covers",
                    command=habilitar_acceso,
                    fg_color="#00c853",
                    hover_color="#00a043",
                    width=220,
                    height=40,
                    font=("Segoe UI", 13, "bold")).pack(side="left", padx=10, pady=5)
        
        UI.CTkButton(buttons_frame_rol, 
                    text="⬅️ Quitar Acceso a Covers",
                    command=deshabilitar_acceso,
                    fg_color="#f04747",
                    hover_color="#d84040",
                    width=220,
                    height=40,
                    font=("Segoe UI", 13, "bold")).pack(side="left", padx=10, pady=5)
        
        UI.CTkButton(buttons_frame_rol, 
                    text="🔄 Refrescar Lista",
                    command=refrescar_lista_operadores,
                    fg_color="#4a90e2",
                    hover_color="#357ABD",
                    width=180,
                    height=40,
                    font=("Segoe UI", 13, "bold")).pack(side="left", padx=10, pady=5)
    else:
        tk.Button(buttons_frame_rol, 
                 text="➡️ Habilitar Acceso a Covers",
                 command=habilitar_acceso,
                 bg="#00c853",
                 fg="white",
                 font=("Segoe UI", 13, "bold"),
                 relief="flat",
                 width=24).pack(side="left", padx=10, pady=5)
        
        tk.Button(buttons_frame_rol, 
                 text="⬅️ Quitar Acceso a Covers",
                 command=deshabilitar_acceso,
                 bg="#f04747",
                 fg="white",
                 font=("Segoe UI", 13, "bold"),
                 relief="flat",
                 width=24).pack(side="left", padx=10, pady=5)
        
        tk.Button(buttons_frame_rol, 
                 text="🔄 Refrescar Lista",
                 command=refrescar_lista_operadores,
                 bg="#4a90e2",
                 fg="white",
                 font=("Segoe UI", 13, "bold"),
                 relief="flat",
                 width=18).pack(side="left", padx=10, pady=5)

    # ==================== COVER TIME CONTAINER ====================
    if UI is not None:
        cover_container = UI.CTkFrame(top, fg_color="#2c2f33")
    else:
        cover_container = tk.Frame(top, bg="#2c2f33")
    # NO hacer pack() aquí - se mostrará solo cuando se cambie a modo Cover Time

    # Frame de filtros para covers_realizados
    if UI is not None:
        cover_filters_frame = UI.CTkFrame(cover_container, fg_color="#23272a", corner_radius=8)
    else:
        cover_filters_frame = tk.Frame(cover_container, bg="#23272a")
    cover_filters_frame.pack(fill="x", padx=10, pady=10)

    # Variables de filtros
    cover_user_var = tk.StringVar()
    cover_desde_var = tk.StringVar()
    cover_hasta_var = tk.StringVar()

    # Fila de filtros
    if UI is not None:
        UI.CTkLabel(cover_filters_frame, text="Usuario:", text_color="#c9d1d9", 
                   font=("Segoe UI", 11)).grid(row=0, column=0, sticky="w", padx=(15, 5), pady=10)
    else:
        tk.Label(cover_filters_frame, text="Usuario:", bg="#23272a", fg="#c9d1d9", 
                font=("Segoe UI", 11)).grid(row=0, column=0, sticky="w", padx=(15, 5), pady=10)

    # Obtener usuarios para el filtro
    try:
        conn = under_super.get_connection()
        cur = conn.cursor()
        cur.execute("SELECT DISTINCT Nombre_usuarios FROM covers_realizados WHERE Nombre_usuarios IS NOT NULL ORDER BY Nombre_usuarios")
        cover_users = ["Todos"] + [r[0] for r in cur.fetchall()]
        cur.close()
        conn.close()
    except Exception:
        cover_users = ["Todos"]

    cover_user_cb = ttk.Combobox(cover_filters_frame, textvariable=cover_user_var, 
                                 values=cover_users, width=20, state="readonly")
    cover_user_cb.set("Todos")
    cover_user_cb.grid(row=0, column=1, sticky="w", padx=5, pady=10)

    if UI is not None:
        UI.CTkLabel(cover_filters_frame, text="Desde:", text_color="#c9d1d9", 
                   font=("Segoe UI", 11)).grid(row=0, column=2, sticky="w", padx=(15, 5), pady=10)
    else:
        tk.Label(cover_filters_frame, text="Desde:", bg="#23272a", fg="#c9d1d9", 
                font=("Segoe UI", 11)).grid(row=0, column=2, sticky="w", padx=(15, 5), pady=10)

    try:
        from tkcalendar import DateEntry
        cover_desde_entry = DateEntry(
            cover_filters_frame,
            textvariable=cover_desde_var,
            date_pattern="yyyy-mm-dd",
            width=15
        )
    except Exception:
        cover_desde_entry = tk.Entry(cover_filters_frame, textvariable=cover_desde_var, width=17)
    cover_desde_entry.grid(row=0, column=3, sticky="w", padx=5, pady=10)

    if UI is not None:
        UI.CTkLabel(cover_filters_frame, text="Hasta:", text_color="#c9d1d9", 
                   font=("Segoe UI", 11)).grid(row=0, column=4, sticky="w", padx=(15, 5), pady=10)
    else:
        tk.Label(cover_filters_frame, text="Hasta:", bg="#23272a", fg="#c9d1d9", 
                font=("Segoe UI", 11)).grid(row=0, column=4, sticky="w", padx=(15, 5), pady=10)

    try:
        from tkcalendar import DateEntry
        cover_hasta_entry = DateEntry(
            cover_filters_frame,
            textvariable=cover_hasta_var,
            date_pattern="yyyy-mm-dd",
            width=15
        )
    except Exception:
        cover_hasta_entry = tk.Entry(cover_filters_frame, textvariable=cover_hasta_var, width=17)
    cover_hasta_entry.grid(row=0, column=5, sticky="w", padx=5, pady=10)

    # Configuración de tablas y columnas
    candidate_tables = ["covers_programados", "covers_realizados"]
    Columnas_deseadas_covers = {
        "covers_programados": ["ID_user", "Time_request", "Station", "Reason", "Approved", "is_Active"],
        "covers_realizados": ["Nombre_usuarios", "Cover_in", "Cover_out", "Covered_by", "Motivo"]
    }

    # Variable para guardar referencia al sheet de covers_realizados
    cover_realizados_sheet_ref = None

    def load_cover_table(tabla):
        """Carga datos de una tabla de covers desde la BD"""
        try:
            conn = under_super.get_connection()
            cur = conn.cursor()
            query = f"SELECT * FROM {tabla}"
            cur.execute(query)
            rows = cur.fetchall()
            col_names = [desc[0] for desc in cur.description]
            cur.close()
            conn.close()
            return col_names, rows
        except Exception as e:
            print(f"[ERROR] load_cover_table({tabla}): {e}")
            return [], []

    def apply_cover_filters():
        """Aplica filtros a la tabla covers_realizados"""
        nonlocal cover_realizados_sheet_ref
        
        if cover_realizados_sheet_ref is None:
            messagebox.showwarning("Filtrar", "No hay datos de covers realizados cargados.", parent=top)
            return
        
        try:
            user_filter = cover_user_var.get().strip()
            desde_filter = cover_desde_var.get().strip()
            hasta_filter = cover_hasta_var.get().strip()
            
            conn = under_super.get_connection()
            cur = conn.cursor()
            
            sql = "SELECT Nombre_usuarios, Cover_in, Cover_out, Covered_by, Motivo FROM covers_realizados WHERE 1=1"
            params = []
            
            if user_filter and user_filter != "Todos":
                sql += " AND Nombre_usuarios = %s"
                params.append(user_filter)
            
            if desde_filter:
                sql += " AND DATE(Cover_in) >= %s"
                params.append(desde_filter)
            
            if hasta_filter:
                sql += " AND DATE(Cover_in) <= %s"
                params.append(hasta_filter)
            
            sql += " ORDER BY Cover_in DESC"
            
            cur.execute(sql, params)
            rows = cur.fetchall()
            cur.close()
            conn.close()
            
            # Procesar datos con duración
            filtered_data = []
            for row in rows:
                nombre_usuarios = row[0] if row[0] else ""
                cover_in = row[1]
                cover_out = row[2]
                covered_by = row[3] if row[3] else ""
                motivo = row[4] if row[4] else ""
                
                # Calcular duración
                duration_str = ""
                if cover_in and cover_out:
                    try:
                        from datetime import datetime, timedelta
                        if isinstance(cover_in, str):
                            cover_in = datetime.strptime(cover_in, "%Y-%m-%d %H:%M:%S")
                        if isinstance(cover_out, str):
                            cover_out = datetime.strptime(cover_out, "%Y-%m-%d %H:%M:%S")
                        
                        delta = cover_out - cover_in
                        hours, remainder = divmod(int(delta.total_seconds()), 3600)
                        minutes, seconds = divmod(remainder, 60)
                        duration_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
                    except Exception as e:
                        print(f"[ERROR] Error calculando duración: {e}")
                        duration_str = "Error"
                
                # Formatear datos para mostrar
                filtered_data.append([
                    nombre_usuarios,
                    str(cover_in) if cover_in else "",
                    duration_str,
                    str(cover_out) if cover_out else "",
                    covered_by,
                    motivo
                ])
            
            if not filtered_data:
                filtered_data = [["No hay resultados con estos filtros"] + [""] * 5]
            
            cover_realizados_sheet_ref.set_sheet_data(filtered_data)
            cover_realizados_sheet_ref.redraw()
            
            print(f"[DEBUG] Cover filters applied: {len(rows)} results")
            
        except Exception as e:
            messagebox.showerror("Error", f"Error aplicando filtros:\n{e}", parent=top)
            traceback.print_exc()

    def clear_cover_filters():
        """Limpia los filtros y recarga todos los datos"""
        nonlocal cover_realizados_sheet_ref
        
        cover_user_var.set("Todos")
        cover_desde_var.set("")
        cover_hasta_var.set("")
        
        if cover_realizados_sheet_ref is None:
            return
        
        # Recargar todos los datos
        try:
            col_names, rows = load_cover_table("covers_realizados")
            
            indices = [col_names.index(c) for c in Columnas_deseadas_covers["covers_realizados"] if c in col_names]
            
            cover_in_idx = None
            cover_out_idx = None
            if "Cover_in" in col_names:
                cover_in_idx = col_names.index("Cover_in")
            if "Cover_out" in col_names:
                cover_out_idx = col_names.index("Cover_out")
            
            filtered_data = []
            for row in rows:
                filtered_row = [row[idx] for idx in indices]
                
                if cover_in_idx is not None and cover_out_idx is not None:
                    cover_in = row[cover_in_idx]
                    cover_out = row[cover_out_idx]
                    
                    duration_str = ""
                    if cover_in and cover_out:
                        try:
                            from datetime import datetime, timedelta
                            if isinstance(cover_in, str):
                                cover_in = datetime.strptime(cover_in, "%Y-%m-%d %H:%M:%S")
                            if isinstance(cover_out, str):
                                cover_out = datetime.strptime(cover_out, "%Y-%m-%d %H:%M:%S")
                            
                            delta = cover_out - cover_in
                            hours, remainder = divmod(int(delta.total_seconds()), 3600)
                            minutes, seconds = divmod(remainder, 60)
                            duration_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
                        except Exception as e:
                            print(f"[ERROR] Error calculando duración: {e}")
                            duration_str = "Error"
                    
                    filtered_row = ["" if v is None else str(v) for v in filtered_row]
                    filtered_row.insert(2, duration_str)
                else:
                    filtered_row = ["" if v is None else str(v) for v in filtered_row]
                
                filtered_data.append(filtered_row)
            
            cover_realizados_sheet_ref.set_sheet_data(filtered_data)
            cover_realizados_sheet_ref.redraw()
            
        except Exception as e:
            print(f"[ERROR] clear_cover_filters: {e}")
            traceback.print_exc()

    # Botones de filtro
    cover_btn_frame = tk.Frame(cover_filters_frame, bg="#23272a")
    cover_btn_frame.grid(row=0, column=6, sticky="e", padx=(15, 15), pady=10)

    if UI is not None:
        UI.CTkButton(
            cover_btn_frame,
            text="🔍 Filtrar",
            command=apply_cover_filters,
            fg_color="#4a90e2",
            hover_color="#357ABD",
            width=100,
            height=32,
            font=("Segoe UI", 11, "bold")
        ).pack(side="left", padx=(0, 8))
        
        UI.CTkButton(
            cover_btn_frame,
            text="🗑️ Limpiar",
            command=clear_cover_filters,
            fg_color="#3b4754",
            hover_color="#4a5560",
            width=100,
            height=32,
            font=("Segoe UI", 11, "bold")
        ).pack(side="left")
    else:
        tk.Button(
            cover_btn_frame,
            text="🔍 Filtrar",
            command=apply_cover_filters,
            bg="#4a90e2",
            fg="white",
            activebackground="#357ABD",
            font=("Segoe UI", 11, "bold"),
            relief="flat",
            width=10
        ).pack(side="left", padx=(0, 8))
        
        tk.Button(
            cover_btn_frame,
            text="🗑️ Limpiar",
            command=clear_cover_filters,
            bg="#3b4754",
            fg="white",
            activebackground="#4a5560",
            font=("Segoe UI", 11, "bold"),
            relief="flat",
            width=10
        ).pack(side="left")

    # Crear TabView para covers_programados y covers_realizados
    if UI is not None:
        cover_notebook = UI.CTkTabview(cover_container, width=1280, height=650)
    else:
        cover_notebook = ttk.Notebook(cover_container)
    cover_notebook.pack(padx=10, pady=10, fill="both", expand=True)

    # Crear pestaña para cada tabla
    for tabla in candidate_tables:
        col_names, rows = load_cover_table(tabla)
        
        # Filtrar solo las columnas deseadas
        indices = [col_names.index(c) for c in Columnas_deseadas_covers[tabla] if c in col_names]
        filtered_col_names = [col_names[i] for i in indices]
        
        if not filtered_col_names:
            continue

        # Crear pestaña
        if UI is not None:
            tab = cover_notebook.add(tabla)
        else:
            tab = tk.Frame(cover_notebook, bg="#2c2f33")
            cover_notebook.add(tab, text=tabla)
        
        # Frame para el tksheet
        if UI is not None:
            sheet_frame_cover = UI.CTkFrame(tab, fg_color="#2c2f33")
        else:
            sheet_frame_cover = tk.Frame(tab, bg="#2c2f33")
        sheet_frame_cover.pack(fill="both", expand=True, padx=10, pady=10)

        # Headers personalizados en español
        program_headers = ["Usuario", "Hora solicitud", "Estación", "Razón", "Aprobado", "Activo"]
        realized_headers = ["Usuario", "Inicio Cover", "Duracion", "Fin Cover", "Cubierto por", "Motivo"]
        headers = program_headers if tabla == "covers_programados" else realized_headers

        # Crear tksheet
        cover_tab_sheet = SheetClass(
            sheet_frame_cover,
            headers=headers,
            theme="dark blue",
            height=550,
            width=1220,
            show_selected_cells_border=True,
            show_row_index=True,
            show_top_left=False,
            empty_horizontal=0,
            empty_vertical=0
        )
        
        # Configurar bindings (solo lectura con selección)
        cover_tab_sheet.enable_bindings([
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
        
        cover_tab_sheet.pack(fill="both", expand=True)
        cover_tab_sheet.change_theme("dark blue")
        
        # Guardar referencia al sheet de covers_realizados
        if tabla == "covers_realizados":
            cover_realizados_sheet_ref = cover_tab_sheet

        # Preparar datos filtrados
        filtered_data = []
        orig_is_idx = None
        if 'is_Active' in Columnas_deseadas_covers.get(tabla, []) and 'is_Active' in col_names:
            try:
                orig_is_idx = col_names.index('is_Active')
            except Exception:
                orig_is_idx = None

        # Para covers_realizados, necesitamos calcular la duración
        cover_in_idx = None
        cover_out_idx = None
        if tabla == "covers_realizados":
            try:
                if "Cover_in" in col_names:
                    cover_in_idx = col_names.index("Cover_in")
                if "Cover_out" in col_names:
                    cover_out_idx = col_names.index("Cover_out")
            except Exception:
                pass

        for row in rows:
            filtered_row = [row[idx] for idx in indices]
            
            # Si es covers_realizados, calcular e insertar duración
            if tabla == "covers_realizados" and cover_in_idx is not None and cover_out_idx is not None:
                cover_in = row[cover_in_idx]
                cover_out = row[cover_out_idx]
                
                # Calcular duración
                duration_str = ""
                if cover_in and cover_out:
                    try:
                        from datetime import datetime, timedelta
                        # Si son strings, convertir a datetime
                        if isinstance(cover_in, str):
                            cover_in = datetime.strptime(cover_in, "%Y-%m-%d %H:%M:%S")
                        if isinstance(cover_out, str):
                            cover_out = datetime.strptime(cover_out, "%Y-%m-%d %H:%M:%S")
                        
                        delta = cover_out - cover_in
                        hours, remainder = divmod(int(delta.total_seconds()), 3600)
                        minutes, seconds = divmod(remainder, 60)
                        duration_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
                    except Exception as e:
                        print(f"[ERROR] Error calculando duración: {e}")
                        duration_str = "Error"
                
                # Convertir valores None a string vacío
                filtered_row = ["" if v is None else str(v) for v in filtered_row]
                
                # Insertar duración en la posición correcta (después de Cover_in, antes de Cover_out)
                # Headers: ["Usuario", "Inicio Cover", "Duracion", "Fin Cover", "Cubierto por", "Motivo"]
                # filtered_row: [Usuario, Cover_in, Cover_out, Covered_by, Motivo]
                # Necesitamos insertar duration_str en el índice 2
                filtered_row.insert(2, duration_str)
            else:
                # Convertir valores None a string vacío
                filtered_row = ["" if v is None else str(v) for v in filtered_row]
            
            filtered_data.append(filtered_row)

        # Insertar datos en el sheet
        cover_tab_sheet.set_sheet_data(filtered_data)

        # Aplicar formato a filas inactivas (is_Active == 0)
        if orig_is_idx is not None:
            try:
                filtered_is_idx = indices.index(orig_is_idx)
                for i, row in enumerate(rows):
                    if row[orig_is_idx] == 0:
                        # Aplicar resaltado gris a toda la fila
                        cover_tab_sheet.highlight_rows([i], bg="#3a3a3a", fg="#808080")
            except (ValueError, Exception):
                pass
        
        # Ajustar anchos de columna
        for idx, col_name in enumerate(filtered_col_names):
            if col_name in ["ID_user", "Station", "Approved", "is_Active"]:
                cover_tab_sheet.column_width(column=idx, width=100)
            elif col_name in ["Time_request", "Cover_in", "Cover_out"]:
                cover_tab_sheet.column_width(column=idx, width=150)
            elif col_name in ["Reason", "Motivo"]:
                cover_tab_sheet.column_width(column=idx, width=200)
            else:
                cover_tab_sheet.column_width(column=idx, width=120)
        
        cover_tab_sheet.redraw()
    
    # Frame de filtros de Cover Time (lo dejamos oculto ya que ahora tenemos tabs)
    if UI is not None:
        cover_filters = UI.CTkFrame(cover_container, fg_color="#23272a", corner_radius=8)
    else:
        cover_filters = tk.Frame(cover_container, bg="#23272a")
    # NO hacer pack - los filtros ya no se usan con el nuevo diseño de tabs
    
    # ⭐ El código antiguo de filtros y búsqueda ha sido reemplazado por el sistema de tabs con tksheet

    # ==================== TOOLBAR (Footer) - Eliminado, Cover Time ahora es modo integrado ====================
    # Ya no necesitamos toolbar, Cover Time es un modo como Audit

    # Vincular eventos
    sheet.bind("<Button-3>", show_context_menu)  # Menú contextual
    sheet.bind("<Double-Button-1>", lambda e: mark_as_done())  # Doble-click marca como "Registrado"

    
# ⭐ CONFIGURAR CIERRE DE VENTANA: Ejecutar logout automáticamente
    def on_window_close_super():
        """Maneja el cierre de la ventana principal ejecutando logout y mostrando login"""
        try:
            if session_id and station:
                login.do_logout(session_id, station, top)
            if not session_id:
                try:
                    login.show_login()
                    top.destroy()
                except Exception as e:
                    print(f"[ERROR] Error during logout: {e}")
        except Exception as e:
            print(f"[ERROR] Error destroying window: {e}")
    # Configurar protocolo de cierre (botón X)
    top.protocol("WM_DELETE_WINDOW", on_window_close_super)


# nueva implementacion: status de supervisores
# fin de la implementaicon de statuses 
# modificable y con efecto en operadores


def get_user_status(username):
    try:
        
        status_value = under_super.get_user_status_bd(username)
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


def open_hybrid_events_lead_supervisor(username, session_id=None, station=None, root=None):
    """
    🚀 VENTANA HÍBRIDA PARA LEAD SUPERVISORS: Visualización de Specials con permisos de eliminación
    
    Similar a supervisores pero con permisos adicionales:
    - Visualización de specials del turno actual
    - Botones: Refrescar, Eliminar (con permisos completos)
    - Marcas persistentes (Registrado, En Progreso)
    - Auto-logout al cerrar ventana
    """
    # Singleton
    ex = _focus_singleton('hybrid_events_lead_supervisor')
    if ex:
        return ex

    # CustomTkinter setup
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

    # tksheet setup
    USE_SHEET = False
    SheetClass = None
    try:
        from tksheet import Sheet as _Sheet
        SheetClass = _Sheet
        USE_SHEET = True
    except Exception:
        messagebox.showerror("Error", "tksheet no está instalado.\nInstala con: pip install tksheet")
        return

    # Crear ventana principal
    if UI is not None:
        top = UI.CTkToplevel()
        top.configure(fg_color="#1e1e1e")
    else:
        top = tk.Toplevel()
        top.configure(bg="#1e1e1e")
    
    top.title(f"👔 Lead Supervisor - Specials - {username}")
    top.geometry("1350x800")
    top.resizable(True, True)

    # Variables de estado
    row_data_cache = []  # Cache de datos
    row_ids = []  # IDs de specials
    auto_refresh_active = tk.BooleanVar(value=True)
    refresh_job = None

    # Columnas
    columns = [" ", "Sitio", "Actividad", "Cantidad", "Camera", "Descripcion", "Usuario", "TZ", "Marca", "Marcado Por"]
    
    # Anchos personalizados
    custom_widths = {
        " ": 150,
        "Sitio": 220,
        "Actividad": 150,
        "Cantidad": 70,
        "Camera": 80,
        "Descripcion": 160,
        "Usuario": 100,
        "TZ": 90,
        "Marca": 150,
        "Marcado Por": 150
    }

    # ==================== FUNCIONES DE DATOS ====================
    
    def load_data():
        """Carga los specials de la tabla specials (filtrados por Lead Supervisor y fecha de START SHIFT)"""
        try:
            conn = under_super.get_connection()
            cursor = conn.cursor()
            
            # Obtener el último START SHIFT del Lead Supervisor (desde tabla Eventos)
            cursor.execute("""
                SELECT e.FechaHora 
                FROM Eventos e
                INNER JOIN user u ON e.ID_Usuario = u.ID_Usuario
                WHERE u.Nombre_Usuario = %s AND e.Nombre_Actividad = 'START SHIFT'
                ORDER BY e.FechaHora DESC
                LIMIT 1
            """, (username,))
            result = cursor.fetchone()
            
            if not result:
                print(f"[INFO] No hay turno activo para {username}")
                sheet.set_sheet_data([["No hay shift activo"] + [""] * (len(columns)-1)])
                row_data_cache.clear()
                row_ids.clear()
                cursor.close()
                conn.close()
                return
            
            fecha_inicio = result[0]
            
            # ⭐ Query desde tabla specials filtrada por Lead Supervisor y fecha
            # Muestra todos los specials asignados a este Lead Supervisor desde su último START SHIFT
            sql = """
                SELECT 
                    s.ID_special,
                    s.FechaHora,
                    s.ID_Sitio,
                    s.Nombre_Actividad,
                    s.Cantidad,
                    s.Camera,
                    s.Descripcion,
                    s.Usuario,
                    s.Time_Zone,
                    s.marked_status,
                    s.marked_by
                FROM specials s
                WHERE s.Supervisor = %s
                  AND s.FechaHora >= %s
                ORDER BY s.FechaHora DESC
            """
            
            cursor.execute(sql, (username, fecha_inicio))
            rows = cursor.fetchall()
            
            # Formatear datos
            data = []
            row_ids.clear()
            row_status = []  # Para almacenar el estado de marca de cada fila
            
            for row in rows:
                row_ids.append(row[0])  # ID_special
                row_status.append(row[9])  # marked_status (para coloreo)
                
                # Resolver nombre de sitio si es ID numérico
                sitio_display = ""
                if row[2]:  # ID_Sitio
                    try:
                        cursor.execute("SELECT Nombre_Sitio FROM Sitios WHERE ID_Sitio = %s", (row[2],))
                        sitio_row = cursor.fetchone()
                        if sitio_row:
                            sitio_display = f"{row[2]} {sitio_row[0]}"
                        else:
                            sitio_display = str(row[2])
                    except Exception:
                        sitio_display = str(row[2]) if row[2] else ""
                
                # Determinar estado de marca
                marca_status = "Sin Marca"
                if row[9]:  # marked_status
                    if row[9] == 'done':
                        marca_status = "✅ Registrado"
                    elif row[9] == 'flagged':
                        marca_status = "🔄 En Progreso"
                    else:
                        marca_status = str(row[9])
                
                # ⭐ Mostrar quién marcó el evento (marked_by)
                marked_by_display = ""
                if row[10]:  # marked_by (quien lo marcó)
                    marked_by_display = str(row[10])
                else:
                    marked_by_display = "Sin Marcar"
                
                formatted_row = [
                    str(row[1]) if row[1] else "",  #  
                    sitio_display,  # Sitio (resuelto)
                    str(row[3]) if row[3] else "",  # Actividad
                    str(row[4]) if row[4] else "",  # Cantidad
                    str(row[5]) if row[5] else "",  # Camera
                    str(row[6]) if row[6] else "",  # Descripcion
                    str(row[7]) if row[7] else "",  # Usuario
                    str(row[8]) if row[8] else "",  # Time_Zone
                    marca_status,  # Marca (procesada)
                    marked_by_display  # ⭐ NUEVO: Quién marcó el evento
                ]
                data.append(formatted_row)
            
            row_data_cache.clear()
            # Actualizar tksheet
            sheet.set_sheet_data(data if data else [["No hay specials asignados"] + [""] * (len(columns)-1)])
            
            # Aplicar anchos personalizados
            for col_idx, col_name in enumerate(columns):
                if col_name in custom_widths:
                    sheet.column_width(column=col_idx, width=custom_widths[col_name])
            
            # ⭐ CRÍTICO: Limpiar TODOS los colores antes de aplicar nuevos
            sheet.dehighlight_all()
            
            # Aplicar coloreo de filas según marked_status
            # Solo colorear filas que tienen marca, las nuevas (sin marca) quedan sin color
            for row_idx, status in enumerate(row_status):
                if status == 'done':
                    # Verde para registrado
                    sheet.highlight_rows(rows=[row_idx], bg="#00c853", fg="#111111", redraw=False)
                elif status == 'flagged':
                    # Ámbar/Naranja para en progreso
                    sheet.highlight_rows(rows=[row_idx], bg="#f5a623", fg="#111111", redraw=False)
                # Sin marca (None o NULL) = color por defecto del tema (no aplicar highlight)
            
            sheet.refresh()  # Refrescar una sola vez al final
            
            cursor.close()
            conn.close()
            
            print(f"[INFO] Cargados {len(data)} specials para Lead Supervisor {username}")
            
            print(f"[INFO] Cargados {len(data)} specials para Lead Supervisor {username}")
            
        except Exception as e:
            print(f"[ERROR] load_data: {e}")
            traceback.print_exc()
            messagebox.showerror("Error", f"Error al cargar datos:\n{e}", parent=top)

    def delete_selected():
        """Elimina los specials seleccionados (con permisos de Lead Supervisor) usando safe_delete"""
        try:
            selected = sheet.get_selected_rows()
            if not selected:
                messagebox.showwarning("Advertencia", "Selecciona al menos una fila para eliminar", parent=top)
                return
            
            # Confirmar eliminación
            count = len(selected)
            confirm = messagebox.askyesno(
                "Confirmar Eliminación",
                f"¿Mover {count} special(s) a la papelera?\n\n💡 Podrán ser recuperados desde el sistema de auditoría.",
                parent=top
            )
            
            if not confirm:
                return
            
            deleted_count = 0
            failed_count = 0
            
            for row_idx in selected:
                if row_idx < len(row_ids):
                    special_id = row_ids[row_idx]
                    try:
                        # ⭐ Usar safe_delete para mover a papelera
                        success = safe_delete(
                            table_name="specials",
                            pk_column="ID_special",
                            pk_value=special_id,
                            deleted_by=username,
                            reason=f"Eliminado por Lead Supervisor desde 'Todos los eventos'"
                        )
                        
                        if success:
                            deleted_count += 1
                        else:
                            failed_count += 1
                            print(f"[WARN] No se pudo mover special {special_id} a papelera")
                            
                    except Exception as e:
                        failed_count += 1
                        print(f"[ERROR] Error al eliminar special {special_id}: {e}")
            
            # Mostrar resultado
            if deleted_count > 0:
                if failed_count > 0:
                    messagebox.showinfo("Éxito", 
                                       f"✅ {deleted_count} special(s) movido(s) a papelera correctamente", 
                                       parent=top)
            else:
                messagebox.showerror("Error", "No se pudo eliminar ningún registro", parent=top)
            
            load_data()
            
        except Exception as e:
            print(f"[ERROR] delete_selected: {e}")
            traceback.print_exc()
            messagebox.showerror("Error", f"Error al eliminar:\n{e}", parent=top)

    # ==================== UI COMPONENTS ====================
    
    # ⭐ FUNCIÓN: Manejar Start/End Shift
    def handle_shift_button():
        """Maneja el click en el botón Start/End Shift"""
        try:
            is_start = Dinamic_button_Shift(username)
            
            if is_start:
                success = on_start_shift(username, parent_window=top)
                if success:
                    update_shift_button()
                    load_data()
            else:
                on_end_shift(username)
                update_shift_button()
                load_data()
            
        except Exception as e:
            messagebox.showerror("Error", f"Error al cambiar turno:\n{e}", parent=top)
            print(f"[ERROR] handle_shift_button: {e}")
            traceback.print_exc()
    
    def update_shift_button():
        """Actualiza el texto y color del botón según el estado del turno"""
        try:
            is_start = Dinamic_button_Shift(username)
            
            if is_start:
                if UI is not None:
                    shift_btn.configure(text="🚀 Start Shift", 
                                       fg_color="#00c853", 
                                       hover_color="#00a043")
                else:
                    shift_btn.configure(text="🚀 Start Shift", bg="#00c853")
            else:
                if UI is not None:
                    shift_btn.configure(text="🏁 End of Shift", 
                                       fg_color="#d32f2f", 
                                       hover_color="#b71c1c")
                else:
                    shift_btn.configure(text="🏁 End of Shift", bg="#d32f2f")
        except Exception as e:
            print(f"[ERROR] update_shift_button: {e}")
    
    # Header
    if UI is not None:
        header = UI.CTkFrame(top, fg_color="#23272a", corner_radius=0)
    else:
        header = tk.Frame(top, bg="#23272a")
    header.pack(fill="x", padx=0, pady=0)

    if UI is not None:
        UI.CTkLabel(header, text=f"👔 Lead Supervisor: {username}", 
                   font=("Segoe UI", 16, "bold"), 
                   text_color="#e0e0e0").pack(side="left", padx=20, pady=15)
        
        # ⭐ INDICADOR DE STATUS CON DROPDOWN (a la derecha, antes del botón Shift)
        status_frame = UI.CTkFrame(header, fg_color="transparent")
        status_frame.pack(side="right", padx=(5, 10), pady=15)
        
        # Obtener status actual del usuario
        current_status_bd = under_super.get_user_status_bd(username)
        
        # Mapear el status a texto legible
        if current_status_bd == 1:
            status_text = "🟢 Disponible"
        elif current_status_bd == 0:
            status_text = "🟡 Ocupado"
        elif current_status_bd == -1:
            status_text = "🔴 No disponible"
        else:
            status_text = "⚪ Desconocido"
        
        status_label = UI.CTkLabel(status_frame, text=status_text, 
                                   font=("Segoe UI", 12, "bold"))
        status_label.pack(side="left", padx=(0, 8))
        
        btn_emoji_green = "🟢"
        btn_emoji_yellow = "🟡"
        btn_emoji_red = "🔴"
        
        def update_status_label(new_value):
            """Actualiza el label y el status en la BD"""
            under_super.set_new_status(new_value, username)
            # Actualizar el texto del label
            if new_value == 1:
                status_label.configure(text="🟢 Disponible")
            elif new_value == 2:
                status_label.configure(text="🟡 Ocupado")
            elif new_value == -1:
                status_label.configure(text="🔴 No disponible")
        
        status_btn_green = UI.CTkButton(status_frame, text=btn_emoji_green, command=lambda:(update_status_label(1), username),
                    fg_color="#00c853", hover_color="#00a043",
                    width=45, height=38,
                    font=("Segoe UI", 16, "bold"))
        status_btn_green.pack(side="left")    

        status_btn_yellow = UI.CTkButton(status_frame, text=btn_emoji_yellow, command=lambda: (update_status_label(2), username),
                    fg_color="#f5a623", hover_color="#e69515",
                    width=45, height=38,
                    font=("Segoe UI", 16, "bold"))
        status_btn_yellow.pack(side="left")

        status_btn_red = UI.CTkButton(status_frame, text=btn_emoji_red, command=lambda: (update_status_label(-1), username),
                    fg_color="#d32f2f", hover_color="#b71c1c",
                    width=45, height=38,
                    font=("Segoe UI", 16, "bold"))
        status_btn_red.pack(side="left")
        
        # ⭐ Botón Start/End Shift a la derecha
        shift_btn = UI.CTkButton(
            header, 
            text="🚀 Start Shift",
            command=handle_shift_button,
            width=160, 
            height=40,
            font=("Segoe UI", 14, "bold"),
            fg_color="#00c853",
            hover_color="#00a043"
        )
        shift_btn.pack(side="right", padx=(5, 20), pady=15)
        
        # Botones de acción
        UI.CTkButton(header, text="🔄 Refrescar", command=load_data,
                    fg_color="#4D6068", hover_color="#27a3e0", 
                    width=120, height=40,
                    font=("Segoe UI", 12, "bold")).pack(side="right", padx=5, pady=15)
        
        UI.CTkButton(header, text="🗑️ Eliminar", command=delete_selected,
                    fg_color="#d32f2f", hover_color="#b71c1c", 
                    width=120, height=40,
                    font=("Segoe UI", 12, "bold")).pack(side="right", padx=5, pady=15)
    else:
        tk.Label(header, text=f"👔 Lead Supervisor: {username}", 
                bg="#23272a", fg="#e0e0e0",
                font=("Segoe UI", 16, "bold")).pack(side="left", padx=20, pady=15)
        
        # ⭐ Botón Start/End Shift (Tkinter fallback)
        shift_btn = tk.Button(
            header,
            text="� Start Shift",
            command=handle_shift_button,
            bg="#00c853",
            fg="white",
            font=("Segoe UI", 12, "bold"),
            relief="flat",
            width=15
        )
        shift_btn.pack(side="right", padx=(5, 20), pady=15)
        
        tk.Button(header, text="�🔄 Refrescar", command=load_data,
                 bg="#666666", fg="white",
                 font=("Segoe UI", 12, "bold"), relief="flat",
                 width=12).pack(side="right", padx=5, pady=15)
        
        tk.Button(header, text="🗑️ Eliminar", command=delete_selected,
                 bg="#d32f2f", fg="white",
                 font=("Segoe UI", 12, "bold"), relief="flat",
                 width=12).pack(side="right", padx=5, pady=15)
    
    # Actualizar botón al iniciar
    update_shift_button()

    # Separador
    try:
        ttk.Separator(top, orient="horizontal").pack(fill="x")
    except Exception:
        pass

    # ==================== BARRA DE NAVEGACIÓN TIPO TABS ====================
    current_view = {'value': 'all_events'}  # 'all_events', 'unassigned_specials', 'audit', 'cover_time', 'admin'
    
    if UI is not None:
        nav_frame = UI.CTkFrame(top, fg_color="#23272a", corner_radius=0, height=50)
    else:
        nav_frame = tk.Frame(top, bg="#23272a", height=50)
    nav_frame.pack(fill="x", padx=0, pady=0)
    nav_frame.pack_propagate(False)

    def switch_view(new_view):
        """Cambia entre las 7 vistas disponibles"""
        current_view['value'] = new_view
        
        # Ocultar todos los containers
        main_container.pack_forget()
        unassigned_container.pack_forget()
        audit_container.pack_forget()
        cover_container.pack_forget()
        admin_container.pack_forget()
        rol_cover_container.pack_forget()
        breaks_container.pack_forget()
        
        # Resetear colores de botones
        inactive_color = "#3b4754"
        inactive_hover = "#4a5560"
        active_color = "#4a90e2"
        active_hover = "#357ABD"
        # Mostrar container activo y resaltar botón
        if new_view == 'all_events':
            main_container.pack(fill="both", expand=True, padx=10, pady=10)
            if UI is not None:
                btn_all_events.configure(fg_color=active_color, hover_color=active_hover)
            else:
                btn_all_events.configure(bg=active_color, activebackground=active_hover)
            # Forzar actualización del sheet para evitar desalineamiento
            top.update_idletasks()
            sheet.refresh()
            load_data()
        elif new_view == 'unassigned_specials':
            unassigned_container.pack(fill="both", expand=True, padx=10, pady=10)
            if UI is not None:
                btn_unassigned.configure(fg_color=active_color, hover_color=active_hover)
            else:
                btn_unassigned.configure(bg=active_color, activebackground=active_hover)
            # Forzar actualización del sheet para evitar desalineamiento
            top.update_idletasks()
            unassigned_sheet.refresh()
            load_unassigned_specials()
        elif new_view == 'audit':
            audit_container.pack(fill="both", expand=True, padx=10, pady=10)
            if UI is not None:
                btn_audit.configure(fg_color=active_color, hover_color=active_hover)
            else:
                btn_audit.configure(bg=active_color, activebackground=active_hover)
            # Forzar actualización del sheet para evitar desalineamiento
            top.update_idletasks()
            audit_sheet.refresh()
            # No auto-cargar audit, usuario debe usar filtros
        elif new_view == 'cover_time':
            cover_container.pack(fill="both", expand=True, padx=10, pady=10)
            if UI is not None:
                btn_cover.configure(fg_color=active_color, hover_color=active_hover)
            else:
                btn_cover.configure(bg=active_color, activebackground=active_hover)
            # Forzar actualización del sheet para evitar desalineamiento
            top.update_idletasks()
            cover_sheet.refresh()
            # No auto-cargar cover time, usuario debe usar filtros
        elif new_view == 'admin':
            admin_container.pack(fill="both", expand=True, padx=10, pady=10)
            if UI is not None:
                btn_admin.configure(fg_color=active_color, hover_color=active_hover)
            else:
                btn_admin.configure(bg=active_color, activebackground=active_hover)
            # Forzar actualización
            top.update_idletasks()
            # No auto-cargar, el usuario selecciona qué tabla ver
        elif new_view == 'rol_cover':
            rol_cover_container.pack(fill="both", expand=True, padx=10, pady=10)
            if UI is not None:
                btn_rol_cover.configure(fg_color=active_color, hover_color=active_hover)
            else:
                btn_rol_cover.configure(bg=active_color, activebackground=active_hover)
            # Cargar operadores al mostrar la vista
            top.update_idletasks()
            cargar_operadores_rol()
        elif new_view == 'breaks':
            breaks_container.pack(fill="both", expand=True, padx=10, pady=10)
            if UI is not None:
                btn_breaks.configure(fg_color=active_color, hover_color=active_hover)
            else:
                btn_breaks.configure(bg=active_color, activebackground=active_hover)
            # Forzar actualización y refrescar tabla de breaks
            top.update_idletasks()
            if USE_SHEET:
                breaks_sheet.refresh()
                refrescar_tabla_breaks()

    # Botones de navegación
    if UI is not None:
        btn_all_events = UI.CTkButton(
            nav_frame, 
            text="📊 Todos los Eventos", 
            command=lambda: switch_view('all_events'),
            fg_color="#4a90e2",
            hover_color="#357ABD",
            width=150,
            height=35,
            font=("Segoe UI", 12, "bold")
        )
        btn_all_events.pack(side="left", padx=(20, 5), pady=8)
        
        btn_unassigned = UI.CTkButton(
            nav_frame, 
            text="⚠️ Specials Sin Marcar", 
            command=lambda: switch_view('unassigned_specials'),
            fg_color="#3b4754",
            hover_color="#4a5560",
            width=180,
            height=35,
            font=("Segoe UI", 12, "bold")
        )
        btn_unassigned.pack(side="left", padx=5, pady=8)
        
        btn_audit = UI.CTkButton(
            nav_frame, 
            text="📋 Audit", 
            command=lambda: switch_view('audit'),
            fg_color="#3b4754",
            hover_color="#4a5560",
            width=120,
            height=35,
            font=("Segoe UI", 12, "bold")
        )
        btn_audit.pack(side="left", padx=5, pady=8)
        
        btn_cover = UI.CTkButton(
            nav_frame, 
            text="⏰ Cover Time", 
            command=lambda: switch_view('cover_time'),
            fg_color="#3b4754",
            hover_color="#4a5560",
            width=140,
            height=35,
            font=("Segoe UI", 12, "bold")
        )
        btn_cover.pack(side="left", padx=5, pady=8)
        
        btn_admin = UI.CTkButton(
            nav_frame, 
            text="🔧 Admin", 
            command=lambda: switch_view('admin'),
            fg_color="#3b4754",
            hover_color="#4a5560",
            width=120,
            height=35,
            font=("Segoe UI", 12, "bold")
        )
        btn_admin.pack(side="left", padx=5, pady=8)
        
        btn_rol_cover = UI.CTkButton(
            nav_frame, 
            text="🎭 Rol de Cover", 
            command=lambda: switch_view('rol_cover'),
            fg_color="#3b4754",
            hover_color="#4a5560",
            width=140,
            height=35,
            font=("Segoe UI", 12, "bold")
        )
        btn_rol_cover.pack(side="left", padx=5, pady=8)
        
        btn_breaks = UI.CTkButton(
            nav_frame, 
            text="☕ Breaks", 
            command=lambda: switch_view('breaks'),
            fg_color="#3b4754",
            hover_color="#4a5560",
            width=120,
            height=35,
            font=("Segoe UI", 12, "bold")
        )
        btn_breaks.pack(side="left", padx=5, pady=8)
    else:
        btn_all_events = tk.Button(
            nav_frame,
            text="📊 Todos los Eventos",
            command=lambda: switch_view('all_events'),
            bg="#4a90e2",
            fg="white",
            activebackground="#357ABD",
            font=("Segoe UI", 12, "bold"),
            relief="flat",
            width=17
        )
        btn_all_events.pack(side="left", padx=(20, 5), pady=8)
        
        btn_unassigned = tk.Button(
            nav_frame,
            text="⚠️ Specials Sin Marcar",
            command=lambda: switch_view('unassigned_specials'),
            bg="#3b4754",
            fg="white",
            activebackground="#4a5560",
            font=("Segoe UI", 12, "bold"),
            relief="flat",
            width=20
        )
        btn_unassigned.pack(side="left", padx=5, pady=8)
        
        btn_audit = tk.Button(
            nav_frame,
            text="📋 Audit",
            command=lambda: switch_view('audit'),
            bg="#3b4754",
            fg="white",
            activebackground="#4a5560",
            font=("Segoe UI", 12, "bold"),
            relief="flat",
            width=12
        )
        btn_audit.pack(side="left", padx=5, pady=8)
        
        btn_cover = tk.Button(
            nav_frame,
            text="⏰ Cover Time",
            command=lambda: switch_view('cover_time'),
            bg="#3b4754",
            fg="white",
            activebackground="#4a5560",
            font=("Segoe UI", 12, "bold"),
            relief="flat",
            width=15
        )
        btn_cover.pack(side="left", padx=5, pady=8)
        
        btn_admin = tk.Button(
            nav_frame,
            text="🔧 Admin",
            command=lambda: switch_view('admin'),
            bg="#3b4754",
            fg="white",
            activebackground="#4a5560",
            font=("Segoe UI", 12, "bold"),
            relief="flat",
            width=12
        )
        btn_admin.pack(side="left", padx=5, pady=8)
        
        btn_rol_cover = tk.Button(
            nav_frame,
            text="🎭 Rol de Cover",
            command=lambda: switch_view('rol_cover'),
            bg="#3b4754",
            fg="white",
            activebackground="#4a5560",
            font=("Segoe UI", 12, "bold"),
            relief="flat",
            width=15
        )
        btn_rol_cover.pack(side="left", padx=5, pady=8)
        
        btn_breaks = tk.Button(
            nav_frame,
            text="☕ Breaks",
            command=lambda: switch_view('breaks'),
            bg="#3b4754",
            fg="white",
            activebackground="#4a5560",
            font=("Segoe UI", 12, "bold"),
            relief="flat",
            width=12
        )
        btn_breaks.pack(side="left", padx=5, pady=8)
        btn_cover.pack(side="left", padx=5, pady=8)
        
        btn_admin = tk.Button(
            nav_frame,
            text="🔧 Admin",
            command=lambda: switch_view('admin'),
            bg="#3b4754",
            fg="white",
            activebackground="#4a5560",
            font=("Segoe UI", 12, "bold"),
            relief="flat",
            width=12
        )
        btn_admin.pack(side="left", padx=5, pady=8)
        
        btn_rol_cover = tk.Button(
            nav_frame,
            text="🎭 Rol de Cover",
            command=lambda: switch_view('rol_cover'),
            bg="#3b4754",
            fg="white",
            activebackground="#4a5560",
            font=("Segoe UI", 12, "bold"),
            relief="flat",
            width=15
        )
        btn_rol_cover.pack(side="left", padx=5, pady=8)

    # Separador después de navegación
    try:
        ttk.Separator(top, orient="horizontal").pack(fill="x")
    except Exception:
        pass

    # Container principal (todos los eventos)
    if UI is not None:
        main_container = UI.CTkFrame(top, fg_color="#2c2f33")
    else:
        main_container = tk.Frame(top, bg="#2c2f33")
    # No hacer pack aquí, se hace en switch_view()
    
    # Frame para el sheet dentro del main_container
    if UI is not None:
        sheet_frame = UI.CTkFrame(main_container, fg_color="#2c2f33")
    else:
        sheet_frame = tk.Frame(main_container, bg="#2c2f33")
    sheet_frame.pack(fill="both", expand=True)

    # Crear tksheet para eventos
    sheet = SheetClass(
        sheet_frame,
        headers=columns,
        theme="dark blue",
        height=600,
        width=1350,
        show_selected_cells_border=True,
        show_row_index=True,
        show_top_left=False,
        empty_horizontal=0,
        empty_vertical=0,
        auto_resize_columns=False,
        auto_resize_rows=False
    )
    # Deshabilitar menú contextual - solo permitir selección y navegación
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

    # Aplicar anchos iniciales
    for col_idx, col_name in enumerate(columns):
        if col_name in custom_widths:
            sheet.column_width(column=col_idx, width=custom_widths[col_name])

    # ==================== TOOLBAR DE MARCAS (Para "Todos los Eventos") ====================
    
    if UI is not None:
        marks_toolbar = UI.CTkFrame(main_container, fg_color="#23272a", corner_radius=0, height=60)
    else:
        marks_toolbar = tk.Frame(main_container, bg="#23272a", height=60)
    marks_toolbar.pack(fill="x", side="bottom", padx=0, pady=0)
    marks_toolbar.pack_propagate(False)
    
    def mark_selected_as_done():
        """Marca los eventos seleccionados como 'Registrado'"""
        try:
            selected = sheet.get_selected_rows()
            if not selected:
                messagebox.showwarning("Advertencia", "Selecciona al menos un evento para marcar", parent=top)
                return
            
            conn = under_super.get_connection()
            cursor = conn.cursor()
            
            marked_count = 0
            for row_idx in selected:
                if row_idx < len(row_ids):
                    event_id = row_ids[row_idx]
                    try:
                        # Marcar en tabla specials (si existe)
                        cursor.execute("""
                            UPDATE specials 
                            SET marked_status = 'done', marked_at = NOW(), marked_by = %s
                            WHERE ID_special = %s
                        """, (username, event_id))
                        marked_count += cursor.rowcount
                    except Exception as e:
                        print(f"[WARNING] No se pudo marcar evento {event_id}: {e}")
            
            conn.commit()
            cursor.close()
            conn.close()
            
            if marked_count > 0:
                load_data()
            else:
                messagebox.showinfo("Info", "Los eventos seleccionados no están en la tabla specials", parent=top)
            
        except Exception as e:
            print(f"[ERROR] mark_selected_as_done: {e}")
            traceback.print_exc()
            messagebox.showerror("Error", f"Error al marcar:\n{e}", parent=top)
    
    def mark_selected_as_progress():
        """Marca los eventos seleccionados como 'En Progreso'"""
        try:
            selected = sheet.get_selected_rows()
            if not selected:
                messagebox.showwarning("Advertencia", "Selecciona al menos un evento para marcar", parent=top)
                return
            
            conn = under_super.get_connection()
            cursor = conn.cursor()
            
            marked_count = 0
            for row_idx in selected:
                if row_idx < len(row_ids):
                    event_id = row_ids[row_idx]
                    try:
                        # Marcar en tabla specials (si existe)
                        cursor.execute("""
                            UPDATE specials 
                            SET marked_status = 'flagged', marked_at = NOW(), marked_by = %s
                            WHERE ID_special = %s
                        """, (username, event_id))
                        marked_count += cursor.rowcount
                    except Exception as e:
                        print(f"[WARNING] No se pudo marcar evento {event_id}: {e}")
            
            conn.commit()
            cursor.close()
            conn.close()
            
            if marked_count > 0:
                load_data()
            else:
                messagebox.showinfo("Info", "Los eventos seleccionados no están en la tabla specials", parent=top)
            
        except Exception as e:
            print(f"[ERROR] mark_selected_as_progress: {e}")
            traceback.print_exc()
            messagebox.showerror("Error", f"Error al marcar:\n{e}", parent=top)
    
    # Botones del toolbar de marcas
    if UI is not None:
        UI.CTkButton(marks_toolbar, text="✅ Marcar como Registrado", 
                    command=mark_selected_as_done,
                    fg_color="#00c853", hover_color="#00a043",
                    width=180, height=40, font=("Segoe UI", 11, "bold")).pack(side="left", padx=(20, 10), pady=10)
        
        UI.CTkButton(marks_toolbar, text="🔄 Marcar como En Progreso", 
                    command=mark_selected_as_progress,
                    fg_color="#ff9800", hover_color="#f57c00",
                    width=200, height=40, font=("Segoe UI", 11, "bold")).pack(side="left", padx=10, pady=10)
    else:
        tk.Button(marks_toolbar, text="✅ Marcar como Registrado", 
                 command=mark_selected_as_done,
                 bg="#00c853", fg="white", font=("Segoe UI", 11, "bold"),
                 relief="flat", width=20).pack(side="left", padx=(20, 10), pady=10)
        
        tk.Button(marks_toolbar, text="🔄 Marcar como En Progreso", 
                 command=mark_selected_as_progress,
                 bg="#ff9800", fg="white", font=("Segoe UI", 11, "bold"),
                 relief="flat", width=22).pack(side="left", padx=10, pady=10)

    # ==================== CONTAINER DE SPECIALS SIN ASIGNAR ====================
    
    if UI is not None:
        unassigned_container = UI.CTkFrame(top, fg_color="#2c2f33")
    else:
        unassigned_container = tk.Frame(top, bg="#2c2f33")
    # No hacer pack aquí, se hace en switch_view()
    
    # Columnas para specials (basado en tabla specials)
    columns_specials = ["ID", " ", "Sitio", "Actividad", "Cantidad", "Camera", "Descripcion", "Usuario", "TZ", "Supervisor"]
    custom_widths_specials = {
        "ID": 60,
        " ": 150,
        "Sitio": 220,
        "Actividad": 150,
        "Cantidad": 70,
        "Camera": 80,
        "Descripcion": 190,
        "Usuario": 100,
        "TZ": 90,
        "Supervisor": 150
    }
    
    # Variables para specials sin asignar
    unassigned_row_ids = []
    unassigned_row_cache = []
    
    def load_unassigned_specials():
        """Carga specials sin marcar (marked_status vacío) desde el último START SHIFT"""
        try:
            conn = under_super.get_connection()
            cursor = conn.cursor()
            
            # Obtener el último START SHIFT del Lead Supervisor
            cursor.execute("""
                SELECT e.FechaHora 
                FROM Eventos e
                INNER JOIN user u ON e.ID_Usuario = u.ID_Usuario
                WHERE u.Nombre_Usuario = %s AND e.Nombre_Actividad = 'START SHIFT'
                ORDER BY e.FechaHora DESC
                LIMIT 1
            """, (username,))
            result = cursor.fetchone()
            
            if not result:
                print(f"[INFO] No hay turno activo para {username}")
                unassigned_sheet.set_sheet_data([["No hay shift activo"] + [""] * (len(columns_specials)-1)])
                unassigned_row_ids.clear()
                unassigned_row_cache.clear()
                cursor.close()
                conn.close()
                return
            
            fecha_inicio = result[0]
            
            # Query: Specials sin marcar (marked_status IS NULL o vacío)
            # Estos son specials que aún NO han sido revisados/marcados por ningún supervisor
            sql = """
                SELECT 
                    s.ID_special,
                    s.FechaHora,
                    s.ID_Sitio,
                    s.Nombre_Actividad,
                    s.Cantidad,
                    s.Camera,
                    s.Descripcion,
                    s.Usuario,
                    s.Time_Zone,
                    s.Supervisor
                FROM specials s
                WHERE (s.marked_status IS NULL OR s.marked_status = '')
                  AND s.FechaHora >= %s
                ORDER BY s.FechaHora ASC
            """
            
            cursor.execute(sql, (fecha_inicio,))
            rows = cursor.fetchall()
            
            # Formatear datos
            data = []
            unassigned_row_ids.clear()
            for row in rows:
                unassigned_row_ids.append(row[0])  # ID_special
                
                # Resolver nombre de sitio si es ID
                sitio_display = ""
                if row[2]:  # ID_Sitio
                    try:
                        cursor.execute("SELECT Nombre_Sitio FROM Sitios WHERE ID_Sitio = %s", (row[2],))
                        sitio_row = cursor.fetchone()
                        if sitio_row:
                            sitio_display = f"{row[2]} {sitio_row[0]}"
                        else:
                            sitio_display = str(row[2])
                    except Exception:
                        sitio_display = str(row[2]) if row[2] else ""
                
                formatted_row = [
                    str(row[0]),  # ID
                    str(row[1]) if row[1] else "",  #  
                    sitio_display,  # Sitio
                    str(row[3]) if row[3] else "",  # Actividad
                    str(row[4]) if row[4] else "",  # Cantidad
                    str(row[5]) if row[5] else "",  # Camera
                    str(row[6]) if row[6] else "",  # Descripcion
                    str(row[7]) if row[7] else "",  # Usuario
                    str(row[8]) if row[8] else "",  # TZ
                    str(row[9]) if row[9] else "Sin Asignar"  # Supervisor
                ]
                data.append(formatted_row)
            
            unassigned_row_cache.clear()
            unassigned_row_cache.extend(data)
            
            # Actualizar tksheet
            unassigned_sheet.set_sheet_data(data if data else [["No hay specials sin asignar"] + [""] * (len(columns_specials)-1)])
            
            # Aplicar anchos personalizados
            for col_idx, col_name in enumerate(columns_specials):
                if col_name in custom_widths_specials:
                    unassigned_sheet.column_width(column=col_idx, width=custom_widths_specials[col_name])
            
            cursor.close()
            conn.close()
            
            print(f"[INFO] Cargados {len(data)} specials sin asignar")
            
        except Exception as e:
            print(f"[ERROR] load_unassigned_specials: {e}")
            traceback.print_exc()
            messagebox.showerror("Error", f"Error al cargar specials sin asignar:\n{e}", parent=top)
    
    def assign_supervisor_to_selected():
        """Abre ventana para asignar supervisor a los specials seleccionados"""
        try:
            selected = unassigned_sheet.get_selected_rows()
            if not selected:
                messagebox.showwarning("Advertencia", "Selecciona al menos un special para asignar", parent=top)
                return
            
            # Ventana modal para seleccionar supervisor (reutilización de accion_supervisores)
            if UI is not None:
                assign_win = UI.CTkToplevel(top)
                try:
                    assign_win.configure(fg_color="#2c2f33")
                except Exception:
                    pass
            else:
                assign_win = tk.Toplevel(top)
                assign_win.configure(bg="#2c2f33")
            
            assign_win.title("Asignar Supervisor")
            assign_win.geometry("400x250")
            assign_win.resizable(False, False)
            assign_win.transient(top)
            assign_win.grab_set()
            
            if UI is not None:
                UI.CTkLabel(assign_win, text="Selecciona un Supervisor:", 
                           text_color="#00bfae", 
                           font=("Segoe UI", 16, "bold")).pack(pady=(20, 10))
                container = UI.CTkFrame(assign_win, fg_color="#2c2f33")
                container.pack(fill="both", expand=True, padx=20, pady=(0, 15))
            else:
                tk.Label(assign_win, text="Selecciona un Supervisor:", 
                        bg="#2c2f33", fg="#00bfae", 
                        font=("Segoe UI", 14, "bold")).pack(pady=(20, 10))
                container = tk.Frame(assign_win, bg="#2c2f33")
                container.pack(fill="both", expand=True, padx=20, pady=(0, 15))
            
            # Consultar supervisores disponibles
            supervisores = []
            try:
                conn = under_super.get_connection()
                cur = conn.cursor()
                # Buscar usuarios con rol "Supervisor" o "Lead Supervisor"
                cur.execute("SELECT Nombre_Usuario FROM user WHERE Rol IN ('Supervisor', 'Lead Supervisor')")
                supervisores = [row[0] for row in cur.fetchall()]
                cur.close()
                conn.close()
            except Exception as e:
                print(f"[ERROR] Error al consultar supervisores: {e}")
            
            sup_var = tk.StringVar()
            if UI is not None:
                if not supervisores:
                    supervisores = ["No hay supervisores disponibles"]
                opt = UI.CTkOptionMenu(container, variable=sup_var, values=supervisores, 
                                      fg_color="#262a31", button_color="#14414e", 
                                      text_color="#00bfae",
                                      font=("Segoe UI", 13))
                if supervisores and supervisores[0] != "No hay supervisores disponibles":
                    sup_var.set(supervisores[0])
                opt.pack(fill="x", padx=10, pady=10)
            else:
                yscroll_sup = tk.Scrollbar(container, orient="vertical")
                yscroll_sup.pack(side="right", fill="y")
                sup_listbox = tk.Listbox(container, height=8, selectmode="browse", 
                                        bg="#262a31", fg="#00bfae", 
                                        font=("Segoe UI", 12), 
                                        yscrollcommand=yscroll_sup.set)
                sup_listbox.pack(side="left", fill="both", expand=True)
                yscroll_sup.config(command=sup_listbox.yview)
                if not supervisores:
                    sup_listbox.insert("end", "No hay supervisores disponibles")
                else:
                    for sup in supervisores:
                        sup_listbox.insert("end", sup)
            
            def confirm_assignment():
                try:
                    # Obtener supervisor seleccionado
                    if UI is not None:
                        supervisor_name = sup_var.get()
                    else:
                        sel_idx = sup_listbox.curselection()
                        if not sel_idx:
                            messagebox.showwarning("Sin selección", "Selecciona un supervisor", parent=assign_win)
                            return
                        supervisor_name = sup_listbox.get(sel_idx[0])
                    
                    if not supervisor_name or supervisor_name == "No hay supervisores disponibles":
                        messagebox.showwarning("Sin selección", "Selecciona un supervisor válido", parent=assign_win)
                        return
                    
                    # Actualizar base de datos
                    conn = under_super.get_connection()
                    cursor = conn.cursor()
                    
                    updated_count = 0
                    for row_idx in selected:
                        if row_idx < len(unassigned_row_ids):
                            special_id = unassigned_row_ids[row_idx]
                            try:
                                cursor.execute(
                                    "UPDATE specials SET Supervisor = %s WHERE ID_special = %s",
                                    (supervisor_name, special_id)
                                )
                                updated_count += 1
                            except Exception as e:
                                print(f"[ERROR] No se pudo asignar supervisor al special {special_id}: {e}")
                    
                    conn.commit()
                    cursor.close()
                    conn.close()
                    
                    assign_win.destroy()
                    load_unassigned_specials()  # Recargar lista
                    
                except Exception as e:
                    print(f"[ERROR] confirm_assignment: {e}")
                    traceback.print_exc()
                    messagebox.showerror("Error", f"Error al asignar supervisor:\n{e}", parent=assign_win)
            
            # Botones
            if UI is not None:
                btn_frame = UI.CTkFrame(assign_win, fg_color="#2c2f33")
                btn_frame.pack(fill="x", padx=20, pady=(0, 20))
                
                UI.CTkButton(btn_frame, text="✅ Asignar", 
                            command=confirm_assignment,
                            fg_color="#00c853", hover_color="#00a043",
                            font=("Segoe UI", 12, "bold"),
                            width=150).pack(side="left", padx=(0, 10))
                
                UI.CTkButton(btn_frame, text="❌ Cancelar", 
                            command=assign_win.destroy,
                            fg_color="#d32f2f", hover_color="#b71c1c",
                            font=("Segoe UI", 12, "bold"),
                            width=150).pack(side="right")
            else:
                btn_frame = tk.Frame(assign_win, bg="#2c2f33")
                btn_frame.pack(fill="x", padx=20, pady=(0, 20))
                
                tk.Button(btn_frame, text="✅ Asignar", 
                         command=confirm_assignment,
                         bg="#00c853", fg="white",
                         font=("Segoe UI", 12, "bold"),
                         width=15).pack(side="left", padx=(0, 10))
                
                tk.Button(btn_frame, text="❌ Cancelar", 
                         command=assign_win.destroy,
                         bg="#d32f2f", fg="white",
                         font=("Segoe UI", 12, "bold"),
                         width=15).pack(side="right")
            
        except Exception as e:
            print(f"[ERROR] assign_supervisor_to_selected: {e}")
            traceback.print_exc()
            messagebox.showerror("Error", f"Error al abrir ventana de asignación:\n{e}", parent=top)
    
    # Frame superior para botones de acción
    if UI is not None:
        unassigned_actions = UI.CTkFrame(unassigned_container, fg_color="#23272a", corner_radius=0, height=60)
    else:
        unassigned_actions = tk.Frame(unassigned_container, bg="#23272a", height=60)
    unassigned_actions.pack(fill="x", padx=0, pady=0)
    unassigned_actions.pack_propagate(False)
    
    if UI is not None:
        UI.CTkLabel(unassigned_actions, text="⚠️ Specials Sin Marcar (Pendientes de Revisión)", 
                   font=("Segoe UI", 14, "bold"), 
                   text_color="#ffa726").pack(side="left", padx=20, pady=15)
        
        UI.CTkButton(unassigned_actions, text="👤 Asignar Supervisor", 
                    command=assign_supervisor_to_selected,
                    fg_color="#00c853", hover_color="#00a043",
                    width=160, height=35,
                    font=("Segoe UI", 12, "bold")).pack(side="right", padx=(5, 20), pady=12)
        
        UI.CTkButton(unassigned_actions, text="🔄 Refrescar", 
                    command=load_unassigned_specials,
                    fg_color="#4D6068", hover_color="#27a3e0",
                    width=120, height=35,
                    font=("Segoe UI", 12, "bold")).pack(side="right", padx=5, pady=12)
    else:
        tk.Label(unassigned_actions, text="⚠️ Specials Sin Marcar (Pendientes de Revisión)", 
                bg="#23272a", fg="#ffa726",
                font=("Segoe UI", 14, "bold")).pack(side="left", padx=20, pady=15)
        
        tk.Button(unassigned_actions, text="👤 Asignar Supervisor", 
                 command=assign_supervisor_to_selected,
                 bg="#00c853", fg="white",
                 font=("Segoe UI", 12, "bold"),
                 width=18).pack(side="right", padx=(5, 20), pady=12)
        
        tk.Button(unassigned_actions, text="🔄 Refrescar", 
                 command=load_unassigned_specials,
                 bg="#666666", fg="white",
                 font=("Segoe UI", 12, "bold"),
                 width=12).pack(side="right", padx=5, pady=12)
    
    # Frame para tksheet de specials sin asignar
    if UI is not None:
        unassigned_sheet_frame = UI.CTkFrame(unassigned_container, fg_color="#2c2f33")
    else:
        unassigned_sheet_frame = tk.Frame(unassigned_container, bg="#2c2f33")
    unassigned_sheet_frame.pack(fill="both", expand=True, padx=0, pady=10)
    
    # Crear tksheet para specials sin asignar
    unassigned_sheet = SheetClass(
        unassigned_sheet_frame,
        headers=columns_specials,
        theme="dark blue",
        height=550,
        width=1350,
        show_selected_cells_border=True,
        show_row_index=True,
        show_top_left=False,
        empty_horizontal=0,
        empty_vertical=0,
        auto_resize_columns=False,
        auto_resize_rows=False
    )
    # ⭐ DESHABILITAR opciones de edición del menú contextual
    # Solo permitir: selección, redimensión, copiar y deshacer
    unassigned_sheet.enable_bindings([
        "single_select",
        "drag_select",
        "column_select",
        "row_select",
        "column_width_resize",
        "double_click_column_resize",
        "arrowkeys",
        "copy",
        "select_all"
    ])
    unassigned_sheet.pack(fill="both", expand=True)
    
    # Aplicar anchos iniciales para specials
    for col_idx, col_name in enumerate(columns_specials):
        if col_name in custom_widths_specials:
            unassigned_sheet.column_width(column=col_idx, width=custom_widths_specials[col_name])

    # ==================== CONTAINERS ADICIONALES: AUDIT Y COVER TIME ====================
    
    # ⭐ Importar tkcalendar para DateEntry (usado en Audit y Cover Time)
    try:
        import tkcalendar
    except ImportError:
        tkcalendar = None
    
    # ⭐ Configurar estilo oscuro para FilteredCombobox (ttk widgets)
    try:
        dark_combo_style = ttk.Style()
        dark_combo_style.theme_use('clam')  # Tema base compatible
        
        # Configurar estilo dark para combobox
        dark_combo_style.configure('Dark.TCombobox',
                                   fieldbackground='#2b2b2b',
                                   background='#2b2b2b',
                                   foreground='#ffffff',
                                   arrowcolor='#ffffff',
                                   bordercolor='#4a90e2',
                                   lightcolor='#2b2b2b',
                                   darkcolor='#2b2b2b',
                                   selectbackground='#4a90e2',
                                   selectforeground='#ffffff')
        
        dark_combo_style.map('Dark.TCombobox',
                            fieldbackground=[('readonly', '#2b2b2b'), ('disabled', '#1a1a1a')],
                            selectbackground=[('readonly', '#4a90e2')],
                            selectforeground=[('readonly', '#ffffff')],
                            foreground=[('readonly', '#ffffff'), ('disabled', '#666666')])
        
        # Configurar estilo para el listbox del dropdown
        top.option_add('*TCombobox*Listbox.background', '#2b2b2b')
        top.option_add('*TCombobox*Listbox.foreground', '#ffffff')
        top.option_add('*TCombobox*Listbox.selectBackground', '#4a90e2')
        top.option_add('*TCombobox*Listbox.selectForeground', '#ffffff')
    except Exception as e:
        print(f"[DEBUG] No se pudo configurar estilo dark para combobox: {e}")
    
    # ===== AUDIT CONTAINER =====
    if UI is not None:
        audit_container = UI.CTkFrame(top, fg_color="#2c2f33")
    else:
        audit_container = tk.Frame(top, bg="#2c2f33")
    # No hacer pack aquí, se hace en switch_view()
    
    # Filtros de Audit
    if UI is not None:
        audit_filters = UI.CTkFrame(audit_container, fg_color="#23272a", corner_radius=0, height=120)
    else:
        audit_filters = tk.Frame(audit_container, bg="#23272a", height=120)
    audit_filters.pack(fill="x", padx=0, pady=0)
    audit_filters.pack_propagate(False)
    
    # Variables de filtros
    audit_user_var = tk.StringVar()
    audit_site_var = tk.StringVar()
    audit_fecha_var = tk.StringVar()
    
    # Obtener usuarios y sitios de la BD
    try:
        conn_temp = under_super.get_connection()
        cur_temp = conn_temp.cursor()
        
        # Usuarios
        cur_temp.execute("SELECT Nombre_Usuario FROM user ORDER BY Nombre_Usuario")
        audit_users_list = ["Todos"] + [row[0] for row in cur_temp.fetchall()]
        
        cur_temp.close()
        conn_temp.close()
        
        # ⭐ Sitios con formato "Nombre (ID)" usando helper con cache
        audit_sites_raw = under_super.get_sites()
        audit_sites_list = ["Todos"] + audit_sites_raw
        
    except Exception as e:
        print(f"[ERROR] Error al cargar usuarios/sitios para audit: {e}")
        audit_users_list = ["Todos"]
        audit_sites_list = ["Todos"]
    
    # Labels y controles de filtros Audit
    if UI is not None:
        UI.CTkLabel(audit_filters, text="📋 Auditoría de Eventos", 
                   font=("Segoe UI", 14, "bold"), text_color="#e0e0e0").pack(side="top", padx=20, pady=(10, 5))
        
        filter_row1 = UI.CTkFrame(audit_filters, fg_color="transparent")
        filter_row1.pack(fill="x", padx=20, pady=5)
        
        UI.CTkLabel(filter_row1, text="Usuario:", text_color="#e0e0e0").pack(side="left", padx=5)
        audit_user_cb = under_super.FilteredCombobox(
            filter_row1, textvariable=audit_user_var, values=audit_users_list,
            font=("Segoe UI", 10), width=25,
            background='#2b2b2b', foreground='#ffffff', 
            bordercolor='#4a90e2', arrowcolor='#ffffff'
        )
        audit_user_cb.pack(side="left", padx=5)
        
        UI.CTkLabel(filter_row1, text="Sitio:", text_color="#e0e0e0").pack(side="left", padx=5)
        audit_site_cb = under_super.FilteredCombobox(
            filter_row1, textvariable=audit_site_var, values=audit_sites_list,
            font=("Segoe UI", 10), width=32,
            background='#2b2b2b', foreground='#ffffff',
            bordercolor='#4a90e2', arrowcolor='#ffffff'
        )
        audit_site_cb.pack(side="left", padx=5)
        
        UI.CTkLabel(filter_row1, text="Fecha:", text_color="#e0e0e0").pack(side="left", padx=(15, 5))
        # Frame contenedor para DateEntry (tkcalendar no es compatible directo con CTk)
        audit_fecha_frame = tk.Frame(filter_row1, bg="#23272a")
        audit_fecha_frame.pack(side="left", padx=5)
        if tkcalendar:
            audit_fecha_entry = tkcalendar.DateEntry(audit_fecha_frame, textvariable=audit_fecha_var,
                                                     width=13, background='#4a90e2', foreground='white',
                                                     borderwidth=2, date_pattern='yyyy-mm-dd',
                                                     font=("Segoe UI", 10))
            audit_fecha_entry.pack()
        else:
            audit_fecha_entry = tk.Entry(audit_fecha_frame, textvariable=audit_fecha_var, width=13,
                                        bg="#2b2b2b", fg="#ffffff", font=("Segoe UI", 10))
            audit_fecha_entry.pack()
        
        filter_row2 = UI.CTkFrame(audit_filters, fg_color="transparent")
        filter_row2.pack(fill="x", padx=20, pady=5)
    else:
        tk.Label(audit_filters, text="📋 Auditoría de Eventos", 
                bg="#23272a", fg="#e0e0e0", font=("Segoe UI", 14, "bold")).pack(side="top", padx=20, pady=(10, 5))
        
        filter_row1 = tk.Frame(audit_filters, bg="#23272a")
        filter_row1.pack(fill="x", padx=20, pady=5)
        
        tk.Label(filter_row1, text="Usuario:", bg="#23272a", fg="#e0e0e0").pack(side="left", padx=5)
        audit_user_cb = under_super.FilteredCombobox(
            filter_row1, textvariable=audit_user_var, values=audit_users_list,
            font=("Segoe UI", 10), width=25
        )
        try:
            audit_user_cb.configure(style='Dark.TCombobox')
        except:
            pass
        audit_user_cb.pack(side="left", padx=5)
        
        tk.Label(filter_row1, text="Sitio:", bg="#23272a", fg="#e0e0e0").pack(side="left", padx=5)
        audit_site_cb = under_super.FilteredCombobox(
            filter_row1, textvariable=audit_site_var, values=audit_sites_list,
            font=("Segoe UI", 10), width=32
        )
        try:
            audit_site_cb.configure(style='Dark.TCombobox')
        except:
            pass
        audit_site_cb.pack(side="left", padx=5)
        
        tk.Label(filter_row1, text="Fecha:", bg="#23272a", fg="#e0e0e0").pack(side="left", padx=(15, 5))
        if tkcalendar:
            audit_fecha_entry = tkcalendar.DateEntry(filter_row1, textvariable=audit_fecha_var,
                                                     width=13, background='#4a90e2', foreground='white',
                                                     borderwidth=2, date_pattern='yyyy-mm-dd',
                                                     font=("Segoe UI", 10))
            audit_fecha_entry.pack(side="left", padx=5)
        else:
            audit_fecha_entry = tk.Entry(filter_row1, textvariable=audit_fecha_var, width=13,
                                        bg="#2b2b2b", fg="#ffffff", font=("Segoe UI", 10))
            audit_fecha_entry.pack(side="left", padx=5)
        
        filter_row2 = tk.Frame(audit_filters, bg="#23272a")
        filter_row2.pack(fill="x", padx=20, pady=5)
    
    def search_audit():
        """Busca eventos según filtros"""
        try:
            conn = under_super.get_connection()
            cursor = conn.cursor()
            
            sql = "SELECT ID_Eventos, FechaHora, ID_Sitio, Nombre_Actividad, Cantidad, Camera, Descripcion, ID_Usuario FROM Eventos WHERE 1=1"
            params = []
            
            if audit_user_var.get() and audit_user_var.get() != "Todos":
                sql += " AND ID_Usuario = (SELECT ID_Usuario FROM user WHERE Nombre_Usuario = %s)"
                params.append(audit_user_var.get())
            
            # ⭐ USAR HELPER para deconstruir formato "Nombre (ID)"
            if audit_site_var.get() and audit_site_var.get() != "Todos":
                site_filter_raw = audit_site_var.get()
                site_name, site_id = under_super.parse_site_filter(site_filter_raw)
                
                if site_name and site_id:
                    # Buscar por nombre (más preciso cuando tenemos ambos)
                    sql += " AND ID_Sitio = (SELECT ID_Sitio FROM Sitios WHERE Nombre_Sitio = %s)"
                    params.append(site_name)
                elif site_id:
                    # Buscar solo por ID
                    sql += " AND ID_Sitio = %s"
                    params.append(site_id)
                elif site_name:
                    # Buscar solo por nombre
                    sql += " AND ID_Sitio = (SELECT ID_Sitio FROM Sitios WHERE Nombre_Sitio = %s)"
                    params.append(site_name)
            
            if audit_fecha_var.get():
                sql += " AND DATE(FechaHora) = %s"
                params.append(audit_fecha_var.get())
            
            sql += " ORDER BY FechaHora DESC LIMIT 500"
            
            cursor.execute(sql, params)
            rows = cursor.fetchall()
            
            # Formatear datos
            data = []
            for row in rows:
                # Resolver nombres
                sitio_nombre = ""
                if row[2]:
                    cursor.execute("SELECT Nombre_Sitio FROM Sitios WHERE ID_Sitio = %s", (row[2],))
                    sitio_row = cursor.fetchone()
                    if sitio_row:
                        sitio_nombre = sitio_row[0]
                
                usuario_nombre = ""
                if row[7]:
                    cursor.execute("SELECT Nombre_Usuario FROM user WHERE ID_Usuario = %s", (row[7],))
                    user_row = cursor.fetchone()
                    if user_row:
                        usuario_nombre = user_row[0]
                
                data.append([
                    str(row[0]),  # ID
                    str(row[1]) if row[1] else "",  #  
                    sitio_nombre,  # Sitio
                    str(row[3]) if row[3] else "",  # Actividad
                    str(row[4]) if row[4] else "",  # Cantidad
                    str(row[5]) if row[5] else "",  # Camera
                    str(row[6]) if row[6] else "",  # Descripcion
                    usuario_nombre  # Usuario
                ])
            
            audit_sheet.set_sheet_data(data if data else [["No se encontraron resultados"] + [""] * 7])
            
            cursor.close()
            conn.close()
            
        except Exception as e:
            print(f"[ERROR] search_audit: {e}")
            traceback.print_exc()
            messagebox.showerror("Error", f"Error al buscar:\n{e}", parent=top)
    
    def clear_audit_filters():
        """Limpia los filtros de audit"""
        audit_user_var.set("")
        audit_site_var.set("")
        audit_fecha_var.set("")
        audit_sheet.set_sheet_data([[""] * 8])
    
    # Botones de Audit
    if UI is not None:
        UI.CTkButton(filter_row2, text="🔍 Buscar", command=search_audit,
                    fg_color="#4a90e2", hover_color="#357ABD",
                    width=100, height=32, font=("Segoe UI", 11, "bold")).pack(side="left", padx=5)
        UI.CTkButton(filter_row2, text="🗑️ Limpiar", command=clear_audit_filters,
                    fg_color="#3b4754", hover_color="#4a5560",
                    width=100, height=32, font=("Segoe UI", 11, "bold")).pack(side="left", padx=5)
    else:
        tk.Button(filter_row2, text="🔍 Buscar", command=search_audit,
                 bg="#4a90e2", fg="white", font=("Segoe UI", 11, "bold"),
                 relief="flat", width=10).pack(side="left", padx=5)
        tk.Button(filter_row2, text="🗑️ Limpiar", command=clear_audit_filters,
                 bg="#3b4754", fg="white", font=("Segoe UI", 11, "bold"),
                 relief="flat", width=10).pack(side="left", padx=5)
    
    # Frame para tksheet de Audit
    if UI is not None:
        audit_sheet_frame = UI.CTkFrame(audit_container, fg_color="#2c2f33")
    else:
        audit_sheet_frame = tk.Frame(audit_container, bg="#2c2f33")
    audit_sheet_frame.pack(fill="both", expand=True, padx=10, pady=10)
    
    # Crear tksheet de Audit
    audit_columns = ["ID", " ", "Sitio", "Actividad", "Cantidad", "Camera", "Descripcion", "Usuario"]
    audit_sheet = SheetClass(
        audit_sheet_frame,
        data=[[""] * len(audit_columns)],
        headers=audit_columns,
        theme="dark blue",
        height=500,
        width=1330,
        show_selected_cells_border=True,
        show_row_index=True,
        show_top_left=False,
        empty_horizontal=0,
        empty_vertical=0,
        auto_resize_columns=False,
        auto_resize_rows=False
    )
    audit_sheet.enable_bindings(
    )
    audit_sheet.enable_bindings([
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
    audit_sheet.pack(fill="both", expand=True)
    audit_widths = {
        "ID": 60,
        " ": 150,
        "Sitio": 180,
        "Actividad": 140,
        "Cantidad": 80,
        "Camera": 80,
        "Descripcion": 200,
        "Usuario": 120
    }
    for col_idx, col_name in enumerate(audit_columns):
        if col_name in audit_widths:
            audit_sheet.column_width(column=col_idx, width=audit_widths[col_name])
    
    # ===== COVER TIME CONTAINER =====
    if UI is not None:
        cover_container = UI.CTkFrame(top, fg_color="#2c2f33")
    else:
        cover_container = tk.Frame(top, bg="#2c2f33")
    # No hacer pack aquí, se hace en switch_view()
    
    # Filtros de Cover Time
    if UI is not None:
        cover_filters = UI.CTkFrame(cover_container, fg_color="#23272a", corner_radius=0, height=170)
    else:
        cover_filters = tk.Frame(cover_container, bg="#23272a", height=170)
    cover_filters.pack(fill="x", padx=0, pady=0)
    cover_filters.pack_propagate(False)
    
    # Variables de Cover Time
    cover_user_var = tk.StringVar()
    cover_station_var = tk.StringVar()
    cover_desde_var = tk.StringVar()
    cover_hasta_var = tk.StringVar()
    
    # Obtener usuarios y estaciones para Cover Time
    try:
        conn_temp = under_super.get_connection()
        cur_temp = conn_temp.cursor()
        
        # Usuarios
        cur_temp.execute("SELECT Nombre_Usuario FROM user ORDER BY Nombre_Usuario")
        cover_users_list = ["Todos"] + [row[0] for row in cur_temp.fetchall()]
        
        # Estaciones
        cur_temp.execute("SELECT DISTINCT Station FROM covers_programados WHERE Station IS NOT NULL ORDER BY Station")
        cover_stations_list = ["Todos"] + [row[0] for row in cur_temp.fetchall()]
        
        cur_temp.close()
        conn_temp.close()
    except Exception as e:
        print(f"[ERROR] Error al cargar usuarios/estaciones para cover: {e}")
        cover_users_list = ["Todos"]
        cover_stations_list = ["Todos"]
    
    # Labels y controles de Cover Time
    if UI is not None:
        UI.CTkLabel(cover_filters, text="⏰ Covers Programados y Realizados", 
                   font=("Segoe UI", 14, "bold"), text_color="#e0e0e0").pack(side="top", padx=20, pady=(10, 5))
        
        cover_summary_label = UI.CTkLabel(cover_filters, text="Total: 0 covers cargados",
                                         font=("Segoe UI", 12, "bold"), text_color="#00bfae")
        cover_summary_label.pack(side="top", pady=5)
        
        cover_filter_row1 = UI.CTkFrame(cover_filters, fg_color="transparent")
        cover_filter_row1.pack(fill="x", padx=20, pady=5)
        
        UI.CTkLabel(cover_filter_row1, text="Usuario:", text_color="#e0e0e0").pack(side="left", padx=5)
        cover_user_cb = under_super.FilteredCombobox(
            cover_filter_row1, textvariable=cover_user_var, values=cover_users_list,
            font=("Segoe UI", 10), width=22,
            background='#2b2b2b', foreground='#ffffff',
            bordercolor='#4a90e2', arrowcolor='#ffffff'
        )
        cover_user_cb.pack(side="left", padx=5)
        
        UI.CTkLabel(cover_filter_row1, text="Estación:", text_color="#e0e0e0").pack(side="left", padx=(10, 5))
        cover_station_cb = under_super.FilteredCombobox(
            cover_filter_row1, textvariable=cover_station_var, values=cover_stations_list,
            font=("Segoe UI", 10), width=22,
            background='#2b2b2b', foreground='#ffffff',
            bordercolor='#4a90e2', arrowcolor='#ffffff'
        )
        cover_station_cb.pack(side="left", padx=5)
        
        UI.CTkLabel(cover_filter_row1, text="Desde:", text_color="#e0e0e0").pack(side="left", padx=(15, 5))
        # Frame contenedor para DateEntry (tkcalendar no es compatible directo con CTk)
        cover_desde_frame = tk.Frame(cover_filter_row1, bg="#23272a")
        cover_desde_frame.pack(side="left", padx=5)
        if tkcalendar:
            cover_desde_entry = tkcalendar.DateEntry(cover_desde_frame, textvariable=cover_desde_var,
                                                     width=13, background='#4a90e2', foreground='white',
                                                     borderwidth=2, date_pattern='yyyy-mm-dd',
                                                     font=("Segoe UI", 10))
            cover_desde_entry.pack()
        else:
            cover_desde_entry = tk.Entry(cover_desde_frame, textvariable=cover_desde_var, width=13,
                                        bg="#2b2b2b", fg="#ffffff", font=("Segoe UI", 10))
            cover_desde_entry.pack()
        
        UI.CTkLabel(cover_filter_row1, text="Hasta:", text_color="#e0e0e0").pack(side="left", padx=(15, 5))
        # Frame contenedor para DateEntry
        cover_hasta_frame = tk.Frame(cover_filter_row1, bg="#23272a")
        cover_hasta_frame.pack(side="left", padx=5)
        if tkcalendar:
            cover_hasta_entry = tkcalendar.DateEntry(cover_hasta_frame, textvariable=cover_hasta_var,
                                                     width=13, background='#4a90e2', foreground='white',
                                                     borderwidth=2, date_pattern='yyyy-mm-dd',
                                                     font=("Segoe UI", 10))
            cover_hasta_entry.pack()
        else:
            cover_hasta_entry = tk.Entry(cover_hasta_frame, textvariable=cover_hasta_var, width=13,
                                        bg="#2b2b2b", fg="#ffffff", font=("Segoe UI", 10))
            cover_hasta_entry.pack()
        
        cover_filter_row2 = UI.CTkFrame(cover_filters, fg_color="transparent")
        cover_filter_row2.pack(fill="x", padx=20, pady=5)
    else:
        tk.Label(cover_filters, text="⏰ Covers Programados y Realizados", 
                bg="#23272a", fg="#e0e0e0", font=("Segoe UI", 14, "bold")).pack(side="top", padx=20, pady=(10, 5))
        
        cover_summary_label = tk.Label(cover_filters, text="Total: 0 covers cargados",
                                      bg="#23272a", fg="#00bfae", font=("Segoe UI", 12, "bold"))
        cover_summary_label.pack(side="top", pady=5)
        
        cover_filter_row1 = tk.Frame(cover_filters, bg="#23272a")
        cover_filter_row1.pack(fill="x", padx=20, pady=5)
        
        tk.Label(cover_filter_row1, text="Usuario:", bg="#23272a", fg="#e0e0e0").pack(side="left", padx=5)
        cover_user_cb = under_super.FilteredCombobox(
            cover_filter_row1, textvariable=cover_user_var, values=cover_users_list,
            font=("Segoe UI", 10), width=22
        )
        try:
            cover_user_cb.configure(style='Dark.TCombobox')
        except:
            pass
        cover_user_cb.pack(side="left", padx=5)
        
        tk.Label(cover_filter_row1, text="Estación:", bg="#23272a", fg="#e0e0e0").pack(side="left", padx=(10, 5))
        cover_station_cb = under_super.FilteredCombobox(
            cover_filter_row1, textvariable=cover_station_var, values=cover_stations_list,
            font=("Segoe UI", 10), width=22
        )
        try:
            cover_station_cb.configure(style='Dark.TCombobox')
        except:
            pass
        cover_station_cb.pack(side="left", padx=5)
        
        tk.Label(cover_filter_row1, text="Desde:", bg="#23272a", fg="#e0e0e0").pack(side="left", padx=(15, 5))
        if tkcalendar:
            cover_desde_entry = tkcalendar.DateEntry(cover_filter_row1, textvariable=cover_desde_var,
                                                     width=13, background='#4a90e2', foreground='white',
                                                     borderwidth=2, date_pattern='yyyy-mm-dd',
                                                     font=("Segoe UI", 10))
            cover_desde_entry.pack(side="left", padx=5)
        else:
            cover_desde_entry = tk.Entry(cover_filter_row1, textvariable=cover_desde_var, width=13,
                                        bg="#2b2b2b", fg="#ffffff", font=("Segoe UI", 10))
            cover_desde_entry.pack(side="left", padx=5)
        
        tk.Label(cover_filter_row1, text="Hasta:", bg="#23272a", fg="#e0e0e0").pack(side="left", padx=(15, 5))
        if tkcalendar:
            cover_hasta_entry = tkcalendar.DateEntry(cover_filter_row1, textvariable=cover_hasta_var,
                                                     width=13, background='#4a90e2', foreground='white',
                                                     borderwidth=2, date_pattern='yyyy-mm-dd',
                                                     font=("Segoe UI", 10))
            cover_hasta_entry.pack(side="left", padx=5)
        else:
            cover_hasta_entry = tk.Entry(cover_filter_row1, textvariable=cover_hasta_var, width=13,
                                        bg="#2b2b2b", fg="#ffffff", font=("Segoe UI", 10))
            cover_hasta_entry.pack(side="left", padx=5)
        
        cover_filter_row2 = tk.Frame(cover_filters, bg="#23272a")
        cover_filter_row2.pack(fill="x", padx=20, pady=5)
    
    def search_covers():
        """Busca covers según filtros usando load_combined_covers()"""
        try:
            # Obtener filtros
            usuario = cover_user_var.get().strip()
            estacion = cover_station_var.get().strip()
            fecha_desde = cover_desde_var.get().strip()
            fecha_hasta = cover_hasta_var.get().strip()
            
            # Validar fechas
            if fecha_desde and fecha_hasta:
                try:
                    from datetime import datetime
                    d1 = datetime.strptime(fecha_desde, "%Y-%m-%d")
                    d2 = datetime.strptime(fecha_hasta, "%Y-%m-%d")
                    if d1 > d2:
                        messagebox.showwarning("Advertencia", "La fecha 'Desde' no puede ser mayor que 'Hasta'", parent=top)
                        return
                except:
                    messagebox.showerror("Error", "Formato de fecha inválido. Use YYYY-MM-DD", parent=top)
                    return
            
            # Cargar todos los covers desde la función combinada
            col_names, rows = under_super.load_combined_covers()
            
            if not rows:
                cover_sheet.set_sheet_data([["No hay datos disponibles"] + [""] * 11])
                cover_summary_label.configure(text="Total: 0 covers cargados")
                return
            
            # Aplicar filtros
            filtered_rows = []
            for row in rows:
                # Filtro por usuario (columna 1: Usuario)
                if usuario and usuario != "Todos":
                    if row[1] != usuario:
                        continue
                
                # Filtro por estación (columna 3: Estacion)
                if estacion and estacion != "Todos":
                    if row[3] != estacion:
                        continue
                
                # Filtro por fecha (columna 2: Hora_Programada)
                if fecha_desde or fecha_hasta:
                    try:
                        from datetime import datetime
                        fecha_cover = row[2]  # Hora_Programada
                        if fecha_cover:
                            if isinstance(fecha_cover, str):
                                fecha_cover_dt = datetime.strptime(fecha_cover.split()[0], "%Y-%m-%d")
                            else:
                                fecha_cover_dt = datetime.combine(fecha_cover.date() if hasattr(fecha_cover, 'date') else fecha_cover, datetime.min.time())
                            
                            if fecha_desde:
                                fecha_d = datetime.strptime(fecha_desde, "%Y-%m-%d")
                                if fecha_cover_dt < fecha_d:
                                    continue
                            
                            if fecha_hasta:
                                fecha_h = datetime.strptime(fecha_hasta, "%Y-%m-%d")
                                if fecha_cover_dt > fecha_h:
                                    continue
                    except Exception as e:
                        print(f"[DEBUG] Error al filtrar fecha: {e}")
                        pass
                
                filtered_rows.append(row)
            
            # Formatear datos para mostrar
            data = []
            for row in filtered_rows:
                formatted_row = [str(cell) if cell is not None else "" for cell in row]
                data.append(formatted_row)
            
            # Actualizar sheet
            cover_sheet.set_sheet_data(data if data else [["No hay resultados con esos filtros"] + [""] * 11])
            
            # Actualizar resumen
            summary_text = f"Total: {len(data)} covers cargados"
            cover_summary_label.configure(text=summary_text)
            
            print(f"[INFO] Cover Time: {len(data)} covers encontrados")
            
        except Exception as e:
            print(f"[ERROR] search_covers: {e}")
            traceback.print_exc()
            messagebox.showerror("Error", f"Error al buscar covers:\n{e}", parent=top)
    
    def clear_cover_filters():
        """Limpia filtros de cover"""
        cover_user_var.set("")
        cover_station_var.set("")
        cover_desde_var.set("")
        cover_hasta_var.set("")
        cover_sheet.set_sheet_data([[""] * 12])
        cover_summary_label.configure(text="Total: 0 covers cargados")
    
    # Botones de Cover Time
    if UI is not None:
        UI.CTkButton(cover_filter_row2, text="🔍 Buscar", command=search_covers,
                    fg_color="#4a90e2", hover_color="#357ABD",
                    width=100, height=32, font=("Segoe UI", 11, "bold")).pack(side="left", padx=5)
        UI.CTkButton(cover_filter_row2, text="🗑️ Limpiar", command=clear_cover_filters,
                    fg_color="#3b4754", hover_color="#4a5560",
                    width=100, height=32, font=("Segoe UI", 11, "bold")).pack(side="left", padx=5)
    else:
        tk.Button(cover_filter_row2, text="🔍 Buscar", command=search_covers,
                 bg="#4a90e2", fg="white", font=("Segoe UI", 11, "bold"),
                 relief="flat", width=10).pack(side="left", padx=5)
        tk.Button(cover_filter_row2, text="🗑️ Limpiar", command=clear_cover_filters,
                 bg="#3b4754", fg="white", font=("Segoe UI", 11, "bold"),
                 relief="flat", width=10).pack(side="left", padx=5)
    
    # Frame para tksheet de Cover Time
    if UI is not None:
        cover_sheet_frame = UI.CTkFrame(cover_container, fg_color="#2c2f33")
    else:
        cover_sheet_frame = tk.Frame(cover_container, bg="#2c2f33")
    cover_sheet_frame.pack(fill="both", expand=True, padx=10, pady=10)
    
    # Crear tksheet de Cover Time con columnas de load_combined_covers
    cover_columns = ["ID_Cover", "Usuario", "Hora_Programada", "Estacion", "Razon_Solicitud", 
                     "Aprobado", "Activo", "Cover_Inicio", "Cover_Fin", "Cubierto_Por", "Motivo_Real", "Estado"]
    cover_sheet = SheetClass(
        cover_sheet_frame,
        data=[[""] * len(cover_columns)],
        headers=cover_columns,
        theme="dark blue",
        height=500,
        width=1330,
        show_selected_cells_border=True,
        show_row_index=True,
        show_top_left=False,
        empty_horizontal=0,
        empty_vertical=0,
        auto_resize_columns=False,
        auto_resize_rows=False
    )
    cover_sheet.enable_bindings([
        
   
        "single_select",

         ],
    )
    cover_sheet.enable_bindings([
        "single_select",
        "drag_select",
        "row_select",
        "column_select",
        "column_width_resize",
        "double_click_column_resize",
        "arrowkeys",
        "copy",
        "select_all"
        ],
    )
    cover_sheet.pack(fill="both", expand=True)

    cover_widths = {
        "ID_Cover": 70,
        "Usuario": 110,
        "Hora_Programada": 150,
        "Estacion": 100,
        "Razon_Solicitud": 150,
        "Aprobado": 80,
        "Activo": 80,
        "Cover_Inicio": 150,
        "Cover_Fin": 150,
        "Cubierto_Por": 110,
        "Motivo_Real": 150,
        "Estado": 150
    }
    for col_idx, col_name in enumerate(cover_columns):
        if col_name in cover_widths:
            cover_sheet.column_width(column=col_idx, width=cover_widths[col_name])

    # ==================== ROL DE COVER CONTAINER ====================
    if UI is not None:
        rol_cover_container = UI.CTkFrame(top, fg_color="#2c2f33")
    else:
        rol_cover_container = tk.Frame(top, bg="#2c2f33")
    # NO hacer pack() aquí - se mostrará solo cuando se cambie a modo Rol de Cover

    # Frame de instrucciones
    if UI is not None:
        info_frame_rol = UI.CTkFrame(rol_cover_container, fg_color="#23272a", corner_radius=8)
    else:
        info_frame_rol = tk.Frame(rol_cover_container, bg="#23272a")
    info_frame_rol.pack(fill="x", padx=10, pady=10)

    if UI is not None:
        UI.CTkLabel(info_frame_rol, 
                   text="🎭 Gestión de Rol de Cover - Habilitar operadores que pueden ver la lista de covers",
                   text_color="#00bfae", 
                   font=("Segoe UI", 14, "bold")).pack(pady=15)
    else:
        tk.Label(info_frame_rol, 
                text="🎭 Gestión de Rol de Cover - Habilitar operadores que pueden ver la lista de covers",
                bg="#23272a", fg="#00bfae", 
                font=("Segoe UI", 14, "bold")).pack(pady=15)

    # Frame principal con dos columnas
    if UI is not None:
        main_frame_rol = UI.CTkFrame(rol_cover_container, fg_color="#2c2f33")
    else:
        main_frame_rol = tk.Frame(rol_cover_container, bg="#2c2f33")
    main_frame_rol.pack(fill="both", expand=True, padx=10, pady=10)

    # Columna izquierda: Operadores disponibles (Active = 1)
    if UI is not None:
        left_frame_rol = UI.CTkFrame(main_frame_rol, fg_color="#23272a", corner_radius=8)
    else:
        left_frame_rol = tk.Frame(main_frame_rol, bg="#23272a")
    left_frame_rol.pack(side="left", fill="both", expand=True, padx=(0, 5))

    if UI is not None:
        UI.CTkLabel(left_frame_rol, 
                   text="👤 Operadores Activos (Sin acceso a covers)",
                   text_color="#ffffff", 
                   font=("Segoe UI", 13, "bold")).pack(pady=10)
    else:
        tk.Label(left_frame_rol, 
                text="👤 Operadores Activos (Sin acceso a covers)",
                bg="#23272a", fg="#ffffff", 
                font=("Segoe UI", 13, "bold")).pack(pady=10)

    # Listbox para operadores sin acceso
    list_frame_sin_acceso = tk.Frame(left_frame_rol, bg="#23272a")
    list_frame_sin_acceso.pack(fill="both", expand=True, padx=15, pady=(0, 15))

    scroll_sin_acceso = tk.Scrollbar(list_frame_sin_acceso, orient="vertical")
    scroll_sin_acceso.pack(side="right", fill="y")

    listbox_sin_acceso = tk.Listbox(list_frame_sin_acceso, 
                                    selectmode="extended",
                                    bg="#262a31", 
                                    fg="#ffffff", 
                                    font=("Segoe UI", 11),
                                    yscrollcommand=scroll_sin_acceso.set,
                                    selectbackground="#4a90e2",
                                    height=20)
    listbox_sin_acceso.pack(side="left", fill="both", expand=True)
    scroll_sin_acceso.config(command=listbox_sin_acceso.yview)

    # Columna derecha: Operadores con acceso (Active = 2)
    if UI is not None:
        right_frame_rol = UI.CTkFrame(main_frame_rol, fg_color="#23272a", corner_radius=8)
    else:
        right_frame_rol = tk.Frame(main_frame_rol, bg="#23272a")
    right_frame_rol.pack(side="left", fill="both", expand=True, padx=(5, 0))

    if UI is not None:
        UI.CTkLabel(right_frame_rol, 
                   text="✅ Operadores con Acceso a Covers",
                   text_color="#00c853", 
                   font=("Segoe UI", 13, "bold")).pack(pady=10)
    else:
        tk.Label(right_frame_rol, 
                text="✅ Operadores con Acceso a Covers",
                bg="#23272a", fg="#00c853", 
                font=("Segoe UI", 13, "bold")).pack(pady=10)

    # Listbox para operadores con acceso
    list_frame_con_acceso = tk.Frame(right_frame_rol, bg="#23272a")
    list_frame_con_acceso.pack(fill="both", expand=True, padx=15, pady=(0, 15))

    scroll_con_acceso = tk.Scrollbar(list_frame_con_acceso, orient="vertical")
    scroll_con_acceso.pack(side="right", fill="y")

    listbox_con_acceso = tk.Listbox(list_frame_con_acceso, 
                                    selectmode="extended",
                                    bg="#262a31", 
                                    fg="#00c853", 
                                    font=("Segoe UI", 11),
                                    yscrollcommand=scroll_con_acceso.set,
                                    selectbackground="#4a90e2",
                                    height=20)
    listbox_con_acceso.pack(side="left", fill="both", expand=True)
    scroll_con_acceso.config(command=listbox_con_acceso.yview)

    # Frame de botones entre las dos columnas
    if UI is not None:
        buttons_frame_rol = UI.CTkFrame(rol_cover_container, fg_color="#2c2f33")
    else:
        buttons_frame_rol = tk.Frame(rol_cover_container, bg="#2c2f33")
    buttons_frame_rol.pack(fill="x", padx=10, pady=10)

    def cargar_operadores_rol():
        """Carga operadores separados por su estado Active en sesion"""
        try:
            conn = under_super.get_connection()
            cur = conn.cursor()
            
            # Limpiar listboxes
            listbox_sin_acceso.delete(0, tk.END)
            listbox_con_acceso.delete(0, tk.END)
            
            # Operadores con Active = 1 (sin acceso a covers)
            cur.execute("""
                SELECT DISTINCT s.ID_user 
                FROM sesion s
                INNER JOIN user u ON s.ID_user = u.Nombre_Usuario
                WHERE s.Active = 1 AND u.Rol = 'Operador'
                ORDER BY s.ID_user
            """)
            sin_acceso = cur.fetchall()
            
            for row in sin_acceso:
                listbox_sin_acceso.insert(tk.END, row[0])
            
            # Operadores con Active = 2 (con acceso a covers)
            cur.execute("""
                SELECT DISTINCT s.ID_user 
                FROM sesion s
                INNER JOIN user u ON s.ID_user = u.Nombre_Usuario
                WHERE s.Active = 2 AND u.Rol = 'Operador'
                ORDER BY s.ID_user
            """)
            con_acceso = cur.fetchall()
            
            for row in con_acceso:
                listbox_con_acceso.insert(tk.END, row[0])
            
            cur.close()
            conn.close()
            
            print(f"[DEBUG] Operadores cargados: {len(sin_acceso)} sin acceso, {len(con_acceso)} con acceso")
            
        except Exception as e:
            print(f"[ERROR] cargar_operadores_rol: {e}")
            traceback.print_exc()
            messagebox.showerror("Error", f"Error al cargar operadores:\n{e}", parent=top)

    def habilitar_acceso():
        """Cambia Active de 1 a 2 para los operadores seleccionados (habilitar acceso a covers)"""
        seleccion = listbox_sin_acceso.curselection()
        if not seleccion:
            messagebox.showwarning("Selección", "Selecciona uno o más operadores para habilitar.", parent=top)
            return
        
        operadores = [listbox_sin_acceso.get(i) for i in seleccion]
        
        if not messagebox.askyesno("Confirmar", 
                                   f"¿Habilitar acceso a covers para {len(operadores)} operador(es)?",
                                   parent=top):
            return
        
        try:
            conn = under_super.get_connection()
            cur = conn.cursor()
            
            for operador in operadores:
                cur.execute("""
                    UPDATE sesion 
                    SET Active = 2 
                    WHERE ID_user = %s AND Active = 1
                """, (operador,))
            
            conn.commit()
            cur.close()
            conn.close()
            
            cargar_operadores_rol()
            messagebox.showinfo("Éxito", f"✅ {len(operadores)} operador(es) habilitado(s) para ver covers", parent=top)
            
        except Exception as e:
            print(f"[ERROR] habilitar_acceso: {e}")
            traceback.print_exc()
            messagebox.showerror("Error", f"Error al habilitar acceso:\n{e}", parent=top)

    def deshabilitar_acceso():
        """Cambia Active de 2 a 1 para los operadores seleccionados (quitar acceso a covers)"""
        seleccion = listbox_con_acceso.curselection()
        if not seleccion:
            messagebox.showwarning("Selección", "Selecciona uno o más operadores para deshabilitar.", parent=top)
            return
        
        operadores = [listbox_con_acceso.get(i) for i in seleccion]
        
        if not messagebox.askyesno("Confirmar", 
                                   f"¿Quitar acceso a covers para {len(operadores)} operador(es)?",
                                   parent=top):
            return
        
        try:
            conn = under_super.get_connection()
            cur = conn.cursor()
            
            for operador in operadores:
                cur.execute("""
                    UPDATE sesion 
                    SET Active = 1 
                    WHERE ID_user = %s AND Active = 2
                """, (operador,))
            
            conn.commit()
            cur.close()
            conn.close()
            
            cargar_operadores_rol()
            messagebox.showinfo("Éxito", f"❌ {len(operadores)} operador(es) deshabilitado(s) para ver covers", parent=top)
            
        except Exception as e:
            print(f"[ERROR] deshabilitar_acceso: {e}")
            traceback.print_exc()
            messagebox.showerror("Error", f"Error al deshabilitar acceso:\n{e}", parent=top)

    def refrescar_lista_operadores():
        """Wrapper para refrescar la lista"""
        cargar_operadores_rol()

    # Botones de acción
    if UI is not None:
        UI.CTkButton(buttons_frame_rol, 
                    text="➡️ Habilitar Acceso a Covers",
                    command=habilitar_acceso,
                    fg_color="#00c853",
                    hover_color="#00a043",
                    width=220,
                    height=40,
                    font=("Segoe UI", 13, "bold")).pack(side="left", padx=10, pady=5)
        
        UI.CTkButton(buttons_frame_rol, 
                    text="⬅️ Quitar Acceso a Covers",
                    command=deshabilitar_acceso,
                    fg_color="#f04747",
                    hover_color="#d84040",
                    width=220,
                    height=40,
                    font=("Segoe UI", 13, "bold")).pack(side="left", padx=10, pady=5)
        
        UI.CTkButton(buttons_frame_rol, 
                    text="🔄 Refrescar Lista",
                    command=refrescar_lista_operadores,
                    fg_color="#4a90e2",
                    hover_color="#357ABD",
                    width=180,
                    height=40,
                    font=("Segoe UI", 13, "bold")).pack(side="left", padx=10, pady=5)
    else:
        tk.Button(buttons_frame_rol, 
                 text="➡️ Habilitar Acceso a Covers",
                 command=habilitar_acceso,
                 bg="#00c853",
                 fg="white",
                 font=("Segoe UI", 13, "bold"),
                 relief="flat",
                 width=24).pack(side="left", padx=10, pady=5)
        
        tk.Button(buttons_frame_rol, 
                 text="⬅️ Quitar Acceso a Covers",
                 command=deshabilitar_acceso,
                 bg="#f04747",
                 fg="white",
                 font=("Segoe UI", 13, "bold"),
                 relief="flat",
                 width=24).pack(side="left", padx=10, pady=5)
        
        tk.Button(buttons_frame_rol, 
                 text="🔄 Refrescar Lista",
                 command=refrescar_lista_operadores,
                 bg="#4a90e2",
                 fg="white",
                 font=("Segoe UI", 13, "bold"),
                 relief="flat",
                 width=18).pack(side="left", padx=10, pady=5)

    # ==================== BREAKS CONTAINER ====================
    if UI is not None:
        breaks_container = UI.CTkFrame(top, fg_color="#2c2f33")
    else:
        breaks_container = tk.Frame(top, bg="#2c2f33")
    # NO hacer pack() aquí - se mostrará solo cuando se cambie a modo Breaks

    # Frame de controles (comboboxes y botones) para Breaks
    if UI is not None:
        breaks_controls_frame = UI.CTkFrame(breaks_container, fg_color="#23272a", corner_radius=8)
    else:
        breaks_controls_frame = tk.Frame(breaks_container, bg="#23272a")
    breaks_controls_frame.pack(fill="x", padx=10, pady=10)

    # Función para cargar usuarios desde la BD
    def load_users_breaks():
        """Carga lista de usuarios desde la base de datos"""
        try:
            users = under_super.load_users()
            return users if users else []
        except Exception as e:
            print(f"[ERROR] load_users_breaks: {e}")
            traceback.print_exc()
            return []

    # Función para cargar covers desde la BD
    def load_covers_from_db():
        """Carga covers activos desde gestion_breaks_programados con nombres de usuario"""
        try:
            conn = under_super.get_connection()
            cur = conn.cursor()
            query = """
                SELECT 
                    u_covered.Nombre_Usuario as usuario_cubierto,
                    u_covering.Nombre_Usuario as usuario_cubre,
                    TIME(gbp.Fecha_hora_cover) as hora
                FROM gestion_breaks_programados gbp
                INNER JOIN user u_covered ON gbp.User_covered = u_covered.ID_Usuario
                INNER JOIN user u_covering ON gbp.User_covering = u_covering.ID_Usuario
                WHERE gbp.is_Active = 1
                ORDER BY gbp.Fecha_hora_cover
            """
            cur.execute(query)
            rows = cur.fetchall()
            cur.close()
            conn.close()
            
            # Debug: Imprimir los datos cargados
            print(f"[DEBUG] Covers cargados desde BD: {len(rows)} registros")
            for row in rows:
                print(f"[DEBUG] Cover: {row[0]} cubierto por {row[1]} a las {row[2]}")
            
            return rows
        except Exception as e:
            print(f"[ERROR] load_covers_from_db: {e}")
            traceback.print_exc()
            return []

    # Variables para comboboxes
    usuario_a_cubrir_var = tk.StringVar()
    cubierto_por_var = tk.StringVar()
    hora_var = tk.StringVar()

    # Cargar usuarios
    users_list = load_users_breaks()

    # Primera fila: Usuario a cubrir
    row1_frame_breaks = tk.Frame(breaks_controls_frame, bg="#23272a")
    row1_frame_breaks.pack(fill="x", padx=20, pady=(15, 5))

    if UI is not None:
        UI.CTkLabel(row1_frame_breaks, text="👤 Usuario a Cubrir:", 
                   text_color="#ffffff", font=("Segoe UI", 14, "bold")).pack(side="left", padx=(0, 10))
    else:
        tk.Label(row1_frame_breaks, text="👤 Usuario a Cubrir:", bg="#23272a", fg="#ffffff", 
                font=("Segoe UI", 14, "bold")).pack(side="left", padx=(0, 10))

    if UI is not None:
        usuario_combo_breaks = under_super.FilteredCombobox(row1_frame_breaks, textvariable=usuario_a_cubrir_var,
                                                     values=users_list, width=40, state="readonly",
                                                     font=("Segoe UI", 11))
        usuario_combo_breaks.set("")  # Establecer vacío inicialmente
    else:
        usuario_combo_breaks = ttk.Combobox(row1_frame_breaks, textvariable=usuario_a_cubrir_var,
                                           values=users_list, width=25, state="readonly")
    usuario_combo_breaks.pack(side="left", padx=5)

    # Segunda fila: Cubierto por
    row2_frame_breaks = tk.Frame(breaks_controls_frame, bg="#23272a")
    row2_frame_breaks.pack(fill="x", padx=20, pady=5)

    if UI is not None:
        UI.CTkLabel(row2_frame_breaks, text="🔄 Cubierto Por:", 
                   text_color="#ffffff", font=("Segoe UI", 14, "bold")).pack(side="left", padx=(0, 10))
    else:
        tk.Label(row2_frame_breaks, text="🔄 Cubierto Por:", bg="#23272a", fg="#ffffff", 
                font=("Segoe UI", 14, "bold")).pack(side="left", padx=(0, 10))

    if UI is not None:
        cover_by_combo_breaks = under_super.FilteredCombobox(row2_frame_breaks, textvariable=cubierto_por_var,
                                              values=users_list, width=40, state="readonly",
                                              font=("Segoe UI", 11))
        cover_by_combo_breaks.set("")  # Establecer vacío inicialmente
    else:
        cover_by_combo_breaks = ttk.Combobox(row2_frame_breaks, textvariable=cubierto_por_var,
                                            values=users_list, width=25, state="readonly")
    cover_by_combo_breaks.pack(side="left", padx=5)

    # Generar lista de horas en formato HH:00:00 (cada hora del día)
    horas_disponibles = [f"{h:02d}:00:00" for h in range(24)]

    # Tercera fila: Hora
    row3_frame_breaks = tk.Frame(breaks_controls_frame, bg="#23272a")
    row3_frame_breaks.pack(fill="x", padx=20, pady=5)

    if UI is not None:
        UI.CTkLabel(row3_frame_breaks, text="🕐 Hora Programada:", 
                   text_color="#ffffff", font=("Segoe UI", 14, "bold")).pack(side="left", padx=(0, 10))
    else:
        tk.Label(row3_frame_breaks, text="🕐 Hora Programada:", bg="#23272a", fg="#ffffff", 
                font=("Segoe UI", 14, "bold")).pack(side="left", padx=(0, 10))

    if UI is not None:
        hora_combo_breaks = under_super.FilteredCombobox(
            row3_frame_breaks, 
            textvariable=hora_var,
            values=horas_disponibles,
            width=25,
            font=("Segoe UI", 13),
            background='#2b2b2b', 
            foreground='#ffffff',
            bordercolor='#4a90e2', 
            arrowcolor='#ffffff'
        )
        hora_combo_breaks.pack(side="left", padx=5)
    else:
        hora_entry_breaks = tk.Entry(row3_frame_breaks, textvariable=hora_var, width=27)
        hora_entry_breaks.pack(side="left", padx=5)

    # Función para cargar datos agrupados (matriz)
    def cargar_datos_agrupados_breaks():
        """Carga datos agrupados por quien cubre (covered_by como columnas)"""
        try:
            rows = load_covers_from_db()
            
            # Obtener lista única de "Cubierto Por" (nombres) para las columnas
            covered_by_set = sorted(set(row[1] for row in rows if row[1]))
            
            # Headers: hora primero + columnas de personas que cubren (nombres)
            headers = ["Hora Programada"]
            for cb in covered_by_set:
                headers.append(cb)  # Ya son nombres de usuario
            
            # Agrupar por hora - solo el PRIMER usuario por covered_by y hora
            horas_dict = {}
            for row in rows:
                usuario_cubierto = row[0]  # Nombre del usuario a cubrir
                usuario_cubre = row[1]     # Nombre del usuario que cubre
                hora = str(row[2])          # Hora en formato HH:MM:SS
                
                if hora not in horas_dict:
                    horas_dict[hora] = {cb: "" for cb in covered_by_set}
                
                # Solo asignar si la celda está vacía (un usuario por celda)
                if usuario_cubre in horas_dict[hora] and not horas_dict[hora][usuario_cubre]:
                    horas_dict[hora][usuario_cubre] = usuario_cubierto
            
            # Convertir a lista de filas para el sheet
            data = []
            for hora in sorted(horas_dict.keys()):
                fila = [hora]
                for covered_by in covered_by_set:
                    fila.append(horas_dict[hora][covered_by])
                data.append(fila)
            
            print(f"[DEBUG] Headers construidos para breaks: {headers}")
            print(f"[DEBUG] Data construida: {len(data)} filas")
            
            return headers, data
            
        except Exception as e:
            print(f"[ERROR] cargar_datos_agrupados_breaks: {e}")
            traceback.print_exc()
            return ["Hora Programada"], [[]]

    # Función para limpiar formulario
    def limpiar_breaks():
        usuario_combo_breaks.set("")
        cover_by_combo_breaks.set("")
        hora_var.set("")
    
    # Función wrapper para eliminar cover
    def eliminar_cover_breaks():
        """Wrapper que llama a under_super.eliminar_cover_breaks con todos los parámetros necesarios"""
        if not USE_SHEET:
            return
        
        success, mensaje, rows = under_super.eliminar_cover_breaks(
            breaks_sheet=breaks_sheet,
            parent_window=top
        )
        
        # Si fue exitoso, refrescar la tabla
        if success:
            refrescar_tabla_breaks()

    # Función para refrescar tabla
    def refrescar_tabla_breaks():
        if not USE_SHEET:
            return
        headers, data = cargar_datos_agrupados_breaks()
        breaks_sheet.headers(headers)
        breaks_sheet.set_sheet_data(data)
        # Reajustar anchos después de refrescar
        for i in range(len(headers)):
            breaks_sheet.column_width(column=i, width=120)
        breaks_sheet.redraw()

    # Función wrapper para agregar y refrescar
    def agregar_y_refrescar():
        """Agrega un cover y luego refresca la tabla"""
        try:
            under_super.select_covered_by(
                username, 
                hora=hora_var.get(), 
                usuario=cubierto_por_var.get(),
                cover=usuario_a_cubrir_var.get()
            )
            # Refrescar tabla y limpiar formulario después de agregar
            limpiar_breaks()
            refrescar_tabla_breaks()
        except Exception as e:
            print(f"[ERROR] agregar_y_refrescar: {e}")
            traceback.print_exc()

    # Cuarta fila: Botones
    row4_frame_breaks = tk.Frame(breaks_controls_frame, bg="#23272a")
    row4_frame_breaks.pack(fill="x", padx=20, pady=(5, 15))

    if UI is not None:
        UI.CTkButton(row4_frame_breaks, text="➕ Agregar",
                    command=agregar_y_refrescar,
                    fg_color="#28a745", hover_color="#218838",
                    font=("Segoe UI", 13, "bold"),
                    width=150).pack(side="left", padx=5)
        
        UI.CTkButton(row4_frame_breaks, text="🔄 Limpiar",
                    command=limpiar_breaks,
                    fg_color="#6c757d", hover_color="#5a6268",
                    font=("Segoe UI", 13),
                    width=120).pack(side="left", padx=5)
        
        UI.CTkButton(row4_frame_breaks, text="🗑️ Eliminar Cover Seleccionado",
                    command=eliminar_cover_breaks,
                    fg_color="#dc3545", hover_color="#c82333",
                    font=("Segoe UI", 13),
                    width=220).pack(side="left", padx=5)
    else:
        tk.Button(row4_frame_breaks, text="➕ Agregar",
                 command=agregar_y_refrescar,
                 bg="#28a745", fg="white",
                 font=("Segoe UI", 13, "bold"),
                 relief="flat", width=12).pack(side="left", padx=5)
        
        tk.Button(row4_frame_breaks, text="🔄 Limpiar",
                 command=limpiar_breaks,
                 bg="#6c757d", fg="white",
                 font=("Segoe UI", 13),
                 relief="flat", width=10).pack(side="left", padx=5)
        
        tk.Button(row4_frame_breaks, text="🗑️ Eliminar Cover Seleccionado",
                 command=eliminar_cover_breaks,
                 bg="#dc3545", fg="white",
                 font=("Segoe UI", 13),
                 relief="flat", width=24).pack(side="left", padx=5)

    # Frame para tksheet de Breaks
    if UI is not None:
        breaks_sheet_frame = UI.CTkFrame(breaks_container, fg_color="#2c2f33")
    else:
        breaks_sheet_frame = tk.Frame(breaks_container, bg="#2c2f33")
    breaks_sheet_frame.pack(fill="both", expand=True, padx=10, pady=10)

    if USE_SHEET:
        headers, data = cargar_datos_agrupados_breaks()
        
        breaks_sheet = SheetClass(breaks_sheet_frame,
                                 headers=headers,
                                 theme="dark blue",
                                 width=1280,
                                 height=450)
        breaks_sheet.enable_bindings([
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
        breaks_sheet.pack(fill="both", expand=True)
        
        breaks_sheet.set_sheet_data(data)
        breaks_sheet.change_theme("dark blue")
        
        # Ajustar anchos de columnas
        for i in range(len(headers)):
            breaks_sheet.column_width(column=i, width=120)
        
        # Función para editar celda con doble clic
        def editar_celda_breaks(event):
            try:
                # Obtener la celda seleccionada
                selection = breaks_sheet.get_currently_selected()
                if not selection:
                    return
                
                row, col = selection.row, selection.column
                
                # Ignorar primera columna (hora) y primera fila (headers)
                if col == 0 or row < 0:
                    return
                
                # Obtener datos de la celda
                current_data = breaks_sheet.get_sheet_data()
                if row >= len(current_data):
                    return
                
                hora_actual = current_data[row][0]  # Primera columna es la hora
                usuario_cubierto_actual = current_data[row][col] if col < len(current_data[row]) else ""  # El que ESTÁ cubierto
                
                # ⭐ OBTENER HEADERS DEL BREAKS_SHEET DIRECTAMENTE (no usar variable 'headers' que puede ser de otra tabla)
                breaks_headers = breaks_sheet.headers()
                usuario_cubre_actual = breaks_headers[col]  # El header es el usuario que HACE el cover
                
                # Si la celda está vacía, no permitir edición
                if not usuario_cubierto_actual or usuario_cubierto_actual.strip() == "":
                    messagebox.showinfo("Información", 
                                      "No hay cover asignado en esta celda.\n\nUsa el botón 'Añadir' para crear un nuevo cover.",
                                      parent=top)
                    return
                
                # Crear ventana de edición
                if UI is not None:
                    edit_win = UI.CTkToplevel(top)
                    edit_win.title("Editar Cover")
                    edit_win.geometry("500x400")
                    edit_win.configure(fg_color="#2c2f33")
                else:
                    edit_win = tk.Toplevel(top)
                    edit_win.title("Editar Cover")
                    edit_win.geometry("500x400")
                    edit_win.configure(bg="#2c2f33")
                
                edit_win.transient(top)
                edit_win.grab_set()
                
                # Frame principal
                if UI is not None:
                    main_frame = UI.CTkFrame(edit_win, fg_color="#23272a", corner_radius=10)
                else:
                    main_frame = tk.Frame(edit_win, bg="#23272a")
                main_frame.pack(fill="both", expand=True, padx=20, pady=20)
                
                # Título
                if UI is not None:
                    UI.CTkLabel(main_frame, text="✏️ Editar Cover de Break", 
                               font=("Segoe UI", 20, "bold"),
                               text_color="#ffffff").pack(pady=(10, 20))
                else:
                    tk.Label(main_frame, text="✏️ Editar Cover de Break", 
                            font=("Segoe UI", 20, "bold"),
                            bg="#23272a", fg="#ffffff").pack(pady=(10, 20))
                
                # Información del cover con mejor formato
                if UI is not None:
                    info_frame = UI.CTkFrame(main_frame, fg_color="#2c2f33", corner_radius=8)
                else:
                    info_frame = tk.Frame(main_frame, bg="#2c2f33")
                info_frame.pack(fill="x", padx=10, pady=10)
                
                # Fila 1: Hora
                hora_row = tk.Frame(info_frame, bg="#2c2f33")
                hora_row.pack(fill="x", padx=15, pady=8)
                if UI is not None:
                    UI.CTkLabel(hora_row, text="🕐 Hora:", 
                               font=("Segoe UI", 13, "bold"),
                               text_color="#99aab5", width=150).pack(side="left")
                    UI.CTkLabel(hora_row, text=hora_actual, 
                               font=("Segoe UI", 13),
                               text_color="#ffffff").pack(side="left")
                else:
                    tk.Label(hora_row, text="🕐 Hora:", 
                            font=("Segoe UI", 13, "bold"),
                            bg="#2c2f33", fg="#99aab5", width=15, anchor="w").pack(side="left")
                    tk.Label(hora_row, text=hora_actual, 
                            font=("Segoe UI", 13),
                            bg="#2c2f33", fg="#ffffff").pack(side="left")
                
                # Fila 2: Usuario que hace el cover
                covering_row = tk.Frame(info_frame, bg="#2c2f33")
                covering_row.pack(fill="x", padx=15, pady=8)
                if UI is not None:
                    UI.CTkLabel(covering_row, text="👤 Usuario que cubre:", 
                               font=("Segoe UI", 13, "bold"),
                               text_color="#99aab5", width=150).pack(side="left")
                    UI.CTkLabel(covering_row, text=usuario_cubre_actual, 
                               font=("Segoe UI", 13),
                               text_color="#4aa3ff").pack(side="left")
                else:
                    tk.Label(covering_row, text="👤 Usuario que cubre:", 
                            font=("Segoe UI", 13, "bold"),
                            bg="#2c2f33", fg="#99aab5", width=15, anchor="w").pack(side="left")
                    tk.Label(covering_row, text=usuario_cubre_actual, 
                            font=("Segoe UI", 13),
                            bg="#2c2f33", fg="#4aa3ff").pack(side="left")
                
                # Fila 3: Usuario cubierto actual
                actual_row = tk.Frame(info_frame, bg="#2c2f33")
                actual_row.pack(fill="x", padx=15, pady=8)
                if UI is not None:
                    UI.CTkLabel(actual_row, text="📋 Usuario cubierto:", 
                               font=("Segoe UI", 13, "bold"),
                               text_color="#99aab5", width=150).pack(side="left")
                    UI.CTkLabel(actual_row, text=usuario_cubierto_actual, 
                               font=("Segoe UI", 13, "bold"),
                               text_color="#7289da").pack(side="left")
                else:
                    tk.Label(actual_row, text="📋 Usuario cubierto:", 
                            font=("Segoe UI", 13, "bold"),
                            bg="#2c2f33", fg="#99aab5", width=15, anchor="w").pack(side="left")
                    tk.Label(actual_row, text=usuario_cubierto_actual, 
                            font=("Segoe UI", 13, "bold"),
                            bg="#2c2f33", fg="#7289da").pack(side="left")
                
                # Selector de nuevo usuario cubierto
                if UI is not None:
                    UI.CTkLabel(main_frame, text="➡️ Cambiar a (nuevo usuario cubierto):", 
                               font=("Segoe UI", 13, "bold"),
                               text_color="#ffffff").pack(anchor="w", padx=10, pady=(15, 5))
                else:
                    tk.Label(main_frame, text="➡️ Cambiar a (nuevo usuario cubierto):", 
                            font=("Segoe UI", 13, "bold"),
                            bg="#23272a", fg="#ffffff").pack(anchor="w", padx=10, pady=(15, 5))
                
                # Obtener lista de usuarios
                usuarios_disponibles = []
                try:
                    conn = under_super.get_connection()
                    cur = conn.cursor()
                    cur.execute("SELECT Nombre_Usuario FROM user ORDER BY Nombre_Usuario")
                    usuarios_disponibles = [row[0] for row in cur.fetchall()]
                    cur.close()
                    conn.close()
                except Exception as e:
                    print(f"[ERROR] No se pudieron cargar usuarios: {e}")
                
                nuevo_usuario_cubierto_var = tk.StringVar(value=usuario_cubierto_actual)
                
                # Usar FilteredCombobox para mejor búsqueda
                usuario_combo = under_super.FilteredCombobox(
                    main_frame,
                    textvariable=nuevo_usuario_cubierto_var,
                    values=usuarios_disponibles,
                    width=35,
                    font=("Segoe UI", 12),
                    bordercolor="#5ab4ff",
                    borderwidth=2,
                    background="#2b2b2b",
                    foreground="#ffffff",
                    fieldbackground="#2b2b2b"
                )
                usuario_combo.pack(padx=10, pady=5, fill="x")
                
                # Función para guardar cambios
                def guardar_cambios():
                    nuevo_usuario_cubierto = nuevo_usuario_cubierto_var.get().strip()
                    if not nuevo_usuario_cubierto:
                        messagebox.showwarning("Advertencia", "Debe seleccionar un usuario", parent=edit_win)
                        return
                    
                    # Llamar a la función de under_super para actualizar el cover
                    # Parámetros: supervisor, hora, quien_cubre, usuario_cubierto_anterior, nuevo_usuario_cubierto
                    exito = under_super.actualizar_cover_breaks(
                        username=username,
                        hora_actual=hora_actual,
                        covered_by_actual=usuario_cubre_actual,
                        usuario_actual=usuario_cubierto_actual,
                        nuevo_usuario=nuevo_usuario_cubierto
                    )
                    
                    if exito:
                        edit_win.destroy()
                        refrescar_tabla_breaks()
                    else:
                        messagebox.showerror("Error", "No se pudo actualizar el cover", parent=edit_win)
                
                # Botones
                if UI is not None:
                    buttons_frame = UI.CTkFrame(main_frame, fg_color="transparent")
                else:
                    buttons_frame = tk.Frame(main_frame, bg="#23272a")
                buttons_frame.pack(pady=20)
                
                if UI is not None:
                    UI.CTkButton(buttons_frame, text="💾 Guardar", 
                                command=guardar_cambios,
                                fg_color="#43b581",
                                hover_color="#3ca374",
                                width=120,
                                font=("Segoe UI", 12, "bold")).pack(side="left", padx=5)
                    UI.CTkButton(buttons_frame, text="❌ Cancelar", 
                                command=edit_win.destroy,
                                fg_color="#f04747",
                                hover_color="#d84040",
                                width=120,
                                font=("Segoe UI", 12, "bold")).pack(side="left", padx=5)
                else:
                    tk.Button(buttons_frame, text="💾 Guardar", 
                             command=guardar_cambios,
                             bg="#43b581",
                             fg="white",
                             font=("Segoe UI", 12, "bold"),
                             width=12).pack(side="left", padx=5)
                    tk.Button(buttons_frame, text="❌ Cancelar", 
                             command=edit_win.destroy,
                             bg="#f04747",
                             fg="white",
                             font=("Segoe UI", 12, "bold"),
                             width=12).pack(side="left", padx=5)
                
            except Exception as e:
                print(f"[ERROR] editar_celda_breaks: {e}")
                traceback.print_exc()
                messagebox.showerror("Error", f"Error al editar celda: {e}")
        
        # Vincular evento de doble clic
        breaks_sheet.bind("<Double-Button-1>", editar_celda_breaks)
        
    else:
        if UI is not None:
            UI.CTkLabel(breaks_sheet_frame, text="⚠️ tksheet no instalado", 
                       text_color="#ff6b6b", font=("Segoe UI", 16)).pack(pady=20)
        else:
            tk.Label(breaks_sheet_frame, text="⚠️ tksheet no instalado", 
                    bg="#2c2f33", fg="#ff6b6b", font=("Segoe UI", 16)).pack(pady=20)

    # ==================== ADMIN CONTAINER ====================
    
    if UI is not None:
        admin_container = UI.CTkFrame(top, fg_color="#2c2f33")
    else:
        admin_container = tk.Frame(top, bg="#2c2f33")
    # No hacer pack aquí, se hace en switch_view()
    
    # Frame superior para selección de tabla
    if UI is not None:
        admin_toolbar = UI.CTkFrame(admin_container, fg_color="#23272a", corner_radius=0, height=100)
    else:
        admin_toolbar = tk.Frame(admin_container, bg="#23272a", height=100)
    admin_toolbar.pack(fill="x", padx=0, pady=0)
    admin_toolbar.pack_propagate(False)
    
    if UI is not None:
        UI.CTkLabel(admin_toolbar, text="🔧 Administración de Base de Datos", 
                   font=("Segoe UI", 14, "bold"), text_color="#e0e0e0").pack(side="top", padx=20, pady=(10, 5))
    else:
        tk.Label(admin_toolbar, text="🔧 Administración de Base de Datos", 
                bg="#23272a", fg="#e0e0e0", font=("Segoe UI", 14, "bold")).pack(side="top", padx=20, pady=(10, 5))
    
    # Frame para controles
    if UI is not None:
        admin_controls = UI.CTkFrame(admin_toolbar, fg_color="transparent")
    else:
        admin_controls = tk.Frame(admin_toolbar, bg="#23272a")
    admin_controls.pack(fill="x", padx=20, pady=5)
    
    # Variable y selector de tabla
    admin_table_var = tk.StringVar()
    admin_tables_list = ["Sitios", "user", "Actividades", "gestion_breaks_programados", "Covers_realizados", "Covers_programados", "Sesiones", "Estaciones", "Specials", "eventos"]
    
    if UI is not None:
        UI.CTkLabel(admin_controls, text="Tabla:", text_color="#e0e0e0").pack(side="left", padx=5)
        admin_table_cb = UI.CTkComboBox(
            admin_controls, variable=admin_table_var, values=admin_tables_list,
            font=("Segoe UI", 10), width=200
        )
        admin_table_cb.pack(side="left", padx=5)
    else:
        tk.Label(admin_controls, text="Tabla:", bg="#23272a", fg="#e0e0e0").pack(side="left", padx=5)
        admin_table_cb = under_super.FilteredCombobox(
            admin_controls, textvariable=admin_table_var, values=admin_tables_list,
            font=("Segoe UI", 10), width=25,
            background='#2b2b2b', foreground='#ffffff',
            bordercolor='#4a90e2', arrowcolor='#ffffff'
        )
        admin_table_cb.pack(side="left", padx=5)
    
    # Metadata de tablas cargadas
    admin_metadata = {
        'current_table': None,
        'col_names': [],
        'pk': None,
        'rows': []
    }
    
    # Funciones auxiliares para Admin
    def sanitize_col_id(name, used):
        cid = re.sub(r'[^0-9A-Za-z_]', '_', str(name))
        if re.match(r'^\d', cid):
            cid = "_" + cid
        base = cid
        i = 1
        while cid in used or cid == "":
            cid = f"{base}_{i}"
            i += 1
        used.add(cid)
        return cid
    
    def guess_pk(col_names):
        candidates = [c for c in col_names if c.lower() in ("id", "id_") or c.lower().endswith("_id") or c.lower().startswith("id_")]
        if candidates:
            return candidates[0]
        for c in col_names:
            if 'id' in c.lower():
                return c
        return col_names[0] if col_names else None
    
    def load_admin_table():
        """Carga la tabla seleccionada en el tksheet de admin"""
        tabla = admin_table_var.get()
        if not tabla:
            messagebox.showwarning("Atención", "Seleccione una tabla para cargar.", parent=top)
            return
        
        try:
            conn = under_super.get_connection()
            cursor = conn.cursor()
            
            query = f"SELECT * FROM {tabla}"
            cursor.execute(query)
            rows = cursor.fetchall()
            
            col_names = [desc[0] for desc in cursor.description]
            
            # Formatear datos para tksheet
            data = []
            for row in rows:
                row_data = []
                for v in row:
                    if v is None:
                        row_data.append("")
                    else:
                        try:
                            if isinstance(v, (bytes, bytearray, memoryview)):
                                row_data.append(v.hex())
                            else:
                                row_data.append(str(v))
                        except Exception:
                            row_data.append(repr(v))
                data.append(row_data)
            
            # Actualizar metadata
            admin_metadata['current_table'] = tabla
            admin_metadata['col_names'] = col_names
            admin_metadata['pk'] = guess_pk(col_names)
            admin_metadata['rows'] = rows
            
            # Configurar tksheet
            admin_sheet.set_sheet_data(data if data else [["No hay datos"] + [""] * (len(col_names)-1)])
            admin_sheet.headers(col_names)
            
            # Ajustar anchos de columna
            for col_idx in range(len(col_names)):
                admin_sheet.column_width(column=col_idx, width=150)
            
            admin_sheet.refresh()
            
            cursor.close()
            conn.close()
            
            print(f"[INFO] Tabla {tabla} cargada: {len(data)} registros")
            
        except Exception as e:
            print(f"[ERROR] load_admin_table: {e}")
            traceback.print_exc()
            messagebox.showerror("Error", f"Error al cargar tabla:\n{e}", parent=top)
    
    def delete_admin_selected():
        """Elimina el registro seleccionado (usando sistema de papelera)"""
        tabla = admin_metadata['current_table']
        if not tabla:
            messagebox.showwarning("Atención", "Primero cargue una tabla.", parent=top)
            return
        
        selected = admin_sheet.get_selected_rows()
        if not selected:
            messagebox.showwarning("Atención", "Seleccione un registro para eliminar.", parent=top)
            return
        
        # Convertir a lista si es un set
        if isinstance(selected, set):
            selected = list(selected)
        
        pk_name = admin_metadata.get('pk')
        col_names = admin_metadata.get('col_names', [])
        if not pk_name or pk_name not in col_names:
            messagebox.showwarning("No PK", "No se pudo determinar la columna primaria.", parent=top)
            return
        
        if not messagebox.askyesno("Confirmar", "¿Mover el registro a Papelera?", parent=top):
            return
        
        try:
            pk_idx = col_names.index(pk_name)
            row_idx = selected[0]
            row_data = admin_sheet.get_row_data(row_idx)
            
            # Convertir a lista si es un set
            if isinstance(row_data, set):
                row_data = list(row_data)
            
            pk_value = row_data[pk_idx] if row_data and pk_idx < len(row_data) else None
            
            if pk_value is None:
                messagebox.showerror("Error", "No se pudo leer el valor de la PK.", parent=top)
                return
            
            ok = safe_delete(
                table_name=tabla,
                pk_column=pk_name,
                pk_value=pk_value,
                deleted_by=username,
                reason=f"Eliminado desde Admin ({tabla})"
            )
            
            if ok:
                load_admin_table()
                messagebox.showinfo("Éxito", "✅ Registro movido a Papelera.", parent=top)
            else:
                messagebox.showerror("Error", "No se pudo mover el registro a Papelera", parent=top)
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo eliminar:\n{e}", parent=top)
            traceback.print_exc()
    
    def edit_admin_selected():
        """Edita el registro seleccionado"""
        tabla = admin_metadata['current_table']
        if not tabla:
            messagebox.showwarning("Atención", "Primero cargue una tabla.", parent=top)
            return
        
        selected = admin_sheet.get_selected_rows()
        if not selected:
            messagebox.showwarning("Atención", "Seleccione un registro para editar.", parent=top)
            return
        
        # Convertir a lista si es un set
        if isinstance(selected, set):
            selected = list(selected)
        
        pk_name = admin_metadata.get('pk')
        col_names = admin_metadata.get('col_names', [])
        if not pk_name or pk_name not in col_names:
            messagebox.showwarning("No PK", "No se pudo determinar la columna primaria.", parent=top)
            return
        
        pk_idx = col_names.index(pk_name)
        row_idx = selected[0]
        row_data = admin_sheet.get_row_data(row_idx)
        
        # Convertir a lista si es un set
        if isinstance(row_data, set):
            row_data = list(row_data)
        
        if not row_data or pk_idx >= len(row_data):
            messagebox.showerror("Error", "No se pudo leer el registro.", parent=top)
            return
        pk_value = row_data[pk_idx]
        
        # Ventana de edición con CustomTkinter
        if UI is not None:
            edit_win = UI.CTkToplevel(top)
            edit_win.configure(fg_color="#2c2f33")
        else:
            edit_win = tk.Toplevel(top)
            edit_win.configure(bg="#2c2f33")
        
        edit_win.title(f"Editar registro de {tabla}")
        win_height = min(130 + 60 * len(col_names), 850)
        edit_win.geometry(f"550x{win_height}")
        edit_win.resizable(False, False)
        
        # Título
        if UI is not None:
            UI.CTkLabel(edit_win, text=f"✏️ Editar: {tabla}", 
                       font=("Segoe UI", 14, "bold"), text_color="#e0e0e0").pack(pady=(10, 20))
        else:
            tk.Label(edit_win, text=f"✏️ Editar: {tabla}", 
                    bg="#2c2f33", fg="#e0e0e0", font=("Segoe UI", 14, "bold")).pack(pady=(10, 20))
        
        # Frame inferior para botón (crear PRIMERO para que aparezca al fondo)
        if UI is not None:
            button_frame = UI.CTkFrame(edit_win, fg_color="#2c2f33")
            button_frame.pack(side="bottom", fill="x", pady=(10, 15))
        else:
            button_frame = tk.Frame(edit_win, bg="#2c2f33")
            button_frame.pack(side="bottom", fill="x", pady=(10, 15))
        
        # Frame scrollable para campos
        if UI is not None:
            fields_container = UI.CTkScrollableFrame(edit_win, fg_color="transparent")
            fields_container.pack(fill="both", expand=True, padx=20, pady=(0, 10))
            fields_frame = fields_container
        else:
            canvas = tk.Canvas(edit_win, bg="#2c2f33", highlightthickness=0)
            scrollbar = tk.Scrollbar(edit_win, orient="vertical", command=canvas.yview)
            fields_frame = tk.Frame(canvas, bg="#2c2f33")
            canvas.configure(yscrollcommand=scrollbar.set)
            canvas.pack(side="left", fill="both", expand=True, padx=20)
            scrollbar.pack(side="right", fill="y")
            canvas.create_window((0, 0), window=fields_frame, anchor="nw")
            fields_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        
        entries = {}
        for i, cname in enumerate(col_names):
            if UI is not None:
                UI.CTkLabel(fields_frame, text=f"{cname}:", text_color="#a3c9f9", 
                           font=("Segoe UI", 10, "bold")).grid(row=i, column=0, sticky="w", padx=10, pady=8)
                e = UI.CTkEntry(fields_frame, width=280, font=("Segoe UI", 10))
                e.grid(row=i, column=1, padx=10, pady=8)
            else:
                tk.Label(fields_frame, text=f"{cname}:", bg="#2c2f33", fg="#a3c9f9", 
                        font=("Segoe UI", 10, "bold")).grid(row=i, column=0, sticky="w", padx=10, pady=8)
                e = tk.Entry(fields_frame, width=38, font=("Segoe UI", 10))
                e.grid(row=i, column=1, padx=10, pady=8)
            
            if i < len(row_data):
                e.insert(0, row_data[i])
            
            # PK de solo lectura
            if cname == pk_name:
                if UI is not None:
                    e.configure(state="disabled")
                else:
                    e.config(state="readonly")
            
            entries[cname] = e
        
        def save_changes():
            new_values = {}
            for c in col_names:
                try:
                    # Para campos deshabilitados, usar el valor original
                    if c == pk_name:
                        new_values[c] = pk_value
                    else:
                        new_values[c] = entries[c].get()
                except:
                    new_values[c] = ""
            
            try:
                conn = under_super.get_connection()
                cur = conn.cursor()
                
                set_clause = ", ".join(f"`{c}` = %s" for c in col_names if c != pk_name)
                sql = f"UPDATE `{tabla}` SET {set_clause} WHERE `{pk_name}` = %s"
                
                params = []
                for c in col_names:
                    if c != pk_name:
                        value = new_values[c]
                        if c == "User_Logged" and (value is None or value == ""):
                            value = None
                        params.append(value)
                params.append(pk_value)
                
                cur.execute(sql, params)
                conn.commit()
                cur.close()
                conn.close()
                
                load_admin_table()
                edit_win.destroy()
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo actualizar:\n{e}", parent=edit_win)
                traceback.print_exc()
        
        # Botón guardar (agregar al frame que ya fue creado)
        if UI is not None:
            UI.CTkButton(button_frame, text="💾 Guardar", command=save_changes,
                        fg_color="#4a90e2", hover_color="#357ABD",
                        width=200, height=40, font=("Segoe UI", 12, "bold")).pack(pady=5)
        else:
            tk.Button(button_frame, text="💾 Guardar", bg="#4aa3ff", fg="white", 
                     font=("Segoe UI", 11, "bold"), command=save_changes, width=20, height=2).pack(pady=5)
    
    def create_admin_record():
        """Crea un nuevo registro en la tabla actual"""
        tabla = admin_metadata['current_table']
        if not tabla:
            messagebox.showwarning("Atención", "Primero cargue una tabla.", parent=top)
            return
        
        col_names = admin_metadata.get('col_names', [])
        pk_name = admin_metadata.get('pk')
        
        # Determinar qué columnas mostrar
        # Para Sitios: mostrar todo (ID no es autoincremental)
        # Para otras tablas: omitir columnas ID autoincrementales
        if tabla == "Sitios":
            visible_cols = col_names
        else:
            # Omitir columnas que terminan con _id o son ID, excepto FK importantes
            visible_cols = []
            for c in col_names:
                c_lower = c.lower()
                # Omitir IDs autoincrementales pero mantener FKs importantes
                if c_lower in ('id_eventos', 'id_usuario', 'id_special', 'id_cover', 'id_sesion', 'id_estacion'):
                    # Es un ID autoincremental, omitir
                    continue
                # Mantener FKs como ID_Sitio, ID_Usuario (sin guion bajo al inicio)
                visible_cols.append(c)
        
        # Ventana de creación con CustomTkinter
        if UI is not None:
            create_win = UI.CTkToplevel(top)
            create_win.configure(fg_color="#2c2f33")
        else:
            create_win = tk.Toplevel(top)
            create_win.configure(bg="#2c2f33")
        
        create_win.title(f"Crear registro en {tabla}")
        win_height = min(120 + 50 * len(visible_cols), 750)
        create_win.geometry(f"550x{win_height}")
        create_win.resizable(False, False)
        
        # Título
        if UI is not None:
            UI.CTkLabel(create_win, text=f"➕ Crear en: {tabla}", 
                       font=("Segoe UI", 14, "bold"), text_color="#e0e0e0").pack(pady=(10, 20))
        else:
            tk.Label(create_win, text=f"➕ Crear en: {tabla}", 
                    bg="#2c2f33", fg="#e0e0e0", font=("Segoe UI", 14, "bold")).pack(pady=(10, 20))
        
        # Frame inferior para botón (crear PRIMERO para que aparezca al fondo)
        if UI is not None:
            button_frame = UI.CTkFrame(create_win, fg_color="#2c2f33")
            button_frame.pack(side="bottom", fill="x", pady=(10, 15))
        else:
            button_frame = tk.Frame(create_win, bg="#2c2f33")
            button_frame.pack(side="bottom", fill="x", pady=(10, 15))
        
        # Frame scrollable para campos
        if UI is not None:
            fields_container = UI.CTkScrollableFrame(create_win, fg_color="transparent")
            fields_container.pack(fill="both", expand=True, padx=20, pady=(0, 10))
            fields_frame = fields_container
        else:
            canvas = tk.Canvas(create_win, bg="#2c2f33", highlightthickness=0)
            scrollbar = tk.Scrollbar(create_win, orient="vertical", command=canvas.yview)
            fields_frame = tk.Frame(canvas, bg="#2c2f33")
            canvas.configure(yscrollcommand=scrollbar.set)
            canvas.pack(side="left", fill="both", expand=True, padx=20)
            scrollbar.pack(side="right", fill="y")
            canvas.create_window((0, 0), window=fields_frame, anchor="nw")
            fields_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        
        entries = {}
        for i, cname in enumerate(visible_cols):
            if UI is not None:
                UI.CTkLabel(fields_frame, text=f"{cname}:", text_color="#a3c9f9", 
                           font=("Segoe UI", 10, "bold")).grid(row=i, column=0, sticky="w", padx=10, pady=8)
                e = UI.CTkEntry(fields_frame, width=280, font=("Segoe UI", 10))
                e.grid(row=i, column=1, padx=10, pady=8)
            else:
                tk.Label(fields_frame, text=f"{cname}:", bg="#2c2f33", fg="#a3c9f9", 
                        font=("Segoe UI", 10, "bold")).grid(row=i, column=0, sticky="w", padx=10, pady=8)
                e = tk.Entry(fields_frame, width=38, font=("Segoe UI", 10))
                e.grid(row=i, column=1, padx=10, pady=8)
            
            entries[cname] = e
        
        def save_new():
            new_values = {}
            for c in visible_cols:
                try:
                    new_values[c] = entries[c].get()
                except:
                    new_values[c] = ""
            
            try:
                conn = under_super.get_connection()
                cur = conn.cursor()
                
                # Construir INSERT solo con columnas visibles
                columns = ", ".join(f"`{c}`" for c in visible_cols)
                placeholders = ", ".join(["%s"] * len(visible_cols))
                sql = f"INSERT INTO `{tabla}` ({columns}) VALUES ({placeholders})"
                
                params = []
                for c in visible_cols:
                    value = new_values[c]
                    if value == "":
                        value = None
                    params.append(value)
                
                cur.execute(sql, params)
                conn.commit()
                cur.close()
                conn.close()
                
                load_admin_table()
                create_win.destroy()
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo crear:\n{e}", parent=create_win)
                traceback.print_exc()
        
        # Botón guardar (agregar al frame que ya fue creado)
        if UI is not None:
            UI.CTkButton(button_frame, text="💾 Guardar", command=save_new,
                        fg_color="#00c853", hover_color="#00a043",
                        width=200, height=40, font=("Segoe UI", 12, "bold")).pack(pady=5)
        else:
            tk.Button(button_frame, text="💾 Guardar", bg="#00c853", fg="white", 
                     font=("Segoe UI", 11, "bold"), command=save_new, width=20, height=2).pack(pady=5)
    
    # Botones de acción en admin_controls
    if UI is not None:
        UI.CTkButton(admin_controls, text="🔄 Cargar", command=load_admin_table,
                    fg_color="#4a90e2", hover_color="#357ABD",
                    width=100, height=32, font=("Segoe UI", 11, "bold")).pack(side="left", padx=5)
        UI.CTkButton(admin_controls, text="➕ Crear", command=create_admin_record,
                    fg_color="#00c853", hover_color="#00a043",
                    width=100, height=32, font=("Segoe UI", 11, "bold")).pack(side="left", padx=5)
        UI.CTkButton(admin_controls, text="✏️ Editar", command=edit_admin_selected,
                    fg_color="#f0ad4e", hover_color="#ec971f",
                    width=100, height=32, font=("Segoe UI", 11, "bold")).pack(side="left", padx=5)
        UI.CTkButton(admin_controls, text="🗑️ Eliminar", command=delete_admin_selected,
                    fg_color="#d32f2f", hover_color="#b71c1c",
                    width=100, height=32, font=("Segoe UI", 11, "bold")).pack(side="left", padx=5)
    else:
        tk.Button(admin_controls, text="🔄 Cargar", command=load_admin_table,
                 bg="#4a90e2", fg="white", font=("Segoe UI", 11, "bold"),
                 relief="flat", width=10).pack(side="left", padx=5)
        tk.Button(admin_controls, text="➕ Crear", command=create_admin_record,
                 bg="#00c853", fg="white", font=("Segoe UI", 11, "bold"),
                 relief="flat", width=10).pack(side="left", padx=5)
        tk.Button(admin_controls, text="✏️ Editar", command=edit_admin_selected,
                 bg="#f0ad4e", fg="white", font=("Segoe UI", 11, "bold"),
                 relief="flat", width=10).pack(side="left", padx=5)
        tk.Button(admin_controls, text="🗑️ Eliminar", command=delete_admin_selected,
                 bg="#d32f2f", fg="white", font=("Segoe UI", 11, "bold"),
                 relief="flat", width=10).pack(side="left", padx=5)
    
    # Frame para tksheet de Admin
    if UI is not None:
        admin_sheet_frame = UI.CTkFrame(admin_container, fg_color="#2c2f33")
    else:
        admin_sheet_frame = tk.Frame(admin_container, bg="#2c2f33")
    admin_sheet_frame.pack(fill="both", expand=True, padx=10, pady=10)
    
    # Crear tksheet de Admin
    admin_sheet = SheetClass(
        admin_sheet_frame,
        data=[["Seleccione una tabla y presione 'Cargar'"]],
        headers=["Datos"],
        theme="dark blue",
        height=500,
        width=1330,
        show_selected_cells_border=True,
        show_row_index=True,
        show_top_left=False,
        empty_horizontal=0,
        empty_vertical=0,
        auto_resize_columns=False,
        auto_resize_rows=False
    )
    admin_sheet.enable_bindings([
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
    admin_sheet.pack(fill="both", expand=True)

    # ==================== CLOSE HANDLER ====================
    
    # ⭐ CONFIGURAR CIERRE DE VENTANA: Ejecutar logout automáticamente
    def on_window_close_leadsuper():
        """Maneja el cierre de la ventana principal ejecutando logout y mostrando login"""
        try:
            if session_id and station:
                login.do_logout(session_id, station, top)
            if not session_id:
                try:
                    login.show_login()
                    top.destroy()
                except Exception as e:
                    print(f"[ERROR] Error during logout: {e}")
        except Exception as e:
            print(f"[ERROR] Error destroying window: {e}")
    # Configurar protocolo de cierre (botón X)
    top.protocol("WM_DELETE_WINDOW", on_window_close_leadsuper)


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
            conn = under_super.get_connection()
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
            conn = under_super.get_connection()
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
            conn = under_super.get_connection()
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


def open_hybrid_events(username, session_id=None, station=None, root=None):
    station = station or under_super.get_station(username)
    """
    🚀 VENTANA HÍBRIDA: Registro + Visualización de Eventos
    
    Combina funcionalidad de registro y edición en una sola ventana tipo Excel:
    - Visualización de eventos del turno actual en tksheet
    - Edición inline con doble-click
    - Widgets especializados por columna (DatePicker, FilteredCombobox, etc.)
    - Botones: Nuevo, Guardar, Eliminar, Refrescar
    - Auto-refresh configurable
    - Validaciones en tiempo real
    - Incluye botones Cover y Start/End Shift en header
    """
    # Singleton
    ex = _focus_singleton('hybrid_events')
    if ex:
        return ex

    # CustomTkinter setup
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

    # tksheet setup
    USE_SHEET = False
    SheetClass = None
    try:
        from tksheet import Sheet as _Sheet
        SheetClass = _Sheet
        USE_SHEET = True
    except Exception:
        messagebox.showerror("Error", "tksheet no está instalado.\nInstala con: pip install tksheet")
        return

    # Crear ventana principal
    # ⭐ Asegurar que existe un root oculto antes de crear Toplevel
    if tk._default_root is None:
        hidden_root = tk.Tk()
        hidden_root.withdraw()  # Ocultar completamente
        tk._default_root = hidden_root
    
    if UI is not None:
        top = UI.CTkToplevel()
        top.configure(fg_color="#1e1e1e")
    else:
        top = tk.Toplevel()
        top.configure(bg="#1e1e1e")
    
    top.title(f"📊 Eventos - {username}")
    top.geometry("1200x800")  # Ancho reducido al eliminar columna "Out at"
    top.resizable(True, True)

    # ⭐ VARIABLE DE MODO: 'daily', 'specials' o 'covers'
    current_mode = tk.StringVar(value='daily')  # Estado del toggle
    
    # Variables de estado
    row_data_cache = []  # Lista de diccionarios con datos de cada fila
    row_ids = []  # IDs de eventos (None para nuevos)
    pending_changes = []  # Lista de índices de filas con cambios sin guardar

    # Columnas de la hoja (DAILY)
    columns_daily = ["Fecha Hora", "Sitio", "Actividad", "Cantidad", "Camera", "Descripción"]
    
    # Columnas para SPECIALS (sin ID ni Usuario - son irrelevantes)
    columns_specials = ["Fecha Hora", "Sitio", "Actividad", "Cantidad", "Camera", "Descripcion", "TZ", "Marca"]
    
    # Columnas para COVERS (sin ID - solo información relevante)
    columns_covers = ["Nombre Usuarios", "Time Request", "Cover in", "Cover out", "Motivo", "Covered by", "Activo"]
    
    # Columnas activas (inicia con daily)
    columns = columns_daily
    
    # Anchos personalizados para DAILY
    custom_widths_daily = {
        "Fecha Hora ": 140,
        "Sitio": 260,
        "Actividad": 170,
        "Cantidad": 80,
        "Camera": 90,
        "Descripción": 340  # Ampliado al eliminar "Out at"
    }
    
    # Anchos personalizados para SPECIALS (sin ID ni Usuario)
    custom_widths_specials = {
        "Fecha Hora": 120,
        "Sitio": 277,
        "Actividad": 150,
        "Cantidad": 60,
        "Camera": 60,
        "Descripcion": 210,
        "TZ": 80,  # Aumentado de 40 a 80 para mejor visibilidad
        "Marca": 180
    }
    
    # Anchos personalizados para COVERS (sin ID_Covers)
    custom_widths_covers = {
        "Nombre Usuarios": 150,
        "Time Request": 150,
        "Cover in": 150,
        "Cover out": 150,
        "Motivo": 200,
        "Covered by": 150,
        "Activo": 80
    }
    
    # Anchos activos (inicia con daily)
    custom_widths = custom_widths_daily

    # Header
    if UI is not None:
        header = UI.CTkFrame(top, fg_color="#23272a", corner_radius=0)
    else:
        header = tk.Frame(top, bg="#23272a")
    header.pack(fill="x", padx=0, pady=0)

    # ⭐ FUNCIÓN: Manejar Start/End Shift
    def handle_shift_button():
        """Maneja el click en el botón Start/End Shift"""
        try:
            # Verificar estado actual
            is_start = Dinamic_button_Shift(username)
            
            if is_start:
                # Iniciar turno
                success = on_start_shift(username, parent_window=top)
                if success:
                    # Actualizar el botón
                    update_shift_button()
                    # Recargar datos (el nuevo evento START/END debe aparecer)
                    load_data()
            else:
                # Finalizar turno
                on_end_shift(username)
                # Actualizar el botón
                update_shift_button()
                # Recargar datos (el nuevo evento START/END debe aparecer)
                load_data()
            
        except Exception as e:
            messagebox.showerror("Error", f"Error al cambiar turno:\n{e}", parent=top)
            print(f"[ERROR] handle_shift_button: {e}")
            traceback.print_exc()
    
    def update_shift_button():
        """Actualiza el texto y color del botón según el estado del turno"""
        try:
            is_start = Dinamic_button_Shift(username)
            
            if is_start:
                # Mostrar "Start Shift"
                if UI is not None:
                    shift_btn.configure(text="🚀 Start Shift", 
                                       fg_color="#00c853", 
                                       hover_color="#00a043")
                else:
                    shift_btn.configure(text="🚀 Start Shift", bg="#00c853")
            else:
                # Mostrar "End of Shift"
                if UI is not None:
                    shift_btn.configure(text="🏁 End of Shift", 
                                       fg_color="#d32f2f", 
                                       hover_color="#b71c1c")
                else:
                    shift_btn.configure(text="🏁 End of Shift", bg="#d32f2f")
        except Exception as e:
            print(f"[ERROR] update_shift_button: {e}")
    
    # ⭐ FUNCIÓN: Manejar botón Cover
    def handle_cover_button(username):
        """Abre la ventana de Cover mode"""
        try:
            # Llamar a cover_mode con los parámetros necesarios
            # Si no tenemos session_id/station/root, usar valores por defecto
            cover_mode(username, session_id, station, root=top)

        except Exception as e:
            messagebox.showerror("Error", f"Error al abrir Cover:\n{e}", parent=top)
            print(f"[ERROR] handle_cover_button: {e}")
            traceback.print_exc()

    if UI is not None:
        # ⭐ Botones Refrescar y Eliminar a la izquierda (movidos desde toolbar)
        UI.CTkButton(header, text="🔄  Refrescar", command=lambda: load_data(),
                    fg_color="#4D6068", hover_color="#27a3e0", 
                    width=120, height=40,
                    font=("Segoe UI", 12, "bold")).pack(side="left", padx=(20, 5), pady=15)
        
        delete_btn_header = UI.CTkButton(header, text="🗑️ Eliminar", command=lambda: None,  # Se asignará después
                    fg_color="#d32f2f", hover_color="#b71c1c", 
                    width=120, height=40,
                    font=("Segoe UI", 12, "bold"))
        delete_btn_header.pack(side="left", padx=5, pady=15)

        # ⭐ Función para obtener próximo cover programado
        def get_next_cover_info():
            """Obtiene el próximo cover programado del usuario desde gestion_breaks_programados"""
            try:
                conn = under_super.get_connection()
                cur = conn.cursor()
                
                # Obtener ID_Usuario del username
                cur.execute("SELECT ID_Usuario FROM user WHERE Nombre_Usuario = %s", (username,))
                user_row = cur.fetchone()
                if not user_row:
                    print(f"[DEBUG] Usuario '{username}' no encontrado en tabla user")
                    cur.close()
                    conn.close()
                    return None
                
                id_usuario = user_row[0]
                print(f"[DEBUG] ID_Usuario obtenido: {id_usuario} para username: {username}")
                
                # Buscar último cover activo donde user_covered = username
                query = """
                    SELECT 
                        gbp.Fecha_hora_cover,
                        u_covering.Nombre_Usuario as covering_name,
                        gbp.User_covered,
                        gbp.User_covering,
                        gbp.is_Active
                    FROM gestion_breaks_programados gbp
                    INNER JOIN user u_covering ON gbp.User_covering = u_covering.ID_Usuario
                    WHERE gbp.User_covered = %s 
                    AND gbp.is_Active = 1
                    ORDER BY gbp.Fecha_hora_cover DESC
                    LIMIT 1
                """
                
                print(f"[DEBUG] Ejecutando query con id_usuario={id_usuario}")
                cur.execute(query, (id_usuario,))
                result = cur.fetchone()
                
                print(f"[DEBUG] Resultado de query: {result}")
                
                # Debug: Mostrar todos los covers activos sin filtro de usuario
                cur.execute("""
                    SELECT User_covered, User_covering, Fecha_hora_cover, is_Active 
                    FROM gestion_breaks_programados 
                    WHERE is_Active = 1
                """)
                all_active = cur.fetchall()
                print(f"[DEBUG] Todos los covers activos en BD: {all_active}")
                
                cur.close()
                conn.close()
                
                if result:
                    fecha_hora_cover, covering_name, user_covered_id, user_covering_id, is_active = result
                    print(f"[DEBUG] Cover encontrado: hora={fecha_hora_cover}, covering={covering_name}, user_covered={user_covered_id}, user_covering={user_covering_id}, active={is_active}")
                    # Formatear hora como HH:MM
                    hora_str = fecha_hora_cover.strftime("%H:%M") if fecha_hora_cover else ""
                    return {
                        'hora': hora_str,
                        'covering': covering_name,
                        'covered': username
                    }
                
                print(f"[DEBUG] No se encontró cover para id_usuario={id_usuario}")
                return None
                
            except Exception as e:
                print(f"[ERROR] get_next_cover_info: {e}")
                traceback.print_exc()
                return None
        
        def update_cover_label():
            """Actualiza el texto del label con la información del próximo cover"""
            try:
                cover_info = get_next_cover_info()
                if cover_info:
                    texto = f"☕ Break: {cover_info['hora']} | Cubierto por: {cover_info['covering']}"
                    cover_label.configure(text=texto)
                else:
                    cover_label.configure(text="☕ No hay covers programados")
            except Exception as e:
                print(f"[ERROR] update_cover_label: {e}")
                cover_label.configure(text="☕ Error al cargar cover")
        
        # ⭐ Función para obtener si el usuario debe cubrir a alguien
        def get_covering_assignment():
            """Obtiene si el usuario debe cubrir a alguien desde gestion_breaks_programados"""
            try:
                conn = under_super.get_connection()
                cur = conn.cursor()
                
                # Obtener ID_Usuario del username
                cur.execute("SELECT ID_Usuario FROM user WHERE Nombre_Usuario = %s", (username,))
                user_row = cur.fetchone()
                if not user_row:
                    print(f"[DEBUG] Usuario '{username}' no encontrado en tabla user para covering")
                    cur.close()
                    conn.close()
                    return None
                
                id_usuario = user_row[0]
                print(f"[DEBUG] Buscando asignaciones de cover para ID_Usuario: {id_usuario} (covering)")
                
                # Buscar próximo cover donde user_covering = username (este usuario debe cubrir a alguien)
                # Busca el más reciente activo sin filtro de fecha para mostrar el último programado
                query = """
                    SELECT 
                        gbp.Fecha_hora_cover,
                        u_covered.Nombre_Usuario as covered_name,
                        gbp.User_covered,
                        gbp.User_covering,
                        gbp.is_Active
                    FROM gestion_breaks_programados gbp
                    INNER JOIN user u_covered ON gbp.User_covered = u_covered.ID_Usuario
                    WHERE gbp.User_covering = %s 
                    AND gbp.is_Active = 1
                    ORDER BY gbp.Fecha_hora_cover DESC
                    LIMIT 1
                """
                
                print(f"[DEBUG] Ejecutando query covering con id_usuario={id_usuario}")
                cur.execute(query, (id_usuario,))
                result = cur.fetchone()
                
                print(f"[DEBUG] Resultado de query covering: {result}")
                
                cur.close()
                conn.close()
                
                if result:
                    fecha_hora_cover, covered_name, user_covered_id, user_covering_id, is_active = result
                    print(f"[DEBUG] Cover assignment encontrado: hora={fecha_hora_cover}, cubriendo a={covered_name}")
                    # Formatear hora como HH:MM
                    hora_str = fecha_hora_cover.strftime("%H:%M") if fecha_hora_cover else ""
                    return {
                        'hora': hora_str,
                        'covered': covered_name,
                        'covering': username
                    }
                
                print(f"[DEBUG] No se encontró asignación de cover para id_usuario={id_usuario} como covering")
                return None
                
            except Exception as e:
                print(f"[ERROR] get_covering_assignment: {e}")
                traceback.print_exc()
                return None
        
        def update_covering_label():
            """Actualiza el texto del label con la información de a quién debe cubrir el usuario"""
            try:
                covering_info = get_covering_assignment()
                if covering_info:
                    texto = f"👤 Cubres a: {covering_info['covered']} | Hora: {covering_info['hora']}"
                    covering_label.configure(text=texto)
                    covering_label.pack(side="left", padx=(0, 20), pady=15)  # Mostrar el label
                else:
                    covering_label.pack_forget()  # Ocultar el label si no hay asignación
            except Exception as e:
                print(f"[ERROR] update_covering_label: {e}")
                covering_label.pack_forget()
        
        # ⭐ Frame contenedor para los dos labels (uno arriba del otro)
        cover_labels_frame = UI.CTkFrame(header, fg_color="transparent")
        cover_labels_frame.pack(side="left", padx=20, pady=15)
        
        # ⭐ Label de información de cover recibido (arriba)
        cover_label = UI.CTkLabel(
            cover_labels_frame,
            text="☕ Cargando...",
            text_color="#00bfae",
            font=("Segoe UI", 13, "bold")
        )
        cover_label.pack(anchor="w")
        
        # ⭐ Label de asignación de cover (abajo - solo se muestra si debe cubrir a alguien)
        covering_label = UI.CTkLabel(
            cover_labels_frame,
            text="",
            text_color="#ffa500",
            font=("Segoe UI", 13, "bold")
        )
        # NO hacer pack() aquí - se mostrará solo si hay asignación
        
        # Actualizar labels al iniciar
        update_cover_label()
        update_covering_label()
        
        # ⭐ Botón Start/End Shift a la derecha
        shift_btn = UI.CTkButton(
            header, 
            text="🚀 Start Shift",  # Texto por defecto, se actualizará
            command=handle_shift_button,
            width=160, 
            height=40,
            font=("Segoe UI", 14, "bold"),
            fg_color="#00c853",
            hover_color="#00a043"
        )
        shift_btn.pack(side="right", padx=(5, 20), pady=15)
        
        # ⭐ Botón Ver Covers a la derecha (al lado de Start/End Shift)
        def switch_to_covers():
            """Cambia al modo Covers actualizando headers y datos"""
            nonlocal columns, custom_widths
            current_mode.set('covers')
            columns = columns_covers
            custom_widths = custom_widths_covers
            sheet.headers(columns_covers)
            toggle_btn.configure(text="📅 Daily")
            
            # ⭐ DESHABILITAR EDICIÓN en sheet (modo solo lectura)
            try:
                sheet.disable_bindings("edit_cell")
            except Exception as e:
                print(f"[DEBUG] No se pudo deshabilitar edit_cell: {e}")
            
            # Ocultar formulario y botones de envío
            entry_frame.pack_forget()
            if enviar_btn:
                enviar_btn.pack_forget()
            if accion_btn:
                accion_btn.pack_forget()
            
            # ⭐ Mostrar frame de posición en cola
            cover_queue_frame.pack(fill="x", padx=10, pady=(10, 5), before=sheet_frame)
            
            load_data()
        
        UI.CTkButton(header, text="📋 Ver Covers", 
                    command=switch_to_covers,
                    fg_color="#4D6068", hover_color="#7b1fa2", 
                    width=130, height=40,
                    font=("Segoe UI", 12, "bold")).pack(side="right", padx=5, pady=15)
        
        # ⭐ Botón Registrar Cover a la derecha (al lado de Ver Covers)
        UI.CTkButton(header, text="👥 Registrar Cover", command=lambda: handle_cover_button(username),
                    fg_color="#4D6068", hover_color="#f57c00", 
                    width=150, height=40,
                    font=("Segoe UI", 12, "bold")).pack(side="right", padx=5, pady=15)
        
                # ⭐ Botón Solicitar Cover a la derecha (al lado de Ver Covers)
        from datetime import datetime
        UI.CTkButton(header, text="❓ Solicitar Cover", 
                    command=lambda: under_super.request_covers(
                        username, 
                        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "Necesito un cover", 
                        1  # aprvoved=1 porque es una solicitud aprobada, pero con posibilidad de denegar
                    ),
                    fg_color="#4D6068", hover_color="#f57c00", 
                    width=150, height=40,
                    font=("Segoe UI", 12, "bold")).pack(side="right", padx=5, pady=15)
        
    else:
        # Fallback Tkinter
        # ⭐ Botones Refrescar y Eliminar a la izquierda (movidos desde toolbar)
        tk.Button(header, text="� Refrescar", command=lambda: load_data(), 
                 bg="#666666", fg="white",
                 font=("Segoe UI", 12, "bold"), relief="flat",
                 width=12).pack(side="left", padx=(20, 5), pady=15)
        
        delete_btn_header = tk.Button(header, text="🗑️ Eliminar", command=lambda: None,  # Se asignará después
                 bg="#d32f2f", fg="white",
                 font=("Segoe UI", 12, "bold"), relief="flat",
                 width=12)
        delete_btn_header.pack(side="left", padx=5, pady=15)
        
        # ⭐ Botón Start/End Shift a la derecha (Tkinter)
        shift_btn = tk.Button(
            header,
            text="🚀 Start Shift",
            command=handle_shift_button,
            bg="#00c853",
            fg="white",
            font=("Segoe UI", 12, "bold"),
            relief="flat",
            width=15
        )
        shift_btn.pack(side="right", padx=(5, 20), pady=15)
        
        # ⭐ Botón Ver Covers a la derecha (al lado de Start/End Shift)
        def switch_to_covers_tk():
            """Cambia al modo Covers actualizando headers y datos (Tkinter fallback)"""
            nonlocal columns, custom_widths
            current_mode.set('covers')
            columns = columns_covers
            custom_widths = custom_widths_covers
            sheet.headers(columns_covers)
            toggle_btn.configure(text="📅 Daily", bg="#4D6068")
            
            # ⭐ DESHABILITAR EDICIÓN en sheet (modo solo lectura)
            try:
                sheet.disable_bindings("edit_cell")
            except Exception as e:
                print(f"[DEBUG] No se pudo deshabilitar edit_cell: {e}")
            
            # Ocultar formulario y botones de envío
            entry_frame.pack_forget()
            if enviar_btn:
                enviar_btn.pack_forget()
            if accion_btn:
                accion_btn.pack_forget()
            
            # ⭐ Mostrar frame de posición en cola
            cover_queue_frame.pack(fill="x", padx=10, pady=(10, 5), before=sheet_frame)
            
            load_data()
        
        tk.Button(header, text="📋 Ver Covers",
                 command=switch_to_covers_tk,
                 bg="#9c27b0", fg="white",
                 font=("Segoe UI", 12, "bold"), relief="flat",
                 width=13).pack(side="right", padx=5, pady=15)
        
        # ⭐ Botón Registrar Cover a la derecha (al lado de Ver Covers)
        tk.Button(header, text="⚙️ Registrar Cover", command=handle_cover_button,
                 bg="#ff9800", fg="white",
                 font=("Segoe UI", 12, "bold"), relief="flat",
                 width=16).pack(side="right", padx=5, pady=15)
    
    # Actualizar botón al iniciar
    update_shift_button()

    # Separador
    try:
        ttk.Separator(top, orient="horizontal").pack(fill="x")
    except Exception:
        pass

    # ⭐ Frame para Label de posición en cola de covers
    if UI is not None:
        cover_queue_frame = UI.CTkFrame(top, fg_color="#1e3a4c", corner_radius=8, height=50)
    else:
        cover_queue_frame = tk.Frame(top, bg="#1e3a4c", height=50)
    cover_queue_frame.pack(fill="x", padx=10, pady=(10, 5))
    cover_queue_frame.pack_propagate(False)

    # Label de posición en cola (se mostrará solo en modo covers)
    if UI is not None:
        cover_queue_label = UI.CTkLabel(
            cover_queue_frame,
            text="Calculando posición en cola...",
            text_color="#00bfae",
            font=("Segoe UI", 13, "bold")
        )
    else:
        cover_queue_label = tk.Label(
            cover_queue_frame,
            text="Calculando posición en cola...",
            bg="#1e3a4c",
            fg="#00bfae",
            font=("Segoe UI", 13, "bold")
        )
    cover_queue_label.pack(pady=10)
    
    # Ocultar el frame inicialmente (solo se muestra en modo covers)
    cover_queue_frame.pack_forget()

    # Frame para tksheet
    if UI is not None:
        sheet_frame = UI.CTkFrame(top, fg_color="#2c2f33")
    else:
        sheet_frame = tk.Frame(top, bg="#2c2f33")
    sheet_frame.pack(fill="both", expand=True, padx=10, pady=10)

    # Crear tksheet
    sheet = SheetClass(
        sheet_frame,
        headers=columns,
        theme="dark blue",
        height=500,
        width=1000,  # Reducido al eliminar columna "Out at"
        show_selected_cells_border=True,
        show_row_index=True,
        show_top_left=False,
        empty_horizontal=0,
        empty_vertical=0
    )
    sheet.enable_bindings([
        "single_select",
        "drag_select",
        "column_select",
        "row_select",
        "column_width_resize",
        "double_click_column_resize",
        "row_height_resize",
        "arrowkeys",
        "right_click_popup_menu",
        "rc_select",
        "copy",
        "cut",
        "paste",
        "delete",
        "undo",
        "edit_cell"  # CRÍTICO: Permite editar celdas con doble-click
    ])
    sheet.pack(fill="both", expand=True)
    sheet.change_theme("dark blue")

    # ⭐ FORMULARIO DE ENTRADA - Simula una fila editable del sheet
    # Frame contenedor con estilo similar al sheet
    if UI is not None:
        entry_frame = UI.CTkFrame(sheet_frame, fg_color="#23272a", corner_radius=0, height=90)
    else:
        entry_frame = tk.Frame(sheet_frame, bg="#23272a", height=90)
    entry_frame.pack(fill="x", side="bottom", padx=0, pady=0)
    entry_frame.pack_propagate(False)  # Mantener altura fija
    
    # Variables para los campos
    fecha_var = tk.StringVar()
    sitio_var = tk.StringVar()
    actividad_var = tk.StringVar()
    cantidad_var = tk.StringVar(value="0")
    camera_var = tk.StringVar()
    descripcion_var = tk.StringVar()
    
    # Obtener listas de valores
    sites_list = under_super.get_sites()
    activities_list = under_super.get_activities()
    
    # ⭐ Configurar estilo oscuro para combobox
    try:
        from tkinter import ttk
        style = ttk.Style()
        style.theme_use('default')
        
        # Estilo para combobox con fondo oscuro
        style.configure('Dark.TCombobox',
                       fieldbackground='#2b2b2b',
                       background='#2b2b2b',
                       foreground='#ffffff',
                       arrowcolor='#ffffff',
                       bordercolor='#4a90e2',
                       lightcolor='#2b2b2b',
                       darkcolor='#2b2b2b',
                       selectbackground='#4a90e2',
                       selectforeground='#ffffff')
        
        style.map('Dark.TCombobox',
                 fieldbackground=[('readonly', '#2b2b2b'), ('disabled', '#1a1a1a')],
                 selectbackground=[('readonly', '#4a90e2')],
                 selectforeground=[('readonly', '#ffffff')],
                 foreground=[('readonly', '#ffffff'), ('disabled', '#666666')])
    except Exception as e:
        print(f"[DEBUG] Could not configure combobox style: {e}")
    
    # ⭐ Espaciador reducido para mover entries a la izquierda
    spacer = tk.Frame(entry_frame, bg="#23272a", width=25)  # Reducido de 45px a 25px
    spacer.pack(side="left", padx=0, pady=0)
    spacer.pack_propagate(False)

    # Campo   (150px) - Exacto al ancho de columna
    fecha_frame = tk.Frame(entry_frame, bg="#23272a", width=150, height=57)
    fecha_frame.pack(side="left", padx=0, pady=5)
    fecha_frame.pack_propagate(False)
    
    # Label para   (centrado)
    tk.Label(fecha_frame, text="Fecha/Hora", bg="#23272a", fg="#a3c9f9",
            font=("Segoe UI", 9, "bold")).pack(anchor="center", padx=2, pady=(0, 2))
    
    if UI is not None:
        fecha_entry = UI.CTkEntry(fecha_frame, textvariable=fecha_var, 
                                  font=("Segoe UI", 11), height=30,
                                  fg_color="#242629", text_color="#ffffff",
                                  border_width=2, border_color="#4a90e2",
                                  corner_radius=5)
        fecha_entry.pack(fill="x", expand=False, padx=1, pady=0)
        # Botón para abrir DateTimePicker (pequeño)
        fecha_btn = UI.CTkButton(fecha_frame, text="📅", width=37, height=27,
                                fg_color="#383f47", hover_color="#3a7bc2",
                                corner_radius=5,
                                command=lambda: None)  # Definiremos después
        fecha_btn.place(relx=1.0, rely=1.0, anchor="se", x=-2, y=-4)
    else:
        fecha_entry = tk.Entry(fecha_frame, textvariable=fecha_var, 
                              font=("Segoe UI", 11), bg="#2b4a6f", fg="#686666")
        fecha_entry.pack(fill="x", expand=False, padx=1, pady=0)

    # Campo Sitio (270px) - Exacto al ancho de columna con Entry + Autocompletado
    sitio_frame = tk.Frame(entry_frame, bg="#23272a", width=270, height=60)
    sitio_frame.pack(side="left", padx=0, pady=5)
    sitio_frame.pack_propagate(False)
    
    # Label para Sitio (centrado)
    tk.Label(sitio_frame, text="Sitio", bg="#23272a", fg="#a3c9f9",
            font=("Segoe UI", 9, "bold")).pack(anchor="center", padx=2, pady=(0, 2))
    
    # ⭐ FilteredCombobox con borde azul prominente
    sitio_combo = under_super.FilteredCombobox(
        sitio_frame, textvariable=sitio_var, values=sites_list,
        font=("Segoe UI", 11), width=32,
        background='#2b2b2b', foreground='#ffffff',
        fieldbackground='#2b2b2b',
        bordercolor='#5ab4ff', arrowcolor='#ffffff',
        borderwidth=3
    )
    sitio_combo.pack(fill="x", expand=False, padx=2, pady=0)
    
    # Campo Actividad (160px) - Exacto al ancho de columna con Entry + Autocompletado
    actividad_frame = tk.Frame(entry_frame, bg="#23272a", width=170, height=60)
    actividad_frame.pack(side="left", padx=0, pady=5)
    actividad_frame.pack_propagate(False)
    
    # Label para Actividad (centrado)
    tk.Label(actividad_frame, text="Actividad", bg="#23272a", fg="#a3c9f9",
            font=("Segoe UI", 9, "bold")).pack(anchor="center", padx=2, pady=(0, 2))
    
    # ⭐ FilteredCombobox con borde azul prominente
    actividad_combo = under_super.FilteredCombobox(
        actividad_frame, textvariable=actividad_var, values=activities_list,
        font=("Segoe UI", 11), width=18,
        background='#2b2b2b', foreground='#ffffff',
        fieldbackground='#2b2b2b',
        bordercolor='#5ab4ff', arrowcolor='#ffffff',
        borderwidth=3
    )
    actividad_combo.pack(fill="x", expand=False, padx=2, pady=0)
    
    # Campo Cantidad (80px) - Exacto al ancho de columna
    cantidad_frame = tk.Frame(entry_frame, bg="#23272a", width=80, height=60)
    cantidad_frame.pack(side="left", padx=0, pady=5)
    cantidad_frame.pack_propagate(False)
    
    # Label para Cantidad (centrado)
    tk.Label(cantidad_frame, text="Cantidad", bg="#23272a", fg="#a3c9f9",
            font=("Segoe UI", 9, "bold")).pack(anchor="center", padx=2, pady=(0, 2))
    
    if UI is not None:
        cantidad_entry = UI.CTkEntry(cantidad_frame, textvariable=cantidad_var,
                                     font=("Segoe UI", 11), height=30,
                                     fg_color="#23272a", text_color="#ffffff",
                                     border_width=2, border_color="#4a90e2",
                                     corner_radius=5)
    else:
        cantidad_entry = tk.Entry(cantidad_frame, textvariable=cantidad_var,
                                 font=("Segoe UI", 11), bg="#23272a", fg="#ffffff")
    cantidad_entry.pack(fill="x", expand=False, padx=1, pady=0)
    
    # Campo Camera (90px) - Exacto al ancho de columna
    camera_frame = tk.Frame(entry_frame, bg="#23272a", width=90, height=60)
    camera_frame.pack(side="left", padx=0, pady=5)
    camera_frame.pack_propagate(False)
    
    # Label para Camera (centrado)
    tk.Label(camera_frame, text="Camera", bg="#23272a", fg="#a3c9f9",
            font=("Segoe UI", 9, "bold")).pack(anchor="center", padx=2, pady=(0, 2))
    
    if UI is not None:
        camera_entry = UI.CTkEntry(camera_frame, textvariable=camera_var,
                                   font=("Segoe UI", 11), height=30,
                                   fg_color="#23272a", text_color="#ffffff",
                                   border_width=2, border_color="#4a90e2",
                                   corner_radius=5)
    else:
        camera_entry = tk.Entry(camera_frame, textvariable=camera_var,
                               font=("Segoe UI", 11), bg="#23272a", fg="#ffffff")
    camera_entry.pack(fill="x", expand=False, padx=1, pady=0)
    
    # Campo Descripción (320px) - Ampliado al eliminar "Out at"
    descripcion_frame = tk.Frame(entry_frame, bg="#23272a", width=320, height=60)
    descripcion_frame.pack(side="left", padx=0, pady=5)
    descripcion_frame.pack_propagate(False)
    
    # Label para Descripción (centrado)
    tk.Label(descripcion_frame, text="Descripción", bg="#23272a", fg="#a3c9f9",
            font=("Segoe UI", 9, "bold")).pack(anchor="center", padx=2, pady=(0, 2))
    
    if UI is not None:
        descripcion_entry = UI.CTkEntry(descripcion_frame, textvariable=descripcion_var,
                                        font=("Segoe UI", 11), height=30,
                                        fg_color="#23272a", text_color="#ffffff",
                                        border_width=2, border_color="#4a90e2",
                                        corner_radius=5,
                                        placeholder_text="Escribe timestamp en formato HH:MM o HH:MM:SS")
        descripcion_entry.pack(fill="x", expand=False, padx=1, pady=0)
    else:
        descripcion_entry = tk.Entry(descripcion_frame, textvariable=descripcion_var,
                                     font=("Segoe UI", 11), bg="#2b4a6f", fg="#ffffff")
        descripcion_entry.pack(fill="x", expand=False, padx=1, pady=0)
    
    # Botón Agregar (al final, después de todas las columnas)
    if UI is not None:
        add_btn = UI.CTkButton(entry_frame, text="➕", width=35, height=35,
                              font=("Segoe UI", 15, "bold"),
                              fg_color="#00c853", hover_color="#00a043",
                              corner_radius=5,
                              command=lambda: None)  # Definiremos después
        add_btn.pack(side="left", padx=5, pady=5)
        add_btn.place(anchor="se", x=-2, y=-4)
    else:
        add_btn = tk.Button(entry_frame, text="➕", bg="#00c853", fg="white",
                           font=("Segoe UI", 15, "bold"), width=3, height=2,
                           command=lambda: None)
    add_btn.pack(side="left", padx=5, pady=5)
    
    # ⭐ FUNCIÓN: Agregar nuevo evento desde el formulario
    def add_event_from_form():
        """Agrega un nuevo evento al sheet desde el formulario de entrada Y LO GUARDA EN LA BD"""
        try:
            # Validar campos obligatorios
            if not sitio_var.get().strip():
                messagebox.showwarning("Campo requerido", "Debes seleccionar un Sitio.", parent=top)
                sitio_combo.focus_set()
                return
            
            if not actividad_var.get().strip():
                messagebox.showwarning("Campo requerido", "Debes seleccionar una Actividad.", parent=top)
                actividad_combo.focus_set()
                return
            
            # Obtener valores
            fecha_str = fecha_var.get().strip()
            if not fecha_str:
                # Usar fecha/hora actual si está vacío
                fecha_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                fecha_var.set(fecha_str)
            
            sitio_str = sitio_var.get().strip()
            actividad_str = actividad_var.get().strip()
            cantidad_str = cantidad_var.get().strip() or "0"
            camera_str = camera_var.get().strip()
            descripcion_str = descripcion_var.get().strip()
            
            # ⭐ GUARDAR DIRECTAMENTE EN LA BASE DE DATOS
            try:
                conn = under_super.get_connection()
                if not conn:
                    messagebox.showerror("Error", "No se pudo conectar a la base de datos.", parent=top)
                    return
                
                cur = conn.cursor()
                
                # Obtener ID_Usuario
                cur.execute("SELECT ID_Usuario FROM user WHERE Nombre_Usuario=%s", (username,))
                user_row = cur.fetchone()
                if not user_row:
                    messagebox.showerror("Error", "Usuario no encontrado.", parent=top)
                    cur.close()
                    conn.close()
                    return
                
                id_usuario = user_row[0]
                
                # Parsear fecha/hora
                try:
                    fecha_dt = datetime.strptime(fecha_str, "%Y-%m-%d %H:%M:%S")
                except:
                    messagebox.showerror("Error", "Formato de fecha inválido.\nUsa: YYYY-MM-DD HH:MM:SS", parent=top)
                    cur.close()
                    conn.close()
                    return
                
                # Extraer ID_Sitio del nombre (formato "Nombre (ID)" o "Nombre ID")
                sitio_id = None
                if sitio_str:
                    try:
                        # ⭐ Método 1: Buscar ID entre paréntesis "Nombre (123)"
                        import re
                        match = re.search(r'\((\d+)\)', sitio_str)
                        if match:
                            sitio_id = int(match.group(1))
                        else:
                            # ⭐ Método 2: Formato antiguo "Nombre 123" (fallback)
                            parts = sitio_str.split()
                            if parts:
                                sitio_id = int(parts[-1])
                    except:
                        messagebox.showerror("Error", "Formato de sitio inválido.", parent=top)
                        cur.close()
                        conn.close()
                        return
                
                # Convertir cantidad
                try:
                    cantidad_float = float(cantidad_str) if cantidad_str else 0.0
                except:
                    cantidad_float = 0.0
                
                # ⭐ INSERTAR EN LA BASE DE DATOS
                cur.execute("""
                    INSERT INTO Eventos 
                    (FechaHora, ID_Sitio, Nombre_Actividad, Cantidad, Camera, Descripcion, ID_Usuario)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (fecha_dt, sitio_id, actividad_str, cantidad_float, camera_str, descripcion_str, id_usuario))
                
                conn.commit()
                nuevo_id = cur.lastrowid
                
                cur.close()
                conn.close()
                
                print(f"[DEBUG] Evento guardado en BD con ID: {nuevo_id}")
                
                # Agregar al sheet con el ID real
                new_row = [fecha_str, sitio_str, actividad_str, cantidad_str, camera_str, 
                          descripcion_var.get().strip()]  # Sin columna "Out at"
                current_data = sheet.get_sheet_data()
                
                # Si solo hay mensaje "No hay eventos", limpiar primero
                if len(current_data) == 1 and "No hay" in str(current_data[0][0]):
                    current_data = []
                    row_data_cache.clear()
                    row_ids.clear()
                
                current_data.append(new_row)
                sheet.set_sheet_data(current_data)
                apply_sheet_widths()
                
                # Agregar a cache con status 'saved' (ya está en BD)
                row_data_cache.append({
                    'id': nuevo_id,
                    'fecha_hora': fecha_dt,
                    'sitio_id': sitio_id,
                    'sitio_nombre': sitio_str,
                    'actividad': actividad_str,
                    'cantidad': cantidad_float,
                    'camera': camera_str,
                    'descripcion': descripcion_str,
                    'status': 'saved'  # ⭐ Ya guardado
                })
                row_ids.append(nuevo_id)
                
                # Resaltar fila como guardada (sin highlight especial)
                new_idx = len(current_data) - 1
                sheet.see(row=new_idx, column=0, keep_yscroll=False, keep_xscroll=True)
                
                print(f"[DEBUG] Evento agregado y guardado: fila {new_idx}, ID: {nuevo_id}")
                
                # Limpiar formulario
                fecha_var.set("")
                sitio_var.set("")
                actividad_var.set("")
                cantidad_var.set("0")
                camera_var.set("")
                descripcion_var.set("")
                
                # Focus en Sitio para siguiente entrada
                sitio_combo.focus_set()
                
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo guardar en la BD:\n{e}", parent=top)
                import traceback
                traceback.print_exc()
                
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo agregar el evento:\n{e}", parent=top)
            import traceback
            traceback.print_exc()
            
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo agregar el evento:\n{e}", parent=top)
            import traceback
            traceback.print_exc()
    
    # Conectar el botón
    add_btn.configure(command=add_event_from_form)
    
    # ⭐ FUNCIÓN: DateTimePicker para el formulario
    def open_form_datetime_picker():
        """Abre el selector de fecha/hora para el formulario"""
        show_datetime_picker_form()
    
    fecha_btn.configure(command=open_form_datetime_picker)
    
    def show_datetime_picker_for_edit(row_idx):
        """Selector moderno de fecha/hora para editar registros existentes"""
        try:
            # Verificar que sea una fila válida
            if row_idx >= len(row_data_cache):
                return
            
            # Obtener valor actual
            current_value = sheet.get_cell_data(row_idx, 0)
            if current_value and current_value.strip():
                try:
                    current_dt = datetime.strptime(current_value, "%Y-%m-%d %H:%M:%S")
                except:
                    current_dt = datetime.now()
            else:
                current_dt = datetime.now()
            
            # Crear ventana con CustomTkinter
            if UI is not None:
                picker_win = UI.CTkToplevel(top)
                picker_win.title("Editar Fecha y Hora")
                picker_win.geometry("500x450")
                picker_win.resizable(False, False)
                picker_win.transient(top)
                picker_win.grab_set()
                
                # Header con icono
                header = UI.CTkFrame(picker_win, fg_color="#1a1a1a", corner_radius=0, height=60)
                header.pack(fill="x", padx=0, pady=0)
                header.pack_propagate(False)
                
                UI.CTkLabel(header, text="📅 Editar Fecha y Hora", 
                           font=("Segoe UI", 20, "bold"),
                           text_color="#4a90e2").pack(pady=15)
                
                # Contenido principal
                content = UI.CTkFrame(picker_win, fg_color="transparent")
                content.pack(fill="both", expand=True, padx=20, pady=20)
                
                # Sección de Fecha
                date_section = UI.CTkFrame(content, fg_color="#2b2b2b", corner_radius=10)
                date_section.pack(fill="x", pady=(0, 15))
                
                UI.CTkLabel(date_section, text="📅 Fecha:", 
                           font=("Segoe UI", 14, "bold"),
                           text_color="#e0e0e0").pack(anchor="w", padx=15, pady=(15, 10))
                
                # Frame para calendario (tkcalendar)
                cal_wrapper = tk.Frame(date_section, bg="#2b2b2b")
                cal_wrapper.pack(padx=15, pady=(0, 15))
                
                cal = tkcalendar.DateEntry(cal_wrapper, width=30, background='#4a90e2',
                                           foreground='white', borderwidth=2,
                                           year=current_dt.year, month=current_dt.month, day=current_dt.day,
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
                hour_var = tk.IntVar(value=current_dt.hour)
                minute_var = tk.IntVar(value=current_dt.minute)
                second_var = tk.IntVar(value=current_dt.second)
                
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
                    now = datetime.now()
                    cal.set_date(now.date())
                    hour_var.set(now.hour)
                    minute_var.set(now.minute)
                    second_var.set(now.second)
                
                UI.CTkButton(time_section, text="⏰ Establecer Hora Actual", command=set_now,
                            fg_color="#4a90e2", hover_color="#3a7bc2",
                            font=("Segoe UI", 11),
                            width=200, height=35).pack(pady=(5, 15))
                
                # Botones Aceptar/Cancelar
                btn_frame = UI.CTkFrame(content, fg_color="transparent")
                btn_frame.pack(pady=10)
                
                def accept():
                    try:
                        selected_date = cal.get_date()
                        selected_time = datetime.strptime(
                            f"{selected_date} {hour_var.get():02d}:{minute_var.get():02d}:{second_var.get():02d}",
                            "%Y-%m-%d %H:%M:%S"
                        )
                        
                        # Actualizar celda
                        formatted = selected_time.strftime("%Y-%m-%d %H:%M:%S")
                        sheet.set_cell_data(row_idx, 0, formatted)
                        
                        # Agregar a pending_changes para auto-guardado
                        if row_idx not in pending_changes:
                            pending_changes.append(row_idx)
                        
                        row_data_cache[row_idx]['fecha_hora'] = selected_time
                        
                        # Guardar automáticamente
                        top.after(500, auto_save_pending)
                        
                        picker_win.destroy()
                    except Exception as e:
                        messagebox.showerror("Error", f"Error al establecer fecha/hora:\n{e}", parent=picker_win)
                
                UI.CTkButton(btn_frame, text="✅ Aceptar", command=accept,
                            fg_color="#00c853", hover_color="#00a043",
                            font=("Segoe UI", 12, "bold"),
                            width=120, height=40).pack(side="left", padx=10)
                
                UI.CTkButton(btn_frame, text="❌ Cancelar", command=picker_win.destroy,
                            fg_color="#666666", hover_color="#555555",
                            font=("Segoe UI", 12),
                            width=120, height=40).pack(side="left", padx=10)
            else:
                # Fallback sin CustomTkinter
                picker_win = tk.Toplevel(top)
                picker_win.title("Editar Fecha y Hora")
                picker_win.geometry("400x400")
                picker_win.transient(top)
                picker_win.grab_set()
                content = tk.Frame(picker_win, bg="#2b2b2b")
                content.pack(fill="both", expand=True, padx=20, pady=20)
                
                tk.Label(content, text="Fecha:", bg="#2b2b2b", fg="#ffffff",
                        font=("Segoe UI", 12, "bold")).pack(anchor="w", pady=(10,5))
                
                cal = tkcalendar.DateEntry(content, width=25, background='#4a90e2',
                                          foreground='white', borderwidth=2,
                                          year=current_dt.year, month=current_dt.month, day=current_dt.day)
                cal.pack(pady=5, fill="x")
                
                tk.Label(content, text="Hora:", bg="#2b2b2b", fg="#ffffff",
                        font=("Segoe UI", 12, "bold")).pack(anchor="w", pady=(20,5))
                
                time_frame = tk.Frame(content, bg="#2b2b2b")
                time_frame.pack(fill="x", pady=5)
                
                hour_var = tk.IntVar(value=current_dt.hour)
                minute_var = tk.IntVar(value=current_dt.minute)
                second_var = tk.IntVar(value=current_dt.second)
                
                hour_spin = tk.Spinbox(time_frame, from_=0, to=23, textvariable=hour_var, width=8)
                hour_spin.pack(side="left", padx=5)
                minute_spin = tk.Spinbox(time_frame, from_=0, to=59, textvariable=minute_var, width=8)
                minute_spin.pack(side="left", padx=5)
                second_spin = tk.Spinbox(time_frame, from_=0, to=59, textvariable=second_var, width=8)
                second_spin.pack(side="left", padx=5)
                
                def accept():
                    selected_date = cal.get_date()
                    selected_time = datetime.strptime(
                        f"{selected_date} {hour_var.get():02d}:{minute_var.get():02d}:{second_var.get():02d}",
                        "%Y-%m-%d %H:%M:%S"
                    )
                    formatted = selected_time.strftime("%Y-%m-%d %H:%M:%S")
                    sheet.set_cell_data(row_idx, 0, formatted)
                    
                    if row_idx not in pending_changes:
                        pending_changes.append(row_idx)
                    row_data_cache[row_idx]['fecha_hora'] = selected_time
                    
                    # Guardar automáticamente
                    top.after(500, auto_save_pending)
                    
                    picker_win.destroy()
                
                btn_frame = tk.Frame(content, bg="#2b2b2b")
                btn_frame.pack(side="bottom", pady=20)
                tk.Button(btn_frame, text="Aceptar", command=accept, bg="#00c853", fg="white", width=10).pack(side="left", padx=5)
                tk.Button(btn_frame, text="Cancelar", command=picker_win.destroy, bg="#666666", fg="white", width=10).pack(side="left", padx=5)
            
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo abrir selector:\n{e}", parent=top)
            import traceback
            traceback.print_exc()
    
    def show_datetime_picker_form():
        """Selector moderno de fecha/hora para el formulario de entrada"""
        try:
            # Fecha actual como defecto
            now = datetime.now()
            
            # Crear ventana con CustomTkinter
            if UI is not None:
                picker_win = UI.CTkToplevel(top)
                picker_win.title("Seleccionar Fecha y Hora")
                picker_win.geometry("500x450")
                picker_win.resizable(False, False)
                picker_win.transient(top)
                picker_win.grab_set()
                
                # Header con icono
                header = UI.CTkFrame(picker_win, fg_color="#1a1a1a", corner_radius=0, height=60)
                header.pack(fill="x", padx=0, pady=0)
                header.pack_propagate(False)
                
                UI.CTkLabel(header, text="📅 Seleccionar Fecha y Hora", 
                           font=("Segoe UI", 20, "bold"),
                           text_color="#4a90e2").pack(pady=15)
                
                # Contenido principal
                content = UI.CTkFrame(picker_win, fg_color="transparent")
                content.pack(fill="both", expand=True, padx=20, pady=20)
                
                # Sección de Fecha
                date_section = UI.CTkFrame(content, fg_color="#2b2b2b", corner_radius=10)
                date_section.pack(fill="x", pady=(0, 15))
                
                UI.CTkLabel(date_section, text="📅 Fecha:", 
                           font=("Segoe UI", 14, "bold"),
                           text_color="#e0e0e0").pack(anchor="w", padx=15, pady=(15, 10))
                
                # Frame para calendario (tkcalendar)
                cal_wrapper = tk.Frame(date_section, bg="#2b2b2b")
                cal_wrapper.pack(padx=15, pady=(0, 15))
                
                cal = tkcalendar.DateEntry(cal_wrapper, width=30, background='#4a90e2',
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
                    current = datetime.now()
                    cal.set_date(current.date())
                    hour_var.set(current.hour)
                    minute_var.set(current.minute)
                    second_var.set(current.second)
                
                UI.CTkButton(time_section, text="⏰ Establecer Hora Actual", command=set_now,
                            fg_color="#4a90e2", hover_color="#3a7bc2",
                            font=("Segoe UI", 11),
                            width=200, height=35).pack(pady=(5, 15))
                
                # Botones Aceptar/Cancelar
                btn_frame = UI.CTkFrame(content, fg_color="transparent")
                btn_frame.pack(pady=10)
                
                def accept():
                    try:
                        selected_date = cal.get_date()
                        selected_time = datetime.strptime(
                            f"{selected_date} {hour_var.get():02d}:{minute_var.get():02d}:{second_var.get():02d}",
                            "%Y-%m-%d %H:%M:%S"
                        )
                        
                        # Establecer en el formulario
                        fecha_var.set(selected_time.strftime("%Y-%m-%d %H:%M:%S"))
                        picker_win.destroy()
                    except Exception as e:
                        messagebox.showerror("Error", f"Error al establecer fecha/hora:\n{e}", parent=picker_win)
                
                UI.CTkButton(btn_frame, text="✅ Aceptar", command=accept,
                            fg_color="#00c853", hover_color="#00a043",
                            font=("Segoe UI", 12, "bold"),
                            width=120, height=40).pack(side="left", padx=10)
                
                UI.CTkButton(btn_frame, text="❌ Cancelar", command=picker_win.destroy,
                            fg_color="#666666", hover_color="#555555",
                            font=("Segoe UI", 12),
                            width=120, height=40).pack(side="left", padx=10)
            else:
                # Fallback sin CustomTkinter
                picker_win = tk.Toplevel(top)
                picker_win.title("Seleccionar Fecha y Hora")
                picker_win.geometry("400x400")
                picker_win.transient(top)
                picker_win.grab_set()
                content = tk.Frame(picker_win, bg="#2b2b2b")
                content.pack(fill="both", expand=True, padx=20, pady=20)
                
                tk.Label(content, text="Fecha:", bg="#2b2b2b", fg="#ffffff",
                        font=("Segoe UI", 12, "bold")).pack(anchor="w", pady=(10,5))
                
                cal = tkcalendar.DateEntry(content, width=25, background='#4a90e2',
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
                
                def accept():
                    selected_date = cal.get_date()
                    selected_time = datetime.strptime(
                        f"{selected_date} {hour_var.get():02d}:{minute_var.get():02d}:{second_var.get():02d}",
                        "%Y-%m-%d %H:%M:%S"
                    )
                    fecha_var.set(selected_time.strftime("%Y-%m-%d %H:%M:%S"))
                    picker_win.destroy()
                
                btn_frame = tk.Frame(content, bg="#2b2b2b")
                btn_frame.pack(side="bottom", pady=20)
                tk.Button(btn_frame, text="Aceptar", command=accept, bg="#00c853", fg="white", width=10).pack(side="left", padx=5)
                tk.Button(btn_frame, text="Cancelar", command=picker_win.destroy, bg="#666666", fg="white", width=10).pack(side="left", padx=5)
            
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo abrir selector:\n{e}", parent=top)
            import traceback
            traceback.print_exc()
    
    # ⭐ VINCULAR ENTER EN TODOS LOS CAMPOS DEL FORMULARIO
    def on_form_enter(event):
        """Ejecuta agregar cuando se presiona Enter en el formulario"""
        add_event_from_form()
        return "break"
    
    # Aplicar binding a todos los campos
    fecha_entry.bind("<Return>", on_form_enter)
    fecha_entry.bind("<KP_Enter>", on_form_enter)
    sitio_combo.bind("<Return>", on_form_enter)
    sitio_combo.bind("<KP_Enter>", on_form_enter)
    actividad_combo.bind("<Return>", on_form_enter)
    actividad_combo.bind("<KP_Enter>", on_form_enter)
    cantidad_entry.bind("<Return>", on_form_enter)
    cantidad_entry.bind("<KP_Enter>", on_form_enter)
    camera_entry.bind("<Return>", on_form_enter)
    camera_entry.bind("<KP_Enter>", on_form_enter)
    descripcion_entry.bind("<Return>", on_form_enter)
    descripcion_entry.bind("<KP_Enter>", on_form_enter)
    
    # Focus inicial en Sitio
    sitio_combo.focus_set()

    def apply_sheet_widths():
        """Aplica anchos personalizados a las columnas"""
        for idx, col_name in enumerate(columns):
            if col_name in custom_widths:
                sheet.column_width(idx, custom_widths[col_name])
        sheet.redraw()

    def get_last_shift_start():
        """Obtiene la última hora de inicio de shift del usuario"""
        try:
            conn = under_super.get_connection()
            cur = conn.cursor()
            cur.execute("""
                SELECT e.FechaHora 
                FROM Eventos e
                INNER JOIN user u ON e.ID_Usuario = u.ID_Usuario
                WHERE u.Nombre_Usuario = %s AND e.Nombre_Actividad = %s
                ORDER BY e.FechaHora DESC
                LIMIT 1
            """, (username, "START SHIFT"))
            row = cur.fetchone()
            cur.close()
            conn.close()
            return row[0] if row and row[0] else None
        except Exception as e:
            print(f"[ERROR] get_last_shift_start: {e}")
            return None

    def load_daily():
        """Carga eventos del turno actual desde la base de datos (MODO DAILY)"""
        nonlocal row_data_cache, row_ids, pending_changes
        
        try:
            last_shift_time = get_last_shift_start()
            if last_shift_time is None:
                data = [["No hay shift activo"] + [""] * (len(columns)-1)]
                sheet.set_sheet_data(data)
                apply_sheet_widths()
                row_data_cache.clear()
                row_ids.clear()
                pending_changes.clear()
                return

            conn = under_super.get_connection()
            cur = conn.cursor()
            
            # Obtener eventos del usuario desde el último shift
            cur.execute("""
                SELECT 
                    e.ID_Eventos,
                    e.FechaHora,
                    e.ID_Sitio,
                    e.Nombre_Actividad,
                    e.Cantidad,
                    e.Camera,
                    e.Descripcion
                FROM Eventos e
                INNER JOIN user u ON e.ID_Usuario = u.ID_Usuario
                WHERE u.Nombre_Usuario = %s AND e.FechaHora >= %s
                ORDER BY e.FechaHora ASC
            """, (username, last_shift_time))

            eventos = cur.fetchall()
            
            row_data_cache.clear()
            row_ids.clear()
            display_rows = []

            for evento in eventos:
                (id_evento, fecha_hora, id_sitio, nombre_actividad, cantidad, camera, descripcion) = evento

                # Resolver Nombre_Sitio desde ID_Sitio
                try:
                    cur.execute("SELECT Nombre_Sitio FROM Sitios WHERE ID_Sitio = %s", (id_sitio,))
                    sit_row = cur.fetchone()
                    # ⭐ Formato consistente: "Nombre (ID)" igual que en load_specials
                    nombre_sitio = f"{sit_row[0]} ({id_sitio})" if sit_row else f"ID: {id_sitio}"
                except Exception:
                    nombre_sitio = f"ID: {id_sitio}"

                # Formatear fecha/hora
                fecha_str = fecha_hora.strftime("%Y-%m-%d %H:%M:%S") if fecha_hora else ""

                # Guardar en cache
                row_data_cache.append({
                    'id': id_evento,
                    'fecha_hora': fecha_hora,
                    'sitio_id': id_sitio,
                    'sitio_nombre': nombre_sitio,
                    'actividad': nombre_actividad or "",
                    'cantidad': cantidad or 0,
                    'camera': camera or "",
                    'descripcion': descripcion or "",
                    'status': 'saved'
                })
                row_ids.append(id_evento)

                # Fila para mostrar
                display_rows.append([
                    fecha_str,
                    nombre_sitio,
                    nombre_actividad or "",
                    str(cantidad) if cantidad is not None else "0",
                    camera or "",
                    descripcion or ""
                ])

            cur.close()
            conn.close()

            if not display_rows:
                display_rows = [["No hay eventos en este turno"] + [""] * (len(columns)-1)]
                row_data_cache.clear()
                row_ids.clear()

            sheet.set_sheet_data(display_rows)
            
            # ⭐ LIMPIAR COLORES (solo Specials tiene colores)
            sheet.dehighlight_all()
            
            apply_sheet_widths()
            pending_changes.clear()

            print(f"[DEBUG] Loaded {len(row_ids)} events for {username}")

        except Exception as e:
            messagebox.showerror("Error", f"No se pudo cargar eventos:\n{e}", parent=top)
            traceback.print_exc()

    def load_specials():
            """Carga eventos de grupos especiales (AS, KG, HUD, PE, SCH, WAG, LT, DT) desde el último START SHIFT (MODO SPECIALS)"""
            nonlocal row_data_cache, row_ids, pending_changes
            
            try:
                # Obtener último START SHIFT del supervisor
                last_shift_time = get_last_shift_start()
                if last_shift_time is None:
                    data = [["No hay shift activo"] + [""] * (len(columns)-1)]
                    sheet.set_sheet_data(data)
                    apply_sheet_widths()
                    row_data_cache.clear()
                    row_ids.clear()
                    pending_changes.clear()
                    return

                # Grupos especiales a filtrar (como open_report_window)
                grupos_especiales = ("AS", "KG", "HUD", "PE", "SCH", "WAG", "LT", "DT")
                
                conn = under_super.get_connection()
                cur = conn.cursor()
                
                # Obtener ID_Usuario del supervisor
                cur.execute("SELECT ID_Usuario FROM user WHERE Nombre_Usuario = %s", (username,))
                user_row = cur.fetchone()
                if not user_row:
                    messagebox.showerror("Error", f"Usuario '{username}' no encontrado.", parent=top)
                    cur.close()
                    conn.close()
                    return
                user_id = int(user_row[0])
                
                # Query: EVENTOS de grupos especiales desde START SHIFT hasta AHORA
                query = """
                    SELECT
                        e.ID_Eventos,
                        e.FechaHora,
                        e.ID_Sitio,
                        e.Nombre_Actividad,
                        e.Cantidad,
                        e.Camera,
                        e.Descripcion,
                        u.Nombre_Usuario
                    FROM Eventos AS e
                    INNER JOIN user u ON e.ID_Usuario = u.ID_Usuario
                    WHERE u.Nombre_Usuario = %s
                    AND e.ID_Sitio IN (
                        SELECT st.ID_Sitio
                        FROM Sitios st
                        WHERE st.ID_Grupo IN (%s, %s, %s, %s, %s, %s, %s, %s)
                    )
                    AND e.FechaHora >= %s
                    ORDER BY e.FechaHora ASC
                """
                
                cur.execute(query, (username, *grupos_especiales, last_shift_time))
                rows = cur.fetchall()
                
                # ⭐ Load timezone offset configuration
                tz_adjust = load_tz_config()
                
                # Resolver nombres de sitios y zonas horarias
                time_zone_cache = {}
                processed = []
                
                for r in rows:
                    id_evento = r[0]
                    fecha_hora = r[1]
                    id_sitio = r[2]
                    nombre_actividad = r[3]
                    cantidad = r[4]
                    camera = r[5]
                    descripcion = r[6]
                    usuario = r[7]
                    
                    # ⭐ GUARDAR VALORES ORIGINALES (antes de ajustes de timezone)
                    fecha_hora_original = r[1]  # Fecha original de BD
                    descripcion_original = str(r[6]) if r[6] else ""  # Guardar copia del valor original
                    usuario_original = usuario  # Usuario original de BD
                    
                    # Resolver nombre de sitio y zona horaria
                    nombre_sitio = ""
                    tz = ""
                    if id_sitio is not None and str(id_sitio).strip() != "":
                        if id_sitio in time_zone_cache:
                            nombre_sitio, tz = time_zone_cache[id_sitio]
                        else:
                            try:
                                cur.execute("SELECT Nombre_Sitio, Time_Zone FROM Sitios WHERE ID_Sitio = %s", (id_sitio,))
                                sit = cur.fetchone()
                                nombre_sitio = sit[0] if sit and sit[0] else ""
                                tz = sit[1] if sit and len(sit) > 1 and sit[1] else ""
                            except Exception:
                                nombre_sitio = ""
                                tz = ""
                            time_zone_cache[id_sitio] = (nombre_sitio, tz)
                    
                    # Formato visual para ID_Sitio (mostrar nombre + ID)
                    if id_sitio and nombre_sitio:
                        display_site = f"{nombre_sitio} ({id_sitio})"
                    elif id_sitio:
                        display_site = str(id_sitio)
                    else:
                        display_site = nombre_sitio or ""
                    
                    # ⭐ Formatear fecha/hora CON ajuste de zona horaria
                    try:
                        # Get timezone offset for this site
                        tz_offset_hours = tz_adjust.get((tz or '').upper(), 0)
                        
                        # Apply offset to datetime
                        if isinstance(fecha_hora, str):
                            fh = datetime.strptime(fecha_hora[:19], "%Y-%m-%d %H:%M:%S")
                        else:
                            fh = fecha_hora
                        
                        fh_adjusted = fh + timedelta(hours=tz_offset_hours)
                        fecha_str = fh_adjusted.strftime("%Y-%m-%d %H:%M:%S")
                    except Exception:
                        fecha_str = fecha_hora.strftime("%Y-%m-%d %H:%M:%S") if fecha_hora else ""
                    
                    # ⭐ Ajustar timestamps dentro de la descripción
                    # Soporta formatos: [HH:MM:SS], [H:MM:SS], HH:MM:SS, H:MM:SS, [HH:MM], [H:MM], HH:MM, H:MM
                    if descripcion:
                        try:
                            desc_text = str(descripcion)
                            
                            # Normalizar formato: convertir [Timestamp: XX:XX:XX] a [XX:XX:XX]
                            # Soporta HH:MM:SS y H:MM:SS
                            desc_text = re.sub(r"\[?\s*Timestamp:\s*(\d{1,2}:\d{2}:\d{2})\s*\]?", r"[\1]", desc_text, flags=re.IGNORECASE)
                            # Soporta HH:MM y H:MM
                            desc_text = re.sub(r"\[?\s*Timestamp:\s*(\d{1,2}:\d{2})\s*\]?", r"[\1]", desc_text, flags=re.IGNORECASE)
                            
                            # Función para ajustar un timestamp (soporta H:MM, HH:MM, H:MM:SS, HH:MM:SS)
                            def adjust_timestamp(match):
                                raw_time = match.group(1) if match.lastindex >= 1 else match.group(0)
                                # Guardar si tiene corchetes al inicio
                                has_brackets = match.group(0).startswith('[')
                                
                                try:
                                    # Usar la fecha del evento como base
                                    base_date = fh.date() if 'fh' in locals() and isinstance(fh, datetime) else datetime.now().date()
                                    
                                    # Parsear el tiempo (puede ser H:MM:SS, HH:MM:SS, H:MM o HH:MM)
                                    time_parts = raw_time.split(":")
                                    if len(time_parts) == 3:
                                        # Formato H:MM:SS o HH:MM:SS
                                        hh, mm, ss = [int(x) for x in time_parts]
                                    elif len(time_parts) == 2:
                                        # Formato H:MM o HH:MM (asumir segundos = 00)
                                        hh, mm = [int(x) for x in time_parts]
                                        ss = 0
                                    elif len(time_parts) == 1:
                                        # Formato H (solo hora, asumir minutos y segundos = 00)
                                        hh = int(time_parts[0])
                                        mm = 0
                                        ss = 0
                                    else:
                                        return match.group(0)  # Formato no reconocido
                                    
                                    # Validar rangos
                                    if not (0 <= hh <= 23 and 0 <= mm <= 59 and 0 <= ss <= 59):
                                        return match.group(0)  # Valores fuera de rango
                                    
                                    desc_dt = datetime.combine(base_date, datetime.min.time()) + timedelta(hours=hh, minutes=mm, seconds=ss)
                                    
                                    # Aplicar el mismo offset de zona horaria
                                    desc_dt_adjusted = desc_dt + timedelta(hours=tz_offset_hours)
                                    
                                    # Mantener el formato original (con o sin ceros a la izquierda)
                                    if len(time_parts) == 3:
                                        # Formato con segundos
                                        if len(time_parts[0]) == 1:
                                            # Formato H:MM:SS (sin cero a la izquierda)
                                            desc_time_adjusted_str = f"{desc_dt_adjusted.hour}:{desc_dt_adjusted.minute:02d}:{desc_dt_adjusted.second:02d}"
                                        else:
                                            # Formato HH:MM:SS (con cero a la izquierda)
                                            desc_time_adjusted_str = desc_dt_adjusted.strftime("%H:%M:%S")
                                    elif len(time_parts) == 2:
                                        # Formato sin segundos
                                        if len(time_parts[0]) == 1:
                                            # Formato H:MM (sin cero a la izquierda)
                                            desc_time_adjusted_str = f"{desc_dt_adjusted.hour}:{desc_dt_adjusted.minute:02d}"
                                        else:
                                            # Formato HH:MM (con cero a la izquierda)
                                            desc_time_adjusted_str = desc_dt_adjusted.strftime("%H:%M")
                                    else:
                                        # Formato solo hora
                                        desc_time_adjusted_str = desc_dt_adjusted.strftime("%H:%M")
                                    
                                    # Mantener el formato original (con o sin corchetes)
                                    if has_brackets:
                                        return f"[{desc_time_adjusted_str}]"
                                    else:
                                        return desc_time_adjusted_str
                                except Exception as e:
                                    print(f"[DEBUG] Error ajustando timestamp '{raw_time}': {e}")
                                    return match.group(0)  # Retornar original si hay error
                            
                            # ⭐ ORDEN DE PROCESAMIENTO: Del más específico al más general
                            
                            # 1. Timestamps con corchetes y segundos: [HH:MM:SS] o [H:MM:SS]
                            desc_text_adjusted = re.sub(r"\[(\d{1,2}:\d{2}:\d{2})\]", adjust_timestamp, desc_text)
                            
                            # 2. Timestamps con corchetes sin segundos: [HH:MM] o [H:MM]
                            desc_text_adjusted = re.sub(r"\[(\d{1,2}:\d{2})\]", adjust_timestamp, desc_text_adjusted)
                            
                            # 3. Timestamps SIN corchetes con segundos: HH:MM:SS o H:MM:SS
                            # Lookahead/lookbehind para evitar coincidir con fechas completas o timestamps ya procesados
                            desc_text_adjusted = re.sub(
                                r"(?<!\d)(\d{1,2}:\d{2}:\d{2})(?!\])",  # No debe tener ] después
                                adjust_timestamp,
                                desc_text_adjusted
                            )
                            
                            # 4. Timestamps SIN corchetes sin segundos: HH:MM o H:MM
                            # Evitar coincidir con HH:MM:SS (que ya fueron procesados)
                            desc_text_adjusted = re.sub(
                                r"(?<!\d)(\d{1,2}:\d{2})(?!:\d|\])",  # No debe tener :dígito después ni ]
                                adjust_timestamp,
                                desc_text_adjusted
                            )
                            
                            descripcion = desc_text_adjusted
                            
                        except Exception:
                            # Mantener descripción original si hay error
                            pass
                    
                    # ⭐ VERIFICAR ESTADO EN TABLA SPECIALS (3 estados posibles)
                    mark_display = ""  # Por defecto: vacío (sin enviar)
                    mark_color = None  # None = sin color, "green" = enviado, "amber" = pendiente
                    
                    try:
                        # ⭐ Buscar usando la fecha AJUSTADA (con timezone) porque así se guarda en specials
                        # fecha_str ya tiene el ajuste de timezone aplicado
                        
                        # Debug: Mostrar valores de búsqueda
                        print(f"[DEBUG] Buscando en specials:")
                        print(f"  FechaHora: {fecha_str} (ajustada con timezone)")
                        print(f"  Usuario: {usuario_original}")
                        print(f"  Actividad: {nombre_actividad}")
                        print(f"  ID_Sitio: {id_sitio}")
                        
                        # Buscar si existe en specials (usando LOWER para case-insensitive)
                        cur.execute(
                            """
                            SELECT ID_special, Supervisor, FechaHora, ID_Sitio, Nombre_Actividad, 
                                Cantidad, Camera, Descripcion
                            FROM specials
                            WHERE FechaHora = %s
                            AND LOWER(Usuario) = LOWER(%s)
                            AND Nombre_Actividad = %s
                            AND IFNULL(ID_Sitio, 0) = IFNULL(%s, 0)
                            LIMIT 1
                            """,
                            (fecha_str, usuario_original, nombre_actividad, id_sitio),
                        )
                        special_row = cur.fetchone()
                        
                        if special_row:
                            print(f"[DEBUG] ✅ ENCONTRADO en specials: ID={special_row[0]}, Supervisor={special_row[1]}")
                        else:
                            print(f"[DEBUG] ❌ NO encontrado en specials")
                        
                        if special_row:
                            # Existe en specials - USAR VALORES DE SPECIALS para mostrar
                            special_supervisor = special_row[1]
                            special_fechahora = special_row[2]
                            special_id_sitio = special_row[3]
                            special_actividad = special_row[4]
                            special_cantidad = special_row[5]
                            special_camera = special_row[6]
                            special_desc = special_row[7]
                            
                            # ⭐ IMPORTANTE: Para comparar, usar valores AJUSTADOS de Eventos
                            # (porque accion_supervisores() guarda valores ajustados en specials)
                            
                            # Normalizar valores de Eventos (con ajuste de timezone aplicado)
                            eventos_cantidad = int(cantidad) if cantidad is not None else 0
                            eventos_camera = str(camera).strip() if camera else ""
                            eventos_desc = str(descripcion).strip() if descripcion else ""  # ⭐ Usar descripcion AJUSTADA
                            
                            # Normalizar valores de specials (convertir a tipos comparables)
                            specials_cantidad = int(special_cantidad) if special_cantidad is not None else 0
                            specials_camera = str(special_camera).strip() if special_camera else ""
                            specials_desc = str(special_desc).strip() if special_desc else ""
                            
                            # Debug: Mostrar comparación
                            print(f"[DEBUG] Comparando valores:")
                            print(f"  Eventos (ajustado) -> Cantidad: {eventos_cantidad}, Camera: '{eventos_camera}', Desc: '{eventos_desc[:50]}...'")
                            print(f"  Specials (guardado) -> Cantidad: {specials_cantidad}, Camera: '{specials_camera}', Desc: '{specials_desc[:50]}...'")
                            
                            if (eventos_cantidad != specials_cantidad or 
                                eventos_camera != specials_camera or 
                                eventos_desc != specials_desc):
                                # HAY CAMBIOS: Estado "Pendiente por actualizar"
                                print(f"[DEBUG] ⚠️ CAMBIOS DETECTADOS - Marca: Pendiente")
                                mark_display = "⏳ Pendiente por actualizar"
                                mark_color = "amber"
                                
                                # USAR VALORES DE EVENTOS (ajustados) para mostrar cuando hay cambios pendientes
                                fecha_str_display = fecha_str
                                descripcion_display = descripcion
                            else:
                                # SIN CAMBIOS: Estado "Enviado a @supervisor"
                                print(f"[DEBUG] ✅ SIN CAMBIOS - Marca: Enviado a {special_supervisor}")
                                mark_display = f"✅ Enviado a {special_supervisor}"
                                mark_color = "green"
                                
                                # USAR VALORES DE SPECIALS para mostrar cuando está enviado sin cambios
                                fecha_str_display = special_fechahora if special_fechahora else fecha_str
                                descripcion_display = special_desc if special_desc else descripcion
                        else:
                            # NO EXISTE EN SPECIALS: Estado vacío (sin enviar)
                            mark_display = ""
                            mark_color = None
                            
                            # USAR VALORES DE EVENTOS (ajustados) para mostrar
                            fecha_str_display = fecha_str
                            descripcion_display = descripcion
                            
                    except Exception:
                        mark_display = ""
                        mark_color = None
                        fecha_str_display = fecha_str
                        descripcion_display = descripcion
                    
                    # Fila para mostrar (SIN columnas ID y Usuario)
                    # Columnas: ["Fecha_hora", "ID_Sitio", "Nombre_Actividad", "Cantidad", "Camera", "Descripcion", "Time_Zone", "Marca"]
                    display_row = [
                        fecha_str_display,        # Fecha_hora (de specials si enviado, de eventos si no)
                        display_site,             # ID_Sitio
                        nombre_actividad or "",   # Nombre_Actividad
                        str(cantidad) if cantidad is not None else "0",  # Cantidad
                        camera or "",             # Camera
                        descripcion_display,      # Descripcion (de specials si enviado, de eventos si no)
                        tz or "",                 # Time_Zone
                        mark_display              # Marca (vacío, enviado, o pendiente)
                    ]
                    
                    processed.append({
                        'id': id_evento,
                        'values': display_row,
                        'mark_color': mark_color  # Para aplicar color después
                    })
                
                cur.close()
                conn.close()
                
                # Actualizar cache
                row_data_cache = processed
                row_ids = [item['id'] for item in processed]
                
                # Poblar sheet
                if not processed:
                    data = [["No hay eventos de grupos especiales en este turno"] + [""] * (len(columns)-1)]
                    sheet.set_sheet_data(data)
                else:
                    data = [item['values'] for item in processed]
                    sheet.set_sheet_data(data)
                    
                    # ⭐ APLICAR COLORES según estado de marca
                    sheet.dehighlight_all()  # Limpiar colores anteriores
                    
                    for idx, item in enumerate(processed):
                        mark_color = item.get('mark_color')
                        if mark_color == 'green':
                            # Verde (#00c853) para "Enviado"
                            sheet.highlight_rows([idx], bg="#00c853", fg="#111111")
                        elif mark_color == 'amber':
                            # Ámbar (#f5a623) para "Pendiente por actualizar"
                            sheet.highlight_rows([idx], bg="#f5a623", fg="#111111")
                        # Sin color si mark_color es None (sin enviar)
                
                apply_sheet_widths()
                pending_changes.clear()
                
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo cargar eventos especiales:\n{e}", parent=top)
                traceback.print_exc()
                pending_changes.clear()
                
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo cargar specials:\n{e}", parent=top)
                traceback.print_exc()
    
    def load_covers():
        """Carga covers desde el último START SHIFT filtrados por username (MODO COVERS)
        Incluye covers normales (con programación) y covers de emergencia (sin programación)"""
        nonlocal row_data_cache, row_ids, pending_changes
        
        try:
            # Obtener último START SHIFT del usuario
            last_shift_time = get_last_shift_start()
            if last_shift_time is None:
                sheet.set_sheet_data([["No hay START SHIFT registrado. Inicia un turno primero.", "", "", "", "", ""]])
                row_data_cache.clear()
                row_ids.clear()
                apply_sheet_widths()
                return
            
            conn = under_super.get_connection()
            cur = conn.cursor()
            
            # Query: Covers del usuario desde START SHIFT hasta AHORA, ordenados de más antiguo a más reciente
            # ⭐ LEFT JOIN con covers_programados para incluir covers de emergencia (ID_programacion_covers NULL)
            query = """
                SELECT 
                    cr.ID_Covers,
                    cr.Nombre_usuarios,
                    cr.Cover_in,
                    cr.Cover_out,
                    cr.Covered_by,
                    cr.Motivo,
                    cp.Time_request,
                    cr.ID_programacion_covers
                FROM Covers_realizados cr
                LEFT JOIN covers_programados cp ON cr.ID_programacion_covers = cp.ID_Cover
                WHERE cr.Nombre_Usuarios = %s
                    AND cr.Cover_in >= %s
                ORDER BY cr.Cover_in ASC
            """
            
            cur.execute(query, (username, last_shift_time))
            rows = cur.fetchall()
            
            row_data_cache.clear()
            row_ids.clear()
            display_rows = []
            
            for r in rows:
                id_cover = r[0]
                nombre_usuario = r[1] if r[1] else ""
                cover_in = r[2]
                cover_out = r[3]
                covered_by = r[4] if r[4] else ""
                motivo = r[5] if r[5] else ""
                time_request = r[6]  # Time_request de covers_programados (puede ser NULL en emergencias)
                id_programacion = r[7]  # ID_programacion_covers para detectar emergencias
                
                # ⭐ Detectar cover de emergencia (sin programación)
                is_emergency = (id_programacion is None)
                
                # Formatear fechas
                if is_emergency:
                    time_request_str = "⚠️ EMERGENCIA"  # Marcador visual para covers de emergencia
                else:
                    time_request_str = time_request.strftime("%Y-%m-%d %H:%M:%S") if time_request else ""
                
                cover_in_str = cover_in.strftime("%Y-%m-%d %H:%M:%S") if cover_in else ""
                cover_out_str = cover_out.strftime("%Y-%m-%d %H:%M:%S") if cover_out else ""
                
                # Covers realizados siempre están cerrados (no tienen campo Activo en la tabla)
                activo_str = "Cerrado"
                
                # Construir fila SIN ID_Covers (no se muestra al usuario)
                # Ahora incluye Time_request al inicio (o "EMERGENCIA" si es cover de emergencia)
                display_row = [
                    nombre_usuario,
                    time_request_str,
                    cover_in_str,
                    cover_out_str,
                    motivo,
                    covered_by,
                    activo_str
                ]
                
                display_rows.append(display_row)
                
                # Guardar en cache con indicador de emergencia
                row_data_cache.append({
                    'id_cover': id_cover,
                    'cover_in': cover_in,
                    'cover_out': cover_out,
                    'motivo': motivo,
                    'covered_by': covered_by,
                    'is_emergency': is_emergency,
                    'status': 'saved'
                })
                row_ids.append(id_cover)
            
            cur.close()
            conn.close()
            
            if not display_rows:
                sheet.set_sheet_data([["No hay covers registrados desde el último START SHIFT.", "", "", "", "", ""]])
                row_data_cache.clear()
                row_ids.clear()
            else:
                sheet.set_sheet_data(display_rows)
            
            # Limpiar colores (no se aplica highlight a covers de emergencia)
            sheet.dehighlight_all()
            
            apply_sheet_widths()
            pending_changes.clear()
            
            print(f"[DEBUG] Loaded {len(row_ids)} covers for {username} (includes emergency covers)")
            
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo cargar covers:\n{e}", parent=top)
            traceback.print_exc()
            pending_changes.clear()

    def update_cover_queue_position():
        """Calcula y muestra cuántos turnos faltan para el cover del usuario"""
        try:
            conn = under_super.get_connection()
            cur = conn.cursor()
            
            # Buscar todos los covers programados activos (is_Active = 1) ordenados por Time_request
            cur.execute("""
                SELECT ID_user, Time_request, is_Active 
                FROM covers_programados 
                WHERE is_Active = 1 
                ORDER BY Time_request ASC
            """)
            active_covers = cur.fetchall()
            
            # Buscar si el usuario actual tiene un cover programado activo
            user_position = None
            for idx, row in enumerate(active_covers):
                if row[0] == username:  # ID_user == username
                    user_position = idx + 1  # Posición 1-indexed
                    break
            
            cur.close()
            conn.close()
            
            # Actualizar el label
            if user_position is not None:
                if user_position == 1:
                    text = "⭐ ¡Eres el siguiente! Estás en turno #1 para tu cover"
                else:
                    text = f"📋 Estás a {user_position} turnos para tu cover"
                
                if UI is not None:
                    cover_queue_label.configure(text=text, text_color="#00ff88")
                else:
                    cover_queue_label.configure(text=text, fg="#00ff88")
            else:
                text = "ℹ️ No tienes covers programados activos"
                if UI is not None:
                    cover_queue_label.configure(text=text, text_color="#ffa500")
                else:
                    cover_queue_label.configure(text=text, fg="#ffa500")
            
            print(f"[DEBUG] Cover queue position for {username}: {user_position}")
            
        except Exception as e:
            print(f"[ERROR] update_cover_queue_position: {e}")
            traceback.print_exc()
            text = "❌ Error calculando posición en cola"
            if UI is not None:
                cover_queue_label.configure(text=text, text_color="#ff4444")
            else:
                cover_queue_label.configure(text=text, fg="#ff4444")
        
        # Auto-refresh cada 30 segundos si estamos en modo covers
        if current_mode.get() == 'covers':
            top.after(30000, update_cover_queue_position)

    def load_data():
        """Wrapper que llama a load_daily(), load_specials() o load_covers() según el modo activo"""
        mode = current_mode.get()
        if mode == 'daily':
            load_daily()
        elif mode == 'specials':
            load_specials()
        elif mode == 'covers':
            load_covers()
            # Actualizar posición en cola cuando se cargan covers
            update_cover_queue_position()
    
    def toggle_mode():
        """Alterna entre modo DAILY ↔ SPECIALS (Covers tiene su propio botón)"""
        nonlocal columns, custom_widths
        
        mode = current_mode.get()
        
        if mode == 'daily':
            # Cambiar a SPECIALS
            current_mode.set('specials')
            columns = columns_specials
            custom_widths = custom_widths_specials
            
            # Actualizar headers del sheet
            sheet.headers(columns_specials)
            
            # ⭐ DESHABILITAR EDICIÓN DIRECTA en sheet (modo solo lectura)
            try:
                sheet.disable_bindings("edit_cell")
            except Exception as e:
                print(f"[DEBUG] No se pudo deshabilitar edit_cell: {e}")
            
            # Ocultar formulario de entrada (no se usa en specials)
            entry_frame.pack_forget()
            
            # Ocultar frame de posición en cola (solo para covers)
            cover_queue_frame.pack_forget()
            
            # Mostrar botones de envío
            if enviar_btn:
                enviar_btn.pack(side="left", padx=5, pady=12)
            if accion_btn:
                accion_btn.pack(side="left", padx=5, pady=12)
            
            # Actualizar botón toggle
            if UI is not None:
                toggle_btn.configure(text="📝 Daily", fg_color="#4D6068", hover_color="#CC43CC")
            else:
                toggle_btn.configure(text="📝 Daily", bg="#CC43CC")

            # Cargar datos de specials
            load_specials()
            
        elif mode == 'specials':
            # Cambiar a DAILY
            current_mode.set('daily')
            columns = columns_daily
            custom_widths = custom_widths_daily
            
            # Actualizar headers del sheet
            sheet.headers(columns_daily)
            
            # ⭐ HABILITAR EDICIÓN DIRECTA en sheet (modo editable)
            try:
                sheet.enable_bindings("edit_cell")
            except Exception as e:
                print(f"[DEBUG] No se pudo habilitar edit_cell: {e}")
            
            # Mostrar formulario de entrada
            entry_frame.pack(fill="x", side="bottom", padx=0, pady=0)
            
            # Ocultar frame de posición en cola (solo para covers)
            cover_queue_frame.pack_forget()
            
            # Ocultar botones de envío (solo en Specials)
            if enviar_btn:
                enviar_btn.pack_forget()
            if accion_btn:
                accion_btn.pack_forget()
            
            # Actualizar botón toggle
            if UI is not None:
                toggle_btn.configure(text="⭐ Specials", fg_color="#4D6068", hover_color="#3a7bc2")
            else:
                toggle_btn.configure(text="⭐ Specials", bg="#4D6068")

            # Cargar datos de daily
            load_daily()
        
        else:  # mode == 'covers' - volver a daily
            # Cambiar a DAILY
            current_mode.set('daily')
            columns = columns_daily
            custom_widths = custom_widths_daily
            
            # Actualizar headers del sheet
            sheet.headers(columns_daily)
            
            # ⭐ HABILITAR EDICIÓN DIRECTA en sheet (modo editable)
            try:
                sheet.enable_bindings("edit_cell")
            except Exception as e:
                print(f"[DEBUG] No se pudo habilitar edit_cell: {e}")
            
            # Mostrar formulario de entrada
            entry_frame.pack(fill="x", side="bottom", padx=0, pady=0)
            
            # ⭐ Ocultar frame de posición en cola
            cover_queue_frame.pack_forget()
            
            # Ocultar botones de envío
            if enviar_btn:
                enviar_btn.pack_forget()
            if accion_btn:
                accion_btn.pack_forget()
            
            # Actualizar botón toggle
            if UI is not None:
                toggle_btn.configure(text="⭐ Specials", fg_color="#4D6068", hover_color="#3a7bc2")
            else:
                toggle_btn.configure(text="⭐ Specials", bg="#4D6068")

            # Cargar datos de daily
            load_daily()
    
    # ⭐ FUNCIONES PARA MODO SPECIALS: Envío a supervisores (estilo open_report_window)
    
    def enviar_todos():
        """Selecciona todas las filas y las envía a un supervisor"""
        if current_mode.get() != 'specials':
            messagebox.showinfo("Modo incorrecto", "Esta función solo está disponible en modo Specials.", parent=top)
            return
        
        try:
            # Seleccionar todas las filas
            try:
                sheet.select_all()
            except Exception:
                try:
                    total = sheet.get_total_rows()
                    sheet.select_rows(list(range(total)))
                except Exception:
                    pass
        except Exception:
            pass
        
        # Llamar al flujo de supervisores indicando que se procesen todas las filas
        accion_supervisores(process_all=True)
    
    def accion_supervisores(process_all=False):
        """Muestra ventana para seleccionar supervisor y enviar eventos especiales"""
        if current_mode.get() != 'specials':
            messagebox.showinfo("Modo incorrecto", "Esta función solo está disponible en modo Specials.", parent=top)
            return
        
        # Ventana modal para elegir supervisor
        if UI is not None:
            supervisor_win = UI.CTkToplevel(top)
            try:
                supervisor_win.configure(fg_color="#2c2f33")
            except Exception:
                pass
        else:
            supervisor_win = tk.Toplevel(top)
            supervisor_win.configure(bg="#2c2f33")
        
        supervisor_win.title("Selecciona un Supervisor")
        supervisor_win.geometry("360x220")
        supervisor_win.resizable(False, False)
        
        if UI is not None:
            UI.CTkLabel(supervisor_win, text="Supervisores disponibles:", 
                       text_color="#00bfae", font=("Segoe UI", 16, "bold")).pack(pady=(18, 8))
            container = UI.CTkFrame(supervisor_win, fg_color="#2c2f33")
            container.pack(fill="both", expand=True, padx=16, pady=(0, 12))
        else:
            tk.Label(supervisor_win, text="Supervisores disponibles:", bg="#2c2f33", fg="#00bfae", 
                    font=("Segoe UI", 13, "bold")).pack(pady=(18, 4))
            container = tk.Frame(supervisor_win, bg="#2c2f33")
            container.pack(fill="both", expand=True, padx=14, pady=(4, 16))
        
        # Consultar lista de supervisores
        supervisores = []
        try:
            conn = under_super.get_connection()
            cur = conn.cursor()
            cur.execute("""
            SELECT u.Nombre_Usuario 
            FROM user u
            WHERE u.Rol IN (%s, %s)
            AND EXISTS (
                SELECT 1 
                FROM sesion s 
                WHERE s.ID_user = u.Nombre_Usuario 
                AND s.Active IN (1, 2)
                ORDER BY s.ID DESC 
                LIMIT 1
            )
            AND (
                SELECT s2.Active
                FROM sesion s2
                WHERE s2.ID_user = u.Nombre_Usuario
                ORDER BY s2.ID DESC
                LIMIT 1
            ) <> 0
        """, ("Supervisor", "Lead Supervisor"))
            supervisores = [row[0] for row in cur.fetchall()]
            cur.close()
            conn.close()
        except Exception as e:
            print(f"[ERROR] al consultar supervisores: {e}")
        
        # Control de selección
        sup_var = tk.StringVar()
        if UI is not None:
            if not supervisores:
                supervisores = ["No hay supervisores disponibles"]
            try:
                opt = UI.CTkOptionMenu(container, variable=sup_var, values=supervisores, 
                                      fg_color="#262a31", button_color="#14414e", text_color="#00bfae")
            except Exception:
                opt = UI.CTkOptionMenu(container, variable=sup_var, values=supervisores)
            if supervisores:
                try:
                    sup_var.set(supervisores[0])
                except Exception:
                    pass
            opt.pack(fill="x", padx=6, pady=6)
        else:
            yscroll_sup = tk.Scrollbar(container, orient="vertical")
            yscroll_sup.pack(side="right", fill="y")
            sup_listbox = tk.Listbox(container, height=10, selectmode="browse", bg="#262a31", fg="#00bfae", 
                                     font=("Segoe UI", 12), yscrollcommand=yscroll_sup.set, 
                                     activestyle="dotbox", selectbackground="#14414e")
            sup_listbox.pack(side="left", fill="both", expand=True)
            yscroll_sup.config(command=sup_listbox.yview)
            if not supervisores:
                sup_listbox.insert("end", "No hay supervisores disponibles")
            else:
                for sup in supervisores:
                    sup_listbox.insert("end", sup)
        
        def aceptar_supervisor():
            """Procesa el envío de eventos al supervisor seleccionado"""
            # Obtener selección de filas
            selected_rows = []
            if process_all:
                # Procesar todas las filas visibles
                try:
                    total = sheet.get_total_rows()
                except Exception:
                    try:
                        total = len(sheet.get_sheet_data())
                    except Exception:
                        total = 0
                selected_rows = list(range(total))
            else:
                try:
                    sel = sheet.get_selected_rows()
                except Exception:
                    sel = []
                
                # Si no hay filas seleccionadas, intentar con selección actual
                if not sel:
                    try:
                        cur_sel = sheet.get_currently_selected()
                        if cur_sel and cur_sel.row is not None:
                            sel = {cur_sel.row}
                    except Exception:
                        pass
                
                if not sel:
                    messagebox.showwarning("Sin selección", "No hay filas seleccionadas.", parent=supervisor_win)
                    return
                
                try:
                    selected_rows = list(sel)
                except Exception:
                    selected_rows = [next(iter(sel))]
            
            # Supervisor seleccionado
            if UI is not None:
                supervisor = (sup_var.get() or "").strip()
                if not supervisor or supervisor == "No hay supervisores disponibles":
                    messagebox.showwarning("Sin supervisor", "Debes seleccionar un supervisor.", parent=supervisor_win)
                    return
            else:
                selected_indices = sup_listbox.curselection()
                if not selected_indices or (sup_listbox.get(selected_indices[0]) == "No hay supervisores disponibles"):
                    messagebox.showwarning("Sin supervisor", "Debes seleccionar un supervisor.", parent=supervisor_win)
                    return
                supervisor = sup_listbox.get(selected_indices[0])
            
            try:
                conn = under_super.get_connection()
                cur = conn.cursor()
                inserted = 0
                updated = 0
                
                for r in selected_rows:
                    try:
                        valores = sheet.get_row_data(r)
                    except Exception:
                        valores = []
                    
                    # ⭐ Extraer valores según NUEVAS columnas (sin ID ni Usuario)
                    # Columnas: ["Fecha_hora", "ID_Sitio", "Nombre_Actividad", "Cantidad", "Camera", "Descripcion", "Time_Zone", "Marca"]
                    fecha_hora = valores[0] if len(valores) > 0 else None
                    id_sitio_str = valores[1] if len(valores) > 1 else None
                    nombre_actividad = valores[2] if len(valores) > 2 else None
                    cantidad = valores[3] if len(valores) > 3 else None
                    camera = valores[4] if len(valores) > 4 else None
                    descripcion = valores[5] if len(valores) > 5 else None
                    time_zone = valores[6] if len(valores) > 6 else None
                    # valores[7] es "Marca" - no lo necesitamos
                    
                    # Usuario actual (el que está enviando)
                    usuario_evt = username
                    
                    # Resolver ID_Sitio (puede venir como "Nombre (ID)" o solo "ID")
                    id_sitio = None
                    try:
                        if id_sitio_str:
                            # Intentar extraer ID de formato "Nombre (ID)"
                            if '(' in str(id_sitio_str) and ')' in str(id_sitio_str):
                                id_sitio = int(str(id_sitio_str).split('(')[1].split(')')[0])
                            else:
                                id_sitio = int(id_sitio_str)
                    except Exception:
                        id_sitio = None
                    
                    # Normalizar valores antes de guardar
                    cantidad_normalizada = int(cantidad) if cantidad is not None and str(cantidad).strip() else 0
                    camera_normalizada = str(camera).strip() if camera else ""
                    descripcion_normalizada = str(descripcion).strip() if descripcion else ""

                    
                    # Upsert en tabla specials
                    try:
                        # Verificar si ya existe en specials (buscar SOLO por campos clave)
                        cur.execute(
                            """
                            SELECT ID_special
                            FROM specials
                            WHERE FechaHora = %s
                              AND Usuario = %s
                              AND Nombre_Actividad = %s
                              AND IFNULL(ID_Sitio, 0) = IFNULL(%s, 0)
                            LIMIT 1
                            """,
                            (fecha_hora, usuario_evt, nombre_actividad, id_sitio),
                        )
                        row_exist = cur.fetchone()
                        
                        if row_exist:
                            # Actualizar registro existente (SIEMPRE actualizar con los valores actuales de Eventos)
                            special_id = row_exist[0]
                            try:
                                cur.execute(
                                    """
                                    UPDATE specials
                                    SET FechaHora = %s,
                                        ID_Sitio = %s,
                                        Nombre_Actividad = %s,
                                        Cantidad = %s,
                                        Camera = %s,
                                        Descripcion = %s,
                                        Usuario = %s,
                                        Time_Zone = %s,
                                        marked_status = NULL,
                                        marked_at = NULL,
                                        marked_by = NULL,
                                        Supervisor = %s
                                    WHERE ID_Special = %s
                                    AND Supervisor is NULL
                                    """,
                                    (fecha_hora, id_sitio, nombre_actividad, cantidad_normalizada, 
                                     camera_normalizada, descripcion_normalizada, 
                                     usuario_evt, time_zone, supervisor, special_id),
                                )
                                updated += 1
                                print(f"  -> ACTUALIZADO en specials (ID={special_id})")
                            except Exception as ue:
                                print(f"[ERROR] al actualizar fila en specials (ID={special_id}): {ue}")
                        else:
                            # Insertar nuevo registro (con campos marked_* inicializados a NULL)
                            try:
                                cur.execute(
                                    """
                                    INSERT INTO specials
                                        (FechaHora, ID_Sitio, Nombre_Actividad, Cantidad, Camera, Descripcion, 
                                         Usuario, Time_Zone, Supervisor, marked_status, marked_by, marked_at)
                                    VALUES
                                        (%s, %s, %s, %s, %s, %s, %s, %s, %s, NULL, NULL, NULL)
                                    """,
                                    (fecha_hora, id_sitio, nombre_actividad, cantidad_normalizada, 
                                     camera_normalizada, descripcion_normalizada, 
                                     usuario_evt, time_zone, supervisor),
                                )
                                inserted += 1
                                print(f"  -> INSERTADO en specials (nuevo registro)")
                            except Exception as ie:
                                print(f"[ERROR] al insertar fila en specials (Fecha_hora={fecha_hora}, Usuario={usuario_evt}): {ie}")
                    except Exception as e_row:
                        print(f"[ERROR] al procesar fila para specials (Usuario={usuario_evt}, Fecha_hora={fecha_hora}): {e_row}")
                
                conn.commit()
                cur.close()
                conn.close()
                
                
                
                supervisor_win.destroy()
                
                # Recargar datos para actualizar columna "Marca"
                load_specials()
                
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo enviar eventos:\n{e}", parent=supervisor_win)
                print(f"[ERROR] accion_supervisores: {e}")
                import traceback
                traceback.print_exc()
        
        # Botones Aceptar/Cancelar
        if UI is not None:
            btn_frame = UI.CTkFrame(supervisor_win, fg_color="transparent")
            btn_frame.pack(pady=(8, 16))
            
            UI.CTkButton(btn_frame, text="✅ Aceptar", command=aceptar_supervisor,
                        fg_color="#00c853", hover_color="#00a043",
                        font=("Segoe UI", 12, "bold"),
                        width=120, height=36).pack(side="left", padx=10)
            
            UI.CTkButton(btn_frame, text="❌ Cancelar", command=supervisor_win.destroy,
                        fg_color="#666666", hover_color="#555555",
                        font=("Segoe UI", 12),
                        width=120, height=36).pack(side="left", padx=10)
        else:
            btn_frame = tk.Frame(supervisor_win, bg="#2c2f33")
            btn_frame.pack(pady=(8, 16))
            
            tk.Button(btn_frame, text="✅ Aceptar", command=aceptar_supervisor,
                     bg="#00c853", fg="white", relief="flat",
                     width=12, font=("Segoe UI", 11, "bold")).pack(side="left", padx=10)
            tk.Button(btn_frame, text="❌ Cancelar", command=supervisor_win.destroy,
                     bg="#666666", fg="white", relief="flat",
                     width=12, font=("Segoe UI", 11)).pack(side="left", padx=10)
        
        supervisor_win.transient(top)
        supervisor_win.grab_set()
        supervisor_win.focus_set()

    # ⭐ NOTA: add_new_row() eliminada - ahora se usa el formulario inferior


    def delete_selected():
        """Elimina la fila seleccionada (SOLO EN MODO DAILY)"""
        # ⭐ BLOQUEAR ELIMINACIÓN en modos Specials y Covers
        mode = current_mode.get()
        if mode == 'specials':
            messagebox.showinfo("Información", 
                               "No se puede eliminar desde el modo Specials.\n"
                               "Usa el modo Daily para eliminar eventos.",
                               parent=top)
            return
        elif mode == 'covers':
            messagebox.showinfo("Información", 
                               "No se puede eliminar desde el modo Covers.\n"
                               "Esta función estará disponible próximamente.",
                               parent=top)
            return
        
        selected = sheet.get_currently_selected()
        if not selected:
            messagebox.showwarning("Advertencia", "No hay fila seleccionada.", parent=top)
            return

        # Obtener índice de fila seleccionada
        if selected.row is None:
            messagebox.showwarning("Advertencia", "Selecciona una fila completa.", parent=top)
            return

        row_idx = selected.row

        try:
            # Verificar si la fila existe en el cache
            if row_idx >= len(row_data_cache):
                messagebox.showwarning("Advertencia", "Índice de fila inválido.", parent=top)
                return

            cached_data = row_data_cache[row_idx]
            event_id = cached_data.get('id')

            # Si es una fila nueva (sin ID), solo quitarla del sheet
            if event_id is None:
                # Confirmar eliminación
                if not messagebox.askyesno("Confirmar", 
                                          "¿Eliminar esta fila nueva sin guardar?",
                                          parent=top):
                    return

                # Quitar del sheet
                current_data = sheet.get_sheet_data()
                current_data.pop(row_idx)
                sheet.set_sheet_data(current_data)
                apply_sheet_widths()

                # Quitar del cache
                row_data_cache.pop(row_idx)
                row_ids.pop(row_idx)

                # Actualizar pending_changes
                if row_idx in pending_changes:
                    pending_changes.remove(row_idx)
                # Ajustar índices mayores
                pending_changes[:] = [i-1 if i > row_idx else i for i in pending_changes]

                messagebox.showinfo("Eliminado", "Fila nueva eliminada.", parent=top)
                return

            # Si es una fila guardada, usar safe_delete
            if not messagebox.askyesno("Confirmar Eliminación", 
                                      f"¿Eliminar evento '{cached_data.get('actividad', '')}'?\n\n"
                                      "Será movido a la papelera.",
                                      parent=top):
                return

            # Pedir razón de eliminación
            reason = simpledialog.askstring("Razón de Eliminación", 
                                           "Ingresa la razón de eliminación:",
                                           parent=top)
            if not reason:
                reason = "Eliminación manual desde ventana híbrida"

            # Usar safe_delete para mover a papelera
            safe_delete("Eventos", "ID_Eventos", event_id, username, reason)

            # Quitar del sheet
            current_data = sheet.get_sheet_data()
            current_data.pop(row_idx)
            sheet.set_sheet_data(current_data)
            apply_sheet_widths()

            # Quitar del cache
            row_data_cache.pop(row_idx)
            row_ids.pop(row_idx)

            # Actualizar pending_changes
            if row_idx in pending_changes:
                pending_changes.remove(row_idx)
            pending_changes[:] = [i-1 if i > row_idx else i for i in pending_changes]

            messagebox.showinfo("Eliminado", "Evento eliminado y movido a la papelera.", parent=top)

        except Exception as e:
            messagebox.showerror("Error", f"Error al eliminar:\n{e}", parent=top)
            traceback.print_exc()
    
    # ⭐ Asignar comando delete_selected al botón del header
    try:
        delete_btn_header.configure(command=delete_selected)
    except:
        pass  # Si no existe el botón (fallback Tkinter), no hay problema

    def on_cell_edit(event):
        """Callback cuando se edita una celda - GUARDA AUTOMÁTICAMENTE"""
        try:
            # Obtener celda actualmente seleccionada (la que acaba de ser editada)
            selected = sheet.get_currently_selected()
            
            if selected and selected.row is not None:
                row_idx = selected.row
                col_idx = selected.column if selected.column is not None else -1
                # Verificar que sea una fila válida
                if row_idx < len(row_data_cache):
                    # Agregar a pending_changes si no está (para procesamiento)
                    if row_idx not in pending_changes:
                        pending_changes.append(row_idx)
                    
                    print(f"[DEBUG] Cell edited: row={row_idx}, col={col_idx}")
                    
                    # ⭐ GUARDAR AUTOMÁTICAMENTE después de un breve delay
                    top.after(500, auto_save_pending)
        except Exception as e:
            print(f"[DEBUG] on_cell_edit error: {e}")
            import traceback
            traceback.print_exc()
    
    def auto_save_pending():
        """Guarda automáticamente los cambios pendientes sin mostrar mensajes"""
        if not pending_changes:
            return
        
        try:
            conn = under_super.get_connection()
            if not conn:
                return
            
            cur = conn.cursor()
            
            # Obtener ID_Usuario
            cur.execute("SELECT ID_Usuario FROM user WHERE Nombre_Usuario=%s", (username,))
            user_row = cur.fetchone()
            if not user_row:
                cur.close()
                conn.close()
                return
            user_id = int(user_row[0])

            for idx in list(pending_changes):  # Copiar lista para evitar modificación durante iteración
                try:
                    # Obtener datos de la fila desde el sheet
                    row_data = sheet.get_row_data(idx)
                    if not row_data or len(row_data) < 6:  # Esperamos 6 columnas
                        continue

                    fecha_str, sitio_str, actividad, cantidad_str, camera, descripcion = row_data

                    # Validación básica - Actividad es obligatoria
                    if not actividad or not actividad.strip():
                        continue

                    # Fecha/Hora
                    if not fecha_str or not fecha_str.strip():
                        fecha_hora = datetime.now()
                    else:
                        try:
                            fecha_hora = datetime.strptime(fecha_str, "%Y-%m-%d %H:%M:%S")
                        except Exception:
                            continue

                    # Sitio - extraer ID_Sitio del formato "Nombre (ID)" o "Nombre ID"
                    sitio_id = None
                    if sitio_str and sitio_str.strip():
                        try:
                            # ⭐ Método 1: Buscar ID entre paréntesis "Nombre (123)"
                            import re
                            match = re.search(r'\((\d+)\)', sitio_str)
                            if match:
                                sitio_id = int(match.group(1))
                            else:
                                # ⭐ Método 2: Formato antiguo "Nombre 123" (fallback)
                                parts = sitio_str.strip().split()
                                sitio_id = int(parts[-1])
                            
                            # Verificar que existe
                            cur.execute("SELECT ID_Sitio FROM Sitios WHERE ID_Sitio=%s", (sitio_id,))
                            if not cur.fetchone():
                                continue
                        except Exception as e:
                            print(f"[DEBUG] Error extrayendo ID_Sitio de '{sitio_str}': {e}")
                            continue

                    # Cantidad
                    try:
                        cantidad = float(cantidad_str) if cantidad_str and cantidad_str.strip() else 0
                    except Exception:
                        continue

                    # Determinar si es INSERT o UPDATE
                    cached_data = row_data_cache[idx]
                    event_id = cached_data.get('id')

                    if cached_data['status'] == 'new' or event_id is None:
                        # INSERT - Nuevo evento
                        cur.execute("""
                            INSERT INTO Eventos (FechaHora, ID_Sitio, Nombre_Actividad, Cantidad, Camera, Descripcion, ID_Usuario)
                            VALUES (%s, %s, %s, %s, %s, %s, %s)
                        """, (fecha_hora, sitio_id, actividad.strip(), cantidad, camera.strip() if camera else "", 
                              descripcion.strip() if descripcion else "", user_id))
                        
                        new_id = cur.lastrowid
                        row_data_cache[idx]['id'] = new_id
                        row_ids[idx] = new_id
                        
                    else:
                        # UPDATE - Evento existente
                        cur.execute("""
                            UPDATE Eventos 
                            SET FechaHora=%s, ID_Sitio=%s, Nombre_Actividad=%s, Cantidad=%s, Camera=%s, Descripcion=%s
                            WHERE ID_Eventos=%s
                        """, (fecha_hora, sitio_id, actividad.strip(), cantidad, camera.strip() if camera else "",
                              descripcion.strip() if descripcion else "", event_id))

                    # Actualizar cache
                    row_data_cache[idx].update({
                        'fecha_hora': fecha_hora,
                        'sitio_id': sitio_id,
                        'sitio_nombre': sitio_str,
                        'actividad': actividad.strip(),
                        'cantidad': cantidad,
                        'camera': camera.strip() if camera else "",
                        'descripcion': descripcion.strip() if descripcion else "",
                        'status': 'saved'
                    })
                    
                    # Remover de pending_changes
                    if idx in pending_changes:
                        pending_changes.remove(idx)
                    
                    print(f"[DEBUG] Auto-saved row {idx}")

                except Exception as e:
                    print(f"[DEBUG] Error auto-saving row {idx}: {e}")
                    continue

            conn.commit()
            cur.close()
            conn.close()
            
        except Exception as e:
            print(f"[DEBUG] auto_save_pending error: {e}")
            import traceback
            traceback.print_exc()

    # Vincular evento de edición de celda
    sheet.bind("<<SheetModified>>", on_cell_edit, add=True)
    
    # ⭐ BINDING ADICIONAL: Capturar ediciones cuando se pierde el foco de la celda
    def on_cell_deselect(event):
        """Agrega la fila a pending_changes cuando se pierde el foco"""
        try:
            selected = sheet.get_currently_selected()
            if selected and selected.row is not None and selected.row < len(row_data_cache):
                row_idx = selected.row
                
                # Solo si no está ya marcada como pendiente
                if row_idx not in pending_changes:
                    # Verificar si realmente cambió algo comparando con cache
                    current_row = sheet.get_row_data(row_idx)
                    if current_row and len(current_row) >= 6:
                        # Agregar a pending changes
                        pending_changes.append(row_idx)
                        print(f"[DEBUG] Cell deselect - fila {row_idx} agregada a pendientes")
        except Exception as e:
            print(f"[DEBUG] on_cell_deselect error: {e}")
    
    sheet.bind("<<SheetSelect>>", on_cell_deselect, add=True)

    # Handler para bloquear edición por teclado en columnas protegidas
    def check_protected_edit(event):
        """Bloquea edición por teclado en columnas Sitio y Actividad"""
        try:
            # Bloquear CUALQUIER tecla en columnas protegidas
            if event.char and event.char.isprintable():
                selected = sheet.get_currently_selected()
                if selected and selected.column in [1, 2]:
                    # Bloquear la tecla completamente
                    return "break"
        except Exception as e:
            print(f"[DEBUG] check_protected_edit error: {e}")
    
    # Vincular evento para detectar intentos de edición POR TECLADO
    sheet.bind("<Key>", check_protected_edit, add=True)

    # ⭐ FUNCIÓN: Abrir ventana emergente para seleccionar Sitio
    def open_site_selector(row_idx):
        """Abre ventana emergente para seleccionar sitio"""
        try:
            if row_idx >= len(row_data_cache):
                return
            
            # Crear ventana de selección
            if UI is not None:
                sel_win = UI.CTkToplevel(top)
                sel_win.title("Seleccionar Sitio")
                sel_win.geometry("500x400")
                sel_win.configure(fg_color="#2c2f33")
            else:
                sel_win = tk.Toplevel(top)
                sel_win.title("Seleccionar Sitio")
                sel_win.geometry("500x400")
                sel_win.configure(bg="#2c2f33")
            
            sel_win.transient(top)
            sel_win.grab_set()
            
            # Header
            if UI is not None:
                UI.CTkLabel(sel_win, text="🏢 Seleccionar Sitio",
                           font=("Segoe UI", 16, "bold"),
                           text_color="#4a90e2").pack(pady=(15, 10))
            else:
                tk.Label(sel_win, text="🏢 Seleccionar Sitio",
                        bg="#2c2f33", fg="#4a90e2",
                        font=("Segoe UI", 16, "bold")).pack(pady=(15, 10))
            
            # Frame para búsqueda
            if UI is not None:
                search_frame = UI.CTkFrame(sel_win, fg_color="#23272a")
            else:
                search_frame = tk.Frame(sel_win, bg="#23272a")
            search_frame.pack(fill="x", padx=15, pady=(0, 10))
            
            # Campo de búsqueda
            search_var = tk.StringVar()
            if UI is not None:
                UI.CTkLabel(search_frame, text="Buscar:",
                           text_color="#c9d1d9",
                           font=("Segoe UI", 11)).pack(side="left", padx=(10, 5))
                search_entry = UI.CTkEntry(search_frame, textvariable=search_var,
                                          width=350, height=32)
            else:
                tk.Label(search_frame, text="Buscar:",
                        bg="#23272a", fg="#c9d1d9",
                        font=("Segoe UI", 11)).pack(side="left", padx=(10, 5))
                search_entry = tk.Entry(search_frame, textvariable=search_var,
                                       width=40, font=("Segoe UI", 11))
            search_entry.pack(side="left", padx=5, pady=8)
            search_entry.focus_set()
            
            # Frame para listbox
            list_frame = tk.Frame(sel_win, bg="#2c2f33")
            list_frame.pack(fill="both", expand=True, padx=15, pady=(0, 10))
            
            # Scrollbar y Listbox
            scrollbar = tk.Scrollbar(list_frame, orient="vertical")
            scrollbar.pack(side="right", fill="y")
            
            listbox = tk.Listbox(list_frame, yscrollcommand=scrollbar.set,
                                bg="#262a31", fg="#ffffff",
                                font=("Segoe UI", 11),
                                selectbackground="#4a90e2",
                                selectforeground="#ffffff",
                                activestyle="none")
            listbox.pack(side="left", fill="both", expand=True)
            scrollbar.config(command=listbox.yview)
            
            # Obtener lista de sitios
            sites_list = under_super.get_sites()
            
            def update_list(filter_text=""):
                """Actualiza la lista según el filtro"""
                listbox.delete(0, tk.END)
                filter_text = filter_text.lower()
                for site in sites_list:
                    if filter_text in site.lower():
                        listbox.insert(tk.END, site)
            
            def on_search_change(*args):
                """Callback cuando cambia el texto de búsqueda"""
                update_list(search_var.get())
            
            search_var.trace_add("write", on_search_change)
            update_list()  # Llenar inicialmente
            
            def on_select():
                """Callback cuando se selecciona un sitio"""
                selection = listbox.curselection()
                if not selection:
                    return
                
                selected_site = listbox.get(selection[0])
                
                # Actualizar celda en el sheet
                sheet.set_cell_data(row_idx, 1, selected_site)
                
                # Marcar como cambio pendiente
                if row_idx not in pending_changes:
                    pending_changes.append(row_idx)
                
                # Guardar automáticamente
                auto_save_pending()
                
                sel_win.destroy()
            
            def on_double_click(event):
                """Double-click para seleccionar"""
                on_select()
            
            def on_enter(event):
                """Enter para seleccionar"""
                on_select()
            
            listbox.bind("<Double-Button-1>", on_double_click)
            listbox.bind("<Return>", on_enter)
            search_entry.bind("<Return>", lambda e: on_select())
            
            # Botones
            if UI is not None:
                btn_frame = UI.CTkFrame(sel_win, fg_color="transparent")
            else:
                btn_frame = tk.Frame(sel_win, bg="#2c2f33")
            btn_frame.pack(fill="x", padx=15, pady=(0, 15))
            
            if UI is not None:
                UI.CTkButton(btn_frame, text="✅ Seleccionar",
                            command=on_select,
                            fg_color="#00c853", hover_color="#00a043",
                            width=120, height=35).pack(side="left", padx=(0, 10))
                UI.CTkButton(btn_frame, text="❌ Cancelar",
                            command=sel_win.destroy,
                            fg_color="#666666", hover_color="#555555",
                            width=120, height=35).pack(side="left")
            else:
                tk.Button(btn_frame, text="✅ Seleccionar",
                         command=on_select,
                         bg="#00c853", fg="white",
                         font=("Segoe UI", 11, "bold"),
                         relief="flat", width=12).pack(side="left", padx=(0, 10))
                tk.Button(btn_frame, text="❌ Cancelar",
                         command=sel_win.destroy,
                         bg="#666666", fg="white",
                         font=("Segoe UI", 11),
                         relief="flat", width=12).pack(side="left")
            
        except Exception as e:
            print(f"[ERROR] open_site_selector: {e}")
            import traceback
            traceback.print_exc()
    
    # ⭐ FUNCIÓN: Abrir ventana emergente para seleccionar Actividad
    def open_activity_selector(row_idx):
        """Abre ventana emergente para seleccionar actividad"""
        try:
            if row_idx >= len(row_data_cache):
                return
            
            # Crear ventana de selección
            if UI is not None:
                sel_win = UI.CTkToplevel(top)
                sel_win.title("Seleccionar Actividad")
                sel_win.geometry("500x400")
                sel_win.configure(fg_color="#2c2f33")
            else:
                sel_win = tk.Toplevel(top)
                sel_win.title("Seleccionar Actividad")
                sel_win.geometry("500x400")
                sel_win.configure(bg="#2c2f33")
            
            sel_win.transient(top)
            sel_win.grab_set()
            
            # Header
            if UI is not None:
                UI.CTkLabel(sel_win, text="📋 Seleccionar Actividad",
                           font=("Segoe UI", 16, "bold"),
                           text_color="#4a90e2").pack(pady=(15, 10))
            else:
                tk.Label(sel_win, text="📋 Seleccionar Actividad",
                        bg="#2c2f33", fg="#4a90e2",
                        font=("Segoe UI", 16, "bold")).pack(pady=(15, 10))
            
            # Frame para búsqueda
            if UI is not None:
                search_frame = UI.CTkFrame(sel_win, fg_color="#23272a")
            else:
                search_frame = tk.Frame(sel_win, bg="#23272a")
            search_frame.pack(fill="x", padx=15, pady=(0, 10))
            
            # Campo de búsqueda
            search_var = tk.StringVar()
            if UI is not None:
                UI.CTkLabel(search_frame, text="Buscar:",
                           text_color="#c9d1d9",
                           font=("Segoe UI", 11)).pack(side="left", padx=(10, 5))
                search_entry = UI.CTkEntry(search_frame, textvariable=search_var,
                                          width=350, height=32)
            else:
                tk.Label(search_frame, text="Buscar:",
                        bg="#23272a", fg="#c9d1d9",
                        font=("Segoe UI", 11)).pack(side="left", padx=(10, 5))
                search_entry = tk.Entry(search_frame, textvariable=search_var,
                                       width=40, font=("Segoe UI", 11))
            search_entry.pack(side="left", padx=5, pady=8)
            search_entry.focus_set()
            
            # Frame para listbox
            list_frame = tk.Frame(sel_win, bg="#2c2f33")
            list_frame.pack(fill="both", expand=True, padx=15, pady=(0, 10))
            
            # Scrollbar y Listbox
            scrollbar = tk.Scrollbar(list_frame, orient="vertical")
            scrollbar.pack(side="right", fill="y")
            
            listbox = tk.Listbox(list_frame, yscrollcommand=scrollbar.set,
                                bg="#262a31", fg="#ffffff",
                                font=("Segoe UI", 11),
                                selectbackground="#4a90e2",
                                selectforeground="#ffffff",
                                activestyle="none")
            listbox.pack(side="left", fill="both", expand=True)
            scrollbar.config(command=listbox.yview)
            
            # Obtener lista de actividades
            activities_list = under_super.get_activities()
            
            def update_list(filter_text=""):
                """Actualiza la lista según el filtro"""
                listbox.delete(0, tk.END)
                filter_text = filter_text.lower()
                for activity in activities_list:
                    if filter_text in activity.lower():
                        listbox.insert(tk.END, activity)
            
            def on_search_change(*args):
                """Callback cuando cambia el texto de búsqueda"""
                update_list(search_var.get())
            
            search_var.trace_add("write", on_search_change)
            update_list()  # Llenar inicialmente
            
            def on_select():
                """Callback cuando se selecciona una actividad"""
                selection = listbox.curselection()
                if not selection:
                    return
                
                selected_activity = listbox.get(selection[0])
                
                # Actualizar celda en el sheet
                sheet.set_cell_data(row_idx, 2, selected_activity)
                
                # Marcar como cambio pendiente
                if row_idx not in pending_changes:
                    pending_changes.append(row_idx)
                
                # Guardar automáticamente
                auto_save_pending()
                
                sel_win.destroy()
            
            def on_double_click(event):
                """Double-click para seleccionar"""
                on_select()
            
            def on_enter(event):
                """Enter para seleccionar"""
                on_select()
            
            listbox.bind("<Double-Button-1>", on_double_click)
            listbox.bind("<Return>", on_enter)
            search_entry.bind("<Return>", lambda e: on_select())
            
            # Botones
            if UI is not None:
                btn_frame = UI.CTkFrame(sel_win, fg_color="transparent")
            else:
                btn_frame = tk.Frame(sel_win, bg="#2c2f33")
            btn_frame.pack(fill="x", padx=15, pady=(0, 15))
            
            if UI is not None:
                UI.CTkButton(btn_frame, text="✅ Seleccionar",
                            command=on_select,
                            fg_color="#00c853", hover_color="#00a043",
                            width=120, height=35).pack(side="left", padx=(0, 10))
                UI.CTkButton(btn_frame, text="❌ Cancelar",
                            command=sel_win.destroy,
                            fg_color="#666666", hover_color="#555555",
                            width=120, height=35).pack(side="left")
            else:
                tk.Button(btn_frame, text="✅ Seleccionar",
                         command=on_select,
                         bg="#00c853", fg="white",
                         font=("Segoe UI", 11, "bold"),
                         relief="flat", width=12).pack(side="left", padx=(0, 10))
                tk.Button(btn_frame, text="❌ Cancelar",
                         command=sel_win.destroy,
                         bg="#666666", fg="white",
                         font=("Segoe UI", 11),
                         relief="flat", width=12).pack(side="left")
            
        except Exception as e:
            print(f"[ERROR] open_activity_selector: {e}")
            import traceback
            traceback.print_exc()
    
    # ⭐ BINDING: Doble click para DateTimePicker en   y ventanas emergentes para Sitio/Actividad
    def on_cell_double_click(event):
        """Detecta DOBLE click y abre ventanas emergentes de selección"""
        try:
            mode = current_mode.get()
            if mode in ('specials', 'covers'):
                return
            
            selected = sheet.get_currently_selected()
            
            if selected and selected.row is not None and selected.column is not None:
                col = selected.column
                row = selected.row
                
                # Columna 0:   → DateTimePicker
                if row < len(row_data_cache) and col == 0:
                    print(f"[DEBUG] Doble click en  ")
                    top.after(100, lambda: show_datetime_picker_for_edit(row))
                # Columna 1: Sitio → Ventana emergente de selección
                elif row < len(row_data_cache) and col == 1:
                    print(f"[DEBUG] Doble click en Sitio - abriendo ventana de selección")
                    top.after(50, lambda: open_site_selector(row))
                    return "break"
                # Columna 2: Actividad → Ventana emergente de selección
                elif row < len(row_data_cache) and col == 2:
                    print(f"[DEBUG] Doble click en Actividad - abriendo ventana de selección")
                    top.after(50, lambda: open_activity_selector(row))
                    return "break"
                    
        except Exception as e:
            print(f"[DEBUG] on_cell_double_click error: {e}")
    
    # Vincular eventos
    sheet.bind("<Double-Button-1>", on_cell_double_click, add=True)


    def show_datetime_picker():
        """Muestra selector moderno de fecha/hora usando CustomTkinter"""
        selected = sheet.get_currently_selected()
        if not selected or selected.row is None:
            messagebox.showinfo("Info", "Selecciona una fila primero.", parent=top)
            return

        row_idx = selected.row
        
        # Verificar que sea una fila válida
        if row_idx >= len(row_data_cache):
            return

        # Obtener valor actual
        current_value = sheet.get_cell_data(row_idx, 0)
        if current_value and current_value.strip():
            try:
                current_dt = datetime.strptime(current_value, "%Y-%m-%d %H:%M:%S")
            except:
                current_dt = datetime.now()
        else:
            current_dt = datetime.now()

        # Crear ventana con CustomTkinter si está disponible
        if UI is not None:
            picker_win = UI.CTkToplevel(top)
            picker_win.title("Seleccionar Fecha y Hora")
            picker_win.geometry("500x450")
            picker_win.resizable(False, False)
            
            # Header con icono
            header = UI.CTkFrame(picker_win, fg_color="#1a1a1a", corner_radius=0, height=60)
            header.pack(fill="x", padx=0, pady=0)
            header.pack_propagate(False)
            
            UI.CTkLabel(header, text="📅 Seleccionar Fecha y Hora", 
                       font=("Segoe UI", 20, "bold"),
                       text_color="#4a90e2").pack(pady=15)
            
            # Contenido principal
            content = UI.CTkFrame(picker_win, fg_color="transparent")
            content.pack(fill="both", expand=True, padx=20, pady=20)
            
            # Sección de Fecha
            date_section = UI.CTkFrame(content, fg_color="#2b2b2b", corner_radius=10)
            date_section.pack(fill="x", pady=(0, 15))
            
            UI.CTkLabel(date_section, text="📅 Fecha:", 
                       font=("Segoe UI", 14, "bold"),
                       text_color="#e0e0e0").pack(anchor="w", padx=15, pady=(15, 10))
            
            # Frame para calendario (tkcalendar no es CTk, lo envolvemos)
            cal_wrapper = tk.Frame(date_section, bg="#2b2b2b")
            cal_wrapper.pack(padx=15, pady=(0, 15))
            
            cal = tkcalendar.DateEntry(cal_wrapper, width=30, background='#4a90e2',
                                       foreground='white', borderwidth=2,
                                       year=current_dt.year, month=current_dt.month, day=current_dt.day,
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
            hour_var = tk.IntVar(value=current_dt.hour)
            minute_var = tk.IntVar(value=current_dt.minute)
            second_var = tk.IntVar(value=current_dt.second)
            
            # Frame para spinboxes (usando tk.Frame dentro de CTkFrame)
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
                now = datetime.now()
                cal.set_date(now.date())
                hour_var.set(now.hour)
                minute_var.set(now.minute)
                second_var.set(now.second)
            
            UI.CTkButton(time_section, text="⏰ Establecer Hora Actual", command=set_now,
                        fg_color="#4a90e2", hover_color="#3a7bc2",
                        font=("Segoe UI", 11),
                        width=200, height=35).pack(pady=(5, 15))
            
            # Botones Aceptar/Cancelar
            btn_frame = UI.CTkFrame(content, fg_color="transparent")
            btn_frame.pack(pady=10)
            
            def accept():
                try:
                    selected_date = cal.get_date()
                    selected_time = datetime.strptime(
                        f"{selected_date} {hour_var.get():02d}:{minute_var.get():02d}:{second_var.get():02d}",
                        "%Y-%m-%d %H:%M:%S"
                    )
                    
                    # Actualizar celda
                    formatted = selected_time.strftime("%Y-%m-%d %H:%M:%S")
                    sheet.set_cell_data(row_idx, 0, formatted)
                    
                    # Agregar a pending_changes para auto-guardado
                    if row_idx not in pending_changes:
                        pending_changes.append(row_idx)
                    
                    # Guardar automáticamente
                    top.after(500, auto_save_pending)
                    
                    picker_win.destroy()
                except Exception as e:
                    messagebox.showerror("Error", f"Error al establecer fecha/hora:\n{e}", parent=picker_win)
            
            UI.CTkButton(btn_frame, text="✅ Aceptar", command=accept,
                        fg_color="#00c853", hover_color="#00a043",
                        font=("Segoe UI", 12, "bold"),
                        width=120, height=40).pack(side="left", padx=10)
            
            UI.CTkButton(btn_frame, text="❌ Cancelar", command=picker_win.destroy,
                        fg_color="#666666", hover_color="#555555",
                        font=("Segoe UI", 12),
                        width=120, height=40).pack(side="left", padx=10)
        
        else:
            # Fallback a Tkinter estándar (mejorado)
            picker_win = tk.Toplevel(top)
            picker_win.title("Selector de Fecha/Hora")
            picker_win.geometry("400x400")
            picker_win.resizable(False, False)
            picker_win.configure(bg="#2c2f33")
            
            # Header
            tk.Label(picker_win, text="📅 Seleccionar Fecha y Hora", bg="#2c2f33", fg="#4a90e2",
                    font=("Segoe UI", 16, "bold")).pack(pady=15)
            
            # Frame superior para calendario
            cal_frame = tk.Frame(picker_win, bg="#2c2f33")
            cal_frame.pack(pady=10, padx=10)

            tk.Label(cal_frame, text="📅 Fecha:", bg="#2c2f33", fg="#e0e0e0",
                    font=("Segoe UI", 11, "bold")).pack(anchor="w")

            cal = tkcalendar.DateEntry(cal_frame, width=25, background='#4a90e2',
                                       foreground='white', borderwidth=2,
                                       year=current_dt.year, month=current_dt.month, day=current_dt.day,
                                       date_pattern='yyyy-mm-dd')
            cal.pack(pady=5)

            # Frame para hora
            time_frame = tk.Frame(picker_win, bg="#2c2f33")
            time_frame.pack(pady=10, padx=10)

            tk.Label(time_frame, text="🕐 Hora:", bg="#2c2f33", fg="#e0e0e0",
                    font=("Segoe UI", 11, "bold")).pack(anchor="w")

            # Spinboxes para hora, minuto, segundo
            spinbox_frame = tk.Frame(time_frame, bg="#2c2f33")
            spinbox_frame.pack(pady=5)

            hour_var = tk.IntVar(value=current_dt.hour)
            minute_var = tk.IntVar(value=current_dt.minute)
            second_var = tk.IntVar(value=current_dt.second)

            tk.Label(spinbox_frame, text="H:", bg="#2c2f33", fg="#a3c9f9",
                    font=("Segoe UI", 10)).grid(row=0, column=0, padx=2)
            hour_spin = tk.Spinbox(spinbox_frame, from_=0, to=23, textvariable=hour_var,
                                  width=5, font=("Segoe UI", 10))
            hour_spin.grid(row=0, column=1, padx=2)

            tk.Label(spinbox_frame, text="M:", bg="#2c2f33", fg="#a3c9f9",
                    font=("Segoe UI", 10)).grid(row=0, column=2, padx=2)
            minute_spin = tk.Spinbox(spinbox_frame, from_=0, to=59, textvariable=minute_var,
                                    width=5, font=("Segoe UI", 10))
            minute_spin.grid(row=0, column=3, padx=2)

            tk.Label(spinbox_frame, text="S:", bg="#2c2f33", fg="#a3c9f9",
                    font=("Segoe UI", 10)).grid(row=0, column=4, padx=2)
            second_spin = tk.Spinbox(spinbox_frame, from_=0, to=59, textvariable=second_var,
                                    width=5, font=("Segoe UI", 10))
            second_spin.grid(row=0, column=5, padx=2)

            # Botón "Ahora"
            def set_now():
                now = datetime.now()
                cal.set_date(now.date())
                hour_var.set(now.hour)
                minute_var.set(now.minute)
                second_var.set(now.second)

            tk.Button(time_frame, text="⏰ Ahora", command=set_now, bg="#4a90e2", fg="white",
                     relief="flat", font=("Segoe UI", 10)).pack(pady=5)

            # Botones Aceptar/Cancelar
            btn_frame = tk.Frame(picker_win, bg="#2c2f33")
            btn_frame.pack(pady=15)

            def accept():
                try:
                    selected_date = cal.get_date()
                    selected_time = datetime.strptime(
                        f"{selected_date} {hour_var.get():02d}:{minute_var.get():02d}:{second_var.get():02d}",
                        "%Y-%m-%d %H:%M:%S"
                    )
                    
                    # Actualizar celda
                    formatted = selected_time.strftime("%Y-%m-%d %H:%M:%S")
                    sheet.set_cell_data(row_idx, 0, formatted)
                    
                    # Agregar a pending_changes para auto-guardado
                    if row_idx not in pending_changes:
                        pending_changes.append(row_idx)
                    
                    # Guardar automáticamente
                    top.after(500, auto_save_pending)
                    
                    picker_win.destroy()
                except Exception as e:
                    messagebox.showerror("Error", f"Error al establecer fecha/hora:\n{e}", parent=picker_win)

            tk.Button(btn_frame, text="✅ Aceptar", command=accept, bg="#00c853", fg="white",
                     relief="flat", width=12, font=("Segoe UI", 11, "bold")).pack(side="left", padx=10)
            tk.Button(btn_frame, text="❌ Cancelar", command=picker_win.destroy, bg="#666666", fg="white",
                     relief="flat", width=12, font=("Segoe UI", 11)).pack(side="left", padx=10)
        
        picker_win.transient(top)
        picker_win.grab_set()
        picker_win.focus_set()

    # FUNCIONES POPUP DE RESPALDO (si dropdowns integrados no funcionan)
    def show_site_picker():
        """Muestra popup moderno para seleccionar sitio usando CustomTkinter"""
        selection = sheet.get_currently_selected()
        if not selection or selection.row is None:
            messagebox.showwarning("Advertencia", "Selecciona una fila primero", parent=top)
            return
        
        row_idx = selection.row
        
        # Crear ventana con CustomTkinter si está disponible
        if UI is not None:
            picker_win = UI.CTkToplevel(top)
            picker_win.title("Seleccionar Sitio")
            picker_win.geometry("500x250")
            
            # Header con icono
            header = UI.CTkFrame(picker_win, fg_color="#1a1a1a", corner_radius=0, height=60)
            header.pack(fill="x", padx=0, pady=0)
            header.pack_propagate(False)
            
            UI.CTkLabel(header, text="🏢 Seleccionar Sitio", 
                       font=("Segoe UI", 20, "bold"),
                       text_color="#4a90e2").pack(pady=15)
            
            # Contenido principal
            content = UI.CTkFrame(picker_win, fg_color="transparent")
            content.pack(fill="both", expand=True, padx=20, pady=20)
            
            UI.CTkLabel(content, text="Buscar y seleccionar un sitio:",
                       font=("Segoe UI", 12),
                       text_color="#e0e0e0").pack(anchor="w", pady=(0, 10))
            
            # ⭐ FilteredCombobox oscuro con borde prominente
            sites = under_super.get_sites()
            combo_var = tk.StringVar()
            combo = under_super.FilteredCombobox(
                content, textvariable=combo_var, values=sites,
                font=("Segoe UI", 11), width=50,
                background='#2b2b2b', foreground='#ffffff',
                fieldbackground='#2b2b2b',
                bordercolor='#5ab4ff', arrowcolor='#ffffff',
                borderwidth=3
            )
            combo.pack(fill="x", pady=(0, 20))
            combo.focus_set()
            
            # Botones
            btn_frame = UI.CTkFrame(content, fg_color="transparent")
            btn_frame.pack(pady=10)
            
            def accept():
                selected = combo_var.get().strip()
                if selected:
                    sheet.set_cell_data(row_idx, 1, selected)
                    if row_idx not in pending_changes:
                        pending_changes.append(row_idx)
                    
                    # Guardar automáticamente
                    top.after(500, auto_save_pending)
                    
                    picker_win.destroy()
                else:
                    messagebox.showwarning("Advertencia", "Selecciona un sitio primero", parent=picker_win)
            
            UI.CTkButton(btn_frame, text="✅ Aceptar", command=accept,
                        fg_color="#00c853", hover_color="#00a043",
                        font=("Segoe UI", 12, "bold"),
                        width=120, height=40).pack(side="left", padx=10)
            
            UI.CTkButton(btn_frame, text="❌ Cancelar", command=picker_win.destroy,
                        fg_color="#666666", hover_color="#555555",
                        font=("Segoe UI", 12),
                        width=120, height=40).pack(side="left", padx=10)
        else:
            # Fallback a Tkinter estándar
            picker_win = tk.Toplevel(top)
            picker_win.title("Seleccionar Sitio")
            picker_win.geometry("450x200")
            picker_win.configure(bg="#2c2f33")
            picker_win.transient(top)
            picker_win.grab_set()
            
            tk.Label(picker_win, text="🏢 Seleccionar Sitio", bg="#2c2f33", fg="#4a90e2",
                    font=("Segoe UI", 16, "bold")).pack(pady=15)
            
            tk.Label(picker_win, text="Buscar y seleccionar sitio:", bg="#2c2f33", fg="#e0e0e0",
                    font=("Segoe UI", 11)).pack(pady=10)
            
            # ⭐ FilteredCombobox oscuro con borde prominente
            sites = under_super.get_sites()
            combo_var = tk.StringVar()
            combo = under_super.FilteredCombobox(
                picker_win, textvariable=combo_var, values=sites,
                font=("Segoe UI", 10), width=50,
                background='#2b2b2b', foreground='#ffffff',
                fieldbackground='#2b2b2b',
                bordercolor='#5ab4ff', arrowcolor='#ffffff',
                borderwidth=3
            )
            combo.pack(pady=10, fill="x", padx=20)
            combo.focus_set()
            
            def accept():
                selected = combo_var.get().strip()
                if selected:
                    sheet.set_cell_data(row_idx, 1, selected)
                    if row_idx not in pending_changes:
                        pending_changes.append(row_idx)
                    
                    # Guardar automáticamente
                    top.after(500, auto_save_pending)
                    
                    picker_win.destroy()
                else:
                    messagebox.showwarning("Advertencia", "Selecciona un sitio primero", parent=picker_win)
            
            btn_frame = tk.Frame(picker_win, bg="#2c2f33")
            btn_frame.pack(pady=15)
            
            tk.Button(btn_frame, text="✅ Aceptar", command=accept, bg="#00c853", fg="white",
                     relief="flat", width=12, font=("Segoe UI", 11, "bold")).pack(side="left", padx=10)
            tk.Button(btn_frame, text="❌ Cancelar", command=picker_win.destroy, bg="#666666", fg="white",
                     relief="flat", width=12, font=("Segoe UI", 11)).pack(side="left", padx=10)
        
        picker_win.transient(top)
        picker_win.grab_set()
        picker_win.focus_set()

    def show_activity_picker():
        """Muestra popup moderno para seleccionar actividad usando CustomTkinter"""
        selection = sheet.get_currently_selected()
        if not selection or selection.row is None:
            messagebox.showwarning("Advertencia", "Selecciona una fila primero", parent=top)
            return
        
        row_idx = selection.row
        
        # Crear ventana con CustomTkinter si está disponible
        if UI is not None:
            picker_win = UI.CTkToplevel(top)
            picker_win.title("Seleccionar Actividad")
            picker_win.geometry("500x250")
            
            # Header con icono
            header = UI.CTkFrame(picker_win, fg_color="#1a1a1a", corner_radius=0, height=60)
            header.pack(fill="x", padx=0, pady=0)
            header.pack_propagate(False)
            
            UI.CTkLabel(header, text="📋 Seleccionar Actividad", 
                       font=("Segoe UI", 20, "bold"),
                       text_color="#4a90e2").pack(pady=15)
            
            # Contenido principal
            content = UI.CTkFrame(picker_win, fg_color="transparent")
            content.pack(fill="both", expand=True, padx=20, pady=20)
            
            UI.CTkLabel(content, text="Buscar y seleccionar una actividad:",
                       font=("Segoe UI", 12),
                       text_color="#e0e0e0").pack(anchor="w", pady=(0, 10))
            
            # ⭐ FilteredCombobox oscuro con borde prominente
            activities = under_super.get_activities()
            combo_var = tk.StringVar()
            combo = under_super.FilteredCombobox(
                content, textvariable=combo_var, values=activities,
                font=("Segoe UI", 11), width=50,
                background='#2b2b2b', foreground='#ffffff',
                fieldbackground='#2b2b2b',
                bordercolor='#5ab4ff', arrowcolor='#ffffff',
                borderwidth=3
            )
            combo.pack(fill="x", pady=(0, 20))
            combo.focus_set()
            
            # Botones
            btn_frame = UI.CTkFrame(content, fg_color="transparent")
            btn_frame.pack(pady=10)
            
            def accept():
                selected = combo_var.get().strip()
                if selected:
                    sheet.set_cell_data(row_idx, 2, selected)
                    if row_idx not in pending_changes:
                        pending_changes.append(row_idx)
                    
                    # Guardar automáticamente
                    top.after(500, auto_save_pending)
                    
                    picker_win.destroy()
                else:
                    messagebox.showwarning("Advertencia", "Selecciona una actividad primero", parent=picker_win)
            
            UI.CTkButton(btn_frame, text="✅ Aceptar", command=accept,
                        fg_color="#00c853", hover_color="#00a043",
                        font=("Segoe UI", 12, "bold"),
                        width=120, height=40).pack(side="left", padx=10)
            
            UI.CTkButton(btn_frame, text="❌ Cancelar", command=picker_win.destroy,
                        fg_color="#666666", hover_color="#555555",
                        font=("Segoe UI", 12),
                        width=120, height=40).pack(side="left", padx=10)
        else:
            # Fallback a Tkinter estándar
            picker_win = tk.Toplevel(top)
            picker_win.title("Seleccionar Actividad")
            picker_win.geometry("450x200")
            picker_win.configure(bg="#2c2f33")
            picker_win.transient(top)
            picker_win.grab_set()
            
            tk.Label(picker_win, text="📋 Seleccionar Actividad", bg="#2c2f33", fg="#4a90e2",
                    font=("Segoe UI", 16, "bold")).pack(pady=15)
            
            tk.Label(picker_win, text="Buscar y seleccionar actividad:", bg="#2c2f33", fg="#e0e0e0",
                    font=("Segoe UI", 11)).pack(pady=10)
            
            # ⭐ FilteredCombobox oscuro con borde prominente
            activities = under_super.get_activities()
            combo_var = tk.StringVar()
            combo = under_super.FilteredCombobox(
                picker_win, textvariable=combo_var, values=activities,
                font=("Segoe UI", 10), width=50,
                background='#2b2b2b', foreground='#ffffff',
                fieldbackground='#2b2b2b',
                bordercolor='#5ab4ff', arrowcolor='#ffffff',
                borderwidth=3
            )
            combo.pack(pady=10, fill="x", padx=20)
            combo.focus_set()
            
            def accept():
                selected = combo_var.get().strip()
                if selected:
                    sheet.set_cell_data(row_idx, 2, selected)
                    if row_idx not in pending_changes:
                        pending_changes.append(row_idx)
                    
                    # Guardar automáticamente
                    top.after(500, auto_save_pending)
                    
                    picker_win.destroy()
                else:
                    messagebox.showwarning("Advertencia", "Selecciona una actividad primero", parent=picker_win)
            
            btn_frame = tk.Frame(picker_win, bg="#2c2f33")
            btn_frame.pack(pady=15)
            
            tk.Button(btn_frame, text="✅ Aceptar", command=accept, bg="#00c853", fg="white",
                     relief="flat", width=12, font=("Segoe UI", 11, "bold")).pack(side="left", padx=10)
            tk.Button(btn_frame, text="❌ Cancelar", command=picker_win.destroy, bg="#666666", fg="white",
                     relief="flat", width=12, font=("Segoe UI", 11)).pack(side="left", padx=10)
        
        picker_win.transient(top)
        picker_win.grab_set()
        picker_win.focus_set()

    # Menú contextual (clic derecho)
    def show_context_menu(event):
        """Muestra menú contextual con opciones"""
        context_menu = tk.Menu(top, tearoff=0, bg="#2c2f33", fg="#e0e0e0",
                              activebackground="#4a90e2", activeforeground="#ffffff",
                              font=("Segoe UI", 10))
        
        # Opciones de edición rápida - MÁS PROMINENTES
        context_menu.add_command(label="🏢 Seleccionar Sitio", command=show_site_picker)
        context_menu.add_command(label="📋 Seleccionar Actividad", command=show_activity_picker)
        context_menu.add_command(label="⌚ Seleccionar Fecha/Hora", command=show_datetime_picker)
        context_menu.add_separator()
        context_menu.add_command(label="🗑️ Eliminar Fila", command=delete_selected)

        
        
        try:
            context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            context_menu.grab_release()

    # Vincular menú contextual
    sheet.bind("<Button-3>", show_context_menu)

    # Barra de herramientas
    if UI is not None:
        toolbar = UI.CTkFrame(top, fg_color="#23272a", corner_radius=0, height=60)
    else:
        toolbar = tk.Frame(top, bg="#23272a", height=60)
    toolbar.pack(fill="x", padx=0, pady=0)
    toolbar.pack_propagate(False)

    if UI is not None:
        # ⭐ BOTÓN TOGGLE DAILY/SPECIALS (ciclo entre dos modos)
        toggle_btn = UI.CTkButton(
            toolbar, text="⭐ Specials", command=toggle_mode,
            fg_color="#4D6068", hover_color="#3a7bc2", 
            width=140, height=36,
            font=("Segoe UI", 12, "bold")
        )
        toggle_btn.pack(side="left", padx=5, pady=12)
        
        # ⭐ BOTONES DE ENVÍO (solo visibles en modo Specials)
        enviar_btn = UI.CTkButton(toolbar, text="📤 Enviar Todos", command=enviar_todos,
                    fg_color="#4D6068", hover_color="#009688", width=130, height=36)
        accion_btn = UI.CTkButton(toolbar, text="👥 Enviar individual", command=accion_supervisores,
                    fg_color="#4D6068", hover_color="#009688", width=160, height=36)

        # ⭐ BOTÓN LISTA DE COVERS (solo visible cuando Active = 2)
        def open_covers_list():
            """Abre panel integrado de lista de covers programados"""
            show_covers_programados_panel(top, UI, username)
        
        lista_covers_btn = UI.CTkButton(
            toolbar, 
            text="📋 Lista de Covers", 
            command=open_covers_list,
            fg_color="#4D6068", 
            hover_color="#ffa726", 
            width=160, 
            height=36
        )
        
        # Función para verificar y actualizar visibilidad del botón
        def check_and_update_covers_button():
            """Verifica si Active = 2 y muestra/oculta el botón según corresponda"""
            try:
                active_status = under_super.get_user_status_bd(username)
                if active_status == 2:
                    # Usuario ocupado - mostrar botón
                    if not lista_covers_btn.winfo_ismapped():
                        lista_covers_btn.pack(side="left", padx=5, pady=12)
                else:
                    # Usuario disponible u otro estado - ocultar botón
                    if lista_covers_btn.winfo_ismapped():
                        lista_covers_btn.pack_forget()
            except Exception as e:
                print(f"[ERROR] Error checking covers button visibility: {e}")
            
            # Programar siguiente verificación (cada 5 segundos)
            top.after(5000, check_and_update_covers_button)
        
        # Inicialmente oculto (se mostrará si Active = 2)
        lista_covers_btn.pack_forget()
        
        # Iniciar verificación periódica
        check_and_update_covers_button()
        
        # Inicialmente ocultos (modo daily) - se mostrarán en toggle_mode
        
    else:
        # ⭐ BOTÓN TOGGLE DAILY/SPECIALS (fallback Tkinter)
        toggle_btn = tk.Button(toolbar, text="📊 Specials", command=toggle_mode, 
                               bg="#4a90e2", fg="white", relief="flat", 
                               width=14, font=("Segoe UI", 10, "bold"))
        toggle_btn.pack(side="left", padx=5, pady=12)
        
        # ⭐ BOTONES DE ENVÍO (fallback Tkinter - solo modo Specials)
        enviar_btn = tk.Button(toolbar, text="📤 Enviar Todos", command=enviar_todos,
                            bg="#00bfae", fg="white", relief="flat", width=14)
        accion_btn = tk.Button(toolbar, text="👥 Acción Supervisores", command=accion_supervisores,
                            bg="#00bfae", fg="white", relief="flat", width=18)
        
        # ⭐ BOTÓN LISTA DE COVERS (fallback tkinter - solo visible cuando Active = 2)
        def open_covers_list():
            """Abre panel integrado de lista de covers programados"""
            show_covers_programados_panel(top, None, username)
        
        lista_covers_btn = tk.Button(
            toolbar, 
            text="📋 Lista de Covers", 
            command=open_covers_list,
            bg="#00bfae", 
            fg="white", 
            relief="flat", 
            width=18
        )
        
        # Función para verificar y actualizar visibilidad del botón (tkinter)
        def check_and_update_covers_button():
            """Verifica si Active = 2 y muestra/oculta el botón según corresponda"""
            try:
                active_status = under_super.get_user_status_bd(username)
                if active_status == 2:
                    # Usuario ocupado - mostrar botón
                    try:
                        lista_covers_btn.pack_info()
                    except:
                        lista_covers_btn.pack(side="left", padx=5, pady=12)
                else:
                    # Usuario disponible u otro estado - ocultar botón
                    try:
                        lista_covers_btn.pack_info()
                        lista_covers_btn.pack_forget()
                    except:
                        pass
            except Exception as e:
                print(f"[ERROR] Error checking covers button visibility: {e}")
            
            # Programar siguiente verificación (cada 5 segundos)
            top.after(5000, check_and_update_covers_button)
        
        # Inicialmente oculto
        lista_covers_btn.pack_forget()
        
        # Iniciar verificación periódica
        check_and_update_covers_button()

    # ⭐ CONFIGURAR CIERRE DE VENTANA: Ejecutar logout automáticamente
    def on_window_close():
        """Maneja el cierre de la ventana principal ejecutando logout"""
        try:
            # Ejecutar logout para cerrar sesión correctamente
            if session_id and station:
                login.do_logout(session_id, station, top)
            else:
                # Si no hay session_id, simplemente destruir la ventana
                try:
                    top.destroy()
                except Exception:
                    pass
        except Exception as e:
            print(f"[ERROR] Error en on_window_close: {e}")
            # En caso de error, destruir la ventana de todos modos
            try:
                top.destroy()
            except Exception:
                pass
    
    # Configurar protocolo de cierre (botón X)
    top.protocol("WM_DELETE_WINDOW", on_window_close)

    # ⭐ RECARGA AUTOMÁTICA: Listener para evento de reenfoque
    def on_window_refocused(event=None):
        """Recarga datos automáticamente cuando la ventana vuelve a ganar foco"""
        try:
            print(f"[DEBUG] Window refocused - Reloading data for {username}...")
            load_data()
        except Exception as e:
            print(f"[ERROR] Failed to reload data on refocus: {e}")
    
    # Vincular evento personalizado
    top.bind("<<WindowRefocused>>", on_window_refocused)

    # Registrar ventana y cargar datos iniciales
    _register_singleton('hybrid_events', top)
    load_data()

    print(f"[DEBUG] Hybrid events window opened for {username}")


def prompt_exit_active_cover(username, root):
    try:
        conn = under_super.get_connection()
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
        conn = under_super.get_connection()
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
    conn = under_super.get_connection()
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



def open_specials_window(username):
    """Muestra specials del supervisor filtrados por el turno actual (START SHIFT → ahora).
    Las marcas son persistentes en DB y visibles entre supervisores.
    VERSION MODERNIZADA con tksheet + CustomTkinter + auto-refresh"""
    try:
        ex = _focus_singleton('specials')
        if ex:
            return ex

        # Importar CustomTkinter
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

        # Importar tksheet
        USE_SHEET = False
        SheetClass = None
        try:
            from tksheet import Sheet as _Sheet
            SheetClass = _Sheet
            USE_SHEET = True
        except Exception:
            USE_SHEET = False
            SheetClass = None

        top_win = (UI.CTkToplevel() if UI is not None else tk.Toplevel())
        top_win.title(f"Specials de {username} - Turno actual")
        top_win.geometry("1350x600")
        try:
            if UI is None:
                top_win.configure(bg="#2c2f33")
            else:
                top_win.configure(fg_color="#2c2f33")
        except Exception:
            pass
        top_win.resizable(True, True)

        # Variables de estado
        auto_refresh_active = tk.BooleanVar(value=True)  # Auto-refresh activo
        refresh_job = None  # ID del job de after()
        
        cols = ["ID", "Fecha_hora", "ID_Sitio", "Nombre_Actividad", "Cantidad", "Camera", "Descripcion", "Usuario", "Time_Zone", "Marca"]
        
        # Anchos personalizados por columna (en píxeles) - SIN AUTOSIZE
        custom_widths = {
            "ID": 60,
            "Fecha_hora": 150,
            "ID_Sitio": 220,
            "Nombre_Actividad": 150,
            "Cantidad": 70,
            "Camera": 80,
            "Descripcion": 190,
            "Usuario": 100,
            "Time_Zone": 90,
            "Marca": 180
        }
        
        # Frame principal para tabla
        table_frame = (UI.CTkFrame(top_win, fg_color="#2c2f33") if UI is not None else tk.Frame(top_win, bg="#2c2f33"))
        table_frame.pack(expand=True, fill="both", padx=10, pady=10)

        # Variable para almacenar referencia de sheet/tree
        sheet = None
        tree = None
        data_cache = []  # Cache de datos para sheet

        if USE_SHEET and SheetClass:
            # USAR TKSHEET (moderno)
            sheet = SheetClass(
                table_frame,
                headers=cols,
                theme="dark blue",
                height=500,
                width=1360,
                show_selected_cells_border=True,
                show_row_index=True,  # Mostrar índice de filas
                show_top_left=False,
                empty_horizontal=0,
                empty_vertical=0
            )
            # ⭐ DESHABILITAR EDICIÓN - Solo visualización
            sheet.enable_bindings([
                "single_select",
                "drag_select",
                "column_select",
                "row_select",
                "column_width_resize",
                "double_click_column_resize",
                "row_height_resize",
                "arrowkeys",
                "right_click_popup_menu",
                "rc_select",
                "copy"
                # ❌ SIN: cut, paste, delete, undo (modo solo lectura)
            ])
            sheet.pack(fill="both", expand=True)
            
            # Colores personalizados
            sheet.change_theme("dark blue")
            
        else:
            # FALLBACK A TREEVIEW (legacy)
            style = ttk.Style(top_win)
            style.configure("Specials.Treeview",
                            background="#23272a",
                            foreground="#e0e0e0",
                            fieldbackground="#23272a",
                            rowheight=26,
                            bordercolor="#23272a",
                            borderwidth=0)
            style.configure("Specials.Treeview.Heading",
                            background="#23272a",
                            foreground="#a3c9f9",
                            font=("Segoe UI", 10, "bold"))
            style.map("Specials.Treeview", background=[("selected", "#4a90e2")], foreground=[("selected", "#ffffff")])

            yscroll = tk.Scrollbar(table_frame, orient="vertical")
            yscroll.pack(side="right", fill="y")
            xscroll = tk.Scrollbar(table_frame, orient="horizontal")
            xscroll.pack(side="bottom", fill="x")
            
            tree = ttk.Treeview(table_frame, columns=cols, show="headings", 
                               yscrollcommand=yscroll.set, xscrollcommand=xscroll.set,
                               style="Specials.Treeview", selectmode="extended")
            yscroll.config(command=tree.yview)
            xscroll.config(command=tree.xview)
            
            col_widths = {
                "ID": 70, "Fecha_hora": 150, "ID_Sitio": 200, "Nombre_Actividad": 140,
                "Cantidad": 70, "Camera": 90, "Descripcion": 240, "Usuario": 110,
                "Time_Zone": 80, "Marca": 150
            }
            for c in cols:
                tree.heading(c, text=c, anchor="center")
                tree.column(c, width=col_widths.get(c, 100), 
                           anchor="center" if c in ("ID", "Cantidad", "Camera", "Time_Zone", "Marca") else "w")
            
            tree.pack(side="left", fill="both", expand=True)
            
            # Tags para marcas visuales
            tree.tag_configure("oddrow", background="#3a3f44", foreground="#e0e0e0")
            tree.tag_configure("evenrow", background="#2f343a", foreground="#e0e0e0")
            tree.tag_configure("flagged", background="#f5a623", foreground="#111111")  # ámbar
            tree.tag_configure("done", background="#00c853", foreground="#111111")     # verde

        # ============= FUNCIONES AUXILIARES =============
        
        # Helper para aplicar anchos personalizados en tksheet (SIN AUTOSIZE)
        def apply_sheet_widths():
            """Aplica anchos personalizados a las columnas del sheet"""
            if sheet is None:
                return
            try:
                # Mapear nombres de columnas a índices
                for idx, col_name in enumerate(cols):
                    if col_name in custom_widths:
                        width = custom_widths[col_name]
                        try:
                            sheet.column_width(idx, int(width))
                        except Exception:
                            try:
                                sheet.set_column_width(idx, int(width))
                            except Exception:
                                pass
                # Forzar redibujado
                try:
                    sheet.redraw()
                except Exception:
                    pass
            except Exception as e:
                print(f"[ERROR] apply_sheet_widths: {e}")
        
        def get_supervisor_shift_start(supervisor_name):
            """Obtiene el último START SHIFT del supervisor dado"""
            try:
                conn = under_super.get_connection()
                cur = conn.cursor()
                cur.execute("""
                    SELECT e.FechaHora 
                    FROM Eventos e
                    INNER JOIN user u ON e.ID_Usuario = u.ID_Usuario
                    WHERE u.Nombre_Usuario = %s AND e.Nombre_Actividad = 'START SHIFT'
                    ORDER BY e.FechaHora DESC
                    LIMIT 1
                """, (supervisor_name,))
                row = cur.fetchone()
                cur.close()
                conn.close()
                return row[0] if row and row[0] else None
            except Exception as e:
                print(f"[ERROR] get_supervisor_shift_start: {e}")
                return None

        def load_specials():
            """Carga specials del supervisor desde el último START SHIFT hasta ahora"""
            nonlocal data_cache, refresh_job
            
            try:
                shift_start = get_supervisor_shift_start(username)
                if not shift_start:
                    if USE_SHEET and sheet:
                        sheet.set_sheet_data([["No hay shift activo"] + [""] * (len(cols)-1)])
                    elif tree:
                        tree.delete(*tree.get_children())
                        tree.insert("", "end", values=["No hay shift activo"] + [""] * (len(cols)-1), tags=("oddrow",))
                    return
                
                conn = under_super.get_connection()
                cur = conn.cursor()
                
                # Query: TODOS los specials desde START SHIFT hasta AHORA
                sql = """
                    SELECT ID_special, FechaHora, ID_Sitio, Nombre_Actividad, Cantidad, Camera,
                           Descripcion, Usuario, Time_Zone, marked_status, marked_by, marked_at
                    FROM specials
                    WHERE Supervisor = %s 
                    AND FechaHora >= %s
                    ORDER BY FechaHora DESC
                """
                params = (username, shift_start)
                window_title = f"Specials de {username} - Turno desde {shift_start.strftime('%d/%m/%Y %H:%M')}"
                
                top_win.title(window_title)
                
                cur.execute(sql, params)
                rows = cur.fetchall()
                
                # Resolver nombres de sitios y zonas horarias
                time_zone_cache = {}
                processed = []
                
                for r in rows:
                    rlist = list(r[:9])  # Primeras 9 columnas
                    id_sitio = rlist[2]
                    marked_status = r[9]
                    marked_by = r[10]
                    marked_at = r[11]
                    
                    # Resolver nombre de sitio y zona horaria
                    nombre_sitio = ""
                    tz = ""
                    if id_sitio is not None and str(id_sitio).strip() != "":
                        if id_sitio in time_zone_cache:
                            nombre_sitio, tz = time_zone_cache[id_sitio]
                        else:
                            try:
                                cur.execute("SELECT Nombre_Sitio, Time_Zone FROM Sitios WHERE ID_Sitio = %s", (id_sitio,))
                                sit = cur.fetchone()
                                nombre_sitio = sit[0] if sit and sit[0] else ""
                                tz = sit[1] if sit and len(sit) > 1 and sit[1] else ""
                            except Exception as e:
                                print(f"[DEBUG] error fetching site for ID_Sitio={id_sitio}: {e}")
                                nombre_sitio = ""
                                tz = ""
                            time_zone_cache[id_sitio] = (nombre_sitio, tz)
                    
                    # Formato visual para ID_Sitio
                    if id_sitio and nombre_sitio:
                        display_site = f"{id_sitio} {nombre_sitio}"
                    elif id_sitio:
                        display_site = str(id_sitio)
                    else:
                        display_site = nombre_sitio or ""
                    
                    rlist[2] = display_site
                    rlist[8] = tz
                    
                    # Formato visual para la marca
                    if marked_status == 'done':
                        mark_display = f"✅ Registrado ({marked_by})" if marked_by else "✅ Registrado"
                    elif marked_status == 'flagged':
                        mark_display = f"🔄 En Progreso ({marked_by})" if marked_by else "🔄 En Progreso"
                    else:
                        mark_display = ""
                    
                    rlist.append(mark_display)
                    processed.append({
                        'id': r[0],
                        'values': rlist,
                        'marked_status': marked_status
                    })
                
                cur.close()
                conn.close()
                
                # Poblar UI
                if USE_SHEET and sheet:
                    # TKSHEET
                    if not processed:
                        data_cache = [["No hay specials en este turno"] + [""] * (len(cols)-1)]
                        sheet.set_sheet_data(data_cache)
                        # Aplicar anchos personalizados
                        apply_sheet_widths()
                    else:
                        data_cache = [item['values'] for item in processed]
                        sheet.set_sheet_data(data_cache)
                        
                        # ⚡ APLICAR anchos personalizados INMEDIATAMENTE después de set_sheet_data
                        apply_sheet_widths()
                        
                        # Limpiar todos los colores de fondo primero (para que los nuevos queden sin color)
                        sheet.dehighlight_all()
                        
                        # Aplicar colores SOLO a los registros marcados
                        for idx, item in enumerate(processed):
                            if item['marked_status'] == 'done':
                                # Verde (#00c853) para registrado
                                sheet.highlight_rows([idx], bg="#00c853", fg="#111111")
                            elif item['marked_status'] == 'flagged':
                                # Ámbar (#f5a623) para en progreso
                                sheet.highlight_rows([idx], bg="#f5a623", fg="#111111")
                            # Los registros sin marca (None/NULL) quedan SIN COLOR
                
                elif tree:
                    # TREEVIEW (fallback)
                    tree.delete(*tree.get_children())
                    if not processed:
                        tree.insert("", "end", values=["No hay specials en este turno"] + [""] * (len(cols)-1), tags=("oddrow",))
                    else:
                        for idx, item in enumerate(processed):
                            values = [str(v) if v is not None else "" for v in item['values']]
                            base_tag = "evenrow" if idx % 2 == 0 else "oddrow"
                            
                            if item['marked_status'] == 'done':
                                tags = (base_tag, "done")
                            elif item['marked_status'] == 'flagged':
                                tags = (base_tag, "flagged")
                            else:
                                tags = (base_tag,)
                            
                            tree.insert("", "end", iid=str(item['id']), values=values, tags=tags)
                
                print(f"[DEBUG] Loaded {len(processed)} specials for {username}")
                
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo cargar specials:\n{e}", parent=top_win)
                import traceback
                traceback.print_exc()
            
            # Programar siguiente refresh si auto-refresh está activo
            finally:
                if auto_refresh_active.get():
                    refresh_job = top_win.after(120000, load_specials)  # Refresh cada 2 minutos

        def get_selected_ids():
            """Obtiene los IDs de los registros seleccionados"""
            if USE_SHEET and sheet:
                selected_rows = sheet.get_selected_rows()
                if not selected_rows:
                    return []
                # Obtener IDs de la primera columna
                ids = []
                for row_idx in selected_rows:
                    try:
                        row_data = sheet.get_row_data(row_idx)
                        if row_data and len(row_data) > 0:
                            ids.append(row_data[0])  # Primera columna es ID
                    except Exception:
                        pass
                return ids
            elif tree:
                return list(tree.selection())
            return []

        def mark_as_done():
            """Marca los registros seleccionados como 'Done' (Registrado)"""
            sel = get_selected_ids()
            if not sel:
                messagebox.showinfo("Marcar", "Selecciona uno o más specials para marcar como Registrado.", parent=top_win)
                return
            
            try:
                conn = under_super.get_connection()
                cur = conn.cursor()
                
                # Marcar todos los seleccionados como 'done'
                for item_id in sel:
                    cur.execute("""
                        UPDATE specials 
                        SET marked_status = 'done', marked_at = NOW(), marked_by = %s
                        WHERE ID_special = %s
                    """, (username, item_id))
                
                conn.commit()
                cur.close()
                conn.close()
                
                load_specials()
                

                
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo marcar:\n{e}", parent=top_win)
                import traceback
                traceback.print_exc()

        def mark_as_progress():
            """Marca los registros seleccionados como 'En Progreso'"""
            sel = get_selected_ids()
            if not sel:
                messagebox.showinfo("Marcar", "Selecciona uno o más specials para marcar como En Progreso.", parent=top_win)
                return
            
            try:
                conn = under_super.get_connection()
                cur = conn.cursor()
                
                # Marcar todos los seleccionados como 'flagged'
                for item_id in sel:
                    cur.execute("""
                        UPDATE specials 
                        SET marked_status = 'flagged', marked_at = NOW(), marked_by = %s
                        WHERE ID_special = %s
                    """, (username, item_id))
                
                conn.commit()
                cur.close()
                conn.close()
                
                load_specials()

                
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo marcar:\n{e}", parent=top_win)
                import traceback
                traceback.print_exc()

        def unmark_selected():
            """Desmarca los registros seleccionados"""
            sel = get_selected_ids()
            if not sel:
                return
            
            try:
                conn = under_super.get_connection()
                cur = conn.cursor()
                
                for item_id in sel:
                    cur.execute("""
                        UPDATE specials 
                        SET marked_status = NULL, marked_at = NULL, marked_by = NULL
                        WHERE ID_special = %s
                    """, (item_id,))
                
                conn.commit()
                cur.close()
                conn.close()
                
                load_specials()
                
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo desmarcar:\n{e}", parent=top_win)
                import traceback
                traceback.print_exc()

        def clear_marks():
            """Limpia todas las marcas del supervisor actual"""
            if not messagebox.askyesno("Limpiar marcas", 
                                       f"¿Desmarcar TODOS los specials de {username}?", 
                                       parent=top_win):
                return
            
            try:
                conn = under_super.get_connection()
                cur = conn.cursor()
                cur.execute("""
                    UPDATE specials 
                    SET marked_status = NULL, marked_at = NULL, marked_by = NULL
                    WHERE Supervisor = %s
                """, (username,))
                conn.commit()
                cur.close()
                conn.close()
                
                load_specials()

                
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo limpiar marcas:\n{e}", parent=top_win)

        def copy_to_clipboard(event=None):
            """Copia la selección al portapapeles"""
            try:
                if USE_SHEET and sheet:
                    sheet.copy()  # tksheet tiene copy integrado

                elif tree:
                    items = tree.selection() if tree.selection() else tree.get_children()
                    if not items:
                        messagebox.showinfo("Copiar", "No hay filas para copiar.", parent=top_win)
                        return "break"
                    
                    lines = ["\t".join(cols)]
                    for it in items:
                        vals = list(tree.item(it, 'values'))
                        clean = [str(v).replace("\t", " ").replace("\r", " ").replace("\n", " ") for v in vals[:len(cols)]]
                        lines.append("\t".join(clean))
                    
                    data = "\n".join(lines)
                    top_win.clipboard_clear()
                    top_win.clipboard_append(data)
                    top_win.update()
                    messagebox.showinfo("Copiar", f"✅ {len(items)} fila(s) copiadas", parent=top_win)
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo copiar:\n{e}", parent=top_win)
            return "break"

        def toggle_auto_refresh():
            """Activa/desactiva auto-refresh"""
            if auto_refresh_active.get():
                print("[DEBUG] Auto-refresh activado")
                load_specials()  # Iniciar ciclo
            else:
                print("[DEBUG] Auto-refresh desactivado")
                if refresh_job:
                    top_win.after_cancel(refresh_job)

        def show_context_menu(event):
            """Muestra menú contextual al hacer clic derecho en las filas"""
            # Crear menú contextual
            context_menu = tk.Menu(top_win, tearoff=0, bg="#2c2f33", fg="#e0e0e0", 
                                  activebackground="#4a90e2", activeforeground="#ffffff",
                                  font=("Segoe UI", 10))
            
            context_menu.add_command(label="✅ Marcar como Registrado", command=mark_as_done)
            context_menu.add_command(label="🔄 Marcar como En Progreso", command=mark_as_progress)
            context_menu.add_separator()
            context_menu.add_command(label="❌ Desmarcar", command=unmark_selected)
            context_menu.add_command(label="📋 Copiar", command=copy_to_clipboard)
            
            try:
                context_menu.tk_popup(event.x_root, event.y_root)
            finally:
                context_menu.grab_release()

        def open_otros_specials(current_username):
            """Ver y tomar specials de otros supervisores (filtrados por turno)"""
            # Ventana de selección de supervisor
            sel_win = (UI.CTkToplevel(top_win) if UI is not None else tk.Toplevel(top_win))
            sel_win.title("Otros Specials - Selecciona Supervisor")
            try:
                if UI is None:
                    sel_win.configure(bg="#2c2f33")
                else:
                    sel_win.configure(fg_color="#2c2f33")
            except Exception:
                pass
            sel_win.geometry("380x340")
            sel_win.resizable(False, False)

            if UI is not None:
                UI.CTkLabel(sel_win, text="Supervisor (origen):", text_color="#00bfae",
                           font=("Segoe UI", 13, "bold")).pack(pady=(14, 6))
            else:
                tk.Label(sel_win, text="Supervisor (origen):", bg="#2c2f33", fg="#00bfae",
                        font=("Segoe UI", 13, "bold")).pack(pady=(14, 6))

            list_frame = (UI.CTkFrame(sel_win, fg_color="#2c2f33") if UI is not None else tk.Frame(sel_win, bg="#2c2f33"))
            list_frame.pack(fill="both", expand=True, padx=14, pady=(4,12))
            
            yscroll_sup = tk.Scrollbar(list_frame, orient="vertical")
            yscroll_sup.pack(side="right", fill="y")
            sup_listbox = tk.Listbox(list_frame, height=10, selectmode="browse",
                                     bg="#262a31", fg="#00bfae", font=("Segoe UI", 12),
                                     yscrollcommand=yscroll_sup.set, activestyle="dotbox",
                                     selectbackground="#14414e")
            sup_listbox.pack(side="left", fill="both", expand=True)
            yscroll_sup.config(command=sup_listbox.yview)

            # Cargar supervisores
            supervisores = []
            try:
                conn = under_super.get_connection()
                cur = conn.cursor()
                cur.execute("SELECT Nombre_Usuario FROM user WHERE Rol = %s ORDER BY Nombre_Usuario", ("Supervisor",))
                supervisores = [r[0] for r in cur.fetchall()]
                cur.close()
                conn.close()
            except Exception as e:
                print(f"[ERROR] otros_specials list: {e}")
            
            if not supervisores:
                sup_listbox.insert("end", "No hay supervisores disponibles")
            else:
                for sup in supervisores:
                    sup_listbox.insert("end", sup)

            def abrir_lista_specials():
                idx = sup_listbox.curselection()
                if not idx:
                    messagebox.showwarning("Otros Specials", "Selecciona un supervisor.", parent=sel_win)
                    return
                old_sup = sup_listbox.get(idx[0])
                if old_sup == "No hay supervisores disponibles":
                    return
                
                try:
                    sel_win.destroy()
                except Exception:
                    pass

                # Ventana de specials del otro supervisor (con filtro de shift)
                key = f"otros_specials_{old_sup}"
                ex = _focus_singleton(key)
                if ex:
                    return ex

                lst_win = (UI.CTkToplevel(top_win) if UI is not None else tk.Toplevel(top_win))
                lst_win.title(f"Otros Specials - {old_sup}")
                try:
                    if UI is None:
                        lst_win.configure(bg="#2c2f33")
                    else:
                        lst_win.configure(fg_color="#2c2f33")
                except Exception:
                    pass
                lst_win.geometry("1350x600")
                lst_win.resizable(True, True)

                # Variables para tabla
                sheet2 = None
                tree2 = None
                row_ids_otros = []  # Mapa de índice -> ID_Special
                data_cache_otros = []
                
                # Columnas y anchos
                cols2 = ["ID", "Fecha_hora", "ID_Sitio", "Nombre_Actividad", "Cantidad", "Camera", 
                        "Descripcion", "Usuario", "Time_Zone", "Marca"]
                
                custom_widths_otros = {
                    "ID": 60,
                    "Fecha_hora": 150,
                    "ID_Sitio": 220,
                    "Nombre_Actividad": 150,
                    "Cantidad": 70,
                    "Camera": 80,
                    "Descripcion": 190,
                    "Usuario": 100,
                    "Time_Zone": 90,
                    "Marca": 180
                }

                # Frame para tabla
                frame2 = (UI.CTkFrame(lst_win, fg_color="#2c2f33") if UI is not None else tk.Frame(lst_win, bg="#2c2f33"))
                frame2.pack(expand=True, fill="both", padx=12, pady=10)
                
                # Helper para aplicar anchos en tksheet
                def apply_sheet_widths_otros():
                    if sheet2 is None:
                        return
                    try:
                        for idx, col_name in enumerate(cols2):
                            if col_name in custom_widths_otros:
                                width = custom_widths_otros[col_name]
                                try:
                                    sheet2.column_width(idx, int(width))
                                except Exception:
                                    try:
                                        sheet2.set_column_width(idx, int(width))
                                    except Exception:
                                        pass
                        try:
                            sheet2.redraw()
                        except Exception:
                            pass
                    except Exception as e:
                        print(f"[ERROR] apply_sheet_widths_otros: {e}")
                
                # Crear tksheet o Treeview
                if USE_SHEET and SheetClass:
                    sheet2 = SheetClass(
                        frame2,
                        headers=cols2,
                        theme="dark blue",
                        height=400,
                        width=1160,
                        show_selected_cells_border=True,
                        show_row_index=True,
                        show_top_left=False,
                        empty_horizontal=0,
                        empty_vertical=0
                    )
                    sheet2.enable_bindings([
                        "single_select",
                        "drag_select",
                        "column_select",
                        "row_select",
                        "column_width_resize",
                        "double_click_column_resize",
                        "row_height_resize",
                        "arrowkeys",
                        "right_click_popup_menu",
                        "rc_select",
                        "copy",
                        "cut",
                        "paste",
                        "delete",
                        "undo"
                    ])
                    sheet2.pack(fill="both", expand=True)
                    sheet2.change_theme("dark blue")
                else:
                    # Fallback a Treeview
                    yscroll2 = tk.Scrollbar(frame2, orient="vertical")
                    yscroll2.pack(side="right", fill="y")
                    xscroll2 = tk.Scrollbar(frame2, orient="horizontal")
                    xscroll2.pack(side="bottom", fill="x")
                    
                    style_otros = ttk.Style()
                    style_otros.configure("OtrosSpecials.Treeview",
                                         background="#23272a",
                                         foreground="#e0e0e0",
                                         fieldbackground="#23272a",
                                         rowheight=26)
                    style_otros.configure("OtrosSpecials.Treeview.Heading",
                                         background="#23272a",
                                         foreground="#a3c9f9",
                                         font=("Segoe UI", 10, "bold"))
                    
                    tree2 = ttk.Treeview(frame2, columns=cols2, show="headings", 
                                        yscrollcommand=yscroll2.set, xscrollcommand=xscroll2.set,
                                        selectmode="extended", style="OtrosSpecials.Treeview")
                    yscroll2.config(command=tree2.yview)
                    xscroll2.config(command=tree2.xview)
                    
                    for c in cols2:
                        tree2.heading(c, text=c, anchor="center")
                        tree2.column(c, width=custom_widths_otros.get(c, 100), 
                                   anchor="center" if c in ("ID", "Cantidad", "Camera", "Time_Zone", "Marca") else "w")
                    
                    tree2.pack(side="left", expand=True, fill="both")
                    tree2.tag_configure("flagged", background="#f5a623", foreground="#111111")
                    tree2.tag_configure("done", background="#00c853", foreground="#111111")

                def cargar_lista():
                    """Cargar specials del otro supervisor filtrados por su turno"""
                    nonlocal data_cache_otros, row_ids_otros
                    
                    try:
                        shift_start = get_supervisor_shift_start(old_sup)
                        if not shift_start:
                            if USE_SHEET and sheet2:
                                data_cache_otros = [[f"{old_sup} no tiene shift activo"] + [""] * (len(cols2)-1)]
                                sheet2.set_sheet_data(data_cache_otros)
                                apply_sheet_widths_otros()
                                row_ids_otros.clear()
                            else:
                                tree2.delete(*tree2.get_children())
                                tree2.insert("", "end", values=[f"{old_sup} no tiene shift activo"] + [""] * (len(cols2)-1))
                            return
                        
                        # Verificar si tiene END SHIFT
                        shift_end = None
                        try:
                            conn_end = under_super.get_connection()
                            cur_end = conn_end.cursor()
                            cur_end.execute("""
                                SELECT e.FechaHora 
                                FROM Eventos e
                                INNER JOIN user u ON e.ID_Usuario = u.ID_Usuario
                                WHERE u.Nombre_Usuario = %s AND e.Nombre_Actividad = 'END SHIFT'
                                AND e.FechaHora > %s
                                ORDER BY e.FechaHora ASC
                                LIMIT 1
                            """, (old_sup, shift_start))
                            row_end = cur_end.fetchone()
                            shift_end = row_end[0] if row_end and row_end[0] else None
                            cur_end.close()
                            conn_end.close()
                        except Exception:
                            shift_end = None
                        
                        conn = under_super.get_connection()
                        cur = conn.cursor()
                        
                        if shift_end:
                            sql = """
                                SELECT ID_special, FechaHora, ID_Sitio, Nombre_Actividad, Cantidad, Camera,
                                       Descripcion, Usuario, Time_Zone, marked_status, marked_by
                                FROM specials
                                WHERE Supervisor = %s AND FechaHora >= %s AND FechaHora <= %s
                                ORDER BY FechaHora DESC
                            """
                            params = (old_sup, shift_start, shift_end)
                            title = f"Otros Specials - {old_sup} (Turno {shift_start.strftime('%H:%M')} a {shift_end.strftime('%H:%M')})"
                        else:
                            sql = """
                                SELECT ID_special, FechaHora, ID_Sitio, Nombre_Actividad, Cantidad, Camera,
                                       Descripcion, Usuario, Time_Zone, marked_status, marked_by
                                FROM specials
                                WHERE Supervisor = %s AND FechaHora >= %s
                                ORDER BY FechaHora DESC
                            """
                            params = (old_sup, shift_start)
                            title = f"Otros Specials - {old_sup} (Turno desde {shift_start.strftime('%H:%M')})"
                        
                        lst_win.title(title)
                        cur.execute(sql, params)
                        rows = cur.fetchall()
                        
                        # Resolver nombres de sitios y zonas horarias (igual que en load_specials principal)
                        time_zone_cache = {}
                        processed = []
                        
                        for r in rows:
                            rlist = list(r[:9])  # Primeras 9 columnas
                            id_sitio = rlist[2]
                            marked_status = r[9]
                            marked_by = r[10]
                            
                            # Resolver nombre de sitio y zona horaria
                            nombre_sitio = ""
                            tz = ""
                            if id_sitio is not None and str(id_sitio).strip() != "":
                                if id_sitio in time_zone_cache:
                                    nombre_sitio, tz = time_zone_cache[id_sitio]
                                else:
                                    try:
                                        cur.execute("SELECT Nombre_Sitio, Time_Zone FROM Sitios WHERE ID_Sitio = %s", (id_sitio,))
                                        sit = cur.fetchone()
                                        nombre_sitio = sit[0] if sit and sit[0] else ""
                                        tz = sit[1] if sit and len(sit) > 1 and sit[1] else ""
                                    except Exception as e:
                                        print(f"[DEBUG] error fetching site for ID_Sitio={id_sitio}: {e}")
                                        nombre_sitio = ""
                                        tz = ""
                                    time_zone_cache[id_sitio] = (nombre_sitio, tz)
                            
                            # Formato visual para ID_Sitio (ID + Nombre)
                            if id_sitio and nombre_sitio:
                                display_site = f"{id_sitio} {nombre_sitio}"
                            elif id_sitio:
                                display_site = str(id_sitio)
                            else:
                                display_site = nombre_sitio or ""
                            
                            rlist[2] = display_site
                            rlist[8] = tz
                            
                            # Formato visual para la marca
                            if marked_status == 'done':
                                mark_display = f"✅ Registrado ({marked_by})" if marked_by else "✅ Registrado"
                            elif marked_status == 'flagged':
                                mark_display = f"🔄 En Progreso ({marked_by})" if marked_by else "🔄 En Progreso"
                            else:
                                mark_display = ""
                            
                            rlist.append(mark_display)
                            processed.append({
                                'id': r[0],
                                'values': rlist,
                                'marked_status': marked_status
                            })
                        
                        cur.close()
                        conn.close()
                        
                        # Poblar UI
                        if USE_SHEET and sheet2:
                            # TKSHEET
                            if not processed:
                                data_cache_otros = [["No hay specials en este turno"] + [""] * (len(cols2)-1)]
                                sheet2.set_sheet_data(data_cache_otros)
                                apply_sheet_widths_otros()
                                row_ids_otros.clear()
                            else:
                                data_cache_otros = [item['values'] for item in processed]
                                row_ids_otros[:] = [item['id'] for item in processed]
                                sheet2.set_sheet_data(data_cache_otros)
                                
                                # Aplicar anchos personalizados
                                apply_sheet_widths_otros()
                                
                                # Limpiar todos los colores de fondo primero (para que los nuevos queden sin color)
                                sheet2.dehighlight_all()
                                
                                # Aplicar colores SOLO a los registros marcados
                                for idx, item in enumerate(processed):
                                    if item['marked_status'] == 'done':
                                        sheet2.highlight_rows([idx], bg="#00c853", fg="#111111")
                                    elif item['marked_status'] == 'flagged':
                                        sheet2.highlight_rows([idx], bg="#f5a623", fg="#111111")
                                    # Los registros sin marca (None/NULL) quedan SIN COLOR
                        else:
                            # TREEVIEW (fallback)
                            tree2.delete(*tree2.get_children())
                            if not processed:
                                tree2.insert("", "end", values=["No hay specials en este turno"] + [""] * (len(cols2)-1))
                            else:
                                for item in processed:
                                    values = [str(v) if v is not None else "" for v in item['values']]
                                    
                                    if item['marked_status'] == 'done':
                                        tag = "done"
                                    elif item['marked_status'] == 'flagged':
                                        tag = "flagged"
                                    else:
                                        tag = ""
                                    
                                    tree2.insert("", "end", iid=str(item['id']), values=values, 
                                               tags=(tag,) if tag else ())
                        
                        print(f"[DEBUG] Loaded {len(processed)} otros specials for {old_sup}")
                        
                    except Exception as e:
                        messagebox.showerror("Error", f"No se pudo cargar specials:\n{e}", parent=lst_win)
                        import traceback
                        traceback.print_exc()

                def tomar_specials():
                    """Tomar specials seleccionados para el supervisor actual"""
                    ids = []
                    
                    if USE_SHEET and sheet2:
                        # Obtener filas seleccionadas de tksheet
                        try:
                            selected_rows = sheet2.get_selected_rows()
                        except Exception:
                            selected_rows = []
                        
                        if not selected_rows:
                            messagebox.showwarning("Tomar Specials", "Selecciona uno o más registros.", parent=lst_win)
                            return
                        
                        # Obtener IDs de row_ids_otros
                        for row_idx in selected_rows:
                            try:
                                if row_idx < len(row_ids_otros):
                                    ids.append(row_ids_otros[row_idx])
                            except Exception:
                                pass
                    else:
                        # Treeview
                        sel = tree2.selection()
                        if not sel:
                            messagebox.showwarning("Tomar Specials", "Selecciona uno o más registros.", parent=lst_win)
                            return
                        
                        for item in sel:
                            try:
                                ids.append(int(item))
                            except Exception:
                                vals = tree2.item(item, 'values')
                                if vals:
                                    try:
                                        ids.append(int(vals[0]))
                                    except Exception:
                                        pass
                    
                    if not ids:
                        messagebox.showwarning("Tomar Specials", "No se pudieron leer los IDs.", parent=lst_win)
                        return
                    
                    if not messagebox.askyesno("Tomar Specials", 
                                               f"¿Reasignar {len(ids)} special(s) de {old_sup} a {current_username}?",
                                               parent=lst_win):
                        return
                    
                    try:
                        conn = under_super.get_connection()
                        cur = conn.cursor()
                        updated = 0
                        for sid in ids:
                            cur.execute("UPDATE specials SET Supervisor = %s WHERE ID_special = %s", (current_username, sid))
                            updated += cur.rowcount
                        conn.commit()
                        cur.close()
                        conn.close()
                        
                        messagebox.showinfo("Tomar Specials", f"✅ {updated} registro(s) reasignados a {current_username}", parent=lst_win)
                        cargar_lista()
                        load_specials()  # Refrescar ventana principal
                    except Exception as e:
                        messagebox.showerror("Error", f"No se pudo reasignar:\n{e}", parent=lst_win)
                        import traceback
                        traceback.print_exc()

                # Botonera
                btns2 = (UI.CTkFrame(lst_win, fg_color="#2c2f33") if UI is not None else tk.Frame(lst_win, bg="#2c2f33"))
                btns2.pack(fill="x", padx=12, pady=(0,10))
                
                if UI is not None:
                    UI.CTkButton(btns2, text="⟳ Refrescar", fg_color="#13988e", hover_color="#0f7f76",
                                command=cargar_lista).pack(side="left")
                    UI.CTkButton(btns2, text="📥 Tomar Specials", fg_color="#4a90e2", hover_color="#3a80d2",
                                command=tomar_specials).pack(side="left", padx=8)
                else:
                    tk.Button(btns2, text="⟳ Refrescar", bg="#13988e", fg="#fff", relief="flat",
                             command=cargar_lista).pack(side="left")
                    tk.Button(btns2, text="📥 Tomar Specials", bg="#4a90e2", fg="#fff", relief="flat",
                             command=tomar_specials).pack(side="left", padx=8)

                _register_singleton(key, lst_win)
                cargar_lista()

            if UI is not None:
                UI.CTkButton(sel_win, text="Aceptar", fg_color="#13988e", hover_color="#0f7f76",
                            command=abrir_lista_specials).pack(pady=8)
            else:
                tk.Button(sel_win, text="Aceptar", bg="#13988e", fg="#fff", relief="flat",
                         command=abrir_lista_specials).pack(pady=8)

        # ============= UI CONTROLS =============
        
        # Botonera principal
        btn_frame = (UI.CTkFrame(top_win, fg_color="#2c2f33") if UI is not None else tk.Frame(top_win, bg="#2c2f33"))
        btn_frame.pack(fill="x", padx=10, pady=(0,8))
        
        if UI is not None:
            UI.CTkButton(btn_frame, text="⟳ Refrescar Manual", fg_color="#13988e", hover_color="#0f7f76", 
                        command=load_specials).pack(side="left")
            UI.CTkButton(btn_frame, text="📋 Copiar", fg_color="#3b4754", hover_color="#4a5560", 
                        command=copy_to_clipboard).pack(side="left", padx=(8,0))
            UI.CTkCheckBox(btn_frame, text="Auto-refresh (2 min)", variable=auto_refresh_active, 
                          fg_color="#4a90e2", text_color="#e0e0e0", command=toggle_auto_refresh).pack(side="left", padx=(12,0))
        else:
            tk.Button(btn_frame, text="⟳ Refrescar Manual", command=load_specials, bg="#13988e", fg="#fff", relief="flat").pack(side="left")
            tk.Button(btn_frame, text="📋 Copiar", command=copy_to_clipboard, bg="#3b4754", fg="#e0e0e0", relief="flat").pack(side="left", padx=(8,0))
            tk.Checkbutton(btn_frame, text="Auto-refresh (2 min)", variable=auto_refresh_active, command=toggle_auto_refresh,
                          bg="#2c2f33", fg="#e0e0e0", selectcolor="#2c2f33").pack(side="left", padx=(12,0))

        # Controles de marcas
        marks_frame = (UI.CTkFrame(top_win, fg_color="#2c2f33") if UI is not None else tk.Frame(top_win, bg="#2c2f33"))
        marks_frame.pack(fill="x", padx=10, pady=(0,8))
        
        if UI is not None:
            UI.CTkButton(marks_frame, text="❌ Desmarcar", fg_color="#3b4754", hover_color="#4a5560", 
                        command=unmark_selected).pack(side="left", padx=(0,8))
            UI.CTkButton(marks_frame, text="🗑️  Limpiar todo", fg_color="#d32f2f", hover_color="#b71c1c", 
                        command=clear_marks).pack(side="left", padx=(0,8))
            UI.CTkButton(marks_frame, text="📋 Otros Specials", fg_color="#4a5f7a", hover_color="#3a4f6a", 
                        command=lambda: open_otros_specials(username)).pack(side="left", padx=(0,8))
        else:
            tk.Button(marks_frame, text="❌ Desmarcar", command=unmark_selected, 
                     bg="#3b4754", fg="#e0e0e0", relief="flat").pack(side="left", padx=(0,8))
            tk.Button(marks_frame, text="🗑️  Limpiar todo", command=clear_marks, 
                     bg="#d32f2f", fg="#fff", relief="flat").pack(side="left", padx=(0,8))
            tk.Button(marks_frame, text="📋 Otros Specials", command=lambda: open_otros_specials(username), 
                     bg="#4a5f7a", fg="#fff", relief="flat").pack(side="left", padx=(0,8))

        # Info box
        info_frame = (UI.CTkFrame(top_win, fg_color="#1a1d21") if UI is not None else tk.Frame(top_win, bg="#1a1d21"))
        info_frame.pack(fill="x", padx=10, pady=(0,10))
        
        info_text = "💡 Haz clic derecho en una fila para marcar como Registrado o En Progreso. Auto-refresh cada 2 minutos."
        if UI is not None:
            UI.CTkLabel(info_frame, text=info_text, text_color="#a3c9f9", 
                       font=("Segoe UI", 9, "italic")).pack(pady=6)
        else:
            tk.Label(info_frame, text=info_text, bg="#1a1d21", fg="#a3c9f9",
                    font=("Segoe UI", 9, "italic")).pack(pady=6)

        # Atajos de teclado y menú contextual
        if tree:
            tree.bind("<Control-c>", copy_to_clipboard)
            tree.bind("<Control-C>", copy_to_clipboard)
            tree.bind("<Button-3>", show_context_menu)  # Menú contextual
            tree.bind("<Double-1>", lambda e: mark_as_done())  # Doble-click marca como "Registrado"
        elif sheet:
            # tksheet ya tiene Ctrl+C integrado
            sheet.bind("<Button-3>", show_context_menu)  # Menú contextual
            def on_sheet_double_click(event):
                mark_as_done()
            sheet.bind("<Double-Button-1>", on_sheet_double_click)

        # Cleanup al cerrar
        def on_close():
            nonlocal refresh_job
            if refresh_job:
                top_win.after_cancel(refresh_job)
            top_win.destroy()
        
        top_win.protocol("WM_DELETE_WINDOW", on_close)

        # Registro singleton
        _register_singleton('specials', top_win)
        
        # Carga inicial
        load_specials()
        
        return top_win

    except Exception as e:
        messagebox.showerror("Error", f"No se pudo abrir la ventana:\n{e}")
        import traceback
        traceback.print_exc()
        return None


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
        conn = under_super.get_connection()
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
        conn = under_super.get_connection()
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
            conn = under_super.get_connection()
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
                    conn = under_super.get_connection()
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
                    conn = under_super.get_connection()
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
                    conn = under_super.get_connection()
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



# -----------------------------
# Ventana de edición de roles
# -----------------------------
def open_rol_window():
    import json
    from pathlib import Path
    ex = _focus_singleton('roles')
    if ex:
        return ex
    rol_win = tk.Toplevel()
    rol_win.title("Edición de Roles")
    rol_win.configure(bg="#2c2f33")
    rol_win.geometry("390x300")
    rol_win.resizable(False, False)

    tk.Label(
        rol_win, 
        text="Editar Roles", 
        bg="#2c2f33", fg="#a3c9f9", 
        font=("Segoe UI", 12, "bold")
    ).pack(pady=10)

    # --- Cargar configuración desde JSON ---
    try:
        with open(under_super.CONFIG_PATH, "r", encoding="utf-8") as f:
            role_permissions = json.load(f)
    except Exception as e:
        messagebox.showerror("Error", f"No se pudo leer el archivo JSON:\n{e}", parent=rol_win)
        rol_win.destroy()
        return

    # --- Selección de Rol ---
    options = list(role_permissions.keys())
    selected_option = tk.StringVar(value=options[0])

    combo = ttk.Combobox(
        rol_win, textvariable=selected_option, 
        values=options, state="readonly"
    )
    combo.pack(pady=10)

    # --- Marco principal ---
    frame = tk.Frame(rol_win, bg="#2c2f33")
    frame.pack(pady=10, expand=True, fill="both")

    # Listbox de permisos asignados
    tk.Label(frame, text="Permisos Asignados", 
             bg="#2c2f33", fg="white").grid(row=0, column=0, padx=10)
    assigned_box = tk.Listbox(frame, height=8, width=20)
    assigned_box.grid(row=1, column=0, padx=10)

    # Botones de acción
    action_frame = tk.Frame(frame, bg="#2c2f33")
    action_frame.grid(row=1, column=1, padx=10)
    add_btn = tk.Button(action_frame, text="➕ Agregar", width=10)
    add_btn.pack(pady=5)
    remove_btn = tk.Button(action_frame, text="➖ Quitar", width=10)
    remove_btn.pack(pady=5)

    # Listbox de permisos disponibles
    tk.Label(frame, text="Permisos Disponibles", 
             bg="#2c2f33", fg="white").grid(row=0, column=2, padx=10)
    available_box = tk.Listbox(frame, height=8, width=20)
    available_box.grid(row=1, column=2, padx=10)

    # --- Funciones ---
    def update_permissions(event=None):
        assigned_box.delete(0, tk.END)
        available_box.delete(0, tk.END)

        role = selected_option.get()
        permisos_asignados = set(role_permissions.get(role, []))
        todos_permisos = set(sum(role_permissions.values(), []))

        # Llenar listboxes
        for p in permisos_asignados:
            assigned_box.insert(tk.END, p)
        for p in sorted(todos_permisos - permisos_asignados):
            available_box.insert(tk.END, p)

    def add_permission():
        sel = available_box.curselection()
        if not sel: return
        permiso = available_box.get(sel[0])
        available_box.delete(sel[0])
        assigned_box.insert(tk.END, permiso)

    def remove_permission():
        sel = assigned_box.curselection()
        if not sel: return
        permiso = assigned_box.get(sel[0])
        assigned_box.delete(sel[0])
        available_box.insert(tk.END, permiso)

    def save_changes():
        role = selected_option.get()
        nuevos = [assigned_box.get(i) for i in range(assigned_box.size())]

        # 🔹 Actualizar en memoria
        role_permissions[role] = nuevos

        # 🔹 Guardar en el JSON
        try:
            with open(under_super.CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump(role_permissions, f, indent=4, ensure_ascii=False)
            messagebox.showinfo("Éxito", f"Permisos de {role} guardados en roles_config.json", parent=rol_win)
            print(f"✅ Permisos actualizados para {role}: {nuevos}")
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo guardar cambios:\n{e}", parent=rol_win)

    # Bind
    combo.bind("<<ComboboxSelected>>", update_permissions)
    add_btn.config(command=add_permission)
    remove_btn.config(command=remove_permission)

    # Botón Guardar
    tk.Button(
        rol_win, text="Guardar", command=save_changes,
        bg="#4caf50", fg="white", relief="flat"
    ).pack(pady=10)

    # Inicializar
    update_permissions()
    _register_singleton('roles', rol_win)

def open_view_window():
    """
    Ventana para ver y borrar registros de tablas Site(s), Usuarios, Actividades, Covers, Sesiones y Estaciones.
    - Intenta tablas: "Sites", "Sitios", "Usuarios", "Actividades", "Covers", "Sesiones", "Estaciones"
    - Crea un Notebook con una pestaña por tabla válida.
    - Cada pestaña tiene Treeview + botones Refrescar / Borrar seleccionado.
    """
    ex = _focus_singleton('view')
    if ex:
        return ex

    def sanitize_col_id(name, used):
        # reemplaza cualquier caracter no alfanumérico por underscore
        cid = re.sub(r'[^0-9A-Za-z_]', '_', str(name))
        # si empieza por número, antepone _
        if re.match(r'^\d', cid):
            cid = "_" + cid
        base = cid
        i = 1
        while cid in used or cid == "":
            cid = f"{base}_{i}"
            i += 1
        used.add(cid)
        return cid

    def guess_pk(col_names):
        # heurística para detectar la columna PK más probable
        candidates = [c for c in col_names if c.lower() in ("id", "id_") or c.lower().endswith("_id") or c.lower().startswith("id_")]
        if candidates:
            return candidates[0]
        # también buscar 'ID' anywhere
        for c in col_names:
            if 'id' in c.lower():
                return c
        # fallback: primera columna
        return col_names[0] if col_names else None

    view_win = tk.Toplevel()
    view_win.title("Vista de Tablas (Sitios / Usuarios / Actividades / Covers / Sesiones / Estaciones / Specials / Covers)")
    view_win.geometry("1000x560")
    view_win.configure(bg="#2c2f33")

    _register_singleton('view', view_win)
    notebook = ttk.Notebook(view_win)
    notebook.pack(fill="both", expand=True, padx=8, pady=8)

    # tablas a intentar (intenta en orden; si no existe, la salta)
    candidate_tables = ["Sitios", "user", "Actividades", "Covers", "Sesiones", "Estaciones", "Specials"]

    # almacenará metadata por tabla: { tabla_name: { 'frame':..., 'tree':..., 'col_names':..., 'pk':... } }
    tabs = {}

    def load_table(tabla):
        """(Re)Carga los datos de la tabla indicada desde MySQL y actualiza su Treeview."""
        try:
            # Conexión MySQL (usa tu módulo under_super)
            conn = under_super.get_connection()
            cur = conn.cursor()

            # En MySQL no se usan corchetes [tabla]
            query = f"SELECT * FROM {tabla}"
            cur.execute(query)
            rows = cur.fetchall()

            # Obtener nombres de columnas
            col_names = [desc[0] for desc in cur.description]

            # Sanitizar identificadores
            used = set()
            col_ids = [sanitize_col_id(n, used) for n in col_names]

            meta = tabs[tabla]
            tree = meta['tree']

            # Limpiar el TreeView y configurar columnas
            tree.delete(*tree.get_children())
            tree["columns"] = col_ids

            for cid, cname in zip(col_ids, col_names):
                tree.heading(cid, text=cname)
                tree.column(cid, width=160, anchor="w", stretch=True)

            # Insertar filas en el TreeView
            for row in rows:
                values = []
                for v in row:
                    if v is None:
                        values.append("")
                    else:
                        try:
                            # Convertir tipos binarios o raros a texto
                            if isinstance(v, (bytes, bytearray, memoryview)):
                                values.append(v.hex())
                            else:
                                values.append(str(v))
                        except Exception:
                            values.append(repr(v))
                tree.insert("", "end", values=values)

            # Actualizar metadatos
            meta['col_names'] = col_names
            meta['col_ids'] = col_ids
            meta['pk'] = guess_pk(col_names)

            # Cerrar conexión
            cur.close()
            conn.close()
            return True

        except Exception as e:
            print(f"[ERROR] load_table({tabla}): {e}")
            import traceback
            traceback.print_exc()
            return False

    def delete_selected(tabla):
        meta = tabs.get(tabla)
        if not meta:
            return
        tree = meta['tree']
        pk_name = meta.get('pk')
        col_names = meta.get('col_names', [])
        if not pk_name or pk_name not in col_names:
            messagebox.showwarning("No PK", "No se pudo determinar la columna primaria para esta tabla.", parent=view_win)
            return

        sel = tree.selection()
        if not sel:
            messagebox.showwarning("Atención", "Seleccione un registro para borrar.", parent=view_win)
            return

        # confirmación
        if not messagebox.askyesno("Confirmar", "¿Mover el registro a Papelera?", parent=view_win):
            return

        try:
            # obtener índice de la PK para extraer el valor del item seleccionado
            pk_idx = col_names.index(pk_name)
            item = tree.item(sel[0])
            values = item.get("values", [])
            pk_value = values[pk_idx] if pk_idx < len(values) else None
            if pk_value is None:
                messagebox.showerror("Error", "No se pudo leer el valor de la PK.", parent=view_win)
                return

            # Usar sistema de backup seguro
            ok = safe_delete(
                table_name=tabla,
                pk_column=pk_name,
                pk_value=pk_value,
                deleted_by="System",
                reason=f"Eliminado desde view_table ({tabla})"
            )
            
            if ok:
                tree.delete(sel[0])
                messagebox.showinfo("Éxito", "✅ Registro movido a Papelera.", parent=view_win)
            else:
                messagebox.showerror("Error", "No se pudo mover el registro a Papelera", parent=view_win)
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo eliminar el registro:\n{e}", parent=view_win)
            traceback.print_exc()

    def edit_selected(tabla):
        meta = tabs.get(tabla)
        if not meta:
            return
        tree = meta['tree']
        pk_name = meta.get('pk')
        col_names = meta.get('col_names', [])
        if not pk_name or pk_name not in col_names:
            messagebox.showwarning("No PK", "No se pudo determinar la columna primaria para esta tabla.", parent=view_win)
            return

        sel = tree.selection()
        if not sel:
            messagebox.showwarning("Atención", "Seleccione un registro para editar.", parent=view_win)
            return

        # obtener índice de la PK para extraer el valor del item seleccionado
        pk_idx = col_names.index(pk_name)
        item = tree.item(sel[0])
        values = item.get("values", [])
        if not values or pk_idx >= len(values):
            messagebox.showerror("Error", "No se pudo leer el valor de la PK.", parent=view_win)
            return
        pk_value = values[pk_idx]

        # Ventana de edición
        edit_win = tk.Toplevel(view_win)
        edit_win.title(f"Editar registro de {tabla}")
        edit_win.configure(bg="#2c2f33")
        edit_win.geometry("380x{}".format(60 + 36 * len(col_names)))
        edit_win.resizable(False, False)

        entries = {}
        for i, cname in enumerate(col_names):
            tk.Label(edit_win, text=cname, bg="#2c2f33", fg="#a3c9f9", font=("Segoe UI", 13, "bold")).grid(row=i, column=0, sticky="w", padx=10, pady=6)
            e = tk.Entry(edit_win, width=38)
            e.grid(row=i, column=1, padx=10, pady=6)
            if i < len(values):
                e.insert(0, values[i])
            # Si es la PK, deshabilitar edición
            if cname == pk_name:
                e.config(state="readonly")
            entries[cname] = e

        def save_changes():
            new_values = {c: entries[c].get() for c in col_names}
            try:
                conn = under_super.get_connection()
                cur = conn.cursor()

                # Generar SET dinámico para todas las columnas excepto la PK
                set_clause = ", ".join(f"`{c}` = %s" for c in col_names if c != pk_name)
                sql = f"UPDATE `{tabla}` SET {set_clause} WHERE `{pk_name}` = %s"

                # Construir parámetros (valores nuevos + valor PK)
                params = []
                for c in col_names:
                    if c != pk_name:
                        value = new_values[c]
                        # 🔹 Si la columna es 'User_Logged' y viene vacía, enviamos None para evitar error FK
                        if c == "User_Logged" and (value is None or value == ""):
                            value = None
                        params.append(value)
                params.append(pk_value)

                cur.execute(sql, params)
                conn.commit()
                cur.close()
                conn.close()

                # Refrescar la tabla
                load_table(tabla)
                edit_win.destroy()
                messagebox.showinfo("Éxito", "Registro actualizado correctamente.", parent=view_win)
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo actualizar el registro:\n{e}", parent=edit_win)
                traceback.print_exc()

        tk.Button(edit_win, text="Guardar", bg="#4aa3ff", fg="white", font=("Segoe UI", 10, "bold"), command=save_changes).grid(row=len(col_names), column=0, columnspan=2, pady=14)

    # Construir pestañas para tablas existentes
    for tabla in candidate_tables:
        # crear frame y treeview vacíos primero
        frame = tk.Frame(notebook, bg="#2c2f33")
        # widget contenedor para controles arriba y tree abajo
        topbar = tk.Frame(frame, bg="#2c2f33")
        topbar.pack(fill="x", pady=(6,0), padx=6)

        refresh_btn = tk.Button(topbar, text="🔁 Refrescar", bg="#4aa3ff", fg="white")
        refresh_btn.pack(side="left", padx=4)

        delete_btn = tk.Button(topbar, text="🗑️ Borrar seleccionado", bg="#d9534f", fg="white")
        delete_btn.pack(side="left", padx=4)

        edit_btn = tk.Button(topbar, text="✏️ Editar seleccionado", bg="#f0ad4e", fg="white")
        edit_btn.pack(side="left", padx=4)

        # placeholder label para mostrar tabla actual en topbar
        lbl = tk.Label(topbar, text=tabla, bg="#2c2f33", fg="white", font=("Segoe UI", 10, "bold"))
        lbl.pack(side="right", padx=6)

        tree = ttk.Treeview(frame, show="headings")
        vsb = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
        hsb = ttk.Scrollbar(frame, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        tree.pack(fill="both", expand=True, side="left", padx=(6,0), pady=6)
        vsb.pack(fill="y", side="left", pady=6)
        hsb.pack(fill="x", side="bottom", padx=6)

        # almacenar metadata
        tabs[tabla] = {
            "frame": frame,
            "tree": tree,
            "refresh_btn": refresh_btn,
            "delete_btn": delete_btn,
            "label": lbl,
            "col_names": [],
            "col_ids": [],
            "pk": None
        }

        # intentamos cargar datos; si falla (tabla no existe) no añadimos pestaña
        ok = load_table(tabla)
        if not ok:
            # limpiar widgets creados y no agregar la pestaña
            frame.destroy()
            tabs.pop(tabla, None)
            continue

        # enlazar botones ahora que la tabla está cargada
        refresh_btn.config(command=lambda t=tabla: load_table(t))
        delete_btn.config(command=lambda t=tabla: delete_selected(t))
        edit_btn.config(command=lambda t=tabla: edit_selected(t))
        

        notebook.add(frame, text=tabla)

    if not tabs:
        messagebox.showwarning("Sin tablas", "No se encontraron las tablas Sites/Sitios/Usuarios/Actividades en la base.", parent=view_win)
        view_win.destroy()
        return

    # lista de tablas cargadas
    print("[open_view_window] pestañas cargadas:", list(tabs.keys()))

def get_station_status(tree=None):
    try:
        conn = under_super.get_connection()
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
        conn = under_super.get_connection()
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
        conn = under_super.get_connection()
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
        conn = under_super.get_connection(); cur = conn.cursor()
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
            conn = under_super.get_connection()
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
        conn = under_super.get_connection()
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
        conn = under_super.get_connection()
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
        conn = under_super.get_connection()
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
            conn = under_super.get_connection()
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
            conn = under_super.get_connection()
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