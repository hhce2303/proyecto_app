"""
🔍 DIAGNÓSTICO DE BUG: TIMEZONE OFFSET Y COMPARACIÓN DE SPECIALS
================================================================
Script para diagnosticar el problema de marcas perdidas al cambiar de estación.

PROBLEMA IDENTIFICADO:
1. Operador tiene specials marcados como enviados en estación A
2. Cambia a estación B (diferente timezone)
3. Los specials aparecen SIN MARCA (aunque ya fueron enviados)

CAUSA RAÍZ:
- La hora en Eventos está en timezone original
- load_specials() aplica offset visual según estación actual
- Al buscar en tabla specials, compara hora AJUSTADA con hora ORIGINAL
- NO encuentra coincidencia → Aparece como "sin marca"

FLUJO CORRECTO:
1. Modo Daily: Hora original sin offset
2. Modo Specials: Hora + offset (SOLO VISUAL)
3. accion_supervisores(): Inserta en specials con hora AJUSTADA
4. load_specials(): Debe buscar en specials usando hora AJUSTADA para comparar

USO:
    python test_timezone_offset_bug.py
"""

import pymysql
from datetime import datetime, timedelta
from collections import defaultdict

# ⭐ CONFIGURACIÓN
DB_CONFIG = {
    'host': '192.168.101.135',
    'user': 'app_user',
    'password': '1234',
    'database': 'daily',
    'port': 3306
}

# ⭐ Configuración de timezone (igual que en operator_window.py)
def load_tz_config():
    """Retorna configuración de timezone offsets"""
    return {
        "ET": 0,
        "CT": -1,
        "MT": -2,
        "MST": -2,
        "PT": -3
    }

def get_connection():
    """Obtiene conexión a la base de datos"""
    try:
        return pymysql.connect(**DB_CONFIG)
    except Exception as e:
        print(f"❌ Error de conexión: {e}")
        return None

def get_station_timezone(station):
    """Obtiene el timezone de una estación"""
    conn = get_connection()
    if not conn:
        return None
    
    try:
        cur = conn.cursor()
        cur.execute("SELECT Zona_horaria FROM estaciones WHERE Nombre_Estacion = %s", (station,))
        result = cur.fetchone()
        cur.close()
        conn.close()
        return result[0] if result else None
    except Exception as e:
        print(f"❌ Error al obtener timezone: {e}")
        return None

def get_user_last_shift_and_specials(username):
    """Obtiene último shift y los specials del usuario"""
    print("\n" + "="*80)
    print(f"📊 OBTENIENDO DATOS DEL USUARIO: {username}")
    print("="*80)
    
    conn = get_connection()
    if not conn:
        return None, None, None
    
    try:
        cur = conn.cursor()
        
        # 1. Obtener último START SHIFT
        cur.execute("""
            SELECT e.FechaHora, ses.Nombre_Estacion, est.Time_Zone
            FROM Eventos e
            INNER JOIN user u ON e.ID_Usuario = u.ID_Usuario
            LEFT JOIN (
                SELECT ID_user, Nombre_Estacion
                FROM sesion
                WHERE Active IN (1, 2)
                ORDER BY ID DESC
            ) ses ON u.Nombre_Usuario = ses.ID_user
            LEFT JOIN estaciones est ON ses.Nombre_Estacion = est.Nombre_Estacion
            WHERE u.Nombre_Usuario = %s 
              AND e.Nombre_Actividad = 'START SHIFT'
            ORDER BY e.FechaHora DESC
            LIMIT 1
        """, (username,))
        shift_row = cur.fetchone()
        
        if not shift_row:
            print(f"⚠️  No se encontró START SHIFT para {username}")
            cur.close()
            conn.close()
            return None, None, None
        
        last_shift_time = shift_row[0]
        current_station = shift_row[1]
        current_tz = shift_row[2]
        
        print(f"\n✅ Último START SHIFT:")
        print(f"   Fecha/Hora: {last_shift_time}")
        print(f"   Estación: {current_station}")
        print(f"   Timezone: {current_tz}")
        
        # 2. Obtener eventos de grupos especiales desde el shift
        grupos_especiales = ("AS", "KG", "HUD", "PE", "SCH", "WAG", "LT", "DT")
        
        cur.execute("""
            SELECT
                e.ID_Eventos,
                e.FechaHora,
                e.ID_Sitio,
                e.Nombre_Actividad,
                e.Cantidad,
                e.Camera,
                e.Descripcion,
                u.Nombre_Usuario,
                st.Time_Zone as sitio_tz
            FROM Eventos AS e
            INNER JOIN user u ON e.ID_Usuario = u.ID_Usuario
            LEFT JOIN Sitios st ON e.ID_Sitio = st.ID_Sitio
            WHERE u.Nombre_Usuario = %s
            AND e.ID_Sitio IN (
                SELECT s.ID_Sitio
                FROM Sitios s
                WHERE s.ID_Grupo IN (%s, %s, %s, %s, %s, %s, %s, %s)
            )
            AND e.FechaHora >= %s
            ORDER BY e.FechaHora ASC
        """, (username, *grupos_especiales, last_shift_time))
        
        eventos = cur.fetchall()
        
        print(f"\n✅ Eventos de grupos especiales: {len(eventos)}")
        
        cur.close()
        conn.close()
        
        return last_shift_time, eventos, current_tz
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return None, None, None

