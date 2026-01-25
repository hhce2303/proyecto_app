"""
Controller para el mapa de Central Station.

Arquitectura: MVC - Solo lectura desde BD
Responsabilidad: Generar WorkspaceState para la vista SVG

Estado: Solo polling del estado actual
Eventos: Generados en transiciones detectadas
"""

import os
from datetime import datetime
from typing import Dict, List, Optional, Any
import uuid

from models.database import get_connection


# ========== CONFIGURACIÓN ==========

SVG_MAP_PATH = os.path.join(os.path.dirname(__file__), '..', 'workspace_map.svg')

# Mapeo: ID del SVG → numero_estacion en BD
# SVG corregido: IDs únicos (duplicados renombrados con sufijos _left, _center, _right)
# En la BD los id_station son '1', '2', '3', etc.
SVG_TO_DB_MAP = {
    # Columna izquierda (LEFT)
    "WS_01": "1", "WS_02": "2", "WS_03": "3",
    "WS_24_left": "24", "WS_28_left": "28",
    "WS_25_left": "25", "WS_30": "30",
    "WS_26_left": "26", "WS_16": "16",
    "WS_27_left": "27", "WS_31": "31",
    
    # Columna centro-izquierda (CENTER-LEFT)
    "WS_36": "36", "WS_35": "35", "WS_34": "34", "WS_33": "33",
    "WS_17_center": "17", "WS_20": "20",
    "WS_18_center": "18", "WS_21": "21",
    "WS_19_center": "19", "WS_22": "22",
    "WS_23_center": "23",
    
    # Columna centro-derecha (CENTER-RIGHT)
    "WS_17": "17", "WS_18": "18", "WS_19": "19", "WS_32": "32",
    "WS_10_right": "10", "WS_13": "13",
    "WS_11": "11", "WS_10_right2": "10",
    "WS_12": "12", "WS_15": "15",
    "WS_23": "23",
    
    # Columna derecha (RIGHT)
    "WS_24": "24", "WS_25": "25", "WS_26": "26", "WS_27": "27",
    "WS_1": "1", "WS_8": "8",
    "WS_2": "2", "WS_7": "7",
    "WS_3": "3", "WS_6": "6",
    "WS_4": "4", "WS_5": "5",
    "WS_9": "9"
}

# IDs del SVG solamente
WORKSTATIONS = list(SVG_TO_DB_MAP.keys())


# ========== ESTADO INTERNO ==========

# Cache del estado anterior para detectar transiciones
_previous_state: Optional[Dict[str, Dict[str, Any]]] = None


# ========== MAPEO DE STATUS ==========

def _map_status_to_label(statuses_value: Optional[int]) -> str:
    """
    Mapea el valor numérico de Statuses a estado legible.
    
    Reglas:
    - NULL o 0 = "active" (estado normal)
    - 2 = "active" (operador con covers, visualmente igual)
    - Otros = "idle" (por defecto)
    
    NOTA: No existe información de break/alert en la BD actual,
    estos estados requerirían consultas adicionales a otras tablas.
    """
    if statuses_value is None or statuses_value == 0 or statuses_value == 2:
        return "active"
    return "idle"


# ========== CONSULTA DE DATOS ==========

def _fetch_current_stations_state() -> Dict[str, Dict[str, Any]]:
    """
    Consulta el estado actual de todas las estaciones desde la BD.
    
    TABLA FUENTE: stations_map
    - Esta es la tabla puente que mapea usuario → estación
    - Campos: station_ID, station_user (ID_Usuario), is_active
    
    Retorna dict:
    {
        "WS_01": {
            "station_id": "WS_01",
            "occupied": True,
            "user": {"user_id": 123, "name": "John Doe"},
            "status": "active",
            "last_change": "2026-01-21T10:30:00"
        },
        ...
    }
    """
    conn = get_connection()
    if not conn:
        print("[ERROR] _fetch_current_stations_state: No database connection")
        return {}
    
    try:
        cursor = conn.cursor()
        
        # Query usando stations_map como fuente de verdad
        # stations_map.station_ID = id de estación (numérico: 1, 2, 3...)
        # stations_map.station_user = ID_Usuario (FK a user.ID_Usuario)
        query = """
            SELECT 
                sm.station_ID,
                sm.station_user,
                sm.is_active,
                u.Nombre_Usuario,
                s.Statuses,
                s.Log_in
            FROM stations_map sm
            LEFT JOIN user u ON sm.station_user = u.ID_Usuario
            LEFT JOIN sesion s ON u.Nombre_Usuario = s.ID_user 
                AND s.Active = 1
            WHERE sm.is_active = 1
            ORDER BY sm.station_ID
        """
        
        cursor.execute(query)
        results = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        # Construir diccionario de estado
        # Mapeo inverso: station_ID (BD) → WS_XX (SVG)
        db_to_svg = {v: k for k, v in SVG_TO_DB_MAP.items()}
        
        stations_dict = {}
        
        for row in results:
            db_station_id, user_id, is_active, username, statuses, log_in = row
            
            # Convertir station_ID numérico a string
            db_station_id_str = str(db_station_id)
            
            # Convertir ID de BD a ID de SVG
            svg_station_id = db_to_svg.get(db_station_id_str)
            
            if svg_station_id is None:
                # ID de BD no tiene mapeo en SVG, ignorar
                print(f"[WARNING] station_ID {db_station_id} no tiene mapeo en SVG")
                continue
            
            # Determinar si está ocupada
            occupied = user_id is not None and username is not None
            
            stations_dict[svg_station_id] = {
                "station_id": svg_station_id,
                "occupied": occupied,
                "user": {
                    "user_id": user_id,
                    "name": username
                } if occupied else None,
                "status": _map_status_to_label(statuses) if occupied else "idle",
                "last_change": log_in.isoformat() if log_in else datetime.now().isoformat()
            }
        
        # Agregar estaciones del SVG que no están en stations_map
        for svg_id in WORKSTATIONS:
            if svg_id not in stations_dict:
                stations_dict[svg_id] = {
                    "station_id": svg_id,
                    "occupied": False,
                    "user": None,
                    "status": "idle",
                    "last_change": datetime.now().isoformat()
                }
        
        return stations_dict
    
    except Exception as e:
        print(f"[ERROR] _fetch_current_stations_state: {e}")
        import traceback
        traceback.print_exc()
        return {}


