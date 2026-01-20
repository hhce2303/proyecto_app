from time import time
from urllib.parse import urlencode
from urllib.request import Request, urlopen
import requests
import json
import urllib3
import pymysql
import gzip
import os
from datetime import datetime, timedelta
from models.database import get_connection

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
_CACHE_TTL = 300  # 5 minutos
row_size = None

# Configuración de rutas
NETWORK_PATH = r"\\192.168.7.12\Data SIG\Central Station SLC-COLOMBIA\1. Daily Logs - Operators\Forbidden access\HealthCheck json"
NORMALIZED_FILENAME = "healthcheck_normalized.json.gz"
RAW_FILENAME = "healthcheck_tickets.json"

def cargar_json_(row_size):
    """
    Retorna el JSON crudo de la API con múltiples tickets activos usando paginación.
    La API tiene un límite de 100 tickets por petición, así que hace múltiples llamadas.
    """
    from urllib.error import HTTPError
    from urllib.parse import urlencode
    from urllib.request import urlopen, Request

    url_base = "https://sigdomain01:8080/api/v3/requests"
    headers = {
        "authtoken": "FE76F794-9884-4C06-85CC-A641E2B20726",
        "Accept": "application/json",
        "Content-Type": "application/x-www-form-urlencoded"
    }
    
    all_requests = []
    start_index = 1
    page_size = 100  # Límite máximo de la API
    
    # Calcular cuántas peticiones necesitamos
    total_pages = (row_size + page_size - 1) // page_size
    
    print(f"[DEBUG] Obteniendo {row_size} tickets en {total_pages} páginas de {page_size}")
    
    for page in range(total_pages):
        current_start = start_index + (page * page_size)
        remaining = min(page_size, row_size - len(all_requests))
        
        if remaining <= 0:
            break
            
        input_data = f'{{"list_info":{{"row_count":"{remaining}","start_index":"{current_start}","sort_field":"created_time","sort_order":"desc"}}}}'
        url = url_base + "?" + urlencode({"input_data": input_data})
        
        print(f"[DEBUG] Página {page + 1}/{total_pages}: start_index={current_start}, row_count={remaining}")
        
        httprequest = Request(url, headers=headers)
        try:
            with urlopen(httprequest) as response:
                raw_data = response.read().decode()
                data = json.loads(raw_data)
                
                if isinstance(data, dict) and "requests" in data:
                    page_requests = data.get("requests", [])
                    all_requests.extend(page_requests)
                    print(f"[DEBUG] Página {page + 1}: {len(page_requests)} tickets obtenidos, total acumulado: {len(all_requests)}")
                    
                    # Si la página devolvió menos de lo esperado, no hay más datos
                    if len(page_requests) < remaining:
                        print(f"[INFO] Última página alcanzada (solo {len(page_requests)} tickets)")
                        break
                else:
                    print(f"[WARNING] Formato inesperado en página {page + 1}")
                    break
                    
        except HTTPError as e:
            error_msg = e.read().decode()
            print(f"[ERROR] HTTPError en página {page + 1}: {error_msg}")
            break
        except Exception as e:
            print(f"[ERROR] Error en página {page + 1}: {e}")
            import traceback
            traceback.print_exc()
            break
    
    # Construir el JSON final con todos los requests
    final_json = {"requests": all_requests}
    result = json.dumps(final_json)
    print(f"[INFO] Total de tickets obtenidos: {len(all_requests)}")
    return result

def get_ticket_details(request_id):

    url = f"https://sigdomain01:8080/api/v3/requests{request_id}"
    headers = {
        "authtoken": "FE76F794-9884-4C06-85CC-A641E2B20726",
        "Accept": "application/json",
        "Content-Type": "application/x-www-form-urlencoded"
    }
    httprequest = Request(url, headers=headers)
    try:
        with urlopen(httprequest) as response:
            raw = response.read().decode()
            print(raw)  # Debug opcional
            return json.loads(raw)
    except Exception as e:
        print(e)
        return None

