import pymysql

# Script para verificar el último evento de turno
username = input("Ingresa tu nombre de usuario: ")

try:
    conn = pymysql.connect(
        host='192.168.101.135',
        port=3306,
        user='root',
        password='SIGdaily',
        database='daily',
        charset='utf8mb4'
    )
    cur = conn.cursor()
    
    # Buscar últimos 5 eventos de turno
    cur.execute("""
        SELECT e.ID_Evento, e.FechaHora, e.Nombre_Actividad, u.Nombre_Usuario
        FROM Eventos e
        INNER JOIN user u ON e.ID_Usuario = u.ID_Usuario
        WHERE u.Nombre_Usuario = %s
          AND e.Nombre_Actividad IN ('START SHIFT', 'END OF SHIFT')
        ORDER BY e.FechaHora DESC
        LIMIT 5
    """, (username,))
    
    rows = cur.fetchall()
    
    if not rows:
        print(f"\n❌ No hay eventos de turno para {username}")
    else:
        print(f"\n✅ Últimos eventos de turno para {username}:")
        print("-" * 80)
        for r in rows:
            print(f"ID: {r[0]} | Fecha: {r[1]} | Actividad: {r[2]} | Usuario: {r[3]}")
        print("-" * 80)
        
        ultimo = rows[0]
        if ultimo[2] == 'START SHIFT':
            print(f"\n🟢 ÚLTIMO EVENTO: START SHIFT ({ultimo[1]})")
            print("   → El botón debería mostrar: 'End of Shift' (ROJO)")
        else:
            print(f"\n🔴 ÚLTIMO EVENTO: END OF SHIFT ({ultimo[1]})")
            print("   → El botón debería mostrar: 'Start Shift' (VERDE)")
    
    cur.close()
    conn.close()
    
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()

input("\nPresiona Enter para cerrar...")
