from models.rol_cover_model import cargar_operadores_rol, en_dis_able_access


class RolCoverController:
    @staticmethod
    def get_operators_covers_statuses():
        """Obtiene operadores separados por su acceso a covers (Statuses)"""
        operadores_data = cargar_operadores_rol()
        
        # Statuses = 2 significa acceso a covers
        # Statuses != 2 significa sin acceso a covers
        con_acceso = [op[0] for op in operadores_data if op[1] == 2]
        sin_acceso = [op[0] for op in operadores_data if op[1] != 2]
        
        return con_acceso, sin_acceso
    
    @staticmethod
    def en_dis_able_access_covers(operadores, new_status):
        """Habilita o deshabilita acceso a covers para los operadores seleccionados
        
        Args:
            operadores: Lista de nombres de operadores
            new_status: 2 para habilitar acceso, 1 para deshabilitar
        
        Returns:
            bool: True si la operación fue exitosa
        """
        if not operadores:
            print("[DEBUG] en_dis_able_access_covers: Lista de operadores vacía")
            return False
        
        if new_status not in [1, 2]:
            print(f"[ERROR] en_dis_able_access_covers: Status inválido {new_status}")
            return False
        
        # Delegar al modelo sin validación adicional
        success = en_dis_able_access(operadores, new_status)
        
        if success:
            action = "habilitado" if new_status == 2 else "deshabilitado"
            print(f"[DEBUG] Acceso {action} para {len(operadores)} operador(es)")
        
        return success
    
    @staticmethod
    def refresh_operators_list():
        """Refresca la lista de operadores desde la BD"""
        return cargar_operadores_rol()
             
        


