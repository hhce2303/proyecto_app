"""
admin_window.py
================
Interfaz administrativa completa con Dashboard en tiempo real, gestión de usuarios,
control de sesiones, auditoría avanzada y configuración del sistema.

Autor: Sistema Daily Log
Fecha: 2025-01-07
"""

import tkinter as tk
from tkinter import ttk, messagebox, font as tkfont
import customtkinter as ctk
from datetime import datetime, timedelta
from models.database import get_connection
from models.admin_model import force_logout_user, get_covers_graph_data, get_dashboard_metrics, get_activity_graph_data, get_active_sessions_detailed, get_pending_alerts
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import traceback

# ==================== CONFIGURACIÓN GLOBAL ====================
ADMIN_WINDOW = None
AUTO_REFRESH_INTERVAL = 30000  # 30 segundos en milisegundos


# ==================== CLASES DE UI ====================

class MetricCard(ctk.CTkFrame):
    """Card para mostrar una métrica con valor y etiqueta"""
    
    def __init__(self, parent, title, value, icon="📊", color="#4a90e2", **kwargs):
        super().__init__(parent, fg_color="#1e1e1e", corner_radius=10, **kwargs)
        
        self.title = title
        self.color = color
        
        # Frame superior con color de acento
        accent_frame = ctk.CTkFrame(self, fg_color=color, height=5, corner_radius=0)
        accent_frame.pack(fill='x', side='top')
        
        # Contenedor principal
        content_frame = ctk.CTkFrame(self, fg_color="transparent")
        content_frame.pack(fill='both', expand=True, padx=15, pady=10)
        
        # Icon y título
        header_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
        header_frame.pack(fill='x', pady=(0, 10))
        
        icon_label = ctk.CTkLabel(
            header_frame, 
            text=icon, 
            font=ctk.CTkFont(size=24)
        )
        icon_label.pack(side='left', padx=(0, 10))
        
        title_label = ctk.CTkLabel(
            header_frame,
            text=title,
            font=ctk.CTkFont(size=12, weight="normal"),
            text_color="#aaaaaa"
        )
        title_label.pack(side='left', anchor='w')
        
        # Valor grande
        self.value_label = ctk.CTkLabel(
            content_frame,
            text=str(value),
            font=ctk.CTkFont(size=36, weight="bold"),
            text_color="#ffffff"
        )
        self.value_label.pack(anchor='w')
    
    def update_value(self, new_value):
        """Actualiza el valor mostrado"""
        self.value_label.configure(text=str(new_value))


