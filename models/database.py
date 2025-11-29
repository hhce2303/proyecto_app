"""
🗄️ DATABASE MANAGER

Gestión centralizada de conexiones a la base de datos MySQL.

Responsabilidades:
- Crear y gestionar pool de conexiones
- Proporcionar conexiones thread-safe
- Manejo de errores de conexión
- Logging de queries (opcional)

TODO: Migrar funciones desde under_super.py
- get_connection()
- Connection pooling
- Error handling
"""

import pymysql
from typing import Optional


class DatabaseManager:
    """Gestor de conexiones a la base de datos"""
    
    _connection_pool = None
    _config = None
    
    @classmethod
    def initialize(cls, host: str, user: str, password: str, database: str, port: int = 3306):
        """
        Inicializa la configuración de la base de datos
        
        Args:
            host: Host de MySQL
            user: Usuario de BD
            password: Contraseña
            database: Nombre de la BD
            port: Puerto (default 3306)
        """
        cls._config = {
            'host': host,
            'user': user,
            'password': password,
            'database': database,
            'port': port
        }
    
    @classmethod
    def get_connection(cls):
        """
        Obtiene una conexión a la base de datos
        
        Returns:
            pymysql.Connection: Conexión activa a la BD
        """
        if cls._config is None:
            raise RuntimeError("DatabaseManager no está inicializado. Llama a initialize() primero.")
        
        try:
            connection = pymysql.connect(
                host=cls._config['host'],
                user=cls._config['user'],
                password=cls._config['password'],
                database=cls._config['database'],
                port=cls._config['port'],
                charset='utf8mb4',
                cursorclass=pymysql.cursors.DictCursor
            )
            return connection
        except pymysql.Error as e:
            print(f"[ERROR] No se pudo conectar a la base de datos: {e}")
            raise
    
    @classmethod
    def close_connection(cls, connection):
        """
        Cierra una conexión de forma segura
        
        Args:
            connection: Conexión a cerrar
        """
        if connection:
            try:
                connection.close()
            except Exception as e:
                print(f"[ERROR] Error al cerrar conexión: {e}")
