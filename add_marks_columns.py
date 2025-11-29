"""
Script para agregar columnas de marcado persistente a la tabla specials
"""
import under_super

def add_marks_columns():
    try:
        conn = under_super.get_connection()
        cur = conn.cursor()
        
        print("Agregando columnas de marcado a 'specials'...")
        
        # Columna 1: marked_status (flagged, last, NULL)
        try:
            cur.execute("""
                ALTER TABLE specials 
                ADD COLUMN marked_status VARCHAR(20) DEFAULT NULL 
                COMMENT 'Estado de marca: flagged, last o NULL'
            """)
            print("✅ Columna 'marked_status' agregada")
        except Exception as e:
            if "Duplicate column" in str(e):
                print("⚠️  Columna 'marked_status' ya existe")
            else:
                print(f"❌ Error en marked_status: {e}")
        
        # Columna 2: marked_at (timestamp)
        try:
            cur.execute("""
                ALTER TABLE specials 
                ADD COLUMN marked_at TIMESTAMP NULL DEFAULT NULL 
                COMMENT 'Fecha/hora de marcado'
            """)
            print("✅ Columna 'marked_at' agregada")
        except Exception as e:
            if "Duplicate column" in str(e):
                print("⚠️  Columna 'marked_at' ya existe")
            else:
                print(f"❌ Error en marked_at: {e}")
        
        # Columna 3: marked_by (usuario que marcó)
        try:
            cur.execute("""
                ALTER TABLE specials 
                ADD COLUMN marked_by VARCHAR(100) DEFAULT NULL 
                COMMENT 'Usuario que marcó el registro'
            """)
            print("✅ Columna 'marked_by' agregada")
        except Exception as e:
            if "Duplicate column" in str(e):
                print("⚠️  Columna 'marked_by' ya existe")
            else:
                print(f"❌ Error en marked_by: {e}")
        
        conn.commit()
        
        # Verificar columnas
        print("\n📋 Verificando columnas agregadas:")
        cur.execute("""
            SELECT COLUMN_NAME, COLUMN_TYPE, IS_NULLABLE, COLUMN_DEFAULT
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE()
            AND TABLE_NAME = 'specials'
            AND COLUMN_NAME IN ('marked_status', 'marked_at', 'marked_by')
            ORDER BY ORDINAL_POSITION
        """)
        
        for row in cur.fetchall():
            print(f"  - {row[0]}: {row[1]} (Nullable: {row[2]}, Default: {row[3]})")
        
        cur.close()
        conn.close()
        print("\n✅ Script completado exitosamente")
        
    except Exception as e:
        print(f"❌ Error general: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    add_marks_columns()
