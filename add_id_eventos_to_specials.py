"""
Script de migración de Base de Datos
Agrega columna ID_Eventos a la tabla specials para relación con Eventos

JUSTIFICACIÓN:
- Tabla specials es hija de tabla Eventos (todos los specials son eventos)
- Facilita determinar si hacer UPDATE o INSERT (evita duplicados)
- Elimina necesidad de cache temporal y pending_changes
- Mayor integridad referencial

EJECUCIÓN:
python add_id_eventos_to_specials.py
"""

from models.database import get_connection
import traceback


def add_id_eventos_column():
    """
    Agrega la columna ID_Eventos a la tabla specials si no existe.
    Crea índice y foreign key constraint.
    """
    print("=" * 70)
    print("MIGRACIÓN: Agregar ID_Eventos a tabla specials")
    print("=" * 70)
    
    try:
        conn = get_connection()
        if not conn:
            print("[ERROR] No se pudo conectar a la base de datos")
            return False
        
        cursor = conn.cursor()
        
        # Verificar si la columna ya existe
        print("\n[1/5] Verificando si columna ID_Eventos ya existe...")
        cursor.execute("""
            SELECT COUNT(*)
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = 'daily'
            AND TABLE_NAME = 'specials'
            AND COLUMN_NAME = 'ID_Eventos'
        """)
        
        exists = cursor.fetchone()[0]
        
        if exists > 0:
            print("✅ La columna ID_Eventos ya existe en la tabla specials")
            cursor.close()
            conn.close()
            return True
        
        print("❌ Columna ID_Eventos no existe. Procediendo con migración...")
        
        # Agregar columna ID_Eventos
        print("\n[2/5] Agregando columna ID_Eventos...")
        cursor.execute("""
            ALTER TABLE specials
            ADD COLUMN ID_Eventos INT NULL
            COMMENT 'FK a tabla Eventos - Relación 1:1 con evento padre'
        """)
        print("✅ Columna ID_Eventos agregada exitosamente")
        
        # Crear índice para mejor performance
        print("\n[3/5] Creando índice en ID_Eventos...")
        cursor.execute("""
            CREATE INDEX idx_specials_id_eventos
            ON specials(ID_Eventos)
        """)
        print("✅ Índice creado exitosamente")
        
        # Agregar foreign key constraint
        print("\n[4/5] Agregando foreign key constraint...")
        try:
            cursor.execute("""
                ALTER TABLE specials
                ADD CONSTRAINT fk_specials_eventos
                FOREIGN KEY (ID_Eventos)
                REFERENCES Eventos(ID_Eventos)
                ON DELETE CASCADE
                ON UPDATE CASCADE
            """)
            print("✅ Foreign key constraint agregada exitosamente")
        except Exception as e:
            print(f"⚠️ Warning: No se pudo agregar foreign key (puede que ya exista): {e}")
        
        # Commit cambios
        print("\n[5/5] Guardando cambios...")
        conn.commit()
        print("✅ Migración completada exitosamente")
        
        # Mostrar estructura actualizada
        print("\n" + "=" * 70)
        print("ESTRUCTURA ACTUALIZADA DE TABLA SPECIALS")
        print("=" * 70)
        cursor.execute("DESCRIBE specials")
        columns = cursor.fetchall()
        
        print(f"\n{'Campo':<25} {'Tipo':<20} {'Null':<8} {'Key':<8}")
        print("-" * 70)
        for col in columns:
            field, type_, null, key, default, extra = col
            print(f"{field:<25} {type_:<20} {null:<8} {key:<8}")
        
        cursor.close()
        conn.close()
        
        print("\n" + "=" * 70)
        print("✅ MIGRACIÓN COMPLETADA CON ÉXITO")
        print("=" * 70)
        print("\nPRÓXIMOS PASOS:")
        print("1. Reiniciar la aplicación para usar la nueva columna")
        print("2. Los nuevos specials se crearán con ID_Eventos automáticamente")
        print("3. Los specials antiguos tendrán ID_Eventos = NULL (funciona como fallback)")
        
        return True
        
    except Exception as e:
        print(f"\n[ERROR] Error durante la migración: {e}")
        traceback.print_exc()
        
        if conn:
            try:
                conn.rollback()
                print("\n⚠️ Cambios revertidos (rollback)")
            except:
                pass
        
        return False


def verify_migration():
    """Verifica que la migración se haya aplicado correctamente."""
    print("\n" + "=" * 70)
    print("VERIFICACIÓN DE MIGRACIÓN")
    print("=" * 70)
    
    try:
        conn = get_connection()
        if not conn:
            print("[ERROR] No se pudo conectar a la base de datos")
            return False
        
        cursor = conn.cursor()
        
        # Verificar columna
        cursor.execute("""
            SELECT COLUMN_NAME, COLUMN_TYPE, IS_NULLABLE, COLUMN_KEY
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = 'daily'
            AND TABLE_NAME = 'specials'
            AND COLUMN_NAME = 'ID_Eventos'
        """)
        
        result = cursor.fetchone()
        
        if result:
            print("\n✅ Columna ID_Eventos encontrada:")
            print(f"   - Nombre: {result[0]}")
            print(f"   - Tipo: {result[1]}")
            print(f"   - Nullable: {result[2]}")
            print(f"   - Key: {result[3]}")
        else:
            print("\n❌ Columna ID_Eventos NO encontrada")
            return False
        
        # Verificar índice
        cursor.execute("""
            SELECT INDEX_NAME
            FROM INFORMATION_SCHEMA.STATISTICS
            WHERE TABLE_SCHEMA = 'daily'
            AND TABLE_NAME = 'specials'
            AND COLUMN_NAME = 'ID_Eventos'
        """)
        
        indexes = cursor.fetchall()
        if indexes:
            print(f"\n✅ Índices encontrados: {', '.join([idx[0] for idx in indexes])}")
        else:
            print("\n⚠️ No se encontraron índices en ID_Eventos")
        
        # Verificar foreign key
        cursor.execute("""
            SELECT CONSTRAINT_NAME, REFERENCED_TABLE_NAME
            FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
            WHERE TABLE_SCHEMA = 'daily'
            AND TABLE_NAME = 'specials'
            AND COLUMN_NAME = 'ID_Eventos'
            AND REFERENCED_TABLE_NAME IS NOT NULL
        """)
        
        fks = cursor.fetchall()
        if fks:
            print(f"\n✅ Foreign keys encontradas:")
            for fk in fks:
                print(f"   - {fk[0]} → {fk[1]}")
        else:
            print("\n⚠️ No se encontraron foreign keys")
        
        cursor.close()
        conn.close()
        
        print("\n" + "=" * 70)
        print("✅ VERIFICACIÓN COMPLETADA")
        print("=" * 70)
        
        return True
        
    except Exception as e:
        print(f"\n[ERROR] Error durante la verificación: {e}")
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("\n🚀 Iniciando migración de base de datos...")
    print("Database: daily")
    print("Table: specials")
    print("Action: ADD COLUMN ID_Eventos INT\n")
    
    # Ejecutar migración
    success = add_id_eventos_column()
    
    if success:
        # Verificar migración
        verify_migration()
        print("\n✨ Proceso completado exitosamente\n")
    else:
        print("\n❌ Migración fallida. Revisa los errores arriba.\n")
