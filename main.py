import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from PIL import Image, ImageTk
import os
import backend
import csv
from datetime import datetime
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo  # Python 3.9+
import re
import shutil
from tkinter import filedialog

# ------------------------------
# Configuración de iconos
# ------------------------------
ICON_PATH = r"\\192.168.7.12\Data SIG\Central Station SLC-COLOMBIA\1. Daily Logs - Operators\DataBase\icons"

# ------------------------------
# Variables globales
# ------------------------------
login_user = None
prev_user = None
cover_state_active = False
cover_reason = ""
event_tree = None
cover_label = None
opened_windows = {}  # Ventanas únicas
exit_cover_button = None  # Botón global salir cover



# ------------------------------
# Combobox filtrable
# ------------------------------
class FilteredCombobox(ttk.Combobox):
    def __init__(self, master=None, **kwargs):
        super().__init__(master, **kwargs)
        self.original_values = self['values']
        self.bind('<KeyRelease>', self.check_key)
        self.set('')

    def check_key(self, event):
        value = self.get()
        if value == '':
            self['values'] = self.original_values
        else:
            filtered = [item for item in self.original_values if value.lower() in str(item).lower()]
            self['values'] = filtered

# ------------------------------
# Login
# ------------------------------
def login():
    global login_user
    selected_user = login_var.get()
    if not selected_user:
        messagebox.showwarning("Login", "Por favor selecciona un usuario")
        return
    login_user = selected_user
    backend.LOGIN_TIMESTAMP = datetime.now()
    login_window.destroy()
    open_main_window()

def create_user_action():
    new_user = simpledialog.askstring("Crear usuario", "Ingrese el nombre del nuevo usuario:")
    if new_user:
        try:
            backend.create_user(new_user.strip())
            messagebox.showinfo("Éxito", f"Usuario '{new_user}' creado correctamente.")
            users = backend.get_users()
            login_combo["values"] = users
            login_combo.set(new_user.strip())
        except FileExistsError as e:
            messagebox.showwarning("Aviso", str(e))
            login_combo.set(new_user.strip())
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo crear el usuario:\n{e}")

def clear_treeview(tree):
    if tree and tree.winfo_exists():
        for item in tree.get_children():
            tree.delete(item)
