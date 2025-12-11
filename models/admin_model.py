"""
Admin Model - Operaciones de base de datos para administración de tablas
Implementa todas las consultas SQL para CRUD de cualquier tabla
"""
from models.database import get_connection
import traceback


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
