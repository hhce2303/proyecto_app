"""
Script de prueba para verificar query de covers
"""
from models.database import get_connection

def test_covers_query():
    """Prueba el query de covers_realizados"""
    try:
        conn = get_connection()
        if not conn:
            print("❌ No se pudo conectar a la base de datos")
            return
        
        cursor = conn.cursor()
        
        # 1. Verificar covers_realizados
        print("\n=== COVERS REALIZADOS ===")
        cursor.execute("""
            SELECT 
                ID_Covers,
                Nombre_usuarios,
                Cover_in,
                Cover_out,
                Motivo,
                Covered_by,
                ID_programacion_covers
            FROM covers_realizados
            ORDER BY Cover_in DESC
            LIMIT 10
        """)
        
        covers = cursor.fetchall()
        print(f"Total de covers encontrados: {len(covers)}")
        
        for cover in covers:
            activo = "Sí" if cover[3] is None else "No"  # Cover_out NULL = activo
            print(f"  ID: {cover[0]}, Usuario: {cover[1]}, Cover_in: {cover[2]}, Activo: {activo}")
        
        # 2. Verificar covers_programados
        print("\n=== COVERS PROGRAMADOS ===")
        cursor.execute("""
            SELECT 
                ID_Cover,
                ID_user,
                Time_request,
                is_Active
            FROM covers_programados
            ORDER BY Time_request DESC
            LIMIT 10
        """)
        
        programados = cursor.fetchall()
        print(f"Total de covers programados: {len(programados)}")
        
        for prog in programados:
            print(f"  ID: {prog[0]}, Usuario: {prog[1]}, Time_request: {prog[2]}, Activo: {prog[3]}")
        
        # 3. Verificar último START SHIFT para 'prueba'
        print("\n=== ÚLTIMO START SHIFT ===")
        cursor.execute("""
            SELECT MAX(FechaHora)
            FROM Eventos
            WHERE ID_Usuario = (SELECT ID_Usuario FROM user WHERE Nombre_Usuario = 'prueba')
            AND Nombre_Actividad = 'START SHIFT'
        """)
        
        last_shift = cursor.fetchone()
        print(f"Último START SHIFT de 'prueba': {last_shift[0] if last_shift else 'N/A'}")
        
        # 4. Query completo con LEFT JOIN
        print("\n=== QUERY COMPLETO CON LEFT JOIN ===")
        cursor.execute("""
            SELECT 
                cr.ID_Covers,
                cr.Nombre_usuarios,
                cr.Cover_in,
                cr.Cover_out,
                cr.Motivo,
                cr.Covered_by,
                cr.ID_programacion_covers,
                cp.ID_Cover,
                cp.Time_request
            FROM covers_realizados cr
            LEFT JOIN covers_programados cp 
                ON cr.ID_programacion_covers = cp.ID_Cover
            WHERE cr.Nombre_usuarios = 'prueba'
            ORDER BY cr.Cover_in DESC
        """)
        
        results = cursor.fetchall()
        print(f"Resultados para usuario 'prueba': {len(results)}")
        
        for res in results:
            activo = "Sí" if res[3] is None else "No"
            print(f"  ID_realizado: {res[0]}, Cover_in: {res[2]}, Cover_out: {res[3]}, "
                  f"Activo: {activo}, ID_programado: {res[7]}, Time_request: {res[8]}")
        
        cursor.close()
        conn.close()
        
        print("\n✅ Prueba completada")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_covers_query()
