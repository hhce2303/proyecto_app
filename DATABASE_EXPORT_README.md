# 📋 Exportación de Estructura de Base de Datos - daily

## 📦 Archivos Generados

- **`daily_structure.sql`** - Script SQL completo con toda la estructura de la base de datos
- **`export_database_structure.py`** - Script Python para regenerar la exportación

---

## ✅ Contenido Exportado

### **26 Tablas Incluidas:**
1. actividades
2. covers
3. covers_deleted
4. covers_programados
5. covers_realizados
6. estaciones
7. estaciones_deleted
8. estaciones_id
9. eventos
10. eventos_backup
11. eventos_deleted
12. gestion_breaks_programados
13. information
14. motivo_id
15. rol_id
16. sesion
17. sesiones
18. sesiones_deleted
19. sitios
20. specials
21. specials_deleted
22. specials_duplicates_backup
23. stations
24. supervisor_status
25. time_zone_id
26. user

### **Estructura Incluida:**
- ✅ Definición de todas las tablas (`CREATE TABLE`)
- ✅ Llaves primarias (`PRIMARY KEY`)
- ✅ Llaves foráneas (`FOREIGN KEY`) con cascadas
- ✅ Índices (`INDEX`, `UNIQUE`)
- ✅ Auto-incrementos
- ✅ Tipos de datos
- ✅ Valores por defecto
- ✅ Comentarios de columnas
- ❌ **NO incluye datos** (solo estructura)

---

## 🚀 Cómo Importar en Otra Máquina

### **Opción 1: Línea de Comandos MySQL**

```bash
# Desde terminal/CMD
mysql -u root -p < daily_structure.sql
```

**Pasos:**
1. Copiar `daily_structure.sql` a la máquina destino
2. Abrir terminal/CMD
3. Navegar al directorio del archivo
4. Ejecutar el comando anterior
5. Ingresar contraseña de MySQL cuando se solicite

---

### **Opción 2: MySQL Workbench**

1. Abrir MySQL Workbench
2. Conectar a tu servidor MySQL
3. Menú: **File → Open SQL Script**
4. Seleccionar `daily_structure.sql`
5. Click en el botón ⚡ **Execute** (o Ctrl+Shift+Enter)
6. Verificar que se ejecute sin errores

---

### **Opción 3: phpMyAdmin**

1. Acceder a phpMyAdmin
2. Ir a la pestaña **SQL**
3. Click en **Browse** y seleccionar `daily_structure.sql`
4. Click en **Go** para ejecutar
5. Verificar mensajes de éxito

---

### **Opción 4: DBeaver / HeidiSQL**

1. Conectar a tu servidor MySQL
2. Abrir editor SQL (F3 o menú SQL Editor)
3. Cargar archivo `daily_structure.sql`
4. Ejecutar (F9 o botón Execute)
5. Revisar mensajes en consola

---

## 🔧 Requisitos Previos

- **MySQL Server** 5.7 o superior (recomendado 8.0+)
- **Permisos:** Usuario con privilegios `CREATE`, `DROP`, `ALTER` en la base de datos
- **Charset:** `utf8mb4` (incluido en el script)

---

## 📝 Configuración en Nueva Máquina

### **1. Verificar Usuario de Base de Datos**

Después de importar, debes crear/configurar el usuario de aplicación:

```sql
-- Crear usuario (cambiar IP si es necesario)
CREATE USER 'app_user'@'%' IDENTIFIED BY '1234';

-- Otorgar permisos en la base de datos 'daily'
GRANT ALL PRIVILEGES ON daily.* TO 'app_user'@'%';

-- Aplicar cambios
FLUSH PRIVILEGES;
```

---

### **2. Verificar Importación Exitosa**

```sql
-- Verificar base de datos
SHOW DATABASES LIKE 'daily';

-- Verificar tablas (debe mostrar 26 tablas)
USE daily;
SHOW TABLES;

-- Verificar foreign keys de una tabla específica
SHOW CREATE TABLE eventos;
```

---

### **3. Actualizar Conexión en la Aplicación**

Editar archivo `models/database.py`:

```python
def get_connection():
    conn = pymysql.connect(
        host="TU_IP_O_LOCALHOST",  # ⬅️ CAMBIAR
        user="app_user",
        password="1234",  # ⬅️ CAMBIAR si modificaste contraseña
        database="daily",
        port=3306
    )
    return conn
```

---

## 🔄 Regenerar Exportación

Si necesitas actualizar la estructura después de cambios en la BD:

```bash
python export_database_structure.py
```

Esto generará un nuevo archivo `daily_structure.sql` con la estructura actualizada.

---

## ⚠️ Notas Importantes

### **ESTE SCRIPT NO INCLUYE DATOS**
- Solo crea la estructura de tablas
- No migra registros existentes
- Las tablas se crearán vacías

### **Migraciones de Datos (Si Necesario)**

Para exportar datos también:

```bash
# Exportar estructura + datos
mysqldump -u root -p daily > daily_full_backup.sql

# Solo datos (sin estructura)
mysqldump -u root -p --no-create-info daily > daily_data_only.sql
```

### **Foreign Keys**

El script desactiva temporalmente verificación de llaves foráneas durante importación:

```sql
SET FOREIGN_KEY_CHECKS = 0;
-- ... CREATE TABLE statements ...
SET FOREIGN_KEY_CHECKS = 1;
```

Esto evita errores de orden al crear tablas con dependencias.

---

## 🐛 Solución de Problemas

### **Error: "Database exists"**
```sql
DROP DATABASE IF EXISTS daily;
-- Luego ejecutar daily_structure.sql
```

### **Error: "Access denied"**
- Verificar permisos del usuario MySQL
- Asegurar que el usuario tenga privilegios CREATE/DROP

### **Error: "Foreign key constraint fails"**
- El script incluye `SET FOREIGN_KEY_CHECKS = 0/1`
- Si persiste, verificar que todas las tablas se crearon

### **Errores de Charset**
```sql
-- Verificar charset del servidor
SHOW VARIABLES LIKE 'character_set%';

-- Debe ser utf8mb4 o utf8
```

---

## 📊 Información Técnica

| Propiedad | Valor |
|-----------|-------|
| **Total Tablas** | 26 |
| **Engine** | InnoDB |
| **Charset** | utf8mb3 / utf8mb4 |
| **Collation** | utf8mb4_unicode_ci |
| **Foreign Keys** | ~20 relaciones |
| **Generado** | 2025-12-12 |

---

## 📞 Soporte

Si encuentras problemas durante la importación:

1. Verificar logs de MySQL: `/var/log/mysql/error.log` (Linux) o visor de eventos (Windows)
2. Revisar versión de MySQL: `SELECT VERSION();`
3. Validar permisos de usuario: `SHOW GRANTS FOR 'app_user'@'%';`

---

## 📜 Licencia

Este script es parte del proyecto Daily Log Application.
**NO incluye datos sensibles**, solo definiciones de estructura.
