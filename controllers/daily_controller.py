from datetime import datetime

import backend_super
from models import daily_model
from models.user_model import load_users
from views.dialogs.register_cover_dialog import RegisterCoverDialog
import login
from tkinter import messagebox


class DailyController:  

    def __init__(self, username, window=None, current_tab=None):
        self.username = username
        self.window = window
        self.current_tab = current_tab
        
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
            print (f"[INFO] Evento ID {sitio_str}, actividad '{actividad}' guardado automáticamente.")
        except Exception as e:
            print(f"[ERROR] auto_save_pending_events: {e}")


    def request_cover(self, username):
        """
        Solicita un cover directamente con motivo predeterminado.
        Usa cover_model.request_covers() (model) para inserción en BD.
        """

        # ⭐ VALIDAR QUE HAY TURNO ACTIVO
        # ⭐ VALIDAR QUE HAY TURNO ACTIVO
        if not backend_super.has_active_shift(self.username):
            messagebox.showwarning(
                "Sin Turno Activo",
                "⚠️ Debes iniciar tu turno antes de solicitar covers.\n\n"
                "Haz clic en el botón '🚀 Start Shift' en la esquina superior derecha.",
                parent=self.window
            )
            return
        
        try:

            from datetime import datetime
            time_request = datetime.now()
            motivo = "Necesito un cover"  # Motivo predeterminado
            approved = 1  # Siempre aprobado
            
            # Llamar al modelo para insertar en BD
            from models import cover_model
            
            cover_id = cover_model.request_covers(
                username=self.username,
                time_request=time_request,
                reason=motivo,
                aprvoved=approved  # Nota: typo en función original
            )
            
            if cover_id:
                print(f"[DEBUG] Cover solicitado exitosamente. ID: {cover_id}")
                # Refrescar módulo de covers si está activo
                if self.current_tab == "Covers" and hasattr(self, 'covers_module'):
                    self.covers_module.load_data()
            else:
                print("[DEBUG] No se generó ID de cover (posible validación fallida)")
        
        except Exception as e:
            from tkinter import messagebox
            messagebox.showerror(
                "Error",
                f"No se pudo solicitar el cover:\n{e}",
                parent=self.window
            )
            print(f"[ERROR] _request_cover: {e}")
            import traceback
            traceback.print_exc()

    def register_covers(self, username, station,  window=None, ui_factory=None, UI=None):
        """
        Registra un cover realizado y cambia de sesión al operador que cubre.
        Usa RegisterCoverDialog (view), cover_model.insertar_cover() (model),
        y login.logout_silent + login.auto_login para cambio de sesión.
        """
        from tkinter import messagebox
        # ⭐ VALIDAR QUE HAY TURNO ACTIVO
        if not backend_super.has_active_shift(self.username):
            messagebox.showwarning(
                "Sin Turno Activo",
                "⚠️ Debes iniciar tu turno antes de registrar covers.\n\n"
                "Haz clic en el botón '🚀 Start Shift' en la esquina superior derecha.",
                parent=window
            )
            return
        try:
            # Obtener lista de operadores disponibles para cubrir
            operadores = load_users()
            if not operadores:
                messagebox.showwarning(
                    "Sin operadores",
                    "No hay operadores disponibles en el sistema.",
                    parent=window
                )
                return
            # Mostrar diálogo para capturar datos
            dialog = RegisterCoverDialog(
                parent=window,
                ui_factory=ui_factory,
                UI=UI
            )
            result = dialog.show(operadores)
            if not result:
                # Usuario canceló
                print("[DEBUG] Registro de cover cancelado por usuario")
                return
            # Obtener datos del diálogo
            motivo = result['motivo']
            covered_by = result['covered_by']
            print(f"[DEBUG] Registrando cover: {self.username} cubierto por {covered_by}, motivo: {motivo}")
            # Llamar al modelo para insertar cover
            from models import cover_model
            cover_model.insertar_cover(
                username=self.username,
                Covered_by=covered_by,
                Motivo=motivo,
                session_id=self.session_id if hasattr(self, 'session_id') else None,
                station=self.station if hasattr(self, 'station') else None
            )
            # Cerrar ventana actual antes de abrir nueva sesión
            if window:
                window.destroy()
            # Auto-login del operador que cubre
            login.auto_login(
                username=covered_by,
                station=station,
                
                password="1234",
                parent=None,
                silent=True
            )
            print(f"[DEBUG] Sesión cambiada exitosamente a {covered_by}")
        except Exception as e:
            messagebox.showerror(
                "Error",
                f"No se pudo registrar el cover:\n{e}",
                parent=window
            )
            print(f"[ERROR] _register_cover: {e}")
            import traceback
            traceback.print_exc()

    def on_cell_edit(self, evento):
        """Handler cuando se edita una celda (recibe la tupla evento)"""
        try:
            self.auto_save_pending_event(evento)
        except Exception as e:
            print(f"[DEBUG] on_cell_edit error: {e}")