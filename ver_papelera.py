"""
Verificar los registros en Eventos_deleted
"""

import under_super

try:
    conn = under_super.get_connection()
    cur = conn.cursor()
    
    print("=" * 80)
    print("📊 REGISTROS EN EVENTOS_DELETED")
    print("=" * 80)
    print()
    
    cur.execute("""
        SELECT 
            ID_Eventos,
            FechaHora,
            Nombre_Actividad,
            deleted_at,
            deleted_by,
            deletion_reason
        FROM Eventos_deleted
        ORDER BY deleted_at DESC
        LIMIT 10
    """)
    
    rows = cur.fetchall()
    
    if not rows:
        print("⚠️ No hay registros en Eventos_deleted")
    else:
        print(f"Total de registros en papelera: {len(rows)}")
        print()
        print("Últimos registros borrados:")
        print("-" * 80)
        
        for row in rows:
            id_evento, fecha_hora, actividad, deleted_at, deleted_by, reason = row
            print(f"ID: {id_evento}")
            print(f"   FechaHora original: {fecha_hora}")
            print(f"   Actividad: {actividad}")
            print(f"   Borrado el: {deleted_at}")
            print(f"   Borrado por: {deleted_by}")
            print(f"   Razón: {reason}")
            print("-" * 80)
    
    cur.close()
    conn.close()
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()

print()
print("💡 También puedes verificar en MySQL Workbench:")
print("   SELECT * FROM Eventos_deleted ORDER BY deleted_at DESC;")
print("=" * 80)
