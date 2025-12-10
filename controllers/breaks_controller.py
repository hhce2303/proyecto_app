from datetime import date
from models.breaks_model import add_break_to_db, load_covers_from_db, delete_break_from_db, get_user_id_by_name
from models.user_model import load_users


class BreaksController:
    """Controlador para gestionar breaks programados"""
    
    def __init__(self):
        pass
    
    @staticmethod
    def load_users_list():
        """Carga lista de usuarios desde la base de datos
        
        Returns:
            list: Lista de nombres de usuario
        """
        users = load_users()
        return users if users else []
    
    @staticmethod
    def load_covers_data():
        """Carga datos de covers desde la BD y los formatea para la vista
        
        Returns:
            list: Lista de listas con datos formateados para tksheet
        """
        raw_data = load_covers_from_db()
        formatted_data = []
        
        for idx, row in enumerate(raw_data, start=1):
            break_id = row[0] if row[0] else ""
            usuario_cubierto = row[1] if row[1] else ""
            usuario_cubre = row[2] if row[2] else ""
            hora = str(row[3]) if row[3] else ""
            estado = row[4] if row[4] else ""
            aprobacion = row[5] if row[5] else ""
            
            formatted_data.append([
                str(idx),
                usuario_cubierto,
                usuario_cubre,
                hora,
                estado,
                aprobacion
            ])
        
        return formatted_data
    
    @staticmethod
    def add_break(user_covered, user_covering, break_time, callback=None):
        """Agrega un nuevo break con validación y conversión de nombres a IDs
        
        Args:
            user_covered (str): Nombre del usuario a cubrir
            user_covering (str): Nombre del usuario que cubre
            break_time (str): Hora del break en formato HH:MM:SS
            callback (callable): Función a llamar después de agregar
            
        Returns:
            bool: True si éxito
        """
        # Validación de datos
        if not user_covered or not user_covering or not break_time:
            print("[WARNING] Faltan datos para agregar break")
            return False
        
        if user_covered == user_covering:
            print("[WARNING] Un usuario no puede cubrirse a sí mismo")
            return False
        
        # Convertir nombres a IDs
        user_covered_id = get_user_id_by_name(user_covered)
        user_covering_id = get_user_id_by_name(user_covering)
        
        if not user_covered_id or not user_covering_id:
            print(f"[ERROR] Usuario no encontrado: covered={user_covered}, covering={user_covering}")
            return False
        
        # Construir datetime completo: fecha actual + hora especificada
        today = date.today()
        datetime_str = f"{today.strftime('%Y-%m-%d')} {break_time}"
        
        # Insertar en BD
        success = add_break_to_db(user_covered_id, user_covering_id, datetime_str)
        
        if success:
            print(f"[DEBUG] Break agregado: {user_covered} -> {user_covering} a las {break_time}")
            if callback:
                callback()
        
        return success
    
    @staticmethod
    def delete_break(break_id, callback=None):
        """Elimina un break programado
        
        Args:
            break_id (int): ID del break
            callback (callable): Función a llamar después de eliminar
            
        Returns:
            bool: True si éxito
        """
        if not break_id:
            return False
        
        success = delete_break_from_db(break_id)
        
        if success and callback:
            callback()
        
        return success
