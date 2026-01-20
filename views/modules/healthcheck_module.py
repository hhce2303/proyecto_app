import threading
import time
import tkinter as tk
from tkinter import messagebox
from tksheet import Sheet
from datetime import datetime
from controllers.healthcheck_controller import HealthcheckController
from utils.ui_factory import UIFactory
from views.healthcheck_view import show_tickets_on_table
from controllers.healthcheck_controller import clear_filters, refresh_data
from views.modules.ticket_card_module import TicketCard


class HealthcheckModule:
    

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
        
        # Cache optimizado con TTL
        self.tickets_cache = {}  # Cache de tickets en memoria (diccionario por ID)
        self.cache_timestamp = None  # Timestamp de última carga
        self.cache_ttl = 300  # TTL de 5 minutos (300 segundos)
        self.cache_metadata = {}  # Metadata del JSON normalizado
        
        # Organización de datos
        self.sites_by_group = {}  # Sitios organizados por grupo
        self.tickets_by_site = {}  # Tickets organizados por sitio
        self.group_tabs = {}  # Tabs por grupo
        self.group_scrollable_frames = {}  # Frames scrollables por grupo
        self.site_sheets = {}  # Diccionario para guardar referencias a los sheets por sitio
        
        # Navegación de sitios (para búsqueda)
        self.site_widgets = {}  # (group_name, site_name) → site_container widget
        self.group_canvas = {}  # group_name → canvas widget para scroll
        
        # ═══════════════════════════════════════════════════════════════
        # PERFORMANCE: Estado para renderizado asíncrono y lazy loading
        # ═══════════════════════════════════════════════════════════════
        self.loading_groups = set()  # Grupos actualmente renderizándose
        self.pending_chunks = {}  # group_name → lista de timers activos (para cancelar)
        self.sheet_states = {}  # site_name → 'placeholder' | 'loaded'
        # ═══════════════════════════════════════════════════════════════
        
        # ═══════════════════════════════════════════════════════════════
        # COLAPSADO CON CONTAINER FIJO: Estado por sitio
        # ═══════════════════════════════════════════════════════════════
        self.site_containers = {}  # site_name → {'site_container': Frame, 'header_row': Frame, 'toggle_btn': Button, 'content_frame': Frame|None, 'is_expanded': bool}
        # ═══════════════════════════════════════════════════════════════

        self.page_label = None
        self.render_module()
        

    def render_module(self):
        """Renderiza el módulo de Healthcheck"""
        self._create_container()
        self._create_toolbar_tree()
        self._load_db_data()
        
        # Cargar sitios de BD inmediatamente y organizarlos por grupo
        print("[INIT] Cargando sitios desde BD...")
        sites_data = self.controller.get_sites()
        if sites_data:
            # Organizar sitios por grupo (guardando datos completos de HC)
            self.sites_by_group = {}
            self.sites_data_cache = {}  # Cache de datos completos por sitio
            for site in sites_data:
                group = site.get("ID_Grupo", "General")
                site_name = site.get("Nombre_sitio", "Unknown")
                if group not in self.sites_by_group:
                    self.sites_by_group[group] = []
                self.sites_by_group[group].append(site_name)
                
                # Guardar datos completos del sitio (incluyendo HC)
                # Convertir cámaras a int (la DB las guarda como varchar)
                total_cam = site.get("total_cameras", 0)
                inactive_cam = site.get("inactive_cameras", 0)
                
                self.sites_data_cache[site_name] = {
                    "id_site": site.get("id_site"),
                    "total_cameras": int(total_cam) if total_cam else 0,
                    "inactive_cameras": int(inactive_cam) if inactive_cam else 0,
                    "notes": site.get("notes", ""),
                    "estado_check": site.get("estado_check", False),
                    "id_admin": site.get("id_admin"),
                    "admin_name": site.get("admin_name", "Sin revisar"),
                    "timestamp_check": site.get("timestamp_check")
                }
            
            print(f"[INIT] {len(sites_data)} sitios cargados en {len(self.sites_by_group)} grupos")
            self._create_tabs()
        else:
            print("[WARNING] No se encontraron sitios en BD.")

    def _create_container(self):
        """Crea el contenedor principal del módulo"""
        self.container = self.ui_factory.frame(self.parent, fg_color="#1e1e1e")
        self.container.pack(fill="both", expand=True)
    
    def _create_toolbar_tree(self):
        """Crea barra de herramientas para vista de árbol"""
        import tkinter as tk
        from under_super import FilteredCombobox
        
        self.toolbar = self.ui_factory.frame(self.container, fg_color="#2c2f33")
        self.toolbar.pack(fill="x", padx=10, pady=(10, 5))
        
        # Título
        title_label = self.ui_factory.label(
            self.toolbar, 
            text="🎫 Healthcheck Registry",
            font=("Segoe UI", 16, "bold"),
            fg="#00c853"
        )
        title_label.pack(side="left", padx=10)
        
        # Barra de búsqueda de sitios (navegación)
        search_frame = tk.Frame(self.toolbar, bg="#2c2f33")
        search_frame.pack(side="left", padx=15)
        
        search_label = self.ui_factory.label(
            search_frame,
            text="🔍 Ir a sitio:",
            font=("Segoe UI", 10, "bold"),
            fg="#ffffff"
        )
        search_label.pack(side="left", padx=(0, 5))
        
        self.site_search_var = tk.StringVar()
        self.site_search_combo = FilteredCombobox(
            search_frame,
            textvariable=self.site_search_var,
            width=35,
            font=("Segoe UI", 10),
            values=[],
            state="normal",  # Permite escribir y filtrar
            bordercolor="#5ab4ff",
            borderwidth=2,
            fieldbackground="#2b2b2b",
            foreground="#ffffff",
            background="#2b2b2b"
        )
        self.site_search_combo.pack(side="left")
        
        # Binding para navegación
        self.site_search_combo.bind("<<ComboboxSelected>>", lambda e: self._on_site_selected())
        
        # Botón Cargar datos desde API
        """
        self.ui_factory.button(
            self.toolbar,
            text="📥 Cargar Datos",
            command=self._load_db_data,
            fg_color="#4D6068",
            hover_color="#27a3e0",
            width=140,
            height=35,
            font=("Segoe UI", 11, "bold")
        ).pack(side="left", padx=5)"""
        
        # Botón Forzar Refresh (invalida cache)
        self.ui_factory.button(
            self.toolbar,
            text="🔄 Refrescar Cache",
            command=self._force_refresh_cache,
            fg_color="#ff6b35",
            hover_color="#e85d2a",
            width=150,
            height=35,
            font=("Segoe UI", 11, "bold")
        ).pack(side="left", padx=5)
        
        """
        # Botón Buscar duplicado
        self.ui_factory.button(
            self.toolbar,
            text="🔍 Buscar duplicado",
            command=self._search_duplicate,
            fg_color="#00c853",
            hover_color="#00a043",
            width=150,
            height=35,
            font=("Segoe UI", 11, "bold")
        ).pack(side="left", padx=5)"""
    
    def _create_toolbar(self):
        """Crea barra de herramientas con botones (versión antigua para compatibilidad)"""
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

        except Exception as e:
            print(f"[ERROR] Error al obtener valores de búsqueda: {e}")
        
        self.ui_factory.button(self.toolbar, text="🗑️ Limpiar", 
                    command=lambda: clear_filters(self),
                    fg_color="#3b4754", hover_color="#4a5560", 
                    width=120, height=35,
                    font=("Segoe UI", 11, "bold")).pack(side="left", padx=5)
        
        self.ui_factory.button(self.toolbar, text="🔄 Refrescar", command=lambda: refresh_data(self),
                    fg_color="#4D6068", hover_color="#27a3e0", 
                    width=120, height=35,
                    font=("Segoe UI", 11, "bold")).pack(side="left", padx=5)
        
        
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
            height=700,
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

    def _create_scrollframe(self):
        """Crea un scrollframe para el tksheet"""
        
        scroll_frame = self.ui_factory.frame(self.container)
        scroll_frame.pack(fill="both", expand=True)
        
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

    def _create_tree_view(self):
        """Crea el contenedor con scroll para mostrar tickets agrupados por sitio con sheets"""
        import tkinter as tk
        from tkinter import ttk
        
        # Frame principal con scroll
        main_frame = self.ui_factory.frame(self.container, fg_color="#23272a")
        main_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Canvas y scrollbar para scroll vertical
        canvas = tk.Canvas(main_frame, bg="#23272a", highlightthickness=0)
        scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=canvas.yview)
        self.scrollable_frame = self.ui_factory.frame(canvas, fg_color="#23272a")
        
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Bind scroll con rueda del mouse
        canvas.bind_all("<MouseWheel>", lambda e: canvas.yview_scroll(int(-1*(e.delta/120)), "units"))
        
        self.site_sheets = {}  # Diccionario para guardar referencias a los sheets por sitio
    
    def _create_tabs(self):
        """Crea tabs por grupo de sitios con CTkScrollableFrame nativo"""
        import tkinter as tk
        from tkinter import ttk
        import customtkinter as ctk
        
        # Frame principal para tabs
        main_frame = self.ui_factory.frame(self.container, fg_color="#23272a")
        main_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Crear Notebook (tabs)
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill="both", expand=True)
        
        # Variable para trackear tabs ya cargados
        self.loaded_tabs = set()
        
        # Crear un tab por cada grupo
        for group_name in sorted(self.sites_by_group.keys()):
            # Frame para el tab
            tab_frame = tk.Frame(self.notebook, bg="#23272a")
            self.notebook.add(tab_frame, text=f"🏛️ {group_name}")
            
            # ═══════════════════════════════════════════════════════════════
            # OPTIMIZATION: Usar CTkScrollableFrame nativo (evita bind_all)
            # ═══════════════════════════════════════════════════════════════
            # Ventajas:
            # 1. Scroll nativo sin conflictos de bind_all("<MouseWheel>")
            # 2. Mejor rendimiento con contenido dinámico
            # 3. API limpia (pack directo, sin Canvas manual)
            # ═══════════════════════════════════════════════════════════════
            scrollable_frame = ctk.CTkScrollableFrame(
                tab_frame,
                fg_color="#23272a",
                scrollbar_button_color="#2c2f33",
                scrollbar_button_hover_color="#3a3f44"
            )
            scrollable_frame.pack(fill="both", expand=True)
            
            # Guardar referencia al frame scrollable de este grupo
            self.group_scrollable_frames[group_name] = scrollable_frame
            
            # Guardar referencia para navegación (CTkScrollableFrame tiene ._parent_canvas)
            self.group_canvas[group_name] = scrollable_frame._parent_canvas
        
        # Binding para cargar automáticamente al cambiar de tab
        self.notebook.bind("<<NotebookTabChanged>>", self._on_tab_changed)
        
        # Poblar combobox de búsqueda (optimizado: solo 50 iniciales)
        self._populate_site_search()
        
        print("[INFO] Tabs creados. Presiona 'Cargar Datos' para visualizar tickets.")
    
    def _load_api_data(self):
        """Carga los datos desde la API y los guarda en cache"""

        
        # Obtener tickets normalizados
        tickets = self.controller.get_json_tickets()
        if not tickets:
            messagebox.showwarning("Advertencia", "No se encontraron tickets")
            return
        
        # Guardar en cache por ID
        self.tickets_cache = {str(ticket["id"]): ticket for ticket in tickets}
        
        # Extraer sitios únicos
        sites_set = set(ticket.get("site", "Sin sitio") for ticket in tickets)
        self.sites_list = sorted(list(sites_set))
        
        print(f"[INFO] {len(tickets)} tickets cargados en cache")
        print(f"[INFO] {len(self.sites_list)} sitios encontrados")
        
        messagebox.showinfo("Éxito", f"{len(tickets)} tickets cargados en memoria\n{len(self.sites_list)} sitios disponibles")
        
        # Recargar sheets vacíos con los nuevos sitios

    def _load_db_data(self):
        """Carga JSON normalizado y tickets de BD con cache inteligente"""
        
        # Verificar si el cache es válido
        if self._is_cache_valid():
            print("[CACHE] Usando datos en memoria (cache válido)")
            messagebox.showinfo(
                "Cache Válido",
                f"Usando datos en memoria\n{len(self.tickets_cache)} tickets cargados\nCache generado: {self.cache_metadata.get('generated_at', 'N/A')}"
            )
            self._load_tree_data()
            return
        
        print("[INFO] Iniciando carga de datos (cache expirado o vacío)...")
        
        # 1. Cargar JSON normalizado optimizado
        print("[STEP 1] Cargando JSON normalizado...")
        tickets_json = self.controller.get_json_tickets()
        
        if not tickets_json:
            messagebox.showwarning("Advertencia", "No se encontraron tickets en JSON normalizado")
            return
        
        # 2. Actualizar cache en memoria
        self.tickets_cache = {str(ticket["id"]): ticket for ticket in tickets_json}
        self.cache_timestamp = time.time()
        print(f"[CACHE] {len(self.tickets_cache)} tickets cargados en cache")
        
        # 3. Obtener tickets guardados en BD
        print("[STEP 2] Obteniendo tickets de BD...")
        tickets_bd = self.controller.get_tickets()
        
        # Organizar tickets de BD por sitio
        self.tickets_by_site = {}
        if tickets_bd and len(tickets_bd) > 0:
            for ticket in tickets_bd:
                site_name = ticket.get("Nombre_sitio", "General")
                ticket_id = str(ticket.get("ID_ticket", ""))
                
                if site_name not in self.tickets_by_site:
                    self.tickets_by_site[site_name] = []
                
                self.tickets_by_site[site_name].append(ticket_id)
            
            print(f"[INFO] {len(tickets_bd)} tickets en BD, organizados en {len(self.tickets_by_site)} sitios")
        else:
            print("[INFO] No hay tickets previos en BD")
        
        # 4. Mostrar stats y recargar UI
        cache_age = self._get_cache_age_display()
        print(
            "Éxito",
            "Datos cargados:\n{len(self.tickets_cache)} tickets en JSON\n{len(tickets_bd) if tickets_bd else 0} tickets en BD\n\nCache: {cache_age}"
        )
        self._load_tree_data()
    
    def _is_cache_valid(self):
        """Verifica si el cache en memoria es válido"""
        if not self.tickets_cache or self.cache_timestamp is None:
            return False
        
        elapsed = time.time() - self.cache_timestamp
        is_valid = elapsed < self.cache_ttl
        
        if not is_valid:
            print(f"[CACHE] Cache expirado ({elapsed:.0f}s > {self.cache_ttl}s TTL)")
        
        return is_valid
    
    def _get_cache_age_display(self):
        """Retorna edad del cache en formato legible"""
        if self.cache_timestamp is None:
            return "Sin cache"
        
        elapsed = time.time() - self.cache_timestamp
        
        if elapsed < 60:
            return f"{int(elapsed)}s"
        elif elapsed < 3600:
            return f"{int(elapsed / 60)}m {int(elapsed % 60)}s"
        else:
            return f"{int(elapsed / 3600)}h {int((elapsed % 3600) / 60)}m"
    
    def _force_refresh_cache(self):
        """Fuerza la recarga del cache (invalida cache actual)"""
        print("[INFO] Forzando recarga de cache...")
        
        # ═══════════════════════════════════════════════════════════════
        # CLEANUP: Cancelar renderizado en progreso y liberar recursos
        # ═══════════════════════════════════════════════════════════════
        self._cancel_group_loading()
        
        # Destruir SiteContainers (destruye header + content)
        for site_name, state in list(self.site_containers.items()):
            try:
                state['site_container'].destroy()
            except:
                pass
        
        # Destruir sheets existentes
        for site_name, sheet in list(self.site_sheets.items()):
            try:
                sheet.destroy()
            except:
                pass
        
        # Limpiar estados
        self.cache_timestamp = None
        self.tickets_cache = {}
        self.loaded_tabs.clear()
        self.loading_groups.clear()
        self.pending_chunks.clear()
        self.sheet_states.clear()
        self.site_sheets.clear()
        self.site_containers.clear()  # Limpiar containers fijos
        
        print("[INFO] Tabs invalidados, se recargarán con datos frescos")
        # ═══════════════════════════════════════════════════════════════
        
        self._load_db_data()
    
    def _cancel_group_loading(self):
        """Cancela el renderizado en progreso de todos los grupos"""
        # Cancelar timers pendientes
        for group_name, timer_list in list(self.pending_chunks.items()):
            for timer_id in timer_list:
                try:
                    self.notebook.after_cancel(timer_id)
                except:
                    pass
        
        # Limpiar estados
        self.pending_chunks.clear()
        self.loading_groups.clear()
        print("[CLEANUP] Renderizado cancelado para todos los grupos")
    
    def _load_tree_data(self):
        """Carga los sheets del tab actualmente activo"""
        if not self.sites_by_group:
            print("[WARNING] No hay grupos disponibles")
            return
        
        try:
            # Obtener el tab actualmente seleccionado
            current_tab = self.notebook.index(self.notebook.select())
            group_names = sorted(self.sites_by_group.keys())
            if current_tab < len(group_names):
                group_name = group_names[current_tab]
                print(f"[INFO] Cargando grupo {group_name}...")
                # Guard delegado a _load_group_data()
                self._load_group_data(group_name)
        except Exception as e:
            print(f"[ERROR] Error cargando tab: {e}")
            import traceback
            traceback.print_exc()
    
    def _on_tab_changed(self, event):
        """Maneja el cambio de tab para cargar automáticamente el grupo"""
        # Solo cargar si hay datos en cache
        if not self.tickets_cache:
            print("[INFO] Cache vacío, usa el botón 'Cargar Datos' primero")
            return
        
        try:
            current_tab = self.notebook.index(self.notebook.select())
            group_names = sorted(self.sites_by_group.keys())
            
            if current_tab < len(group_names):
                group_name = group_names[current_tab]
                
                # Guard delegado a _load_group_data()
                print(f"[AUTO-LOAD] Intentando cargar grupo {group_name}...")
                self._load_group_data(group_name)
        except Exception as e:
            print(f"[ERROR] Error en cambio de tab: {e}")
            import traceback
            traceback.print_exc()
    
    def _load_group_data(self, group_name):
        """Carga los sheets de un grupo específico con chunked rendering"""
        # ═══════════════════════════════════════════════════════════════
        # GUARD CENTRALIZADO: Evitar re-renderizado de grupos ya cargados
        # ═══════════════════════════════════════════════════════════════
        # Este guard protege contra:
        # 1. Fugas de recursos (menús nativos de tksheet no liberables)
        # 2. Dobles renders que causan TclError: "No more menus"
        # 3. Performance degradation por recreación innecesaria de widgets
        #
        # Flujo garantizado: _load_group_data() se ejecuta UNA SOLA VEZ por grupo
        if group_name in self.loaded_tabs:
            print(f"[SKIP] Grupo '{group_name}' ya renderizado, evitando re-render")
            return
        
        # Check si ya está cargándose
        if group_name in self.loading_groups:
            print(f"[SKIP] Grupo '{group_name}' ya en proceso de carga")
            return
        # ═══════════════════════════════════════════════════════════════
        
        sites_list = self.sites_by_group.get(group_name, [])
        if not sites_list:
            print(f"[WARNING] No hay sitios para el grupo {group_name}")
            return
        
        print(f"[CHUNKED] Iniciando carga de grupo {group_name} con {len(sites_list)} sitios")
        
        # Marcar como cargando
        self.loading_groups.add(group_name)
        
        # ═══════════════════════════════════════════════════════════════
        # CHUNKED RENDERING: Renderizar sitios en chunks de 5 cada 20ms
        # ═══════════════════════════════════════════════════════════════
        # Por qué:
        # - Evita freeze de UI con 50+ sitios por grupo
        # - Distribuye trabajo pesado (tksheet) a lo largo del tiempo
        # - Permite actualización visual progresiva
        # - Mejora responsiveness percibida por usuario
        # ═══════════════════════════════════════════════════════════════
        
        # Iniciar renderizado en chunks
        chunk_size = 5  # Sitios por chunk
        chunk_delay = 20  # ms entre chunks
        
        self._render_chunk(group_name, sites_list, 0, chunk_size, chunk_delay)
    
    def _render_chunk(self, group_name, sites_list, start_idx, chunk_size, delay_ms):
        """Renderiza un chunk de sitios recursivamente
        
        Args:
            group_name: Nombre del grupo
            sites_list: Lista completa de sitios
            start_idx: Índice inicial del chunk actual
            chunk_size: Cantidad de sitios por chunk
            delay_ms: Delay en ms entre chunks
        """
        # Verificar si se canceló la carga
        if group_name not in self.loading_groups:
            print(f"[CHUNKED] Renderizado de {group_name} cancelado en chunk {start_idx}")
            return
        
        # Calcular rango del chunk
        end_idx = min(start_idx + chunk_size, len(sites_list))
        chunk = sites_list[start_idx:end_idx]
        
        print(f"[CHUNKED] Renderizando chunk {start_idx}-{end_idx}/{len(sites_list)} de {group_name}")
        
        COLUMNS_WIDTHS = {
            "ID": 80,
            "Estado": 100,
            "Asunto": 430,
            "Solicitante": 100,
            "Creado": 180,
            "Asignado": 110
        }
        
        # Obtener el frame scrollable de este grupo
        scrollable_frame = self.group_scrollable_frames.get(group_name)
        if not scrollable_frame:
            print(f"[ERROR] No se encontró frame para el grupo {group_name}")
            self.loading_groups.discard(group_name)
            return
        
        # Renderizar sitios del chunk actual en modo COLAPSADO
        for site_name in chunk:
            # Renderizar SOLO collapsed row (no widgets pesados)
            self._render_site_collapsed(group_name, site_name, scrollable_frame)
        
        # Programar siguiente chunk
        if end_idx < len(sites_list):
            # Hay más sitios por renderizar
            timer_id = self.notebook.after(
                delay_ms,
                lambda: self._render_chunk(group_name, sites_list, end_idx, chunk_size, delay_ms)
            )
            
            # Guardar timer para posible cancelación
            if group_name not in self.pending_chunks:
                self.pending_chunks[group_name] = []
            self.pending_chunks[group_name].append(timer_id)
        else:
            # Último chunk completado
            print(f"[CHUNKED] Grupo {group_name} completado: {len(sites_list)} sitios renderizados")
            self.loading_groups.discard(group_name)
            self.loaded_tabs.add(group_name)
            
            # Limpiar lista de timers
            if group_name in self.pending_chunks:
                del self.pending_chunks[group_name]
    
    def _render_site_collapsed(self, group_name, site_name, scrollable_frame):
        """Renderiza SiteContainer FIJO con HeaderRow visible.
        ContentFrame NO se crea (lazy loading).
        SiteContainer NUNCA se destruye, solo su contenido se muestra/oculta.
        
        Args:
            group_name: Nombre del grupo
            site_name: Nombre del sitio
            scrollable_frame: Frame contenedor scrollable
        """
        try:
            # Obtener datos del sitio
            site_data = self.sites_data_cache.get(site_name, {})
            site_tickets_ids = self.tickets_by_site.get(site_name, []) if hasattr(self, 'tickets_by_site') else []
            ticket_count = len(site_tickets_ids)
            
            # Calcular color según % de cámaras caídas
            total_cameras = int(site_data.get("total_cameras", 0) or 0)
            inactive_cameras = int(site_data.get("inactive_cameras", 0) or 0)
            
            if total_cameras > 0:
                percentage_down = (inactive_cameras / total_cameras) * 100
                if percentage_down <= 10:
                    header_color = "#00c853"  # Verde
                elif percentage_down <= 30:
                    header_color = "#ffb300"  # Amarillo
                else:
                    header_color = "#ff3d00"  # Rojo
            else:
                header_color = "#256ff9"  # Azul (sin datos)
            
            # ═══════════════════════════════════════════════════════════════
            # SITE CONTAINER FIJO (NUNCA se destruye)
            # ═══════════════════════════════════════════════════════════════
            site_container = self.ui_factory.frame(
                scrollable_frame,
                fg_color="#1e1e1e"
            )
            site_container.pack(fill="x", padx=5, pady=2)
            
            # ═══════════════════════════════════════════════════════════════
            # HEADER ROW (SIEMPRE VISIBLE)
            # ═══════════════════════════════════════════════════════════════
            header_row = self.ui_factory.frame(
                site_container,
                fg_color=header_color,
                corner_radius=8,
                height=50
            )
            header_row.pack(fill="x")
            
            # Toggle button ▶
            toggle_btn = self.ui_factory.button(
                header_row,
                text="▶",
                width=40,
                height=40,
                fg_color="transparent",
                hover_color=("gray90", "gray20"),
                font=("Segoe UI", 16, "bold"),
                text_color="#000000",
                command=lambda: self._toggle_site(site_name)
            )
            toggle_btn.pack(side="left", padx=5)
            
            # Site name label
            name_label = self.ui_factory.label(
                header_row,
                text=f"🏛️ {site_name}",
                font=("Segoe UI", 11, "bold"),
                text_color="#000000"
            )
            name_label.pack(side="left", padx=10)
            
            # Ticket count label
            count_label = self.ui_factory.label(
                header_row,
                text=f"({ticket_count} tickets)",
                font=("Segoe UI", 9),
                text_color="#000000"
            )
            count_label.pack(side="left", padx=5)
            
            # Cámaras info (compacto)
            if total_cameras > 0:
                cameras_label = self.ui_factory.label(
                    header_row,
                    text=f"🎥 {total_cameras}/{inactive_cameras} ⬇️",
                    font=("Segoe UI", 9),
                    text_color="#000000"
                )
                cameras_label.pack(side="left", padx=10)
            
            # ═══════════════════════════════════════════════════════════════
            # GUARDAR ESTADO (ContentFrame se creará lazy)
            # ═══════════════════════════════════════════════════════════════
            self.site_containers[site_name] = {
                'site_container': site_container,  # Container raíz FIJO
                'header_row': header_row,
                'toggle_btn': toggle_btn,
                'content_frame': None,  # Lazy: se crea en primera expansión
                'is_expanded': False,
                'group_name': group_name
            }
            
            # Guardar referencias para navegación
            self.site_widgets[(group_name, site_name)] = site_container
            self.sheet_states[site_name] = 'collapsed'
            
            print(f"[CONTAINER] {site_name} renderizado con container fijo (~500 bytes)")
            
        except Exception as e:
            print(f"[ERROR] _render_site_collapsed para {site_name}: {e}")
            import traceback
            traceback.print_exc()
    
    def _toggle_site(self, site_name):
        """Toggle expand/collapse de un sitio.
        SiteContainer NUNCA se mueve de posición.
        
        Args:
            site_name: Nombre del sitio
        """
        try:
            state = self.site_containers.get(site_name)
            if not state:
                print(f"[ERROR] Estado no encontrado para {site_name}")
                return
            
            if state['is_expanded']:
                # Colapsar: ocultar ContentFrame
                self._collapse_content(site_name)
            else:
                # Expandir: crear o mostrar ContentFrame
                self._expand_content(site_name)
                
        except Exception as e:
            print(f"[ERROR] _toggle_site para {site_name}: {e}")
            import traceback
            traceback.print_exc()
    
    def _expand_content(self, site_name):
        """Expande sitio: crea ContentFrame (primera vez) o lo muestra (siguientes).
        SiteContainer permanece en su posición.
        
        Args:
            site_name: Nombre del sitio
        """
        try:
            state = self.site_containers.get(site_name)
            if not state:
                return
            
            site_container = state['site_container']
            
            if state['content_frame'] is None:
                # ═══ PRIMERA EXPANSIÓN: CREAR CONTENT ═══
                print(f"[EXPAND] Primera expansión de {site_name}, creando content...")
                
                # Obtener datos
                site_data = self.sites_data_cache.get(site_name, {})
                site_tickets_ids = self.tickets_by_site.get(site_name, []) if hasattr(self, 'tickets_by_site') else []
                
                # Crear ContentFrame dentro de SiteContainer
                content_frame = self.ui_factory.frame(site_container, fg_color="#2b2b2b")
                
                # Crear body con sidebar + sheet
                body_frame = self.ui_factory.frame(content_frame, fg_color="#2b2b2b")
                body_frame.pack(fill="both", expand=True, padx=5, pady=5)
                
                # Renderizar sidebar (cámaras, firma, notas)
                sidebar_frame = self._render_sidebar_full(body_frame, site_name, site_data)
                sidebar_frame.pack(side="left", fill="y", padx=(0, 10))
                
                # Renderizar sheet (tickets)
                sheet_frame = self._render_sheet_full(body_frame, site_name, site_data, site_tickets_ids)
                sheet_frame.pack(side="left", fill="both", expand=True)
                
                # Guardar referencia
                state['content_frame'] = content_frame
                
            else:
                # ═══ RE-EXPANSIÓN: SOLO MOSTRAR ═══
                print(f"[EXPAND] Re-expandiendo {site_name} (reutilizando content)")
            
            # Mostrar ContentFrame
            state['content_frame'].pack(fill="both", expand=True, pady=(0, 5))
            
            # Actualizar toggle button
            state['toggle_btn'].configure(text="▼")
            state['is_expanded'] = True
            self.sheet_states[site_name] = 'loaded'
            
            print(f"[EXPAND] {site_name} expandido exitosamente")
            
        except Exception as e:
            print(f"[ERROR] _expand_content para {site_name}: {e}")
            import traceback
            traceback.print_exc()
    
    def _collapse_content(self, site_name):
        """Colapsa sitio: oculta ContentFrame (NO lo destruye).
        SiteContainer permanece en su posición.
        
        Args:
            site_name: Nombre del sitio
        """
        try:
            state = self.site_containers.get(site_name)
            if not state:
                return
            
            print(f"[COLLAPSE] Colapsando {site_name}...")
            
            # Ocultar ContentFrame (NO destruir)
            if state['content_frame']:
                state['content_frame'].pack_forget()
            
            # Actualizar toggle button
            state['toggle_btn'].configure(text="▶")
            state['is_expanded'] = False
            self.sheet_states[site_name] = 'collapsed'
            
            print(f"[COLLAPSE] {site_name} colapsado exitosamente")
            
        except Exception as e:
            print(f"[ERROR] _collapse_content para {site_name}: {e}")
            import traceback
            traceback.print_exc()
    
    def _render_sidebar_full(self, parent, site_name, site_data):
        """Crea sidebar completo con cámaras, firma y notas.
        Solo llamado cuando sitio está expandido.
        
        Args:
            parent: Frame padre
            site_name: Nombre del sitio
            site_data: Datos del sitio
            
        Returns:
            Frame del sidebar
        """
        try:
            import tkinter as tk
            import customtkinter
            
            sidebar = self.ui_factory.frame(parent, width=250, fg_color="#333333")
            
            # ───────────────────────────────────────────────────────────────
            # SECCIÓN: CÁMARAS (CON ENTRIES EDITABLES)
            # ───────────────────────────────────────────────────────────────
            cameras_label = self.ui_factory.label(
                sidebar,
                text="📹 CAMARAS",
                font=("Segoe UI", 10, "bold"),
                text_color="#ffffff"
            )
            cameras_label.pack(pady=(5, 5), padx=10, anchor="w")
            
            cameras_frame = self.ui_factory.frame(sidebar, fg_color="transparent")
            cameras_frame.pack(fill="x", padx=10, pady=5)
            
            # Total Cameras
            total_label = self.ui_factory.label(
                cameras_frame,
                text="Total:",
                font=("Segoe UI", 12),
                text_color="#aaaaaa"
            )
            total_label.grid(row=0, column=0, sticky="w", pady=2)
            
            total_var = tk.StringVar(value=str(site_data.get("total_cameras", 0)))
            total_entry = self.ui_factory.entry(
                cameras_frame,
                textvariable=total_var,
                width=80,
                font=("Segoe UI", 12)
            )
            total_entry.grid(row=0, column=1, sticky="ew", padx=(5, 0), pady=2)
            
            # Inactive Cameras
            inactive_label = self.ui_factory.label(
                cameras_frame,
                text="Down:",
                font=("Segoe UI", 12),
                text_color="#aaaaaa"
            )
            inactive_label.grid(row=1, column=0, sticky="w", pady=2)
            
            inactive_var = tk.StringVar(value=str(site_data.get("inactive_cameras", 0)))
            inactive_entry = self.ui_factory.entry(
                cameras_frame,
                textvariable=inactive_var,
                width=80,
                font=("Segoe UI", 12)
            )
            inactive_entry.grid(row=1, column=1, sticky="ew", padx=(5, 0), pady=2)
            
            cameras_frame.columnconfigure(1, weight=1)
            
            # Binding FocusOut para auto-save + actualizar color del header
            def on_camera_change(event):
                self._on_camera_change(site_name, total_var, inactive_var)
                # Actualizar color del header después de guardar
                self._update_header_color(site_name)
            
            total_entry.bind("<FocusOut>", on_camera_change)
            inactive_entry.bind("<FocusOut>", on_camera_change)
            
            # ───────────────────────────────────────────────────────────────
            # SEPARADOR
            # ───────────────────────────────────────────────────────────────
            separator = self.ui_factory.frame(sidebar, height=2, fg_color="#444444")
            separator.pack(fill="x", pady=5, padx=10)
            
            # ───────────────────────────────────────────────────────────────
            # SECCIÓN: ADMIN (Check + Firma)
            # ───────────────────────────────────────────────────────────────
            admin_label = self.ui_factory.label(
                sidebar,
                text="✅ REVISIÓN ADMIN",
                font=("Segoe UI", 10, "bold"),
                text_color="#ffffff"
            )
            admin_label.pack(pady=(3, 2), padx=10, anchor="w")
            
            admin_frame = self.ui_factory.frame(sidebar, fg_color="transparent")
            admin_frame.pack(fill="x", padx=10, pady=2)
            
            # Checkbox "Revisado"
            check_var = tk.BooleanVar(value=site_data.get("estado_check", False))
            
            check_button = tk.Checkbutton(
                admin_frame,
                text="Revisado",
                variable=check_var,
                command=lambda: self._on_check_toggle(site_name, check_var),
                bg="#2b2b2b",
                fg="#ffffff",
                selectcolor="#1e1e1e",
                activebackground="#2b2b2b",
                activeforeground="#ffffff",
                font=("Segoe UI", 12)
            )
            check_button.pack(anchor="w", pady=1)
            
            # Label de firma
            if site_data.get("id_admin") and site_data.get("timestamp_check"):
                admin_name = site_data.get("admin_name", "Unknown")
                timestamp_display = site_data.get("timestamp_check", "")
                firma_text = f"🖊️ {admin_name}\n{timestamp_display}"
            else:
                firma_text = "Sin firma"
            
            firma_label = self.ui_factory.label(
                admin_frame,
                text=firma_text,
                font=("Segoe UI", 9),
                text_color="#888888",
                justify="left"
            )
            firma_label.pack(anchor="w", pady=(5, 0))
            
            # Guardar referencia para actualizar desde _on_check_toggle
            if not hasattr(self, 'firma_labels'):
                self.firma_labels = {}
            self.firma_labels[site_name] = firma_label
            
            # ───────────────────────────────────────────────────────────────
            # SEPARADOR
            # ───────────────────────────────────────────────────────────────
            separator2 = self.ui_factory.frame(sidebar, height=2, fg_color="#444444")
            separator2.pack(fill="x", pady=5, padx=10)
            
            # ───────────────────────────────────────────────────────────────
            # SECCIÓN: NOTAS
            # ───────────────────────────────────────────────────────────────
            notas_label = self.ui_factory.label(
                sidebar,
                text="📝 NOTAS",
                font=("Segoe UI", 10, "bold"),
                text_color="#ffffff"
            )
            notas_label.pack(pady=(3, 2), padx=10, anchor="w")
            
            notas_textbox = customtkinter.CTkTextbox(sidebar, height=150)
            notas_textbox.pack(fill="both", expand=True, padx=10, pady=(0, 10))
            notas_textbox.insert("1.0", site_data.get("notes", ""))
            
            # Bind para guardar notas
            notas_textbox.bind("<FocusOut>", lambda e: self._save_notes(site_name, notas_textbox.get("1.0", "end-1c")))
            
            return sidebar
            
        except Exception as e:
            print(f"[ERROR] _render_sidebar_full para {site_name}: {e}")
            import traceback
            traceback.print_exc()
            return self.ui_factory.frame(parent, width=250, fg_color="#333333")
    
    def _render_sheet_full(self, parent, site_name, site_data, site_tickets_ids):
        """Crea tksheet completo con tickets.
        Solo llamado cuando sitio está expandido.
        
        Args:
            parent: Frame padre
            site_name: Nombre del sitio
            site_data: Datos del sitio
            site_tickets_ids: Lista de IDs de tickets
            
        Returns:
            Frame del sheet
        """
        try:
            import customtkinter
            
            sheet_container = self.ui_factory.frame(parent, fg_color="#2b2b2b")
            
            # ═══════════════════════════════════════════════════════════════
            # TOOLBAR: Botón de agregar ticket
            # ═══════════════════════════════════════════════════════════════
            toolbar_frame = self.ui_factory.frame(sheet_container, fg_color="#1e1e1e", height=40)
            toolbar_frame.pack(fill="x", padx=5, pady=(5, 0))
            toolbar_frame.pack_propagate(False)
            
            add_ticket_btn = customtkinter.CTkButton(
                toolbar_frame,
                text="➕ Agregar Ticket",
                width=150,
                height=30,
                fg_color="#00c853",
                hover_color="#00a040",
                font=("Segoe UI", 11, "bold"),
                command=lambda: self._add_ticket_row(site_name)
            )
            add_ticket_btn.pack(side="left", padx=5, pady=5)
            
            # Crear tksheet
            site_sheet = Sheet(
                sheet_container,
                headers=["ID", "Estado", "Asunto", "Solicitante", "Creado", "Asignado"],
                theme="dark blue",
                height=280,
                width=800,
                show_row_index=False,
                show_top_left=False,
                empty_horizontal=0,
                empty_vertical=0
            )
            
            site_sheet.enable_bindings([
                "single_select",
                "row_select",
                "copy",
                "column_width_resize",
                "cell_double_click",
                "edit_cell",
                "delete"
            ])
            
            # Cargar datos
            COLUMNS_WIDTHS = {
                "ID": 80,
                "Estado": 100,
                "Asunto": 430,
                "Solicitante": 100,
                "Creado": 180,
                "Asignado": 110
            }
            
            sheet_data = []
            for ticket_id in site_tickets_ids:
                if ticket_id in self.tickets_cache:
                    ticket = self.tickets_cache[ticket_id]
                    status = ticket.get("status", "Unknown")
                    status_emoji = "🟢"
                    if status.lower() in ["closed", "resolved"]:
                        status_emoji = "🔴"
                    elif status.lower() in ["pending", "onhold", "pending resolution"]:
                        status_emoji = "🟡"
                    
                    sheet_data.append([
                        ticket_id,
                        f"{status_emoji} {status}",
                        ticket.get("subject", "Sin asunto"),
                        ticket.get("requester", "Sin solicitante"),
                        ticket.get("created_time", "N/A"),
                        ticket.get("technician", "Sin técnico")
                    ])
                else:
                    sheet_data.append([
                        ticket_id,
                        "⚠️ No encontrado",
                        "N/A",
                        "N/A",
                        "N/A",
                        "N/A"
                    ])
            
            if sheet_data:
                site_sheet.set_sheet_data(sheet_data)
            
            # Aplicar anchos de columnas
            column_headers = ["ID", "Estado", "Asunto", "Solicitante", "Creado", "Asignado"]
            for idx, col_name in enumerate(column_headers):
                if col_name in COLUMNS_WIDTHS:
                    try:
                        site_sheet.set_column_width(idx, COLUMNS_WIDTHS[col_name])
                    except Exception:
                        site_sheet.column_width(column=idx, width=COLUMNS_WIDTHS[col_name])
            
            site_sheet.pack(fill="both", expand=True)
            
            # Bind eventos
            site_sheet.bind("<Double-Button-1>", lambda e, s=site_sheet: self._on_sheet_double_click(s))
            site_sheet.bind("<<SheetModified>>", lambda e, s=site_sheet, sn=site_name: self._on_cell_edit(e, s, sn))
            site_sheet.bind("<Delete>", lambda e, s=site_sheet, sn=site_name: self._on_delete_row(s, sn))
            
            # Guardar referencia
            self.site_sheets[site_name] = site_sheet
            
            print(f"[SHEET] Sheet de {site_name} creado con {len(sheet_data)} tickets")
            
            return sheet_container
            
        except Exception as e:
            print(f"[ERROR] _render_sheet_full para {site_name}: {e}")
            import traceback
            traceback.print_exc()
            return self.ui_factory.frame(parent, fg_color="#2b2b2b")
    
    # ═══════════════════════════════════════════════════════════════
    # DEPRECATED: Métodos antiguos (mantener por compatibilidad)
    # ═══════════════════════════════════════════════════════════════
    
    def _expand_site_full(self, site_name, *args, **kwargs):
        """DEPRECATED: Usa _expand_content()"""
        print(f"[DEPRECATED] _expand_site_full llamado para {site_name}, usando _expand_content()")
        self._expand_content(site_name)
    
    def _collapse_site_full(self, site_name, *args, **kwargs):
        """DEPRECATED: Usa _collapse_content()"""
        print(f"[DEPRECATED] _collapse_site_full llamado para {site_name}, usando _collapse_content()")
        self._collapse_content(site_name)
    
    def _toggle_site_accordion(self, site_name):
        """DEPRECATED: Usa _toggle_site()"""
        print(f"[DEPRECATED] _toggle_site_accordion llamado para {site_name}, usando _toggle_site()")
        self._toggle_site(site_name)
    
    def _expand_site_lazy(self, site_name):
        """DEPRECATED: Usa _expand_content()"""
        print(f"[DEPRECATED] _expand_site_lazy llamado para {site_name}, usando _expand_content()")
        self._expand_content(site_name)
    
    def _collapse_site(self, site_name):
        """DEPRECATED: Usa _collapse_content()"""
        print(f"[DEPRECATED] _collapse_site llamado para {site_name}, usando _collapse_content()")
        self._collapse_content(site_name)
    
    def _load_sheet_in_accordion(self, site_name):
        """DEPRECATED: Usa _expand_content()"""
        print(f"[DEPRECATED] _load_sheet_in_accordion llamado para {site_name}")
        pass
    
    # ═══════════════════════════════════════════════════════════════
    # HELPERS: Métodos auxiliares para sidebar
    # ═══════════════════════════════════════════════════════════════
    
    def _toggle_revision(self, site_name, check_var):
        """Toggle de revisión de healthcheck
        
        Args:
            site_name: Nombre del sitio
            check_var: Variable del checkbox
        """
        try:
            is_checked = check_var.get()
            
            # Guardar en BD
            success, error_msg = self.controller.save_healthcheck_revision(
                site_name, 
                is_checked,
                self.username
            )
            
            if not success:
                messagebox.showerror("Error", error_msg or "No se pudo guardar la revisión")
                check_var.set(not is_checked)  # Revertir
                return
            
            # Actualizar cache local
            if site_name in self.sites_data_cache:
                self.sites_data_cache[site_name]["estado_check"] = is_checked
                if is_checked:
                    self.sites_data_cache[site_name]["admin_name"] = self.username
            
            action = "marcado" if is_checked else "desmarcado"
            print(f"[INFO] Revisión {action} para {site_name}")
            
        except Exception as e:
            print(f"[ERROR] _toggle_revision: {e}")
            import traceback
            traceback.print_exc()
    
    def _save_notes(self, site_name, notes_text):
        """Guarda notas del healthcheck (auto-save)
        
        Args:
            site_name: Nombre del sitio
            notes_text: Contenido de las notas
        """
        try:
            # Guardar en BD
            success, error_msg = self.controller.save_healthcheck_notes(site_name, notes_text)
            
            if not success:
                print(f"[ERROR] No se pudieron guardar notas para {site_name}: {error_msg}")
                return
            
            # Actualizar cache local
            if site_name in self.sites_data_cache:
                self.sites_data_cache[site_name]["notes"] = notes_text.strip()
            
            print(f"[INFO] Notas guardadas para {site_name}")
            
        except Exception as e:
            print(f"[ERROR] _save_notes: {e}")
            import traceback
            traceback.print_exc()
        pass
    
    def _load_sheet_in_accordion(self, site_name):
        """DEPRECATED: Usa _render_sheet_full"""
        print(f"[DEPRECATED] _load_sheet_in_accordion llamado para {site_name}")
        pass
    
    def _load_sheet_on_demand(self, site_name, sheet_container, COLUMNS_WIDTHS):
        """DEPRECATED: Mantenido por compatibilidad, redirige a accordion
        
        Este método ya no se usa en la nueva implementación accordion,
        pero se mantiene para evitar romper referencias existentes.
        """
        print(f"[DEPRECATED] _load_sheet_on_demand llamado para {site_name}, usando accordion...")
        self._expand_site_lazy(site_name)
    
    def _on_sheet_double_click(self, sheet):
        """Maneja el doble clic en un sheet para abrir detalles del ticket"""
        try:
            selected = sheet.get_currently_selected()
            if selected is None or selected.row is None:
                return
            
            row_data = sheet.get_row_data(selected.row)
            if not row_data or not row_data[0]:
                return
            
            ticket_id = str(row_data[0]).strip()
            print(f"[INFO] Abriendo detalles del ticket {ticket_id}")
            self.open_ticket_detailes("/" + ticket_id)
            
        except Exception as e:
            print(f"[ERROR] _on_sheet_double_click: {e}")
            import traceback
            traceback.print_exc()
    
    def _save_camera_counts(self, site_name, total_str, down_str, header_frame):
        """Guarda contadores de cámaras automáticamente al perder foco
        
        LEGACY: Este método se mantiene para compatibilidad con código anterior.
        El nuevo sidebar usa _on_camera_change()
        
        Args:
            site_name: Nombre del sitio
            total_str: Valor del input de total cámaras (string)
            down_str: Valor del input de cámaras inactivas (string)
            header_frame: Frame del header para actualizar color
        """
        try:
            # Validar que sean números
            total = int(total_str) if total_str.strip() else 0
            down = int(down_str) if down_str.strip() else 0
            
            # Guardar en BD
            success, warning = self.controller.update_camera_counts(site_name, total, down)
            
            if not success:
                messagebox.showerror("Error", warning or "No se pudo actualizar los contadores de cámaras")
                return
            
            # Mostrar advertencia si existe (pero ya se guardó)
            if warning:
                messagebox.showwarning("Advertencia", warning)
            
            # Actualizar cache local
            if site_name in self.sites_data_cache:
                self.sites_data_cache[site_name]["total_cameras"] = total
                self.sites_data_cache[site_name]["inactive_cameras"] = down
            
            # Actualizar color del header según nuevo porcentaje
            if total > 0:
                percentage_down = (down / total) * 100
                if percentage_down <= 10:
                    new_color = "#00c853"  # Verde
                elif percentage_down <= 30:
                    new_color = "#ffb300"  # Amarillo
                else:
                    new_color = "#ff3d00"  # Rojo
            else:
                new_color = "#256ff9"  # Azul (sin datos)
            
            try:
                header_frame.configure(fg_color=new_color)
            except Exception:
                pass  # Si falla el cambio de color, continuar
            
            print(f"[INFO] Cámaras actualizadas para {site_name}: total={total}, down={down}")
            
        except ValueError:
            messagebox.showerror("Error de Validación", "Los valores deben ser números enteros")
        except Exception as e:
            print(f"[ERROR] _save_camera_counts: {e}")
            import traceback
            traceback.print_exc()
            messagebox.showerror("Error", f"Error al guardar: {str(e)}")
    
    # ═══════════════════════════════════════════════════════════════════════
    # HEALTHCHECK SIDEBAR - MÉTODOS NUEVOS
    # ═══════════════════════════════════════════════════════════════════════
    
    def _create_healthcheck_sidebar(self, parent, site_name, site_data):
        """Crea el frame lateral con información de Healthcheck
        
        Args:
            parent: Widget padre
            site_name: Nombre del sitio
            site_data: Dict con datos del sitio desde cache
        
        Returns:
            Frame del sidebar
        """
        try:
            # Sidebar frame (280px width para acomodar notas, fondo oscuro)
            sidebar = self.ui_factory.frame(parent, fg_color="#2b2b2b", corner_radius=5)
            sidebar.configure(width=280, height=290)  # Width y height fijos
            sidebar.pack_propagate(False)  # Mantener dimensiones fijas
            
            # ───────────────────────────────────────────────────────────────
            # HEADER: Nombre del sitio (truncado si es muy largo)
            # ───────────────────────────────────────────────────────────────
            
            # ───────────────────────────────────────────────────────────────
            # SECCIÓN: CÁMARAS
            # ───────────────────────────────────────────────────────────────
            cameras_label = self.ui_factory.label(
                sidebar,
                text="📹 CAMARAS",
                font=("Segoe UI", 10, "bold"),
                text_color="#ffffff"
            )
            cameras_label.pack(pady=(5, 5), padx=10, anchor="w")
            
            cameras_frame = self.ui_factory.frame(sidebar, fg_color="transparent")
            cameras_frame.pack(fill="x", padx=10, pady=5)
            
            # Total Cameras
            total_label = self.ui_factory.label(
                cameras_frame,
                text="Total:",
                font=("Segoe UI", 12),
                text_color="#aaaaaa"
            )
            total_label.grid(row=0, column=0, sticky="w", pady=2)
            
            total_var = tk.StringVar(value=str(site_data.get("total_cameras", 0)))
            total_entry = self.ui_factory.entry(
                cameras_frame,
                textvariable=total_var,
                width=80,
                font=("Segoe UI", 12)
            )
            total_entry.grid(row=0, column=1, sticky="ew", padx=(5, 0), pady=2)
            
            # Inactive Cameras
            inactive_label = self.ui_factory.label(
                cameras_frame,
                text="Down:",
                font=("Segoe UI", 12),
                text_color="#aaaaaa"
            )
            inactive_label.grid(row=1, column=0, sticky="w", pady=2)
            
            inactive_var = tk.StringVar(value=str(site_data.get("inactive_cameras", 0)))
            inactive_entry = self.ui_factory.entry(
                cameras_frame,
                textvariable=inactive_var,
                width=80,
                font=("Segoe UI", 12)
            )
            inactive_entry.grid(row=1, column=1, sticky="ew", padx=(5, 0), pady=2)
            
            cameras_frame.columnconfigure(1, weight=1)
            
            # Binding FocusOut para auto-save
            def on_camera_change(event):
                self._on_camera_change(site_name, total_var, inactive_var)
            
            total_entry.bind("<FocusOut>", on_camera_change)
            inactive_entry.bind("<FocusOut>", on_camera_change)
            
            # ───────────────────────────────────────────────────────────────
            # SEPARADOR
            # ───────────────────────────────────────────────────────────────
            separator = self.ui_factory.frame(sidebar, height=2, fg_color="#444444")
            separator.pack(fill="x", pady=5, padx=10)
            
            # ───────────────────────────────────────────────────────────────
            # SECCIÓN: ADMIN (Check + Firma)
            # ───────────────────────────────────────────────────────────────
            admin_label = self.ui_factory.label(
                sidebar,
                text="✅ REVISIÓN ADMIN",
                font=("Segoe UI", 10, "bold"),
                text_color="#ffffff"
            )
            admin_label.pack(pady=(3, 2), padx=10, anchor="w")
            
            admin_frame = self.ui_factory.frame(sidebar, fg_color="transparent")
            admin_frame.pack(fill="x", padx=10, pady=2)
            
            # Checkbox "Revisado"
            check_var = tk.BooleanVar(value=site_data.get("estado_check", False))
            
            # TODO: En versión futura, deshabilitar si user_role != "Admin"
            check_button = tk.Checkbutton(
                admin_frame,
                text="Revisado",
                variable=check_var,
                command=lambda: self._on_check_toggle(site_name, check_var),
                bg="#2b2b2b",
                fg="#ffffff",
                selectcolor="#1e1e1e",
                activebackground="#2b2b2b",
                activeforeground="#ffffff",
                font=("Segoe UI", 12)
            )
            check_button.pack(anchor="w", pady=1)
            
            # Label de firma
            if site_data.get("id_admin") and site_data.get("timestamp_check"):
                admin_name = site_data.get("admin_name", "Unknown")
                timestamp = site_data.get("timestamp_check")
                try:
                    if isinstance(timestamp, str):
                        timestamp_display = timestamp[:16]  # YYYY-MM-DD HH:MM
                    else:
                        timestamp_display = timestamp.strftime("%Y-%m-%d %H:%M")
                except:
                    timestamp_display = str(timestamp)
                
                firma_text = f"🖊️ {admin_name}\n{timestamp_display}"
            else:
                firma_text = "Sin firma"
            
            firma_label = self.ui_factory.label(
                admin_frame,
                text=firma_text,
                font=("Segoe UI", 9),
                text_color="#aaaaaa"
            )
            firma_label.pack(anchor="w", pady=1)
            
            # Guardar referencia para actualizar después
            if not hasattr(self, 'firma_labels'):
                self.firma_labels = {}
            self.firma_labels[site_name] = firma_label
            
            # ───────────────────────────────────────────────────────────────
            # SEPARADOR
            # ───────────────────────────────────────────────────────────────
            separator2 = self.ui_factory.frame(sidebar, height=2, fg_color="#444444")
            separator2.pack(fill="x", pady=3, padx=10)
            
            # ───────────────────────────────────────────────────────────────
            # SECCIÓN: NOTAS
            # ───────────────────────────────────────────────────────────────
            notes_label = self.ui_factory.label(
                sidebar,
                text="📝 NOTAS",
                font=("Segoe UI", 10, "bold"),
                text_color="#ffffff"
            )
            notes_label.pack(pady=(3, 3), padx=10, anchor="w")
            
            # Textbox para notas (multilínea, más grande)
            notes_text = tk.Text(
                sidebar,
                height=8,  # Más altura para ver mejor las notas
                width=30,  # Ancho ajustado al nuevo sidebar
                bg="#1e1e1e",
                fg="#ffffff",
                font=("Segoe UI", 9),
                wrap="word",
                relief="solid",
                borderwidth=1,
                highlightthickness=1,
                highlightbackground="#4aa3ff",
                highlightcolor="#4aa3ff"
            )
            notes_text.insert("1.0", site_data.get("notes", ""))
            notes_text.pack(padx=10, pady=(3, 8), fill="both", expand=True)
            
            # Binding FocusOut para auto-save
            def on_notes_save(event):
                notes_content = notes_text.get("1.0", "end-1c")
                self._on_notes_save(site_name, notes_content)
            
            notes_text.bind("<FocusOut>", on_notes_save)
            
            return sidebar
            
        except Exception as e:
            print(f"[ERROR] _create_healthcheck_sidebar para {site_name}: {e}")
            import traceback
            traceback.print_exc()
            # Retornar frame vacío en caso de error
            return self.ui_factory.frame(parent, width=250, fg_color="#2b2b2b")
    
    def _on_camera_change(self, site_name, total_var, inactive_var):
        """Handler: auto-save de cámaras al perder foco
        
        Args:
            site_name: Nombre del sitio
            total_var: StringVar del input de total
            inactive_var: StringVar del input de inactive
        """
        try:
            total_str = total_var.get().strip()
            inactive_str = inactive_var.get().strip()
            
            # Llamar al controller
            success, msg = self.controller.update_camera_counts(site_name, total_str, inactive_str)
            
            if not success:
                # Error crítico, revertir valores
                if site_name in self.sites_data_cache:
                    total_var.set(str(self.sites_data_cache[site_name].get("total_cameras", 0)))
                    inactive_var.set(str(self.sites_data_cache[site_name].get("inactive_cameras", 0)))
                print("Error", msg or "No se pudo actualizar")
                return
            
            if msg:
                # Hay warning (inactive > total) pero se guardó
                print("Advertencia", msg)
            
            # Actualizar cache local
            try:
                total_int = int(total_str) if total_str else 0
                inactive_int = int(inactive_str) if inactive_str else 0
                
                if site_name in self.sites_data_cache:
                    self.sites_data_cache[site_name]["total_cameras"] = total_int
                    self.sites_data_cache[site_name]["inactive_cameras"] = inactive_int
            except:
                pass
            
            print(f"[INFO] HC: Cámaras actualizadas para {site_name}")
            
        except Exception as e:
            print(f"[ERROR] _on_camera_change: {e}")
            import traceback
            traceback.print_exc()
            messagebox.showerror("Error", f"Error inesperado: {str(e)}")
    
    def _update_header_color(self, site_name):
        """Actualiza el color del header basado en el porcentaje de cámaras caídas
        
        Args:
            site_name: Nombre del sitio
        """
        try:
            # Verificar que el sitio existe en containers
            if site_name not in self.site_containers:
                return
            
            # Obtener datos actualizados del cache
            site_data = self.sites_data_cache.get(site_name, {})
            total_cameras = int(site_data.get("total_cameras", 0) or 0)
            inactive_cameras = int(site_data.get("inactive_cameras", 0) or 0)
            
            # Calcular color según % de cámaras caídas
            if total_cameras > 0:
                percentage_down = (inactive_cameras / total_cameras) * 100
                if percentage_down <= 10:
                    header_color = "#00c853"  # Verde
                elif percentage_down <= 30:
                    header_color = "#ffb300"  # Amarillo
                else:
                    header_color = "#ff3d00"  # Rojo
            else:
                header_color = "#256ff9"  # Azul (sin datos)
            
            # Actualizar el color del header_row
            header_row = self.site_containers[site_name].get('header_row')
            if header_row and header_row.winfo_exists():
                header_row.configure(fg_color=header_color)
                print(f"[INFO] HC: Header color actualizado para {site_name}: {header_color}")
            
        except Exception as e:
            print(f"[ERROR] _update_header_color: {e}")
            import traceback
            traceback.print_exc()
    
    def _on_check_toggle(self, site_name, check_var):
        """Handler: toggle del check de revisión + firma
        
        Args:
            site_name: Nombre del sitio
            check_var: BooleanVar del checkbox
        """
        try:
            is_checked = check_var.get()
            
            # Llamar al controller
            success, error_msg = self.controller.toggle_healthcheck_check(site_name, is_checked)
            
            if not success:
                # Revertir checkbox en UI
                check_var.set(not is_checked)
                messagebox.showerror("Error", error_msg or "No se pudo actualizar el check")
                return
            
            # Actualizar label de firma
            if is_checked:
                # Firmado ahora
                from datetime import datetime
                timestamp_display = datetime.now().strftime("%Y-%m-%d %H:%M")
                firma_text = f"🖊️ {self.username}\n{timestamp_display}"
            else:
                # Desmarcado
                firma_text = "Sin firma"
            
            # Actualizar label si existe
            if hasattr(self, 'firma_labels') and site_name in self.firma_labels:
                try:
                    self.firma_labels[site_name].configure(text=firma_text)
                except:
                    pass
            
            # Actualizar cache local
            if site_name in self.sites_data_cache:
                self.sites_data_cache[site_name]["estado_check"] = is_checked
            
            action = "marcado" if is_checked else "desmarcado"
            print(f"[INFO] HC: Check {action} para {site_name}")
            
        except Exception as e:
            print(f"[ERROR] _on_check_toggle: {e}")
            import traceback
            traceback.print_exc()
            messagebox.showerror("Error", f"Error inesperado: {str(e)}")
    
    def _on_notes_save(self, site_name, notes_text):
        """Handler: auto-save de notas al perder foco
        
        Args:
            site_name: Nombre del sitio
            notes_text: Contenido de las notas
        """
        try:
            # Llamar al controller (silencioso, no muestra mensajes de éxito)
            success, error_msg = self.controller.save_healthcheck_notes(site_name, notes_text)
            
            if not success:
                messagebox.showerror("Error", error_msg or "No se pudieron guardar las notas")
                return
            
            # Actualizar cache local
            if site_name in self.sites_data_cache:
                self.sites_data_cache[site_name]["notes"] = notes_text.strip()
            
            # Sin feedback visual (silencioso)
            print(f"[INFO] HC: Notas guardadas para {site_name} ({len(notes_text)} chars)")
            
        except Exception as e:
            print(f"[ERROR] _on_notes_save: {e}")
            import traceback
            traceback.print_exc()
            # No mostrar error al usuario (guardado silencioso)
    
    def _add_ticket_row(self, site_name):
        """Agrega una fila vacía al sheet de un sitio específico"""
        sheet = self.site_sheets.get(site_name)
        if sheet:
            current_data = sheet.get_sheet_data()
            new_row = ["", "", "", "", "", ""]
            current_data.append(new_row)
            sheet.set_sheet_data(current_data)
            print("[INFO] Fila agregada a {site_name}")
            print("Ticket Agregado", "Fila vacía agregada a {site_name}. Ingresa el ID del ticket en la primera columna.")
        else:
            print(f"[WARN] No se encontró sheet para {site_name}")
    
    def _on_delete_row(self, sheet, site_name):
        """Elimina la fila seleccionada del sheet y de la BD"""
        try:
            selected = sheet.get_currently_selected()
            if selected is None or selected.row is None:
                messagebox.showwarning("Sin selección", "Selecciona una fila para eliminar")
                return
            
            # Obtener el ID del ticket antes de eliminar
            row_data = sheet.get_row_data(selected.row)
            if not row_data or not row_data[0]:
                # Si es una fila vacía, simplemente eliminarla
                current_data = sheet.get_sheet_data()
                if 0 <= selected.row < len(current_data):
                    del current_data[selected.row]
                    sheet.set_sheet_data(current_data)
                    print(f"[INFO] Fila vacía eliminada de {site_name}")
                return
            
            ticket_id = str(row_data[0]).strip()
            
            # Confirmar eliminación
            confirm = messagebox.askyesno(
                "Confirmar Eliminación",
                f"¿Eliminar ticket {ticket_id} de {site_name}?\n\nSe eliminará de la vista y de la base de datos."
            )
            
            if not confirm:
                return
            
            # Eliminar de la BD
            success = self.controller.delete_ticket(ticket_id, site_name)
            if not success:
                messagebox.showerror("Error", f"No se pudo eliminar el ticket {ticket_id} de la base de datos")
                return
            
            # Eliminar de la vista
            current_data = sheet.get_sheet_data()
            if 0 <= selected.row < len(current_data):
                del current_data[selected.row]
                sheet.set_sheet_data(current_data)
                
                # Actualizar el contador en el cache
                if site_name in self.tickets_by_site and ticket_id in self.tickets_by_site[site_name]:
                    self.tickets_by_site[site_name].remove(ticket_id)
                
                print(f"[INFO] Ticket {ticket_id} eliminado de {site_name}")
                messagebox.showinfo("Éxito", f"Ticket {ticket_id} eliminado correctamente")
            
        except Exception as e:
            print(f"[ERROR] Error eliminando fila: {e}")
            import traceback
            traceback.print_exc()
            messagebox.showerror("Error", f"Error al eliminar: {str(e)}")
    
    
    def _on_cell_edit(self, event, sheet, site_name):
        """Maneja la edición de celdas - inserta en BD y autocompleta desde JSON"""
        try:
            selected = sheet.get_currently_selected()
            if selected is None or selected.row is None or selected.column is None:
                return
            
            # Solo procesar si editaron la columna ID (columna 0)
            if selected.column != 0:
                return
            
            # Obtener el ID ingresado
            row_data = sheet.get_row_data(selected.row)
            if not row_data or not row_data[0]:
                return
            
            ticket_id = str(row_data[0]).strip()
            print(f"[DEBUG] Procesando ticket ID: {ticket_id} en sitio {site_name}")
            
            # 1. Insertar en BD
            print("[DEBUG] Insertando ticket {ticket_id} en BD...")
            success = self.controller.insert_ticket(ticket_id, site_name)
            if not success:
                messagebox.showerror("Error BD", f"No se pudo insertar el ticket {ticket_id} en la base de datos")
                return
            
            print("[INFO] Ticket {ticket_id} insertado en BD exitosamente")
            
            # 2. Buscar en cache JSON
            if ticket_id not in self.tickets_cache:
                print("[INFO] Ticket {ticket_id} no encontrado en cache, buscando en API...")
                
                # Intentar obtener de la API
                ticket = self.controller.fetch_missing_ticket(ticket_id)
                
                if ticket:
                    # Ticket encontrado en API y agregado al JSON
                    print("[SUCCESS] Ticket {ticket_id} obtenido de API")
                    
                    # Agregar al cache en memoria
                    self.tickets_cache[ticket_id] = ticket
                    
                    # Autocompletar la fila
                    status = ticket.get("status", "Unknown")
                    status_emoji = "🟢"
                    if status.lower() in ["closed", "resolved"]:
                        status_emoji = "🔴"
                    elif status.lower() in ["pending", "onhold", "pending resolution"]:
                        status_emoji = "🟡"
                    
                    new_row = [
                        ticket_id,
                        f"{status_emoji} {status}",
                        ticket.get("subject", "Sin asunto"),
                        ticket.get("requester", "Sin solicitante"),
                        ticket.get("created_time", "N/A"),
                        ticket.get("technician", "Sin técnico")
                    ]
                    
                    sheet.set_row_data(selected.row, values=new_row)
                    print(
                        "Ticket Encontrado",
                        "Ticket {ticket_id} obtenido de la API y agregado al JSON.\n\n"
                        "Otros supervisores ahora podrán verlo."
                    )
                    return
                else:
                    # No encontrado en API tampoco
                    messagebox.showwarning(
                        "Ticket no encontrado", 
                        "El ticket {ticket_id} no existe en el JSON ni en la API.\n\n"
                        "Se guardó en BD pero sin detalles."
                    )
                    # Dejar la fila con "No encontrado"
                    new_row = [
                        ticket_id,
                        "⚠️ No encontrado",
                        "N/A",
                        "N/A",
                        "N/A",
                        "N/A"
                    ]
                    sheet.set_row_data(selected.row, values=new_row)
                    return
            
            # 3. Autocompletar desde JSON
            ticket = self.tickets_cache[ticket_id]
            
            status = ticket.get("status", "Unknown")
            status_emoji = "🟢"
            if status.lower() in ["closed", "resolved"]:
                status_emoji = "🔴"
            elif status.lower() in ["pending", "onhold", "pending resolution"]:
                status_emoji = "🟡"
            
            new_row = [
                ticket_id,
                f"{status_emoji} {status}",
                ticket.get("subject", "Sin asunto"),
                ticket.get("requester", "Sin solicitante"),
                ticket.get("created_time", "N/A"),
                ticket.get("technician", "Sin técnico")
            ]
            
            sheet.set_row_data(selected.row, values=new_row)
            print(f"[INFO] Ticket {ticket_id} autocompletado en {site_name}")
            
        except Exception as e:
            print(f"[ERROR] Error en _on_cell_edit: {e}")
            import traceback
            traceback.print_exc()
    
    def _refresh_tree_data(self):
        """Refresca los sheets vacíos"""
        print("[INFO] Refrescando sheets...")
        self._load_tree_data()
    
    def _search_duplicate(self):
        """Busca tickets duplicados (placeholder)"""
        messagebox.showinfo("Buscar duplicado", "Funcionalidad de búsqueda de duplicados en desarrollo.")
    
    def _populate_site_search(self):
        """Puebla el combobox de búsqueda con LAZY LOADING (50 iniciales, filtrado de lista completa)"""
        try:
            # Extraer lista plana de todos los sitios
            all_sites = []
            for group_name, sites_list in self.sites_by_group.items():
                all_sites.extend(sites_list)
            
            # Ordenar alfabéticamente
            all_sites.sort()
            
            # ═══════════════════════════════════════════════════════════════
            # OPTIMIZATION: Lazy loading del combobox
            # ═══════════════════════════════════════════════════════════════
            # Por qué:
            # - 300+ sitios en combobox causa slowdown al abrir dropdown
            # - Usuario típicamente filtra, no scrollea toda la lista
            # - FilteredCombobox busca en original_values, no en ['values']
            #
            # Estrategia:
            # 1. ['values'] = primeros 50 sitios (carga rápida de dropdown)
            # 2. original_values = lista completa (para filtrado)
            # 3. Usuario escribe → filtrado usa original_values automáticamente
            # ═══════════════════════════════════════════════════════════════
            
            if hasattr(self, 'site_search_combo'):
                # Lista completa para filtrado
                full_list = tuple(all_sites)
                
                # Solo primeros 50 para dropdown inicial
                initial_list = tuple(all_sites[:50]) if len(all_sites) > 50 else full_list
                
                # Configurar combobox
                self.site_search_combo['values'] = initial_list
                self.site_search_combo.original_values = full_list
                
                print(f"[INFO] Combobox poblado: {len(initial_list)} visibles, {len(full_list)} filtrables")
        
        except Exception as e:
            print(f"[ERROR] _populate_site_search: {e}")
            import traceback
            traceback.print_exc()
    
    def _on_site_selected(self):
        """Handler cuando se selecciona un sitio en el combobox de búsqueda"""
        try:
            site_name = self.site_search_var.get()
            if site_name:
                self._navigate_to_site(site_name)
        except Exception as e:
            print(f"[ERROR] _on_site_selected: {e}")
            import traceback
            traceback.print_exc()
    
    def _navigate_to_site(self, site_name):
        """Navega al sitio especificado: cambia de tab y hace scroll (con espera si está cargando)
        
        Args:
            site_name: Nombre del sitio a buscar
        """
        try:
            # 1. Buscar grupo del sitio
            target_group = None
            for group_name, sites_list in self.sites_by_group.items():
                if site_name in sites_list:
                    target_group = group_name
                    break
            
            if not target_group:
                print(f"[WARNING] Sitio '{site_name}' no encontrado en ningún grupo")
                messagebox.showwarning("Sitio no encontrado", f"El sitio '{site_name}' no está disponible")
                return
            
            # 2. Cambiar al tab del grupo
            group_names = sorted(self.sites_by_group.keys())
            try:
                tab_index = group_names.index(target_group)
                self.notebook.select(tab_index)
                print(f"[NAV] Cambiando a tab {tab_index}: {target_group}")
            except ValueError:
                print(f"[ERROR] Grupo '{target_group}' no encontrado en tabs")
                return
            
            # ═══════════════════════════════════════════════════════════════
            # SAFE NAVIGATION: Esperar a que termine el chunked rendering
            # ═══════════════════════════════════════════════════════════════
            # Por qué:
            # - Si el grupo está en chunked rendering, el widget puede no existir
            # - Forzar Sheet creation si está en placeholder
            # - Garantizar scroll preciso después de render completo
            # ═══════════════════════════════════════════════════════════════
            
            # 3. Garantizar carga del grupo (guard delegado a _load_group_data)
            self._load_group_data(target_group)
            
            # 4. Si está cargando, esperar a que termine
            if target_group in self.loading_groups:
                print(f"[NAV] Grupo {target_group} cargando, esperando...")
                # Programar navegación después del render
                self.notebook.after(100, lambda: self._navigate_to_site(site_name))
                return
            
            # 5. Auto-expandir si está colapsado
            state = self.site_containers.get(site_name)
            if state and not state['is_expanded']:
                print(f"[NAV] Sitio {site_name} colapsado, expandiendo automáticamente...")
                self._expand_content(site_name)
            # ═══════════════════════════════════════════════════════════════
            
            # 6. Esperar a que el widget esté renderizado (necesario después de lazy load)
            self.notebook.update_idletasks()
            
            # 7. Obtener referencias al canvas y widget del sitio
            canvas = self.group_canvas.get(target_group)
            site_widget = self.site_widgets.get((target_group, site_name))
            
            if not canvas:
                print(f"[ERROR] Canvas no encontrado para grupo '{target_group}'")
                return
            
            if not site_widget:
                print(f"[ERROR] Widget no encontrado para sitio '{site_name}'")
                return
            
            # 8. Calcular posición del sitio en el scrollable_frame
            scrollable_frame = self.group_scrollable_frames.get(target_group)
            if not scrollable_frame:
                print(f"[ERROR] Scrollable frame no encontrado para grupo '{target_group}'")
                return
            
            # Forzar actualización de geometría
            canvas.update_idletasks()
            scrollable_frame.update_idletasks()
            
            # ═══════════════════════════════════════════════════════════════
            # SCROLL PRECISO: Calcular posición basada en VIEWPORT visible
            # ═══════════════════════════════════════════════════════════════
            # 1. Obtener dimensiones
            bbox = canvas.bbox("all")  # Región scrollable total
            if not bbox:
                print(f"[WARNING] No se pudo obtener bbox del canvas")
                return
            
            total_height = bbox[3]  # Altura total del contenido
            viewport_height = canvas.winfo_height()  # Altura visible
            widget_y = site_widget.winfo_y()  # Posición Y del widget
            widget_height = site_widget.winfo_height()  # Altura del widget
            widget_bottom = widget_y + widget_height
            
            # 2. CASO BORDE: Si el widget está en el último viewport, forzar scroll al final
            if widget_bottom >= total_height - viewport_height:
                # Widget está dentro del último viewport visible
                canvas.yview_moveto(1.0)
                print(f"[NAV] Scroll a final: sitio='{site_name}' (último viewport)")
            elif total_height > viewport_height:
                # 3. CASO NORMAL: Calcular offset basado en viewport (20%)
                offset_pixels = viewport_height * 0.2  # 20% del VIEWPORT, no del total
                target_y_pixels = max(0, widget_y - offset_pixels)
                
                # 4. Convertir a fracción (0.0 - 1.0)
                scroll_fraction = target_y_pixels / total_height
                scroll_fraction = min(1.0, max(0.0, scroll_fraction))  # Clamp
                
                # 5. Aplicar scroll
                canvas.yview_moveto(scroll_fraction)
                print(f"[NAV] Scroll ejecutado: sitio='{site_name}', pos={scroll_fraction:.3f}")
            else:
                # Todo el contenido es visible, no se necesita scroll
                print(f"[NAV] Contenido completamente visible, no se requiere scroll")
            # ═══════════════════════════════════════════════════════════════
            
            # 9. Feedback visual (opcional: highlight temporal)
            try:
                original_color = site_widget.cget("fg_color") if hasattr(site_widget, 'cget') else None
                if original_color:
                    site_widget.configure(fg_color="#3a5f7d")  # Highlight azul
                    self.notebook.after(800, lambda: site_widget.configure(fg_color=original_color))
            except:
                pass  # Si falla el highlight, continuar sin él
            
            print(f"[SUCCESS] Navegación completada: {site_name} en {target_group}")
            
        except Exception as e:
            print(f"[ERROR] _navigate_to_site: {e}")
            import traceback
            traceback.print_exc()
            messagebox.showerror("Error de Navegación", f"No se pudo navegar al sitio:\n{str(e)}")
    
    def _on_tree_double_click(self, event):
        """Maneja el doble clic en el árbol"""
        selection = self.tree.selection()
        if not selection:
            return
        
        item = selection[0]
        values = self.tree.item(item, "values")
        
        # Si tiene values, es un ticket (no un sitio)
        if values:
            ticket_id = values[0]
            print(f"[INFO] Abriendo detalles del ticket {ticket_id}")
            self.open_ticket_detailes("/" + str(ticket_id))


    