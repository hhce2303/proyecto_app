import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk
from PIL import ImageDraw
from pathlib import Path
import backend_super
import main_super  # módulo principal
from datetime import datetime
import under_super
now = datetime.now()

# ---- Cache global para recursos de Login (evita recargar imagen desde red en cada logout) ----
_LOGIN_BG_CACHE = {
    "image": None,  # PIL.Image
    "photo": None,  # ImageTk.PhotoImage
}
_LOGIN_BG_SIZE = (500, 350)
_LOGIN_BG_PATH = Path(r"\\192.168.7.12\Data SIG\Central Station SLC-COLOMBIA\1. Daily Logs - Operators\DataBase\icons\fondo.jpg")

# --- Botón de Logout ---
def do_logout(session_id, station, root):
    """Cierra sesión, destruye la ventana actual y muestra el login una sola vez.

    También restablece tk._default_root para evitar que nuevas ventanas se adjunten
    a un root destruido (causa común de errores 'invalid command name' en callbacks).
    """
    try:
        conn = under_super.get_connection()
        cursor = conn.cursor()

        # 🔹 Fecha/hora actual para Log_Out
        log_out_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[DEBUG] log_out_time = {log_out_time}")
        print(f"[DEBUG] session_id   = {session_id}")

        # 🔹 Ejecutar el UPDATE
        print("[DEBUG] Ejecutando UPDATE Sesiones...")
        cursor.execute(
            """
            UPDATE Sesiones
            SET Log_Out = %s, Is_Active = '0'
            WHERE ID_Sesion = %s AND Is_Active = '-1'
            """,
            (log_out_time, int(session_id))
        )
        print(f"[DEBUG] Filas afectadas: {cursor.rowcount}")
        print("[DEBUG] UPDATE Sesiones OK ✅")

        # 🔹 Liberar estación (ahora usando Station_Number)
        cursor.execute(
            """
            UPDATE Estaciones
            SET User_Logged = NULL
            WHERE Station_Number=%s
            """,
            (station,)
        )
        print("[DEBUG] Estación liberada en tabla Estaciones")

        conn.commit()
        conn.close()
    except Exception as e:
        messagebox.showerror("Error", f"No se pudo cerrar sesión correctamente:\n{e}")
        print(f"[DEBUG] ERROR logout: {e}")

    # Cerrar ventana actual de forma segura (si existe)
    try:
        if root is not None and hasattr(root, 'winfo_exists') and root.winfo_exists():
            try:
                root.grab_release()
            except Exception:
                pass
            root.destroy()
    except tk.TclError:
        # La ventana ya fue destruida o no es válida
        pass

    # Mostrar pantalla de login (una sola vez)
    try:
        # Forzar nueva raíz limpia para garantizar que mainloop arranque
        tk._default_root = None
    except Exception:
        pass
    show_login()

