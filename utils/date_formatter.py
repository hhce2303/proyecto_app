"""
Utilidad para formateo de fechas en formato amigable.
Parte del patrón MVC - capa de utilidades de presentación.
"""
from datetime import datetime, date, timedelta


def format_friendly_datetime(dt, show_seconds=False, force_full=False):
    """
    Formatea datetime en formato amigable para UI.
    
    Args:
        dt (datetime): Fecha/hora a formatear
        show_seconds (bool): Si True, muestra segundos en la hora
        force_full (bool): Si True, fuerza formato completo sin importar la fecha
    
    Returns:
        str: Fecha formateada en formato amigable
        
    Ejemplos:
        - Hoy 2025-12-15 16:30:00 -> "HOY 4:30 PM"
        - Ayer 2025-12-14 09:15:00 -> "AYER 9:15 AM"
        - Esta semana 2025-12-13 14:00:00 -> "VIE 2:00 PM"
        - Más antiguo 2025-11-20 10:30:00 -> "2025-11-20 10:30"
    """
    if not dt:
        return ""
    
    # Si se fuerza formato completo, retornar inmediatamente
    if force_full:
        time_format = "%H:%M:%S" if show_seconds else "%H:%M"
        return dt.strftime(f"%Y-%m-%d {time_format}")
    
    # Obtener fecha actual
    today = date.today()
    dt_date = dt.date()
    
    # Calcular diferencia en días
    delta = (today - dt_date).days
    
    # Determinar formato de hora (12h con AM/PM)
    time_format = "%I:%M:%S %p" if show_seconds else "%I:%M %p"
    time_str = dt.strftime(time_format).lstrip('0')  # Remover cero inicial de hora
    
    # HOY
    if delta == 0:
        return f"HOY {time_str}"
    
    # AYER
    elif delta == 1:
        return f"AYER {time_str}"
    
    # ESTA SEMANA (últimos 6 días)
    elif delta <= 6:
        dias_semana = {
            0: "LUN", 1: "MAR", 2: "MIÉ", 3: "JUE", 
            4: "VIE", 5: "SÁB", 6: "DOM"
        }
        dia_nombre = dias_semana[dt.weekday()]
        return f"{dia_nombre} {time_str}"
    
    # MÁS ANTIGUO - formato completo compacto
    else:
        time_format_short = "%H:%M:%S" if show_seconds else "%H:%M"
        return dt.strftime(f"%Y-%m-%d {time_format_short}")


def format_time_only(dt, show_seconds=False):
    """
    Formatea solo la hora de un datetime.
    
    Args:
        dt (datetime): Fecha/hora a formatear
        show_seconds (bool): Si True, muestra segundos
    
    Returns:
        str: Hora formateada (ejemplo: "4:30 PM" o "16:30")
    """
    if not dt:
        return ""
    
    # Formato 12 horas con AM/PM
    time_format = "%I:%M:%S %p" if show_seconds else "%I:%M %p"
    return dt.strftime(time_format).lstrip('0')


def format_date_only(dt):
    """
    Formatea solo la fecha de un datetime.
    
    Args:
        dt (datetime): Fecha/hora a formatear
    
    Returns:
        str: Fecha formateada (ejemplo: "2025-12-15")
    """
    if not dt:
        return ""
    
    return dt.strftime("%Y-%m-%d")