# ========== DETECCIÓN DE EVENTOS ==========

def _detect_events(current: Dict[str, Dict], previous: Optional[Dict[str, Dict]]) -> List[Dict[str, Any]]:
    """
    Detecta transiciones entre estado anterior y actual.
    
    Eventos generados:
    - login: Usuario se loguea en estación
    - move: Usuario cambia de estación (logout implícito + login)
    - logout: Usuario sale (solo si no está en otra estación)
    - status_change: Cambio de status (active -> break, etc)
    
    Reglas:
    - Solo transiciones, no historial
    - TTL por defecto: 5000ms (5 segundos)
    - Severity por tipo de evento
    """
    if previous is None:
        # Primera ejecución, no hay eventos
        return []
    
    events = []
    
    # Mapeo de usuarios: estación actual
    current_user_locations = {
        st["user"]["name"]: st["station_id"] 
        for st in current.values() 
        if st["occupied"]
    }
    
    previous_user_locations = {
        st["user"]["name"]: st["station_id"] 
        for st in previous.values() 
        if st["occupied"]
    }
    
    # Detectar cambios por estación
    for station_id, curr_st in current.items():
        prev_st = previous.get(station_id, {})
        
        # LOGIN: Estación estaba vacía, ahora ocupada
        if not prev_st.get("occupied", False) and curr_st["occupied"]:
            username = curr_st["user"]["name"]
            
            # Verificar si es MOVE (usuario estaba en otra estación)
            if username in previous_user_locations:
                old_station = previous_user_locations[username]
                events.append({
                    "event_id": str(uuid.uuid4()),
                    "station_id": station_id,
                    "type": "move",
                    "label": f"{username} moved from {old_station}",
                    "severity": "info",
                    "ttl": 5000
                })
            else:
                # LOGIN genuino
                events.append({
                    "event_id": str(uuid.uuid4()),
                    "station_id": station_id,
                    "type": "login",
                    "label": f"{username} logged in",
                    "severity": "info",
                    "ttl": 5000
                })
        
        # LOGOUT: Estación estaba ocupada, ahora vacía
        elif prev_st.get("occupied", False) and not curr_st["occupied"]:
            username = prev_st["user"]["name"]
            
            # Solo es logout si no está en otra estación
            if username not in current_user_locations:
                events.append({
                    "event_id": str(uuid.uuid4()),
                    "station_id": station_id,
                    "type": "logout",
                    "label": f"{username} logged out",
                    "severity": "info",
                    "ttl": 5000
                })
        
        # STATUS CHANGE: Mismo usuario, diferente status
        elif (prev_st.get("occupied", False) and curr_st["occupied"] and
              prev_st["user"]["name"] == curr_st["user"]["name"] and
              prev_st["status"] != curr_st["status"]):
            
            username = curr_st["user"]["name"]
            old_status = prev_st["status"]
            new_status = curr_st["status"]
            
            # Determinar severity
            severity = "info"
            if new_status == "alert":
                severity = "critical"
            elif new_status == "break":
                severity = "warning"
            
            events.append({
                "event_id": str(uuid.uuid4()),
                "station_id": station_id,
                "type": "status_change",
                "label": f"{username}: {old_status} → {new_status}",
                "severity": severity,
                "ttl": 5000
            })
    
    return events


# ========== API PÚBLICA ==========

def get_workspace_state() -> Dict[str, Any]:
    """
    Genera el WorkspaceState completo para la vista.
    
    Retorna estructura conforme al contrato:
    {
        "timestamp": ISO_STRING,
        "stations": {...},
        "events": [...]
    }
    
    Esta función debe ser llamada periódicamente (polling).
    """
    global _previous_state
    
    current_stations = _fetch_current_stations_state()
    events = _detect_events(current_stations, _previous_state)
    
    # Actualizar cache de estado anterior
    _previous_state = current_stations.copy()
    
    workspace_state = {
        "timestamp": datetime.now().isoformat(),
        "stations": current_stations,
        "events": events
    }
    
    return workspace_state


def reset_state():
    """
    Resetea el estado interno del controller.
    Útil para testing o re-inicialización.
    """
    global _previous_state
    _previous_state = None 

