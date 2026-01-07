"""
Admin Model - Operaciones de base de datos para administración de tablas
Implementa todas las consultas SQL para CRUD de cualquier tabla
"""
from models.database import get_connection
import traceback
ALERT_THRESHOLDS = {
    'session_long_hours': 12,      # Sesiones >12 horas
    'cover_pending_minutes': 30,   # Covers sin aprobar >30 min
    'event_open_hours': 8,         # Eventos abiertos >8 horas
    'break_unassigned_minutes': 15 # Breaks sin cubrir >15 min
}

def get_table_list():
    """
    Retorna lista de tablas disponibles para admin
    
    Returns:
        list: Nombres de tablas disponibles
    """
    return [
        "Sitios", "user", "Actividades", "gestion_breaks_programados",
        "Covers_realizados", "Covers_programados", "sesion", 
        "Estaciones", "Specials", "eventos"
    ]


def get_table_structure(table_name):
    """
    Obtiene la estructura de columnas de una tabla
    
    Args:
        table_name: Nombre de la tabla
    
    Returns:
        tuple: (col_names, col_names_original, pk_name)
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Para tablas con JOIN especial, manejar por separado
        if table_name == "eventos":
            # Columnas originales
            cursor.execute(f"SELECT * FROM `{table_name}` LIMIT 0")
            col_names_original = [desc[0] for desc in cursor.description]
            
            # Columnas con JOIN (para mostrar)
            cursor.execute("""
                SELECT e.ID_Eventos, e.FechaHora, e.ID_Sitio, e.Nombre_Actividad, 
                       e.Cantidad, e.Camera, e.Descripcion, e.ID_Usuario, u.Nombre_Usuario
                FROM Eventos e
                INNER JOIN user u ON e.ID_Usuario = u.ID_Usuario
                LIMIT 0
            """)
            col_names = [desc[0] for desc in cursor.description]
            
        elif table_name == "gestion_breaks_programados":
            # Columnas originales
            cursor.execute(f"SELECT * FROM `{table_name}` LIMIT 0")
            col_names_original = [desc[0] for desc in cursor.description]
            
            # Columnas con JOIN
            cursor.execute("""
                SELECT gbp.ID_cover, 
                       uc.Nombre_Usuario as User_covering, 
                       uv.Nombre_Usuario as User_covered,
                       gbp.Fecha_hora_cover, gbp.is_Active,
                       us.Nombre_Usuario as Supervisor,
                       gbp.Fecha_creacion
                FROM gestion_breaks_programados gbp
                LEFT JOIN user uc ON gbp.User_covering = uc.ID_Usuario
                LEFT JOIN user uv ON gbp.User_covered = uv.ID_Usuario
                LEFT JOIN user us ON gbp.Supervisor = us.ID_Usuario
                LIMIT 0
            """)
            col_names = [desc[0] for desc in cursor.description]
            
        else:
            # Para otras tablas, columnas normales
            cursor.execute(f"SELECT * FROM `{table_name}` LIMIT 0")
            col_names = [desc[0] for desc in cursor.description]
            col_names_original = col_names
        
        cursor.close()
        conn.close()
        
        # Detectar PK
        pk_name = _guess_pk(col_names_original)
        
        return (col_names, col_names_original, pk_name)
        
    except Exception as e:
        print(f"[ERROR] get_table_structure: {e}")
        traceback.print_exc()
        return ([], [], None)


def load_table_data(table_name, fecha_desde=None, fecha_hasta=None, columna_fecha=None, tipo_evento=None):
    """
    Carga datos de una tabla con filtros opcionales
    
    Args:
        table_name: Nombre de la tabla
        fecha_desde: Fecha desde (opcional)
        fecha_hasta: Fecha hasta (opcional)
        columna_fecha: Columna de fecha para filtrar (opcional, "Auto" para detectar)
        tipo_evento: Filtro de tipo de evento (solo para eventos)
    
    Returns:
        tuple: (rows, col_names, col_names_original, pk_name, fecha_cols)
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Obtener estructura
        col_names, col_names_original, pk_name = get_table_structure(table_name)
        
        # Detectar columnas de fecha
        fecha_cols = [col for col in col_names if any(keyword in col.lower() for keyword in 
                     ['fecha', 'date', 'log_in', 'log_out', 'hora', 'time', 'timestamp', 
                      'created', 'updated', 'cover_in', 'cover_out'])]
        
        # Construir query según tabla
        where_clauses = []
        params = []
        
        if table_name == "eventos":
            query = """
                SELECT e.ID_Eventos, e.FechaHora, e.ID_Sitio, e.Nombre_Actividad, 
                       e.Cantidad, e.Camera, e.Descripcion, e.ID_Usuario, u.Nombre_Usuario
                FROM Eventos e
                INNER JOIN user u ON e.ID_Usuario = u.ID_Usuario
            """
            
            # Filtro de fechas
            if (fecha_desde or fecha_hasta) and fecha_cols:
                if not columna_fecha or columna_fecha == "Auto":
                    columna_fecha = fecha_cols[0]
                
                if columna_fecha in col_names:
                    if fecha_desde:
                        where_clauses.append(f"DATE(e.{columna_fecha}) >= %s")
                        params.append(fecha_desde)
                    if fecha_hasta:
                        where_clauses.append(f"DATE(e.{columna_fecha}) <= %s")
                        params.append(fecha_hasta)
            
            # Filtro de tipo de evento
            if tipo_evento and tipo_evento != "Todos":
                where_clauses.append("e.Nombre_Actividad = %s")
                params.append(tipo_evento)
            
            if where_clauses:
                query += " WHERE " + " AND ".join(where_clauses)
            
            query += " ORDER BY e.ID_Eventos DESC LIMIT 1000"
            
        elif table_name == "gestion_breaks_programados":
            query = """
                SELECT gbp.ID_cover, 
                       uc.Nombre_Usuario as User_covering, 
                       uv.Nombre_Usuario as User_covered,
                       gbp.Fecha_hora_cover, gbp.is_Active,
                       us.Nombre_Usuario as Supervisor,
                       gbp.Fecha_creacion
                FROM gestion_breaks_programados gbp
                LEFT JOIN user uc ON gbp.User_covering = uc.ID_Usuario
                LEFT JOIN user uv ON gbp.User_covered = uv.ID_Usuario
                LEFT JOIN user us ON gbp.Supervisor = us.ID_Usuario
            """
            
            # Filtro de fechas
            if (fecha_desde or fecha_hasta) and fecha_cols:
                if not columna_fecha or columna_fecha == "Auto":
                    columna_fecha = fecha_cols[0]
                
                if columna_fecha in col_names:
                    if fecha_desde:
                        where_clauses.append(f"DATE(gbp.{columna_fecha}) >= %s")
                        params.append(fecha_desde)
                    if fecha_hasta:
                        where_clauses.append(f"DATE(gbp.{columna_fecha}) <= %s")
                        params.append(fecha_hasta)
            
            if where_clauses:
                query += " WHERE " + " AND ".join(where_clauses)
            
            query += " ORDER BY gbp.ID_cover DESC LIMIT 1000"
            
        else:
            # Query normal para otras tablas
            query = f"SELECT * FROM `{table_name}`"
            
            # Filtro de fechas
            if (fecha_desde or fecha_hasta) and fecha_cols:
                if not columna_fecha or columna_fecha == "Auto":
                    columna_fecha = fecha_cols[0]
                
                if columna_fecha in col_names:
                    if fecha_desde:
                        where_clauses.append(f"DATE({columna_fecha}) >= %s")
                        params.append(fecha_desde)
                    if fecha_hasta:
                        where_clauses.append(f"DATE({columna_fecha}) <= %s")
                        params.append(fecha_hasta)
            
            if where_clauses:
                query += " WHERE " + " AND ".join(where_clauses)
            
            if col_names:
                query += f" ORDER BY {col_names[0]} DESC LIMIT 1000"
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return (rows, col_names, col_names_original, pk_name, fecha_cols)
        
    except Exception as e:
        print(f"[ERROR] load_table_data: {e}")
        traceback.print_exc()
        return ([], [], [], None, [])


