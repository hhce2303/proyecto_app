from under_super import FilteredCombobox
from backend_super import can_end_shift, get_shift_start_time, has_active_shift, on_end_shift, on_start_shift
import customtkinter as ctk
import tkinter as tk
import tkcalendar
from datetime import datetime
from controllers.daily_controller import DailyController



class OperatorDailyFormModule:
    def __init__(self, parent, blackboard):
        """Renderiza el módulo de formulario diario del operador"""
        # Guardar referencias
        self.blackboard = blackboard
        self.daily_form_parent = parent
        self.ui_factory = blackboard.ui_factory
        self.username = blackboard.username
        self.window = blackboard.window
        self.controller = DailyController(self.username)
        self.UI = getattr(blackboard, 'UI', None)

        # Crear contenedor principal
        self.daily_form_frame = tk.Frame(parent, bg="#2b2b2b")
        # self.daily_form_frame.pack(fill="x", padx=10, pady=(5, 10))  # <--- QUITAR ESTE PACK

        # Crear formulario
        self._create_event_form(self.daily_form_frame)

    def _create_event_form(self, parent):
        # ...existing code for form creation (copied from previous _create_event_form)...
        inner_frame = tk.Frame(parent, bg="#2b2b2b")
        inner_frame.pack(fill="x", padx=(0, 10), pady=5)

        self.add_event_btn = self.ui_factory.button(
            inner_frame,
            text="➕",
            command=self._add_event,
            width=30,
            fg_color="#4CAF50",
            hover_color="#45a049"
        )
        self.add_event_btn.pack(side="left", padx=(2, 12))

        datetime_container = tk.Frame(inner_frame, bg="#2b2b2b")
        datetime_container.pack(side="left", padx=(0, 10))
        tk.Label(
            datetime_container,
            text="Fecha/Hora:",
            font=("Segoe UI", 9),
            fg="#ffffff",
            bg="#2b2b2b",
            justify="center"
        ).pack(side="top")
        entry_wrapper = tk.Frame(datetime_container, bg="#333333", highlightthickness=0)
        entry_wrapper.pack(side="top")
        self.datetime_entry = ctk.CTkEntry(
            entry_wrapper,
            width=120,
            font=("Segoe UI", 10),
            fg_color="#333333",
            text_color="#ffffff",
            border_width=3,
            border_color="#4a90e2"
        )
        self.datetime_entry.pack(side="left", padx=(3, 0), pady=2)
        datetime_btn = self.ui_factory.button(
            entry_wrapper,
            text="📅",
            command=lambda: self.blackboard._show_datetime_picker(
                callback=lambda dt: self._set_datetime_value(dt)
            ),
            width=25,
            height=22,
            fg_color="#4a90e2",
            hover_color="#3a7bc2"
        )
        datetime_btn.pack(side="left", padx=(2, 2), pady=2)

        site_container = tk.Frame(inner_frame, bg="#2b2b2b")
        site_container.pack(side="left", padx=0)
        tk.Label(
            site_container,
            text="Sitio:",
            font=("Segoe UI", 9),
            fg="#ffffff",
            bg="#2b2b2b",
            justify="center"
        ).pack(side="top")
        self.site_combo = FilteredCombobox(
            site_container,
            width=36,
            height=5,
            values=self._get_sites()
        )
        self.site_combo.pack(side="top")

        activity_container = tk.Frame(inner_frame, bg="#2b2b2b")
        activity_container.pack(side="left", padx=3)
        tk.Label(
            activity_container,
            text="Actividad:",
            font=("Segoe UI", 9),
            fg="#ffffff",
            bg="#2b2b2b",
            justify="center"
        ).pack(side="top")
        self.activity_combo = FilteredCombobox(
            activity_container,
            width=25,
            values=self._get_activities()
        )
        self.activity_combo.pack(side="top")

        quantity_container = tk.Frame(inner_frame, bg="#2b2b2b")
        quantity_container.pack(side="left", padx=3)
        tk.Label(
            quantity_container,
            text="Cantidad:",
            font=("Segoe UI", 9),
            fg="#ffffff",
            bg="#2b2b2b",
            justify="center"
        ).pack(side="top")
        self.quantity_entry = ctk.CTkEntry(
            quantity_container,
            width=60,
            font=("Segoe UI", 10),
            fg_color="#333333",
            text_color="#ffffff",
            border_width=3,
            border_color="#4a90e2",
            justify="center"
        )
        self.quantity_entry.insert(0, "0")
        self.quantity_entry.pack(side="top")

        camera_container = tk.Frame(inner_frame, bg="#2b2b2b")
        camera_container.pack(side="left", padx=3)
        tk.Label(
            camera_container,
            text="Camera:",
            font=("Segoe UI", 9),
            fg="#ffffff",
            bg="#2b2b2b",
            justify="center"
        ).pack(side="top")
        self.camera_entry = ctk.CTkEntry(
            camera_container,
            width=80,
            font=("Segoe UI", 10),
            fg_color="#333333",
            text_color="#ffffff",
            border_width=3,
            border_color="#4a90e2",
            justify="center"
        )
        self.camera_entry.pack(side="top")

        description_container = tk.Frame(inner_frame, bg="#2b2b2b")
        description_container.pack(side="left", padx=3)
        tk.Label(
            description_container,
            text="Descripción:",
            font=("Segoe UI", 9),
            fg="#ffffff",
            bg="#2b2b2b",
            justify="center"
        ).pack(side="top")
        self.description_entry = ctk.CTkEntry(
            description_container,
            width=290,
            font=("Segoe UI", 10),
            fg_color="#333333",
            text_color="#ffffff",
            border_width=3,
            border_color="#4a90e2"
        )
        self.description_entry.pack(side="top")

        self._bind_enter_to_submit()
        self.site_combo.focus_set()

    def _bind_enter_to_submit(self):
        fields = [
            self.datetime_entry,
            self.site_combo,
            self.activity_combo,
            self.quantity_entry,
            self.camera_entry,
            self.description_entry
        ]
        for field in fields:
            field.bind("<Return>", self._on_form_enter)
            field.bind("<KP_Enter>", self._on_form_enter)

    def _on_form_enter(self, event):
        self._add_event()
        return "break"

    def _get_sites(self):
        sites = self.controller.get_sites()
        return [f"{row[1]} ({row[0]})" for row in sites]

    def _get_activities(self):
        activities = self.controller.get_activities()
        return [row[0] for row in activities]

    def _add_event(self):
        from tkinter import messagebox
        if not has_active_shift(self.username):
            messagebox.showwarning(
                "Sin Turno Activo",
                "⚠️ Debes iniciar tu turno antes de registrar eventos.\n\nHaz clic en el botón '🚀 Start Shift' en la esquina superior derecha.",
                parent=self.window
            )
            return
        site_text = self.site_combo.get()
        activity = self.activity_combo.get()
        quantity = self.quantity_entry.get()
        camera = self.camera_entry.get()
        description = self.description_entry.get()
        if not site_text or not activity:
            messagebox.showwarning(
                "Campos requeridos",
                "Sitio y Actividad son obligatorios",
                parent=self.window
            )
            return
        try:
            site_id = int(site_text.split("(")[-1].split(")")[0])
        except:
            messagebox.showerror("Error", "Formato de sitio inválido", parent=self.window)
            return
        try:
            quantity_val = int(quantity) if quantity else 0
        except:
            messagebox.showerror("Error", "Cantidad debe ser un número", parent=self.window)
            return
        fecha_hora_str = self.datetime_entry.get().strip()
        fecha_hora = None
        if fecha_hora_str:
            try:
                from datetime import datetime
                fecha_hora = datetime.strptime(fecha_hora_str, "%Y-%m-%d %H:%M:%S")
            except Exception as e:
                print(f"[WARNING] No se pudo parsear fecha del formulario: {fecha_hora_str}, usando datetime.now(). Error: {e}")
                fecha_hora = None
        success, message = self.controller.create_event(
            site_id,
            activity,
            quantity_val,
            camera,
            description,
            fecha_hora
        )
        if success:
            self.site_combo.set("")
            self.activity_combo.set("")
            self.quantity_entry.delete(0, "end")
            self.quantity_entry.insert(0, "0")
            self.camera_entry.delete(0, "end")
            self.description_entry.delete(0, "end")
            self.datetime_entry.configure(state="normal")
            self.datetime_entry.delete(0, "end")
            self.datetime_entry.configure(state="readonly")
            if hasattr(self.blackboard, 'daily_module'):
                self.blackboard.daily_module.load_data()
            print(f"[DEBUG] {message}")
        else:
            messagebox.showerror(
                "Error",
                f"No se pudo agregar el evento: Recuerda no agregar numeros en el campo de actividad.",
                parent=self.window
            )

    def _set_datetime_value(self, dt):
        self.datetime_entry.configure(state="normal")
        self.datetime_entry.delete(0, "end")
        self.datetime_entry.insert(0, dt.strftime("%Y-%m-%d %H:%M:%S"))
        self.datetime_entry.configure(state="readonly")

    # Métodos públicos para exponer funcionalidad
    def get_frame(self):
        return self.daily_form_frame

    def clear_form(self):
        self.site_combo.set("")
        self.activity_combo.set("")
        self.quantity_entry.delete(0, "end")
        self.quantity_entry.insert(0, "0")
        self.camera_entry.delete(0, "end")
        self.description_entry.delete(0, "end")
        self.datetime_entry.configure(state="normal")
        self.datetime_entry.delete(0, "end")
        self.datetime_entry.configure(state="readonly")

    def reload_sites(self):
        self.site_combo.configure(values=self._get_sites())

    def reload_activities(self):
        self.activity_combo.configure(values=self._get_activities())

    # Puedes agregar más métodos públicos según necesidad

def render_operator_daily_form_module(parent, blackboard):
    """Función de fábrica para crear el módulo y exponer el frame principal"""
    module = OperatorDailyFormModule(parent, blackboard)
    return module.get_frame(), module
