"""
Controlador para Specials Sin Asignar (Unassigned Specials)
Maneja la lógica de negocio entre el modelo y la vista
"""

from models import unassigned_specials_model


class UnassignedSpecialsController:
    """Controlador para gestionar specials sin asignar"""
    
    def __init__(self, username):
        """
        Inicializa el controlador
        
        Args:
            username: Nombre del usuario (Lead Supervisor)
        """
        self.username = username
        self.row_ids = []  # Cache de IDs de specials
        self.row_cache = []  # Cache de datos formateados
        
    def load_data(self):
        """
        Carga los specials sin asignar desde el último START SHIFT
        
        Returns:
            Tupla (éxito: bool, datos: list, mensaje_error: str)
            datos es una lista de listas formateadas para el sheet
        """
        try:
            # Obtener último START SHIFT
            fecha_inicio = unassigned_specials_model.get_last_shift_start(self.username)
            
            if not fecha_inicio:
                print(f"[INFO] No hay turno activo para {self.username}")
                self.row_ids.clear()
                self.row_cache.clear()
                return True, [], "No hay shift activo"
            
            # Cargar specials sin marcar
            rows = unassigned_specials_model.load_unassigned_specials_data(fecha_inicio)
            
            # Formatear datos
            formatted_data = []
            self.row_ids.clear()
            
            for row in rows:
                self.row_ids.append(row[0])  # ID_special
                
                # Resolver nombre de sitio si es ID
                sitio_display = ""
                if row[2]:  # ID_Sitio
                    sitio_nombre = unassigned_specials_model.get_site_name(row[2])
                    if sitio_nombre:
                        sitio_display = f"{row[2]} {sitio_nombre}"
                    else:
                        sitio_display = str(row[2])
                
                formatted_row = [
                    str(row[0]),  # ID
                    str(row[1]) if row[1] else "",  # FechaHora
                    sitio_display,  # Sitio
                    str(row[3]) if row[3] else "",  # Actividad
                    str(row[4]) if row[4] else "",  # Cantidad
                    str(row[5]) if row[5] else "",  # Camera
                    str(row[6]) if row[6] else "",  # Descripcion
                    str(row[7]) if row[7] else "",  # Usuario
                    str(row[8]) if row[8] else "",  # TZ
                    str(row[9]) if row[9] else "Sin Asignar"  # Supervisor
                ]
                formatted_data.append(formatted_row)
            
            self.row_cache = formatted_data.copy()
            
            print(f"[INFO] Cargados {len(formatted_data)} specials sin asignar")
            return True, formatted_data, ""
            
        except Exception as e:
            error_msg = f"Error al cargar specials sin asignar: {str(e)}"
            print(f"[ERROR] UnassignedSpecialsController.load_data: {e}")
            import traceback
            traceback.print_exc()
            return False, [], error_msg
    
    def get_supervisors(self):
        """
        Obtiene la lista de supervisores disponibles
        
        Returns:
            Lista de nombres de supervisores
        """
        supervisores = unassigned_specials_model.get_supervisors_list()
        return supervisores if supervisores else []
    
    def assign_supervisor_to_rows(self, row_indices, supervisor_name):
        """
        Asigna un supervisor a las filas seleccionadas
        
        Args:
            row_indices: Lista de índices de filas seleccionadas
            supervisor_name: Nombre del supervisor a asignar
            
        Returns:
            Tupla (éxito: bool, mensaje: str)
        """
        try:
            # Obtener IDs de specials seleccionados
            special_ids = []
            for row_idx in row_indices:
                if row_idx < len(self.row_ids):
                    special_ids.append(self.row_ids[row_idx])
            
            if not special_ids:
                return False, "No se encontraron IDs válidos para asignar"
            
            # Asignar supervisor
            success, updated_count, error_msg = unassigned_specials_model.assign_supervisor(
                special_ids, supervisor_name
            )
            
            if success:
                return True, f"Supervisor asignado correctamente a {updated_count} special(s)"
            else:
                return False, error_msg
                
        except Exception as e:
            error_msg = f"Error al asignar supervisor: {str(e)}"
            print(f"[ERROR] UnassignedSpecialsController.assign_supervisor_to_rows: {e}")
            import traceback
            traceback.print_exc()
            return False, error_msg