def get_tickets():
    """Obtiene la lista de tickets desde la base de datos con información de sitio"""
    try:
        conn = get_connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        cursor.execute("""
            SELECT t.ID_ticket, t.ID_sitio, t.ID_supervisor, s.Nombre_sitio
            FROM tickets t
            LEFT JOIN sitios s ON t.ID_sitio = s.ID_sitio;
        """)
        tickets = cursor.fetchall()
        cursor.close()
        conn.close()
        return tickets
    except Exception as e:
        print(f"[ERROR] get_tickets: {e}")
        return []

def get_sites():
    """Obtiene la lista de sitios con sus grupos desde la base de datos
    
    LEGACY: Esta función se mantiene para compatibilidad.
    Para HealthCheck sidebar, usar get_sites_with_healthcheck()
    """
    try:
        conn = get_connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        cursor.execute("""SELECT Nombre_sitio, ID_Grupo, total_cameras, cameras_down FROM sitios ORDER BY ID_Grupo, Nombre_sitio;""")
        sites = cursor.fetchall()
        cursor.close()
        conn.close()
        return sites
    except Exception as e:
        print(f"[ERROR] get_sites: {e}")
        return []

def get_sites_with_healthcheck():
    """Obtiene sitios con información completa de Healthcheck desde sites_hc
    
    Returns:
        Lista de dicts con estructura:
        {
            'id_site': int,
            'Nombre_sitio': str,
            'ID_Grupo': str,
            'total_cameras': int or None,
            'inactive_cameras': int or None,
            'notes': str or None,
            'estado_check': int or None,
            'id_admin': int or None,
            'timestamp_check': datetime or None,
            'admin_name': str or None
        }
    """
    try:
        conn = get_connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        
        sql = """
            SELECT 
                s.ID_Sitio as id_site,
                s.Nombre_sitio,
                s.ID_Grupo,
                hc.cameras_totales as total_cameras,
                hc.cameras_down as inactive_cameras,
                hc.notes,
                hc.estado_check,
                hc.ID_admin as id_admin,
                hc.timestamp_check,
                u.Nombre_Usuario as admin_name
            FROM sitios s
            LEFT JOIN sites_hc hc ON s.ID_Sitio = hc.ID_sitio
            LEFT JOIN user u ON hc.ID_admin = u.ID_Usuario
            ORDER BY s.ID_Grupo, s.Nombre_sitio
        """
        
        cursor.execute(sql)
        sites = cursor.fetchall()
        cursor.close()
        conn.close()
        
        print(f"[INFO] get_sites_with_healthcheck: {len(sites)} sitios cargados con datos de HC")
        return sites
        
    except Exception as e:
        print(f"[ERROR] get_sites_with_healthcheck: {e}")
        import traceback
        traceback.print_exc()
        return []

def get_site_id(site_name):
    """Obtiene el ID de un sitio por su nombre"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""SELECT ID_sitio FROM sitios WHERE Nombre_sitio = %s;""", (site_name,))
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        return result[0] if result else None
    except Exception as e:
        print(f"[ERROR] get_site_id: {e}")
        return None

def get_supervisor_id(username):
    """Obtiene el ID de un supervisor por su nombre de usuario"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""SELECT ID_usuario FROM user WHERE Nombre_usuario = %s;""", (username,))
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        return result[0] if result else None
    except Exception as e:
        print(f"[ERROR] get_supervisor_id: {e}")
        return None

def insert_ticket(ticket_id, site_id, supervisor_id):
    """Inserta un ticket en la base de datos"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO tickets (ID_ticket, ID_sitio, ID_supervisor)
            VALUES (%s, %s, %s)
            ON DUPLICATE KEY UPDATE ID_sitio = %s, ID_supervisor = %s;
        """, (ticket_id, site_id, supervisor_id, site_id, supervisor_id))
        conn.commit()
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        print(f"[ERROR] insert_ticket: {e}")
        return False