def show_login():
    # Intentar usar CustomTkinter
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

    # Reusar root existente si aplica; de lo contrario, crearlo
    win = getattr(tk, '_default_root', None)
    try:
        exists = bool(win and win.winfo_exists())
    except Exception:
        exists = False
    created_new_root = False
    if not exists:
        win = (UI.CTk() if UI is not None else tk.Tk())
        created_new_root = True
    else:
        # Limpiar contenido y mostrar
        for child in win.winfo_children():
            try:
                child.destroy()
            except Exception:
                pass
        try:
            # Asegurar que la ventana vuelva a mostrarse y al frente
            win.deiconify()
            win.update_idletasks()
            try:
                win.lift()
            except Exception:
                pass
            try:
                # traer al frente de forma temporal
                win.attributes('-topmost', True)
                win.after(150, lambda: win.attributes('-topmost', False))
            except Exception:
                pass
        except Exception:
            pass
    win.title("Login")
    win.geometry("500x350")
    win.resizable(False, False)

    # --- Fondo con imagen (cacheado) ---
    # Cargar desde cache si ya lo hicimos antes; evita esperas por red + resize en cada logout
    try:
        if _LOGIN_BG_CACHE["image"] is None:
            if _LOGIN_BG_PATH.exists():
                img = Image.open(_LOGIN_BG_PATH).resize(_LOGIN_BG_SIZE, Image.Resampling.LANCZOS)
                _LOGIN_BG_CACHE["image"] = img
            else:
                _LOGIN_BG_CACHE["image"] = None
    except Exception:
        _LOGIN_BG_CACHE["image"] = None

    # Dibujar fondo: CTkLabel con CTkImage si está disponible; si no, usar Canvas clásico
    if UI is not None and _LOGIN_BG_CACHE["image"] is not None:
        try:
            # Crear una copia con overlay oscuro detrás del formulario (simula translúcido)
            try:
                base_img = _LOGIN_BG_CACHE["image"].copy().convert("RGBA")
                overlay = Image.new("RGBA", _LOGIN_BG_SIZE, (0, 0, 0, 0))
                draw = ImageDraw.Draw(overlay)
                # Coordenadas centradas para el frame (mismo tamaño 350x260) con margen extra
                w, h = _LOGIN_BG_SIZE
                fw, fh = 350, 260
                margin = 10
                x1 = (w - fw) // 2 - margin
                y1 = (h - fh) // 2 - margin
                x2 = x1 + fw + margin * 2
                y2 = y1 + fh + margin * 2
                # Hacer el overlay más claro para que se vea mejor el fondo
                draw.rectangle([x1, y1, x2, y2], fill=(0, 0, 0, 80))
                composed = Image.alpha_composite(base_img, overlay)
            except Exception:
                composed = _LOGIN_BG_CACHE["image"]

            bg_ctk_image = UI.CTkImage(light_image=composed, dark_image=composed, size=_LOGIN_BG_SIZE)
            win._bg_ctk_image = bg_ctk_image  # strong ref
            bg_label = UI.CTkLabel(win, image=bg_ctk_image, text="")
            bg_label.place(x=0, y=0, relwidth=1, relheight=1)
            win._bg_label = bg_label
        except Exception:
            # Fallback al Canvas clásico si algo falla
            canvas = tk.Canvas(win, width=500, height=600, highlightthickness=0)
            canvas.pack(fill="both", expand=True)
            try:
                bg_photo = ImageTk.PhotoImage(_LOGIN_BG_CACHE["image"]) if _LOGIN_BG_CACHE["image"] is not None else None
            except Exception:
                bg_photo = None
            if bg_photo is not None:
                win._bg_photo = bg_photo
                canvas.create_image(0, 0, anchor="nw", image=bg_photo)
            else:
                canvas.configure(bg="#1c1c1c")
            try:
                canvas.focus_set()
            except Exception:
                pass
            win._bg_canvas = canvas
    else:
        canvas = tk.Canvas(win, width=500, height=600, highlightthickness=0)
        canvas.pack(fill="both", expand=True)
        try:
            bg_photo = ImageTk.PhotoImage(_LOGIN_BG_CACHE["image"]) if _LOGIN_BG_CACHE["image"] is not None else None
        except Exception:
            bg_photo = None
        if bg_photo is not None:
            win._bg_photo = bg_photo
            canvas.create_image(0, 0, anchor="nw", image=bg_photo)
        else:
            canvas.configure(bg="#1c1c1c")
        try:
            canvas.focus_set()
        except Exception:
            pass
        win._bg_canvas = canvas
        # Dibujar overlay translúcido (simulado con stipple) detrás del formulario para mejorar legibilidad
        try:
            fw, fh = 350, 260
            margin = 10
            x1 = (500 - fw) // 2 - margin
            y1 = (350 - fh) // 2 - margin
            x2 = x1 + fw + margin * 2
            y2 = y1 + fh + margin * 2
            # Usar una trama más clara para que se vea más el fondo
            canvas.create_rectangle(x1, y1, x2, y2, fill="#000000", outline="", stipple="gray25")
        except Exception:
            pass

    # --- Frame para widgets ---
    if UI is not None:
        # En CTk, intentar frame "transparente" para dejar ver más el fondo; fallback a un color más claro
        try:
            frame = UI.CTkFrame(win, fg_color="transparent", width=350, height=260)
        except Exception:
            frame = UI.CTkFrame(win, fg_color="#15191e", width=350, height=260)
        frame.place(relx=0.5, rely=0.5, anchor="center")
    else:
        frame = tk.Frame(win, bg="#1c1c1c")
        frame.place(relx=0.5, rely=0.5, anchor="center", width=350, height=260)

    # Título
    if UI is not None:
        UI.CTkLabel(frame, text="Iniciar Sesión", text_color="#4aa3ff", font=("Segoe UI", 18, "bold")).pack(pady=(9, 12))
    else:
        tk.Label(frame, text="Iniciar Sesión", bg="#1c1c1c", fg="#4aa3ff",
                 font=("Segoe UI", 18, "bold")).pack(pady=(9, 12))

    # Usuario
    if UI is not None:
        UI.CTkLabel(frame, text="Usuario:", text_color="white", font=("Segoe UI", 11)).pack(anchor="w", padx=20)
        username_entry = UI.CTkEntry(frame, width=240)
        username_entry.pack(pady=2, padx=20)
    else:
        tk.Label(frame, text="Usuario:", bg="#1c1c1c", fg="white", font=("Segoe UI", 9)).pack(anchor="w", padx=20)
        username_entry = ttk.Entry(frame, width=30)
        username_entry.pack(pady=2, padx=20)

    # Contraseña
    if UI is not None:
        UI.CTkLabel(frame, text="Contraseña:", text_color="white", font=("Segoe UI", 11)).pack(anchor="w", padx=20)
        password_entry = UI.CTkEntry(frame, show="*", width=240)
        password_entry.pack(pady=2, padx=20)
    else:
        tk.Label(frame, text="Contraseña:", bg="#1c1c1c", fg="white", font=("Segoe UI", 9)).pack(anchor="w", padx=20)
        password_entry = ttk.Entry(frame, show="*", width=30)
        password_entry.pack(pady=2, padx=20)

    # Estacion
    if UI is not None:
        UI.CTkLabel(frame, text="Estacion:", text_color="white", font=("Segoe UI", 11)).pack(anchor="w", padx=20)
        station_entry = UI.CTkEntry(frame, width=240)
        station_entry.pack(pady=2, padx=20)
    else:
        tk.Label(frame, text="Estacion:", bg="#1c1c1c", fg="white", font=("Segoe UI", 9)).pack(anchor="w", padx=20)
        station_entry = ttk.Entry(frame, width=30)
        station_entry.pack(pady=2, padx=20)


    def do_login():
        username = username_entry.get()
        password = password_entry.get()
        station_input = station_entry.get()

        # Validar estación
        if not station_input.isdigit():
            messagebox.showerror("Error", "Debes ingresar un número de estación válido")
            return
        station = int(station_input)  # Número lógico de estación

        print(f"[DEBUG] username: {username} ({type(username)})")
        print(f"[DEBUG] password: {password} ({type(password)})")
        print(f"[DEBUG] station: {station} ({type(station)})")

        try:
            conn = under_super.get_connection()
            cursor = conn.cursor()

            # Validar usuario
            cursor.execute(
                    "SELECT Contraseña, Rol FROM user WHERE Nombre_Usuario=%s",
                (username,)
            )
            result = cursor.fetchone()
            print(f"[DEBUG] SELECT user result: {result}")

            if not result:
                messagebox.showerror("Error", "Usuario no encontrado")
                conn.close()
                return

            db_password, role = result
            if db_password != password:
                messagebox.showerror("Error", "Contraseña incorrecta")
                conn.close()
                return

            # Insertar nueva sesión
            cursor.execute("""
                INSERT INTO Sesiones (Nombre_Usuario, Stations_ID, Login_Time, Is_Active)
                VALUES (%s, %s, %s, %s)
            """, (username, station, datetime.now(), "-1"))
            print("[DEBUG] INSERT Sesiones ejecutado")

            # 🔹 Obtener último ID insertado
            cursor.execute("SELECT LAST_INSERT_ID()")
            session_id = cursor.fetchone()[0]
            print(f"[DEBUG] Nuevo Session_ID generado: {session_id}")

            # 🔹 Verificar si la estación ya está ocupada
            cursor.execute("SELECT User_Logged FROM Estaciones WHERE Station_Number=%s", (station,))
            row = cursor.fetchone()

            if row and row[0]:  # Si ya hay alguien logeado
                print(f"❌ La estación {station} ya está siendo usada por {row[0]}")
                return

            # 🔹 Actualizar estación si está libre
            cursor.execute("""INSERT INTO estaciones (User_Logged, Station_Number)
            VALUES (%s, %s)
            """, (username, station))

            print("[DEBUG] INSERT Estaciones ejecutado")
            conn.commit()
            conn.close()

            backend_super.prompt_exit_active_cover(username, win)

            # Mensaje de bienvenida
            messagebox.showinfo("Login", f"Bienvenido {username} ({role})")
            # No destruir el root: solo ocultarlo; main window será un Toplevel
            try:
                win.withdraw()
            except Exception:
                pass
            
            # ⭐ VERIFICAR ROL: Si es Operador, ir directamente a open_hybrid_events
            if role == "Operador":
                print(f"[DEBUG] Rol Operador detectado, abriendo open_hybrid_events directamente")
                backend_super.open_hybrid_events(username, session_id, station, win)
            elif role == "Supervisor":
                # Para Supervisor, abrir ventana de hybrid events supervisor
                print(f"[DEBUG] Rol Supervisor detectado, abriendo hybrid events supervisor")
                backend_super.open_hybrid_events_supervisor(username=username, root=win)
            elif role == "Lead Supervisor":
                # Para Lead Supervisor, abrir ventana específica con permisos de eliminación
                print(f"[DEBUG] Rol Lead Supervisor detectado, abriendo hybrid events lead supervisor")
                backend_super.open_hybrid_events_lead_supervisor(username=username, root=win)
            else:
                # Para otros roles, abrir menú principal
                print(f"[DEBUG] Rol {role} detectado, abriendo menú principal")
                main_super.open_main_window(username, station, role, session_id)

        except Exception as e:
            messagebox.showerror("Error", f"Fallo en la conexión a la base de datos:\n{e}")
            print(f"[DEBUG] ERROR: {e}")

    if UI is not None:
        login_btn = UI.CTkButton(frame, text="Ingresar", command=do_login,
                                 fg_color="#2b2b2b", hover_color="#4aa3ff", text_color="white")
        login_btn.pack(pady=15)
    else:
        # --- Botón personalizado con hover ---
        def on_enter(e):
            login_btn.config(bg="#4aa3ff", fg="white")

        def on_leave(e):
            login_btn.config(bg="#2b2b2b", fg="white")

        login_btn = tk.Button(frame, text="Ingresar", command=do_login,
                            bg="#2b2b2b", fg="white", font=("Segoe UI", 11, "bold"),
                            relief="flat", padx=20, pady=5)
        login_btn.pack(pady=15)
        login_btn.bind("<Enter>", on_enter)
        login_btn.bind("<Leave>", on_leave)

    # Enter para login
    win.bind("<Return>", lambda event: do_login())

    # Solo iniciar mainloop si acabamos de crear el root
    if created_new_root:
        win.mainloop()


