


from database import get_connection



def get_centralstation_positions():

    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""SELECT 
            station_number,
            station_user, 
            is_active
            FROM stations_map
            WHERE is_active = '1';""")
        for sid, user in cur.fetchall():
            print(f"[DEBUG] Station {sid} - User: {user}")
        cur.close()
        conn.close()    
    except Exception as e:
        print(f"[ERROR] get_centralstation_positions: {e}")
    return []