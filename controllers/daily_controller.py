

from datetime import datetime

from models import daily_model


class DailyController:  

    def __init__(self, username):
        self.username = username
        
    def load_daily(self):
        """Carga datos diarios desde el último START SHIFT (MODO DAILY)"""
        try:
            eventos = daily_model.load_daily(self.username)
            return eventos
        except Exception as e:
            print(f"[ERROR] load_daily: {e}")
            return []
        
    def obtain_site_name(self, cur, id_sitio):
        try:           
            site_name = daily_model.obtain_site_name(cur, id_sitio)
            return site_name
        except Exception as e:
            print(f"[ERROR] obtain_site_name: {e}")
            return None
    
    def get_sites(self):
        """Obtiene lista de sitios desde el modelo"""
        return daily_model.get_sites()
    
    def get_activities(self):
        """Obtiene lista de actividades desde el modelo"""
        return daily_model.get_activities()
    
    def create_event(self, site_id, activity, quantity, camera, description, fecha_hora=None):
        """Crea un nuevo evento usando el modelo"""
        return daily_model.create_event(
            self.username,
            site_id,
            activity,
            quantity,
            camera,
            description,
            fecha_hora
        )
    
    
    def datetime_parser(self, fecha_str):
        """Parsea una cadena de fecha y hora en un objeto datetime.
        Soporta formatos estándar, 'AYER', 'HOY' y abreviaturas de días en español (LUN, MAR, MIÉ, JUE, VIE, SÁB, DOM)."""
        from datetime import datetime, timedelta
        import re
        fecha_hora = None
        if fecha_str:
            # 1. Intentar formatos estándar
            formatos_posibles = [
                "%Y-%m-%d %H:%M:%S",
                "%Y-%m-%d %H:%M",
            ]
            for formato in formatos_posibles:
                try:
                    fecha_hora = datetime.strptime(fecha_str, formato)
                    return fecha_hora
                except Exception:
                    continue

            # 2. AYER/HOY HH:MM AM/PM
            hoy = datetime.now()
            fecha_str_strip = fecha_str.strip().upper()
            match = re.match(r"^(AYER|HOY)\s+(\d{1,2}:\d{2}(?:\s*[AP]M)?)$", fecha_str_strip)
            if match:
                dia, hora = match.groups()
                hora = hora.replace(" ", "")
                if dia == "AYER":
                    base_date = hoy - timedelta(days=1)
                else:
                    base_date = hoy
                hora_formatos = ["%I:%M%p", "%H:%M"]
                hora_dt = None
                for hfmt in hora_formatos:
                    try:
                        hora_dt = datetime.strptime(hora, hfmt)
                        break
                    except Exception:
                        continue
                if hora_dt:
                    fecha_hora = base_date.replace(hour=hora_dt.hour, minute=hora_dt.minute, second=0, microsecond=0)
                    return fecha_hora

            # 3. DÍA_ABREV HH:MM AM/PM (ej: DOM 11:07 AM)
            dias_esp = ["LUN", "MAR", "MIÉ", "MIE", "JUE", "VIE", "SÁB", "SAB", "DOM"]
            # Regex: DÍA_ABREV HH:MM AM/PM
            match = re.match(r"^([A-ZÁÉÍÓÚÜ]{3})\s+(\d{1,2}:\d{2}(?:\s*[AP]M)?)$", fecha_str_strip)
            if match:
                dia_abrev, hora = match.groups()
                dia_abrev = dia_abrev.replace("Á", "A").replace("É", "E").replace("Í", "I").replace("Ó", "O").replace("Ú", "U").replace("Ü", "U")
                dias_esp_norm = [d.replace("Á", "A").replace("É", "E").replace("Í", "I").replace("Ó", "O").replace("Ú", "U").replace("Ü", "U") for d in dias_esp]
                if dia_abrev in dias_esp_norm:
                    idx_dia = dias_esp_norm.index(dia_abrev)
                    hoy_idx = hoy.weekday()  # lunes=0, domingo=6
                    # Mapear idx_dia a weekday (lunes=0, ..., domingo=6)
                    # dias_esp_norm: [LUN, MAR, MIE, JUE, VIE, SAB, DOM]
                    # weekday: lunes=0 ... domingo=6
                    # DOM debe ser 6
                    if idx_dia == 6:
                        dia_objetivo = 6
                    else:
                        dia_objetivo = idx_dia
                    # Calcular días de diferencia
                    dias_diff = (hoy.weekday() - dia_objetivo) % 7
                    base_date = hoy - timedelta(days=dias_diff)
                    hora = hora.replace(" ", "")
                    hora_formatos = ["%I:%M%p", "%H:%M"]
                    hora_dt = None
                    for hfmt in hora_formatos:
                        try:
                            hora_dt = datetime.strptime(hora, hfmt)
                            break
                        except Exception:
                            continue
                    if hora_dt:
                        fecha_hora = base_date.replace(hour=hora_dt.hour, minute=hora_dt.minute, second=0, microsecond=0)
                        return fecha_hora

            # 4. Fallback: devolver como string si no se puede parsear
            fecha_hora = fecha_str
        return fecha_hora


    def auto_save_pending_event(self, evento):
        """Guarda automáticamente los cambios pendientes para un solo evento (tupla)"""
        try:
            # Desempaquetar la tupla recibida
            (
                event_id,
                fecha_str,
                sitio_str,
                actividad,
                cantidad,
                camera,
                descripcion
            ) = evento

            fecha_hora = self.datetime_parser(fecha_str)

            # Extraer ID_Sitio de formato "ID - Nombre"
            id_sitio = None
            if sitio_str:
                try:
                    id_sitio = int(sitio_str.split(' - ')[0].strip())
                except Exception:
                    id_sitio = None

            # Llamar al modelo para guardar el evento
            daily_model.auto_save_pending_events_bd(
                username=self.username,
                fecha_hora=fecha_hora,
                id_sitio=id_sitio,
                actividad=actividad,
                cantidad=cantidad,
                camera=camera,
                descripcion=descripcion,
                event_id=event_id
            )
        except Exception as e:
            print(f"[ERROR] auto_save_pending_events: {e}")