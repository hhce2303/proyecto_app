"""
Controlador para Specials - Lógica de negocio y formateo de datos
Responsabilidad: Transformar datos del modelo para la vista
"""

from models import specials_model


class SpecialsController:
    """
    Controlador para gestión de specials
    """
    
    def __init__(self, username):
        """
        Inicializa el controlador
        
        Args:
            username (str): Nombre del supervisor
        """
        self.username = username
    
    def get_table_snapshot(self):
        """
        Obtiene snapshot de datos de specials formateados para renderizado
        
        Returns:
            dict: Diccionario con estructura:
                - headers (list): Lista de nombres de columnas
                - rows (list): Lista de listas con datos formateados
                - column_widths (dict): Diccionario {nombre_columna: ancho}
                - row_count (int): Número de filas
                - row_ids (list): Lista de IDs de specials
                - row_metadata (list): Lista de metadata (marked_status) por fila
        """
        # Cargar datos del modelo (ya incluye JOIN con Sitios)
        raw_data = specials_model.load_specials_by_supervisor(self.username)
        
        # Definir headers
        headers = [
            "ID", 
            "Fecha Hora", 
            "Sitio", 
            "Actividad", 
            "Cantidad", 
            "Camera", 
            "Descripcion", 
            "Usuario", 
            "TZ", 
            "Marca"
        ]
        
        # Definir anchos personalizados
        column_widths = {
            "ID": 60,
            "Fecha Hora": 150,
            "Sitio": 220,
            "Actividad": 150,
            "Cantidad": 70,
            "Camera": 80,
            "Descripcion": 190,
            "Usuario": 100,
            "TZ": 90,
            "Marca": 180
        }
        
        # Procesar datos
        rows = []
        row_ids = []
        row_metadata = []
        
        for r in raw_data:
            id_special = r[0]
            fecha_hora = r[1]
            id_sitio = r[2]
            nombre_sitio = r[3]
            time_zone_sitio = r[4]
            nombre_actividad = r[5]
            cantidad = r[6]
            camera = r[7]
            descripcion = r[8]
            usuario = r[9]
            time_zone_special = r[10]
            marked_status = r[11]
            marked_by = r[12]
            
            # Formato visual para Sitio (ID + Nombre)
            display_site = self._format_site_display(id_sitio, nombre_sitio)
            
            # Formato visual para la marca
            mark_display = self._format_mark_display(marked_status, marked_by)
            
            # Time Zone (prioritario del sitio, fallback al del special)
            tz = time_zone_sitio or time_zone_special or ""
            
            # Formatear fecha
            fecha_str = fecha_hora.strftime("%Y-%m-%d %H:%M:%S") if fecha_hora else ""
            
            # Fila para mostrar
            display_row = [
                str(id_special),
                fecha_str,
                display_site,
                nombre_actividad or "",
                str(cantidad) if cantidad is not None else "0",
                camera or "",
                descripcion or "",
                usuario or "",
                tz,
                mark_display
            ]
            
            rows.append(display_row)
            row_ids.append(id_special)
            row_metadata.append({'marked_status': marked_status})
        
        return {
            'headers': headers,
            'rows': rows,
            'column_widths': column_widths,
            'row_count': len(rows),
            'row_ids': row_ids,
            'row_metadata': row_metadata
        }
    
    def _format_site_display(self, id_sitio, nombre_sitio):
        """
        Formatea el display del sitio (ID + Nombre)
        
        Args:
            id_sitio: ID del sitio
            nombre_sitio: Nombre del sitio
        
        Returns:
            str: Sitio formateado
        """
        if id_sitio and nombre_sitio:
            return f"{id_sitio} {nombre_sitio}"
        elif id_sitio:
            return str(id_sitio)
        else:
            return nombre_sitio or ""
    
    def _format_mark_display(self, marked_status, marked_by):
        """
        Formatea el display de la marca de estado
        
        Args:
            marked_status: Estado de marca
            marked_by: Usuario que marcó
        
        Returns:
            str: Marca formateada
        """
        if marked_status == 'done':
            return f"✅ Registrado ({marked_by})" if marked_by else "✅ Registrado"
        elif marked_status == 'flagged':
            return f"🔄 En Progreso ({marked_by})" if marked_by else "🔄 En Progreso"
        else:
            return ""
    
    def apply_snapshot_to_sheet(self, sheet, snapshot, apply_widths_func):
        """
        Aplica un snapshot de datos al tksheet con highlighting
        
        Args:
            sheet: Widget tksheet
            snapshot (dict): Snapshot con headers, rows, metadata
            apply_widths_func (callable): Función para aplicar anchos de columna
        """
        # Aplicar datos
        if snapshot['row_count'] == 0:
            data = [["No hay specials en este turno"] + [""] * (len(snapshot['headers'])-1)]
            sheet.set_sheet_data(data)
        else:
            sheet.set_sheet_data(snapshot['rows'])
            
            # Aplicar anchos personalizados
            apply_widths_func()
            
            # Limpiar colores primero
            sheet.dehighlight_all()
            
            # Aplicar colores según marca
            for idx, metadata in enumerate(snapshot['row_metadata']):
                if metadata['marked_status'] == 'done':
                    sheet.highlight_rows([idx], bg="#00c853", fg="#111111")
                elif metadata['marked_status'] == 'flagged':
                    sheet.highlight_rows([idx], bg="#f5a623", fg="#111111")
        
        apply_widths_func()
        print(f"[DEBUG] Loaded {snapshot['row_count']} specials for {self.username}")
    
    def mark_specials(self, special_ids, status):
        """
        Marca múltiples specials con un estado
        
        Args:
            special_ids (list): Lista de IDs de specials
            status (str): Estado ('done', 'flagged', o None)
        
        Returns:
            bool: True si exitoso, False si error
        """
        try:
            for special_id in special_ids:
                success = specials_model.update_special_status(
                    special_id, 
                    status, 
                    self.username
                )
                if not success:
                    return False
            return True
        except Exception as e:
            print(f"[ERROR] SpecialsController.mark_specials: {e}")
            return False
    
    def delete_specials(self, special_ids):
        """
        Elimina múltiples specials
        
        Args:
            special_ids (list): Lista de IDs de specials
        
        Returns:
            bool: True si exitoso, False si error
        """
        try:
            for special_id in special_ids:
                success = specials_model.delete_special(special_id)
                if not success:
                    return False
            return True
        except Exception as e:
            print(f"[ERROR] SpecialsController.delete_specials: {e}")
            return False
    
    def get_supervisor_shift_start(self):
        """
        Obtiene hora de inicio del shift actual
        
        Returns:
            datetime: Hora de inicio o None
        """
        return specials_model.get_supervisor_shift_start(self.username)
    
    def get_all_supervisors(self):
        """
        Obtiene lista de todos los supervisores
        
        Returns:
            list: Lista de nombres de supervisores
        """
        return specials_model.get_all_supervisors()
    
    def load_otros_specials_snapshot(self, other_supervisor):
        """
        Carga snapshot de specials de otro supervisor
        
        Args:
            other_supervisor (str): Nombre del otro supervisor
        
        Returns:
            dict: Snapshot similar a get_table_snapshot() o None si sin shift
        """
        # Obtener shift start del otro supervisor
        shift_start = specials_model.get_supervisor_shift_start(other_supervisor)
        
        if not shift_start:
            return None
        
        # Cargar specials desde esa fecha
        raw_data = specials_model.load_specials_by_supervisor_since(
            other_supervisor, 
            shift_start
        )
        
        # Mismo procesamiento que get_table_snapshot
        headers = ["ID", "Fecha_hora", "ID_Sitio", "Nombre_Actividad", "Cantidad", 
                  "Camera", "Descripcion", "Usuario", "Time_Zone", "Marca"]
        
        column_widths = {
            "ID": 60, "Fecha_hora": 150, "ID_Sitio": 220, "Nombre_Actividad": 150,
            "Cantidad": 70, "Camera": 80, "Descripcion": 190, "Usuario": 100,
            "Time_Zone": 90, "Marca": 180
        }
        
        rows = []
        row_ids = []
        row_metadata = []
        
        for r in raw_data:
            id_special = r[0]
            fecha_hora = r[1]
            id_sitio = r[2]
            nombre_sitio = r[3]
            time_zone_sitio = r[4]
            nombre_actividad = r[5]
            cantidad = r[6]
            camera = r[7]
            descripcion = r[8]
            usuario = r[9]
            time_zone_special = r[10]
            marked_status = r[11]
            marked_by = r[12]
            
            display_site = self._format_site_display(id_sitio, nombre_sitio)
            mark_display = self._format_mark_display(marked_status, marked_by)
            tz = time_zone_sitio or time_zone_special or ""
            fecha_str = fecha_hora.strftime("%Y-%m-%d %H:%M:%S") if fecha_hora else ""
            
            display_row = [
                str(id_special), fecha_str, display_site, nombre_actividad or "",
                str(cantidad or 0), camera or "", descripcion or "", usuario or "",
                tz, mark_display
            ]
            
            rows.append(display_row)
            row_ids.append(id_special)
            row_metadata.append({'marked_status': marked_status})
        
        return {
            'headers': headers,
            'rows': rows,
            'column_widths': column_widths,
            'row_count': len(rows),
            'row_ids': row_ids,
            'row_metadata': row_metadata
        }
    
    def transfer_specials(self, special_ids, new_supervisor):
        """
        Transfiere specials a otro supervisor
        
        Args:
            special_ids (list): Lista de IDs
            new_supervisor (str): Nuevo supervisor
        
        Returns:
            bool: True si exitoso
        """
        return specials_model.transfer_specials_to_supervisor(
            special_ids, 
            new_supervisor
        )