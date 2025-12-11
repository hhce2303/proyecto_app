"""
Controlador para Audit - Lógica de negocio y formateo de datos
Responsabilidad: Transformar datos del modelo para la vista
"""

from models import audit_model


class AuditController:
    """
    Controlador para gestión de auditoría de eventos
    """
    
    def __init__(self):
        """Inicializa el controlador"""
        pass
    
    def get_users_list(self):
        """
        Obtiene lista de usuarios para filtros
        
        Returns:
            list: Lista de nombres de usuario
        """
        return audit_model.get_users_list()
    
    def get_sites_list(self):
        """
        Obtiene lista de sitios para filtros
        
        Returns:
            list: Lista de sitios formateados
        """
        return audit_model.get_sites_list()
    
    def get_table_snapshot(self, user_filter=None, site_filter=None, fecha_filter=None):
        """
        Obtiene snapshot de datos de eventos formateados para renderizado
        
        Args:
            user_filter (str, optional): Nombre de usuario para filtrar
            site_filter (str, optional): Filtro de sitio
            fecha_filter (str, optional): Fecha en formato YYYY-MM-DD
        
        Returns:
            dict: Diccionario con estructura:
                - headers (list): Lista de nombres de columnas
                - rows (list): Lista de listas con datos formateados
                - column_widths (dict): Diccionario {nombre_columna: ancho}
                - row_count (int): Número de filas
        """
        # Cargar datos del modelo
        raw_data = audit_model.load_eventos(
            user_filter=user_filter,
            site_filter=site_filter,
            fecha_filter=fecha_filter
        )
        
        # Definir headers
        headers = [
            "ID_Evento",
            "FechaHora",
            "Nombre_Sitio",
            "Nombre_Actividad",
            "Cantidad",
            "Camera",
            "Descripcion",
            "Usuario"
        ]
        
        # Definir anchos personalizados
        column_widths = {
            "ID_Evento": 80,
            "FechaHora": 150,
            "Nombre_Sitio": 220,
            "Nombre_Actividad": 150,
            "Cantidad": 70,
            "Camera": 70,
            "Descripcion": 200,
            "Usuario": 100
        }
        
        # Formatear datos para la vista
        rows = []
        for r in raw_data:
            rows.append([
                r[0] or "",  # ID_Eventos
                str(r[1]) if r[1] else "",  # FechaHora
                r[2] or "",  # Nombre_Sitio
                r[3] or "",  # Nombre_Actividad
                r[4] or "",  # Cantidad
                r[5] or "",  # Camera
                r[6] or "",  # Descripcion
                r[7] or ""   # Usuario
            ])
        
        return {
            'headers': headers,
            'rows': rows,
            'column_widths': column_widths,
            'row_count': len(rows)
        }
    
    def search_audit_data(self, user_filter=None, site_filter=None, fecha_filter=None):
        """
        Busca datos de auditoría con filtros
        (Wrapper para get_table_snapshot con mejor nombre semántico)
        
        Args:
            user_filter (str, optional): Nombre de usuario
            site_filter (str, optional): Filtro de sitio
            fecha_filter (str, optional): Fecha YYYY-MM-DD
        
        Returns:
            dict: Snapshot de datos formateados
        """
        return self.get_table_snapshot(
            user_filter=user_filter,
            site_filter=site_filter,
            fecha_filter=fecha_filter
        )
    
    def apply_snapshot_to_sheet(self, sheet, snapshot):
        """
        Aplica un snapshot de datos al tksheet
        
        Args:
            sheet: Widget tksheet
            snapshot (dict): Snapshot con headers, rows, column_widths
        """
        # Aplicar datos
        if snapshot['row_count'] == 0:
            sheet.set_sheet_data([["No se encontraron resultados"] + [""] * (len(snapshot['headers'])-1)])
        else:
            sheet.set_sheet_data(snapshot['rows'])
        
        # Aplicar anchos de columna
        for idx, col_name in enumerate(snapshot['headers']):
            if col_name in snapshot['column_widths']:
                try:
                    sheet.column_width(idx, int(snapshot['column_widths'][col_name]))
                except Exception:
                    pass
        
        sheet.redraw()
        print(f"[DEBUG] Audit search returned {snapshot['row_count']} results")
    
    def clear_filters(self, user_var, site_var, fecha_var):
        """
        Limpia las variables de filtros
        
        Args:
            user_var (tk.StringVar): Variable de usuario
            site_var (tk.StringVar): Variable de sitio
            fecha_var (tk.StringVar): Variable de fecha
        """
        user_var.set("")
        site_var.set("")
        fecha_var.set("")
