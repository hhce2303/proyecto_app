from tkinter import messagebox
from utils.ui_factory import UIFactory
from models.healthcheck_model import (
    cargar_json_, get_sites, get_ticket_details, get_tickets,
    normalize_tickets, save_normalized_json, load_normalized_json,
    get_and_normalize_single_ticket, append_ticket_to_normalized_json
)
import tkinter as tk
import os
import json
import time
from datetime import datetime
UIFactory = ui_factory = UIFactory(tk)

# Lista de supervisores por defecto
SUPERVISORES_LISTA = [
    "Alexander Serna",
    "Wendy Heredia",
    "Julian Valdes",
    "Nicolas Murillo",
    "Harvin Vidal",
    "Diego Fernandez",
    "Christian Perlaza",
    "Logan Gonzalez",
    "Edwin Ortiz",
    "Nicoll Moreno",
    "Service Desk",
    "Atera"
]


# Cache global para tickets de supervisores
_CACHE_SUPERVISORES = {
    "tickets": [],
    "timestamp": None,
    "ttl": 300  # 5 minutos de caché
}

def clear_filters(module):
    """Limpia todos los filtros y recarga datos"""
    module.id_search_var.set("")
    module.site_search_var.set("")
    module.status_search_var.set("")
    module.requester_search_var.set("")
    module.current_page = 1
    module._load_data_paged()


def refresh_data(module):
    """Refresca datos limpiando el cache"""
    from models.healthcheck_model import _CACHE_SUPERVISORES
    _CACHE_SUPERVISORES["tickets"] = []
    _CACHE_SUPERVISORES["timestamp"] = None
    print("[INFO] Cache limpiado, recargando datos...")
    module.current_page = 1
    module._load_data_paged()

