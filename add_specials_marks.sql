-- Agregar columnas para sistema de marcas persistentes en specials
USE Daily;

-- Verificar si las columnas ya existen antes de agregarlas
SET @dbname = DATABASE();
SET @tablename = 'specials';

-- marked_status: 'flagged' (múltiple) o 'last' (último tratado)
SET @col_exists = (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS 
                   WHERE TABLE_SCHEMA = @dbname 
                   AND TABLE_NAME = @tablename 
                   AND COLUMN_NAME = 'marked_status');

SET @sql = IF(@col_exists = 0,
    'ALTER TABLE specials ADD COLUMN marked_status VARCHAR(20) DEFAULT NULL COMMENT "Estado de marca: flagged, last o NULL"',
    'SELECT "La columna marked_status ya existe" AS mensaje');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- marked_at: timestamp de cuando se marcó
SET @col_exists = (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS 
                   WHERE TABLE_SCHEMA = @dbname 
                   AND TABLE_NAME = @tablename 
                   AND COLUMN_NAME = 'marked_at');

SET @sql = IF(@col_exists = 0,
    'ALTER TABLE specials ADD COLUMN marked_at TIMESTAMP NULL DEFAULT NULL COMMENT "Fecha/hora de marcado"',
    'SELECT "La columna marked_at ya existe" AS mensaje');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- marked_by: usuario que marcó
SET @col_exists = (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS 
                   WHERE TABLE_SCHEMA = @dbname 
                   AND TABLE_NAME = @tablename 
                   AND COLUMN_NAME = 'marked_by');

SET @sql = IF(@col_exists = 0,
    'ALTER TABLE specials ADD COLUMN marked_by VARCHAR(100) DEFAULT NULL COMMENT "Usuario que marcó el registro"',
    'SELECT "La columna marked_by ya existe" AS mensaje');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Verificar que se agregaron correctamente
SELECT 
    COLUMN_NAME, 
    COLUMN_TYPE, 
    IS_NULLABLE, 
    COLUMN_DEFAULT,
    COLUMN_COMMENT
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = DATABASE()
AND TABLE_NAME = 'specials'
AND COLUMN_NAME IN ('marked_status', 'marked_at', 'marked_by')
ORDER BY ORDINAL_POSITION;
