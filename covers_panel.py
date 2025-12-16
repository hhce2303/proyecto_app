"""
covers_panel.py
Panel modal para mostrar la lista de covers programados.
Cumple con POO + MVC + BPP, reutiliza CoversModule y lógica de controller.
"""

from views.modules.covers_module import CoversModule
from controllers.covers_operator_controller import CoversOperatorController
import tkinter as tk


def show_covers_programados_panel(parent, UI, username):
    """
    Muestra el panel modal de covers programados.
    parent: ventana principal (Tk o CTkToplevel)
    UI: UI factory (CustomTkinter) o None para fallback Tkinter
    username: usuario actual
    """
    # Crear ventana modal
    if UI is not None:
        win = UI.CTkToplevel(parent)
        win.title("Lista de Covers Programados")
        win.geometry("900x600")
        win.configure(fg_color="#23272a")
    else:
        win = tk.Toplevel(parent)
        win.title("Lista de Covers Programados")
        win.geometry("900x600")
        win.configure(bg="#23272a")

    win.transient(parent)
    win.grab_set()
    win.focus_set()

    # Instanciar controller y módulo
    controller = CoversOperatorController(username)
    covers_panel = CoversModule(win, controller, UI)
    covers_panel.pack(fill="both", expand=True, padx=0, pady=0)

    # Botón cerrar
    def close_panel():
        win.destroy()

    if UI is not None:
        UI.CTkButton(win, text="❌ Cerrar", command=close_panel,
                     fg_color="#666666", hover_color="#555555",
                     width=120, height=36).pack(side="bottom", pady=18)
    else:
        tk.Button(win, text="❌ Cerrar", command=close_panel,
                  bg="#666666", fg="white", relief="flat",
                  width=12, font=("Segoe UI", 11)).pack(side="bottom", pady=18)

    # Centrar ventana respecto al padre
    win.update_idletasks()
    x = parent.winfo_rootx() + (parent.winfo_width() // 2) - (win.winfo_width() // 2)
    y = parent.winfo_rooty() + (parent.winfo_height() // 2) - (win.winfo_height() // 2)
    win.geometry(f"+{x}+{y}")

    return win
