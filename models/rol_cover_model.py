



from models.database import get_connection


def cargar_operadores_rol():
        """Carga operadores activos con su status actual"""
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT DISTINCT s.ID_user, s.Statuses 
            FROM sesion s
            INNER JOIN user u ON s.ID_user = u.Nombre_Usuario
            WHERE s.Active = 1 
                AND u.Rol = 'Operador'
            ORDER BY s.ID_user
        """)
        operadores_covers = cur.fetchall()
        
        cur.close()
        conn.close()
        return operadores_covers



def en_dis_able_access(operadores, new_status):
        """Cambia Statuses para los operadores seleccionados (habilitar/deshabilitar acceso a covers)"""
        try:
            conn = get_connection()
            cur = conn.cursor()
            
            for operador in operadores:
                cur.execute("""
                    UPDATE sesion 
                    SET Statuses = %s 
                    WHERE ID_user = %s AND Active = 1
                """, (new_status, operador))
            
            conn.commit()
            cur.close()
            conn.close()
            return True
        
        except Exception as e:
            print(f"[ERROR] en_dis_able_access: {e}")
            return False