-- ============================================================================
-- Script para preparar la base de datos para el Sistema de Papelera
-- ============================================================================
-- Este script configura las restricciones de Foreign Keys para permitir
-- el sistema de soft-delete (Papelera) sin errores.
--
-- EJECUTAR ESTE SCRIPT ANTES DE USAR LA FUNCIÓN safe_delete()
-- ============================================================================

USE Daily;

-- ============================================================================
-- OPCIÓN 1: ELIMINAR FOREIGN KEYS (Más flexible para Papelera)
-- ============================================================================
-- Esta opción elimina las restricciones de FK para permitir borrados libres
-- Solo descomenta si NO necesitas integridad referencial estricta

-- Eventos
-- ALTER TABLE Eventos DROP FOREIGN KEY IF EXISTS fk_eventos_sitio;
-- ALTER TABLE Eventos DROP FOREIGN KEY IF EXISTS fk_eventos_usuario;
-- ALTER TABLE Eventos DROP FOREIGN KEY IF EXISTS fk_eventos_actividad;

-- Covers
-- ALTER TABLE Covers DROP FOREIGN KEY IF EXISTS fk_covers_usuario;
-- ALTER TABLE Covers DROP FOREIGN KEY IF EXISTS fk_covers_motivo;

-- Sesiones
-- ALTER TABLE Sesiones DROP FOREIGN KEY IF EXISTS fk_sesiones_usuario;
-- ALTER TABLE Sesiones DROP FOREIGN KEY IF EXISTS fk_sesiones_estacion;

-- specials
-- ALTER TABLE specials DROP FOREIGN KEY IF EXISTS fk_specials_sitio;


-- ============================================================================
-- OPCIÓN 2: CAMBIAR A ON DELETE SET NULL (Recomendado)
-- ============================================================================
-- Esta opción mantiene integridad pero permite borrados sin errores
-- Los campos FK se pondrán NULL cuando se borre el registro padre

-- Primero, asegurarse que las columnas FK acepten NULL
ALTER TABLE Eventos MODIFY COLUMN ID_Sitio INT NULL;
ALTER TABLE Eventos MODIFY COLUMN ID_Usuario INT NULL;
ALTER TABLE Eventos MODIFY COLUMN Nombre_Actividad VARCHAR(100) NULL;

ALTER TABLE Covers MODIFY COLUMN Nombre_Usuarios VARCHAR(100) NULL;
ALTER TABLE Covers MODIFY COLUMN Motivo VARCHAR(100) NULL;

ALTER TABLE Sesiones MODIFY COLUMN Nombre_Usuario VARCHAR(100) NULL;
ALTER TABLE Sesiones MODIFY COLUMN Station_Number INT NULL;

ALTER TABLE specials MODIFY COLUMN ID_Sitio INT NULL;

-- Luego, eliminar las FK existentes (si existen) y recrear con ON DELETE SET NULL
-- Eventos
ALTER TABLE Eventos DROP FOREIGN KEY IF EXISTS fk_eventos_sitio;
ALTER TABLE Eventos DROP FOREIGN KEY IF EXISTS fk_eventos_usuario;
ALTER TABLE Eventos DROP FOREIGN KEY IF EXISTS fk_eventos_actividad;

-- Covers
ALTER TABLE Covers DROP FOREIGN KEY IF EXISTS fk_covers_usuario;
ALTER TABLE Covers DROP FOREIGN KEY IF EXISTS fk_covers_motivo;

-- Sesiones
ALTER TABLE Sesiones DROP FOREIGN KEY IF EXISTS fk_sesiones_usuario;
ALTER TABLE Sesiones DROP FOREIGN KEY IF EXISTS fk_sesiones_estacion;

-- specials
ALTER TABLE specials DROP FOREIGN KEY IF EXISTS fk_specials_sitio;


-- Recrear con ON DELETE SET NULL
-- Eventos
ALTER TABLE Eventos
  ADD CONSTRAINT fk_eventos_sitio
  FOREIGN KEY (ID_Sitio) REFERENCES Sitios(ID_Sitio)
  ON DELETE SET NULL ON UPDATE CASCADE;

ALTER TABLE Eventos
  ADD CONSTRAINT fk_eventos_usuario
  FOREIGN KEY (ID_Usuario) REFERENCES user(ID_Usuario)
  ON DELETE SET NULL ON UPDATE CASCADE;

-- Covers
ALTER TABLE Covers
  ADD CONSTRAINT fk_covers_usuario
  FOREIGN KEY (Nombre_Usuarios) REFERENCES user(ID_Usuario)
  ON DELETE SET NULL ON UPDATE CASCADE;

-- Sesiones
ALTER TABLE Sesiones
  ADD CONSTRAINT fk_sesiones_usuario
  FOREIGN KEY (Nombre_Usuario) REFERENCES user(ID_Usuario)
  ON DELETE SET NULL ON UPDATE CASCADE;

ALTER TABLE Sesiones
  ADD CONSTRAINT fk_sesiones_estacion
  FOREIGN KEY (Station_Number) REFERENCES Estaciones(Station_Number)
  ON DELETE SET NULL ON UPDATE CASCADE;

-- specials
ALTER TABLE specials
  ADD CONSTRAINT fk_specials_sitio
  FOREIGN KEY (ID_Sitio) REFERENCES Sitios(ID_Sitio)
  ON DELETE SET NULL ON UPDATE CASCADE;


-- ============================================================================
-- VERIFICACIÓN: Ver las Foreign Keys actuales
-- ============================================================================
SELECT 
    kcu.TABLE_NAME,
    kcu.COLUMN_NAME,
    kcu.CONSTRAINT_NAME,
    kcu.REFERENCED_TABLE_NAME,
    kcu.REFERENCED_COLUMN_NAME,
    rc.DELETE_RULE
FROM
    INFORMATION_SCHEMA.KEY_COLUMN_USAGE kcu
    LEFT JOIN INFORMATION_SCHEMA.REFERENTIAL_CONSTRAINTS rc
      ON kcu.CONSTRAINT_NAME = rc.CONSTRAINT_NAME
      AND kcu.CONSTRAINT_SCHEMA = rc.CONSTRAINT_SCHEMA
WHERE
    kcu.TABLE_SCHEMA = 'Daily'
    AND kcu.CONSTRAINT_NAME != 'PRIMARY'
    AND kcu.REFERENCED_TABLE_NAME IS NOT NULL
ORDER BY kcu.TABLE_NAME, kcu.COLUMN_NAME;


-- ============================================================================
-- NOTAS IMPORTANTES
-- ============================================================================
-- 1. El sistema de Papelera funciona moviendo registros a tablas *_deleted
-- 2. Al restaurar, el registro vuelve a la tabla original
-- 3. Si usas ON DELETE SET NULL, los registros relacionados tendrán FK = NULL
--    después del borrado (esto es reversible al restaurar)
-- 4. Si eliminas las FK completamente (Opción 1), no habrá validación de
--    integridad referencial
-- 5. Recomendación: Usar Opción 2 (ON DELETE SET NULL) para balance entre
--    flexibilidad e integridad
-- ============================================================================