def get_record_by_pk(table_name, pk_column, pk_value):
    """
    Obtiene un registro por su PK (con columnas originales, sin JOIN)
    
    Args:
        table_name: Nombre de la tabla
        pk_column: Nombre de la columna PK
        pk_value: Valor de la PK
    
    Returns:
        tuple: Row data o None
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute(f"SELECT * FROM `{table_name}` WHERE `{pk_column}` = %s", (pk_value,))
        row = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        return row
        
    except Exception as e:
        print(f"[ERROR] get_record_by_pk: {e}")
        traceback.print_exc()
        return None


def update_record(table_name, pk_column, pk_value, col_names, new_values):
    """
    Actualiza un registro en la tabla
    
    Args:
        table_name: Nombre de la tabla
        pk_column: Nombre de la columna PK
        pk_value: Valor de la PK
        col_names: Lista de nombres de columnas (sin PK)
        new_values: Dict con nuevos valores {col_name: value}
    
    Returns:
        bool: True si éxito, False si error
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Para gestion_breaks_programados, convertir nombres a IDs
        if table_name == "gestion_breaks_programados":
            for field in ["User_covering", "User_covered", "Supervisor"]:
                if field in new_values and new_values[field]:
                    username = new_values[field]
                    cursor.execute("SELECT ID_Usuario FROM user WHERE Nombre_Usuario = %s", (username,))
                    result = cursor.fetchone()
                    if result:
                        new_values[field] = result[0]
                    else:
                        cursor.close()
                        conn.close()
                        raise ValueError(f"Usuario '{username}' no encontrado")
        
        # Construir UPDATE
        set_clause = ", ".join(f"`{c}` = %s" for c in col_names if c != pk_column)
        sql = f"UPDATE `{table_name}` SET {set_clause} WHERE `{pk_column}` = %s"
        
        params = []
        for c in col_names:
            if c != pk_column:
                value = new_values.get(c)
                # Convertir vacíos a NULL para campos específicos
                if value is None or value == "":
                    null_keywords = ['id_', '_id', 'user_logged', 'fecha', 'date', 'time', 
                                   'hora', 'timestamp', '_in', '_out', 'cover_', '_at',
                                   'created', 'updated', 'modified', 'deleted', 'log_']
                    if any(keyword in c.lower() for keyword in null_keywords):
                        value = None
                params.append(value)
        params.append(pk_value)
        
        cursor.execute(sql, params)
        conn.commit()
        cursor.close()
        conn.close()
        
        return True
        
    except Exception as e:
        print(f"[ERROR] update_record: {e}")
        traceback.print_exc()
        return False