def test_timezone_offset_logic(username):
    """Simula la lógica de load_specials() y encuentra discrepancias"""
    print("\n" + "="*80)
    print("🧪 SIMULANDO LÓGICA DE load_specials()")
    print("="*80)
    
    # Obtener datos
    last_shift, eventos, current_tz = get_user_last_shift_and_specials(username)
    if not eventos:
        print("⚠️  No hay eventos para analizar")
        return
    
    # Cargar configuración de timezone
    tz_adjust = load_tz_config()
    offset_hours = tz_adjust.get(current_tz, 0)
    
    print(f"\n📍 Timezone actual: {current_tz} (Offset: {offset_hours} horas)")
    
    conn = get_connection()
    if not conn:
        return
    
    cur = conn.cursor()
    
    print("\n" + "="*80)
    print("🔍 ANÁLISIS DE CADA EVENTO")
    print("="*80)
    
    problemas_encontrados = []
    
    for evento in eventos:
        id_evento, fecha_hora_orig, id_sitio, actividad, cantidad, camera, descripcion, usuario, sitio_tz = evento
        
        # ⭐ PASO 1: Aplicar offset (como en load_specials)
        try:
            fecha_hora_ajustada = fecha_hora_orig + timedelta(hours=offset_hours)
            fecha_str_display = fecha_hora_ajustada.strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            fecha_str_display = str(fecha_hora_orig)
        
        print(f"\n{'─'*80}")
        print(f"📋 Evento ID: {id_evento}")
        print(f"   Actividad: {actividad}")
        print(f"   Sitio: {id_sitio} (TZ: {sitio_tz})")
        print(f"   Hora ORIGINAL: {fecha_hora_orig}")
        print(f"   Hora AJUSTADA (visual): {fecha_str_display}")
        
        # ⭐ PASO 2: Buscar en tabla specials (LÓGICA ACTUAL - POSIBLE BUG)
        # Búsqueda 1: Con hora AJUSTADA (lo que SE DEBERÍA hacer)
        cur.execute("""
            SELECT ID_special, FechaHora, marked_status, marked_by, Supervisor
            FROM specials
            WHERE Usuario = %s
              AND Nombre_Actividad = %s
              AND IFNULL(ID_Sitio, 0) = IFNULL(%s, 0)
              AND FechaHora = %s
            LIMIT 1
        """, (usuario, actividad, id_sitio, fecha_hora_ajustada))
        found_adjusted = cur.fetchone()
        
        # Búsqueda 2: Con hora ORIGINAL (lo que probablemente está pasando)
        cur.execute("""
            SELECT ID_special, FechaHora, marked_status, marked_by, Supervisor
            FROM specials
            WHERE Usuario = %s
              AND Nombre_Actividad = %s
              AND IFNULL(ID_Sitio, 0) = IFNULL(%s, 0)
              AND FechaHora = %s
            LIMIT 1
        """, (usuario, actividad, id_sitio, fecha_hora_orig))
        found_original = cur.fetchone()
        
        # Búsqueda 3: SIN FechaHora (la correcta según el fix anterior)
        cur.execute("""
            SELECT ID_special, FechaHora, marked_status, marked_by, Supervisor
            FROM specials
            WHERE Usuario = %s
              AND Nombre_Actividad = %s
              AND IFNULL(ID_Sitio, 0) = IFNULL(%s, 0)
            LIMIT 1
        """, (usuario, actividad, id_sitio))
        found_no_fecha = cur.fetchone()
        
        print(f"\n   🔍 RESULTADOS DE BÚSQUEDA:")
        print(f"   1️⃣ Con hora AJUSTADA ({fecha_str_display}):")
        if found_adjusted:
            print(f"      ✅ ENCONTRADO - ID: {found_adjusted[0]}, Status: {found_adjusted[2] or 'NULL'}")
        else:
            print(f"      ❌ NO ENCONTRADO")
        
        print(f"   2️⃣ Con hora ORIGINAL ({fecha_hora_orig}):")
        if found_original:
            print(f"      ✅ ENCONTRADO - ID: {found_original[0]}, Status: {found_original[2] or 'NULL'}")
        else:
            print(f"      ❌ NO ENCONTRADO")
        
        print(f"   3️⃣ SIN FechaHora (solo Usuario/Actividad/Sitio):")
        if found_no_fecha:
            print(f"      ✅ ENCONTRADO - ID: {found_no_fecha[0]}, Hora en DB: {found_no_fecha[1]}, Status: {found_no_fecha[2] or 'NULL'}")
        else:
            print(f"      ❌ NO ENCONTRADO")
        
        # Detectar discrepancias
        if found_no_fecha and not found_adjusted:
            problema = {
                'id_evento': id_evento,
                'actividad': actividad,
                'hora_orig': fecha_hora_orig,
                'hora_ajustada': fecha_str_display,
                'hora_en_specials': found_no_fecha[1],
                'status': found_no_fecha[2],
                'tipo': 'DISCREPANCIA_TIMEZONE'
            }
            problemas_encontrados.append(problema)
            print(f"\n   ⚠️  PROBLEMA DETECTADO:")
            print(f"      Existe en specials con hora: {found_no_fecha[1]}")
            print(f"      Pero NO coincide con hora ajustada: {fecha_str_display}")
            print(f"      Esto causa que aparezca como 'SIN MARCA' en la interfaz")
    
    cur.close()
    conn.close()
    
    # Resumen de problemas
    if problemas_encontrados:
        print("\n" + "="*80)
        print("🚨 RESUMEN DE PROBLEMAS ENCONTRADOS")
        print("="*80)
        print(f"\nTotal de eventos con discrepancia: {len(problemas_encontrados)}")
        print("\nEstos eventos existen en 'specials' pero NO se están encontrando")
        print("debido a diferencias en la hora causadas por el offset de timezone.\n")
        
        for idx, prob in enumerate(problemas_encontrados, 1):
            print(f"{idx}. ID_Evento: {prob['id_evento']} | {prob['actividad']}")
            print(f"   Hora original: {prob['hora_orig']}")
            print(f"   Hora ajustada (buscada): {prob['hora_ajustada']}")
            print(f"   Hora en specials: {prob['hora_en_specials']}")
            print(f"   Status en DB: {prob['status']}")
            print()
    else:
        print("\n✅ No se encontraron discrepancias de timezone")

