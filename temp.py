from datetime import datetime
import sqlite3  # o pyodbc / según lo que uses
from under import get_connection
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from datetime import datetime, timedelta
username = "hector"


root = tk.Tk()
root.geometry("420x180")
root.title("Prueba Spinboxes con checkbox")

frame = tk.Frame(root, bg="#23272a", padx=12, pady=12)
frame.pack(fill="both", expand=True)

# Variables (DEFINIR ANTES)
desc_time_enabled = tk.BooleanVar(value=False)
desc_hour_var = tk.StringVar(value="00")
desc_minute_var = tk.StringVar(value="00")
desc_second_var = tk.StringVar(value="00")

def set_spins_to_now():
    """Poner la hora actual en las StringVar. No tocar directamente el contenido del Spinbox."""
    now = datetime.now()
    desc_hour_var.set(str(now.hour).zfill(2))
    desc_minute_var.set(str(now.minute).zfill(2))
    desc_second_var.set(str(now.second).zfill(2))

def toggle_spins():
    """Callback llamado por el checkbox (cuando se hace click)."""
    enabled = desc_time_enabled.get()
    new_state = "normal" if enabled else "disabled"
    spin_hour.config(state=new_state)
    spin_min.config(state=new_state)
    spin_sec.config(state=new_state)
    btn_refresh.config(state="normal" if enabled else "disabled")
    if enabled:
        # sincroniza inmediatamente al activar
        set_spins_to_now()

# Checkbox
cb = tk.Checkbutton(
    frame,
    text="Agregar tiempo editable",
    variable=desc_time_enabled,
    command=toggle_spins,
    bg="#23272a", fg="#a3c9f9", selectcolor="#23272a",
    font=("Segoe UI", 10, "bold"),
    anchor="w"
)
cb.grid(row=0, column=0, columnspan=6, sticky="w", pady=(0,8))

# Spinboxes (vinculados a StringVar)
spin_hour = tk.Spinbox(frame, from_=0, to=23, wrap=True, textvariable=desc_hour_var, width=3,
                       font=("Segoe UI", 11, "bold"), justify="center", state="disabled", bd=0)
spin_min  = tk.Spinbox(frame, from_=0, to=59, wrap=True, textvariable=desc_minute_var, width=3,
                       font=("Segoe UI", 11, "bold"), justify="center", state="disabled", bd=0)
spin_sec  = tk.Spinbox(frame, from_=0, to=59, wrap=True, textvariable=desc_second_var, width=3,
                       font=("Segoe UI", 11, "bold"), justify="center", state="disabled", bd=0)

spin_hour.grid(row=1, column=0, sticky="w")
tk.Label(frame, text=":", bg="#23272a", fg="#a3c9f9", font=("Segoe UI", 12, "bold")).grid(row=1, column=1)
spin_min.grid(row=1, column=2, sticky="w")
tk.Label(frame, text=":", bg="#23272a", fg="#a3c9f9", font=("Segoe UI", 12, "bold")).grid(row=1, column=3)
spin_sec.grid(row=1, column=4, sticky="w")

# Botón refrescar (inicialmente deshabilitado)
btn_refresh = tk.Button(frame, text="Refrescar Hora", command=set_spins_to_now, state="disabled",
                        font=("Segoe UI", 8, "bold"))
btn_refresh.grid(row=1, column=5, padx=(10,0))

# Además, si prefieres que el checkbox active también vía trace (opcional):
def on_time_enabled_change(*_):
    # Esto mantendrá la ui coherente si otra parte del código cambia desc_time_enabled
    toggle_spins()

desc_time_enabled.trace_add("write", on_time_enabled_change)

# inicialización: valores limpitos
set_spins_to_now()  # fija valor inicial (pero los widgets están disabled hasta que active checkbox)
root.mainloop()