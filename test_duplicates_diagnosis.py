"""
🔍 DIAGNÓSTICO DE DUPLICADOS EN TABLA SPECIALS
==============================================
Script para detectar y analizar registros duplicados que difieren solo en FechaHora y ID_special.

USO:
    python test_duplicates_diagnosis.py

FUNCIONES:
1. find_duplicates() - Encuentra duplicados ignorando FechaHora e ID_special
2. show_duplicate_groups() - Muestra grupos de duplicados agrupados
3. test_upsert_logic() - Simula la lógica de operator_window para identificar el bug
4. suggest_fix() - Sugiere registros a eliminar (conservando el más antiguo)
"""

import mysql.connector
from datetime import datetime
from collections import defaultdict

# ⭐ CONFIGURACIÓN DE CONEXIÓN (ajusta según tu config)
DB_CONFIG = {
    'host': 'localhost',
    'user': 'app_user',
    'password': '1234',  # Ajusta tu contraseña
    'database': 'daily'
}

def get_connection():
    """Obtiene conexión a la base de datos"""
    try:
        return mysql.connector.connect(**DB_CONFIG)
    except Exception as e:
        print(f"❌ Error de conexión: {e}")
        return None

def find_duplicates():
    """
    Encuentra duplicados en specials que difieren SOLO en FechaHora e ID_special
    (Usa la misma lógica que tu consulta SQL)
    """
    print("\n" + "="*80)
    print("🔍 BUSCANDO DUPLICADOS EN TABLA SPECIALS")
    print("="*80)
    
    conn = get_connection()
    if not conn:
        return
    
    cur = conn.cursor()
    
    # Query que encuentra duplicados (ignora FechaHora e ID_special)
    query = """
        SELECT 
            Usuario,
            Nombre_Actividad,
            ID_Sitio,
            Descripcion,
            COUNT(*) as cantidad_duplicados,
            GROUP_CONCAT(ID_special ORDER BY FechaHora ASC) as IDs_duplicados,
            GROUP_CONCAT(FechaHora ORDER BY FechaHora ASC) as Fechas_duplicadas,
            GROUP_CONCAT(IFNULL(marked_status, 'NULL') ORDER BY FechaHora ASC) as Status_duplicados,
            GROUP_CONCAT(IFNULL(Supervisor, 'NULL') ORDER BY FechaHora ASC) as Supervisores_duplicados
        FROM specials
        GROUP BY Usuario, Nombre_Actividad, ID_Sitio, Descripcion
        HAVING COUNT(*) > 1
        ORDER BY cantidad_duplicados DESC, Usuario
    """
    
    cur.execute(query)
    duplicates = cur.fetchall()
    
    if not duplicates:
        print("\n✅ No se encontraron duplicados.")
        cur.close()
        conn.close()
        return []
    
    print(f"\n⚠️ ENCONTRADOS {len(duplicates)} GRUPOS DE DUPLICADOS:\n")
    
    results = []
    for idx, dup in enumerate(duplicates, 1):
        usuario, actividad, sitio, descripcion, count, ids, fechas, statuses, supervisores = dup
        
        print(f"\n📋 Grupo #{idx} - {count} registros duplicados:")
        print(f"   👤 Usuario: {usuario}")
        print(f"   🎯 Actividad: {actividad}")
        print(f"   🏢 Sitio: {sitio}")
        print(f"   📝 Descripcion: {descripcion[:50] if descripcion else 'N/A'}")
        print(f"\n   🆔 IDs: {ids}")
        print(f"   📅 FechaHoras: {fechas}")
        print(f"   ✅ Status: {statuses}")
        print(f"   👔 Supervisores: {supervisores}")
        print(f"   {'─'*70}")
        
        results.append({
            'usuario': usuario,
            'actividad': actividad,
            'sitio': sitio,
            'descripcion': descripcion,
            'count': count,
            'ids': ids.split(',') if ids else [],
            'fechas': fechas.split(',') if fechas else [],
            'statuses': statuses.split(',') if statuses else [],
            'supervisores': supervisores.split(',') if supervisores else []
        })
    
    cur.close()
    conn.close()
    
    return results