def delete_ticket(ticket_id):
    """Elimina un ticket de la base de datos"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM tickets WHERE ID_ticket = %s", (ticket_id,))
        conn.commit()
        affected_rows = cursor.rowcount
        cursor.close()
        conn.close()
        
        if affected_rows > 0:
            print(f"[INFO] Ticket {ticket_id} eliminado de BD")
            return True
        else:
            print(f"[WARN] Ticket {ticket_id} no encontrado en BD")
            return False
    except Exception as e:
        print(f"[ERROR] delete_ticket: {e}")
        return False
def update_camera_counts(site_name, total_cameras, cameras_down):
    """Actualiza los contadores de cámaras para un sitio
    
    LEGACY: Esta función actualiza en tabla 'sitios' (viejo modelo)
    Para HealthCheck sidebar, usar update_healthcheck_cameras()
    
    Args:
        site_name: Nombre del sitio a actualizar
        total_cameras: Total de cámaras del sitio
        cameras_down: Cantidad de cámaras inactivas
    
    Returns:
        bool indicando éxito
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """UPDATE sitios 
               SET total_cameras = %s, cameras_down = %s 
               WHERE Nombre_sitio = %s""",
            (total_cameras, cameras_down, site_name)
        )
        conn.commit()
        affected_rows = cursor.rowcount
        cursor.close()
        conn.close()
        
        if affected_rows > 0:
            print(f"[INFO] Cámaras actualizadas para {site_name}: total={total_cameras}, down={cameras_down}")
            return True
        else:
            print(f"[WARNING] No se encontró el sitio {site_name} para actualizar")
            return False
    except Exception as e:
        print(f"[ERROR] update_camera_counts: {e}")
        return False

# ═══════════════════════════════════════════════════════════════
# HEALTHCHECK SIDEBAR - FUNCIONES NUEVAS
# ═══════════════════════════════════════════════════════════════

def get_site_id_by_name(site_name):
    """Convierte nombre de sitio → ID_Sitio
    
    Args:
        site_name: Nombre del sitio
    
    Returns:
        int (ID_Sitio) o None si no existe
    """
    try:
        site_name_clean = site_name.strip()
        
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT ID_Sitio FROM sitios WHERE Nombre_sitio = %s", (site_name_clean,))
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if result:
            return result[0]
        else:
            print(f"[WARNING] get_site_id_by_name: Sitio no encontrado '{site_name_clean}'")
            return None
            
    except Exception as e:
        print(f"[ERROR] get_site_id_by_name: {e}")
        return None

def get_user_id_by_name(username):
    """Convierte nombre de usuario → ID_Usuario
    
    Args:
        username: Nombre del usuario
    
    Returns:
        int (ID_Usuario) o None si no existe
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT ID_Usuario FROM user WHERE Nombre_Usuario = %s", (username,))
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if result:
            return result[0]
        else:
            print(f"[WARNING] get_user_id_by_name: Usuario no encontrado '{username}'")
            return None
            
    except Exception as e:
        print(f"[ERROR] get_user_id_by_name: {e}")
        return None

def ensure_healthcheck_record(id_site):
    """Asegura que existe un registro en sites_hc para el sitio dado
    
    Si no existe, lo crea con valores default.
    Esta función es llamada antes de cualquier UPDATE en sites_hc.
    
    Args:
        id_site: ID del sitio en tabla 'sitios'
    
    Returns:
        bool indicando si se creó o ya existía
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Verificar si existe
        cursor.execute("SELECT 1 FROM sites_hc WHERE ID_sitio = %s", (id_site,))
        exists = cursor.fetchone()
        
        if not exists:
            # Crear registro con defaults
            cursor.execute(
                """INSERT INTO sites_hc (ID_sitio, cameras_totales, cameras_down, notes, estado_check)
                   VALUES (%s, '0', '0', '', 0)""",
                (id_site,)
            )
            conn.commit()
            print(f"[INFO] Registro creado en sites_hc para id_site={id_site}")
            created = True
        else:
            created = False
        
        cursor.close()
        conn.close()
        return created
        
    except Exception as e:
        print(f"[ERROR] ensure_healthcheck_record: {e}")
        return False

