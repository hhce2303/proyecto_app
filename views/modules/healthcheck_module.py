import threading
from models.healthcheck_model import _CACHE_SUPERVISORES
import time
import tkinter as tk
from tkinter import messagebox
import webbrowser
from tksheet import Sheet
from controllers.healthcheck_controller import HealthcheckController
from utils.ui_factory import UIFactory
from views.healthcheck_view import show_tickets_on_table
from controllers.healthcheck_controller import clear_filters, refresh_data
from views.modules.ticket_card_module import TicketCard


class HealthcheckModule:
    cache_lock = threading.Lock()
    def refresh(self):
        """Forzar refresh real de datos y caché desde la UI o el hilo de supervisor."""
        refresh_data(self)
    """Módulo de Healthcheck"""

    COLUMNS = ["ID", "Asunto", "Sitio", "Solicitante", "Estado", "Creado", "Asignado"]
    COLUMN_WIDTHS = {
        "ID": 70,
        "Asunto": 410,
        "Sitio": 270,
        "Solicitante": 180,
        "Estado": 85,
        "Creado": 110,
        "Asignado": 110
    }

    def __init__(self, parent, username, UI=None, SheetClass=None):
        self.current_page = 1
        self.page_size = 50
        self.parent = parent
        self.username = username
        self.UI = UI
        self.ui_factory = UIFactory(UI)
            
        # Referencia al blackboard (se establecerá desde OperatorBlackboard)
        self.blackboard = None
        
        # Componentes UI
        self.container = None
        self.toolbar = None
        self.sheet_frame = None
        self.sheet = None

        # Controller
        self.controller = HealthcheckController(username)

        self.page_label = None
        self.render_module()

    def render_module(self):
        """Renderiza el módulo de Healthcheck"""
        self._create_container()
        self._create_toolbar()
        self._create_sheet()
        self.refresh_cache_supervisor()
        self._load_data()

    def _create_container(self):
        """Crea el contenedor principal del módulo"""
        self.container = self.ui_factory.frame(self.parent, fg_color="#1e1e1e")
        self.container.pack(fill="both", expand=True)
    
    def _create_toolbar(self):
        """Crea barra de herramientas con botones"""
        self.toolbar = self.ui_factory.frame(self.container, fg_color="#2c2f33")
        self.toolbar.pack(fill="x", padx=10, pady=(10, 5))

        self.toolbar_label_frame = self.ui_factory.frame(self.toolbar, fg_color="#2c2f33")
        self.toolbar_label_frame.pack(fill="x", expand=True)
        
        self.id_search_var = tk.StringVar()
        self.site_search_var = tk.StringVar()
        self.status_search_var = tk.StringVar()
        self.requester_search_var = tk.StringVar()


        #============= Labels =============

        # ==== id label ======
        id_label = self.ui_factory.label(self.toolbar_label_frame, text="ID Ticket:", 
                                        font=("Segoe UI", 11, "bold"), fg="#ffffff", bg="#2c2f33")
        id_label.pack(side="left", padx=(35, 2))

        
        # ==== site label ======

        site_label = self.ui_factory.label(self.toolbar_label_frame, text="Buscar Sitio:",
                                        font=("Segoe UI", 11, "bold"), fg="#ffffff", bg="#2c2f33")
        site_label.pack(side="left", padx=(95, 2))

        # ==== status label ======
        status_label = self.ui_factory.label(self.toolbar_label_frame, text="Estado:", 
                                        font=("Segoe UI", 11, "bold"), fg="#ffffff", bg="#2c2f33")
        status_label.pack(side="left", padx=(130, 15))


        # ==== requester label ====

        requester_label = self.ui_factory.label(self.toolbar_label_frame, text="Buscar Solicitante:", 
                                        font=("Segoe UI", 11, "bold"), fg="#ffffff", bg="#2c2f33")
        requester_label.pack(side="left", padx=(140, 15))

        #============= Entrys =============

        #===== id entry =====

        healthcheck_id_entry = self.ui_factory.entry(self.toolbar, textvariable=self.id_search_var, 
                                        width=100, font=("Segoe UI", 11))
        healthcheck_id_entry.pack(side="left", padx=5)

        #==== site entry ====

        healthcheck_site_entry = self.ui_factory.entry(self.toolbar, textvariable=self.site_search_var, 
                                        width=200, font=("Segoe UI", 11))
        healthcheck_site_entry.pack(side="left", padx=5)

        #==== status entry ====
        healthcheck_status_entry = self.ui_factory.entry(self.toolbar, textvariable=self.status_search_var, 
                                        width=150, font=("Segoe UI", 11))
        healthcheck_status_entry.pack(side="left", padx=5)

        #==== requester entry ====

        healthcheck_requester_entry = self.ui_factory.entry(self.toolbar, textvariable=self.requester_search_var, 
                                        width=200, font=("Segoe UI", 11))
        healthcheck_requester_entry.pack(side="left", padx=5)

        #============= Buttons =============
        self.ui_factory.button(
            self.toolbar,
            text="⏭️ Siguiente Página",
            command=self.next_page,
            fg_color="#4D6068", hover_color="#27a3e0",
            width=150, height=35,
            font=("Segoe UI", 11, "bold")
        ).pack(side="right", padx=5)

        self.ui_factory.button(
            self.toolbar,
            text="⏮️ Página Anterior",
            command=self.prev_page,
            fg_color="#4D6068", hover_color="#27a3e0",
            width=150, height=35,
            font=("Segoe UI", 11, "bold")
        ).pack(side="right", padx=5)

        self.ui_factory.button(
            self.toolbar,
            text="🏘️ Buscar",
            command=self.wrapper_search,
            fg_color="#00c853", hover_color="#00a043",
            width=100, height=35,
            font=("Segoe UI", 11, "bold")
        ).pack(side="left", padx=5)

        # Label de página actual
        self.page_label = tk.Label(self.toolbar, text="Página 1", font=("Segoe UI", 11, "bold"), fg="#ffffff", bg="#2c2f33")
        self.page_label.pack(side="right", padx=10)

    def wrapper_search(self):
        try:
            id = self.id_search_var.get().strip()   
            site = self.site_search_var.get().strip()
            status = self.status_search_var.get().strip()
            requester = self.requester_search_var.get().strip()

            print(f"[DEBUG] Buscando: id={id}, site={site}, status={status}, requester={requester}")

            self.current_page = 1
            tickets = self.controller.cargar_tickets_pagina(
                page=self.current_page,
                page_size=self.page_size,
                site=site if site else None,
                requester=requester if requester else None,
                status=status if status else None,
                id=id if id else None
            )
            print(f"[DEBUG] Resultado de búsqueda: {type(tickets)}")
            tickets = tickets.get("requests", []) if isinstance(tickets, dict) else tickets
            print(f"[DEBUG] Tickets encontrados: {len(tickets)}")
            headers, data = show_tickets_on_table(tickets)
            self.sheet.set_sheet_data(data)
            self.sheet.headers(headers)
            self._apply_column_widths()
            self._update_page_label()
        except Exception as e:
            messagebox.showerror("Error", f"Ocurrió un error durante la búsqueda: {e}")
        
        self.ui_factory.button(self.toolbar, text="🗑️ Limpiar", 
                    command=lambda: clear_filters(self),
                    fg_color="#3b4754", hover_color="#4a5560", 
                    width=120, height=35,
                    font=("Segoe UI", 11, "bold")).pack(side="left", padx=5)
        
        self.ui_factory.button(self.toolbar, text="🔄 Refrescar", command=lambda: refresh_data(self),
                    fg_color="#4D6068", hover_color="#27a3e0", 
                    width=120, height=35,
                    font=("Segoe UI", 11, "bold")).pack(side="left", padx=5)
        

    def next_page(self):
        self.current_page += 1
        self._load_data_paged()

    def prev_page(self):
        if self.current_page > 1:
            self.current_page -= 1
            self._load_data_paged()

    def _update_page_label(self):
        if self.page_label:
            self.page_label.config(text=f"Página {self.current_page}")

    def color_status_cells(self, sheet, data):
        """Colorea las celdas de estado según su valor"""
        # Encuentra el índice de la columna "Estado"
        status_col = 4  # Según tu headers: ["ID", "Asunto", "sitio", "Solicitante", "Estado", ...]
        for row_idx, row in enumerate(data):
            status = row[status_col].lower()
            if status == "open":
                sheet.highlight_cells(row=row_idx, column=status_col, bg="#2196F3", fg="white")   # Azul
            elif status == "onhold":
                sheet.highlight_cells(row=row_idx, column=status_col, bg="#F44336", fg="white")   # Rojo
            elif status == "closed":
                sheet.highlight_cells(row=row_idx, column=status_col, bg="#4CAF50", fg="white")   # Verde
            elif status == "resolved":
                sheet.highlight_cells(row=row_idx, column=status_col, bg="#205022", fg="white")   # Verde oscuro
            elif status == "pending resolution":
                sheet.highlight_cells(row=row_idx, column=status_col, bg="#FF9800", fg="white")   # Naranja
            elif status == "coordinate":
                sheet.highlight_cells(row=row_idx, column=status_col, bg="#9C27B0", fg="white")   # Morado

    def refresh_cache_supervisor(self, interval=30):
        """Actualiza la caché de tickets de supervisores cada X segundos, protegido con Lock."""
        print(f"[DEBUG] Iniciando hilo de actualización de caché de supervisores cada {interval}s")
        def _actualizar():
            while True:
                try:
                    print(f"[DEBUG] Actualizando caché de supervisores...")
                    with self.cache_lock:
                        self.controller.cargar_healthchecks_activos()
                    # Actualizar la UI de forma segura desde el hilo principal
                    if hasattr(self.parent, 'after'):
                        self.parent.after(0, self._safe_load_data_paged)
                    else:
                        # fallback si no hay after (ejemplo: pruebas)
                        self._load_data_paged()
                except Exception as e:
                    print(f"[ERROR] Error al actualizar caché de supervisores: {e}")
                time.sleep(interval)
        hilo = threading.Thread(target=_actualizar, daemon=True)
        hilo.start()

    def _safe_load_data_paged(self):
        try:
            with self.cache_lock:
                refresh_data(self)
        except Exception as e:
            print(f"[ERROR] Error al actualizar la UI de healthcheck: {e}")

    def _load_data(self):
        """Carga datos en el tksheet desde el controller (primera página)"""
        self.current_page = 1
        self._load_data_paged()

    def _load_data_paged(self):
        tickets_dict = self.controller.cargar_tickets_pagina(page=self.current_page, page_size=self.page_size)
        tickets = tickets_dict.get("requests", []) if isinstance(tickets_dict, dict) else tickets_dict
        # Paginación local
        start = (self.current_page - 1) * self.page_size
        end = start + self.page_size
        page_tickets = tickets[start:end]
        headers, data = show_tickets_on_table(page_tickets)
        self.sheet.set_sheet_data(data)
        self.sheet.headers(headers)
        self.color_status_cells(self.sheet, data)
        self._apply_column_widths()
        self._update_page_label()
        
        
    def _create_sheet(self):
        """Crea y configura el tksheet"""
        # Frame para el sheet
        self.sheet_frame = self.ui_factory.frame(self.container, fg_color="#23272a")
        self.sheet_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Crear tksheet
        self.sheet = Sheet(
            self.sheet_frame,
            headers=self.COLUMNS,
            theme="dark blue",
            height=500,
            width=1000,
        )
        
        # Habilitar bindings (solo navegación, selección y undo)
        self.sheet.enable_bindings([
            "single_select",
            "drag_select",
            "column_select",
            "row_select",
            "undo",
            "copy",
            "row_height_resize",
            "column_width_resize",
            "cell_double_click",

        ])
        self.sheet.bind("<Double-Button-1>",lambda e: self.on_tk_double_click())

        self.sheet.pack(fill="both", expand=True)
        self.sheet.change_theme("dark blue")
        
        # Aplicar anchos de columnas
        self._apply_column_widths()

    def get_ids_rows(self):
        """Obtiene los IDs de los registros seleccionados"""
        selected_rows = self.sheet.get_selected_rows()
        if not selected_rows:
            return []
        ids = []

        for row_idx in selected_rows:
            try:
                row = self.sheet.get_row_data(row_idx)
                ticket_id = row[0]  # Asumiendo que la primera columna es ID
            except Exception:
                pass
        return ticket_id


    def on_tk_double_click(self):
        print("Doble clic en tksheet")
        ticket_id = self.get_ids_rows()
        print(f"IDs de filas seleccionadas: {ticket_id}")
        print(f"Abrir ticket ID {ticket_id} en navegador...")
        self.open_ticket_detailes("/" + ticket_id)

        if not ticket_id:
            messagebox.showinfo("Información", "No hay filas seleccionadas.")
            return
                

    def open_ticket_detailes(self, ticket_id):
        """Abre una ventana con los detalles del ticket"""
        ticket = self.controller.obtener_detalles_ticket(ticket_id)
        if ticket:
            TicketCard(self.parent, ticket, username=self.username)
        else:
            messagebox.showerror("Error", f"No se pudieron obtener los detalles del ticket {ticket_id}.")


    def _apply_column_widths(self):
        """Aplica anchos personalizados a las columnas"""
        # tksheet espera set_column_width(column, width)
        for idx, col_name in enumerate(self.COLUMNS):
            if col_name in self.COLUMN_WIDTHS:
                try:
                    self.sheet.set_column_width(idx, self.COLUMN_WIDTHS[col_name])
                except Exception:
                    # fallback para versiones antiguas
                    self.sheet.column_width(column=idx, width=self.COLUMN_WIDTHS[col_name])
        self.sheet.redraw()