def create_record(table_name, col_names, new_values):
    """
    Crea un nuevo registro en la tabla
    
    Args:
        table_name: Nombre de la tabla
        col_names: Lista de nombres de columnas (sin IDs autoincrementales)
        new_values: Dict con valores {col_name: value}
    
    Returns:
        bool: True si éxito, False si error
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        columns = ", ".join(f"`{c}`" for c in col_names)
        placeholders = ", ".join(["%s"] * len(col_names))
        sql = f"INSERT INTO `{table_name}` ({columns}) VALUES ({placeholders})"
        
        params = []
        for c in col_names:
            value = new_values.get(c, "")
            if value == "":
                value = None
            params.append(value)
        
        cursor.execute(sql, params)
        conn.commit()
        cursor.close()
        conn.close()
        
        return True
        
    except Exception as e:
        print(f"[ERROR] create_record: {e}")
        traceback.print_exc()
        return False


def get_users_list():
    """
    Obtiene lista de usuarios para comboboxes
    
    Returns:
        tuple: (users_list, id_to_name_dict)
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT ID_Usuario, Nombre_Usuario FROM user ORDER BY Nombre_Usuario")
        rows = cursor.fetchall()
        
        users_list = []
        id_to_name = {}
        for id_user, nombre in rows:
            users_list.append(nombre)
            id_to_name[str(id_user)] = nombre
        
        cursor.close()
        conn.close()
        
        return (users_list, id_to_name)
        
    except Exception as e:
        print(f"[ERROR] get_users_list: {e}")
        traceback.print_exc()
        return ([], {})


def _guess_pk(col_names):
    """Adivina cuál es la columna PK"""
    candidates = [c for c in col_names if c.lower() in ("id", "id_") or 
                 c.lower().endswith("_id") or c.lower().startswith("id_")]
    if candidates:
        return candidates[0]
    for c in col_names:
        if 'id' in c.lower():
            return c
    return col_names[0] if col_names else None



