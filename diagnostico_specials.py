# -*- coding: utf-8 -*-
"""
Script de diagnóstico para problemas de Specials
Verifica:
1. Estructura de tabla Sitios y valores de ID_Grupo
2. Configuración de timezones
3. Ajuste de fechas y descripciones
"""

import sys
import io
# Configurar salida UTF-8 para Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from models.database import get_connection
from models import specials_model
from utils.timezone_adjuster import adjust_datetime, adjust_description_timestamps, get_timezone_offset
from datetime import datetime

def diagnosticar_id_grupo():
    """Verifica estructura de ID_Grupo en tabla Sitios"""
    print("\n" + "="*80)
    print("DIAGNÓSTICO 1: ESTRUCTURA DE ID_GRUPO EN TABLA SITIOS")
    print("="*80)
    
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Obtener estructura de columna ID_Grupo
        print("\n📊 Estructura de columna ID_Grupo:")
        cursor.execute("DESCRIBE Sitios")
        columns = cursor.fetchall()
        for col in columns:
            if 'Grupo' in str(col):
                print(f"  {col}")
        
        # Obtener valores únicos de ID_Grupo
        print("\n📋 Valores únicos de ID_Grupo:")
        cursor.execute("SELECT DISTINCT ID_Grupo FROM Sitios ORDER BY ID_Grupo")
        grupos = cursor.fetchall()
        print(f"  Total de grupos únicos: {len(grupos)}")
        for grupo in grupos:
            print(f"    - {grupo[0]} (tipo: {type(grupo[0]).__name__})")
        
        # Verificar sitios de grupos especiales
        print("\n⭐ Sitios en grupos ESPECIALES (AS, KG, HUD, PE, SCH, WAG, LT, DT):")
        grupos_especiales = ("AS", "KG", "HUD", "PE", "SCH", "WAG", "LT", "DT")
        
        placeholders = ', '.join(['%s'] * len(grupos_especiales))
        query = f"""
            SELECT ID_Sitio, Nombre_Sitio, ID_Grupo, Time_Zone
            FROM Sitios
            WHERE ID_Grupo IN ({placeholders})
            ORDER BY ID_Grupo, ID_Sitio
        """
        
        cursor.execute(query, grupos_especiales)
        sitios_especiales = cursor.fetchall()
        
        if sitios_especiales:
            print(f"  ✅ Encontrados {len(sitios_especiales)} sitios especiales:")
            grupos_dict = {}
            for sitio in sitios_especiales:
                id_sitio, nombre, grupo, tz = sitio
                if grupo not in grupos_dict:
                    grupos_dict[grupo] = []
                grupos_dict[grupo].append(f"{nombre} (ID: {id_sitio}, TZ: {tz})")
            
            for grupo, sitios in sorted(grupos_dict.items()):
                print(f"\n  📍 Grupo {grupo}: {len(sitios)} sitios")
                for sitio_info in sitios[:3]:  # Mostrar solo primeros 3
                    print(f"    - {sitio_info}")
                if len(sitios) > 3:
                    print(f"    ... y {len(sitios) - 3} más")
        else:
            print("  ❌ NO se encontraron sitios especiales!")
            print("  ⚠️ PROBLEMA DETECTADO: El filtro de ID_Grupo no está funcionando")
            
            # Intentar con LIKE para ver si son categorías
            print("\n  🔍 Intentando buscar con LIKE:")
            for grupo in grupos_especiales:
                cursor.execute("""
                    SELECT COUNT(*) FROM Sitios 
                    WHERE ID_Grupo LIKE %s OR Nombre_Sitio LIKE %s
                """, (f"%{grupo}%", f"%{grupo}%"))
                count = cursor.fetchone()[0]
                if count > 0:
                    print(f"    - Grupo '{grupo}': {count} coincidencias con LIKE")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()