def update_healthcheck_cameras(site_name, total_cameras, inactive_cameras):
    """Actualiza contadores de cámaras en sites_hc (nuevo modelo)
    
    Args:
        site_name: Nombre del sitio
        total_cameras: Total de cámaras
        inactive_cameras: Cámaras inactivas
    
    Returns:
        bool indicando éxito
    """
    try:
        # Convertir nombre → ID
        id_site = get_site_id_by_name(site_name)
        if id_site is None:
            print(f"[ERROR] update_healthcheck_cameras: Sitio no encontrado '{site_name}'")
            return False
        
        # Asegurar que existe registro en sites_hc
        ensure_healthcheck_record(id_site)
        
        # Actualizar
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """UPDATE sites_hc 
               SET cameras_totales = %s, cameras_down = %s 
               WHERE ID_sitio = %s""",
            (total_cameras, inactive_cameras, id_site)
        )
        conn.commit()
        affected_rows = cursor.rowcount
        cursor.close()
        conn.close()
        
        if affected_rows > 0:
            print(f"[INFO] HC: Cámaras actualizadas para {site_name}: total={total_cameras}, inactive={inactive_cameras}")
            return True
        else:
            print(f"[WARNING] HC: No se actualizó ningún registro para {site_name}")
            return False
            
    except Exception as e:
        print(f"[ERROR] update_healthcheck_cameras: {e}")
        import traceback
        traceback.print_exc()
        return False

def update_healthcheck_check(site_name, estado_check, id_admin, timestamp_check):
    """Actualiza estado de revisión y firma en sites_hc
    
    Args:
        site_name: Nombre del sitio
        estado_check: 1 (revisado) o 0 (no revisado)
        id_admin: ID del admin que firma (o None)
        timestamp_check: Fecha/hora de firma (o None)
    
    Returns:
        bool indicando éxito
    """
    try:
        id_site = get_site_id_by_name(site_name)
        if id_site is None:
            return False
        
        ensure_healthcheck_record(id_site)
        
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """UPDATE sites_hc 
               SET estado_check = %s, ID_admin = %s, timestamp_check = %s 
               WHERE ID_sitio = %s""",
            (estado_check, id_admin, timestamp_check, id_site)
        )
        conn.commit()
        affected_rows = cursor.rowcount
        cursor.close()
        conn.close()
        
        if affected_rows > 0:
            action = "marcado" if estado_check else "desmarcado"
            print(f"[INFO] HC: Check {action} para {site_name} por admin_id={id_admin}")
            return True
        else:
            return False
            
    except Exception as e:
        print(f"[ERROR] update_healthcheck_check: {e}")
        return False

def update_healthcheck_notes(site_name, notes):
    """Actualiza notas en sites_hc
    
    Args:
        site_name: Nombre del sitio
        notes: Texto de las notas
    
    Returns:
        bool indicando éxito
    """
    try:
        id_site = get_site_id_by_name(site_name)
        if id_site is None:
            print(f"[ERROR] update_healthcheck_notes: Sitio '{site_name}' no encontrado")
            return False
        
        # Asegurar que existe el registro
        ensure_healthcheck_record(id_site)
        
        # Nueva conexión para el UPDATE (evitar problemas de transacción)
        conn = get_connection()
        cursor = conn.cursor()
        
        # Usar INSERT...ON DUPLICATE KEY UPDATE para mayor robustez
        cursor.execute(
            """INSERT INTO sites_hc (ID_sitio, cameras_totales, cameras_down, notes, estado_check)
               VALUES (%s, '0', '0', %s, 0)
               ON DUPLICATE KEY UPDATE notes = %s""",
            (id_site, notes, notes)
        )
        conn.commit()
        affected_rows = cursor.rowcount
        cursor.close()
        conn.close()
        
        # affected_rows puede ser 1 (insert) o 2 (update), ambos son éxito
        if affected_rows > 0:
            print(f"[INFO] HC: Notas actualizadas para {site_name} ({len(notes)} chars)")
            return True
        else:
            print("[WARNING] update_healthcheck_notes: No se afectaron filas para {site_name}")
            return False
            
    except Exception as e:
        print(f"[ERROR] update_healthcheck_notes: {e}")
        import traceback
        traceback.print_exc()
        return False