# ==================== FUNCIONES DE DATOS ====================

def get_dashboard_metrics():
    """
    Obtiene métricas clave para el dashboard en tiempo real
    
    Returns:
        dict: {
            'sesiones_activas': int,
            'covers_pendientes': int,
            'breaks_activos': int,
            'eventos_dia': int,
            'usuarios_conectados': int,
            'covers_completados_hoy': int,
            'eventos_abiertos': int,
            'alertas_criticas': int
        }
    """
    try:
        conn = get_connection()
        cur = conn.cursor()
        
        metrics = {}
        
        # 1. Sesiones activas (Active = 1)
        cur.execute("SELECT COUNT(*) FROM sesion WHERE Active = '1'")
        metrics['sesiones_activas'] = cur.fetchone()[0]
        
        # 2. Covers pendientes de aprobación
        cur.execute("""
            SELECT COUNT(*) FROM covers_programados 
            WHERE Approved = 1 AND is_Active = 1
        """)
        metrics['covers_pendientes'] = cur.fetchone()[0]
        
        # 3. Breaks activos programados para hoy
        cur.execute("""
            SELECT COUNT(*) FROM gestion_breaks_programados 
            WHERE is_Active = 1 
            AND DATE(Fecha_hora_cover) = CURDATE()
        """)
        metrics['breaks_activos'] = cur.fetchone()[0]
        
        # 4. Eventos registrados hoy
        cur.execute("""
            SELECT COUNT(*) FROM Eventos 
            WHERE DATE(FechaHora) = CURDATE()
        """)
        metrics['eventos_dia'] = cur.fetchone()[0]
        
        # 5. Usuarios únicos conectados
        cur.execute("""
            SELECT COUNT(DISTINCT ID_user) FROM sesion 
            WHERE Active = '1'
        """)
        metrics['usuarios_conectados'] = cur.fetchone()[0]
        
        # 6. Covers completados hoy
        cur.execute("""
            SELECT COUNT(*) FROM covers_realizados 
            WHERE DATE(Cover_in) = CURDATE()
        """)
        metrics['covers_completados_hoy'] = cur.fetchone()[0]
        
        # 7. Usuario operadores con lista de covers
        cur.execute("""
            SELECT COUNT(*) FROM sesion
            WHERE Active = 1 AND Statuses = 2
        """)

        metrics['usuarios_lista'] = cur.fetchone()[0]

        # 8. Cantidad de Specials

        cur.execute("""
            SELECT COUNT(*) FROM specials
            WHERE date(FechaHora) = CURDATE()
        """)
        metrics['specials_dia'] = cur.fetchone()[0]

        cur.close()
        conn.close()
        
        print(f"[DEBUG] Dashboard metrics: {metrics}")
        return metrics
        
    except Exception as e:
        print(f"[ERROR] get_dashboard_metrics: {e}")
        traceback.print_exc()
        return {
            'sesiones_activas': 0,
            'covers_pendientes': 0,
            'breaks_activos': 0,
            'eventos_dia': 0,
            'usuarios_conectados': 0,
            'covers_completados_hoy': 0,
            'usuarios_lista': 0,
            'specials_dia': 0
        }


def get_active_sessions_detailed():
    """
    Obtiene detalles de todas las sesiones activas
    
    Returns:
        list: [{
            'usuario': str,
            'estacion': str,
            'hora_inicio': datetime,
            'tiempo_activo': str (HH:MM),
            'estado': str,
            'rol': str,
            'session_id': int
        }]
    """
    try:
        conn = get_connection()
        cur = conn.cursor()
        
        query = """
            SELECT 
                s.ID_user AS usuario,
                s.ID_estacion AS estacion,
                s.Log_in AS hora_inicio,
                TIMESTAMPDIFF(MINUTE, s.Log_in, NOW()) AS minutos_activo,
                s.Statuses AS estado,
                u.Rol AS rol,
                s.ID AS session_id
            FROM sesion s
            LEFT JOIN user u ON s.ID_user = u.Nombre_Usuario
            WHERE s.Active = '1'
            ORDER BY s.Log_in DESC
        """
        
        cur.execute(query)
        rows = cur.fetchall()
        
        sessions = []
        for row in rows:
            minutos = row[3] or 0
            horas = minutos // 60
            mins = minutos % 60
            
            sessions.append({
                'usuario': row[0],
                'estacion': row[1] or 'N/A',
                'hora_inicio': row[2],
                'tiempo_activo': f"{horas:02d}:{mins:02d}",
                'estado': row[4] or 'Desconocido',
                'rol': row[5] or 'N/A',
                'session_id': row[6]
            })
        
        cur.close()
        conn.close()
        
        print(f"[DEBUG] Active sessions: {len(sessions)} usuarios")
        return sessions
        
    except Exception as e:
        print(f"[ERROR] get_active_sessions_detailed: {e}")
        traceback.print_exc()
        return []


