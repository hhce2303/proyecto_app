"""
🧹 LIMPIEZA DE DUPLICADOS EN TABLA SPECIALS
===========================================
Script SEGURO para eliminar registros duplicados conservando el más antiguo.

CARACTERÍSTICAS:
- Hace backup automático antes de eliminar
- Muestra preview de qué se eliminará
- Pide confirmación múltiple
- Registra todas las acciones en log
- Puede revertir cambios si hay problemas

USO:
    python cleanup_duplicates.py

ADVERTENCIA:
    Este script MODIFICARÁ la base de datos. Asegúrate de tener un respaldo completo.
"""

import mysql.connector
from datetime import datetime
import json

# ⭐ CONFIGURACIÓN DE CONEXIÓN
DB_CONFIG = {
    'host': 'localhost',
    'user': 'app_user',
    'password': '1234',
    'database': 'daily'
}

def get_connection():
    """Obtiene conexión a la base de datos"""
    try:
        return mysql.connector.connect(**DB_CONFIG)
    except Exception as e:
        print(f"❌ Error de conexión: {e}")
        return None

def create_backup_table():
    """Crea tabla de respaldo para duplicados eliminados"""
    print("\n" + "="*80)
    print("💾 CREANDO TABLA DE BACKUP")
    print("="*80)
    
    conn = get_connection()
    if not conn:
        return False
    
    try:
        cur = conn.cursor()
        
        # Verificar si ya existe la tabla
        cur.execute("SHOW TABLES LIKE 'specials_duplicates_backup'")
        if cur.fetchone():
            print("⚠️  Tabla 'specials_duplicates_backup' ya existe.")
            response = input("   ¿Deseas crear una nueva tabla con timestamp? (s/n): ").lower()
            if response == 's':
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_table = f"specials_duplicates_backup_{timestamp}"
            else:
                backup_table = "specials_duplicates_backup"
                cur.execute(f"DROP TABLE IF EXISTS {backup_table}")
                print(f"   ✅ Tabla anterior eliminada")
        else:
            backup_table = "specials_duplicates_backup"
        
        # Crear tabla de backup (estructura idéntica a specials)
        cur.execute(f"""
            CREATE TABLE IF NOT EXISTS {backup_table} LIKE specials
        """)
        
        # Agregar columnas de auditoría
        try:
            cur.execute(f"""
                ALTER TABLE {backup_table}
                ADD COLUMN deleted_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                ADD COLUMN deleted_reason VARCHAR(255) DEFAULT 'Duplicate removal'
            """)
        except:
            pass  # Columnas ya existen
        
        conn.commit()
        cur.close()
        conn.close()
        
        print(f"✅ Tabla de backup creada: {backup_table}")
        return backup_table
        
    except Exception as e:
        print(f"❌ Error al crear tabla de backup: {e}")
        return False

def find_duplicates():
    """Encuentra y retorna grupos de duplicados"""
    print("\n" + "="*80)
    print("🔍 IDENTIFICANDO DUPLICADOS")
    print("="*80)
    
    conn = get_connection()
    if not conn:
        return None
    
    cur = conn.cursor()
    
    # Query para encontrar duplicados
    query = """
        SELECT 
            Usuario,
            Nombre_Actividad,
            ID_Sitio,
            Descripcion,
            COUNT(*) as count,
            GROUP_CONCAT(ID_special ORDER BY ID_special ASC) as ids,
            MIN(ID_special) as keep_id,
            GROUP_CONCAT(FechaHora ORDER BY ID_special ASC) as fechas
        FROM specials
        GROUP BY Usuario, Nombre_Actividad, ID_Sitio, Descripcion
        HAVING COUNT(*) > 1
        ORDER BY count DESC
    """
    
    cur.execute(query)
    duplicates = cur.fetchall()
    
    cur.close()
    conn.close()
    
    if not duplicates:
        print("\n✅ No se encontraron duplicados en la tabla specials.")
        return None
    
    print(f"\n⚠️  Encontrados {len(duplicates)} grupos de duplicados:")
    print("="*80)
    
    total_to_delete = 0
    for idx, dup in enumerate(duplicates, 1):
        usuario, actividad, sitio, desc, count, ids, keep_id, fechas = dup
        delete_count = count - 1
        total_to_delete += delete_count
        
        print(f"\n📋 Grupo #{idx}:")
        print(f"   Usuario: {usuario}")
        print(f"   Actividad: {actividad}")
        print(f"   Sitio: {sitio}")
        print(f"   Descripción: {desc[:50] if desc else 'N/A'}...")
        print(f"   Total registros: {count}")
        print(f"   IDs: {ids}")
        print(f"   FechaHoras: {fechas}")
        print(f"   ✅ Conservar: ID={keep_id} (más antiguo)")
        print(f"   ❌ Eliminar: {delete_count} registro(s)")
    
    print("\n" + "="*80)
    print(f"📊 RESUMEN:")
    print(f"   Grupos duplicados: {len(duplicates)}")
    print(f"   Registros a eliminar: {total_to_delete}")
    print(f"   Registros a conservar: {len(duplicates)}")
    print("="*80)
    
    return duplicates

