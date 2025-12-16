"""
Controlador de Specials para Operadores
Arquitectura: MVC - Capa de Controlador (Business Logic Layer)
Responsabilidad: Mediador entre Vista y Modelo
"""

from models import specials_model
from datetime import datetime, timedelta
from utils.timezone_adjuster import adjust_datetime, adjust_description_timestamps, get_timezone_offset
import re


class SpecialsOperatorController:
    """
    Controlador para gestión de specials del operador.
    Maneja la lógica de negocio para eventos especiales.
    """
    
    def __init__(self, username):
        """
        Inicializa el controlador.
        
        Args:
            username (str): Nombre del operador
        """
        self.username = username
    
    def load_specials_data(self):
        """
        Carga datos de specials formateados para la vista.
        
        Returns:
            list: Lista de diccionarios con:
                - id (int): ID del evento
                - id_special (int): ID en tabla specials (None si no enviado)
                - fecha_hora (str): Fecha/hora ajustada con timezone
                - sitio (str): Nombre del sitio con ID
                - actividad (str): Nombre de la actividad
                - cantidad (str): Cantidad
                - camera (str): Camera
                - descripcion (str): Descripción con timestamps ajustados
                - time_zone (str): Zona horaria
                - estado (str): Estado del envío ("", "Enviado a X", "Pendiente")
                - estado_color (str): Color para el estado ("green", "amber", None)
                - fecha_hora_original (datetime): Fecha original sin ajustes
                - descripcion_original (str): Descripción original sin ajustes
        """
        try:
            # Obtener último shift
            last_shift = specials_model.get_last_shift_start(self.username)
            if not last_shift:
                print(f"[DEBUG] No hay último shift para {self.username}")
                return []
            
            # Obtener eventos de grupos especiales
            eventos = specials_model.get_specials_eventos(self.username, last_shift)
            
            if not eventos:
                print(f"[DEBUG] No hay eventos especiales para {self.username}")
                return []
            
            print(f"[DEBUG] Procesando {len(eventos)} eventos especiales")
            processed = []
            
            for idx, evento in enumerate(eventos):
                try:
                    # Validar longitud de tupla
                    if len(evento) != 8:
                        print(f"[ERROR] Evento {idx} tiene {len(evento)} campos (esperado 8): {evento}")
                        continue
                    
                    (
                        id_evento, fecha_hora, id_sitio, nombre_actividad,
                        cantidad, camera, descripcion, usuario
                    ) = evento
                    
                    print(f"[DEBUG] Procesando evento {idx}: ID={id_evento}, Sitio={id_sitio}, Actividad={nombre_actividad}")
                    
                    # Guardar valores originales
                    fecha_hora_original = fecha_hora
                    descripcion_original = str(descripcion) if descripcion else ""
                    
                    # Obtener info del sitio (nombre y timezone)
                    nombre_sitio, time_zone = specials_model.get_site_info(id_sitio)
                    
                    # Formatear sitio para mostrar
                    if nombre_sitio and id_sitio:
                        display_sitio = f"{nombre_sitio} ({id_sitio})"
                    elif id_sitio:
                        display_sitio = str(id_sitio)
                    else:
                        display_sitio = nombre_sitio or ""
                    
                    # Ajustar fecha/hora con timezone usando timezone_adjuster
                    tz_offset_hours = get_timezone_offset(time_zone)
                    try:
                        if isinstance(fecha_hora, str):
                            fh = datetime.strptime(fecha_hora[:19], "%Y-%m-%d %H:%M:%S")
                        else:
                            fh = fecha_hora
                        
                        fh_adjusted = fh + timedelta(hours=tz_offset_hours)
                        fecha_str = fh_adjusted.strftime("%Y-%m-%d %H:%M:%S")
                    except Exception:
                        fecha_str = fecha_hora.strftime("%Y-%m-%d %H:%M:%S") if fecha_hora else ""
                    
                    # Ajustar timestamps en descripción
                    desc_adjusted = self._adjust_timestamps_in_description(
                        descripcion_original,
                        tz_offset_hours,
                        fh.date() if 'fh' in locals() else datetime.now().date()
                    )
                    
                    # Verificar si existe en tabla specials
                    special_data = specials_model.get_special_by_evento_id(id_evento)
                    
                    if special_data and len(special_data) >= 12:
                        # Existe in specials - comparar para determinar estado
                        (
                            id_special, special_fecha, special_sitio, special_actividad,
                            special_cantidad, special_camera, special_desc, supervisor,
                            special_tz, marked_status, marked_by, marked_at
                        ) = special_data
                        
                        # Normalizar valores para comparación
                        eventos_cantidad = int(cantidad) if cantidad is not None else 0
                        especials_cantidad = int(special_cantidad) if special_cantidad is not None else 0
                        
                        eventos_camera = str(camera).strip() if camera else ""
                        specials_camera = str(special_camera).strip() if special_camera else ""
                        
                        eventos_desc = str(desc_adjusted).strip()
                        specials_desc = str(special_desc).strip() if special_desc else ""
                        
                        eventos_fechahora = fecha_str
                        specials_fechahora = special_fecha.strftime("%Y-%m-%d %H:%M:%S") if special_fecha else ""
                        
                        # Comparar todos los campos
                        hay_cambios = (
                            eventos_fechahora != specials_fechahora or
                            id_sitio != special_sitio or
                            nombre_actividad != special_actividad or
                            eventos_cantidad != especials_cantidad or
                            eventos_camera != specials_camera or
                            eventos_desc != specials_desc
                        )
                        
                        if hay_cambios:
                            estado = "⏳ Pendiente por actualizar"
                            estado_color = "amber"
                            fecha_display = fecha_str
                            desc_display = desc_adjusted
                        else:
                            estado = f"✅ Enviado a {supervisor}"
                            estado_color = "green"
                            fecha_display = specials_fechahora
                            desc_display = special_desc if special_desc else desc_adjusted
                    else:
                        # No existe en specials
                        id_special = None
                        estado = ""
                        estado_color = None
                        fecha_display = fecha_str
                        desc_display = desc_adjusted
                    
                    # Agregar a lista procesada
                    processed.append({
                        'id': id_evento,
                        'id_special': id_special,
                        'fecha_hora': fecha_display,
                        'sitio': display_sitio,
                        'actividad': nombre_actividad or "",
                        'cantidad': str(cantidad) if cantidad is not None else "0",
                        'camera': camera or "",
                        'descripcion': desc_display,
                        'time_zone': time_zone or "",
                        'estado': estado,
                        'estado_color': estado_color,
                        'fecha_hora_original': fecha_hora_original,
                        'descripcion_original': descripcion_original,
                        'id_sitio': id_sitio,
                        'nombre_actividad': nombre_actividad,
                        'usuario': usuario
                    })
                
                except ValueError as ve:
                    print(f"[ERROR] Error desempaquetando evento {idx}: {ve}")
                    print(f"[ERROR] Datos del evento: {evento if 'evento' in locals() else 'N/A'}")
                    continue
                except Exception as e:
                    print(f"[ERROR] Error procesando evento {idx}: {e}")
                    import traceback
                    traceback.print_exc()
                    continue
        
            print(f"[DEBUG] SpecialsOperatorController: Procesados {len(processed)} eventos")
            return processed
            
        except Exception as e:
            print(f"[ERROR] SpecialsOperatorController.load_specials_data: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def _adjust_timestamps_in_description(self, description, offset_hours, base_date):
        """
        Ajusta timestamps dentro de una descripción.
        
        Args:
            description (str): Descripción original
            offset_hours (int): Horas de offset
            base_date (date): Fecha base del evento
            
        Returns:
            str: Descripción con timestamps ajustados
        """
        if not description or offset_hours == 0:
            return description
        
        try:
            desc_text = str(description)
            
            # Normalizar formato: [Timestamp: XX:XX:XX] → [XX:XX:XX]
            desc_text = re.sub(
                r"\[?\s*Timestamp:\s*(\d{1,2}:\d{2}:\d{2})\s*\]?",
                r"[\1]",
                desc_text,
                flags=re.IGNORECASE
            )
            desc_text = re.sub(
                r"\[?\s*Timestamp:\s*(\d{1,2}:\d{2})\s*\]?",
                r"[\1]",
                desc_text,
                flags=re.IGNORECASE
            )
            
            def adjust_timestamp(match):
                raw_time = match.group(1) if match.lastindex >= 1 else match.group(0)
                has_brackets = match.group(0).startswith('[')
                
                try:
                    # Parsear el tiempo
                    time_parts = raw_time.split(":")
                    if len(time_parts) == 3:
                        hh, mm, ss = [int(x) for x in time_parts]
                    elif len(time_parts) == 2:
                        hh, mm = [int(x) for x in time_parts]
                        ss = 0
                    elif len(time_parts) == 1:
                        hh = int(time_parts[0])
                        mm = ss = 0
                    else:
                        return match.group(0)
                    
                    # Validar rangos
                    if not (0 <= hh <= 23 and 0 <= mm <= 59 and 0 <= ss <= 59):
                        return match.group(0)
                    
                    # Crear datetime y ajustar
                    desc_dt = datetime.combine(base_date, datetime.min.time()) + timedelta(
                        hours=hh, minutes=mm, seconds=ss
                    )
                    desc_dt_adjusted = desc_dt + timedelta(hours=offset_hours)
                    
                    # Formatear resultado
                    if len(time_parts) == 3:
                        result = desc_dt_adjusted.strftime("%H:%M:%S")
                    elif len(time_parts) == 2:
                        result = desc_dt_adjusted.strftime("%H:%M")
                    else:
                        result = str(desc_dt_adjusted.hour)
                    
                    return f"[{result}]" if has_brackets else result
                    
                except Exception:
                    return match.group(0)
            
            # Aplicar ajuste a todos los timestamps
            desc_text = re.sub(
                r"\[?(\d{1,2}:\d{2}(?::\d{2})?)\]?",
                adjust_timestamp,
                desc_text
            )
            
            return desc_text
            
        except Exception as e:
            print(f"[ERROR] _adjust_timestamps_in_description: {e}")
            return description
    
    def get_active_supervisors(self):
        """
        Obtiene lista de supervisores activos.
        
        Returns:
            list: Lista de nombres de supervisores
        """
        return specials_model.get_active_supervisors()
    
    def send_to_supervisor(self, evento_ids, supervisor):
        """
        Envía eventos especiales a un supervisor (INSERT o UPDATE).
        
        Args:
            evento_ids (list): Lista de IDs de eventos a enviar
            supervisor (str): Nombre del supervisor
            
        Returns:
            tuple: (success: bool, message: str, stats: dict)
        """
        if not evento_ids:
            return False, "No hay eventos seleccionados", {}
        
        if not supervisor:
            return False, "No se seleccionó un supervisor", {}
        
        try:
            # Recargar datos para obtener información actualizada
            all_data = self.load_specials_data()
            
            # Crear diccionario de búsqueda rápida por ID
            data_by_id = {item['id']: item for item in all_data}
            
            inserted = 0
            updated = 0
            errors = []
            
            for evento_id in evento_ids:
                item = data_by_id.get(evento_id)
                if not item:
                    errors.append(f"Evento {evento_id} no encontrado")
                    continue
                
                # Extraer ID del sitio y timezone
                id_sitio = item['id_sitio']
                time_zone = item['time_zone']
                
                # ⭐ APLICAR AJUSTES DE TIMEZONE ANTES DE ENVIAR
                # Usar valores ORIGINALES (sin ajustar) y aplicar ajuste aquí
                # Ajustar FechaHora según timezone del sitio
                fecha_hora_ajustada = adjust_datetime(item['fecha_hora_original'], time_zone)
                
                # Ajustar timestamps en descripción según timezone
                descripcion_ajustada = adjust_description_timestamps(
                    item['descripcion_original'],
                    item['fecha_hora_original'],  # Base datetime (original)
                    time_zone
                )
                
                # Normalizar valores
                try:
                    cantidad_int = int(item['cantidad']) if item['cantidad'] else 0
                except:
                    cantidad_int = 0
                
                camera_str = str(item['camera']).strip() if item['camera'] else ""
                
                # Determinar si es INSERT o UPDATE
                if item['id_special']:
                    # Ya existe en specials → UPDATE
                    success, message = specials_model.update_special(
                        id_special=item['id_special'],
                        fecha_hora=fecha_hora_ajustada,  # ⭐ Con ajuste de timezone
                        id_sitio=id_sitio,
                        nombre_actividad=item['nombre_actividad'],
                        cantidad=cantidad_int,
                        camera=camera_str,
                        descripcion=descripcion_ajustada,  # ⭐ Con timestamps ajustados
                        usuario=item['usuario'],
                        time_zone=time_zone,
                        supervisor=supervisor
                    )
                    
                    if success:
                        updated += 1
                    else:
                        errors.append(f"Error actualizando evento {evento_id}: {message}")
                else:
                    # No existe en specials → INSERT
                    success, message, id_special = specials_model.insert_special(
                        evento_id=evento_id,
                        fecha_hora=fecha_hora_ajustada,  # ⭐ Con ajuste de timezone
                        id_sitio=id_sitio,
                        nombre_actividad=item['nombre_actividad'],
                        cantidad=cantidad_int,
                        camera=camera_str,
                        descripcion=descripcion_ajustada,  # ⭐ Con timestamps ajustados
                        usuario=item['usuario'],
                        time_zone=time_zone,
                        supervisor=supervisor
                    )
                    
                    if success:
                        inserted += 1
                    else:
                        errors.append(f"Error insertando evento {evento_id}: {message}")
            
            # Construir mensaje de resultado
            stats = {
                'inserted': inserted,
                'updated': updated,
                'errors': len(errors),
                'total': len(evento_ids)
            }
            
            if errors:
                error_msg = "\n".join(errors[:5])  # Mostrar máximo 5 errores
                if len(errors) > 5:
                    error_msg += f"\n... y {len(errors) - 5} errores más"
                return False, error_msg, stats
            
            success_msg = f"Enviados a {supervisor}:\n"
            success_msg += f"• {inserted} nuevos\n"
            success_msg += f"• {updated} actualizados"
            
            return True, success_msg, stats
            
        except Exception as e:
            print(f"[ERROR] send_to_supervisor: {e}")
            import traceback
            traceback.print_exc()
            return False, str(e), {}
