"""
Script de diagnóstico para el Sistema de Papelera
Ejecuta este script para verificar que todo está configurado correctamente
"""

import under_super
import traceback

def check_backup_system():
    """Verifica que el sistema de Papelera esté configurado correctamente"""
    
    print("=" * 80)
    print("🔍 DIAGNÓSTICO DEL SISTEMA DE PAPELERA")
    print("=" * 80)
    print()
    
    try:
        conn = under_super.get_connection()
        cur = conn.cursor()
        
        # 1. Verificar tablas de respaldo
        print("1️⃣ Verificando tablas de respaldo (*_deleted)...")
        tables_to_check = ['Eventos_deleted', 'Covers_deleted', 'Sesiones_deleted', 
                          'Estaciones_deleted', 'specials_deleted']
        
        for table in tables_to_check:
            cur.execute(f"SHOW TABLES LIKE '{table}'")
            if cur.fetchone():
                print(f"   ✅ {table} existe")
                
                # Verificar columnas de auditoría
                cur.execute(f"SHOW COLUMNS FROM {table} WHERE Field IN ('deleted_at', 'deleted_by', 'deletion_reason')")
                audit_cols = cur.fetchall()
                if len(audit_cols) == 3:
                    print(f"      ✅ Columnas de auditoría presentes")
                else:
                    print(f"      ⚠️ Faltan columnas de auditoría (encontradas: {len(audit_cols)}/3)")
            else:
                print(f"   ❌ {table} NO existe - ejecutar create_backup_tables()")
        
        print()
        
        # 2. Verificar Foreign Keys
        print("2️⃣ Verificando configuración de Foreign Keys...")
        cur.execute("""
            SELECT 
                kcu.TABLE_NAME,
                kcu.COLUMN_NAME,
                kcu.CONSTRAINT_NAME,
                rc.DELETE_RULE,
                kcu.REFERENCED_TABLE_NAME
            FROM
                INFORMATION_SCHEMA.KEY_COLUMN_USAGE kcu
                LEFT JOIN INFORMATION_SCHEMA.REFERENTIAL_CONSTRAINTS rc
                  ON kcu.CONSTRAINT_NAME = rc.CONSTRAINT_NAME
                  AND kcu.CONSTRAINT_SCHEMA = rc.CONSTRAINT_SCHEMA
            WHERE
                kcu.CONSTRAINT_SCHEMA = 'Daily'
                AND kcu.TABLE_NAME IN ('Eventos', 'Covers', 'Sesiones', 'specials')
                AND kcu.REFERENCED_TABLE_NAME IS NOT NULL
            ORDER BY kcu.TABLE_NAME, kcu.COLUMN_NAME
        """)
        
        fks = cur.fetchall()
        if not fks:
            print("   ⚠️ No se encontraron Foreign Keys - el sistema funcionará pero sin integridad referencial")
        else:
            for fk in fks:
                table, col, constraint, delete_rule, ref_table = fk
                if delete_rule == 'SET NULL':
                    status = "✅"
                elif delete_rule == 'NO ACTION' or delete_rule == 'RESTRICT':
                    status = "❌"
                else:
                    status = "⚠️"
                
                print(f"   {status} {table}.{col} → {ref_table} (ON DELETE {delete_rule})")
        
        print()
        
        # 3. Verificar columnas NULL
        print("3️⃣ Verificando que columnas FK acepten NULL...")
        critical_columns = [
            ('Eventos', 'ID_Sitio'),
            ('Eventos', 'ID_Usuario'),
            ('Covers', 'Nombre_Usuarios'),
            ('Sesiones', 'Nombre_Usuario'),
            ('specials', 'ID_Sitio')
        ]
        
        for table, column in critical_columns:
            cur.execute(f"SHOW COLUMNS FROM {table} WHERE Field = '{column}'")
            col_info = cur.fetchone()
            if col_info:
                null_allowed = col_info[2]  # NULL field
                if null_allowed == 'YES':
                    print(f"   ✅ {table}.{column} acepta NULL")
                else:
                    print(f"   ❌ {table}.{column} NO acepta NULL - ejecutar script SQL de preparación")
        
        print()
        
        # 4. Contar registros en papelera
        print("4️⃣ Estadísticas de registros en papelera...")
        total_deleted = 0
        for table in ['Eventos_deleted', 'Covers_deleted', 'Sesiones_deleted', 
                     'Estaciones_deleted', 'specials_deleted']:
            try:
                cur.execute(f"SELECT COUNT(*) FROM {table}")
                count = cur.fetchone()[0]
                total_deleted += count
                if count > 0:
                    print(f"   📊 {table}: {count} registros")
            except Exception as e:
                print(f"   ❌ Error al contar {table}: {e}")
        
        if total_deleted == 0:
            print(f"   ✨ No hay registros en papelera (sistema limpio)")
        else:
            print(f"   📊 Total en papelera: {total_deleted} registros")
        
        print()
        
        # 5. Verificar funciones de Python
        print("5️⃣ Verificando funciones de Python...")
        import backend_super
        
        functions = [
            ('create_backup_tables', 'Crear tablas de respaldo'),
            ('safe_delete', 'Borrado seguro'),
            ('restore_deleted', 'Restaurar registros'),
            ('open_trash_window', 'Ventana de papelera')
        ]
        
        for func_name, description in functions:
            if hasattr(backend_super, func_name):
                print(f"   ✅ {func_name}() - {description}")
            else:
                print(f"   ❌ {func_name}() NO ENCONTRADA")
        
        print()
        
        # 6. Verificar permisos de roles
        print("6️⃣ Verificando permisos en roles_config.json...")
        try:
            import json
            with open(under_super.CONFIG_PATH, 'r', encoding='utf-8') as f:
                roles = json.load(f)
                
            roles_with_papelera = []
            roles_without_papelera = []
            
            for role_name, permissions in roles.items():
                if 'Papelera' in permissions:
                    roles_with_papelera.append(role_name)
                else:
                    roles_without_papelera.append(role_name)
            
            if roles_with_papelera:
                print(f"   ✅ Roles con acceso a Papelera: {', '.join(roles_with_papelera)}")
            if roles_without_papelera:
                print(f"   ⚠️ Roles SIN acceso a Papelera: {', '.join(roles_without_papelera)}")
                
        except Exception as e:
            print(f"   ❌ Error al leer roles_config.json: {e}")
        
        print()
        
        # Resumen final
        print("=" * 80)
        print("📋 RESUMEN")
        print("=" * 80)
        
        # Determinar estado general
        all_tables_exist = all([
            cur.execute(f"SHOW TABLES LIKE '{t}'") and cur.fetchone() 
            for t in tables_to_check
        ])
        
        if all_tables_exist and len(fks) > 0:
            print("✅ Sistema de Papelera configurado correctamente")
            print("🎉 Puedes empezar a usar safe_delete() y open_trash_window()")
        elif all_tables_exist:
            print("⚠️ Tablas de respaldo existen pero faltan Foreign Keys")
            print("💡 Ejecuta prepare_papelera_system.sql para configuración óptima")
        else:
            print("❌ Sistema de Papelera NO configurado")
            print("💡 Ejecuta backend_super.create_backup_tables() al iniciar la app")
        
        cur.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ Error durante el diagnóstico: {e}")
        traceback.print_exc()
    
    print()
    print("=" * 80)


if __name__ == "__main__":
    check_backup_system()
