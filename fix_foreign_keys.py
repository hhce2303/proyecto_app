"""
Script para configurar Foreign Keys automáticamente para el Sistema de Papelera
Ejecuta este script UNA VEZ para configurar la base de datos correctamente
"""

import under_super
import traceback

def fix_foreign_keys():
    """Elimina y recrea las Foreign Keys con ON DELETE SET NULL"""
    
    print("=" * 80)
    print("🔧 CONFIGURANDO FOREIGN KEYS PARA PAPELERA")
    print("=" * 80)
    print()
    
    try:
        conn = under_super.get_connection()
        cur = conn.cursor()
        
        # PASO 1: Asegurar que columnas FK acepten NULL
        print("1️⃣ Modificando columnas para aceptar NULL...")
        
        modifications = [
            "ALTER TABLE eventos MODIFY COLUMN ID_Sitio INT NULL",
            "ALTER TABLE eventos MODIFY COLUMN ID_Usuario INT NULL",
            "ALTER TABLE eventos MODIFY COLUMN Nombre_Actividad VARCHAR(100) NULL",
            "ALTER TABLE covers MODIFY COLUMN Nombre_Usuarios INT NULL",
            "ALTER TABLE covers MODIFY COLUMN Covered_by INT NULL",
            "ALTER TABLE sesiones MODIFY COLUMN Nombre_Usuario INT NULL",
            "ALTER TABLE specials MODIFY COLUMN ID_Sitio INT NULL",
            "ALTER TABLE specials MODIFY COLUMN Usuario INT NULL",
            "ALTER TABLE specials MODIFY COLUMN Supervisor INT NULL",
            "ALTER TABLE specials MODIFY COLUMN Nombre_Actividad VARCHAR(100) NULL",
        ]
        
        for sql in modifications:
            try:
                cur.execute(sql)
                print(f"   ✅ {sql.split('MODIFY')[1].strip()}")
            except Exception as e:
                print(f"   ⚠️ {sql.split('MODIFY')[1].strip()} - {e}")
        
        conn.commit()
        print()
        
        # PASO 2: Eliminar Foreign Keys existentes
        print("2️⃣ Eliminando Foreign Keys antiguas...")
        
        drops = [
            ("eventos", "eventos_ibfk_1"),
            ("eventos", "eventos_ibfk_2"),
            ("eventos", "eventos_ibfk_3"),
            ("covers", "covers_ibfk_1"),
            ("covers", "covers_ibfk_2"),
            ("sesiones", "sesiones_ibfk_1"),
            ("specials", "specials_ibfk_1"),
            ("specials", "specials_ibfk_2"),
            ("specials", "specials_ibfk_3"),
            ("specials", "specials_ibfk_4"),
        ]
        
        for table, constraint in drops:
            try:
                cur.execute(f"ALTER TABLE {table} DROP FOREIGN KEY {constraint}")
                print(f"   ✅ Eliminado {table}.{constraint}")
            except Exception as e:
                print(f"   ⚠️ {table}.{constraint} - {e}")
        
        conn.commit()
        print()
        
        # PASO 3: Recrear con ON DELETE SET NULL
        print("3️⃣ Creando nuevas Foreign Keys con ON DELETE SET NULL...")
        
        creates = [
            # Eventos
            ("eventos", "eventos_ibfk_1", "ID_Sitio", "sitios", "ID_Sitio"),
            ("eventos", "eventos_ibfk_2", "ID_Usuario", "user", "ID_Usuario"),
            ("eventos", "eventos_ibfk_3", "Nombre_Actividad", "actividades", "ID_Actividad"),
            # Covers
            ("covers", "covers_ibfk_1", "Nombre_Usuarios", "user", "ID_Usuario"),
            ("covers", "covers_ibfk_2", "Covered_by", "user", "ID_Usuario"),
            # Sesiones
            ("sesiones", "sesiones_ibfk_1", "Nombre_Usuario", "user", "ID_Usuario"),
            # specials
            ("specials", "specials_ibfk_1", "ID_Sitio", "sitios", "ID_Sitio"),
            ("specials", "specials_ibfk_2", "Nombre_Actividad", "actividades", "ID_Actividad"),
            ("specials", "specials_ibfk_3", "Usuario", "user", "ID_Usuario"),
            ("specials", "specials_ibfk_4", "Supervisor", "user", "ID_Usuario"),
        ]
        
        for table, constraint, col, ref_table, ref_col in creates:
            try:
                sql = f"""
                    ALTER TABLE {table}
                      ADD CONSTRAINT {constraint}
                      FOREIGN KEY ({col}) REFERENCES {ref_table}({ref_col})
                      ON DELETE SET NULL ON UPDATE CASCADE
                """
                cur.execute(sql)
                print(f"   ✅ {table}.{col} → {ref_table}.{ref_col} (ON DELETE SET NULL)")
            except Exception as e:
                print(f"   ❌ {table}.{col} - {e}")
        
        conn.commit()
        print()
        
        # VERIFICACIÓN
        print("4️⃣ Verificando configuración...")
        cur.execute("""
            SELECT 
                kcu.TABLE_NAME,
                kcu.COLUMN_NAME,
                rc.DELETE_RULE
            FROM
                INFORMATION_SCHEMA.KEY_COLUMN_USAGE kcu
                LEFT JOIN INFORMATION_SCHEMA.REFERENTIAL_CONSTRAINTS rc
                  ON kcu.CONSTRAINT_NAME = rc.CONSTRAINT_NAME
                  AND kcu.CONSTRAINT_SCHEMA = rc.CONSTRAINT_SCHEMA
            WHERE
                kcu.TABLE_SCHEMA = 'Daily'
                AND kcu.TABLE_NAME IN ('eventos', 'covers', 'sesiones', 'specials')
                AND kcu.REFERENCED_TABLE_NAME IS NOT NULL
            ORDER BY kcu.TABLE_NAME, kcu.COLUMN_NAME
        """)
        
        fks = cur.fetchall()
        all_ok = True
        for table, col, delete_rule in fks:
            if delete_rule == 'SET NULL':
                print(f"   ✅ {table}.{col} → ON DELETE {delete_rule}")
            else:
                print(f"   ❌ {table}.{col} → ON DELETE {delete_rule}")
                all_ok = False
        
        cur.close()
        conn.close()
        
        print()
        print("=" * 80)
        if all_ok:
            print("✅ CONFIGURACIÓN COMPLETADA CON ÉXITO")
            print("🎉 El sistema de Papelera está listo para usar")
        else:
            print("⚠️ ALGUNAS CONFIGURACIONES FALLARON")
            print("💡 Revisa los errores arriba y ejecuta manualmente el SQL que falló")
        print("=" * 80)
        
    except Exception as e:
        print(f"❌ Error durante la configuración: {e}")
        traceback.print_exc()


if __name__ == "__main__":
    print("\n⚠️  ADVERTENCIA:")
    print("Este script modificará las Foreign Keys de tu base de datos.")
    print("Asegúrate de tener un backup antes de continuar.\n")
    
    respuesta = input("¿Deseas continuar? (si/no): ").strip().lower()
    
    if respuesta in ('si', 's', 'sí', 'yes', 'y'):
        print()
        fix_foreign_keys()
    else:
        print("❌ Operación cancelada")
