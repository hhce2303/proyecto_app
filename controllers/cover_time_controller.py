from models.cover_time_model import (
    get_cover_users_list,
    load_covers_programados,
    load_covers_realizados
)
from datetime import datetime


class CoverTimeController:
    """Controlador para gestionar covers programados y realizados"""
    
    # Configuración de columnas deseadas por tabla
    COLUMNS_CONFIG = {
        "covers_programados": ["ID_user", "Time_request", "Station", "Reason", "Approved", "is_Active"],
        "covers_realizados": ["Nombre_usuarios", "Cover_in", "Cover_out", "Covered_by", "Motivo"]
    }
    
    def __init__(self):
        pass
    
    @staticmethod
    def get_users_for_filter():
        """Obtiene lista de usuarios para el filtro
        
        Returns:
            list: Lista de nombres de usuario
        """
        return get_cover_users_list()
    
    @staticmethod
    def calculate_duration(cover_in, cover_out):
        """Calcula la duración entre dos timestamps
        
        Args:
            cover_in: Datetime de inicio
            cover_out: Datetime de fin
            
        Returns:
            str: Duración en formato HH:MM:SS o cadena vacía
        """
        if not cover_in or not cover_out:
            return ""
        
        try:
            if isinstance(cover_in, str):
                cover_in = datetime.strptime(cover_in, "%Y-%m-%d %H:%M:%S")
            if isinstance(cover_out, str):
                cover_out = datetime.strptime(cover_out, "%Y-%m-%d %H:%M:%S")
            
            delta = cover_out - cover_in
            hours, remainder = divmod(int(delta.total_seconds()), 3600)
            minutes, seconds = divmod(remainder, 60)
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        except Exception as e:
            print(f"[ERROR] calculate_duration: {e}")
            return "Error"
    
    @staticmethod
    def get_table_snapshot_programados():
        """Genera estructura tabular para covers_programados
        
        Returns:
            dict: headers, rows, metadata
        """
        col_names, rows = load_covers_programados()
        
        if not col_names or not rows:
            return {
                "headers": ["#", "Usuario", "Hora solicitud", "Estación", "Razón", "Aprobación", "Estado"],
                "rows": [],
                "row_count": 0,
                "inactive_rows": []
            }
        
        # Filtrar columnas deseadas
        desired_cols = CoverTimeController.COLUMNS_CONFIG["covers_programados"]
        indices = [col_names.index(c) for c in desired_cols if c in col_names]
        
        # Buscar índices de columnas específicas
        approved_idx = col_names.index("Approved") if "Approved" in col_names else None
        is_active_idx = col_names.index("is_Active") if "is_Active" in col_names else None
        
        formatted_rows = []
        inactive_rows = []
        
        for idx, row in enumerate(rows, start=1):
            filtered_row = [row[i] for i in indices]
            
            # Convertir None a string vacío
            filtered_row = ["" if v is None else str(v) for v in filtered_row]
            
            # Transformar Approved: 1 = "Aprobado", 0 = "No Aprobado"
            if approved_idx is not None and len(filtered_row) > 4:
                try:
                    approved_val = int(filtered_row[4]) if filtered_row[4] else 0
                    filtered_row[4] = "Aprobado" if approved_val == 1 else "No Aprobado"
                except (ValueError, IndexError):
                    filtered_row[4] = "No Aprobado"
            
            # Transformar is_Active: 1 = "Abierto", 0 = "Cerrado"
            if is_active_idx is not None and len(filtered_row) > 5:
                try:
                    active_val = int(filtered_row[5]) if filtered_row[5] else 0
                    filtered_row[5] = "Abierto" if active_val == 1 else "Cerrado"
                    
                    # Guardar índice de filas inactivas
                    if active_val == 0:
                        inactive_rows.append(idx - 1)  # idx-1 porque las filas empiezan en 0
                except (ValueError, IndexError):
                    filtered_row[5] = "Cerrado"
            
            # Agregar índice al inicio
            filtered_row.insert(0, str(idx))
            formatted_rows.append(filtered_row)
        
        return {
            "headers": ["#", "Usuario", "Hora solicitud", "Estación", "Razón", "Aprobación", "Estado"],
            "rows": formatted_rows,
            "row_count": len(formatted_rows),
            "inactive_rows": inactive_rows
        }
    
    @staticmethod
    def get_table_snapshot_realizados(user_filter=None, fecha_desde=None, fecha_hasta=None):
        """Genera estructura tabular para covers_realizados con filtros
        
        Args:
            user_filter (str): Usuario a filtrar o None
            fecha_desde (str): Fecha inicio o None
            fecha_hasta (str): Fecha fin o None
            
        Returns:
            dict: headers, rows, metadata
        """
        col_names, rows = load_covers_realizados(user_filter, fecha_desde, fecha_hasta)
        
        if not col_names or not rows:
            return {
                "headers": ["#", "Usuario", "Inicio Cover", "Duración", "Fin Cover", "Cubierto por", "Motivo"],
                "rows": [["1", "No hay resultados", "", "", "", "", ""]],
                "row_count": 0
            }
        
        # Filtrar columnas deseadas
        desired_cols = CoverTimeController.COLUMNS_CONFIG["covers_realizados"]
        indices = [col_names.index(c) for c in desired_cols if c in col_names]
        
        # Buscar índices de Cover_in y Cover_out para calcular duración
        cover_in_idx = col_names.index("Cover_in") if "Cover_in" in col_names else None
        cover_out_idx = col_names.index("Cover_out") if "Cover_out" in col_names else None
        
        formatted_rows = []
        for idx, row in enumerate(rows, start=1):
            filtered_row = [row[i] for i in indices]
            
            # Calcular duración
            duration_str = ""
            if cover_in_idx is not None and cover_out_idx is not None:
                duration_str = CoverTimeController.calculate_duration(
                    row[cover_in_idx],
                    row[cover_out_idx]
                )
            
            # Convertir None a string vacío
            filtered_row = ["" if v is None else str(v) for v in filtered_row]
            
            # Insertar duración después de Cover_in (índice 2)
            filtered_row.insert(2, duration_str)
            
            # Agregar índice al inicio
            filtered_row.insert(0, str(idx))
            formatted_rows.append(filtered_row)
        
        return {
            "headers": ["#", "Usuario", "Inicio Cover", "Duración", "Fin Cover", "Cubierto por", "Motivo"],
            "rows": formatted_rows,
            "row_count": len(formatted_rows)
        }
