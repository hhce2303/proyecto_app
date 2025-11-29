-- ============================================================================
-- Script Rápido para Arreglar Foreign Keys (Papelera)
-- ============================================================================
-- Este script elimina y recrea las Foreign Keys con ON DELETE SET NULL
-- Ejecutar en MySQL Workbench conectado a la BD 'Daily'
-- ============================================================================

USE Daily;

-- ============================================================================
-- PASO 1: Asegurar que columnas FK acepten NULL
-- ============================================================================
ALTER TABLE Eventos MODIFY COLUMN ID_Sitio INT NULL;
ALTER TABLE Eventos MODIFY COLUMN ID_Usuario INT NULL;
ALTER TABLE Eventos MODIFY COLUMN Nombre_Actividad VARCHAR(100) NULL;

ALTER TABLE Covers MODIFY COLUMN Nombre_Usuarios INT NULL;
ALTER TABLE Covers MODIFY COLUMN Covered_by INT NULL;

ALTER TABLE Sesiones MODIFY COLUMN Nombre_Usuario INT NULL;

ALTER TABLE specials MODIFY COLUMN ID_Sitio INT NULL;
ALTER TABLE specials MODIFY COLUMN Usuario INT NULL;
ALTER TABLE specials MODIFY COLUMN Supervisor INT NULL;
ALTER TABLE specials MODIFY COLUMN Nombre_Actividad VARCHAR(100) NULL;

-- ============================================================================
-- PASO 2: Eliminar Foreign Keys existentes
-- ============================================================================

-- Eventos
ALTER TABLE eventos DROP FOREIGN KEY eventos_ibfk_1;
ALTER TABLE eventos DROP FOREIGN KEY eventos_ibfk_2;
ALTER TABLE eventos DROP FOREIGN KEY eventos_ibfk_3;

-- Covers  
ALTER TABLE covers DROP FOREIGN KEY covers_ibfk_1;
ALTER TABLE covers DROP FOREIGN KEY covers_ibfk_2;

-- Sesiones
ALTER TABLE sesiones DROP FOREIGN KEY sesiones_ibfk_1;

-- specials
ALTER TABLE specials DROP FOREIGN KEY specials_ibfk_1;
ALTER TABLE specials DROP FOREIGN KEY specials_ibfk_2;
ALTER TABLE specials DROP FOREIGN KEY specials_ibfk_3;
ALTER TABLE specials DROP FOREIGN KEY specials_ibfk_4;

-- ============================================================================
-- PASO 3: Recrear Foreign Keys con ON DELETE SET NULL
-- ============================================================================

-- Eventos
ALTER TABLE eventos
  ADD CONSTRAINT eventos_ibfk_1
  FOREIGN KEY (ID_Sitio) REFERENCES sitios(ID_Sitio)
  ON DELETE SET NULL ON UPDATE CASCADE;

ALTER TABLE eventos
  ADD CONSTRAINT eventos_ibfk_2
  FOREIGN KEY (ID_Usuario) REFERENCES user(ID_Usuario)
  ON DELETE SET NULL ON UPDATE CASCADE;

ALTER TABLE eventos
  ADD CONSTRAINT eventos_ibfk_3
  FOREIGN KEY (Nombre_Actividad) REFERENCES actividades(ID_Actividad)
  ON DELETE SET NULL ON UPDATE CASCADE;

-- Covers
ALTER TABLE covers
  ADD CONSTRAINT covers_ibfk_1
  FOREIGN KEY (Nombre_Usuarios) REFERENCES user(ID_Usuario)
  ON DELETE SET NULL ON UPDATE CASCADE;

ALTER TABLE covers
  ADD CONSTRAINT covers_ibfk_2
  FOREIGN KEY (Covered_by) REFERENCES user(ID_Usuario)
  ON DELETE SET NULL ON UPDATE CASCADE;

-- Sesiones
ALTER TABLE sesiones
  ADD CONSTRAINT sesiones_ibfk_1
  FOREIGN KEY (Nombre_Usuario) REFERENCES user(ID_Usuario)
  ON DELETE SET NULL ON UPDATE CASCADE;

-- specials
ALTER TABLE specials
  ADD CONSTRAINT specials_ibfk_1
  FOREIGN KEY (ID_Sitio) REFERENCES sitios(ID_Sitio)
  ON DELETE SET NULL ON UPDATE CASCADE;

ALTER TABLE specials
  ADD CONSTRAINT specials_ibfk_2
  FOREIGN KEY (Nombre_Actividad) REFERENCES actividades(ID_Actividad)
  ON DELETE SET NULL ON UPDATE CASCADE;

ALTER TABLE specials
  ADD CONSTRAINT specials_ibfk_3
  FOREIGN KEY (Usuario) REFERENCES user(ID_Usuario)
  ON DELETE SET NULL ON UPDATE CASCADE;

ALTER TABLE specials
  ADD CONSTRAINT specials_ibfk_4
  FOREIGN KEY (Supervisor) REFERENCES user(ID_Usuario)
  ON DELETE SET NULL ON UPDATE CASCADE;

-- ============================================================================
-- VERIFICACIÓN
-- ============================================================================
SELECT 
    kcu.TABLE_NAME,
    kcu.COLUMN_NAME,
    kcu.CONSTRAINT_NAME,
    rc.DELETE_RULE,
    kcu.REFERENCED_TABLE_NAME
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
-- Deberías ver DELETE_RULE = 'SET NULL' para todas las FKs
-- ============================================================================