def test_upsert_logic(usuario, actividad, sitio, fecha_hora_1, fecha_hora_2):
    """
    Simula la lógica de accion_supervisores() para demostrar el bug
    
    Args:
        usuario: Nombre de usuario
        actividad: Nombre de actividad
        sitio: ID de sitio
        fecha_hora_1: Primera FechaHora (será insertada)
        fecha_hora_2: Segunda FechaHora (debería actualizar pero insertará de nuevo)
    """
    print("\n" + "="*80)
    print("🧪 TEST: SIMULACIÓN DE LÓGICA UPSERT (con bug)")
    print("="*80)
    
    conn = get_connection()
    if not conn:
        return
    
    cur = conn.cursor()
    
    # TEST 1: Insertar primer registro
    print(f"\n📝 TEST 1: Insertando primer registro")
    print(f"   Usuario: {usuario}")
    print(f"   Actividad: {actividad}")
    print(f"   Sitio: {sitio}")
    print(f"   FechaHora: {fecha_hora_1}")
    
    # Buscar si existe (lógica ACTUAL con bug - incluye FechaHora)
    cur.execute("""
        SELECT ID_special
        FROM specials
        WHERE FechaHora = %s
          AND Usuario = %s
          AND Nombre_Actividad = %s
          AND IFNULL(ID_Sitio, 0) = IFNULL(%s, 0)
        LIMIT 1
    """, (fecha_hora_1, usuario, actividad, sitio))
    
    found = cur.fetchone()
    if found:
        print(f"   ✅ Registro encontrado (ID: {found[0]}) - Se actualizaría")
    else:
        print(f"   ❌ Registro NO encontrado - Se insertará")
        # Simular INSERT (sin ejecutar realmente)
        print(f"   ➡️ INSERT INTO specials (FechaHora, Usuario, Actividad, Sitio) VALUES ('{fecha_hora_1}', '{usuario}', '{actividad}', {sitio})")
    
    # TEST 2: Intentar insertar segundo registro con fecha diferente
    print(f"\n📝 TEST 2: Intentando insertar con FechaHora diferente")
    print(f"   Usuario: {usuario} (MISMO)")
    print(f"   Actividad: {actividad} (MISMO)")
    print(f"   Sitio: {sitio} (MISMO)")
    print(f"   FechaHora: {fecha_hora_2} (DIFERENTE)")
    
    # Buscar si existe (lógica ACTUAL con bug - incluye FechaHora)
    cur.execute("""
        SELECT ID_special
        FROM specials
        WHERE FechaHora = %s
          AND Usuario = %s
          AND Nombre_Actividad = %s
          AND IFNULL(ID_Sitio, 0) = IFNULL(%s, 0)
        LIMIT 1
    """, (fecha_hora_2, usuario, actividad, sitio))
    
    found = cur.fetchone()
    if found:
        print(f"   ✅ Registro encontrado (ID: {found[0]}) - Se actualizaría")
    else:
        print(f"   ❌ Registro NO encontrado - Se insertará")
        print(f"   ➡️ INSERT INTO specials (FechaHora, Usuario, Actividad, Sitio) VALUES ('{fecha_hora_2}', '{usuario}', '{actividad}', {sitio})")
        print(f"\n   ⚠️ ¡BUG DETECTADO! Se creará un DUPLICADO porque FechaHora es diferente")
    
    # TEST 3: Mostrar cómo debería ser (sin FechaHora en búsqueda)
    print(f"\n📝 TEST 3: Lógica CORRECTA (sin FechaHora en búsqueda)")
    cur.execute("""
        SELECT ID_special, FechaHora
        FROM specials
        WHERE Usuario = %s
          AND Nombre_Actividad = %s
          AND IFNULL(ID_Sitio, 0) = IFNULL(%s, 0)
        LIMIT 1
    """, (usuario, actividad, sitio))
    
    found = cur.fetchone()
    if found:
        print(f"   ✅ Registro encontrado (ID: {found[0]}, FechaHora: {found[1]})")
        print(f"   ➡️ UPDATE specials SET FechaHora='{fecha_hora_2}' WHERE ID_special={found[0]}")
        print(f"   ✅ CORRECTO: Se actualizaría en lugar de insertar")
    else:
        print(f"   ❌ Registro NO encontrado - Se insertaría")
    
    cur.close()
    conn.close()