class HealthcheckController:

    def __init__(self, username):
        self.username = username
    

    
    def load_healthcheck_json(self, row_size):
        """Carga el JSON crudo de HealthCheck y lo guarda en un archivo para debugging"""
        print(f"[DEBUG] Cargando JSON con row_size={row_size}")
        json_data = cargar_json_(row_size)
        if json_data:
            print(f"[DEBUG] JSON cargado exitosamente: {len(json_data)} caracteres")
            saved_path = self.save_json_to_file(json_data)
            print(f"[DEBUG] JSON guardado en: {saved_path}")
            return True
        else:
            print("[ERROR] No se pudo cargar el JSON de HealthCheck desde la API")
            return False
    
    def sync_healthcheck_data_optimized(self, row_size=10000):
        """Método optimizado para ADMIN: request API -> normalizar -> guardar comprimido
        
        Este método realiza todo el proceso pesado:
        1. Hace request a la API
        2. Normaliza el JSON
        3. Filtra supervisores
        4. Filtra últimos 30 días
        5. Guarda con compresión y metadata
        
        Returns:
            dict con stats del proceso o None si falla
        """
        try:
            print(f"[ADMIN] Iniciando sincronización optimizada de {row_size} tickets...")
            start_time = time.time()
            
            # 1. Request API
            print("[STEP 1/4] Obteniendo datos de API...")
            raw_json = cargar_json_(row_size)
            if not raw_json:
                return {"success": False, "error": "No se pudo obtener datos de la API"}
            
            # 2. Normalizar con filtros
            print("[STEP 2/4] Normalizando y filtrando tickets...")
            tickets = normalize_tickets(
                raw_json,
                supervisores_lista=SUPERVISORES_LISTA,
                days_filter=180  # Últimos 180 días
            )
            
            if not tickets:
                return {"success": False, "error": "No se encontraron tickets después de filtros"}
            
            # 3. Guardar JSON normalizado comprimido
            print("[STEP 3/4] Guardando JSON normalizado...")
            file_path = save_normalized_json(tickets, use_compression=True)
            
            if not file_path:
                return {"success": False, "error": "Error guardando JSON normalizado"}
            
            # 4. Guardar también el JSON crudo para backup
            print("[STEP 4/4] Guardando JSON crudo como backup...")
            self.save_json_to_file(raw_json)
            
            elapsed = time.time() - start_time
            
            stats = {
                "success": True,
                "total_tickets": len(tickets),
                "file_path": file_path,
                "elapsed_seconds": round(elapsed, 2),
                "timestamp": datetime.now().isoformat()
            }
            
            print(f"[ADMIN] Sincronización completada en {elapsed:.2f}s: {len(tickets)} tickets")
            return stats
            
        except Exception as e:
            print(f"[ERROR] sync_healthcheck_data_optimized: {e}")
            import traceback
            traceback.print_exc()
            return {"success": False, "error": str(e)}
    

    def save_json_to_file(self, json_data, filename="healthcheck_tickets.json"):
        """Guarda el JSON crudo en un archivo local o de red para debugging"""
        import os
        print(f"[DEBUG] Intentando guardar JSON: {len(json_data)} caracteres")
        # Ruta de red destino
        dest_dir = r"\\192.168.7.12\Data SIG\Central Station SLC-COLOMBIA\1. Daily Logs - Operators\Forbidden access\HealthCheck json"
        try:
            os.makedirs(dest_dir, exist_ok=True)
            print(f"[DEBUG] Directorio verificado/creado: {dest_dir}")
        except Exception as e:
            print(f"[ERROR] No se pudo crear directorio: {e}")
        dest_path = os.path.join(dest_dir, filename)
        try:
            with open(dest_path, 'w', encoding='utf-8') as f:
                f.write(json_data)
            print(f"[INFO] JSON guardado exitosamente en: {dest_path}, cantidad de tickets: {json_data.count('\"id\":')}")
        except Exception as e:
            print(f"[ERROR] No se pudo guardar el JSON: {e}")
            import traceback
            traceback.print_exc()
        return dest_path

    def get_json_tickets(self, filename="healthcheck_tickets.json"):
        """Método optimizado para SUPERVISOR: solo lee JSON normalizado
        
        Este método ligero solo lee el JSON ya procesado por el Admin.
        No hace normalización ni filtros, solo carga y retorna.
        
        Returns:
            Lista de tickets normalizados
        """
        try:
            # Intentar cargar JSON normalizado primero
            data = load_normalized_json()
            
            if data:
                tickets = data.get("tickets", [])
                metadata = data.get("metadata", {})
                
                print(f"[SUPERVISOR] JSON normalizado cargado: {len(tickets)} tickets")
                print(f"[SUPERVISOR] Generado: {metadata.get('generated_at', 'Unknown')}")
                return tickets
            
            # Fallback: leer JSON crudo si normalizado no existe (legacy)
            print("[WARNING] JSON normalizado no disponible, usando método legacy...")
            return self._get_json_tickets_legacy(filename)
            
        except Exception as e:
            print(f"[ERROR] get_json_tickets: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def _get_json_tickets_legacy(self, filename="healthcheck_tickets.json"):
        """Método legacy: normaliza desde JSON crudo (antiguo comportamiento)"""
        dest_dir = r"\\192.168.7.12\Data SIG\Central Station SLC-COLOMBIA\1. Daily Logs - Operators\Forbidden access\HealthCheck json"
        json_path = os.path.join(dest_dir, filename)
        
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                raw_json = f.read()
            
            # Usar función de normalización del modelo
            tickets = normalize_tickets(
                raw_json,
                supervisores_lista=SUPERVISORES_LISTA,
                days_filter=None  # Sin filtro de fecha en legacy
            )
            
            print(f"[INFO] {len(tickets)} tickets desde JSON crudo (legacy)")
            # Usar función de normalización del modelo
            tickets = normalize_tickets(
                raw_json,
                supervisores_lista=SUPERVISORES_LISTA,
                days_filter=None  # Sin filtro de fecha en legacy
            )
            
            print(f"[INFO] {len(tickets)} tickets desde JSON crudo (legacy)")
            return tickets
            
        except FileNotFoundError:
            print(f"[ERROR] Archivo no encontrado: {json_path}")
            return []
        except json.JSONDecodeError as e:
            print(f"[ERROR] Error al parsear JSON: {e}")
            return []
        except Exception as e:
            print(f"[ERROR] _get_json_tickets_legacy: {e}")
            return []

    @staticmethod
    def get_tickets(self):
        """Obtiene la lista de tickets desde la base de datos MySQL"""

        tickets = get_tickets()
        return tickets

    def get_sites(self):
        """Obtiene la lista de sitios desde la base de datos MySQL"""
        sites = get_sites()
        return sites
    
    def obtener_detalles_ticket(self, ticket_id):
        """Obtiene detalles de un ticket específico"""
        data = get_ticket_details(ticket_id)
        ticket = {}
        if data and isinstance(data, dict):
            ticket = data.get("request", {})
        return ticket
    
    def get_sites(self):
        """Obtiene lista de sitios con datos de Healthcheck normalizados
        
        Usa get_sites_with_healthcheck() que trae datos de sites + sites_hc.
        Normaliza valores NULL del LEFT JOIN a defaults.
        """
        from models.healthcheck_model import get_sites_with_healthcheck
        
        try:
            sites_raw = get_sites_with_healthcheck()
            
            # Normalizar NULL values de LEFT JOIN
            sites_normalized = []
            for site in sites_raw:
                site_data = {
                    "id_site": site.get("id_site"),
                    "Nombre_sitio": site.get("Nombre_sitio", "Unknown"),
                    "ID_Grupo": site.get("ID_Grupo", "General"),
                    "total_cameras": site.get("total_cameras") or 0,
                    "inactive_cameras": site.get("inactive_cameras") or 0,
                    "notes": site.get("notes") or "",
                    "estado_check": bool(site.get("estado_check")),
                    "id_admin": site.get("id_admin"),
                    "admin_name": site.get("admin_name") or "Sin revisar",
                    "timestamp_check": site.get("timestamp_check")
                }
                sites_normalized.append(site_data)
            
            return sites_normalized
            
        except Exception as e:
            print(f"[ERROR] Controller.get_sites: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def get_tickets(self):
        """Obtiene lista de tickets desde BD"""
        from models.healthcheck_model import get_tickets
        return get_tickets()
    
    def insert_ticket(self, ticket_id, site_name):
        """Inserta un ticket en la BD con el sitio y supervisor actual"""
        from models.healthcheck_model import get_site_id, get_supervisor_id, insert_ticket
        
        # Obtener IDs
        site_id = get_site_id(site_name)
        supervisor_id = get_supervisor_id(self.username)
        
        if not site_id:
            print(f"[ERROR] No se encontró ID para sitio: {site_name}")
            return False
        
        if not supervisor_id:
            print(f"[ERROR] No se encontró ID para supervisor: {self.username}")
            return False
        
        return insert_ticket(ticket_id, site_id, supervisor_id)
    
    def delete_ticket(self, ticket_id, site_name):
        """Elimina un ticket de la BD"""
        from models.healthcheck_model import delete_ticket
        
        try:
            return delete_ticket(ticket_id)
        except Exception as e:
            print(f"[ERROR] Error eliminando ticket {ticket_id}: {e}")
            return False
    
    def update_camera_counts(self, site_name, total_cameras, cameras_down):
        """Actualiza contadores de cámaras en sites_hc con validación
        
        Args:
            site_name: Nombre del sitio
            total_cameras: Total de cámaras (debe ser entero no negativo)
            cameras_down: Cámaras inactivas (debe ser entero no negativo)
        
        Returns:
            tuple (success: bool, warning_msg: str or None)
        """
        from models.healthcheck_model import update_healthcheck_cameras
        
        try:
            # Validación básica
            total = int(total_cameras) if total_cameras else 0
            down = int(cameras_down) if cameras_down else 0
            
            if total < 0 or down < 0:
                return False, "Los valores no pueden ser negativos"
            
            # Advertencia si down > total (pero permitir guardar)
            warning = None
            if down > total:
                warning = f"⚠️ Cámaras inactivas ({down}) mayor que total ({total})\n\nSe guardará de todas formas."
            
            # Guardar en BD (ahora usa sites_hc)
            success = update_healthcheck_cameras(site_name, total, down)
            
            return success, warning
            
        except ValueError:
            return False, "Los valores deben ser números enteros"
        except Exception as e:
            print(f"[ERROR] update_camera_counts controller: {e}")
            return False, f"Error: {str(e)}"
    
    def fetch_missing_ticket(self, ticket_id):
        """Busca un ticket faltante en la API y lo agrega al JSON normalizado
        
        Este método se usa cuando un supervisor ingresa un ticket que no está
        en el JSON normalizado. Hace request a la API, normaliza el ticket,
        y lo agrega al JSON para que otros supervisores puedan verlo.
        
        Args:
            ticket_id: ID del ticket a buscar
        
        Returns:
            dict con ticket normalizado o None si no se encuentra
        """
        try:
            print(f"[CONTROLLER] Buscando ticket {ticket_id} en API...")
            
            # 1. Obtener y normalizar ticket de la API
            ticket = get_and_normalize_single_ticket(ticket_id)
            
            if not ticket:
                print(f"[WARNING] Ticket {ticket_id} no encontrado en API")
                return None
            
            # 2. Agregar al JSON normalizado
            success = append_ticket_to_normalized_json(ticket)
            
            if success:
                print(f"[SUCCESS] Ticket {ticket_id} agregado al JSON normalizado")
            else:
                print(f"[WARNING] No se pudo agregar ticket {ticket_id} al JSON")
            
            return ticket
            
        except Exception as e:
            print(f"[ERROR] fetch_missing_ticket: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    # ═══════════════════════════════════════════════════════════════════════
    # HEALTHCHECK SIDEBAR - MÉTODOS NUEVOS
    # ═══════════════════════════════════════════════════════════════════════
    
    def toggle_healthcheck_check(self, site_name, is_checked):
        """Orquesta toggle del check de revisión + firma
        
        Args:
            site_name: Nombre del sitio
            is_checked: True (marcar) o False (desmarcar)
        
        Returns:
            tuple (success: bool, error_msg: str or None)
        """
        from models.healthcheck_model import update_healthcheck_check, get_user_id_by_name
        from datetime import datetime
        
        try:
            username = self.username
            
            # TODO: Validar rol (solo Admin puede marcar check)
            # En versión futura verificar: if user_role != "Admin": return (False, "Solo Admin...")
            
            if is_checked:
                # Marcar check → guardar firma
                id_admin = get_user_id_by_name(username)
                if id_admin is None:
                    return False, f"Usuario '{username}' no encontrado en base de datos"
                
                timestamp = datetime.now()
                estado_check = 1
            else:
                # Desmarcar check → limpiar firma
                id_admin = None
                timestamp = None
                estado_check = 0
            
            success = update_healthcheck_check(site_name, estado_check, id_admin, timestamp)
            
            if success:
                action = "marcado" if is_checked else "desmarcado"
                print(f"[INFO] Check {action} para '{site_name}' por '{username}'")
                return True, None
            else:
                return False, "Error al actualizar check en base de datos"
        
        except Exception as e:
            print(f"[ERROR] toggle_healthcheck_check: {e}")
            import traceback
            traceback.print_exc()
            return False, f"Error: {str(e)}"
    
    def save_healthcheck_notes(self, site_name, notes):
        """Orquesta guardado de notas con validación
        
        Args:
            site_name: Nombre del sitio
            notes: Texto de las notas
        
        Returns:
            tuple (success: bool, error_msg: str or None)
        """
        from models.healthcheck_model import update_healthcheck_notes
        
        try:
            notes_clean = notes.strip()
            
            # Validación de longitud (opcional, suave)
            if len(notes_clean) > 1000:
                print(f"[WARNING] Notas muy largas ({len(notes_clean)} chars), truncando...")
                notes_clean = notes_clean[:1000]
            
            success = update_healthcheck_notes(site_name, notes_clean)
            
            if success:
                return True, None
            else:
                return False, "Error al guardar notas en base de datos"
        
        except Exception as e:
            print(f"[ERROR] save_healthcheck_notes: {e}")
            import traceback
            traceback.print_exc()
            return False, f"Error: {str(e)}"
