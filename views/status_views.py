import tkinter as tk
from tkinter import ttk
from controllers.status_controller import StatusController, get_status_display_text

try: 
    import customtkinter as UI  
except ImportError:
    UI = None


def render_status_header(parent_frame, username, controller=None, UI=None):
    """
    Renderiza el header de status con indicador y botones de cambio
    
    Args:
        parent_frame: Frame padre donde se renderizará el status
        username: Nombre del usuario
        controller: Instancia de StatusController (opcional, se crea si no se pasa)
        UI: Módulo customtkinter o None para tkinter estándar
    
    Returns:
        dict: Diccionario con referencias a los widgets creados
    """
    # Crear controlador si no se pasó uno
    if controller is None:
        controller = StatusController(username)
    
    # Obtener status actual
    current_status = controller.get_current_status()
    status_text = get_status_display_text(current_status)
    
    # Crear contenedor para el status
    if UI is not None:
        status_container = UI.CTkFrame(parent_frame, fg_color="transparent")
    else:
        status_container = tk.Frame(parent_frame, bg="#23272a")
    status_container.pack(side="right", padx=(5, 10), pady=15)
    
    # Label de status actual
    if UI is not None:
        status_label = UI.CTkLabel(
            status_container, 
            text=status_text, 
            font=("Segoe UI", 12, "bold")
        )
    else:
        status_label = tk.Label(
            status_container, 
            text=status_text,
            bg="#23272a", 
            fg="#c9d1d9",
            font=("Segoe UI", 12, "bold")
        )
    status_label.pack(side="left", padx=(0, 8))
    
    # Función para actualizar status
    def update_status_ui(new_value):
        """Actualiza el status en BD y en la UI"""
        success = controller.update_status(new_value)
        if success:
            # Actualizar el label visual
            new_status = controller.get_current_status()
            new_text = get_status_display_text(new_status)
            status_label.configure(text=new_text)
        else:
            print(f"[ERROR] No se pudo actualizar status a {new_value}")
    
    # Botones de status
    btn_emoji_green = "🟢"
    btn_emoji_yellow = "🟡"
    btn_emoji_red = "🔴"
    
    if UI is not None:
        # Botón Verde (Disponible = 0)
        status_btn_green = UI.CTkButton(
            status_container, 
            text=btn_emoji_green, 
            command=lambda: update_status_ui(0),
            fg_color="#00c853", 
            hover_color="#00a043",
            width=45, 
            height=38,
            font=("Segoe UI", 16, "bold")
        )
        status_btn_green.pack(side="left", padx=2)
        
        # Botón Amarillo (Ocupado = 1)
        status_btn_yellow = UI.CTkButton(
            status_container, 
            text=btn_emoji_yellow, 
            command=lambda: update_status_ui(1),
            fg_color="#f5a623", 
            hover_color="#e69515",
            width=45, 
            height=38,
            font=("Segoe UI", 16, "bold")
        )
        status_btn_yellow.pack(side="left", padx=2)
        
        # Botón Rojo (No disponible = -1)
        status_btn_red = UI.CTkButton(
            status_container, 
            text=btn_emoji_red, 
            command=lambda: update_status_ui(-1),
            fg_color="#d32f2f", 
            hover_color="#b71c1c",
            width=45, 
            height=38,
            font=("Segoe UI", 16, "bold")
        )
        status_btn_red.pack(side="left", padx=2)
    else:
        # Fallback tkinter
        status_btn_green = tk.Button(
            status_container,
            text=btn_emoji_green,
            command=lambda: update_status_ui(0),
            bg="#00c853",
            fg="white",
            activebackground="#00a043",
            font=("Segoe UI", 16, "bold"),
            relief="flat",
            width=3,
            height=1
        )
        status_btn_green.pack(side="left", padx=2)
        
        status_btn_yellow = tk.Button(
            status_container,
            text=btn_emoji_yellow,
            command=lambda: update_status_ui(1),
            bg="#f5a623",
            fg="white",
            activebackground="#e69515",
            font=("Segoe UI", 16, "bold"),
            relief="flat",
            width=3,
            height=1
        )
        status_btn_yellow.pack(side="left", padx=2)
        
        status_btn_red = tk.Button(
            status_container,
            text=btn_emoji_red,
            command=lambda: update_status_ui(-1),
            bg="#d32f2f",
            fg="white",
            activebackground="#b71c1c",
            font=("Segoe UI", 16, "bold"),
            relief="flat",
            width=3,
            height=1
        )
        status_btn_red.pack(side="left", padx=2)
    
    # Retornar referencias útiles
    return {
        'container': status_container,
        'label': status_label,
        'buttons': {
            'green': status_btn_green,
            'yellow': status_btn_yellow,
            'red': status_btn_red
        },
        'controller': controller
    }


        

