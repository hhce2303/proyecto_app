-- Migration: Replace usage of Eventos.Nombre_Sitio with Eventos.ID_Sitio (foreign key to Sitios)
-- MySQL-safe script. Review and run step by step if needed.

START TRANSACTION;

-- 1) Add ID_Sitio column to Eventos if it doesn't exist
-- If your MySQL supports IF NOT EXISTS (8.0+):
ALTER TABLE `Eventos` ADD COLUMN IF NOT EXISTS `ID_Sitio` INT NULL;

-- If your server doesn't support IF NOT EXISTS, comment the above and use:
-- -- Check manually whether the column exists before running this (SHOW COLUMNS FROM Eventos LIKE 'ID_Sitio';)
-- ALTER TABLE `Eventos` ADD COLUMN `ID_Sitio` INT NULL;

-- 2) Populate ID_Sitio based on existing textual Nombre_Sitio values in Eventos
-- Adjust collation/trim if you have trailing spaces or different case sensitivity.
UPDATE `Eventos` e
JOIN `Sitios` s ON TRIM(e.`Nombre_Sitio`) = TRIM(s.`Nombre_Sitio`)
SET e.`ID_Sitio` = s.`ID_Sitio`
WHERE (e.`ID_Sitio` IS NULL OR e.`ID_Sitio` = 0);

-- 3) Audit any rows that could not be mapped
SELECT e.`Nombre_Sitio` AS unmapped_site, COUNT(*) AS rows_unmapped
FROM `Eventos` e
LEFT JOIN `Sitios` s ON TRIM(e.`Nombre_Sitio`) = TRIM(s.`Nombre_Sitio`)
WHERE s.`ID_Sitio` IS NULL
GROUP BY e.`Nombre_Sitio`;

-- 4) (Optional) Enforce NOT NULL now that data is populated (do this only when no unmapped rows remain)
-- ALTER TABLE `Eventos` MODIFY `ID_Sitio` INT NOT NULL;

-- 5) (Optional) Add a foreign key constraint to keep referential integrity
-- ALTER TABLE `Eventos`
--   ADD CONSTRAINT `fk_eventos_sitios`
--   FOREIGN KEY (`ID_Sitio`) REFERENCES `Sitios`(`ID_Sitio`)
--   ON UPDATE CASCADE ON DELETE RESTRICT;

-- 6) (Optional) Drop the old textual column once you're sure all code uses ID_Sitio
-- ALTER TABLE `Eventos` DROP COLUMN `Nombre_Sitio`;

COMMIT;

-- Notes:
-- - The app code already uses Eventos.ID_Sitio and joins Sitios to display Nombre_Sitio.
-- - If you keep filters by site name, they should be done via JOIN Sitios and WHERE s.Nombre_Sitio LIKE ...