# ------------------------------
# Ventana principal
# ------------------------------
def open_main_window():
    global root, cover_label, login_user, prev_user, cover_state_active, cover_reason, exit_cover_button, exit_cover_button
    exit_cover_button = None
    root = tk.Tk()
    root.title("Daily Log")
    width, height = 320, 380
    root.geometry(f"{width}x{height}+0+{root.winfo_screenheight()-height}")
    root.configure(bg="#2b2b2b")
    root.resizable(False, False)

    # ------------------------------
    # Carga de iconos
    # ------------------------------
    def load_icon(filename, size=(40, 40)):
        path = os.path.join(ICON_PATH, filename)
        img = Image.open(path).resize(size, Image.LANCZOS)
        return ImageTk.PhotoImage(img)

    icons = {name: load_icon(f"{name}.png") for name in ["add", "event", "report", "settings"]}

    # ------------------------------
    # Canvas de fondo con rectángulo
    # ------------------------------
    canvas = tk.Canvas(root, width=width-10, height=height-115, bg="#2b2b2b", highlightthickness=0)
    canvas.pack(pady=10)

    def create_rounded_rect(canvas, x1, y1, x2, y2, radius=15, fill="#353c47", outline="", width=0):
        points = [
            x1+radius, y1, x2-radius, y1, x2, y1, x2, y1+radius,
            x2, y2-radius, x2, y2, x2-radius, y2, x1+radius, y2,
            x1, y2, x1, y2-radius, x1, y1+radius, x1, y1
        ]
        return canvas.create_polygon(points, smooth=True, fill=fill, outline=outline, width=width)

    create_rounded_rect(canvas, 10, 10, width-10, height-120, radius=20, fill="#1a1a1a")
    create_rounded_rect(canvas, 6, 6, width-14, height-124, radius=15, fill="#353c47", outline="#1e3a5f", width=2)

    frame = tk.Frame(canvas, bg="#353c47")
    frame.place(x=15, y=15, width=width-40, height=height-145)

    # ------------------------------
    # Estilo botones
    # ------------------------------
    style = ttk.Style()
    style.theme_use("clam")
    style.configure("Card.TButton", background="#3f4a5a", foreground="#d0d0d0",
                    font=("Segoe UI", 11, "bold"), relief="flat", padding=10)
    style.map("Card.TButton", background=[("active", "#54657a")], foreground=[("active", "#a3c9f9")])

    # ------------------------------
    # Label de usuario y Cover
    # ------------------------------
    def update_cover_label():
        global cover_label
        if cover_label and cover_label.winfo_exists():
            cover_label.destroy()
        text = f"Usuario: {login_user}"
        if cover_state_active:
            text += f"  (Cover: {cover_reason})"
        cover_label = tk.Label(root, text=text, bg="#2b2b2b", fg="#a3c9f9", font=("Segoe UI", 10, "bold"))
        cover_label.pack(pady=10)

    # ------------------------------
    # Ventanas únicas
    # ------------------------------
    def single_window(name, func):
        if name in opened_windows and opened_windows[name].winfo_exists():
            opened_windows[name].focus()
            return
        win = func()
        opened_windows[name] = win

    # ------------------------------
    # Registrar evento
    # ------------------------------
    def open_register_form():
        form = tk.Toplevel()
        form.title("Registrar Evento")
        form.configure(bg="#2c2f33")
        form.geometry(f"420x460+0+{root.winfo_screenheight()-460}")
        form.resizable(False, False)

        tk.Label(form, text="*Activity Requiered only*", bg="#2c2f33", fg="#d0d0d0", font=("Segoe UI", 8, "bold")).place(x=30, y=10)


        tk.Label(form, text="Site:", bg="#2c2f33", fg="#d0d0d0", font=("Segoe UI", 11, "bold")).place(x=30, y=30)
        site_var = tk.StringVar()

        # Combobox con valores tal cual vienen de backend
        raw_sites = backend.get_sites()  # Ej: "{AS - AS 3281 Storage Lot - 305} ET"

       
        cleaned_sites = []
        site_timezone_map = {}

        for s in raw_sites:
            if not s:  # saltar None o vacíos
                continue
    # Asegurar string y reemplazar espacios no separables
            if isinstance(s, list) or isinstance(s, tuple):
                site_name_raw = str(s[0]).replace("\xa0", " ").strip()
                timezone = str(s[1]).strip() if len(s) > 1 else ""
            else:
                site_name_raw = str(s).replace("\xa0", " ").strip()
                timezone = ""
            cleaned_sites.append(site_name_raw)
            site_timezone_map[site_name_raw] = timezone

        # Combobox con valores limpios
        site_menu = FilteredCombobox(form, textvariable=site_var, values=cleaned_sites, font=("Segoe UI", 10))
        site_menu.place(x=150, y=30, width=250)



        site_menu = FilteredCombobox(form, textvariable=site_var, values=cleaned_sites, font=("Segoe UI", 10))
        site_menu.place(x=150, y=30, width=250)

        

        tk.Label(form, text="Actividad*:", bg="#2c2f33", fg="#d0d0d0", font=("Segoe UI", 11, "bold")).place(x=30, y=70)
        activity_var = tk.StringVar()
        activity_menu = FilteredCombobox(form, textvariable=activity_var, values=backend.get_activities(), font=("Segoe UI", 10))
        activity_menu.place(x=150, y=70, width=250)

        tk.Label(form, text="Cantidad:", bg="#2c2f33", fg="#d0d0d0", font=("Segoe UI", 11, "bold")).place(x=30, y=110)
        quantity_var = tk.StringVar()
        tk.Entry(form, textvariable=quantity_var, font=("Segoe UI", 10)).place(x=150, y=110, width=250)

        tk.Label(form, text="Camera:", bg="#2c2f33", fg="#d0d0d0", font=("Segoe UI", 11, "bold")).place(x=30, y=150)
        camera_var = tk.StringVar()
        tk.Entry(form, textvariable=camera_var, font=("Segoe UI", 10)).place(x=150, y=150, width=250)

        tk.Label(form, text="Descripción:", bg="#2c2f33", fg="#d0d0d0", font=("Segoe UI", 11, "bold")).place(x=30, y=190)
        desc_entry = tk.Text(form, font=("Segoe UI", 10), height=5, width=30)
        desc_entry.place(x=150, y=190)

        tk.Label(form, text="Usuario:", bg="#2c2f33", fg="#d0d0d0", font=("Segoe UI", 11, "bold")).place(x=30, y=310)
        user_var = tk.StringVar()
        user_options = backend.get_users()
        user_menu = FilteredCombobox(form, textvariable=user_var, values=user_options, font=("Segoe UI", 10))
        user_menu.place(x=150, y=310, width=250)
        user_var.set(login_user if login_user in user_options else user_options[0])

        # Timestamp real (audit trail)
        login_time = datetime.now()

        # Valores iniciales para hora editable
        hour_var = tk.StringVar(value=f"{login_time.hour:02}")
        minute_var = tk.StringVar(value=f"{login_time.minute:02}")
        second_var = tk.StringVar(value=f"{login_time.second:02}")

        tk.Label(form, text="Hora editable:", bg="#2c2f33", fg="#d0d0d0", font=("Segoe UI", 10, "bold")).place(x=30, y=350)
        tk.Spinbox(form, from_=0, to=23, wrap=True, textvariable=hour_var, width=3, font=("Segoe UI", 10)).place(x=150, y=350)
        tk.Label(form, text=":", bg="#2c2f33", fg="#a3c9f9").place(x=188, y=350)
        tk.Spinbox(form, from_=0, to=59, wrap=True, textvariable=minute_var, width=3, font=("Segoe UI", 10)).place(x=200, y=350)
        tk.Label(form, text=":", bg="#2c2f33", fg="#a3c9f9").place(x=238, y=350)
        tk.Spinbox(form, from_=0, to=59, wrap=True, textvariable=second_var, width=3, font=("Segoe UI", 10)).place(x=250, y=350)

        # Label pequeño de referencia
        tk.Label(form, text=f"(Hora real apertura: {login_time.strftime('%H:%M:%S')})", 
                bg="#2c2f33", fg="#a3c9f9", font=("Segoe UI", 8, "italic")).place(x=150, y=375)
        

        
        def save_event():
            global show_events
            site = site_var.get()
            activity = activity_var.get()
            quantity = quantity_var.get().strip()
            camera = camera_var.get().strip()
            desc = desc_entry.get("1.0", "end").strip()
            user = user_var.get()

            if not activity:
                messagebox.showwarning("Datos incompletos", "Por favor completa todos los campos")
                return

            # Construir timestamp editable a partir de Spinboxes
            try:
                hour = int(hour_var.get())
                minute = int(minute_var.get())
                second = int(second_var.get())
                # Combina fecha real con hora editable
                event_time = login_time.replace(hour=hour, minute=minute, second=second, microsecond=0)
            except ValueError:
                messagebox.showerror("Error", "Hora inválida")
                return

            # Llamada al backend usando event_time en lugar de login_time
            msg = backend.add_record_user_log_full(site, activity, quantity, camera, desc, user, event_time)
            messagebox.showinfo("Registro", msg)

            # --- LIMPIAR CAMPOS DEL FORMULARIO ---
            site_var.set("")       # si es un StringVar
            activity_var.set("")
            quantity_var.set("")
            camera_var.set("")
            desc_entry.delete("1.0", tk.END)  # si es un Text widgets

            # NOTA: No destruimos la ventana
            # form.destroy()  <-- eliminado

            # --- Insertar inmediatamente en la ventana de eventos si está abierta ---
            if "Event" in opened_windows and opened_windows["Event"] and opened_windows["Event"].winfo_exists():
                win_event = opened_windows["Event"]
                tree = None
                # Buscar el Treeview dentro de la ventana
                for child in win_event.winfo_children():
                    if isinstance(child, ttk.Treeview):
                        tree = child
                        break

                if tree:
                    # Determinar si el sitio es Especial
                    especiales = ("AS", "DT", "HUD", "SCH", "KG", "LT", "PE", "WAG")
                    es_especial = site.startswith(especiales)
                    valor_especial = "✔" if es_especial else ""
                    valor_registrado = "☐"  # por defecto desmarcado

                    # Crear la fila completa para el Treeview
                    row = [
                        event_time.strftime("%Y-%m-%d %H:%M:%S"),  # Timestamp
                        user,                                       # Usuario
                        valor_especial,                             # Especial
                        site,                                       # Site
                        activity,                                   # Actividad
                        quantity,                                   # Cantidad
                        camera,                                     # Camera
                        desc,                                       # Descripción
                        valor_registrado,                           # Registrado
                        
                    ]

                # Mantener un set de timestamps para evitar duplicados
                if not hasattr(win_event, 'last_timestamps'):
                    win_event.last_timestamps = set()

                ts_val = row[0]
                if ts_val not in win_event.last_timestamps:
                    win_event.last_timestamps.add(ts_val)

                    # --- Insertar según orden cronológico ---
                    # Convertimos timestamps de las filas existentes
                    existing_items = tree.get_children()
                    insert_index = "end"  # por defecto al final
                    try:
                        new_ts = datetime.strptime(ts_val, "%Y-%m-%d %H:%M:%S")
                        for idx, item in enumerate(existing_items):
                            existing_ts_str = tree.item(item)["values"][0]
                            existing_ts = datetime.strptime(existing_ts_str, "%Y-%m-%d %H:%M:%S")
                            # Si la nueva fila es anterior a la fila actual, insertamos aquí
                            if new_ts < existing_ts:
                                insert_index = idx
                                break
                    except Exception:
                        pass  # si hay error en parseo, insertamos al final

                    tree.insert("", insert_index, values=row, tags=("evenrow",))


            # No es necesario llamar a refrescar_eventos(), porque la ventana de eventos
            # ya tiene su bucle de refresco automático cada 5 segundos
        ttk.Button(form, text="Guardar", command=save_event, style="Card.TButton").place(x=100, y=400, width=235, height=45)
        
        # Enter para login
        form.bind("<Return>", lambda event: save_event())

        return form

