import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from PIL import Image, ImageTk
import os
import backend
from datetime import datetime

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
    root.title("Event Logger")
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

    icons = {name: load_icon(f"{name}.png") for name in ["add", "event", "resume", "settings"]}

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

        tk.Label(form, text="Site:", bg="#2c2f33", fg="#d0d0d0", font=("Segoe UI", 11, "bold")).place(x=30, y=30)
        site_var = tk.StringVar()
        site_menu = FilteredCombobox(form, textvariable=site_var, values=backend.get_sites(), font=("Segoe UI", 10))
        site_menu.place(x=150, y=30, width=250)

        tk.Label(form, text="Actividad:", bg="#2c2f33", fg="#d0d0d0", font=("Segoe UI", 11, "bold")).place(x=30, y=70)
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

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        tk.Label(form, text=f"Fecha/Hora: {timestamp}", bg="#2c2f33", fg="#a3c9f9", font=("Segoe UI", 10, "italic")).place(x=150, y=350)

        def save_event():
            site = site_var.get()
            activity = activity_var.get()
            quantity = quantity_var.get().strip()
            camera = camera_var.get().strip()
            desc = desc_entry.get("1.0", "end").strip()
            user = user_var.get()
            if not site or not activity or not quantity or not camera or not desc:
                messagebox.showwarning("Datos incompletos", "Por favor completa todos los campos")
                return
            msg = backend.add_record_user_log_full(site, activity, quantity, camera, desc, user)
            messagebox.showinfo("Registro", msg)
            form.destroy()
            refresh_event_tree()

        ttk.Button(form, text="Guardar", command=save_event, style="Card.TButton").place(x=100, y=400, width=250, height=40)
        return form

    # ------------------------------
    # Mostrar eventos
    # ------------------------------
    def show_events():
        global event_tree

        # Si la ventana ya existe, destruirla
        if "Event" in opened_windows and opened_windows["Event"] and opened_windows["Event"].winfo_exists():
            opened_windows["Event"].destroy()

        top = tk.Toplevel()
        top.title("Eventos registrados")
        top.configure(bg="#2c2f33")
        top.geometry(f"1100x220+0+{root.winfo_screenheight()-220}")

        scrollbar = tk.Scrollbar(top)
        scrollbar.pack(side="right", fill="y")
        event_tree = ttk.Treeview(
            top,
            columns=("Site", "Actividad", "Cantidad", "Camera", "Descripción", "Usuario", "Timestamp"),
            show="headings",
            yscrollcommand=scrollbar.set,
            selectmode="browse"
        )
        scrollbar.config(command=event_tree.yview)

        headers = ["Site", "Actividad", "Cantidad", "Camera", "Descripción", "Usuario","Timestamp"]
        widths = [50, 100, 100, 60, 100, 250, 120, 80, 150]
        for h, w in zip(headers, widths):
            event_tree.heading(h, text=h)
            event_tree.column(h, width=w, anchor="center")

        event_tree.tag_configure("oddrow", background="#3a3f44", foreground="#d0d0d0")
        event_tree.tag_configure("evenrow", background="#2f343a", foreground="#d0d0d0")

        # Limpiar cualquier registro previo
        clear_treeview(event_tree)

        # <-- PASAR login_user AQUÍ
        events = backend.get_events(login_user)

        for idx, event in enumerate(events):
            tag = "evenrow" if idx % 2 == 0 else "oddrow"
            event_tree.insert("", "end", values=event, tags=(tag,))

        event_tree.pack(expand=True, fill="both", padx=10, pady=10)

        # Guardar ventana abierta
        opened_windows["Event"] = top

        return top


    def refresh_event_tree():
        global event_tree
        if event_tree and event_tree.winfo_exists():
            for item in event_tree.get_children():
                event_tree.delete(item)
            events = backend.get_events()
            for idx, event in enumerate(events):
                tag = "evenrow" if idx % 2 == 0 else "oddrow"
                event_tree.insert("", "end", values=event, tags=(tag,))

    # ------------------------------
    # Ventana Report
    # ------------------------------
    def open_report_window():
        global opened_windows

        # Destruir ventana previa si existe
        if "Report" in opened_windows and opened_windows["Report"] and opened_windows["Report"].winfo_exists():
            opened_windows["Report"].destroy()

        win = tk.Toplevel()
        win.title("Reporte de Eventos")
        win.geometry(f"400x300+0+{root.winfo_screenheight()-400}")
        win.configure(bg="#1d2024")
        win.resizable(False, False)

        #columns = ["Actividad", "Site", "Cantidad Total"]
        columns = ["Site", "Actividad", "Cantidad Total"]
        tree = ttk.Treeview(win, columns=columns, show="headings")
        scrollbar = ttk.Scrollbar(win, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        tree.pack(expand=True, fill="both", padx=10, pady=10)

        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, width=70, anchor="center")

        # Limpiar registros previos
        clear_treeview(tree)

        # <-- PASAR login_user a backend
        summary = backend.generate_report(login_user)

        for idx, (act, site, total) in enumerate(summary):
            tag = "evenrow" if idx % 1 == 0 else "oddrow"
            tree.insert("", "end", values=(site,act,total), tags=(tag,))

        # Guardar ventana abierta
        opened_windows["Resume"] = win

        return win

    # ------------------------------
    # Exportar Excel
    # ------------------------------
    def export_excel_action():
        global event_tree
        try:
            path = backend.export_events_to_excel(login_user)
            messagebox.showinfo("Éxito", f"Eventos exportados a Excel:\n{path}")
            refresh_event_tree()
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
        ("Resume", icons["resume"], lambda: single_window("Report", open_report_window)),
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

login_window.mainloop()