def get_pending_alerts():
    """
    Obtiene lista de alertas críticas pendientes
    
    Returns:
        list: [{
            'tipo': str,
            'mensaje': str,
            'usuario': str,
            'timestamp': datetime,
            'prioridad': str ('alta', 'media', 'baja')
        }]
    """
    try:
        conn = get_connection()
        cur = conn.cursor()
        
        alerts = []
        
        # 1. Sesiones largas (>12 horas)
        cur.execute("""
            SELECT 
                s.ID_user,
                s.Log_in,
                TIMESTAMPDIFF(HOUR, s.Log_in, NOW()) AS horas
            FROM sesion s
            WHERE s.Active = '1'
            AND TIMESTAMPDIFF(HOUR, s.Log_in, NOW()) >= %s
        """, (ALERT_THRESHOLDS['session_long_hours'],))
        
        for row in cur.fetchall():
            alerts.append({
                'tipo': 'Sesión Larga',
                'mensaje': f"Usuario {row[0]} lleva {row[2]} horas conectado",
                'usuario': row[0],
                'timestamp': row[1],
                'prioridad': 'alta'
            })
        
        # 2. Covers sin aprobar (>30 minutos)
        cur.execute("""
            SELECT 
                ID_user,
                Time_request,
                TIMESTAMPDIFF(MINUTE, Time_request, NOW()) AS minutos
            FROM covers_programados
            WHERE Approved = 0 
            AND is_Active = 1
            AND TIMESTAMPDIFF(MINUTE, Time_request, NOW()) >= %s
        """, (ALERT_THRESHOLDS['cover_pending_minutes'],))
        
        for row in cur.fetchall():
            alerts.append({
                'tipo': 'Cover Pendiente',
                'mensaje': f"Cover de {row[0]} sin aprobar hace {row[2]} minutos",
                'usuario': row[0],
                'timestamp': row[1],
                'prioridad': 'media'
            })
        
        # 3. Breaks sin asignar covered_by (>15 minutos antes de la hora)
        cur.execute("""
            SELECT 
                User_covered,
                Fecha_hora_cover,
                TIMESTAMPDIFF(MINUTE, NOW(), Fecha_hora_cover) AS minutos_hasta
            FROM gestion_breaks_programados
            WHERE is_Active = 1
            AND User_covering IS NULL
            AND Fecha_hora_cover > NOW()
            AND TIMESTAMPDIFF(MINUTE, NOW(), Fecha_hora_cover) <= %s
        """, (ALERT_THRESHOLDS['break_unassigned_minutes'],))
        
        for row in cur.fetchall():
            alerts.append({
                'tipo': 'Break Sin Cubrir',
                'mensaje': f"Break de {row[0]} en {row[2]} minutos sin asignar",
                'usuario': str(row[0]),
                'timestamp': row[1],
                'prioridad': 'alta'
            })
        
        cur.close()
        conn.close()
        
        # Ordenar por prioridad y timestamp
        priority_order = {'alta': 0, 'media': 1, 'baja': 2}
        alerts.sort(key=lambda x: (priority_order[x['prioridad']], x['timestamp']), reverse=True)
        
        print(f"[DEBUG] Alerts: {len(alerts)} pendientes")
        return alerts
        
    except Exception as e:
        print(f"[ERROR] get_pending_alerts: {e}")
        traceback.print_exc()
        return []


