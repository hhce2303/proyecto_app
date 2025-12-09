import tkinter as tk
from datetime import datetime
from tkinter import ttk  
now = datetime.now()
from under_super import FilteredCombobox

# ==================== NEWS CONTAINER ====================
def create_news_container(top, username, controller, UI=None):

    
    """Crea el contenedor de news dentro de la ventana principal"""
    if UI is not None:
        news_container = UI.CTkFrame(top, fg_color="#2c2f33")
    else:
        news_container = tk.Frame(top, bg="#2c2f33")
    # NO hacer pack() aquí - se mostrará solo cuando se cambie a modo News

    # Frame de formulario para crear news
    if UI is not None:
        news_form_frame = UI.CTkFrame(news_container, fg_color="#23272a", corner_radius=8)
    else:
        news_form_frame = tk.Frame(news_container, bg="#23272a")
    news_form_frame.pack(fill="x", padx=10, pady=10)

    # Variables para el formulario de news
    news_tipo_var = tk.StringVar()
    news_nombre_var = tk.StringVar()
    news_urgencia_var = tk.StringVar()
    news_fecha_out_var = tk.StringVar()

    # Listas de opciones
    news_tipos = ['SITE DOWN', 'MAINTENANCE', 'UPDATE', 'ALERT', 'INFO', 'REMINDER']
    news_urgencias = ['HIGH', 'MID', 'LOW']

    # Primera fila: Tipo y Nombre
    row1_news = tk.Frame(news_form_frame, bg="#23272a")
    row1_news.pack(fill="x", padx=20, pady=(15, 5))

    if UI is not None:
        UI.CTkLabel(row1_news, text="Tipo:", text_color="#c9d1d9", 
                   font=("Segoe UI", 11, "bold")).pack(side="left", padx=(0, 5))
    else:
        tk.Label(row1_news, text="Tipo:", bg="#23272a", fg="#c9d1d9", 
                font=("Segoe UI", 11, "bold")).pack(side="left", padx=(0, 5))

    try:
        news_tipo_combo = FilteredCombobox(row1_news, textvariable=news_tipo_var, 
                                                       values=news_tipos, width=20)
    except:
        news_tipo_combo = ttk.Combobox(row1_news, textvariable=news_tipo_var, 
                                       values=news_tipos, width=20)
    news_tipo_combo.pack(side="left", padx=5)

    if UI is not None:
        UI.CTkLabel(row1_news, text="Nombre:", text_color="#c9d1d9", 
                   font=("Segoe UI", 11, "bold")).pack(side="left", padx=(15, 5))
    else:
        tk.Label(row1_news, text="Nombre:", bg="#23272a", fg="#c9d1d9", 
                font=("Segoe UI", 11, "bold")).pack(side="left", padx=(15, 5))

    if UI is not None:
        news_nombre_entry = UI.CTkEntry(row1_news, textvariable=news_nombre_var, 
                                        width=400, font=("Segoe UI", 11))
    else:
        news_nombre_entry = tk.Entry(row1_news, textvariable=news_nombre_var, 
                                     width=50, font=("Segoe UI", 11))
    news_nombre_entry.pack(side="left", padx=5)

    # Segunda fila: Urgencia y Fecha Out
    row2_news = tk.Frame(news_form_frame, bg="#23272a")
    row2_news.pack(fill="x", padx=20, pady=5)

    if UI is not None:
        UI.CTkLabel(row2_news, text="Urgencia:", text_color="#c9d1d9", 
                   font=("Segoe UI", 11, "bold")).pack(side="left", padx=(0, 5))
    else:
        tk.Label(row2_news, text="Urgencia:", bg="#23272a", fg="#c9d1d9", 
                font=("Segoe UI", 11, "bold")).pack(side="left", padx=(0, 5))

    try:
        news_urgencia_combo = FilteredCombobox(row2_news, textvariable=news_urgencia_var, 
                                                           values=news_urgencias, width=15)
    except:
        news_urgencia_combo = ttk.Combobox(row2_news, textvariable=news_urgencia_var, 
                                           values=news_urgencias, width=15)
    news_urgencia_combo.pack(side="left", padx=5)

    if UI is not None:
        UI.CTkLabel(row2_news, text="Fecha Vencimiento (opcional):", text_color="#c9d1d9", 
                   font=("Segoe UI", 11, "bold")).pack(side="left", padx=(15, 5))
    else:
        tk.Label(row2_news, text="Fecha Vencimiento (opcional):", bg="#23272a", fg="#c9d1d9", 
                font=("Segoe UI", 11, "bold")).pack(side="left", padx=(15, 5))

    try:
        from tkcalendar import DateEntry
        news_fecha_out_entry = DateEntry(row2_news, textvariable=news_fecha_out_var, 
                                         date_pattern="yyyy-mm-dd", width=18)
    except:
        news_fecha_out_entry = tk.Entry(row2_news, textvariable=news_fecha_out_var, 
                                        width=20, font=("Segoe UI", 11))
    news_fecha_out_entry.pack(side="left", padx=5)

    # Panel scrollable para mostrar news activas (CREAR ANTES DE LOS BOTONES)
    if UI is not None:
        news_cards_container = UI.CTkScrollableFrame(news_container, fg_color="#2c2f33")
    else:
        news_cards_scroll = tk.Frame(news_container, bg="#2c2f33")
        news_canvas = tk.Canvas(news_cards_scroll, bg="#2c2f33", highlightthickness=0)
        news_scrollbar = tk.Scrollbar(news_cards_scroll, orient="vertical", command=news_canvas.yview)
        news_cards_container = tk.Frame(news_canvas, bg="#2c2f33")
        news_cards_container.bind("<Configure>", lambda e: news_canvas.configure(scrollregion=news_canvas.bbox("all")))
        news_canvas.create_window((0, 0), window=news_cards_container, anchor="nw")
        news_canvas.configure(yscrollcommand=news_scrollbar.set)
        news_canvas.pack(side="left", fill="both", expand=True)
        news_scrollbar.pack(side="right", fill="y")
        news_cards_scroll.pack(fill="both", expand=True, padx=10, pady=10)
    
    news_cards_container.pack(fill="both", expand=True, padx=10, pady=10)

    # Tercera fila: Botones (NECESITA ACCESO A news_cards_container)
    row3_news = tk.Frame(news_form_frame, bg="#23272a")
    row3_news.pack(fill="x", padx=20, pady=(5, 15))
    
    # Función helper para refrescar
    def refrescar():
        news_data = controller.cargar_news_activas()  # ✅ Sin parámetro
        render_news_cards(news_cards_container, news_data, controller)
    
    if UI is not None:
        UI.CTkButton(row3_news, text="✅ Crear News", 
                    command=lambda: controller.crear_news_controller(
            news_tipo_var.get(),
            news_nombre_var.get(),
            news_urgencia_var.get(),
            news_fecha_out_var.get(),
            refrescar
        ),
                    fg_color="#00c853", hover_color="#00a043", 
                    width=150, height=35,
                    font=("Segoe UI", 11, "bold")).pack(side="left", padx=5)
        
        UI.CTkButton(row3_news, text="🗑️ Limpiar", 
                    command=lambda: controller.limpiar_news_form(
            news_tipo_var, news_nombre_var, 
            news_urgencia_var, news_fecha_out_var
        ),
                    fg_color="#3b4754", hover_color="#4a5560", 
                    width=120, height=35,
                    font=("Segoe UI", 11, "bold")).pack(side="left", padx=5)
        
        UI.CTkButton(row3_news, text="🔄 Refrescar", command=refrescar,
                    fg_color="#4D6068", hover_color="#27a3e0", 
                    width=120, height=35,
                    font=("Segoe UI", 11, "bold")).pack(side="left", padx=5)
    else:
        tk.Button(row3_news, text="✅ Crear News", 
                 command=lambda: controller.crear_news_controller(
                                          tipo_var=news_tipo_var, 
                                          nombre_var=news_nombre_var, 
                                          urgencia_var=news_urgencia_var, 
                                          fecha_out_var=news_fecha_out_var, 
                                          callback_refresh=refrescar),
                 bg="#00c853", fg="white", relief="flat", width=12).pack(side="left", padx=5)
        
        tk.Button(row3_news, text="🗑️ Limpiar", 
                 command=lambda: controller.limpiar_news_form(news_tipo_var, news_nombre_var, 
                                                  news_urgencia_var, news_fecha_out_var),
                 bg="#3b4754", fg="white", relief="flat", width=10).pack(side="left", padx=5)
        
        tk.Button(row3_news, text="🔄 Refrescar", command=refrescar,
                 bg="#4D6068", fg="white", relief="flat", width=10).pack(side="left", padx=5)
    
    # Cargar news al iniciar
    refrescar()
    
    return news_container