def diagnosticar_timezones():
    """Verifica configuración de timezones"""
    print("\n" + "="*80)
    print("DIAGNÓSTICO 2: CONFIGURACIÓN DE TIMEZONES")
    print("="*80)
    
    try:
        # 1. Configuración de timezone_adjuster.py (hardcoded)
        print("\n📝 Configuración hardcoded en timezone_adjuster.py:")
        tz_codes = ["ET", "CT", "MT", "MST", "PT"]
        for code in tz_codes:
            offset = get_timezone_offset(code)
            print(f"  {code}: {offset:+d} horas")
        
        # 2. Configuración en base de datos
        print("\n💾 Configuración en tabla time_zone_config:")
        print("  ℹ️ NOTA: Esta tabla no se usa más, ahora se usa timezone_adjuster.py")
        print("  ✅ El sistema ahora usa get_timezone_offset() de timezone_adjuster.py")
        
        # 3. Verificar timezones usados en Sitios
        print("\n🗺️ Timezones en tabla Sitios:")
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT DISTINCT Time_Zone, COUNT(*) as count
            FROM Sitios
            GROUP BY Time_Zone
            ORDER BY count DESC
        """)
        tz_sitios = cursor.fetchall()
        for tz, count in tz_sitios:
            tz_upper = (tz or '').upper()
            offset_hardcoded = get_timezone_offset(tz_upper)
            status = "✅" if offset_hardcoded != 0 or tz_upper == "ET" else "⚠️"
            print(f"  {status} {tz}: {count} sitios (Offset: {offset_hardcoded:+d}h)")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()


def diagnosticar_ajustes():
    """Verifica ajustes de fechas y descripciones"""
    print("\n" + "="*80)
    print("DIAGNÓSTICO 3: PRUEBA DE AJUSTES DE TIMEZONE")
    print("="*80)
    
    # Casos de prueba
    test_cases = [
        {
            "fecha": datetime(2025, 12, 16, 14, 30, 0),
            "descripcion": "Cleaner out at 14:30, called at [02:35]",
            "tz": "MT",
            "esperado_offset": -2
        },
        {
            "fecha": datetime(2025, 12, 16, 20, 15, 0),
            "descripcion": "Event at 8:15 PM, ref [20:15:30]",
            "tz": "CT",
            "esperado_offset": -1
        },
        {
            "fecha": datetime(2025, 12, 16, 10, 0, 0),
            "descripcion": "Started at 10:00:00",
            "tz": "PT",
            "esperado_offset": -3
        }
    ]
    
    for i, test in enumerate(test_cases, 1):
        print(f"\n📝 Caso de prueba {i}:")
        print(f"  Timezone: {test['tz']} (esperado offset: {test['esperado_offset']:+d}h)")
        print(f"  Fecha original: {test['fecha']}")
        print(f"  Descripción original: {test['descripcion']}")
        
        # Ajustar fecha
        fecha_ajustada = adjust_datetime(test['fecha'], test['tz'])
        print(f"  ✅ Fecha ajustada: {fecha_ajustada}")
        print(f"     Diferencia: {(fecha_ajustada - test['fecha']).total_seconds() / 3600:+.1f} horas")
        
        # Ajustar descripción
        desc_ajustada = adjust_description_timestamps(
            test['descripcion'],
            test['fecha'],
            test['tz']
        )
        print(f"  ✅ Descripción ajustada: {desc_ajustada}")


def diagnosticar_eventos_reales(username):
    """Verifica eventos reales de un operador"""
    print("\n" + "="*80)
    print(f"DIAGNÓSTICO 4: EVENTOS REALES DEL OPERADOR '{username}'")
    print("="*80)
    
    try:
        # Obtener último shift
        last_shift = specials_model.get_last_shift_start(username)
        if not last_shift:
            print(f"\n❌ No se encontró START SHIFT para {username}")
            return
        
        print(f"\n⏰ Último START SHIFT: {last_shift}")
        
        # Obtener eventos especiales
        eventos = specials_model.get_specials_eventos(username, last_shift)
        print(f"\n📊 Total de eventos especiales encontrados: {len(eventos)}")
        
        if eventos:
            print("\n📋 Primeros 3 eventos:")
            for i, evento in enumerate(eventos[:3], 1):
                id_ev, fecha, sitio, actividad, cant, cam, desc, user = evento
                
                # Obtener info del sitio
                nombre_sitio, tz = specials_model.get_site_info(sitio)
                
                print(f"\n  Evento {i}:")
                print(f"    ID: {id_ev}")
                print(f"    Fecha original: {fecha}")
                print(f"    Sitio: {nombre_sitio} (ID: {sitio})")
                print(f"    Timezone: {tz}")
                print(f"    Actividad: {actividad}")
                print(f"    Descripción original: {desc}")
                
                if tz:
                    # Probar ajuste
                    fecha_ajustada = adjust_datetime(fecha, tz)
                    desc_ajustada = adjust_description_timestamps(desc, fecha, tz)
                    print(f"    ➡️ Fecha ajustada: {fecha_ajustada}")
                    print(f"    ➡️ Descripción ajustada: {desc_ajustada}")
                    
                    offset = get_timezone_offset(tz)
                    print(f"    📌 Offset aplicado: {offset:+d} horas")
        else:
            print("\n⚠️ No hay eventos especiales desde el último START SHIFT")
            
            # Verificar todos los eventos del operador
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT COUNT(*) FROM Eventos e
                INNER JOIN user u ON e.ID_Usuario = u.ID_Usuario
                WHERE u.Nombre_Usuario = %s AND e.FechaHora >= %s
            """, (username, last_shift))
            total_eventos = cursor.fetchone()[0]
            print(f"  Total de eventos (todos los grupos): {total_eventos}")
            
            # Verificar eventos por grupo
            cursor.execute("""
                SELECT s.ID_Grupo, COUNT(*) as count
                FROM Eventos e
                INNER JOIN user u ON e.ID_Usuario = u.ID_Usuario
                INNER JOIN Sitios s ON e.ID_Sitio = s.ID_Sitio
                WHERE u.Nombre_Usuario = %s AND e.FechaHora >= %s
                GROUP BY s.ID_Grupo
                ORDER BY count DESC
            """, (username, last_shift))
            grupos = cursor.fetchall()
            
            if grupos:
                print("\n  Distribución por grupo:")
                for grupo, count in grupos:
                    es_especial = "⭐" if grupo in specials_model.GRUPOS_ESPECIALES else "  "
                    print(f"    {es_especial} {grupo}: {count} eventos")
            
            cursor.close()
            conn.close()
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print("\n🔍 DIAGNÓSTICO COMPLETO DE SISTEMA SPECIALS")
    print("=" * 80)
    
    # Ejecutar todos los diagnósticos
    diagnosticar_id_grupo()
    diagnosticar_timezones()
    diagnosticar_ajustes()
    
    # Para diagnóstico de eventos reales, cambiar el username
    # diagnosticar_eventos_reales("NOMBRE_OPERADOR_AQUI")
    
    print("\n" + "="*80)
    print("✅ DIAGNÓSTICO COMPLETADO")
    print("="*80)
    print("\n💡 PRÓXIMOS PASOS:")
    print("  1. Revisar los resultados del DIAGNÓSTICO 1 para verificar ID_Grupo")
    print("  2. Revisar el DIAGNÓSTICO 2 para confirmar configuración de timezones")
    print("  3. Descomentar última línea y poner tu username para ver eventos reales")
    print()
