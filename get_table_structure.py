"""
Script para obtener estructura de covers_realizados
"""
from models.database import get_connection

def get_table_structure():
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Obtener estructura de la tabla
        cursor.execute("DESCRIBE covers_realizados")
        columns = cursor.fetchall()
        
        print("\n=== ESTRUCTURA DE covers_realizados ===")
        for col in columns:
            print(f"{col[0]:<30} {col[1]:<15} NULL: {col[2]}")
        
        # Obtener un registro de ejemplo
        cursor.execute("SELECT * FROM covers_realizados LIMIT 1")
        result = cursor.fetchone()
        
        if result:
            print(f"\n=== EJEMPLO DE REGISTRO (total de columnas: {len(result)}) ===")
            for idx, val in enumerate(result):
                print(f"Columna {idx}: {val}")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    get_table_structure()