def normalize_tickets(raw_json_string, supervisores_lista=None, days_filter=30):
    """Normaliza el JSON crudo de la API a formato optimizado
    
    Args:
        raw_json_string: JSON crudo de la API como string
        supervisores_lista: Lista de supervisores para filtrar (None = todos)
        days_filter: Filtrar tickets de últimos N días (None = todos)
    
    Returns:
        Lista de tickets normalizados
    """
    try:
        data = json.loads(raw_json_string)
        tickets = []
        
        if not isinstance(data, dict) or "requests" not in data:
            print("[ERROR] Formato de JSON inválido")
            return []
        
        requests_data = data.get("requests", [])
        cutoff_date = None
        
        if days_filter:
            cutoff_date = datetime.now() - timedelta(days=days_filter)
        
        print(f"[DEBUG] Normalizando {len(requests_data)} tickets...")
        
        for req in requests_data:
            try:
                # Extraer campos con defaults seguros
                status_obj = req.get("status") or {}
                requester_obj = req.get("requester") or {}
                created_time_obj = req.get("created_time") or {}
                site_obj = req.get("site") or {}
                technician_obj = req.get("technician") or {}
                priority_obj = req.get("priority") or {}
                
                requester_name = requester_obj.get("name", "Sin solicitante")
                created_display = created_time_obj.get("display_value", "N/A")
                
                # Filtro de supervisores
                if supervisores_lista and requester_name not in supervisores_lista:
                    continue
                
                # Filtro de fecha
                if cutoff_date and created_time_obj.get("value"):
                    try:
                        ticket_timestamp = int(created_time_obj["value"]) / 1000
                        ticket_date = datetime.fromtimestamp(ticket_timestamp)
                        if ticket_date < cutoff_date:
                            continue
                    except:
                        pass
                
                # Normalizar ticket
                ticket = {
                    "id": req.get("id", "N/A"),
                    "subject": req.get("subject", "Sin asunto"),
                    "status": status_obj.get("name", "Unknown"),
                    "requester": requester_name,
                    "created_time": created_display,
                    "site": site_obj.get("name", "Sin sitio"),
                    "technician": technician_obj.get("name", "Sin técnico"),
                    "priority": priority_obj.get("name", "Sin prioridad")
                }
                tickets.append(ticket)
                
            except Exception as e:
                print(f"[WARNING] Error normalizando ticket: {e}")
                continue
        
        print(f"[INFO] {len(tickets)} tickets normalizados de {len(requests_data)} totales")
        return tickets
        
    except Exception as e:
        print(f"[ERROR] normalize_tickets: {e}")
        import traceback
        traceback.print_exc()
        return []