if __name__ == "__main__":
    show_login()


# === Programmatic helpers for cover flow ===
def logout_silent(session_id, station):
    """Logout without showing login UI; updates Sesiones and frees Estaciones."""
    try:
        conn = under_super.get_connection()
        cursor = conn.cursor()
        log_out_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute(
            """
            UPDATE Sesiones
            SET Log_Out = %s, Is_Active = '0'
            WHERE ID_Sesion = %s AND Is_Active = '-1'
            """,
            (log_out_time, int(session_id))
        )
        cursor.execute(
            """
            UPDATE Estaciones
            SET User_Logged = NULL
            WHERE Station_Number=%s
            """,
            (station,)
        )
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"[ERROR] logout_silent: {e}")
        return False


def auto_login(username, station, password="1234", parent=None, silent=True):
    """Perform login programmatically and open main window, without showing login UI.

    Returns (ok, session_id, role) and opens main_super.open_main_window on success.
    """
    try:
        # Validate station
        if isinstance(station, str):
            if not station.isdigit():
                raise ValueError("Station must be numeric")
            station = int(station)

        conn = under_super.get_connection()
        cursor = conn.cursor()

        # Validate user
        cursor.execute(
            "SELECT Contraseña, Rol FROM user WHERE Nombre_Usuario=%s",
            (username,)
        )
        result = cursor.fetchone()
        if not result:
            raise ValueError("Usuario no encontrado")
        db_password, role = result
        if db_password != password:
            raise ValueError("Contraseña incorrecta")

        # Start session
        cursor.execute(
            """
            INSERT INTO Sesiones (Nombre_Usuario, Stations_ID, Login_Time, Is_Active)
            VALUES (%s, %s, %s, %s)
            """,
            (username, station, datetime.now(), "-1")
        )
        cursor.execute("SELECT LAST_INSERT_ID()")
        session_id = cursor.fetchone()[0]

        # Check station availability
        cursor.execute("SELECT User_Logged FROM Estaciones WHERE Station_Number=%s", (station,))
        row = cursor.fetchone()
        if row and row[0]:
            # Occupied
            conn.commit(); conn.close()
            raise RuntimeError(f"La estación {station} ya está siendo usada por {row[0]}")

        # Update station status (insert as in UI flow)
        cursor.execute(
            """INSERT INTO estaciones (User_Logged, Station_Number)
            VALUES (%s, %s)
            """,
            (username, station)
        )
        conn.commit(); conn.close()

        # If a previous main window exists (parent), destroy it before opening the new session UI
        try:
            if parent is not None and hasattr(parent, 'winfo_exists') and parent.winfo_exists():
                parent.destroy()
                # Ensure Tk will create a fresh root for the next window
                try:
                    import tkinter as _tk
                    _tk._default_root = None
                except Exception:
                    pass
        except Exception as e:
            print(f"[WARN] no se pudo destruir la ventana anterior: {e}")

        # Open main window
        try:
            if not silent:
                messagebox.showinfo("Login", f"Bienvenido {username} ({role})")
        except Exception:
            pass

        # ⭐ VERIFICAR ROL: Si es Operador, ir directamente a open_hybrid_events
        if role == "Operador":
            print(f"[DEBUG] auto_login - Rol Operador detectado, abriendo open_hybrid_events directamente")
            backend_super.open_hybrid_events(username, session_id, station, None)
        elif role == "Supervisor":
            # Para Supervisor, abrir ventana de hybrid events supervisor
            print(f"[DEBUG] auto_login - Rol Supervisor detectado, abriendo hybrid events supervisor")
            backend_super.open_hybrid_events_supervisor(username=username, root=None)
        elif role == "Lead Supervisor":
            # Para Lead Supervisor, abrir ventana específica con permisos de eliminación
            print(f"[DEBUG] auto_login - Rol Lead Supervisor detectado, abriendo hybrid events lead supervisor")
            backend_super.open_hybrid_events_lead_supervisor(username=username, root=None)
        else:
            # Para otros roles, abrir menú principal
            print(f"[DEBUG] auto_login - Rol {role} detectado, abriendo menú principal")
            main_super.open_main_window(username, station, role, session_id)
        
        return True, session_id, role
    except Exception as e:
        print(f"[ERROR] auto_login: {e}")
        try:
            messagebox.showerror("Auto Login", str(e), parent=parent)
        except Exception:
            pass
        return False, None, None
