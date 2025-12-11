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
            dict: Diccionario agrupado por usuario_covering con sus breaks
        """
        raw_data = load_covers_from_db()
        
        # Agrupar por usuario_covering
        grouped_data = {}
        for row in raw_data:
            break_id = row[0] if row[0] else ""
            hora = str(row[1]) if row[1] else ""
            usuario_covered = row[2] if row[2] else ""
            usuario_covering = row[3] if row[3] else ""
            estado = row[4] if row[4] else ""
            aprobacion = row[5] if row[5] else ""
            
            if usuario_covering not in grouped_data:
                grouped_data[usuario_covering] = []
            
            grouped_data[usuario_covering].append({
                'id': break_id,
                'hora': hora,
                'usuario_covered': usuario_covered,
                'estado': estado,
                'aprobacion': aprobacion
            })
        
        return grouped_data

    @staticmethod
    def get_table_snapshot():
        """Genera la estructura tabular lista para la vista"""
        grouped_data = BreaksController.load_covers_data()

        covering_users = sorted(
            grouped_data.keys(),
            key=lambda name: (name is None or name == "", str(name or "").lower())
        )

        display_headers = [
            usuario if usuario not in (None, "") else "Sin asignar"
            for usuario in covering_users
        ]

        headers = ["Hora Programada"] + display_headers

        all_horas = set()
        for breaks_list in grouped_data.values():
            for break_info in breaks_list:
                if break_info['hora']:
                    all_horas.add(break_info['hora'])

        sorted_horas = sorted(all_horas)

        cell_map = {}
        rows = []

        for row_index, hora in enumerate(sorted_horas):
            row = [hora]
            for col_offset, usuario_covering in enumerate(covering_users, start=1):
                matching_breaks = [
                    break_info for break_info in grouped_data.get(usuario_covering, [])
                    if break_info['hora'] == hora
                ]

                if matching_breaks:
                    cell_map[(row_index, col_offset)] = [
                        break_info['id'] for break_info in matching_breaks if break_info['id']
                    ]

                usuarios_cubiertos = [break_info['usuario_covered'] for break_info in matching_breaks]
                row.append(", ".join(usuarios_cubiertos) if usuarios_cubiertos else "")

            rows.append(row)

        return {
            "headers": headers,
            "rows": rows,
            "cell_map": cell_map,
            "column_keys": covering_users,
            "row_count": len(sorted_horas),
            "column_count": len(headers),
        }
    
    @staticmethod
    def add_break(user_covered, user_covering, break_time, supervisor, callback=None):
        """Agrega un nuevo break con validación y conversión de nombres a IDs
        
        Args:
            user_covered (str): Nombre del usuario a cubrir
            user_covering (str): Nombre del usuario que cubre
            break_time (str): Hora del break en formato HH:MM:SS
            supervisor (str): Nombre del supervisor que aprueba
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
        supervisor_id = get_user_id_by_name(supervisor)
        
        if not user_covered_id or not user_covering_id:
            print(f"[ERROR] Usuario no encontrado: covered={user_covered}, covering={user_covering}")
            return False
        
        if not supervisor_id:
            print(f"[ERROR] Supervisor no encontrado: {supervisor}")
            return False
        
        # Construir datetime completo: fecha actual + hora especificada
        today = date.today()
        datetime_str = f"{today.strftime('%Y-%m-%d')} {break_time}"
        
        # Insertar en BD
        success = add_break_to_db(user_covered_id, user_covering_id, datetime_str, supervisor_id)
        
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
