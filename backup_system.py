# ============================================================================
# SISTEMA DE BACKUP/RESTAURACIÓN (PAPELERA) - Sistema de recuperación de registros borrados
# ============================================================================

import tkinter as tk
from tkinter import ttk, messagebox
import traceback
import under_super


def create_backup_tables():
    """Crea tablas de respaldo para cada tabla principal con sufijo _deleted"""
    try:
        conn = under_super.get_connection()
        cur = conn.cursor()
        
        # Tablas a respaldar
        tables = ['Eventos', 'Covers', 'Sesiones', 'Estaciones', 'specials']
        
        for table in tables:
            # Crear tabla de respaldo si no existe (copia estructura)
            cur.execute(f"CREATE TABLE IF NOT EXISTS `{table}_deleted` LIKE `{table}`")
            
            # Agregar columnas de auditoría si no existen
            try:
                cur.execute(f"""
                    ALTER TABLE `{table}_deleted`
                    ADD COLUMN `deleted_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    ADD COLUMN `deleted_by` VARCHAR(100),
                    ADD COLUMN `deletion_reason` TEXT
                """)
            except Exception:
                # Columnas ya existen, continuar
                pass
        
        conn.commit()
        cur.close()
        conn.close()
        print("✅ Tablas de backup creadas correctamente")
        return True
    except Exception as e:
        print(f"❌ create_backup_tables: {e}")
        traceback.print_exc()
        return False


def safe_delete(table_name, pk_column, pk_value, deleted_by, reason="Manual deletion"):
    """Borra un registro moviéndolo primero a la tabla _deleted
    
    Args:
        table_name: Nombre de la tabla (ej: 'Eventos')
        pk_column: Nombre de la columna PK (ej: 'ID_Eventos')
        pk_value: Valor de la PK a borrar
        deleted_by: Usuario que borra
        reason: Motivo del borrado
    
    Returns:
        True si se borró correctamente, False si hubo error
    """
    try:
        conn = under_super.get_connection()
        cur = conn.cursor()
        
        # 1. Copiar registro a tabla _deleted con metadatos
        cur.execute(f"""
            INSERT INTO `{table_name}_deleted`
            SELECT *, NOW(), %s, %s
            FROM `{table_name}`
            WHERE `{pk_column}` = %s
        """, (deleted_by, reason, pk_value))
        
        # 2. Borrar de tabla original
        cur.execute(f"DELETE FROM `{table_name}` WHERE `{pk_column}` = %s", (pk_value,))
        
        conn.commit()
        cur.close()
        conn.close()
        print(f"✅ Registro {pk_value} de {table_name} movido a backup")
        return True
    except Exception as e:
        print(f"❌ safe_delete: {e}")
        traceback.print_exc()
        try:
            conn.rollback()
        except:
            pass
        return False


def restore_deleted(table_name, pk_column, pk_value):
    """Restaura un registro desde la tabla _deleted
    
    Returns:
        True si se restauró, False si hubo error
    """
    try:
        conn = under_super.get_connection()
        cur = conn.cursor()
        
        # 1. Obtener columnas de la tabla original (sin las de audit)
        cur.execute(f"SHOW COLUMNS FROM `{table_name}`")
        original_cols = [row[0] for row in cur.fetchall()]
        cols_str = ", ".join(f"`{c}`" for c in original_cols)
        
        # 2. Copiar de _deleted a tabla original
        cur.execute(f"""
            INSERT INTO `{table_name}` ({cols_str})
            SELECT {cols_str}
            FROM `{table_name}_deleted`
            WHERE `{pk_column}` = %s
        """, (pk_value,))
        
        # 3. Borrar de _deleted
        cur.execute(f"DELETE FROM `{table_name}_deleted` WHERE `{pk_column}` = %s", (pk_value,))
        
        conn.commit()
        cur.close()
        conn.close()
        print(f"✅ Registro {pk_value} restaurado en {table_name}")
        return True
    except Exception as e:
        print(f"❌ restore_deleted: {e}")
        traceback.print_exc()
        try:
            conn.rollback()
        except:
            pass
        return False


def delete_permanent(table_name, pk_column, pk_value):
    """Elimina permanentemente un registro de la papelera (irreversible)"""
    try:
        conn = under_super.get_connection()
        cur = conn.cursor()
        cur.execute(f"DELETE FROM `{table_name}_deleted` WHERE `{pk_column}` = %s", (pk_value,))
        conn.commit()
        cur.close()
        conn.close()
        print(f"✅ Registro {pk_value} eliminado permanentemente de {table_name}_deleted")
        return True
    except Exception as e:
        print(f"❌ delete_permanent: {e}")
        traceback.print_exc()
        return False


# Mapeo de tablas a sus columnas PK
PK_MAP = {
    "Eventos": "ID_Eventos",
    "Covers": "ID_Covers",
    "Sesiones": "ID_Sesiones",
    "specials": "ID_special",
    "Estaciones": "Station_Number"
}
