"""
Utilidad para ajustes de timezone en eventos especiales.
Parte del patrón MVC - capa de utilidades de transformación de datos.

Responsabilidades:
- Ajustar datetime según timezone del sitio
- Parsear y ajustar timestamps en descripciones
- Soportar múltiples formatos de hora (12h/24h, con/sin segundos)
"""
from datetime import datetime, timedelta
import re


def get_timezone_offset(tz_code):
    """
    Obtiene el offset en horas para un código de timezone.
    
    Args:
        tz_code (str): Código de timezone (ET, CT, MT, MST, PT)
        
    Returns:
        int: Offset en horas (negativo para zonas retrasadas)
        
    Reglas fijas:
        - ET (Eastern Time): 0
        - CT (Central Time): -1
        - MT (Mountain Time): -2
        - MST (Mountain Standard Time): -2
        - PT (Pacific Time): -3
    """
    TZ_OFFSETS = {
        "ET": 0,
        "CT": -1,
        "MT": -2,
        "MST": -2,
        "PT": -3
    }
    
    tz_upper = (tz_code or '').upper().strip()
    return TZ_OFFSETS.get(tz_upper, 0)


def adjust_datetime(dt, tz_code):
    """
    Ajusta un datetime según el timezone del sitio.
    
    Args:
        dt (datetime|str): Fecha/hora a ajustar (datetime object o string en formato ISO)
        tz_code (str): Código de timezone del sitio
        
    Returns:
        datetime: Fecha/hora ajustada
        
    Ejemplo:
        dt = datetime(2025, 12, 15, 14, 30, 0)
        tz_code = "MT"  # Mountain Time (-2 horas)
        result = adjust_datetime(dt, tz_code)
        # result = datetime(2025, 12, 15, 12, 30, 0)
    """
    if not dt:
        return dt
    
    # Convertir string a datetime si es necesario
    if isinstance(dt, str):
        try:
            # Intentar parsear formato ISO estándar
            dt = datetime.strptime(dt[:19], "%Y-%m-%d %H:%M:%S")
        except Exception as e:
            print(f"[ERROR] adjust_datetime: No se pudo parsear '{dt}': {e}")
            return dt
    
    offset_hours = get_timezone_offset(tz_code)
    return dt + timedelta(hours=offset_hours)