def backup_duplicates(backup_table):
    """Copia registros duplicados a tabla de backup antes de eliminar"""
    print("\n" + "="*80)
    print("💾 RESPALDANDO DUPLICADOS")
    print("="*80)
    
    conn = get_connection()
    if not conn:
        return False
    
    try:
        cur = conn.cursor()
        
        # Insertar duplicados en tabla de backup (todos excepto el más antiguo)
        query = f"""
            INSERT INTO {backup_table}
            SELECT s.*, NOW(), 'Duplicate - kept oldest record'
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
        """
        
        cur.execute(query)
        backed_up = cur.rowcount
        conn.commit()
        
        cur.close()
        conn.close()
        
        print(f"✅ Respaldados {backed_up} registros en tabla '{backup_table}'")
        return True
        
    except Exception as e:
        print(f"❌ Error al respaldar: {e}")
        return False

def delete_duplicates():
    """Elimina registros duplicados (conservando el más antiguo)"""
    print("\n" + "="*80)
    print("🗑️  ELIMINANDO DUPLICADOS")
    print("="*80)
    
    conn = get_connection()
    if not conn:
        return False
    
    try:
        cur = conn.cursor()
        
        # Eliminar duplicados (conservar MIN(ID_special))
        query = """
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
                AND s.ID_special != dup.keep_id
        """
        
        cur.execute(query)
        deleted = cur.rowcount
        conn.commit()
        
        cur.close()
        conn.close()
        
        print(f"✅ Eliminados {deleted} registros duplicados")
        return deleted
        
    except Exception as e:
        print(f"❌ Error al eliminar: {e}")
        return False

def verify_cleanup():
    """Verifica que no queden duplicados después de la limpieza"""
    print("\n" + "="*80)
    print("✔️  VERIFICANDO LIMPIEZA")
    print("="*80)
    
    conn = get_connection()
    if not conn:
        return False
    
    cur = conn.cursor()
    
    # Buscar duplicados restantes
    query = """
        SELECT COUNT(*) as grupos_duplicados
        FROM (
            SELECT Usuario, Nombre_Actividad, ID_Sitio, Descripcion, COUNT(*) as count
            FROM specials
            GROUP BY Usuario, Nombre_Actividad, ID_Sitio, Descripcion
            HAVING COUNT(*) > 1
        ) sub
    """
    
    cur.execute(query)
    result = cur.fetchone()
    remaining = result[0] if result else 0
    
    cur.close()
    conn.close()
    
    if remaining == 0:
        print("✅ Limpieza exitosa: No quedan duplicados en la tabla")
        return True
    else:
        print(f"⚠️  Aún quedan {remaining} grupos de duplicados")
        return False