def save_normalized_json(tickets, use_compression=True):
    """Guarda tickets normalizados con metadata y compresión
    
    IMPORTANTE: Hace merge con tickets existentes para preservar tickets
    agregados manualmente por supervisores.
    
    Args:
        tickets: Lista de tickets normalizados desde la API
        use_compression: Si True, usa gzip para comprimir
    
    Returns:
        Path completo del archivo guardado
    """
    try:
        os.makedirs(NETWORK_PATH, exist_ok=True)
        
        # 1. Intentar cargar JSON existente para preservar tickets manuales
        existing_data = load_normalized_json()
        existing_tickets = []
        manual_tickets = []
        
        if existing_data:
            existing_tickets = existing_data.get("tickets", [])
            # Filtrar tickets que fueron agregados manualmente (tienen metadata especial)
            manual_tickets = [
                t for t in existing_tickets 
                if t.get("_source") == "manual_fetch"
            ]
            print(f"[INFO] {len(manual_tickets)} tickets manuales encontrados en JSON existente")
        
        # 2. Crear diccionario de nuevos tickets por ID
        new_tickets_dict = {str(t["id"]): t for t in tickets}
        
        # 3. Agregar tickets manuales que NO estén en la nueva lista de la API
        for manual_ticket in manual_tickets:
            ticket_id = str(manual_ticket["id"])
            if ticket_id not in new_tickets_dict:
                # Preservar ticket manual
                new_tickets_dict[ticket_id] = manual_ticket
                print(f"[PRESERVE] Ticket manual {ticket_id} preservado")
            else:
                # Ticket existe en API, actualizar pero mantener flag manual
                new_tickets_dict[ticket_id]["_previously_manual"] = True
                print(f"[UPDATE] Ticket {ticket_id} actualizado desde API (era manual)")
        
        # 4. Convertir de vuelta a lista
        merged_tickets = list(new_tickets_dict.values())
        
        # 5. Construir estructura con metadata
        output = {
            "metadata": {
                "generated_at": datetime.now().isoformat(),
                "total_tickets": len(merged_tickets),
                "api_tickets": len(tickets),
                "manual_tickets": len(manual_tickets),
                "version": "2.0",
                "compression": use_compression,
                "filters_applied": ["supervisores_only", "last_30_days"],
                "merge_strategy": "preserve_manual_tickets"
            },
            "tickets": merged_tickets
        }
        
        filename = NORMALIZED_FILENAME if use_compression else NORMALIZED_FILENAME.replace(".gz", "")
        file_path = os.path.join(NETWORK_PATH, filename)
        
        if use_compression:
            with gzip.open(file_path, "wt", encoding="utf-8") as f:
                json.dump(output, f, indent=2, ensure_ascii=False)
        else:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(output, f, indent=2, ensure_ascii=False)
        
        file_size = os.path.getsize(file_path)
        print(f"[INFO] JSON normalizado guardado con merge: {file_path} ({file_size / 1024:.2f} KB)")
        print(f"[INFO] Total: {len(merged_tickets)} tickets (API: {len(tickets)}, Preservados: {len(manual_tickets)})")
        return file_path
        
    except Exception as e:
        print(f"[ERROR] save_normalized_json: {e}")
        import traceback
        traceback.print_exc()
        return None

def load_normalized_json():
    """Carga tickets normalizados con validación de metadata
    
    Returns:
        dict con 'metadata' y 'tickets', o None si hay error
    """
    try:
        file_path = os.path.join(NETWORK_PATH, NORMALIZED_FILENAME)
        
        if not os.path.exists(file_path):
            print(f"[WARNING] Archivo normalizado no encontrado: {file_path}")
            return None
        
        with gzip.open(file_path, "rt", encoding="utf-8") as f:
            data = json.load(f)
        
        # Validar estructura
        if not isinstance(data, dict) or "metadata" not in data or "tickets" not in data:
            print("[ERROR] Formato de JSON normalizado inválido")
            return None
        
        metadata = data["metadata"]
        tickets = data["tickets"]
        
        # Validar versión
        if metadata.get("version") != "2.0":
            print(f"[WARNING] Versión de JSON obsoleta: {metadata.get('version')}")
        
        # Mostrar info de cache
        generated_at = metadata.get("generated_at", "Unknown")
        print(f"[INFO] JSON normalizado cargado: {len(tickets)} tickets, generado: {generated_at}")
        
        return data
        
    except Exception as e:
        print(f"[ERROR] load_normalized_json: {e}")
        import traceback
        traceback.print_exc()
        return None