def compare_stations_logic(username):
    """Compara cómo se ve el mismo evento desde diferentes estaciones"""
    print("\n" + "="*80)
    print("🌍 COMPARACIÓN: MISMO EVENTO, DIFERENTES ESTACIONES")
    print("="*80)
    
    # Obtener un evento de ejemplo
    conn = get_connection()
    if not conn:
        return
    
    cur = conn.cursor()
    
    # Obtener último evento especial del usuario
    grupos_especiales = ("AS", "KG", "HUD", "PE", "SCH", "WAG", "LT", "DT")
    
    cur.execute("""
        SELECT
            e.ID_Eventos,
            e.FechaHora,
            e.ID_Sitio,
            e.Nombre_Actividad,
            u.Nombre_Usuario,
            st.Time_Zone as sitio_tz
        FROM Eventos AS e
        INNER JOIN user u ON e.ID_Usuario = u.ID_Usuario
        LEFT JOIN Sitios st ON e.ID_Sitio = st.ID_Sitio
        WHERE u.Nombre_Usuario = %s
        AND e.ID_Sitio IN (
            SELECT s.ID_Sitio
            FROM Sitios s
            WHERE s.ID_Grupo IN (%s, %s, %s, %s, %s, %s, %s, %s)
        )
        ORDER BY e.FechaHora DESC
        LIMIT 1
    """, (username, *grupos_especiales))
    
    evento = cur.fetchone()
    
    if not evento:
        print("⚠️  No hay eventos para comparar")
        cur.close()
        conn.close()
        return
    
    id_evento, fecha_hora_orig, id_sitio, actividad, usuario, sitio_tz = evento
    
    print(f"\n📋 Evento de prueba:")
    print(f"   ID: {id_evento}")
    print(f"   Actividad: {actividad}")
    print(f"   Hora ORIGINAL en DB: {fecha_hora_orig}")
    print(f"   Sitio: {id_sitio} (TZ: {sitio_tz})")
    
    # Simular vista desde diferentes estaciones
    tz_adjust = load_tz_config()
    estaciones_ejemplo = {
        "ET": 0,
        "CT": -1,
        "PT": -3
    }
    
    print(f"\n{'='*80}")
    print("🔄 CÓMO SE VE ESTE EVENTO DESDE DIFERENTES ESTACIONES:")
    print("="*80)
    
    for tz_name, offset in estaciones_ejemplo.items():
        fecha_ajustada = fecha_hora_orig + timedelta(hours=offset)
        fecha_str = fecha_ajustada.strftime("%Y-%m-%d %H:%M:%S")
        
        print(f"\n🏢 Estación en zona {tz_name} (offset: {offset}h):")
        print(f"   Hora visualizada: {fecha_str}")
        
        # Buscar en specials con esta hora
        cur.execute("""
            SELECT ID_special, marked_status
            FROM specials
            WHERE Usuario = %s
              AND Nombre_Actividad = %s
              AND IFNULL(ID_Sitio, 0) = IFNULL(%s, 0)
              AND FechaHora = %s
        """, (usuario, actividad, id_sitio, fecha_ajustada))
        
        found = cur.fetchone()
        if found:
            print(f"   ✅ ENCONTRADO en specials (ID: {found[0]}, Status: {found[1] or 'NULL'})")
        else:
            print(f"   ❌ NO ENCONTRADO en specials")
            print(f"   💡 Aparecería como 'SIN MARCA' en esta estación")
    
    cur.close()
    conn.close()

