"""
Módulo de Specials para Operadores
Arquitectura: MVC - Vista (Presentation Layer)
Responsabilidad: Renderizar datos de eventos especiales en tksheet
"""
from tksheet import Sheet
from controllers.specials_operator_controller import SpecialsOperatorController


class SpecialsModule:
    """
    Módulo de Specials - Muestra eventos de grupos especiales (AS, KG, HUD, PE, SCH, WAG, LT, DT).
    Implementa patrón Observer para actualización de datos.
    """
    
    def __init__(self, container, username, ui_factory, UI=None):
        """
        Inicializa el módulo de Specials.
        
        Args:
            container: Frame contenedor del módulo
            username (str): Nombre del operador
            ui_factory: Factory para crear componentes UI
            UI: Referencia a CustomTkinter (None si no disponible)
        """
        self.container = container
        self.username = username
        self.ui_factory = ui_factory
        self.UI = UI
        self.blackboard = None  # Referencia al Blackboard padre
        
        # Controlador MVC
        self.controller = SpecialsOperatorController(username)
        
        # Datos internos
        self.row_ids = []  # IDs de eventos (Eventos.ID_Eventos)
        self.row_data = []  # Datos completos de las filas
        
        # Definir columnas
        self.columns = [
            "Fecha Hora",    # 0
            "Sitio",         # 1
            "Actividad",     # 2
            "Cantidad",      # 3
            "Camera",        # 4
            "Descripción",   # 5
            "Time Zone",     # 6
            "Estado"         # 7
        ]
        
        self.column_widths = {
            "Fecha Hora": 150,
            "Sitio": 270,
            "Actividad": 170,
            "Cantidad": 80,
            "Camera": 90,
            "Descripción": 320,
            "Time Zone": 80,
            "Estado": 220
        }
        
        # Configurar sheet
        self._setup_sheet()
        self._setup_bindings()
        
        # ⏰ TIMER AUTOMÁTICO: Envío cada 30 minutos (inicia después del primer intervalo)
        self._schedule_auto_send(first_run=True)
    
    def _setup_sheet(self):
        """Configura el tksheet."""
        # Crear sheet
        self.sheet = Sheet(
            self.container,
            headers=self.columns,
            header_bg="#1a1a1a",
            header_fg="#e0e0e0",
            header_font=("Segoe UI", 10, "bold"),
            show_row_index= True,
            show_top_left=False,
            outline_thickness=0,
            outline_color="#3a3a3a",
            theme="dark blue",
            font=("Segoe UI", 10, "normal"),
            align="w",
            auto_resize_columns=False,
        )
        self.sheet.pack(fill="both", expand=True)
        
        # Aplicar anchos de columnas
        for idx, col_name in enumerate(self.columns):
            width = self.column_widths[col_name]
            self.sheet.column_width(column=idx, width=width)
        
        # Habilitar solo bindings esenciales (navegación, selección y undo)
        self.sheet.enable_bindings([
            "single_select",
            "drag_select",
            "column_select",
            "row_select",
            "column_width_resize",
            "double_click_column_resize",
            "arrowkeys",
            "right_click_popup_menu",
            "rc_select",
            "undo"  # Solo UNDO (Ctrl+Z)
        ])
    
    def _setup_bindings(self):
        """Configura eventos del sheet."""
        # Eventos de edición (para futura funcionalidad)
        # self.sheet.bind("<<SheetModified>>", self._on_cell_edit, add=True)
        pass
    
    def load_data(self):
        """
        Carga datos de specials desde el controlador.
        Muestra eventos de grupos especiales con indicadores de estado.
        """
        try:
            # Obtener datos del controlador
            data_list = self.controller.load_specials_data()
            
            if not data_list:
                # No hay datos - mostrar mensaje
                empty_row = ["No hay eventos de grupos especiales en este turno"] + [""] * (len(self.columns) - 1)
                self.sheet.set_sheet_data([empty_row])
                self.row_ids.clear()
                self.row_data.clear()
                self._apply_column_widths()
                return
            
            # Preparar datos para el sheet
            display_rows = []
            self.row_ids = []
            self.row_data = data_list
            
            for item in data_list:
                row = [
                    item['fecha_hora'],
                    item['sitio'],
                    item['actividad'],
                    item['cantidad'],
                    item['camera'],
                    item['descripcion'],
                    item['time_zone'],
                    item['estado']
                ]
                display_rows.append(row)
                self.row_ids.append(item['id'])
            
            # Actualizar sheet
            self.sheet.set_sheet_data(display_rows)
            
            # Aplicar colores según estado
            self._apply_row_colors(data_list)
            
            # Aplicar anchos de columnas
            self._apply_column_widths()
            
            print(f"[DEBUG] SpecialsModule: Loaded {len(data_list)} special events for {self.username}")
            
        except Exception as e:
            print(f"[ERROR] SpecialsModule.load_data: {e}")
            import traceback
            traceback.print_exc()
    
    def _apply_row_colors(self, data_list):
        """
        Aplica colores a las filas según el estado.
        
        Args:
            data_list (list): Lista de datos con estado_color
        """
        self.sheet.dehighlight_all()
        
        for idx, item in enumerate(data_list):
            color = item.get('estado_color')
            if color == 'green':
                # Verde: Enviado al supervisor sin cambios
                self.sheet.highlight_rows([idx], bg="#00c853", fg="#111111")
            elif color == 'amber':
                # Ámbar: Pendiente por actualizar (hay cambios)
                self.sheet.highlight_rows([idx], bg="#f5a623", fg="#111111")
            # Sin color: No enviado aún
    
    def _apply_column_widths(self):
        """Aplica los anchos de columnas configurados."""
        for idx, col_name in enumerate(self.columns):
            width = self.column_widths[col_name]
            self.sheet.column_width(column=idx, width=width)
    
    def get_selected_row_id(self):
        """
        Obtiene el ID del evento seleccionado.
        
        Returns:
            int: ID del evento o None si no hay selección
        """
        try:
            selection = self.sheet.get_currently_selected()
            if not selection or not hasattr(selection, 'row') or selection.row is None:
                return None
            
            row_idx = selection.row
            if row_idx < len(self.row_ids):
                return self.row_ids[row_idx]
            return None
            
        except Exception as e:
            print(f"[ERROR] get_selected_row_id: {e}")
            return None
    
    def get_selected_row_data(self):
        """
        Obtiene los datos completos de la fila seleccionada.
        
        Returns:
            dict: Diccionario con datos de la fila o None
        """
        try:
            selection = self.sheet.get_currently_selected()
            if not selection or not hasattr(selection, 'row') or selection.row is None:
                return None
            
            row_idx = selection.row
            if row_idx < len(self.row_data):
                return self.row_data[row_idx]
            return None
            
        except Exception as e:
            print(f"[ERROR] get_selected_row_data: {e}")
            return None
    
    def get_selected_rows(self):
        """
        Obtiene las filas seleccionadas en el sheet.
        
        Returns:
            list: Lista de índices de filas seleccionadas
        """
        try:
            selected = self.sheet.get_selected_rows()
            return list(selected) if selected else []
        except Exception as e:
            print(f"[ERROR] get_selected_rows: {e}")
            return []
    
    def get_total_rows(self):
        """
        Obtiene el total de filas en el sheet.
        
        Returns:
            int: Número total de filas
        """
        try:
            return self.sheet.get_total_rows()
        except Exception:
            return len(self.row_data)
    
    def get_evento_ids_for_rows(self, row_indices):
        """
        Obtiene los IDs de eventos para las filas especificadas.
        
        Args:
            row_indices (list): Lista de índices de filas
            
        Returns:
            list: Lista de IDs de eventos
        """
        evento_ids = []
        
        for idx in row_indices:
            if 0 <= idx < len(self.row_ids):
                evento_ids.append(self.row_ids[idx])
        
        return evento_ids
    
    def trigger_auto_send(self):
        """
        Hook para disparar envío automático de specials.
        
        Proceso:
        1. Recarga datos actualizados del controlador
        2. Filtra eventos que necesitan acción:
           - Sin color (sin marca): INSERT nuevo
           - Ámbar (pendiente): UPDATE
           - Verde (sincronizado): IGNORAR
        3. Llama al controlador para auto-detección y envío
        4. Recarga vista después del envío
        
        Returns:
            tuple: (success: bool, message: str)
        """
        try:
            print(f"[TRIGGER_AUTO_SEND] Iniciando envío automático para '{self.username}'")
            
            # 1. Recargar datos actualizados desde el controlador
            current_data = self.controller.load_specials_data()
            
            if not current_data or len(current_data) == 0:
                message = "No hay eventos especiales en este turno"
                print(f"[TRIGGER_AUTO_SEND] ℹ️ {message}")
                return False, message
            
            # 2. Filtrar eventos que necesitan ser enviados/actualizados
            eventos_to_send = []
            for item in current_data:
                estado_color = item.get('estado_color')
                evento_id = item.get('id')
                
                if estado_color == 'green':
                    # Verde = ya sincronizado, ignorar
                    continue
                elif estado_color == 'amber':
                    # Ámbar = pendiente por actualizar (UPDATE)
                    eventos_to_send.append(evento_id)
                else:
                    # Sin color = sin enviar (INSERT)
                    eventos_to_send.append(evento_id)
            
            # 3. Validar que hay eventos para procesar
            if not eventos_to_send or len(eventos_to_send) == 0:
                message = "Todos los eventos ya están sincronizados (verde)"
                print(f"[TRIGGER_AUTO_SEND] ✅ {message}")
                return True, message
            
            print(f"[TRIGGER_AUTO_SEND] Eventos a procesar: {len(eventos_to_send)}/{len(current_data)}")
            print(f"[TRIGGER_AUTO_SEND] - Sin enviar o pendientes: {len(eventos_to_send)}")
            print(f"[TRIGGER_AUTO_SEND] - Ya sincronizados (ignorados): {len(current_data) - len(eventos_to_send)}")
            
            # 4. Llamar al controlador para auto-detección y envío
            success, supervisor, message = self.controller.auto_detect_and_send(eventos_to_send)

            
            # 5. Recargar vista después del envío
            if success:
                print(f"[TRIGGER_AUTO_SEND] ✅ ÉXITO: {message}")
                print(f"[TRIGGER_AUTO_SEND] Supervisor: {supervisor}")
                print(f"[TRIGGER_AUTO_SEND] Recargando vista...")
                
            else:
                print(f"[TRIGGER_AUTO_SEND] ❌ ERROR: {message}")
            
            # 6. Retornar resultado
            self.load_data()  # Recargar para actualizar colores
            return success, message
            
        except Exception as e:
            error_msg = f"Error en trigger_auto_send: {e}"
            print(f"[TRIGGER_AUTO_SEND] ❌ EXCEPCIÓN: {error_msg}")
            import traceback
            traceback.print_exc()
            return False, error_msg
    
    def _schedule_auto_send(self, first_run=False):
        """
        Programa el envío automático de specials cada 30 minutos.
        
        Funcionamiento:
        - En la primera llamada (first_run=True): Solo programa, no ejecuta
        - En llamadas subsecuentes: Ejecuta trigger_auto_send() y se reprograma
        - Intervalo: 1800000 ms (30 minutos)
        
        Args:
            first_run (bool): True si es la primera llamada desde __init__
        
        Nota: El timer se inicia automáticamente al crear el módulo.
        """
        try:
            if first_run:
                # Primera llamada: Solo programar, no ejecutar todavía (datos aún no cargados)
                print(f"[TIMER_AUTO_SEND] Timer iniciado para '{self.username}' - primer envío en 30 minutos")
                if hasattr(self, 'container') and self.container.winfo_exists():
                    self.container.after(500, self._schedule_auto_send)  # 2 min = 2000 ms
            else:
                # Llamadas subsecuentes: Ejecutar y reprogramar
                print(f"[TIMER_AUTO_SEND] Ejecutando envío automático programado para '{self.username}'")
                
                # Ejecutar envío automático
                self.trigger_auto_send()
                
                # Reprogramar para el próximo ciclo (30 minutos)
                if hasattr(self, 'container') and self.container.winfo_exists():
                    self.container.after(30000, self._schedule_auto_send)  # 0.1 min = 6000 ms
                    print(f"[TIMER_AUTO_SEND] Próximo envío automático en 0.1 minutos")
                else:
                    print(f"[TIMER_AUTO_SEND] Módulo destruido, timer cancelado")
                
        except Exception as e:
            print(f"[TIMER_AUTO_SEND] ❌ Error en timer: {e}")
            import traceback
            traceback.print_exc()
            
            # Intentar reprogramar incluso si hubo error
            try:
                if hasattr(self, 'container') and self.container.winfo_exists():
                    self.container.after(1800000, self._schedule_auto_send)
            except:
                pass
    
    
    def refresh(self):
        """Recarga los datos del módulo."""
        self.load_data()
