
from time import time
from urllib.request import Request, urlopen
import requests
import json
import urllib3


urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
_CACHE_TTL = 300  # 5 minutos


# Lista de supervisores por defecto
SUPERVISORES_LISTA = [
    "Alexander Serna",
    "Wendy Heredia",
    "Julian Valdez",
    "Nicolas Murillo",
    "Harvin Vidal",
    "Diego Fernandez",
    "Christian Perlaza",
    "Logan Gonzales",
    "Edwin Ortiz",
    "Nicoll Moreno"
]


# Cache global para tickets de supervisores
_CACHE_SUPERVISORES = {
    "tickets": [],
    "timestamp": None,
    "ttl": 300  # 5 minutos de caché
}


def _cargar_por_requesters_multiples(requester_list, row_size=50, max_total=None, use_cache=True):
    """
    Hace múltiples requests (uno por requester) y combina los resultados.
    Usa caché para evitar consultas repetidas al cambiar de página.
    
    Args:
        requester_list: Lista de nombres de requesters
        row_size: Tickets máximos por supervisor (default: 50)
        max_total: Límite total de tickets a retornar (None = sin límite)
        use_cache: Si True, usa caché para paginación (default: True)
    """
    import time
    
    # Revisar si hay cache válido
    if use_cache and _CACHE_SUPERVISORES["tickets"]:
        cache_age = time.time() - (_CACHE_SUPERVISORES["timestamp"] or 0)
        if cache_age < _CACHE_SUPERVISORES["ttl"]:
            print(f"[DEBUG] Usando cache de supervisores ({len(_CACHE_SUPERVISORES['tickets'])} tickets, {int(cache_age)}s de antigüedad)")
            return {"requests": _CACHE_SUPERVISORES["tickets"]}
    
    url = "https://sigdomain01:8080/api/v3/requests"
    headers = {
        "authtoken": "FE76F794-9884-4C06-85CC-A641E2B20726",
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    
    all_tickets = []
    ticket_ids_seen = set()  # Para evitar duplicados

    for requester in requester_list:
        input_record = {
            "list_info": {
                "start_index": 1,
                "row_count": row_size,
                "sort_field": "created_time",
                "sort_order": "desc",
                "fields_required": ["id", "subject", "site", "status", "created_time", "requester", "technician"],
                "search_fields": {
                    "requester.name": requester
                }
            }
        }
        
        input_text = json.dumps(input_record)
        params = {"input_data": input_text}
        
        try:
            response = requests.get(url, headers=headers, params=params, verify=False, timeout=10)
            response.raise_for_status()
            data = response.json()
            tickets = data.get("requests", [])
            
            # Agregar solo tickets únicos
            for ticket in tickets:
                ticket_id = ticket.get('id')
                if ticket_id not in ticket_ids_seen:
                    ticket_ids_seen.add(ticket_id)
                    all_tickets.append(ticket)
        
        except requests.RequestException as e:
            print(f"[ERROR] Fallo al consultar {requester}: {e}")
            continue
    
    # Ordenar por sitio (alfabético) y luego por created_time descendente
    def sort_key(ticket):
        site_data = ticket.get('site') or {}
        site_name = site_data.get('name', 'ZZZ') if isinstance(site_data, dict) else 'ZZZ'
        
        created_data = ticket.get('created_time') or {}
        created_value = created_data.get('value', 0) if isinstance(created_data, dict) else 0
        
        # Convertir a número si es posible, sino usar 0
        try:
            created_num = int(created_value) if created_value else 0
        except (ValueError, TypeError):
            created_num = 0
        return (site_name, -created_num)  # Sitio ASC, fecha DESC
    
    all_tickets.sort(key=sort_key)
    
    # Guardar en cache si se usa cache
    if use_cache:
        _CACHE_SUPERVISORES["tickets"] = all_tickets
        _CACHE_SUPERVISORES["timestamp"] = time.time()
        print(f"[DEBUG] Cache actualizado con {len(all_tickets)} tickets")
    
    return {"requests": all_tickets}



def cargar_healthcheck_activas(row_size=50, min_rows=50, start_index=1, id=None, site=None, status=None, requester=None, requester_list=None, solo_supervisores=True):
    """
    Retorna lista de tickets activos (paginados, acumulando hasta min_rows). 
    Por defecto trae SOLO tickets de supervisores (solo_supervisores=True).
    Permite filtrar por site, requester único o lista de requesters.
    """
    global _CACHE_SUPERVISORES
    now = time()
    filtros_activos = any([id, site, status, requester, requester_list])
    if solo_supervisores and not filtros_activos:
        if _CACHE_SUPERVISORES["tickets"] and (now - _CACHE_SUPERVISORES["timestamp"] < _CACHE_TTL):
            print(f"[DEBUG] Usando caché local de supervisores ({len(_CACHE_SUPERVISORES['tickets'])} tickets)")
            # Aquí haces la paginación local
            return {"requests": _CACHE_SUPERVISORES["tickets"]}
        
        else:
            print(f"[DEBUG] Caché local de supervisores inválida o inexistente")
            if solo_supervisores and not any([id, site, status, requester, requester_list]):
                print(f"[DEBUG] Filtrando por supervisores predeterminados ({len(SUPERVISORES_LISTA)} usuarios)")
                # Traer todos los tickets y paginar localmente
                result = _cargar_por_requesters_multiples(SUPERVISORES_LISTA, row_size=100, use_cache=True)
                all_tickets = result.get("requests", [])
                
                # Aplicar paginación local
                start_idx = start_index - 1  # Convertir a índice base-0
                end_idx = start_idx + min_rows
                paginated_tickets = all_tickets[start_idx:end_idx]
                
                print(f"[DEBUG] Paginación local: {len(paginated_tickets)} tickets (índice {start_index} a {end_idx})")
                return {"requests": paginated_tickets}
    # Si no es solo supervisores o hay filtros adicionales, hacer request normal
    else:
        print(f"[DEBUG] Cargando tickets con filtros adicionales o sin solo_supervisores")
        
    
    url = "https://sigdomain01:8080/api/v3/requests"
    headers = {
        "authtoken": "FE76F794-9884-4C06-85CC-A641E2B20726",
        "Accept": "application/json",
        "Content-Type": "application/json"
    }

    all_requests = []
    start = start_index
    acc = 0
    has_more = True

    while has_more and acc < min_rows:
        input_record = {
            "list_info": {
                "start_index": start,
                "row_count": row_size,
                "sort_field": "created_time",
                "sort_order": "desc",
                "fields_required": ["id", "subject", "site", "status", "created_time", "requester", "technician"]
            }
        }
        # Construir search_fields combinando site y requester si se proporcionan
        search_fields = {}
        if id:
            print(f"[DEBUG] Filtrando por ID: '{id}' (usando search_fields)")
            search_fields["id"] = id
        if site:
            print(f"[DEBUG] Filtrando por site: '{site}' (usando search_fields)")
            search_fields["site.name"] = site
        if status:
            print(f"[DEBUG] Filtrando por status: '{status}' (usando search_fields)")
            search_fields["status.name"] = status
        if requester:
            print(f"[DEBUG] Filtrando por requester: '{requester}' (usando search_fields)")
            search_fields["requester.name"] = requester
        
        # Filtro por lista de requesters: Método multi-query (funcional)
        if requester_list:
            print(f"[DEBUG] Filtrando por lista de {len(requester_list)} requesters usando múltiples requests")
            # Traer todos y paginar localmente
            result = _cargar_por_requesters_multiples(requester_list, row_size=100, use_cache=False)
            all_tickets = result.get("requests", [])
            
            start_idx = start_index - 1
            end_idx = start_idx + min_rows
            paginated_tickets = all_tickets[start_idx:end_idx]
            
            return {"requests": paginated_tickets}
        
        if search_fields:
            input_record["list_info"]["search_fields"] = search_fields
            
        input_text = json.dumps(input_record)
        params = {"input_data": input_text}
        try:
            response = requests.get(url, headers=headers, params=params, verify=False)
            response.raise_for_status()
            data = response.json()
            requests_block = data.get("requests", [])
            all_requests.extend(requests_block)
            block_count = len(requests_block)
            acc += block_count
            has_more = data.get("list_info", {}).get("has_more_rows", False)
            start += row_size
            if block_count == 0:
                break
        except requests.RequestException as e:
            print(f"[ERROR] No se pudo obtener los tickets: {e}")
            break

    # Devuelve en el mismo formato que antes (dict con "requests")
    return {"requests": all_requests}

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
        