# ------------------------------
# Mostrar eventos
# ------------------------------

    opened_windows = {}  # Para controlar ventanas abiertas

    def show_events():
        # Destruir ventana previa si existe
        if "Event" in opened_windows and opened_windows["Event"] and opened_windows["Event"].winfo_exists():
            opened_windows["Event"].destroy()

        top = tk.Toplevel()
        top.title("Eventos registrados")
        top.configure(bg="#2c2f33")
        top.geometry("1200x450+0+200")

        # Scrollbar
        scrollbar = tk.Scrollbar(top)
        scrollbar.pack(side="right", fill="y")

        # Columnas del Treeview
        columns = ("Timestamp", "Usuario", "Especial", "Site",
                "Actividad", "Cantidad", "Camera", "Descripción", "Registrado", "csv_path")
        tree = ttk.Treeview(top, columns=columns, show="headings", yscrollcommand=scrollbar.set)
        scrollbar.config(command=tree.yview)

        headers = ["Timestamp", "Usuario", "Especial", "Site", "Actividad",
                "Cantidad", "Camera", "Descripción", "Registrado", "csv_path"]
        widths = [150, 100, 70, 160, 100, 60, 100, 200, 90, 0]  # csv_path oculta
        for h, w in zip(headers, widths):
            anchor = "center" if h in ("Especial", "Registrado") else "w"
            tree.heading(h, text=h)
            tree.column(h, width=w, anchor=anchor)

        # Colores de filas
        tree.tag_configure("oddrow", background="#3a3f44", foreground="#d0d0d0")
        tree.tag_configure("evenrow", background="#2f343a", foreground="#d0d0d0")
        tree.tag_configure("especial", foreground="lime green")
        tree.pack(expand=True, fill="both", padx=10, pady=10)

        top.edit_box = None
        especiales = ("AS", "DT", "HUD", "SCH", "KG", "LT", "PE", "WAG")

        # ---------------------------
        # Cargar CSVs del usuario usando DictReader
        # ---------------------------
        user_folder = backend.get_user_folder(login_user)
        if user_folder and os.path.exists(user_folder):
            csv_files = [f for f in os.listdir(user_folder) if f.lower().endswith(".csv")]
            for idx, csv_file in enumerate(sorted(csv_files)):
                file_path = os.path.join(user_folder, csv_file)
                try:
                    with open(file_path, newline="", encoding="utf-8") as f:
                        reader = csv.DictReader(f)
                        for row in reader:
                            site_name = row.get("Site", "")
                            es_especial = site_name.startswith(especiales)
                            valor_especial = "✔" if es_especial else ""
                            valor_registrado = row.get("Registrado", "☐")

                            values = (
                                row.get("Timestamp", ""),
                                row.get("Usuario", ""),
                                valor_especial,
                                site_name,
                                row.get("Actividad", ""),
                                row.get("Cantidad", ""),
                                row.get("Camera", ""),
                                row.get("Descripción", ""),
                                valor_registrado,
                                file_path
                            )

                            tags = ("evenrow" if idx % 2 == 0 else "oddrow",)
                            if es_especial:
                                tags += ("especial",)
                            tree.insert("", "end", values=values, tags=tags)
                except Exception as e:
                    print(f"No se pudo leer {file_path}: {e}")

        # ---------------------------
        # Doble clic para editar celdas
        # ---------------------------
        def on_double_click(event):
            region = tree.identify("region", event.x, event.y)
            if region != "cell":
                return

            row_id = tree.identify_row(event.y)
            col_id = tree.identify_column(event.x)  # forma "#1", "#2", ...

            # Bloquear edición de Especial (#3)
            if col_id == "#3":
                return

            # Toggle de Registrado (#9)
            if col_id == "#9":
                current = tree.set(row_id, column=col_id)
                tree.set(row_id, column=col_id, value="☑" if current == "☐" else "☐")
                return

            # Para el resto de columnas, abrir Entry
            tree.update_idletasks()
            x, y, width, height = tree.bbox(row_id, col_id)
            value = tree.set(row_id, column=col_id)

            # Destruir Entry previo
            if top.edit_box:
                top.edit_box.destroy()

                # Si es la columna Descripción (#8) → Entry + Spinboxes
            if col_id == "#8":
                # Entry para texto
                top.edit_box = tk.Entry(tree)
                top.edit_box.place(x=x, y=y, width=width - 100,height=height)  # dejar espacio a la derecha
                top.edit_box.insert(0, value)
                top.edit_box.focus()

                now = datetime.now()
                hour_var = tk.StringVar(value=f"{now.hour:02}")
                min_var = tk.StringVar(value=f"{now.minute:02}")
                sec_var = tk.StringVar(value=f"{now.second:02}")

                top.hour_spin = tk.Spinbox(tree, from_=0, to=23, wrap=True, textvariable=hour_var, width=3, font=("Segoe UI", 9), justify="center")
                top.min_spin  = tk.Spinbox(tree, from_=0, to=59, wrap=True, textvariable=min_var, width=3, font=("Segoe UI", 9), justify="center")
                top.sec_spin  = tk.Spinbox(tree, from_=0, to=59, wrap=True, textvariable=sec_var, width=3, font=("Segoe UI", 9), justify="center")

                # Colocarlos justo a la derecha del Entry
                top.hour_spin.place(x=x+width+1, y=y, width=30, height=height)
                top.min_spin.place(x=x+width+50, y=y, width=30, height=height)
                top.sec_spin.place(x=x+width+90, y=y, width=30, height=height)

            # Crear Entry
            top.edit_box = tk.Entry(tree)
            top.edit_box.place(x=x, y=y, width=width, height=height)
            top.edit_box.insert(0, value)
            top.edit_box.focus()

            # Guardar cambios al presionar Enter o perder foco
            def save_edit(event=None):
                if top.edit_box:
                    desc_text = top.edit_box.get()
                    hora = f"{hour_var.get()}:{min_var.get()}:{sec_var.get()}"
                    tree.set(row_id, column=col_id, value=f"{desc_text} [{hora}]")
                    top.edit_box.destroy()
                    top.edit_box = None
                    top.hour_spin.destroy()
                    top.min_spin.destroy()
                    top.sec_spin.destroy()
                    del top.hour_spin, top.min_spin, top.sec_spin

            top.edit_box.bind("<Return>", save_edit)
            top.edit_box.bind("<FocusOut>", save_edit)

        tree.bind("<Double-1>", on_double_click)

        # ---------------------------
        # Guardar cambios (sobrescribe CSV originales)
        # ---------------------------
        def save_changes():
            for item in tree.get_children():
                values = tree.item(item)["values"]
                if not values or len(values) < 10:
                    continue
                csv_file = values[-1]  # csv_path
                row_data = values[:-1]

                headers = ["Timestamp", "Usuario", "Especial", "Site",
                        "Actividad", "Cantidad", "Camera", "Descripción", "Registrado"]

                try:
                    with open(csv_file, "w", newline="", encoding="utf-8") as f:
                        writer = csv.writer(f)
                        writer.writerow(headers)
                        writer.writerow(row_data)
                except Exception as e:
                    messagebox.showerror("Error", f"No se pudo guardar {csv_file}:\n{e}")

            messagebox.showinfo("Guardado", "Todos los cambios se han guardado correctamente.")

        save_btn = tk.Button(top, text="Guardar cambios", command=save_changes,
                            bg="#7289da", fg="white", font=("Arial", 12))
        save_btn.pack(pady=5)

        # ---------------------------
        # Borrar evento
        # ---------------------------
        def delete_event():
            selected = tree.selection()
            if not selected:
                messagebox.showwarning("Seleccionar evento", "Por favor selecciona un evento para borrar.")
                return

            row_id = selected[0]
            values = tree.item(row_id)["values"]
            if not values or len(values) < 10:
                return

            csv_file = values[-1]
            if not os.path.exists(csv_file):
                messagebox.showerror("Error", f"No se encontró el archivo:\n{csv_file}")
                return

            confirm = messagebox.askyesno("Confirmar eliminación",
                                        f"¿Deseas eliminar este evento?\n{csv_file}")
            if confirm:
                try:
                    os.remove(csv_file)
                    tree.delete(row_id)
                    messagebox.showinfo("Borrado", "Evento eliminado correctamente.")
                except Exception as e:
                    messagebox.showerror("Error", f"No se pudo eliminar el evento:\n{e}")

        delete_btn = tk.Button(top, text="Borrar evento", command=delete_event,
                            bg="#e74c3c", fg="white", font=("Arial", 12))
        delete_btn.pack(pady=5)

        # Guardar referencia
        opened_windows["Event"] = top
        return top



    # ------------------------------
    # Ventana Report
    # ------------------------------
    def open_report_window():
        # Destruir ventana previa si existe
        if "Report" in opened_windows and opened_windows["Report"] and opened_windows["Report"].winfo_exists():
            opened_windows["Report"].destroy()

        top = tk.Toplevel()
        top.title("Reporte de Eventos Especiales")
        top.configure(bg="#2c2f33")
        top.geometry("1200x450+0+200")

        # Scrollbar
        scrollbar = tk.Scrollbar(top)
        scrollbar.pack(side="right", fill="y")

        # Columnas del Treeview
        columns = ("Timestamp", "Usuario", "Especial", "Site",
                "Actividad", "Cantidad", "Camera", "Descripción", "Seleccionar", "csv_path")
        tree = ttk.Treeview(top, columns=columns, show="headings", yscrollcommand=scrollbar.set)
        scrollbar.config(command=tree.yview)

        headers = ["Timestamp", "Usuario", "Especial", "Site", "Actividad",
                "Cantidad", "Camera", "Descripción", "Seleccionar", "csv_path"]
        widths = [150, 100, 70, 160, 100, 60, 100, 200, 90, 0]  # csv_path oculta
        for h, w in zip(headers, widths):
            anchor = "center" if h in ("Especial", "Seleccionar") else "w"
            tree.heading(h, text=h)
            tree.column(h, width=w, anchor=anchor)

        tree.tag_configure("oddrow", background="#3a3f44", foreground="#d0d0d0")
        tree.tag_configure("evenrow", background="#2f343a", foreground="#d0d0d0")
        tree.tag_configure("especial", foreground="lime green")
        tree.pack(expand=True, fill="both", padx=10, pady=10)


        # ---------------------------
        # Cargar CSVs del usuario y filtrar solo Especiales
        # ---------------------------
        user_folder = backend.get_user_folder(login_user)
        site_db = backend.get_sites()  # Devuelve lista de [Nombre site, TimeZone]

        # Map Time Zone del site a zonas IANA
        tz_map = {
            "ET": "America/New_York",
            "CT": "America/Chicago",
            "MT": "America/Denver",
            "MST": "America/Phoenix",
            "PT": "America/Los_Angeles"
        }

        if user_folder and os.path.exists(user_folder):
            csv_files = [f for f in os.listdir(user_folder) if f.lower().endswith(".csv")]
            for idx, csv_file in enumerate(sorted(csv_files)):
                file_path = os.path.join(user_folder, csv_file)
                try:
                    with open(file_path, newline="", encoding="utf-8") as f:
                        reader = csv.DictReader(f)
                        for row in reader:
                            site_name = row.get("Site", "").strip()
                            es_especial = row.get("Especial", "") == "✔"
                            if not es_especial:
                                continue  # solo mostrar eventos Especiales

                            # Detectar Time Zone
                            tz = "CT"  # default Colombia
                            site_name_norm = re.sub(r"[^A-Z0-9]", "", site_name.upper())
                            for s in site_db:
                                db_site_name_norm = re.sub(r"[^A-Z0-9]", "", s[0].upper())
                                if site_name_norm == db_site_name_norm:
                                    tz_candidate = s[1].strip().upper()
                                    if tz_candidate in tz_map:
                                        tz = tz_candidate
                                    break

                            # Mapear a ZoneInfo y ajustar timestamp
                            ts_str_original = row.get("Timestamp", "").strip()
                            try:
                                ts_col = datetime.strptime(ts_str_original, "%Y-%m-%d %H:%M:%S")
                                ts_col = ts_col.replace(tzinfo=ZoneInfo("America/Bogota"))  # CSV en hora Colombia
                                ts_adjusted = ts_col.astimezone(ZoneInfo(tz_map.get(tz, "America/Bogota")))
                                ts_str = ts_adjusted.strftime("%Y-%m-%d %H:%M:%S")
                            except:
                                ts_str = ts_str_original  # fallback

                            # Checkbox Seleccionar
                            select_val = "☐"

                            # Valores para insertar en treeview
                            values = (
                                ts_str,
                                row.get("Usuario", ""),
                                "✔",
                                site_name,
                                row.get("Actividad", ""),
                                row.get("Cantidad", ""),
                                row.get("Camera", ""),
                                row.get("Descripción", ""),
                                select_val,
                                file_path
                            )

                            tags = ("evenrow" if idx % 2 == 0 else "oddrow", "especial")
                            tree.insert("", "end", values=values, tags=tags)

                except Exception as e:
                    print(f"No se pudo leer {file_path}: {e}")

        # ---------------------------
        # Toggle de Seleccionar al hacer clic
        # ---------------------------
        def on_click(event):
            region = tree.identify("region", event.x, event.y)
            if region != "cell":
                return
            row_id = tree.identify_row(event.y)
            col_id = tree.identify_column(event.x)
            if col_id == "#9":  # columna Seleccionar
                current = tree.set(row_id, column=col_id)
                tree.set(row_id, column=col_id, value="☑" if current == "☐" else "☐")

        tree.bind("<Button-1>", on_click)


        # ---------------------------
        # Botón para procesar eventos seleccionados
        # ---------------------------
        def process_selected(tree):
            """
            Procesa los eventos seleccionados en el Treeview de open_report_window().
            1. Pide al usuario una carpeta destino.
            2. Copia los CSV correspondientes a esa carpeta.
            """
            # Obtener carpeta destino con diálogo personalizado
            dest_folder = custom_folder_tree_dialog(
                base_path=r"\\192.168.7.12\Data SIG\Central Station SLC-COLOMBIA\1. Daily Logs - Operators",
                filter_word="SUP"
            )

            if not dest_folder:
                return  # usuario canceló si cancela, no hace nada

            copied = 0
            for item in tree.get_children():
                if tree.set(item, "Seleccionar") == "☑":  # Solo los marcados
                    csv_file = tree.set(item, "csv_path")  # viene oculto en el tree
                    if os.path.exists(csv_file):
                        try:
                            shutil.copy(csv_file, dest_folder)
                            copied += 1
                        except Exception as e:
                            messagebox.showerror("Error", f"No se pudo copiar {csv_file}:\n{e}")

            # 3. Resultado
            if copied:
                messagebox.showinfo("Procesado", f"{copied} eventos fueron copiados a:\n{dest_folder}")
            else:
                messagebox.showwarning("Sin selección", "No seleccionaste ningún evento.")

            if copied:
                messagebox.showinfo("Procesado", f"{copied} eventos fueron copiados a:\n{dest_folder}")
            else:
                messagebox.showwarning("Sin selección", "No seleccionaste ningún evento.")
                return
            # Obtener las rutas de los CSV seleccionados
            selected_items = [item for item in tree.get_children() if tree.set(item, "Seleccionar") == "☑"]
            paths = [tree.set(item, "csv_path") for item in selected_items]

            print("Eventos seleccionados:", paths)
            messagebox.showinfo("Seleccionados", f"{len(paths)} eventos seleccionados.")

        process_btn = tk.Button(
            top,
            text="Procesar seleccionados",
            command=lambda: process_selected(tree),  # ✅ se ejecuta solo al hacer click
            bg="#7289da",
            fg="white",
            font=("Arial", 12)
        )
        process_btn.pack(pady=5)

        # Guardar referencia
        opened_windows["Report"] = top
        return top
    
    def custom_folder_tree_dialog(base_path, filter_word=None):
        """
        Diálogo personalizado para seleccionar carpetas con Treeview y restricciones.
        - base_path: carpeta inicial y límite superior.
        - filter_word: si se pasa, solo muestra carpetas que contengan esa palabra.
        Arranca automáticamente en el último año/mes disponible.
        """
        import os
        import tkinter as tk
        from tkinter import ttk, messagebox

        result = {"path": None}

        # --- obtener último año/mes automáticamente ---
        def get_latest_year_month_path(base_path):
            if not os.path.exists(base_path):
                return base_path

            años = [d for d in os.listdir(base_path) if d.isdigit() and os.path.isdir(os.path.join(base_path, d))]
            if not años:
                return base_path
            latest_year = max(años)
            year_path = os.path.join(base_path, latest_year)

            meses = [d for d in os.listdir(year_path) if os.path.isdir(os.path.join(year_path, d))]
            if not meses:
                return year_path
            meses_sorted = sorted(meses, key=lambda x: int(x.split(".")[0]))
            latest_month = meses_sorted[-1]

            return os.path.join(year_path, latest_month)

        # punto de inicio (último año/mes)
        root_dir = get_latest_year_month_path(base_path)

        top = tk.Toplevel()
        top.title("Seleccionar carpeta")
        top.geometry("600x400")
        top.grab_set()

        # --- Variables ---
        current_path = tk.StringVar(value=root_dir)
        filter_var = tk.StringVar(value=filter_word if filter_word else "")

        # --- Widgets ---
        path_label = tk.Label(top, textvariable=current_path, fg="blue")
        path_label.pack(fill="x", padx=10, pady=5)

        filter_entry = tk.Entry(top, textvariable=filter_var)
        filter_entry.pack(fill="x", padx=10, pady=5)

        tree = ttk.Treeview(top, columns=("path",), displaycolumns=())
        tree.pack(expand=True, fill="both", padx=10, pady=5)

        # --- Funciones internas ---
        def populate_tree(parent, path):
            try:
                for name in os.listdir(path):
                    full_path = os.path.join(path, name)
                    if os.path.isdir(full_path):
                        if not filter_var.get() or filter_var.get().lower() in name.lower():
                            node = tree.insert(parent, "end", text=name, values=(full_path,))
                            # Insertar hijo falso para mostrar expandible
                            tree.insert(node, "end", text="dummy")
            except PermissionError:
                pass

        def open_node(event):
            node = tree.focus()
            path = tree.item(node, "values")[0]
            # limpiar hijos anteriores
            tree.delete(*tree.get_children(node))
            populate_tree(node, path)

        def update_filter(*args):
            tree.delete(*tree.get_children(""))
            populate_tree("", root_dir)

        def select_final():
            node = tree.focus()
            if not node:
                messagebox.showwarning("Atención", "Selecciona una carpeta.")
                return
            result["path"] = tree.item(node, "values")[0]
            top.destroy()

        # --- Eventos ---
        tree.bind("<<TreeviewOpen>>", open_node)
        filter_var.trace_add("write", update_filter)

        # --- Botones ---
        btn_frame = tk.Frame(top)
        btn_frame.pack(pady=10)

        tk.Button(btn_frame, text="Seleccionar", command=select_final).pack(side="left", padx=5)
        tk.Button(btn_frame, text="Cancelar", command=top.destroy).pack(side="left", padx=5)

        # --- Inicializar ---
        populate_tree("", root_dir)

        top.wait_window()
        return result["path"]

        
    # ------------------------------
    # Exportar Excel
    # ------------------------------
    def export_excel_action():
        global event_tree
        try:
            path = backend.export_events_to_excel(login_user)
            messagebox.showinfo("Éxito", f"Eventos exportados a Excel:\n{path}")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    ttk.Button(root, text="Exportar Excel", command=export_excel_action, style="Card.TButton").pack(pady=6, fill="x", padx=2)

    # ------------------------------
    # Cover Mode
    # ------------------------------
    def open_cover_mode():
        global login_user, prev_user, cover_state_active, cover_reason

        prev_user = login_user
        cover_win = tk.Toplevel()
        cover_win.title("Modo Cover")
        cover_win.configure(bg="#2b2b2b")
        cover_win.geometry(f"350x250+0+{root.winfo_screenheight()-250}")
        cover_win.resizable(False, False)

        tk.Label(cover_win, text="Selecciona tu usuario:", bg="#2b2b2b", fg="#d0d0d0",
                 font=("Segoe UI", 11, "bold")).pack(pady=10)
        user_var = tk.StringVar()
        users = backend.get_users()
        user_combo = FilteredCombobox(cover_win, textvariable=None, values=users, font=("Segoe UI", 10))
        user_combo.pack(pady=5, fill="x", padx=20)
        user_var.set(prev_user if prev_user in users else users[0])

        tk.Label(cover_win, text="Motivo Cover:", bg="#2b2b2b", fg="#d0d0d0",
                 font=("Segoe UI", 11, "bold")).pack(pady=10)
        reason_var = tk.StringVar()
        reasons = ["Break", "Cover Baño", "Cover Daily"]
        reason_combo = ttk.Combobox(cover_win, textvariable=reason_var, values=reasons, state="readonly", font=("Segoe UI", 10))
        reason_combo.pack(pady=5, fill="x", padx=20)
        reason_var.set(reasons[0])

        def apply_cover():
            global login_user, cover_state_active, cover_reason
            login_user = user_combo.get()
            cover_reason = reason_var.get()
            cover_state_active = True
            update_cover_label()
            show_exit_cover_button()
            cover_win.destroy()

        ttk.Button(cover_win, text="Activar Cover", command=apply_cover, style="Card.TButton").pack(pady=10, fill="x", padx=40)

        return cover_win  # <<--- IMPORTANTE


    def show_exit_cover_button():
        global exit_cover_button
        if exit_cover_button is not None and exit_cover_button.winfo_exists():
            return

        # Aumentar altura de la ventana principal
        width = root.winfo_width()
        height = root.winfo_height()
        root.geometry(f"{width}x{height + 60}")  # subimos 60px para el botón

        exit_cover_button = ttk.Button(root, text="Salir Cover", command=exit_cover, style="Card.TButton")
        exit_cover_button.pack(pady=3, fill="x", padx=2)

    def exit_cover():
        global login_user, prev_user, cover_state_active, cover_reason, exit_cover_button
        login_user = prev_user
        cover_state_active = False
        cover_reason = ""
        update_cover_label()

        # Restaurar tamaño original de la ventana
        width = root.winfo_width()
        height = root.winfo_height()
        root.geometry(f"{width}x{height - 60}")  # bajamos 40px al cerrar cover

        if exit_cover_button is not None and exit_cover_button.winfo_exists():
            exit_cover_button.destroy()
            exit_cover_button = None  # Muy importante reiniciarlo

    # ------------------------------
    # Botones principales
    # ------------------------------
    for widget in frame.winfo_children():
        widget.destroy()

    buttons = [
        ("Register", icons["add"], lambda: single_window("Register", open_register_form)),
        ("Event", icons["event"], lambda: single_window("Event", show_events)),
        ("Report", icons["report"], lambda: single_window("Report", open_report_window)),
        ("Cover", icons["settings"], lambda: single_window("Cover", open_cover_mode))
    ]

    for i, (text, icon, cmd) in enumerate(buttons):
        ttk.Button(frame, text=text, image=icon, compound="top", style="Card.TButton", command=cmd)\
            .grid(row=i//2, column=i%2, padx=8, pady=8, sticky="nsew")

    # Configurar cuadrícula
    for i in range(2):
        frame.grid_rowconfigure(i, weight=1)
        frame.grid_columnconfigure(i, weight=1)

    # Actualizar etiqueta Cover
    update_cover_label()

    root.mainloop()

# ------------------------------
# Ventana login
# ------------------------------
login_window = tk.Tk()
login_window.title("Login")
login_window.configure(bg="#2b2b2b")
login_window.geometry("300x150")
login_window.resizable(False, False)

tk.Label(login_window, text="Selecciona tu usuario:", bg="#2b2b2b", fg="#d0d0d0",
         font=("Segoe UI", 11, "bold")).pack(pady=10)
login_var = tk.StringVar()
users = backend.get_users()
login_combo = FilteredCombobox(login_window, textvariable=login_var, values=users, font=("Segoe UI", 10))
login_combo.pack(pady=5, fill="x", padx=20)

ttk.Button(login_window, text="Login", command=login).pack(pady=5, fill="x", padx=20)
ttk.Button(login_window, text="Crear Usuario", command=create_user_action).pack(pady=2, fill="x", padx=20)

# Enter para login
login_window.bind("<Return>", lambda event: login())

login_window.mainloop()