def get_covers_graph_data(days=7):
    """
    Obtiene datos para análisis visual de covers
    
    Args:
        days: Días hacia atrás para analizar (default: 7)
    
    Returns:
        dict: {
            'covers_por_dia': [(fecha, completados, pendientes), ...],
            'covers_por_usuario': [(usuario, cantidad), ...],
            'covers_por_estado': [(estado, cantidad), ...],
            'tiempo_aprobacion': [(fecha, minutos_promedio), ...],
            'covers_por_razon': [(razon, cantidad), ...],
            'cobertura_por_usuario': [(cubierto_por, cantidad), ...]
        }
    """
    try:
        conn = get_connection()
        cur = conn.cursor()
        
        data = {}
        
        # 1. Covers por día (completados vs pendientes)
        cur.execute("""
            SELECT 
                DATE(COALESCE(cr.Cover_in, cp.Time_request)) AS fecha,
                COUNT(CASE WHEN cr.Cover_in IS NOT NULL THEN 1 END) AS completados,
                COUNT(CASE WHEN cr.Cover_in IS NULL AND cp.Approved = 1 THEN 1 END) AS pendientes
            FROM covers_programados cp
            LEFT JOIN covers_realizados cr ON cp.ID_Cover = cr.ID_programacion_covers
            WHERE DATE(COALESCE(cr.Cover_in, cp.Time_request)) >= CURDATE() - INTERVAL %s DAY
            GROUP BY fecha
            ORDER BY fecha
        """, (days,))
        data['covers_por_dia'] = cur.fetchall()
        
        # 2. Covers por usuario (top 10 solicitantes)
        cur.execute("""
            SELECT 
                cp.ID_user AS usuario,
                COUNT(*) AS cantidad
            FROM covers_programados cp
            WHERE cp.Time_request >= NOW() - INTERVAL %s DAY
            GROUP BY cp.ID_user
            ORDER BY cantidad DESC
            LIMIT 10
        """, (days,))
        data['covers_por_usuario'] = cur.fetchall()
        
        # 3. Distribución por estado
        cur.execute("""
            SELECT 
                CASE 
                    WHEN cr.Cover_in IS NOT NULL THEN 'Completado'
                    WHEN cp.Approved = 1 THEN 'Aprobado - Pendiente'
                    WHEN cp.Approved = 0 THEN 'Pendiente Aprobación'
                    ELSE 'Desconocido'
                END AS estado,
                COUNT(*) AS cantidad
            FROM covers_programados cp
            LEFT JOIN covers_realizados cr ON cp.ID_Cover = cr.ID_programacion_covers
            WHERE cp.Time_request >= NOW() - INTERVAL %s DAY
            GROUP BY estado
            ORDER BY cantidad DESC
        """, (days,))
        data['covers_por_estado'] = cur.fetchall()
        
        # 4. Tiempo promedio de aprobación (minutos) por día
        cur.execute("""
            SELECT 
                DATE(cp.Time_request) AS fecha,
                AVG(TIMESTAMPDIFF(MINUTE, cp.Time_request, 
                    CASE WHEN cp.Approved = 1 THEN cr.Cover_in ELSE NULL END)) AS minutos_promedio
            FROM covers_programados cp
            LEFT JOIN covers_realizados cr ON cp.ID_Cover = cr.ID_programacion_covers
            WHERE cp.Time_request >= NOW() - INTERVAL %s DAY
            AND cp.Approved = 1
            AND cr.Cover_in IS NOT NULL
            GROUP BY fecha
            ORDER BY fecha
        """, (days,))
        data['tiempo_aprobacion'] = cur.fetchall()
        
        # 5. Covers por razón/motivo (top 10)
        cur.execute("""
            SELECT 
                COALESCE(cp.Reason, 'Sin especificar') AS razon,
                COUNT(*) AS cantidad
            FROM covers_programados cp
            WHERE cp.Time_request >= NOW() - INTERVAL %s DAY
            GROUP BY razon
            ORDER BY cantidad DESC
            LIMIT 10
        """, (days,))
        data['covers_por_razon'] = cur.fetchall()
        
        # 6. Top usuarios que cubren (Covered_by)
        cur.execute("""
            SELECT 
                cr.Covered_by AS cubierto_por,
                COUNT(*) AS cantidad
            FROM covers_realizados cr
            WHERE cr.Cover_in >= NOW() - INTERVAL %s DAY
            AND cr.Covered_by IS NOT NULL
            GROUP BY cr.Covered_by
            ORDER BY cantidad DESC
            LIMIT 10
        """, (days,))
        data['cobertura_por_usuario'] = cur.fetchall()
        
        cur.close()
        conn.close()
        
        print(f"[DEBUG] Covers graph data: {len(data)} datasets")
        return data
        
    except Exception as e:
        print(f"[ERROR] get_covers_graph_data: {e}")
        traceback.print_exc()
        return {
            'covers_por_dia': [],
            'covers_por_usuario': [],
            'covers_por_estado': [],
            'tiempo_aprobacion': [],
            'covers_por_razon': [],
            'cobertura_por_usuario': []
        }