def get_and_normalize_single_ticket(ticket_id):
    """Obtiene un ticket individual de la API y lo normaliza
    
    Args:
        ticket_id: ID del ticket a buscar
    
    Returns:
        dict con ticket normalizado o None si hay error
    """
    try:
        print(f"[API] Buscando ticket {ticket_id} en API...")
        
        # Obtener detalles del ticket
        ticket_data = get_ticket_details(f"/{ticket_id}")
        
        if not ticket_data:
            print(f"[WARNING] Ticket {ticket_id} no encontrado en API")
            return None
        
        # Extraer el request del wrapper si existe
        if isinstance(ticket_data, dict) and "request" in ticket_data:
            req = ticket_data["request"]
        else:
            req = ticket_data
        
        # Normalizar con misma lógica que normalize_tickets
        status_obj = req.get("status") or {}
        requester_obj = req.get("requester") or {}
        created_time_obj = req.get("created_time") or {}
        site_obj = req.get("site") or {}
        technician_obj = req.get("technician") or {}
        priority_obj = req.get("priority") or {}
        
        normalized_ticket = {
            "id": req.get("id", ticket_id),
            "subject": req.get("subject", "Sin asunto"),
            "status": status_obj.get("name", "Unknown"),
            "requester": requester_obj.get("name", "Sin solicitante"),
            "created_time": created_time_obj.get("display_value", "N/A"),
            "site": site_obj.get("name", "Sin sitio"),
            "technician": technician_obj.get("name", "Sin técnico"),
            "priority": priority_obj.get("name", "Sin prioridad")
        }
        
        print(f"[API] Ticket {ticket_id} obtenido y normalizado exitosamente")
        return normalized_ticket
        
    except Exception as e:
        print(f"[ERROR] get_and_normalize_single_ticket: {e}")
        import traceback
        traceback.print_exc()
        return None

def append_ticket_to_normalized_json(new_ticket):
    """Agrega un ticket al JSON normalizado existente
    
    Marca el ticket como agregado manualmente para que no se borre
    en futuras sincronizaciones del Admin.
    
    Args:
        new_ticket: dict con ticket normalizado a agregar
    
    Returns:
        bool indicando éxito
    """
    try:
        # Cargar JSON existente
        data = load_normalized_json()
        
        if not data:
            print("[WARNING] No se puede agregar ticket, JSON normalizado no existe")
            return False
        
        tickets = data.get("tickets", [])
        
        # Verificar si el ticket ya existe
        ticket_id = str(new_ticket.get("id"))
        existing_ids = [str(t.get("id")) for t in tickets]
        
        # IMPORTANTE: Marcar como agregado manualmente
        new_ticket["_source"] = "manual_fetch"
        new_ticket["_added_at"] = datetime.now().isoformat()
        
        if ticket_id in existing_ids:
            print(f"[INFO] Ticket {ticket_id} ya existe en JSON normalizado")
            # Actualizar el ticket existente y marcarlo como manual
            for i, ticket in enumerate(tickets):
                if str(ticket.get("id")) == ticket_id:
                    # Preservar metadata manual si ya existía
                    if ticket.get("_source") == "manual_fetch":
                        new_ticket["_added_at"] = ticket.get("_added_at")
                    tickets[i] = new_ticket
                    print(f"[INFO] Ticket {ticket_id} actualizado en JSON (marcado como manual)")
                    break
        else:
            # Agregar nuevo ticket
            tickets.append(new_ticket)
            print(f"[INFO] Ticket {ticket_id} agregado al JSON normalizado (marcado como manual)")
        
        # Actualizar metadata
        metadata = data.get("metadata", {})
        metadata["total_tickets"] = len(tickets)
        metadata["last_updated"] = datetime.now().isoformat()
        
        # Contar tickets manuales
        manual_count = sum(1 for t in tickets if t.get("_source") == "manual_fetch")
        metadata["manual_tickets"] = manual_count
        
        data["metadata"] = metadata
        
        # Guardar JSON actualizado
        file_path = os.path.join(NETWORK_PATH, NORMALIZED_FILENAME)
        
        with gzip.open(file_path, "wt", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        print(f"[INFO] JSON normalizado actualizado exitosamente ({manual_count} tickets manuales)")
        return True
        
    except Exception as e:
        print(f"[ERROR] append_ticket_to_normalized_json: {e}")
        import traceback
        traceback.print_exc()
        return False