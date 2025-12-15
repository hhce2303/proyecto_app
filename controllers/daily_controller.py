

from models import daily_model


class DailyController:  

    def __init__(self, username):
        self.username = username
        
    def load_daily(self, session_id):
        """Carga datos diarios desde el último START SHIFT (MODO DAILY)"""
        try:
            eventos = daily_model.load_daily(self.username, session_id)
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
    
    def create_event(self, site_id, activity, quantity, camera, description):
        """Crea un nuevo evento usando el modelo"""
        return daily_model.create_event(
            self.username,
            site_id,
            activity,
            quantity,
            camera,
            description
        )