def suggest_fix():
    """Sugiere la corrección necesaria en operator_window.py"""
    print("\n" + "="*80)
    print("🔧 SOLUCIÓN PROPUESTA")
    print("="*80)
    
    print("""
PROBLEMA RAÍZ:
En load_specials(), la búsqueda en tabla 'specials' usa FechaHora ajustada,
pero en accion_supervisores() se inserta con una hora diferente.

SOLUCIÓN:
1. En accion_supervisores(): Insertar/actualizar con hora AJUSTADA
2. En load_specials(): Buscar con hora AJUSTADA
3. Opción alternativa: NO usar FechaHora en la búsqueda (solo Usuario/Actividad/Sitio)

CAMBIO NECESARIO EN operator_window.py:

📍 Línea ~2118 (en load_specials - verificación de estado):
   
   ANTES (INCORRECTO):
   ```python
   cur.execute(\"\"\"
       SELECT ID_special, marked_status, marked_by, marked_at, Supervisor
       FROM specials
       WHERE FechaHora = %s           # ❌ Usa hora ORIGINAL
         AND Usuario = %s
         AND Nombre_Actividad = %s
         AND IFNULL(ID_Sitio, 0) = IFNULL(%s, 0)
   \"\"\", (fecha_hora, usuario_evt, nombre_actividad, id_sitio))
   ```
   
   DESPUÉS (CORRECTO):
   ```python
   cur.execute(\"\"\"
       SELECT ID_special, marked_status, marked_by, marked_at, Supervisor
       FROM specials
       WHERE FechaHora = %s           # ✅ Usa hora AJUSTADA (fecha_dt)
         AND Usuario = %s
         AND Nombre_Actividad = %s
         AND IFNULL(ID_Sitio, 0) = IFNULL(%s, 0)
   \"\"\", (fecha_dt, usuario_evt, nombre_actividad, id_sitio))  # fecha_dt ya tiene offset
   ```
   
   O MEJOR AÚN (SIN FechaHora):
   ```python
   cur.execute(\"\"\"
       SELECT ID_special, marked_status, marked_by, marked_at, Supervisor
       FROM specials
       WHERE Usuario = %s
         AND Nombre_Actividad = %s
         AND IFNULL(ID_Sitio, 0) = IFNULL(%s, 0)
   \"\"\", (usuario_evt, nombre_actividad, id_sitio))  # Sin FechaHora
   ```

VENTAJAS DE NO USAR FechaHora:
- Funciona independientemente de la estación/timezone
- Más robusto ante cambios de offset
- Previene duplicados por timezone
- Más simple y mantenible
    """)

# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    print("\n" + "═"*80)
    print("🔬 DIAGNÓSTICO: BUG DE TIMEZONE OFFSET EN SPECIALS")
    print("═"*80)
    
    # Solicitar username
    username = input("\n👤 Ingresa el username a diagnosticar (ej: hector): ").strip()
    if not username:
        print("❌ Username requerido")
        return
    
    # Test 1: Analizar lógica de timezone offset
    test_timezone_offset_logic(username)
    
    # Test 2: Comparar vistas desde diferentes estaciones
    compare_stations_logic(username)
    
    # Test 3: Sugerir solución
    suggest_fix()
    
    print("\n" + "═"*80)
    print("✅ DIAGNÓSTICO COMPLETO")
    print("═"*80)
    print()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n❌ Diagnóstico cancelado (Ctrl+C)")
    except Exception as e:
        print(f"\n\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
