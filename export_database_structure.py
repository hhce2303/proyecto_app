"""
Script para exportar la estructura completa de la base de datos 'daily'
Genera un archivo SQL con todas las tablas, llaves primarias, foráneas, índices, etc.
NO incluye datos, solo la estructura para replicar el schema en otra máquina.

Uso:
    python export_database_structure.py

Salida:
    daily_structure.sql - Archivo SQL ejecutable para recrear el schema
"""

import pymysql
from datetime import datetime
import traceback


def get_connection():
    """Establece conexión con la base de datos"""
    try:
        conn = pymysql.connect(
            host="192.168.101.135",
            user="app_user",
            password="1234",
            database="daily",
            port=3306
        )
        print("✅ Conexión exitosa a la base de datos 'daily'")
        return conn
    except pymysql.Error as e:
        print(f"❌ Error de conexión: {e}")
        return None


def get_all_tables(cursor):
    """Obtiene lista de todas las tablas en el schema"""
    cursor.execute("SHOW TABLES")
    tables = [row[0] for row in cursor.fetchall()]
    print(f"📊 Encontradas {len(tables)} tablas")
    return tables


def get_create_table_statement(cursor, table_name):
    """Obtiene el statement CREATE TABLE completo con todas las llaves"""
    cursor.execute(f"SHOW CREATE TABLE `{table_name}`")
    result = cursor.fetchone()
    return result[1] if result else None


def get_foreign_keys(cursor, table_name):
    """Obtiene información detallada de foreign keys"""
    query = """
        SELECT 
            CONSTRAINT_NAME,
            COLUMN_NAME,
            REFERENCED_TABLE_NAME,
            REFERENCED_COLUMN_NAME
        FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
        WHERE TABLE_SCHEMA = 'daily'
          AND TABLE_NAME = %s
          AND REFERENCED_TABLE_NAME IS NOT NULL
        ORDER BY ORDINAL_POSITION
    """
    cursor.execute(query, (table_name,))
    return cursor.fetchall()


def get_indexes(cursor, table_name):
    """Obtiene información de índices"""
    cursor.execute(f"SHOW INDEX FROM `{table_name}`")
    return cursor.fetchall()


def get_table_columns(cursor, table_name):
    """Obtiene información detallada de columnas"""
    query = """
        SELECT 
            COLUMN_NAME,
            COLUMN_TYPE,
            IS_NULLABLE,
            COLUMN_KEY,
            COLUMN_DEFAULT,
            EXTRA,
            COLUMN_COMMENT
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = 'daily'
          AND TABLE_NAME = %s
        ORDER BY ORDINAL_POSITION
    """
    cursor.execute(query, (table_name,))
    return cursor.fetchall()


def export_database_structure():
    """
    Exporta la estructura completa de la base de datos 'daily'
    Genera archivo SQL con CREATE TABLE, índices, foreign keys, etc.
    """
    conn = get_connection()
    if not conn:
        print("❌ No se pudo conectar a la base de datos")
        return
    
    try:
        cursor = conn.cursor()
        
        # Obtener todas las tablas
        tables = get_all_tables(cursor)
        
        if not tables:
            print("⚠️ No se encontraron tablas en el schema 'daily'")
            return
        
        # Preparar archivo SQL de salida
        output_file = "daily_structure.sql"
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        with open(output_file, 'w', encoding='utf-8') as f:
            # Header del archivo
            f.write("-- =====================================================\n")
            f.write("-- ESTRUCTURA COMPLETA DE BASE DE DATOS: daily\n")
            f.write(f"-- Generado: {timestamp}\n")
            f.write("-- NOTA: Este script NO incluye datos, solo estructura\n")
            f.write("-- =====================================================\n\n")
            
            f.write("-- Crear base de datos si no existe\n")
            f.write("CREATE DATABASE IF NOT EXISTS `daily` DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;\n\n")
            f.write("USE `daily`;\n\n")
            
            f.write("-- Deshabilitar verificación de foreign keys temporalmente\n")
            f.write("SET FOREIGN_KEY_CHECKS = 0;\n\n")
            
            # Procesar cada tabla
            for idx, table_name in enumerate(tables, 1):
                print(f"📝 Procesando tabla {idx}/{len(tables)}: {table_name}")
                
                f.write(f"-- =====================================================\n")
                f.write(f"-- Tabla: {table_name}\n")
                f.write(f"-- =====================================================\n\n")
                
                # Obtener CREATE TABLE completo
                create_statement = get_create_table_statement(cursor, table_name)
                
                if create_statement:
                    # Agregar DROP TABLE IF EXISTS
                    f.write(f"DROP TABLE IF EXISTS `{table_name}`;\n\n")
                    
                    # Escribir CREATE TABLE
                    f.write(f"{create_statement};\n\n")
                    
                    # Información adicional de columnas (comentario)
                    columns = get_table_columns(cursor, table_name)
                    if columns:
                        f.write(f"-- Columnas de {table_name}:\n")
                        for col in columns:
                            col_name, col_type, nullable, key, default, extra, comment = col
                            f.write(f"--   {col_name}: {col_type}")
                            if key == 'PRI':
                                f.write(" [PRIMARY KEY]")
                            elif key == 'UNI':
                                f.write(" [UNIQUE]")
                            elif key == 'MUL':
                                f.write(" [INDEX]")
                            if nullable == 'NO':
                                f.write(" NOT NULL")
                            if default is not None:
                                f.write(f" DEFAULT {default}")
                            if extra:
                                f.write(f" {extra}")
                            if comment:
                                f.write(f" -- {comment}")
                            f.write("\n")
                        f.write("\n")
                    
                    # Información de foreign keys (comentario)
                    foreign_keys = get_foreign_keys(cursor, table_name)
                    if foreign_keys:
                        f.write(f"-- Foreign Keys de {table_name}:\n")
                        for fk in foreign_keys:
                            constraint_name, column_name, ref_table, ref_column = fk
                            f.write(f"--   {column_name} -> {ref_table}({ref_column}) [{constraint_name}]\n")
                        f.write("\n")
                    
                else:
                    f.write(f"-- ⚠️ No se pudo obtener CREATE TABLE para {table_name}\n\n")
            
            f.write("-- Rehabilitar verificación de foreign keys\n")
            f.write("SET FOREIGN_KEY_CHECKS = 1;\n\n")
            
            # Footer
            f.write("-- =====================================================\n")
            f.write(f"-- EXPORTACIÓN COMPLETADA: {len(tables)} tablas\n")
            f.write(f"-- Archivo generado: {timestamp}\n")
            f.write("-- =====================================================\n")
        
        print(f"\n✅ Estructura exportada exitosamente a: {output_file}")
        print(f"📊 Total de tablas exportadas: {len(tables)}")
        print(f"\n📌 Para importar en otra máquina:")
        print(f"   mysql -u usuario -p < {output_file}")
        
        # Resumen de tablas
        print(f"\n📋 Tablas exportadas:")
        for i, table in enumerate(tables, 1):
            print(f"   {i:2d}. {table}")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ Error durante la exportación: {e}")
        traceback.print_exc()


if __name__ == "__main__":
    print("=" * 70)
    print("EXPORTADOR DE ESTRUCTURA DE BASE DE DATOS - daily")
    print("=" * 70)
    print()
    
    export_database_structure()
    
    print()
    print("=" * 70)