def crear_news_card_preview(parent, news_data, controller):
    UI = None
    try:
        import customtkinter as UI
    except:
        pass
    """Crea una card visual para preview de news"""
    # ✅ Usa controller en vez de importar del modelo
    command=lambda: controller.delete_news(news_data['id'], create_news_container.refrescar())
    
    urgency_colors = {
        'HIGH': '#e74c3c',
        'MID': '#f39c12',
        'LOW': '#3498db',
        None: '#7d8590'
    }
    color = urgency_colors.get(news_data.get('urgencia'), '#7d8590')
    
    type_icons = {
        'SITE DOWN': '🔴',
        'MAINTENANCE': '🔧',
        'UPDATE': '🆕',
        'ALERT': '⚠️',
        'INFO': '📌',
        'REMINDER': '⏰',
        None: '📝'
    }
    icon = type_icons.get(news_data.get('tipo'), '📝')

    def _eliminar_news():
        controller.delete_news_card_controller(
            news_data['id'], 
            lambda: controller.cargar_news_activas()  # ← Callback correcto
        )
    
        
    def _desactivar_news():
        controller.deactivate_news_card_controller(
            news_data['id'], 
            lambda: controller.cargar_news_activas()
        )
        
    def _open_settings(event):
        context_menu = tk.Menu(card, tearoff=0, bg="#2c2f33", fg="#e0e0e0")
        context_menu.add_command(label="🗑️ Eliminar", command=_eliminar_news)
        context_menu.add_command(label="🚫 Desactivar", command=_desactivar_news)
        context_menu.add_separator()
        context_menu.add_command(label="❌ Cancelar", command=context_menu.destroy)
        try:
            context_menu.tk_popup(event.x_root, event.y_root, 0)
        finally:
            context_menu.grab_release()
    
    # Crear card
    if UI is not None:
        card = UI.CTkFrame(parent, fg_color="#23272a", corner_radius=8, 
                            border_width=1, border_color="#444444")
        card.pack(fill="x", pady=5, padx=10)
    else:
        card = tk.Frame(parent, bg="#23272a", relief="solid", borderwidth=1)
        card.pack(fill="x", pady=5, padx=10)
    
    # Barra de urgencia
    if UI is not None:
        urgency_bar = UI.CTkFrame(card, fg_color=color, width=5, height=20, corner_radius=0)
        
    else:
        urgency_bar = tk.Frame(card, bg=color, width=5)
    urgency_bar.pack(side="left", fill="y")
    
    # Contenido
    if UI is not None:
        content = UI.CTkFrame(card, fg_color="transparent")
    else:
        content = tk.Frame(card, bg="#23272a")
    content.pack(side="left", fill="both", expand=True, padx=10, pady=8)
    
    # Header
    if UI is not None:
        header = UI.CTkFrame(content, fg_color="transparent")
    else:
        header = tk.Frame(content, bg="#23272a")
    header.pack(fill="x")
    
    if UI is not None:
        UI.CTkLabel(header, text=f"{icon} {news_data.get('tipo') or 'Info'}", 
                    font=("Segoe UI", 11, "bold"),
                    text_color="#ffffff").pack(side="left")
        
        if news_data.get('urgencia'):
            UI.CTkLabel(header, text=news_data.get('urgencia'),
                        font=("Segoe UI", 10, "bold"),
                        text_color=color,
                        fg_color="#1e1e1e",
                        corner_radius=5,
                        padx=6, pady=2).pack(side="right")
    else:
        tk.Label(header, text=f"{icon} {news_data.get('tipo') or 'Info'}", bg="#23272a", fg="#ffffff",
                font=("Segoe UI", 11, "bold")).pack(side="left")
    
    # Título
    if UI is not None:
        UI.CTkLabel(content, text=news_data.get('nombre') or "Sin título",
                    font=("Segoe UI", 11),
                    text_color="#e0e0e0",
                    wraplength=1200,
                    anchor="w",
                    justify="left").pack(fill="x", pady=(3, 0))
    else:
        tk.Label(content, text=news_data.get('nombre') or "Sin título", bg="#23272a", fg="#e0e0e0",
                font=("Segoe UI", 11),
                wraplength=1200, anchor="w", justify="left").pack(fill="x", pady=(3, 0))
    
    # Footer
    if UI is not None:
        footer = UI.CTkFrame(content, fg_color="transparent")
    else:
        footer = tk.Frame(content, bg="#23272a")
    footer.pack(fill="x", pady=(3, 0))
    
    fecha_str = news_data.get('fecha_in').strftime("%d/%m %H:%M") if news_data.get('fecha_in') else "N/A"
    footer_text = f"👤 {news_data.get('publicado_por') or 'Sistema'} • 📅 {fecha_str}"
    
    if UI is not None:
        UI.CTkLabel(footer, text=footer_text,
                    font=("Segoe UI", 9),
                    text_color="#7d8590").pack(side="left")
    else:
        tk.Label(footer, text=footer_text, bg="#23272a", fg="#7d8590",
                font=("Segoe UI", 9)).pack(side="left")
    
    if news_data.get('fecha_out'):
        dias_restantes = (news_data.get('fecha_out') - datetime.now()).days
        if dias_restantes >= 0:
            expiry_text = f"⏳ Vence en {dias_restantes} días" if dias_restantes > 0 else "⏳ Vence hoy"
            if UI is not None:
                UI.CTkLabel(footer, text=expiry_text,
                            font=("Segoe UI", 9),
                            text_color="#f39c12").pack(side="right")
    
    # Bind recursivo para click derecho en toda la card y sus hijos
    def bind_recursive(widget):
        """Aplica el bind a un widget y todos sus hijos recursivamente"""
        widget.bind("<Button-3>", _open_settings)
        for child in widget.winfo_children():
            bind_recursive(child)
    
    bind_recursive(card)
    return card

def render_news_cards(container, news_data, controller):
    """Renderiza las news cards en el contenedor dado"""
    UI = None
    try:
        import customtkinter as UI
    except:
        pass
    
    # 1. Limpiar contenedor PRIMERO
    for widget in container.winfo_children():
        widget.destroy()
    
    # 2. Validar si hay datos
    if not news_data:
        if UI is not None:
            no_news_label = UI.CTkLabel(container, text="No hay noticias activas.", 
                                        font=("Segoe UI", 12), text_color="#888888")
            no_news_label.pack(pady=20)
        else:
            no_news_label = tk.Label(container, text="No hay noticias activas.", 
                                     font=("Segoe UI", 12), fg="#888888", bg="#2c2f33")
            no_news_label.pack(pady=20)
        return
    
    # 3. Renderizar cards UNA SOLA VEZ
    for row in news_data:
        news_dict = {
            'id': row[0],
            'tipo': row[1],
            'nombre': row[2],
            'urgencia': row[3],
            'publicado_por': row[4],
            'fecha_in': row[5],
            'fecha_out': row[6]
        }
        crear_news_card_preview(container, news_dict, controller)