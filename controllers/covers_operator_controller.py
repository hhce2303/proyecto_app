"""
CoversOperatorController - Controlador para lógica de covers del operador.
Maneja carga, cálculo de duración, posición en turno y cancelación.

Responsabilidades:
- Obtener covers realizados desde último START SHIFT
- Calcular duración de covers en formato legible
- Calcular posición en turno/cola
- Coordinar cancelación de covers programados
"""
from datetime import datetime, timedelta
from models import cover_model


class CoversOperatorController:
    """
    Controller para módulo Covers de operador.
    Gestiona lógica de negocio sin dependencias de UI.
    """
    
    def __init__(self, username):
        """
        Inicializa el controller
        
        Args:
            username (str): Nombre del usuario
        """
        self.username = username
    
    def load_covers_data(self):
        """
        Carga covers realizados con información enriquecida.
        
        Returns:
            list: Lista de dicts con campos:
                - id_cover_realizado (int)
                - id_cover_programado (int or None)
                - nombre_usuario (str)
                - time_request (str)
                - cover_in (str)
                - cover_out (str or "En progreso")
                - duracion (str) - "45 min", "1h 20min"
                - turno (str) - "3/7" (posición/total)
                - motivo (str)
                - covered_by (str)
                - activo (str) - "Sí" o "No"
        """
        try:
            print(f"[DEBUG] CoversOperatorController: Cargando covers para {self.username}")
            
            # Obtener último START SHIFT
            last_shift = self._get_last_shift_start()
            
            # ⭐ Si no hay último shift, cargar TODOS los covers del usuario
            if not last_shift:
                print("[DEBUG] CoversOperatorController: No hay último shift, cargando TODOS los covers")
            else:
                print(f"[DEBUG] CoversOperatorController: Último shift: {last_shift}")
            
            # Query covers realizados (con o sin filtro de fecha)
            covers = cover_model.get_covers_realizados_by_user(
                username=self.username,
                fecha_desde=last_shift  # None si no hay shift
            )
            
            if not covers:
                print("[DEBUG] CoversOperatorController: No hay covers en BD")
                return []
            
            print(f"[DEBUG] CoversOperatorController: Obtenidos {len(covers)} covers de BD")
            
            # Obtener posiciones en turno
            turnos_dict = self._calculate_turnos(covers)
            
            # Procesar cada cover
            processed = []
            for idx, cover in enumerate(covers):
                try:
                    # Extraer datos del cover
                    # (id_realizado, nombre_usuario, cover_in, cover_out,
                    #  motivo, covered_by, id_programacion_covers, id_programado, time_request)
                    if len(cover) < 9:
                        print(f"[ERROR] Cover con estructura inválida (idx={idx}): {len(cover)} campos")
                        continue
                    
                    (
                        id_realizado, nombre_usuario, cover_in, cover_out,
                        motivo, covered_by, id_programacion_covers, id_programado, time_request
                    ) = cover
                    
                    # ⭐ Calcular "Activo" basado en Cover_out (NULL = activo)
                    activo = 1 if cover_out is None else 0
                    
                    # ⭐ CALCULAR DURACIÓN
                    duracion_str = self._calculate_duration(cover_in, cover_out)
                    
                    # ⭐ OBTENER TURNO
                    turno_str = turnos_dict.get(id_realizado, "N/A")
                    
                    # Formatear fechas
                    time_request_str = time_request.strftime("%Y-%m-%d %H:%M:%S") if time_request else "N/A"
                    cover_in_str = cover_in.strftime("%Y-%m-%d %H:%M:%S") if cover_in else "N/A"
                    cover_out_str = cover_out.strftime("%Y-%m-%d %H:%M:%S") if cover_out else "En progreso"
                    
                    activo_str = "Sí" if activo == 1 else "No"
                    
                    processed.append({
                        'id_cover_realizado': id_realizado,
                        'id_cover_programado': id_programado,
                        'nombre_usuario': nombre_usuario or "",
                        'time_request': time_request_str,
                        'cover_in': cover_in_str,
                        'cover_out': cover_out_str,
                        'duracion': duracion_str,
                        'turno': turno_str,
                        'motivo': motivo or "",
                        'covered_by': covered_by or "",
                        'activo': activo_str
                    })
                
                except ValueError as ve:
                    print(f"[ERROR] Error desempaquetando cover {idx}: {ve}")
                    continue
                except Exception as e:
                    print(f"[ERROR] Error procesando cover {idx}: {e}")
                    import traceback
                    traceback.print_exc()
                    continue
            
            print(f"[DEBUG] CoversOperatorController: Procesados {len(processed)} covers")
            return processed
        
        except Exception as e:
            print(f"[ERROR] CoversOperatorController.load_covers_data: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def _get_last_shift_start(self):
        """
        Obtiene timestamp del último START SHIFT del usuario.
        
        Returns:
            datetime: Timestamp del último START SHIFT o None
        """
        from models.database import get_connection
        
        try:
            conn = get_connection()
            if not conn:
                return None
            
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT MAX(FechaHora)
                FROM Eventos
                WHERE ID_Usuario = (SELECT ID_Usuario FROM user WHERE Nombre_Usuario = %s)
                AND Nombre_Actividad = 'START SHIFT'
            """, (self.username,))
            
            result = cursor.fetchone()
            
            cursor.close()
            conn.close()
            
            return result[0] if result and result[0] else None
        
        except Exception as e:
            print(f"[ERROR] _get_last_shift_start: {e}")
            return None
    
    def _calculate_duration(self, cover_in, cover_out):
        """
        Calcula duración del cover en formato legible.
        
        Args:
            cover_in (datetime): Inicio del cover
            cover_out (datetime or None): Fin del cover
        
        Returns:
            str: "45 min", "1h 20min", "En progreso"
        """
        if not cover_in:
            return "N/A"
        
        if not cover_out:
            # Cover en progreso - calcular desde ahora
            duration = datetime.now() - cover_in
            total_minutes = int(duration.total_seconds() / 60)
            
            if total_minutes < 60:
                return f"{total_minutes} min ⏱️"
            else:
                hours = total_minutes // 60
                minutes = total_minutes % 60
                return f"{hours}h {minutes}min ⏱️"
        
        # Cover completado
        duration = cover_out - cover_in
        total_minutes = int(duration.total_seconds() / 60)
        
        if total_minutes < 60:
            return f"{total_minutes} min"
        else:
            hours = total_minutes // 60
            minutes = total_minutes % 60
            if minutes == 0:
                return f"{hours}h"
            return f"{hours}h {minutes}min"
    
    def _calculate_turnos(self, covers):
        """
        Calcula posición en turno para cada cover.
        
        Lógica: Ordenar covers por Cover_in, asignar posición secuencial.
        
        Args:
            covers (list): Lista de tuplas de covers
        
        Returns:
            dict: {id_realizado: "3/7", ...}
        """
        try:
            # Ordenar por Cover_in (índice 2)
            sorted_covers = sorted(
                covers,
                key=lambda x: x[2] if x[2] else datetime.min
            )
            
            total = len(sorted_covers)
            turnos = {}
            
            for idx, cover in enumerate(sorted_covers, start=1):
                id_realizado = cover[0]
                turnos[id_realizado] = f"{idx}/{total}"
            
            return turnos
        
        except Exception as e:
            print(f"[ERROR] _calculate_turnos: {e}")
            return {}
    
    def get_user_position_in_queue(self):
        """
        Obtiene la posición del usuario en la cola de covers programados activos.
        
        Lógica:
        - Consulta covers_programados con is_Active = 1
        - Ordena por Time_request ASC (más antiguo primero)
        - Encuentra posición del usuario en la cola
        
        Returns:
            dict: {
                'position': int or None - Posición en cola (1-based)
                'total': int - Total de covers programados activos
                'message': str - Mensaje formateado para UI
            }
        """
        try:
            # Obtener covers programados activos desde el modelo
            active_covers = cover_model.get_active_covers_programados()
            
            if not active_covers:
                return {
                    'position': None,
                    'total': 0,
                    'message': '✅ No hay covers en cola'
                }
            
            total_active = len(active_covers)
            
            # Buscar posición del usuario en la cola
            # Tupla: (ID_Cover, ID_user, Time_request, Station, Reason, Approved)
            user_position = None
            for idx, cover in enumerate(active_covers, start=1):
                id_user = cover[1]  # índice 1 = ID_user
                if id_user == self.username:
                    user_position = idx
                    break
            
            if user_position:
                return {
                    'position': user_position,
                    'total': total_active,
                    'message': f'🎯 Tu posición en cola: {user_position}/{total_active}'
                }
            else:
                return {
                    'position': None,
                    'total': total_active,
                    'message': f'📊 Covers en cola: {total_active}'
                }
        
        except Exception as e:
            print(f"[ERROR] get_user_position_in_queue: {e}")
            import traceback
            traceback.print_exc()
            return {
                'position': None,
                'total': 0,
                'message': '❌ Error calculando posición'
            }
    
    def get_user_active_cover(self):
        """
        Obtiene el cover programado activo del usuario actual.
        
        Returns:
            tuple or None: (ID_Cover, Time_request, Reason) del cover activo
                          o None si no tiene cover activo
        """
        try:
            # Obtener covers programados activos
            active_covers = cover_model.get_active_covers_programados()
            
            if not active_covers:
                return None
            
            # Buscar cover del usuario
            # Tupla: (ID_Cover, ID_user, Time_request, Station, Reason, Approved)
            for cover in active_covers:
                id_user = cover[1]  # índice 1 = ID_user
                if id_user == self.username:
                    id_cover = cover[0]
                    time_request = cover[2]
                    reason = cover[4]
                    return (id_cover, time_request, reason)
            
            return None
        
        except Exception as e:
            print(f"[ERROR] get_user_active_cover: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def cancel_cover(self, programado_id):
        """
        Cancela un cover programado (UPDATE is_Active = 0).
        
        Args:
            programado_id (int): ID del cover programado
        
        Returns:
            tuple: (success: bool, message: str)
        """
        try:
            success, message = cover_model.cancel_cover_programado(programado_id)
            return success, message
        
        except Exception as e:
            print(f"[ERROR] CoversOperatorController.cancel_cover: {e}")
            import traceback
            traceback.print_exc()
            return False, str(e)