def suggest_cleanup():
    """Sugiere qué registros eliminar para limpiar duplicados"""
    print("\n" + "="*80)
    print("🧹 SUGERENCIAS DE LIMPIEZA")
    print("="*80)
    
    conn = get_connection()
    if not conn:
        return
    
    cur = conn.cursor()
    
    # Query que muestra registros a eliminar (conservando el más antiguo)
    query = """
        SELECT s.*
        FROM specials s
        INNER JOIN (
            SELECT Usuario, Nombre_Actividad, ID_Sitio, Descripcion, MIN(ID_special) as keep_id
            FROM specials
            GROUP BY Usuario, Nombre_Actividad, ID_Sitio, Descripcion
            HAVING COUNT(*) > 1
        ) dup ON s.Usuario <=> dup.Usuario
            AND s.Nombre_Actividad <=> dup.Nombre_Actividad
            AND s.ID_Sitio <=> dup.ID_Sitio
            AND s.Descripcion <=> dup.Descripcion
            AND s.ID_special != dup.keep_id
        ORDER BY s.Usuario, s.Nombre_Actividad, s.FechaHora DESC
    """
    
    cur.execute(query)
    to_delete = cur.fetchall()
    
    if not to_delete:
        print("\n✅ No hay registros duplicados para eliminar.")
        cur.close()
        conn.close()
        return
    
    print(f"\n⚠️ Se sugiere ELIMINAR {len(to_delete)} registros duplicados:")
    print(f"   (Se conservará el registro MÁS ANTIGUO de cada grupo)\n")
    
    for idx, record in enumerate(to_delete, 1):
        id_special = record[0]
        fecha_hora = record[1]
        id_sitio = record[2]
        nombre_actividad = record[3]
        usuario = record[7]
        
        print(f"   {idx}. ID={id_special} | Usuario={usuario} | Actividad={nombre_actividad} | Sitio={id_sitio} | FechaHora={fecha_hora}")
    
    print(f"\n💡 Query para eliminar (CUIDADO - RESPALDA PRIMERO):")
    print(f"""
    DELETE s
    FROM specials s
    INNER JOIN (
        SELECT Usuario, Nombre_Actividad, ID_Sitio, Descripcion, MIN(ID_special) as keep_id
        FROM specials
        GROUP BY Usuario, Nombre_Actividad, ID_Sitio, Descripcion
        HAVING COUNT(*) > 1
    ) dup ON s.Usuario <=> dup.Usuario
        AND s.Nombre_Actividad <=> dup.Nombre_Actividad
        AND s.ID_Sitio <=> dup.ID_Sitio
        AND s.Descripcion <=> dup.Descripcion
        AND s.ID_special != dup.keep_id;
    """)
    
    cur.close()
    conn.close()