class DatabaseManagement(ctk.CTkFrame):
    """
    Panel de gestión avanzada de base de datos con operaciones masivas
    """
    
    def __init__(self, parent, username, session_id, station):
        super().__init__(parent, fg_color="#0d1117")
        
        self.username = username
        self.session_id = session_id
        self.station = station
        self.current_table = None
        self.current_data = []
        self.selected_rows = []
        
        # Container principal
        main_container = ctk.CTkFrame(self, fg_color="transparent")
        main_container.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Header
        self._create_header(main_container)
        
        # Panel de control (selector de tabla + acciones)
        self._create_control_panel(main_container)
        
        # Panel de búsqueda y filtros
        self._create_search_panel(main_container)
        
        # Tabla de datos (Treeview)
        self._create_data_table(main_container)
        
        # Panel de acciones masivas
        self._create_bulk_actions_panel(main_container)
        
        # Cargar tablas disponibles
        self._load_available_tables()
    
    def _create_header(self, parent):
        """Header con título"""
        header = ctk.CTkFrame(parent, fg_color="transparent")
        header.pack(fill='x', pady=(0, 20))
        
        title = ctk.CTkLabel(
            header,
            text="🗄️ Gestión de Base de Datos",
            font=ctk.CTkFont(size=28, weight="bold"),
            text_color="#ffffff"
        )
        title.pack(side='left')
        
        info_label = ctk.CTkLabel(
            header,
            text="Administración masiva de tablas • Exportación • Operaciones por lotes",
            font=ctk.CTkFont(size=12),
            text_color="#7d8590"
        )
        info_label.pack(side='left', padx=(20, 0))
    
    def _create_control_panel(self, parent):
        """Panel de selección de tabla y acciones principales"""
        control_frame = ctk.CTkFrame(parent, fg_color="#1e1e1e", corner_radius=10)
        control_frame.pack(fill='x', pady=(0, 15))
        
        inner_frame = ctk.CTkFrame(control_frame, fg_color="transparent")
        inner_frame.pack(fill='x', padx=15, pady=15)
        
        # Selector de tabla
        table_label = ctk.CTkLabel(
            inner_frame,
            text="Seleccionar Tabla:",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        table_label.pack(side='left', padx=(0, 10))
        
        self.table_selector = ctk.CTkComboBox(
            inner_frame,
            width=250,
            command=self._on_table_selected,
            state="readonly"
        )
        self.table_selector.pack(side='left', padx=(0, 20))
        
        # Botón cargar
        load_btn = ctk.CTkButton(
            inner_frame,
            text="🔄 Cargar Datos",
            width=120,
            command=self._load_table_data,
            fg_color="#238636",
            hover_color="#2ea043"
        )
        load_btn.pack(side='left', padx=5)
        
        # Botón exportar
        export_btn = ctk.CTkButton(
            inner_frame,
            text="📥 Exportar CSV",
            width=120,
            command=self._export_to_csv,
            fg_color="#4a90e2",
            hover_color="#357abd"
        )
        export_btn.pack(side='left', padx=5)
        
        # Botón agregar registro
        add_btn = ctk.CTkButton(
            inner_frame,
            text="➕ Nuevo Registro",
            width=140,
            command=self._add_record,
            fg_color="#8e44ad",
            hover_color="#7d3c98"
        )
        add_btn.pack(side='left', padx=5)
        
        # Label de info
        self.info_label = ctk.CTkLabel(
            inner_frame,
            text="Seleccione una tabla para comenzar",
            font=ctk.CTkFont(size=11),
            text_color="#7d8590"
        )
        self.info_label.pack(side='right', padx=(20, 0))
    
    def _create_search_panel(self, parent):
        """Panel de búsqueda y filtros"""
        search_frame = ctk.CTkFrame(parent, fg_color="#1e1e1e", corner_radius=10)
        search_frame.pack(fill='x', pady=(0, 15))
        
        inner_frame = ctk.CTkFrame(search_frame, fg_color="transparent")
        inner_frame.pack(fill='x', padx=15, pady=15)
        
        # Campo de búsqueda
        search_label = ctk.CTkLabel(
            inner_frame,
            text="🔍 Buscar:",
            font=ctk.CTkFont(size=13)
        )
        search_label.pack(side='left', padx=(0, 10))
        
        self.search_entry = ctk.CTkEntry(
            inner_frame,
            width=300,
            placeholder_text="Buscar en todos los campos..."
        )
        self.search_entry.pack(side='left', padx=(0, 10))
        self.search_entry.bind('<Return>', lambda e: self._search_data())
        
        search_btn = ctk.CTkButton(
            inner_frame,
            text="Buscar",
            width=80,
            command=self._search_data,
            fg_color="#4a90e2",
            hover_color="#357abd"
        )
        search_btn.pack(side='left', padx=5)
        
        clear_btn = ctk.CTkButton(
            inner_frame,
            text="Limpiar",
            width=80,
            command=self._clear_search,
            fg_color="#7d8590",
            hover_color="#6c757d"
        )
        clear_btn.pack(side='left', padx=5)
        
        # Filtros avanzados
        filter_label = ctk.CTkLabel(
            inner_frame,
            text="Filtros:",
            font=ctk.CTkFont(size=13)
        )
        filter_label.pack(side='left', padx=(30, 10))
        
        self.filter_column = ctk.CTkComboBox(
            inner_frame,
            width=150,
            values=["Todas las columnas"],
            state="readonly"
        )
        self.filter_column.pack(side='left', padx=5)
    
    def _create_data_table(self, parent):
        """Tabla de datos principal con Treeview"""
        table_frame = ctk.CTkFrame(parent, fg_color="#1e1e1e", corner_radius=10)
        table_frame.pack(fill='both', expand=True, pady=(0, 15))
        
        # Header
        header = ctk.CTkFrame(table_frame, fg_color="transparent")
        header.pack(fill='x', padx=15, pady=(15, 10))
        
        table_title = ctk.CTkLabel(
            header,
            text="📋 Registros",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        table_title.pack(side='left')
        
        self.record_count_label = ctk.CTkLabel(
            header,
            text="0 registros",
            font=ctk.CTkFont(size=12),
            text_color="#7d8590"
        )
        self.record_count_label.pack(side='left', padx=(15, 0))
        
        # Botón seleccionar todos
        select_all_btn = ctk.CTkButton(
            header,
            text="☑️ Seleccionar Todos",
            width=140,
            height=28,
            command=self._select_all_rows,
            fg_color="#6c757d",
            hover_color="#5a6268"
        )
        select_all_btn.pack(side='right', padx=5)
        
        # Container de tabla con scrollbars
        table_container = ctk.CTkFrame(table_frame, fg_color="#0d1117")
        table_container.pack(fill='both', expand=True, padx=15, pady=(0, 15))
        
        # Estilo
        style = ttk.Style()
        style.configure("Database.Treeview",
            background="#0d1117",
            foreground="#ffffff",
            fieldbackground="#0d1117",
            borderwidth=0,
            rowheight=28
        )
        style.configure("Database.Treeview.Heading",
            background="#2d333b",
            foreground="#ffffff",
            borderwidth=1
        )
        style.map("Database.Treeview",
            background=[('selected', '#4a90e2')],
            foreground=[('selected', '#ffffff')]
        )
        
        # Treeview con scrollbars
        self.data_tree = ttk.Treeview(
            table_container,
            style="Database.Treeview",
            selectmode='extended',
            height=15
        )
        
        vsb = ttk.Scrollbar(table_container, orient="vertical", command=self.data_tree.yview)
        hsb = ttk.Scrollbar(table_container, orient="horizontal", command=self.data_tree.xview)
        self.data_tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        
        self.data_tree.grid(row=0, column=0, sticky='nsew')
        vsb.grid(row=0, column=1, sticky='ns')
        hsb.grid(row=1, column=0, sticky='ew')
        
        table_container.grid_rowconfigure(0, weight=1)
        table_container.grid_columnconfigure(0, weight=1)
        
        # Bind eventos
        self.data_tree.bind('<Double-1>', self._edit_record)
        self.data_tree.bind('<<TreeviewSelect>>', self._on_row_select)
    
    def _create_bulk_actions_panel(self, parent):
        """Panel de acciones masivas"""
        actions_frame = ctk.CTkFrame(parent, fg_color="#1e1e1e", corner_radius=10)
        actions_frame.pack(fill='x')
        
        inner_frame = ctk.CTkFrame(actions_frame, fg_color="transparent")
        inner_frame.pack(fill='x', padx=15, pady=15)
        
        actions_label = ctk.CTkLabel(
            inner_frame,
            text="⚡ Acciones Masivas:",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        actions_label.pack(side='left', padx=(0, 20))
        
        self.selected_count_label = ctk.CTkLabel(
            inner_frame,
            text="0 seleccionados",
            font=ctk.CTkFont(size=12),
            text_color="#7d8590"
        )
        self.selected_count_label.pack(side='left', padx=(0, 20))
        
        # Botones de acciones
        edit_btn = ctk.CTkButton(
            inner_frame,
            text="✏️ Editar",
            width=100,
            command=self._edit_selected,
            fg_color="#4a90e2",
            hover_color="#357abd"
        )
        edit_btn.pack(side='left', padx=5)
        
        delete_btn = ctk.CTkButton(
            inner_frame,
            text="🗑️ Eliminar",
            width=100,
            command=self._delete_selected,
            fg_color="#e74c3c",
            hover_color="#c0392b"
        )
        delete_btn.pack(side='left', padx=5)
        
        duplicate_btn = ctk.CTkButton(
            inner_frame,
            text="📋 Duplicar",
            width=100,
            command=self._duplicate_selected,
            fg_color="#27ae60",
            hover_color="#229954"
        )
        duplicate_btn.pack(side='left', padx=5)
        
        update_field_btn = ctk.CTkButton(
            inner_frame,
            text="🔄 Actualizar Campo",
            width=140,
            command=self._bulk_update_field,
            fg_color="#f39c12",
            hover_color="#e67e22"
        )
        update_field_btn.pack(side='left', padx=5)
    
    def _load_available_tables(self):
        """Carga lista de tablas disponibles"""
        try:
            conn = get_connection()
            cur = conn.cursor()
            
            cur.execute("SHOW TABLES")
            tables = [row[0] for row in cur.fetchall()]
            
            cur.close()
            conn.close()
            
            # Tablas principales del sistema
            priority_tables = [
                'user', 'sesion', 'Eventos', 'Sitios',
                'covers_programados', 'covers_realizados',
                'gestion_breaks_programados', 'Activities'
            ]
            
            # Ordenar: prioritarias primero, luego alfabético
            sorted_tables = []
            for t in priority_tables:
                if t in tables:
                    sorted_tables.append(t)
            
            for t in sorted(tables):
                if t not in sorted_tables:
                    sorted_tables.append(t)
            
            self.table_selector.configure(values=sorted_tables)
            if sorted_tables:
                self.table_selector.set(sorted_tables[0])
            
            print(f"[INFO] Tablas disponibles: {len(sorted_tables)}")
            
        except Exception as e:
            print(f"[ERROR] _load_available_tables: {e}")
            messagebox.showerror("Error", f"Error al cargar tablas: {e}")
    
    def _on_table_selected(self, choice):
        """Evento al seleccionar una tabla"""
        self.current_table = choice
        self.info_label.configure(text=f"Tabla: {choice} • Click 'Cargar Datos' para ver registros")
    
    def _load_table_data(self):
        """Carga datos de la tabla seleccionada"""
        if not self.current_table:
            messagebox.showwarning("Advertencia", "Seleccione una tabla primero")
            return
        
        try:
            conn = get_connection()
            cur = conn.cursor()
            
            # Obtener estructura de la tabla
            cur.execute(f"DESCRIBE `{self.current_table}`")
            columns_info = cur.fetchall()
            column_names = [col[0] for col in columns_info]
            
            # Obtener datos (limitar a 1000 registros por seguridad)
            cur.execute(f"SELECT * FROM `{self.current_table}` LIMIT 1000")
            rows = cur.fetchall()
            
            cur.close()
            conn.close()
            
            # Configurar Treeview
            self.data_tree['columns'] = column_names
            self.data_tree['show'] = 'tree headings'
            
            # Configurar columna #0 (checkbox visual)
            self.data_tree.column('#0', width=30, anchor='center')
            self.data_tree.heading('#0', text='☐')
            
            # Configurar columnas de datos
            for col in column_names:
                self.data_tree.heading(col, text=col)
                self.data_tree.column(col, width=120, anchor='w')
            
            # Limpiar datos anteriores
            for item in self.data_tree.get_children():
                self.data_tree.delete(item)
            
            # Insertar datos
            self.current_data = []
            for row in rows:
                # Convertir valores a string y manejar None
                display_values = tuple(str(v) if v is not None else '' for v in row)
                item_id = self.data_tree.insert('', 'end', text='☐', values=display_values)
                self.current_data.append({'id': item_id, 'data': row})
            
            # Actualizar filtros
            self.filter_column.configure(values=['Todas las columnas'] + column_names)
            self.filter_column.set('Todas las columnas')
            
            # Actualizar info
            self.record_count_label.configure(text=f"{len(rows)} registros")
            self.info_label.configure(
                text=f"Tabla: {self.current_table} • {len(rows)} registros cargados • {len(column_names)} columnas"
            )
            
            print(f"[INFO] Cargados {len(rows)} registros de {self.current_table}")
            
        except Exception as e:
            print(f"[ERROR] _load_table_data: {e}")
            traceback.print_exc()
            messagebox.showerror("Error", f"Error al cargar datos:\n{e}")
    
    def _search_data(self):
        """Busca datos en la tabla actual"""
        search_term = self.search_entry.get().strip().lower()
        if not search_term:
            self._load_table_data()
            return
        
        # Filtrar items visibles
        for item in self.data_tree.get_children():
            values = self.data_tree.item(item)['values']
            match = any(search_term in str(v).lower() for v in values)
            
            if not match:
                self.data_tree.detach(item)
    
    def _clear_search(self):
        """Limpia búsqueda y recarga datos"""
        self.search_entry.delete(0, 'end')
        self._load_table_data()
    
    def _on_row_select(self, event):
        """Evento al seleccionar filas"""
        selected = self.data_tree.selection()
        self.selected_count_label.configure(text=f"{len(selected)} seleccionados")
        
        # Actualizar visual de checkboxes
        for item in self.data_tree.get_children():
            if item in selected:
                self.data_tree.item(item, text='☑')
            else:
                self.data_tree.item(item, text='☐')
    
    def _select_all_rows(self):
        """Selecciona todas las filas"""
        all_items = self.data_tree.get_children()
        self.data_tree.selection_set(all_items)
    
    def _add_record(self):
        """Agrega un nuevo registro"""
        messagebox.showinfo("Agregar Registro", 
                           "Función en desarrollo\n\nPermitirá agregar registros con formulario dinámico")
    
    def _edit_record(self, event):
        """Edita un registro (doble click)"""
        selection = self.data_tree.selection()
        if not selection:
            return
        
        item = self.data_tree.item(selection[0])
        messagebox.showinfo("Editar Registro", 
                           f"Función en desarrollo\n\nEditando registro:\n{item['values'][:3]}")
    
    def _edit_selected(self):
        """Edita registros seleccionados"""
        selected = self.data_tree.selection()
        if not selected:
            messagebox.showwarning("Advertencia", "Seleccione al menos un registro")
            return
        
        messagebox.showinfo("Editar Seleccionados", 
                           f"Función en desarrollo\n\n{len(selected)} registros seleccionados")
    
    def _delete_selected(self):
        """Elimina registros seleccionados"""
        selected = self.data_tree.selection()
        if not selected:
            messagebox.showwarning("Advertencia", "Seleccione registros para eliminar")
            return
        
        if not messagebox.askyesno("Confirmar Eliminación", 
                                   f"¿Eliminar {len(selected)} registros?\n\n⚠️ Esta acción no se puede deshacer"):
            return
        
        messagebox.showinfo("Eliminar", "Función en desarrollo")
    
    def _duplicate_selected(self):
        """Duplica registros seleccionados"""
        selected = self.data_tree.selection()
        if not selected:
            messagebox.showwarning("Advertencia", "Seleccione registros para duplicar")
            return
        
        messagebox.showinfo("Duplicar", f"Función en desarrollo\n\nDuplicando {len(selected)} registros")
    
    def _bulk_update_field(self):
        """Actualiza un campo masivamente"""
        selected = self.data_tree.selection()
        if not selected:
            messagebox.showwarning("Advertencia", "Seleccione registros para actualizar")
            return
        
        messagebox.showinfo("Actualización Masiva", 
                           f"Función en desarrollo\n\nActualizar campo para {len(selected)} registros")
    
    def _export_to_csv(self):
        """Exporta tabla actual a CSV"""
        if not self.current_table:
            messagebox.showwarning("Advertencia", "Cargue una tabla primero")
            return
        
        try:
            from tkinter import filedialog
            import csv
            from datetime import datetime
            
            filename = filedialog.asksaveasfilename(
                defaultextension=".csv",
                filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
                initialfile=f"{self.current_table}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            )
            
            if not filename:
                return
            
            # Obtener columnas y datos
            columns = self.data_tree['columns']
            
            with open(filename, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(columns)
                
                for item in self.data_tree.get_children():
                    values = self.data_tree.item(item)['values']
                    writer.writerow(values)
            
            messagebox.showinfo("Éxito", f"Datos exportados a:\n{filename}")
            
        except Exception as e:
            print(f"[ERROR] _export_to_csv: {e}")
            messagebox.showerror("Error", f"Error al exportar: {e}")


class CoversAnalytics(ctk.CTkFrame):
    """
    Panel de análisis visual para covers (programados y emergencias)
    """
    
    def __init__(self, parent, username, session_id, station):
        super().__init__(parent, fg_color="#0d1117")
        
        self.username = username
        self.session_id = session_id
        self.station = station
        self.auto_refresh_job = None
        
        # Scrollable container
        self.scroll_container = ctk.CTkScrollableFrame(
            self,
            fg_color="transparent",
            scrollbar_button_color="#2d333b",
            scrollbar_button_hover_color="#3d444d"
        )
        self.scroll_container.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Header
        self._create_header()
        
        # Gráficos de covers
        self._create_covers_graphs()
        
        # Cargar datos iniciales
        self.refresh_analytics()
        
        # Iniciar auto-refresh
        self._start_auto_refresh()
    
    def _create_header(self):
        """Crea el header con título y controles"""
        header_frame = ctk.CTkFrame(self.scroll_container, fg_color="transparent")
        header_frame.pack(fill='x', pady=(0, 20))
        
        title_label = ctk.CTkLabel(
            header_frame,
            text="📊 Análisis de Covers",
            font=ctk.CTkFont(size=28, weight="bold"),
            text_color="#ffffff"
        )
        title_label.pack(side='left', anchor='w')
        
        refresh_btn = ctk.CTkButton(
            header_frame,
            text="🔄 Actualizar",
            width=120,
            height=32,
            command=self.refresh_analytics,
            fg_color="#238636",
            hover_color="#2ea043"
        )
        refresh_btn.pack(side='right', padx=(10, 0))
        
        self.last_update_label = ctk.CTkLabel(
            header_frame,
            text="Última actualización: --:--:--",
            font=ctk.CTkFont(size=11),
            text_color="#7d8590"
        )
        self.last_update_label.pack(side='right', padx=(0, 10))
    
    def _create_covers_graphs(self):
        """Crea la sección de gráficos de covers"""
        # Fila 1: Covers por día y Estado
        row1_frame = ctk.CTkFrame(self.scroll_container, fg_color="transparent")
        row1_frame.pack(fill='both', expand=True, pady=(0, 15))
        
        row1_frame.grid_columnconfigure(0, weight=1)
        row1_frame.grid_columnconfigure(1, weight=1)
        
        self.graph_covers_dia_frame = ctk.CTkFrame(row1_frame, fg_color="#1e1e1e", corner_radius=10)
        self.graph_covers_dia_frame.grid(row=0, column=0, padx=5, pady=5, sticky='nsew')
        
        self.graph_covers_estado_frame = ctk.CTkFrame(row1_frame, fg_color="#1e1e1e", corner_radius=10)
        self.graph_covers_estado_frame.grid(row=0, column=1, padx=5, pady=5, sticky='nsew')
        
        # Fila 2: Covers por usuario y Razón
        row2_frame = ctk.CTkFrame(self.scroll_container, fg_color="transparent")
        row2_frame.pack(fill='both', expand=True, pady=(0, 15))
        
        row2_frame.grid_columnconfigure(0, weight=1)
        row2_frame.grid_columnconfigure(1, weight=1)
        
        self.graph_covers_usuario_frame = ctk.CTkFrame(row2_frame, fg_color="#1e1e1e", corner_radius=10)
        self.graph_covers_usuario_frame.grid(row=0, column=0, padx=5, pady=5, sticky='nsew')
        
        self.graph_covers_razon_frame = ctk.CTkFrame(row2_frame, fg_color="#1e1e1e", corner_radius=10)
        self.graph_covers_razon_frame.grid(row=0, column=1, padx=5, pady=5, sticky='nsew')
        
        # Fila 3: Tiempo de aprobación y Cobertura por usuario
        row3_frame = ctk.CTkFrame(self.scroll_container, fg_color="transparent")
        row3_frame.pack(fill='both', expand=True)
        
        row3_frame.grid_columnconfigure(0, weight=1)
        row3_frame.grid_columnconfigure(1, weight=1)
        
        self.graph_tiempo_aprobacion_frame = ctk.CTkFrame(row3_frame, fg_color="#1e1e1e", corner_radius=10)
        self.graph_tiempo_aprobacion_frame.grid(row=0, column=0, padx=5, pady=5, sticky='nsew')
        
        self.graph_cobertura_frame = ctk.CTkFrame(row3_frame, fg_color="#1e1e1e", corner_radius=10)
        self.graph_cobertura_frame.grid(row=0, column=1, padx=5, pady=5, sticky='nsew')
    
    def refresh_analytics(self):
        """Actualiza todos los gráficos de covers"""
        try:
            print("[INFO] 🔄 Refrescando análisis de covers...")
            
            data = get_covers_graph_data(days=7)
            
            # Limpiar gráficos anteriores
            for frame in [self.graph_covers_dia_frame, self.graph_covers_estado_frame,
                         self.graph_covers_usuario_frame, self.graph_covers_razon_frame,
                         self.graph_tiempo_aprobacion_frame, self.graph_cobertura_frame]:
                for widget in frame.winfo_children():
                    widget.destroy()
            
            # Gráfico 1: Covers por día (barras apiladas)
            self._create_covers_por_dia_graph(data['covers_por_dia'])
            
            # Gráfico 2: Estado de covers (pie)
            self._create_covers_estado_graph(data['covers_por_estado'])
            
            # Gráfico 3: Top usuarios solicitantes (barras horizontales)
            self._create_covers_usuario_graph(data['covers_por_usuario'])
            
            # Gráfico 4: Covers por razón (barras)
            self._create_covers_razon_graph(data['covers_por_razon'])
            
            # Gráfico 5: Tiempo de aprobación (línea)
            self._create_tiempo_aprobacion_graph(data['tiempo_aprobacion'])
            
            # Gráfico 6: Top usuarios que cubren (barras horizontales)
            self._create_cobertura_graph(data['cobertura_por_usuario'])
            
            # Actualizar timestamp
            now = datetime.now().strftime("%H:%M:%S")
            self.last_update_label.configure(text=f"Última actualización: {now}")
            
            print("[INFO] ✅ Análisis de covers actualizado")
            
        except Exception as e:
            print(f"[ERROR] refresh_analytics: {e}")
            traceback.print_exc()
    
    def _create_covers_por_dia_graph(self, data):
        """Gráfico de barras apiladas: completados vs pendientes por día"""
        title = ctk.CTkLabel(
            self.graph_covers_dia_frame,
            text="📅 Covers por Día (Última Semana)",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        title.pack(pady=10)
        
        if data:
            fig = Figure(figsize=(6, 3.5), facecolor='#1e1e1e')
            ax = fig.add_subplot(111)
            ax.set_facecolor('#1e1e1e')
            
            fechas = [str(row[0]) for row in data]
            completados = [row[1] for row in data]
            pendientes = [row[2] for row in data]
            
            x = range(len(fechas))
            width = 0.6
            
            ax.bar(x, completados, width, label='Completados', color='#2ecc71')
            ax.bar(x, pendientes, width, bottom=completados, label='Pendientes', color='#f39c12')
            
            ax.set_xlabel('Fecha', color='#ffffff')
            ax.set_ylabel('Cantidad', color='#ffffff')
            ax.set_xticks(x)
            ax.set_xticklabels(fechas, rotation=45, ha='right')
            ax.tick_params(colors='#ffffff', labelsize=8)
            ax.legend(facecolor='#2d333b', edgecolor='#7d8590', labelcolor='#ffffff')
            ax.spines['bottom'].set_color('#7d8590')
            ax.spines['left'].set_color('#7d8590')
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
            
            fig.tight_layout()
            
            canvas = FigureCanvasTkAgg(fig, self.graph_covers_dia_frame)
            canvas.draw()
            canvas.get_tk_widget().pack(fill='both', expand=True, padx=10, pady=10)
    
    def _create_covers_estado_graph(self, data):
        """Gráfico de pie: distribución por estado"""
        title = ctk.CTkLabel(
            self.graph_covers_estado_frame,
            text="🥧 Distribución por Estado",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        title.pack(pady=10)
        
        if data:
            fig = Figure(figsize=(6, 3.5), facecolor='#1e1e1e')
            ax = fig.add_subplot(111)
            ax.set_facecolor('#1e1e1e')
            
            estados = [row[0] for row in data]
            cantidades = [row[1] for row in data]
            
            colors = ['#2ecc71', '#f39c12', '#e74c3c', '#3498db']
            ax.pie(cantidades, labels=estados, autopct='%1.1f%%', startangle=90,
                   colors=colors, textprops={'color': '#ffffff', 'fontsize': 9})
            
            fig.tight_layout()
            
            canvas = FigureCanvasTkAgg(fig, self.graph_covers_estado_frame)
            canvas.draw()
            canvas.get_tk_widget().pack(fill='both', expand=True, padx=10, pady=10)
    
    def _create_covers_usuario_graph(self, data):
        """Gráfico de barras horizontales: top usuarios solicitantes"""
        title = ctk.CTkLabel(
            self.graph_covers_usuario_frame,
            text="👥 Top 10 Usuarios Solicitantes",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        title.pack(pady=10)
        
        if data:
            fig = Figure(figsize=(6, 3.5), facecolor='#1e1e1e')
            ax = fig.add_subplot(111)
            ax.set_facecolor('#1e1e1e')
            
            usuarios = [row[0][:15] for row in data]  # Truncar nombres largos
            cantidades = [row[1] for row in data]
            
            y = range(len(usuarios))
            ax.barh(y, cantidades, color='#4a90e2', height=0.6)
            
            ax.set_xlabel('Cantidad de Covers', color='#ffffff')
            ax.set_yticks(y)
            ax.set_yticklabels(usuarios)
            ax.tick_params(colors='#ffffff', labelsize=8)
            ax.spines['bottom'].set_color('#7d8590')
            ax.spines['left'].set_color('#7d8590')
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
            
            fig.tight_layout()
            
            canvas = FigureCanvasTkAgg(fig, self.graph_covers_usuario_frame)
            canvas.draw()
            canvas.get_tk_widget().pack(fill='both', expand=True, padx=10, pady=10)
    
    def _create_covers_razon_graph(self, data):
        """Gráfico de barras: covers por razón"""
        title = ctk.CTkLabel(
            self.graph_covers_razon_frame,
            text="📋 Covers por Razón/Motivo",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        title.pack(pady=10)
        
        if data:
            fig = Figure(figsize=(6, 3.5), facecolor='#1e1e1e')
            ax = fig.add_subplot(111)
            ax.set_facecolor('#1e1e1e')
            
            razones = [row[0][:20] for row in data]  # Truncar textos largos
            cantidades = [row[1] for row in data]
            
            x = range(len(razones))
            ax.bar(x, cantidades, color='#8e44ad', width=0.6)
            
            ax.set_xlabel('Razón', color='#ffffff')
            ax.set_ylabel('Cantidad', color='#ffffff')
            ax.set_xticks(x)
            ax.set_xticklabels(razones, rotation=45, ha='right')
            ax.tick_params(colors='#ffffff', labelsize=8)
            ax.spines['bottom'].set_color('#7d8590')
            ax.spines['left'].set_color('#7d8590')
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
            
            fig.tight_layout()
            
            canvas = FigureCanvasTkAgg(fig, self.graph_covers_razon_frame)
            canvas.draw()
            canvas.get_tk_widget().pack(fill='both', expand=True, padx=10, pady=10)
    
    def _create_tiempo_aprobacion_graph(self, data):
        """Gráfico de línea: tiempo promedio de aprobación"""
        title = ctk.CTkLabel(
            self.graph_tiempo_aprobacion_frame,
            text="⏱️ Tiempo Promedio de Aprobación (min)",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        title.pack(pady=10)
        
        if data:
            fig = Figure(figsize=(6, 3.5), facecolor='#1e1e1e')
            ax = fig.add_subplot(111)
            ax.set_facecolor('#1e1e1e')
            
            fechas = [str(row[0]) for row in data]
            tiempos = [float(row[1]) if row[1] else 0 for row in data]
            
            ax.plot(fechas, tiempos, marker='o', color='#e67e22', linewidth=2, markersize=6)
            
            ax.set_xlabel('Fecha', color='#ffffff')
            ax.set_ylabel('Minutos', color='#ffffff')
            ax.tick_params(colors='#ffffff', labelsize=8)
            plt.setp(ax.get_xticklabels(), rotation=45, ha='right')
            ax.spines['bottom'].set_color('#7d8590')
            ax.spines['left'].set_color('#7d8590')
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
            ax.grid(True, alpha=0.2, color='#7d8590')
            
            fig.tight_layout()
            
            canvas = FigureCanvasTkAgg(fig, self.graph_tiempo_aprobacion_frame)
            canvas.draw()
            canvas.get_tk_widget().pack(fill='both', expand=True, padx=10, pady=10)
    
    def _create_cobertura_graph(self, data):
        """Gráfico de barras horizontales: top usuarios que cubren"""
        title = ctk.CTkLabel(
            self.graph_cobertura_frame,
            text="🛡️ Top 10 Usuarios Cubriendo",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        title.pack(pady=10)
        
        if data:
            fig = Figure(figsize=(6, 3.5), facecolor='#1e1e1e')
            ax = fig.add_subplot(111)
            ax.set_facecolor('#1e1e1e')
            
            usuarios = [row[0][:15] for row in data]
            cantidades = [row[1] for row in data]
            
            y = range(len(usuarios))
            ax.barh(y, cantidades, color='#27ae60', height=0.6)
            
            ax.set_xlabel('Cantidad de Coberturas', color='#ffffff')
            ax.set_yticks(y)
            ax.set_yticklabels(usuarios)
            ax.tick_params(colors='#ffffff', labelsize=8)
            ax.spines['bottom'].set_color('#7d8590')
            ax.spines['left'].set_color('#7d8590')
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
            
            fig.tight_layout()
            
            canvas = FigureCanvasTkAgg(fig, self.graph_cobertura_frame)
            canvas.draw()
            canvas.get_tk_widget().pack(fill='both', expand=True, padx=10, pady=10)
    
    def _start_auto_refresh(self):
        """Inicia el auto-refresh periódico"""
        self.auto_refresh_job = self.after(AUTO_REFRESH_INTERVAL, self._auto_refresh_callback)
    
    def _auto_refresh_callback(self):
        """Callback para auto-refresh"""
        self.refresh_analytics()
        self._start_auto_refresh()
    
    def destroy(self):
        """Cleanup al destruir"""
        if self.auto_refresh_job:
            self.after_cancel(self.auto_refresh_job)
        super().destroy()


class AdminDashboard(ctk.CTkFrame):
    """
    Dashboard principal del Admin con métricas en tiempo real
    """
    
    def __init__(self, parent, username, session_id, station):
        super().__init__(parent, fg_color="#0d1117")
        
        self.username = username
        self.session_id = session_id
        self.station = station
        self.auto_refresh_job = None
        self.metric_cards = {}
        
        # Scrollable container
        self.scroll_container = ctk.CTkScrollableFrame(
            self,
            fg_color="transparent",
            scrollbar_button_color="#2d333b",
            scrollbar_button_hover_color="#3d444d"
        )
        self.scroll_container.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Header con título y última actualización
        self._create_header()
        
        # Sección de métricas (cards)
        self._create_metrics_section()
        
        # Gráficos
        self._create_graphs_section()
        
        # Sesiones activas
        self._create_sessions_section()
        
        # Panel de alertas
        self._create_alerts_section()
        
        # Cargar datos iniciales
        self.refresh_dashboard()
        
        # Iniciar auto-refresh
        self._start_auto_refresh()
    
    def _create_header(self):
        """Crea el header con título y controles"""
        header_frame = ctk.CTkFrame(self.scroll_container, fg_color="transparent")
        header_frame.pack(fill='x', pady=(0, 20))
        
        # Título
        title_label = ctk.CTkLabel(
            header_frame,
            text="🎛️ Dashboard Administrativo",
            font=ctk.CTkFont(size=28, weight="bold"),
            text_color="#ffffff"
        )
        title_label.pack(side='left', anchor='w')
        
        # Botón refresh manual
        refresh_btn = ctk.CTkButton(
            header_frame,
            text="🔄 Actualizar",
            width=120,
            height=32,
            command=self.refresh_dashboard,
            fg_color="#238636",
            hover_color="#2ea043"
        )
        refresh_btn.pack(side='right', padx=(10, 0))
        
        # Label de última actualización
        self.last_update_label = ctk.CTkLabel(
            header_frame,
            text="Última actualización: --:--:--",
            font=ctk.CTkFont(size=11),
            text_color="#7d8590"
        )
        self.last_update_label.pack(side='right', padx=(0, 10))
    
    def _create_metrics_section(self):
        """Crea la sección de cards de métricas"""
        metrics_frame = ctk.CTkFrame(self.scroll_container, fg_color="transparent")
        metrics_frame.pack(fill='x', pady=(0, 20))
        
        section_title = ctk.CTkLabel(
            metrics_frame,
            text="📈 Métricas en Tiempo Real",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color="#ffffff"
        )
        section_title.pack(anchor='w', pady=(0, 15))
        
        # Grid de cards
        cards_grid = ctk.CTkFrame(metrics_frame, fg_color="transparent")
        cards_grid.pack(fill='x')
        
        # Configurar grid 4x2
        for i in range(4):
            cards_grid.grid_columnconfigure(i, weight=1, uniform="col")
        
        # Definir cards
        cards_config = [
            ("Sesiones Activas", 0, "👥", "#4a90e2"),
            ("Covers Pendientes", 0, "⏳", "#f39c12"),
            ("Breaks Activos", 0, "☕", "#27ae60"),
            ("Eventos Hoy", 0, "📝", "#8e44ad"),
            ("Usuarios Conectados", 0, "🟢", "#16a085"),
            ("Covers Completados", 0, "✅", "#2ecc71"),
            ("Eventos Abiertos", 0, "🔓", "#e74c3c"),
            ("Alertas Críticas", 0, "⚠️", "#e67e22")
        ]
        
        for idx, (title, value, icon, color) in enumerate(cards_config):
            row = idx // 4
            col = idx % 4
            
            card = MetricCard(
                cards_grid,
                title=title,
                value=value,
                icon=icon,
                color=color,
                width=200,
                height=120
            )
            card.grid(row=row, column=col, padx=5, pady=5, sticky='ew')
            
            # Guardar referencia para actualizar
            key = title.lower().replace(' ', '_')
            self.metric_cards[key] = card
    
    def _create_graphs_section(self):
        """Crea la sección de gráficos"""
        graphs_frame = ctk.CTkFrame(self.scroll_container, fg_color="transparent")
        graphs_frame.pack(fill='both', expand=True, pady=(0, 20))
        
        section_title = ctk.CTkLabel(
            graphs_frame,
            text="📊 Análisis Visual",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color="#ffffff"
        )
        section_title.pack(anchor='w', pady=(0, 15))
        
        # Container para gráficos (2 columnas)
        graphs_container = ctk.CTkFrame(graphs_frame, fg_color="transparent")
        graphs_container.pack(fill='both', expand=True)
        
        graphs_container.grid_columnconfigure(0, weight=1)
        graphs_container.grid_columnconfigure(1, weight=1)
        
        # Gráfico 1: Eventos por hora
        self.graph1_frame = ctk.CTkFrame(graphs_container, fg_color="#1e1e1e", corner_radius=10)
        self.graph1_frame.grid(row=0, column=0, padx=5, pady=5, sticky='nsew')
        
        graph1_title = ctk.CTkLabel(
            self.graph1_frame,
            text="📈 Eventos por Hora (Últimas 24h)",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        graph1_title.pack(pady=10)
        
        # Gráfico 2: Distribución de eventos
        self.graph2_frame = ctk.CTkFrame(graphs_container, fg_color="#1e1e1e", corner_radius=10)
        self.graph2_frame.grid(row=0, column=1, padx=5, pady=5, sticky='nsew')
        
        graph2_title = ctk.CTkLabel(
            self.graph2_frame,
            text="🥧 Distribución por Actividad (Hoy)",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        graph2_title.pack(pady=10)
    
    def _create_sessions_section(self):
        """Crea la tabla de sesiones activas"""
        sessions_frame = ctk.CTkFrame(self.scroll_container, fg_color="#1e1e1e", corner_radius=10)
        sessions_frame.pack(fill='both', expand=True, pady=(0, 20))
        
        # Header
        header = ctk.CTkFrame(sessions_frame, fg_color="transparent")
        header.pack(fill='x', padx=15, pady=(15, 10))
        
        section_title = ctk.CTkLabel(
            header,
            text="👤 Sesiones Activas en Tiempo Real",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color="#ffffff"
        )
        section_title.pack(side='left')
        
        # Tabla
        table_container = ctk.CTkFrame(sessions_frame, fg_color="#0d1117")
        table_container.pack(fill='both', expand=True, padx=15, pady=(0, 15))
        
        # Crear Treeview con estilo
        style = ttk.Style()
        style.theme_use('clam')
        style.configure("Dashboard.Treeview",
            background="#0d1117",
            foreground="#ffffff",
            fieldbackground="#0d1117",
            borderwidth=0,
            rowheight=30
        )
        style.configure("Dashboard.Treeview.Heading",
            background="#2d333b",
            foreground="#ffffff",
            borderwidth=1,
            relief='flat'
        )
        style.map("Dashboard.Treeview",
            background=[('selected', '#4a90e2')],
            foreground=[('selected', '#ffffff')]
        )
        
        columns = ('Usuario', 'Estación', 'Hora Inicio', 'Tiempo Activo', 'Estado', 'Rol')
        self.sessions_tree = ttk.Treeview(
            table_container,
            columns=columns,
            show='headings',
            style="Dashboard.Treeview",
            height=8
            
        )
        
        # Configurar columnas
        widths = [150, 100, 150, 120, 150, 100]
        for col, width in zip(columns, widths):
            self.sessions_tree.heading(col, text=col)
            self.sessions_tree.column(col, width=width, anchor='center')
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(table_container, orient='vertical', command=self.sessions_tree.yview)
        self.sessions_tree.configure(yscrollcommand=scrollbar.set)
        
        self.sessions_tree.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
        
        # Botones de acción
        actions_frame = ctk.CTkFrame(sessions_frame, fg_color="transparent")
        actions_frame.pack(fill='x', padx=15, pady=(0, 15))
        
        view_activity_btn = ctk.CTkButton(
            actions_frame,
            text="📋 Ver Actividad",
            width=150,
            command=self._view_user_activity,
            fg_color="#4a90e2",
            hover_color="#357abd"
        )
        view_activity_btn.pack(side='left', padx=(0, 10))
        
        force_logout_btn = ctk.CTkButton(
            actions_frame,
            text="🚪 Cerrar Sesión",
            width=150,
            command=self._force_logout_user,
            fg_color="#e74c3c",
            hover_color="#c0392b"
        )
        force_logout_btn.pack(side='left')
    
    def _create_alerts_section(self):
        """Crea el panel de alertas críticas"""
        alerts_frame = ctk.CTkFrame(self.scroll_container, fg_color="#1e1e1e", corner_radius=10)
        alerts_frame.pack(fill='both', expand=True)
        
        # Header
        header = ctk.CTkFrame(alerts_frame, fg_color="transparent")
        header.pack(fill='x', padx=15, pady=(15, 10))
        
        section_title = ctk.CTkLabel(
            header,
            text="⚠️ Alertas y Notificaciones",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color="#ffffff"
        )
        section_title.pack(side='left')
        
        # Contenedor de alertas (scrollable)
        self.alerts_container = ctk.CTkScrollableFrame(
            alerts_frame,
            fg_color="#0d1117",
            height=200
        )
        self.alerts_container.pack(fill='both', expand=True, padx=15, pady=(0, 15))
    
    def refresh_dashboard(self):
        """Actualiza todos los datos del dashboard"""
        try:
            print(f"[INFO] 🔄 Refrescando dashboard...")
            
            # 1. Actualizar métricas
            metrics = get_dashboard_metrics()
            
            self.metric_cards['sesiones_activas'].update_value(metrics['sesiones_activas'])
            self.metric_cards['covers_pendientes'].update_value(metrics['covers_pendientes'])
            self.metric_cards['breaks_activos'].update_value(metrics['breaks_activos'])
            self.metric_cards['eventos_hoy'].update_value(metrics['eventos_dia'])
            self.metric_cards['usuarios_conectados'].update_value(metrics['usuarios_conectados'])
            self.metric_cards['covers_completados'].update_value(metrics['covers_completados_hoy'])
            self.metric_cards['eventos_abiertos'].update_value(metrics['eventos_abiertos'])
            self.metric_cards['alertas_críticas'].update_value(metrics['alertas_criticas'])
            
            # 2. Actualizar gráficos
            self._update_graphs()
            
            # 3. Actualizar sesiones activas
            self._update_sessions_table()
            
            # 4. Actualizar alertas
            self._update_alerts()
            
            # 5. Actualizar timestamp
            now = datetime.now().strftime("%H:%M:%S")
            self.last_update_label.configure(text=f"Última actualización: {now}")
            
            print(f"[INFO] ✅ Dashboard actualizado correctamente")
            
        except Exception as e:
            print(f"[ERROR] refresh_dashboard: {e}")
            traceback.print_exc()
    
    def _update_graphs(self):
        """Actualiza los gráficos con datos frescos"""
        try:
            data = get_activity_graph_data()
            
            # Limpiar TODOS los widgets de ambos frames
            for widget in self.graph1_frame.winfo_children():
                widget.destroy()
            
            for widget in self.graph2_frame.winfo_children():
                widget.destroy()
            
            # Recrear títulos
            graph1_title = ctk.CTkLabel(
                self.graph1_frame,
                text="📈 Eventos por Hora (Últimas 24h)",
                font=ctk.CTkFont(size=14, weight="bold")
            )
            graph1_title.pack(pady=10)
            
            graph2_title = ctk.CTkLabel(
                self.graph2_frame,
                text="🥧 Distribución por Actividad (Hoy)",
                font=ctk.CTkFont(size=14, weight="bold")
            )
            graph2_title.pack(pady=10)
            
            # Gráfico 1: Eventos por hora (barras)
            if data['eventos_por_hora']:
                fig1 = Figure(figsize=(5, 3), facecolor='#1e1e1e')
                ax1 = fig1.add_subplot(111)
                ax1.set_facecolor('#1e1e1e')
                
                horas = [f"{row[0]:02d}:00" for row in data['eventos_por_hora']]
                cantidades = [row[1] for row in data['eventos_por_hora']]
                
                ax1.bar(horas, cantidades, color='#4a90e2', width=0.6)
                ax1.set_xlabel('Hora', color='#ffffff')
                ax1.set_ylabel('Cantidad', color='#ffffff')
                ax1.tick_params(colors='#ffffff', labelsize=8, rotation=45)
                ax1.spines['bottom'].set_color('#7d8590')
                ax1.spines['left'].set_color('#7d8590')
                ax1.spines['top'].set_visible(False)
                ax1.spines['right'].set_visible(False)
                
                fig1.tight_layout()
                
                canvas1 = FigureCanvasTkAgg(fig1, self.graph1_frame)
                canvas1.draw()
                canvas1.get_tk_widget().pack(fill='both', expand=True, padx=10, pady=10)
            
            # Gráfico 2: Distribución de eventos (pie)
            if data['distribucion_eventos']:
                fig2 = Figure(figsize=(5, 3), facecolor='#1e1e1e')
                ax2 = fig2.add_subplot(111)
                ax2.set_facecolor('#1e1e1e')
                
                tipos = [row[0] or 'Sin tipo' for row in data['distribucion_eventos']]
                cantidades = [row[1] for row in data['distribucion_eventos']]
                
                colors = ['#4a90e2', '#f39c12', '#27ae60', '#8e44ad', '#e74c3c']
                ax2.pie(cantidades, labels=tipos, autopct='%1.1f%%', startangle=90,
                       colors=colors, textprops={'color': '#ffffff', 'fontsize': 9})
                
                fig2.tight_layout()
                
                canvas2 = FigureCanvasTkAgg(fig2, self.graph2_frame)
                canvas2.draw()
                canvas2.get_tk_widget().pack(fill='both', expand=True, padx=10, pady=10)
            
        except Exception as e:
            print(f"[ERROR] _update_graphs: {e}")
            traceback.print_exc()
    
    def _update_sessions_table(self):
        """Actualiza la tabla de sesiones activas"""
        try:
            # Limpiar tabla
            for item in self.sessions_tree.get_children():
                self.sessions_tree.delete(item)
            
            # Obtener sesiones
            sessions = get_active_sessions_detailed()
            
            # Insertar datos
            for session in sessions:
                hora_inicio = session['hora_inicio'].strftime("%Y-%m-%d %H:%M") if session['hora_inicio'] else 'N/A'
                
                # Aplicar tag según tiempo activo
                tiempo_horas = int(session['tiempo_activo'].split(':')[0])
                tag = 'warning' if tiempo_horas >= 12 else ''
                
                self.sessions_tree.insert('', 'end', values=(
                    session['usuario'],
                    session['estacion'],
                    hora_inicio,
                    session['tiempo_activo'],
                    session['estado'],
                    session['rol']
                ), tags=(tag,))
            
            # Configurar colores de tags
            self.sessions_tree.tag_configure('warning', background='#e67e22', foreground='#ffffff')
            
        except Exception as e:
            print(f"[ERROR] _update_sessions_table: {e}")
            traceback.print_exc()
    
    def _update_alerts(self):
        """Actualiza el panel de alertas"""
        try:
            # Limpiar alertas anteriores
            for widget in self.alerts_container.winfo_children():
                widget.destroy()
            
            # Obtener alertas
            alerts = get_pending_alerts()
            
            if not alerts:
                no_alerts_label = ctk.CTkLabel(
                    self.alerts_container,
                    text="✅ No hay alertas críticas",
                    font=ctk.CTkFont(size=14),
                    text_color="#27ae60"
                )
                no_alerts_label.pack(pady=20)
                return
            
            # Crear card por cada alerta
            for alert in alerts[:10]:  # Mostrar máximo 10
                alert_card = self._create_alert_card(alert)
                alert_card.pack(fill='x', pady=5)
            
        except Exception as e:
            print(f"[ERROR] _update_alerts: {e}")
            traceback.print_exc()
    
    def _create_alert_card(self, alert):
        """Crea un card visual para una alerta"""
        # Color según prioridad
        colors = {
            'alta': '#e74c3c',
            'media': '#f39c12',
            'baja': '#3498db'
        }
        color = colors.get(alert['prioridad'], '#7d8590')
        
        card = ctk.CTkFrame(self.alerts_container, fg_color="#1e1e1e", corner_radius=5)
        
        # Barra de color izquierda
        accent = ctk.CTkFrame(card, fg_color=color, width=5, height=10)
        accent.pack(side='left', fill='y')
        
        # Contenido
        content = ctk.CTkFrame(card, fg_color="transparent")
        content.pack(side='left', fill='both', expand=True, padx=15, pady=10)
        
        # Header con tipo y timestamp
        header = ctk.CTkFrame(content, fg_color="transparent")
        header.pack(fill='x')
        
        tipo_label = ctk.CTkLabel(
            header,
            text=f"⚠️ {alert['tipo']}",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#ffffff"
        )
        tipo_label.pack(side='left')
        
        time_label = ctk.CTkLabel(
            header,
            text=alert['timestamp'].strftime("%H:%M") if isinstance(alert['timestamp'], datetime) else str(alert['timestamp']),
            font=ctk.CTkFont(size=11),
            text_color="#7d8590"
        )
        time_label.pack(side='right')
        
        # Mensaje
        msg_label = ctk.CTkLabel(
            content,
            text=alert['mensaje'],
            font=ctk.CTkFont(size=12),
            text_color="#c9d1d9",
            anchor='w'
        )
        msg_label.pack(fill='x', pady=(5, 0))
        
        return card
    
    def _view_user_activity(self):
        """Ver actividad detallada del usuario seleccionado"""
        selection = self.sessions_tree.selection()
        if not selection:
            messagebox.showwarning("Advertencia", "Seleccione una sesión primero")
            return
        
        item = self.sessions_tree.item(selection[0])
        usuario = item['values'][0]
        
        messagebox.showinfo("Actividad de Usuario", 
                           f"Mostrando actividad de: {usuario}\n\n(Función en desarrollo)")
    
    def _force_logout_user(self):
        """Forzar cierre de sesión de uno o varios usuarios seleccionados"""
        selection = self.sessions_tree.selection()
        if not selection:
            messagebox.showwarning("Advertencia", "Seleccione al menos una sesión")
            return

        usuarios = []
        for sel in selection:
            item = self.sessions_tree.item(sel)
            if item['values']:
                usuarios.append(item['values'][0])

        if not usuarios:
            messagebox.showwarning("Advertencia", "No se pudo obtener el/los usuario(s) seleccionado(s)")
            return

        if messagebox.askyesno("Confirmar", 
                              f"¿Cerrar sesión de {usuarios}?"):
            try:
                force_logout_user(usuarios)

                if force_logout_user(usuarios) == True:
                    messagebox.showinfo("Éxito", f"Sesión cerrada para: {usuarios}")
                else:
                    messagebox.showwarning("Advertencia", f"No se pudo cerrar sesión para: {usuarios}")    
                self.refresh_dashboard()
            except Exception as e:
                print(f"[ERROR] _force_logout_user: {e}")
                messagebox.showerror("Error", f"Error al cerrar sesión: {e}")
    
    def _start_auto_refresh(self):
        """Inicia el auto-refresh periódico"""
        self.auto_refresh_job = self.after(AUTO_REFRESH_INTERVAL, self._auto_refresh_callback)
    
    def _auto_refresh_callback(self):
        """Callback para auto-refresh"""
        self.refresh_dashboard()
        self._start_auto_refresh()  # Re-agendar
    
    def destroy(self):
        """Cleanup al destruir el dashboard"""
        if self.auto_refresh_job:
            self.after_cancel(self.auto_refresh_job)
        super().destroy()


# ==================== VENTANA PRINCIPAL ====================

def open_admin_panel(username, session_id, station, parent=None):
    """
    Abre el panel administrativo completo
    
    Args:
        username: Nombre del admin
        session_id: ID de sesión
        station: Estación asignada
        parent: Ventana padre (opcional)
    """
    global ADMIN_WINDOW
    
    # Verificar singleton
    if ADMIN_WINDOW and ADMIN_WINDOW.winfo_exists():
        ADMIN_WINDOW.focus()
        return
    
    # Crear ventana principal
    ADMIN_WINDOW = ctk.CTkToplevel() if parent else ctk.CTk()
    ADMIN_WINDOW.title(f"Admin Panel - {username}")
    ADMIN_WINDOW.geometry("1400x900")
    
    # Configurar tema oscuro
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")
    
    # Header con info del admin
    header = ctk.CTkFrame(ADMIN_WINDOW, fg_color="#2d333b", height=60)
    header.pack(fill='x', side='top')
    
    title_label = ctk.CTkLabel(
        header,
        text=f"🔐 Panel de Administración - {username}",
        font=ctk.CTkFont(size=20, weight="bold")
    )
    title_label.pack(side='left', padx=20, pady=15)
    
    logout_btn = ctk.CTkButton(
        header,
        text="Cerrar Sesión",
        width=120,
        command=lambda: _logout_admin(session_id, station),
        fg_color="#e74c3c",
        hover_color="#c0392b"
    )
    logout_btn.pack(side='right', padx=20, pady=15)
    
    # Contenedor principal con tabs
    tab_view = ctk.CTkTabview(ADMIN_WINDOW, fg_color="#0d1117")
    tab_view.pack(fill='both', expand=True, padx=10, pady=10)
    
    # TAB 1: Dashboard
    tab_dashboard = tab_view.add("🎛️ Dashboard")
    dashboard = AdminDashboard(tab_dashboard, username, session_id, station)
    dashboard.pack(fill='both', expand=True)
    
    # TAB 2: Gestión de Base de Datos
    tab_database = tab_view.add("🗄️ Gestión BD")
    database_mgmt = DatabaseManagement(tab_database, username, session_id, station)
    database_mgmt.pack(fill='both', expand=True)
    
    # TAB 3: Análisis de Covers
    tab_covers = tab_view.add("📊 Análisis Covers")
    covers_analytics = CoversAnalytics(tab_covers, username, session_id, station)
    covers_analytics.pack(fill='both', expand=True)
    
    # TODO: Agregar más tabs (User Management, Auditoría Avanzada, Configuración, etc.)
    
    print(f"[INFO] ✅ Admin panel opened for {username}")
    
    if not parent:
        ADMIN_WINDOW.mainloop()


def _logout_admin(session_id, station):
    """Cierra sesión del admin"""
    try:
        import login
        login.logout_silent(session_id, station)
        
        if ADMIN_WINDOW:
            ADMIN_WINDOW.destroy()
        
        print("[INFO] Admin logged out")
        
    except Exception as e:
        print(f"[ERROR] _logout_admin: {e}")


# ==================== TESTING ====================

if __name__ == "__main__":
    # Test del dashboard
    open_admin_panel("admin_test", 999, "TEST_STATION")
