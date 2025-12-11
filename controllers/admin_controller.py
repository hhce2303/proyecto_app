"""
Admin Controller - Lógica de negocio para administración de tablas
Intermedia entre modelo y vista
"""
from models.admin_model import (
    get_table_list, get_table_structure, load_table_data,
    get_record_by_pk, update_record, create_record, get_users_list
)
from backend_super import safe_delete
import traceback


class AdminController:
    """
    Controlador para módulo de administración de tablas
    """
    
    def __init__(self, username):
        """
        Args:
            username: Usuario actual para logs y auditoría
        """
        self.username = username
        self.current_table = None
        self.metadata = {
            "col_names": [],
            "col_names_original": [],
            "pk": None,
            "rows": [],
            "fecha_cols": []
        }
    
    def get_available_tables(self):
        """Retorna lista de tablas disponibles"""
        return get_table_list()
    
    def load_table(self, table_name, fecha_desde=None, fecha_hasta=None, 
                   columna_fecha=None, tipo_evento=None):
        """
        Carga una tabla con filtros
        
        Args:
            table_name: Nombre de la tabla
            fecha_desde: Fecha desde (opcional)
            fecha_hasta: Fecha hasta (opcional)
            columna_fecha: Columna para filtrar fechas (opcional)
            tipo_evento: Filtro de tipo de evento (opcional, solo para eventos)
        
        Returns:
            tuple: (rows, col_names) o (None, None) si error
        """
        try:
            rows, col_names, col_names_original, pk_name, fecha_cols = load_table_data(
                table_name, 
                fecha_desde=fecha_desde,
                fecha_hasta=fecha_hasta,
                columna_fecha=columna_fecha,
                tipo_evento=tipo_evento
            )
            
            # Guardar metadata
            self.current_table = table_name
            self.metadata["col_names"] = col_names
            self.metadata["col_names_original"] = col_names_original
            self.metadata["pk"] = pk_name
            self.metadata["rows"] = rows
            self.metadata["fecha_cols"] = fecha_cols
            
            return (rows, col_names)
            
        except Exception as e:
            print(f"[ERROR] AdminController.load_table: {e}")
            traceback.print_exc()
            return (None, None)
    
    def get_fecha_columns(self):
        """Retorna lista de columnas de fecha detectadas"""
        return self.metadata.get("fecha_cols", [])
    
    def get_record_for_edit(self, row_index):
        """
        Obtiene datos de un registro para editar (con columnas originales)
        
        Args:
            row_index: Índice de fila en self.metadata["rows"]
        
        Returns:
            dict: {col_name: value} o None si error
        """
        try:
            if not self.current_table or not self.metadata["rows"]:
                return None
            
            if row_index < 0 or row_index >= len(self.metadata["rows"]):
                return None
            
            displayed_row = self.metadata["rows"][row_index]
            pk_name = self.metadata["pk"]
            
            if not pk_name:
                return None
            
            # Obtener índice de PK en columnas mostradas
            pk_index = None
            for i, col in enumerate(self.metadata["col_names"]):
                if col == pk_name:
                    pk_index = i
                    break
            
            if pk_index is None:
                return None
            
            pk_value = displayed_row[pk_index]
            
            # Para tablas con JOIN, recargar con columnas originales
            if self.current_table in ["eventos", "gestion_breaks_programados"]:
                original_row = get_record_by_pk(self.current_table, pk_name, pk_value)
                if not original_row:
                    return None
                
                col_names = self.metadata["col_names_original"]
                row_data = original_row
            else:
                col_names = self.metadata["col_names"]
                row_data = displayed_row
            
            # Construir diccionario
            result = {}
            for i, col in enumerate(col_names):
                if i < len(row_data):
                    result[col] = row_data[i]
            
            return result
            
        except Exception as e:
            print(f"[ERROR] get_record_for_edit: {e}")
            traceback.print_exc()
            return None
    
    def save_edit(self, row_index, field_values):
        """
        Guarda edición de un registro
        
        Args:
            row_index: Índice de la fila
            field_values: Dict {col_name: new_value}
        
        Returns:
            tuple: (success: bool, error_msg: str)
        """
        try:
            if not self.current_table or not self.metadata["rows"]:
                return (False, "No hay tabla cargada")
            
            if row_index < 0 or row_index >= len(self.metadata["rows"]):
                return (False, "Índice de fila inválido")
            
            displayed_row = self.metadata["rows"][row_index]
            pk_name = self.metadata["pk"]
            col_names = self.metadata["col_names_original"]
            
            if not pk_name:
                return (False, "No se pudo detectar la columna PK")
            
            # Obtener PK value
            pk_index = None
            for i, col in enumerate(self.metadata["col_names"]):
                if col == pk_name:
                    pk_index = i
                    break
            
            if pk_index is None:
                return (False, f"Columna PK '{pk_name}' no encontrada")
            
            pk_value = displayed_row[pk_index]
            
            # Actualizar
            success = update_record(
                self.current_table,
                pk_name,
                pk_value,
                col_names,
                field_values
            )
            
            if not success:
                return (False, "Error al actualizar registro")
            
            return (True, "")
            
        except Exception as e:
            error_msg = str(e)
            print(f"[ERROR] save_edit: {error_msg}")
            traceback.print_exc()
            
            # Mensajes amigables para errores FK
            if "foreign key" in error_msg.lower() or "cannot add or update" in error_msg.lower():
                if "User_logged" in error_msg or "ID_Usuario" in error_msg:
                    return (False, "Error: El usuario especificado no existe. Por favor, seleccione un usuario válido de la lista.")
                elif "ID_Sitio" in error_msg:
                    return (False, "Error: El sitio especificado no existe. Por favor, ingrese un ID de sitio válido.")
                else:
                    return (False, f"Error de clave foránea: {error_msg}")
            
            return (False, f"Error: {error_msg}")
    
    def get_fields_for_create(self):
        """
        Obtiene lista de campos para crear un nuevo registro
        
        Returns:
            list: Lista de nombres de columnas (filtrando IDs autoincrementales)
        """
        if not self.current_table:
            return []
        
        col_names = self.metadata["col_names_original"]
        
        # Filtrar columnas según la tabla
        if self.current_table == "Sitios":
            # Sitios no tiene autoincrement en ID, mostrar todo
            return col_names
        else:
            # Omitir columnas ID autoincrementales
            visible_cols = []
            for c in col_names:
                c_lower = c.lower()
                # Omitir si es ID y parece autoincremental
                if c_lower in ('id', 'id_') or (c_lower.startswith('id_') and 
                   any(word in c_lower for word in ['usuario', 'sitio', 'actividad', 
                   'cover', 'sesion', 'estacion', 'special', 'evento', 'break'])):
                    continue
                visible_cols.append(c)
            return visible_cols
    
    def save_create(self, field_values):
        """
        Guarda nuevo registro
        
        Args:
            field_values: Dict {col_name: value}
        
        Returns:
            tuple: (success: bool, error_msg: str)
        """
        try:
            if not self.current_table:
                return (False, "No hay tabla seleccionada")
            
            col_names = self.get_fields_for_create()
            
            success = create_record(
                self.current_table,
                col_names,
                field_values
            )
            
            if not success:
                return (False, "Error al crear registro")
            
            return (True, "")
            
        except Exception as e:
            error_msg = str(e)
            print(f"[ERROR] save_create: {error_msg}")
            traceback.print_exc()
            return (False, f"Error: {error_msg}")
    
    def delete_selected(self, row_index):
        """
        Elimina un registro (usando sistema papelera)
        
        Args:
            row_index: Índice de la fila
        
        Returns:
            tuple: (success: bool, error_msg: str)
        """
        try:
            if not self.current_table or not self.metadata["rows"]:
                return (False, "No hay tabla cargada")
            
            if row_index < 0 or row_index >= len(self.metadata["rows"]):
                return (False, "Índice de fila inválido")
            
            displayed_row = self.metadata["rows"][row_index]
            pk_name = self.metadata["pk"]
            
            if not pk_name:
                return (False, "No se pudo detectar la columna PK")
            
            # Obtener PK value
            pk_index = None
            for i, col in enumerate(self.metadata["col_names"]):
                if col == pk_name:
                    pk_index = i
                    break
            
            if pk_index is None:
                return (False, f"Columna PK '{pk_name}' no encontrada")
            
            pk_value = displayed_row[pk_index]
            
            # Usar safe_delete (sistema papelera)
            success = safe_delete(
                self.current_table,
                pk_name,
                pk_value,
                deleted_by=self.username
            )
            
            if not success:
                return (False, "Error al eliminar registro")
            
            return (True, "")
            
        except Exception as e:
            error_msg = str(e)
            print(f"[ERROR] delete_selected: {error_msg}")
            traceback.print_exc()
            return (False, f"Error: {error_msg}")
    
    def get_users_for_combobox(self):
        """
        Obtiene lista de usuarios para comboboxes
        
        Returns:
            tuple: (users_list, id_to_name_dict)
        """
        return get_users_list()
    
    @staticmethod
    def sanitize_col_id(col_name):
        """
        Limpia nombre de columna para IDs seguros
        
        Args:
            col_name: Nombre original de columna
        
        Returns:
            str: Nombre sanitizado
        """
        if not col_name:
            return "col"
        
        sanitized = "".join(c if c.isalnum() else "_" for c in col_name)
        if not sanitized[0].isalpha():
            sanitized = "col_" + sanitized
        return sanitized