def adjust_description_timestamps(descripcion, base_datetime, tz_code):
    """
    Ajusta todos los timestamps en una descripción según timezone.
    
    Soporta formatos:
        - [HH:MM:SS], [HH:MM], [H:MM]  (con brackets)
        - HH:MM:SS, HH:MM, H:MM        (sin brackets)
        - 12h con AM/PM: "2:30 PM", "02:30 AM"
        - 24h: "14:30", "2:30"
        
    Args:
        descripcion (str): Texto con timestamps
        base_datetime (datetime|str): Fecha base para el ajuste (datetime object o string ISO)
        tz_code (str): Código de timezone del sitio
        
    Returns:
        str: Descripción con timestamps ajustados
        
    Ejemplos:
        desc = "Cleaner out at 02:35"
        tz_code = "MT"  # -2 horas
        result = adjust_description_timestamps(desc, datetime.now(), tz_code)
        # result = "Cleaner out at 00:35"
        
        desc = "Called at [14:30:00]"
        tz_code = "MT"  # -2 horas  
        result = adjust_description_timestamps(desc, datetime.now(), tz_code)
        # result = "Called at [12:30:00]"
    """
    if not descripcion:
        return descripcion
    
    try:
        desc_text = str(descripcion)
        offset_hours = get_timezone_offset(tz_code)
        
        # Si offset es 0, no hay nada que ajustar
        if offset_hours == 0:
            return desc_text
        
        # Normalizar formatos legacy de "Timestamp:"
        desc_text = re.sub(r"\[?\s*Timestamp:\s*(\d{1,2}:\d{2}:\d{2})\s*\]?", r"[\1]", desc_text, flags=re.IGNORECASE)
        desc_text = re.sub(r"\[?\s*Timestamp:\s*(\d{1,2}:\d{2})\s*\]?", r"[\1]", desc_text, flags=re.IGNORECASE)
        
        def adjust_timestamp(match):
            """Ajusta un timestamp individual"""
            raw_time = match.group(1) if match.lastindex >= 1 else match.group(0)
            has_brackets = match.group(0).startswith('[')
            
            try:
                # Usar fecha base o fecha actual
                if base_datetime:
                    # Convertir string a datetime si es necesario
                    if isinstance(base_datetime, str):
                        try:
                            base_dt = datetime.strptime(base_datetime[:19], "%Y-%m-%d %H:%M:%S")
                            base_date = base_dt.date()
                        except:
                            base_date = datetime.now().date()
                    elif isinstance(base_datetime, datetime):
                        base_date = base_datetime.date()
                    else:
                        base_date = datetime.now().date()
                else:
                    base_date = datetime.now().date()
                
                # Parsear componentes de tiempo
                time_parts = raw_time.split(":")
                if len(time_parts) == 3:
                    # HH:MM:SS
                    hh, mm, ss = [int(x) for x in time_parts]
                elif len(time_parts) == 2:
                    # HH:MM o H:MM
                    hh, mm = [int(x) for x in time_parts]
                    ss = 0
                else:
                    return match.group(0)
                
                # Validar rangos
                if not (0 <= hh <= 23 and 0 <= mm <= 59 and 0 <= ss <= 59):
                    return match.group(0)
                
                # Crear datetime y aplicar ajuste
                desc_dt = datetime.combine(base_date, datetime.min.time()) + timedelta(hours=hh, minutes=mm, seconds=ss)
                desc_dt_adjusted = desc_dt + timedelta(hours=offset_hours)
                
                # Formatear salida preservando formato original
                if len(time_parts) == 3:
                    # Preservar formato con segundos
                    if len(time_parts[0]) == 1:
                        # Formato H:MM:SS (sin cero a la izquierda)
                        desc_time_str = f"{desc_dt_adjusted.hour}:{desc_dt_adjusted.minute:02d}:{desc_dt_adjusted.second:02d}"
                    else:
                        # Formato HH:MM:SS (con cero)
                        desc_time_str = desc_dt_adjusted.strftime("%H:%M:%S")
                else:
                    # Preservar formato sin segundos
                    if len(time_parts[0]) == 1:
                        # Formato H:MM (sin cero a la izquierda) - EL MÁS IMPORTANTE
                        desc_time_str = f"{desc_dt_adjusted.hour}:{desc_dt_adjusted.minute:02d}"
                    else:
                        # Formato HH:MM (con cero)
                        desc_time_str = desc_dt_adjusted.strftime("%H:%M")
                
                return f"[{desc_time_str}]" if has_brackets else desc_time_str
            
            except Exception as e:
                print(f"[ERROR] adjust_timestamp: {e}")
                return match.group(0)
        
        # Aplicar ajustes a diferentes patrones
        # Orden de prioridad: brackets primero, luego sin brackets
        
        # 1. [HH:MM:SS] o [H:MM:SS]
        desc_text = re.sub(r"\[(\d{1,2}:\d{2}:\d{2})\]", adjust_timestamp, desc_text)
        
        # 2. [HH:MM] o [H:MM] - MÁS IMPORTANTE
        desc_text = re.sub(r"\[(\d{1,2}:\d{2})\]", adjust_timestamp, desc_text)
        
        # 3. HH:MM:SS o H:MM:SS sin brackets (no al final de una URL o seguido de ])
        desc_text = re.sub(r"(?<!\d)(\d{1,2}:\d{2}:\d{2})(?!\])", adjust_timestamp, desc_text)
        
        # 4. HH:MM o H:MM sin brackets (no seguido de :SS o ])
        desc_text = re.sub(r"(?<!\d)(\d{1,2}:\d{2})(?!:\d|\])", adjust_timestamp, desc_text)
        
        return desc_text
    
    except Exception as e:
        print(f"[ERROR] adjust_description_timestamps: {e}")
        import traceback
        traceback.print_exc()
        return descripcion


def parse_12h_to_24h(time_str):
    """
    Convierte formato 12h con AM/PM a 24h.
    
    Args:
        time_str (str): Hora en formato 12h (ej: "2:30 PM", "02:30 AM")
        
    Returns:
        str: Hora en formato 24h (ej: "14:30", "02:30")
        
    Ejemplos:
        "2:30 PM" -> "14:30"
        "02:35 AM" -> "02:35"
        "12:00 PM" -> "12:00" (mediodía)
        "12:00 AM" -> "00:00" (medianoche)
    """
    try:
        # Buscar patrón HH:MM AM/PM
        match = re.match(r'(\d{1,2}):(\d{2})\s*(AM|PM)', time_str.strip(), re.IGNORECASE)
        if not match:
            return time_str
        
        hh = int(match.group(1))
        mm = int(match.group(2))
        period = match.group(3).upper()
        
        # Convertir a 24h
        if period == "AM":
            if hh == 12:
                hh = 0  # 12 AM = 00:00
        else:  # PM
            if hh != 12:
                hh += 12  # 1 PM = 13:00, etc.
        
        return f"{hh:02d}:{mm:02d}"
    
    except Exception:
        return time_str