def analyze_marked_status():
    """Analiza el estado marked_status de los duplicados"""
    print("\n" + "="*80)
    print("📊 ANÁLISIS DE MARKED_STATUS EN DUPLICADOS")
    print("="*80)
    
    conn = get_connection()
    if not conn:
        return
    
    cur = conn.cursor()
    
    query = """
        SELECT 
            s.ID_special,
            s.FechaHora,
            s.Usuario,
            s.Nombre_Actividad,
            s.ID_Sitio,
            s.marked_status,
            s.marked_by,
            s.marked_at,
            s.Supervisor
        FROM specials s
        INNER JOIN (
            SELECT Usuario, Nombre_Actividad, ID_Sitio, Descripcion
            FROM specials
            GROUP BY Usuario, Nombre_Actividad, ID_Sitio, Descripcion
            HAVING COUNT(*) > 1
        ) dup ON s.Usuario <=> dup.Usuario
            AND s.Nombre_Actividad <=> dup.Nombre_Actividad
            AND s.ID_Sitio <=> dup.ID_Sitio
            AND s.Descripcion <=> dup.Descripcion
        ORDER BY s.Usuario, s.Nombre_Actividad, s.FechaHora ASC
    """
    
    cur.execute(query)
    records = cur.fetchall()
    
    if not records:
        print("\n✅ No hay duplicados para analizar.")
        cur.close()
        conn.close()
        return
    
    # Agrupar por Usuario+Actividad+Sitio
    groups = defaultdict(list)
    for record in records:
        key = (record[2], record[3], record[4])  # Usuario, Actividad, Sitio
        groups[key].append(record)
    
    print(f"\n📋 Encontrados {len(groups)} grupos de duplicados:\n")
    
    for idx, (key, records) in enumerate(groups.items(), 1):
        usuario, actividad, sitio = key
        print(f"\n{'─'*70}")
        print(f"Grupo #{idx}: Usuario={usuario} | Actividad={actividad} | Sitio={sitio}")
        print(f"{'─'*70}")
        
        for rec in records:
            id_special, fecha_hora, _, _, _, marked_status, marked_by, marked_at, supervisor = rec
            
            status_emoji = {
                None: "⚪ Sin marca",
                "": "⚪ Sin marca",
                "✅ APROBADO": "🟢 Aprobado",
                "⏳ PENDIENTE": "🟡 Pendiente",
                "❌ RECHAZADO": "🔴 Rechazado"
            }.get(marked_status, f"❓ {marked_status}")
            
            print(f"  ID={id_special:4d} | {fecha_hora} | {status_emoji:20s} | By: {marked_by or 'N/A':15s} | Sup: {supervisor or 'N/A'}")
        
        # Análisis de inconsistencias
        statuses = [r[5] for r in records]
        if len(set(statuses)) > 1:
            print(f"  ⚠️ INCONSISTENCIA: Estados diferentes en duplicados del mismo evento")
    
    cur.close()
    conn.close()

# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("\n" + "═"*80)
    print("🔬 DIAGNÓSTICO DE DUPLICADOS - TABLA SPECIALS")
    print("═"*80)
     
    # 4. Test de lógica (con datos REALES de la BD)
    print("\n" + "═"*80)
    print("💡 EJEMPLO: Simulación de bug con datos REALES")
    print("═"*80)
    test_upsert_logic(
        usuario="prueba",
        actividad="Break",
        sitio=130,
        fecha_hora_1="2025-12-12 10:00:00",
        fecha_hora_2="2025-12-12 10:05:00"
    )
    
    print("\n" + "═"*80)
    print("✅ DIAGNÓSTICO COMPLETO")
    print("═"*80)
    print("\n📝 RESUMEN DEL PROBLEMA:")
    print("   1. operator_window.py busca duplicados INCLUYENDO FechaHora en WHERE")
    print("   2. Si un evento se envía con hora diferente, NO lo encuentra")
    print("   3. Se INSERTA como nuevo en lugar de ACTUALIZAR el existente")
    print("   4. Resultado: DUPLICADOS en tabla specials")
    print("\n🔧 SOLUCIÓN:")
    print("   Remover FechaHora del WHERE en la búsqueda de duplicados")
    print("   Líneas 2740-2750 de operator_window.py")
    print("\n")