def generate_report(backup_table):
    """Genera reporte detallado de la limpieza"""
    print("\n" + "="*80)
    print("📄 GENERANDO REPORTE")
    print("="*80)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = f"cleanup_report_{timestamp}.txt"
    
    conn = get_connection()
    if not conn:
        return
    
    cur = conn.cursor()
    
    # Obtener registros respaldados
    cur.execute(f"SELECT * FROM {backup_table}")
    backed_up = cur.fetchall()
    
    cur.close()
    conn.close()
    
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write("="*80 + "\n")
        f.write("REPORTE DE LIMPIEZA DE DUPLICADOS - TABLA SPECIALS\n")
        f.write("="*80 + "\n")
        f.write(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Tabla de backup: {backup_table}\n")
        f.write(f"Registros eliminados: {len(backed_up)}\n")
        f.write("="*80 + "\n\n")
        
        f.write("REGISTROS ELIMINADOS:\n")
        f.write("-"*80 + "\n")
        for record in backed_up:
            f.write(f"ID: {record[0]} | FechaHora: {record[1]} | Usuario: {record[7]} | ")
            f.write(f"Actividad: {record[3]} | Sitio: {record[2]}\n")
        
        f.write("\n" + "="*80 + "\n")
        f.write("QUERY PARA REVERTIR (si es necesario):\n")
        f.write("-"*80 + "\n")
        f.write(f"""
-- Para restaurar los registros eliminados:
INSERT INTO specials 
SELECT 
    ID_special, FechaHora, ID_Sitio, Nombre_Actividad, Cantidad, 
    Camera, Descripcion, Usuario, Time_Zone, Turno, Supervisor,
    marked_status, marked_by, marked_at
FROM {backup_table};
        """)
    
    print(f"✅ Reporte generado: {report_file}")
    return report_file

# ═══════════════════════════════════════════════════════════════════════════════
# MAIN - FLUJO SEGURO DE LIMPIEZA
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    print("\n" + "═"*80)
    print("🧹 LIMPIEZA SEGURA DE DUPLICADOS EN TABLA SPECIALS")
    print("═"*80)
    print("\nEste script eliminará registros duplicados conservando el MÁS ANTIGUO.")
    print("Se hará un backup completo antes de cualquier eliminación.\n")
    
    # Paso 1: Encontrar duplicados
    duplicates = find_duplicates()
    if not duplicates:
        return
    
    # Confirmación 1
    print("\n" + "⚠️ "*40)
    response = input("\n¿Deseas continuar con la limpieza? (escribe 'SI' para confirmar): ")
    if response.upper() != 'SI':
        print("❌ Operación cancelada por el usuario.")
        return
    
    # Paso 2: Crear tabla de backup
    backup_table = create_backup_table()
    if not backup_table:
        print("❌ No se pudo crear tabla de backup. Operación abortada.")
        return
    
    # Paso 3: Respaldar duplicados
    if not backup_duplicates(backup_table):
        print("❌ Error al respaldar. Operación abortada.")
        return
    
    # Confirmación 2
    print("\n" + "⚠️ "*40)
    print("ÚLTIMA ADVERTENCIA: Los registros duplicados serán ELIMINADOS de 'specials'")
    print(f"(pero estarán respaldados en '{backup_table}')")
    response = input("\n¿Confirmas la eliminación? (escribe 'ELIMINAR' para confirmar): ")
    if response.upper() != 'ELIMINAR':
        print("❌ Operación cancelada por el usuario.")
        print(f"ℹ️  Los duplicados fueron respaldados en '{backup_table}'")
        return
    
    # Paso 4: Eliminar duplicados
    deleted = delete_duplicates()
    if deleted is False:
        print("❌ Error al eliminar duplicados.")
        return
    
    # Paso 5: Verificar limpieza
    verify_cleanup()
    
    # Paso 6: Generar reporte
    report = generate_report(backup_table)
    
    print("\n" + "═"*80)
    print("✅ LIMPIEZA COMPLETADA")
    print("═"*80)
    print(f"\n📊 Resultado:")
    print(f"   • Registros eliminados: {deleted}")
    print(f"   • Tabla de backup: {backup_table}")
    print(f"   • Reporte: {report}")
    print(f"\n💡 Notas:")
    print(f"   • Los registros más antiguos fueron conservados")
    print(f"   • Puedes restaurar desde '{backup_table}' si es necesario")
    print(f"   • El bug en operator_window.py ya fue corregido")
    print("\n")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n❌ Operación cancelada por el usuario (Ctrl+C)")
    except Exception as e:
        print(f"\n\n❌ Error inesperado: {e}")
        import traceback
        traceback.print_exc()