def get_activity_graph_data(hours=24):
    """
    Obtiene datos para gráficos de actividad
    
    Args:
        hours: Horas hacia atrás para analizar (default: 24)
    
    Returns:
        dict: {
            'eventos_por_hora': [(hora, cantidad), ...],
            'covers_por_supervisor': [(supervisor, cantidad), ...],
            'distribucion_eventos': [(tipo, cantidad), ...],
            'sesiones_por_dia': [(dia, cantidad), ...]
        }
    """
    try:
        conn = get_connection()
        cur = conn.cursor()
        
        data = {}
        
        # 1. Eventos por hora (últimas 24h)
        cur.execute("""
            SELECT 
                HOUR(FechaHora) AS hora,
                COUNT(*) AS cantidad
            FROM Eventos
            WHERE FechaHora >= NOW() - INTERVAL %s HOUR
            GROUP BY HOUR(FechaHora)
            ORDER BY hora
        """, (hours,))
        data['eventos_por_hora'] = cur.fetchall()
        
        # 2. Covers aprobados por supervisor (último mes)
        cur.execute("""
            SELECT 
                u.Nombre_Usuario AS supervisor,
                COUNT(*) AS cantidad
            FROM covers_programados cp
            LEFT JOIN sesion s ON cp.ID_user = s.ID_user
            LEFT JOIN user u ON s.ID_user = u.Nombre_Usuario
            WHERE cp.Approved = 1
            AND cp.Time_request >= NOW() - INTERVAL 30 DAY
            AND u.Rol = 'Supervisor'
            GROUP BY u.Nombre_Usuario
            ORDER BY cantidad DESC
            LIMIT 10
        """)
        data['covers_por_supervisor'] = cur.fetchall()
        
        # 3. Distribución de eventos por actividad (hoy)
        cur.execute("""
            SELECT 
                Nombre_Actividad,
                COUNT(*) AS cantidad
            FROM Eventos
            WHERE DATE(FechaHora) = CURDATE()
            GROUP BY Nombre_Actividad
            ORDER BY cantidad DESC
            LIMIT 10
        """)
        data['distribucion_eventos'] = cur.fetchall()
        
        # 4. Sesiones por día (última semana)
        cur.execute("""
            SELECT 
                DATE(Log_in) AS dia,
                COUNT(DISTINCT ID_user) AS cantidad
            FROM sesion
            WHERE Log_in >= NOW() - INTERVAL 7 DAY
            GROUP BY DATE(Log_in)
            ORDER BY dia
        """)
        data['sesiones_por_dia'] = cur.fetchall()
        
        cur.close()
        conn.close()
        
        return data
        
    except Exception as e:
        print(f"[ERROR] get_activity_graph_data: {e}")
        traceback.print_exc()
        return {
            'eventos_por_hora': [],
            'covers_por_supervisor': [],
            'distribucion_eventos': [],
            'sesiones_por_dia': []
        }


def force_logout_user(usuarios):
    """
    Fuerza el logout de un usuario terminando sus sesiones activas
    
    Args:
        username: Nombre de usuario
    
    Returns:
        bool: True si éxito, False si error
    """
    try:
        conn = get_connection()
        cur = conn.cursor()
        
        cur.executemany("""
            UPDATE sesion 
            SET Active = '0', 
                Log_Out = NOW()
            WHERE ID_user = %s 
            AND Active = '1'
        """, [(u,) for u in usuarios])
        
        conn.commit()
        cur.close()
        conn.close()
        
        return True
        
    except Exception as e:
        print(f"[ERROR] force_logout_user: {e}")
        traceback.print_exc()
        return False
