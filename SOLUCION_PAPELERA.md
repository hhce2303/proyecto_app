# 🚨 SOLUCIÓN AL PROBLEMA: Registros no se insertan en Papelera

## 📋 Diagnóstico Realizado

✅ Las tablas `*_deleted` **SÍ están creadas**
✅ Las columnas de auditoría **SÍ existen** (`deleted_at`, `deleted_by`, `deletion_reason`)
✅ Las funciones de Python **SÍ están disponibles** (`safe_delete`, `restore_deleted`)

❌ **PROBLEMA ENCONTRADO:** Las Foreign Keys tienen `ON DELETE NO ACTION`
❌ Esto **impide** que el DELETE funcione en `safe_delete()`

---

## 🔧 SOLUCIÓN RÁPIDA (3 opciones)

### Opción 1: Script Python Automático (⚡ MÁS FÁCIL)

1. Ejecuta el script:
   ```powershell
   python fix_foreign_keys.py
   ```

2. Cuando pregunte "¿Deseas continuar?", escribe: **si**

3. El script automáticamente:
   - ✅ Modifica columnas para aceptar NULL
   - ✅ Elimina Foreign Keys antiguas
   - ✅ Crea nuevas con `ON DELETE SET NULL`
   - ✅ Verifica que todo esté correcto

4. ¡Listo! Ya puedes usar la Papelera

---

### Opción 2: Ejecutar SQL Manual (MySQL Workbench)

1. Abre **MySQL Workbench**
2. Conecta a tu servidor MySQL
3. Abre el archivo: `Other_Scripts/fix_foreign_keys_quick.sql`
4. Ejecuta todo el script (⚡ botón o Ctrl+Shift+Enter)
5. Verifica que la última consulta muestre `DELETE_RULE = 'SET NULL'`

---

### Opción 3: Eliminar Foreign Keys Completamente (temporal)

Si solo quieres probar rápidamente la Papelera sin Foreign Keys:

```sql
USE Daily;

-- Eliminar todas las Foreign Keys
ALTER TABLE eventos DROP FOREIGN KEY eventos_ibfk_1;
ALTER TABLE eventos DROP FOREIGN KEY eventos_ibfk_2;
ALTER TABLE eventos DROP FOREIGN KEY eventos_ibfk_3;
ALTER TABLE covers DROP FOREIGN KEY covers_ibfk_1;
ALTER TABLE covers DROP FOREIGN KEY covers_ibfk_2;
ALTER TABLE sesiones DROP FOREIGN KEY sesiones_ibfk_1;
ALTER TABLE specials DROP FOREIGN KEY specials_ibfk_1;
ALTER TABLE specials DROP FOREIGN KEY specials_ibfk_2;
ALTER TABLE specials DROP FOREIGN KEY specials_ibfk_3;
ALTER TABLE specials DROP FOREIGN KEY specials_ibfk_4;
```

⚠️ **Advertencia:** Sin Foreign Keys pierdes integridad referencial

---

## 🧪 Prueba que Funciona

Después de ejecutar cualquiera de las opciones:

1. **Ejecuta el diagnóstico:**
   ```powershell
   python check_papelera_system.py
   ```

2. **Deberías ver:**
   ```
   ✅ eventos.ID_Sitio → sitios (ON DELETE SET NULL)
   ✅ eventos.ID_Usuario → user (ON DELETE SET NULL)
   ✅ covers.Nombre_Usuarios → user (ON DELETE SET NULL)
   ...
   ```

3. **Prueba borrar un registro:**
   - Abre la aplicación
   - Ve a "Eventos"
   - Selecciona un registro
   - Haz clic en "Eliminar"
   - Confirma

4. **Verifica que se movió a Papelera:**
   ```sql
   SELECT * FROM Eventos_deleted ORDER BY deleted_at DESC LIMIT 5;
   ```

   Deberías ver el registro con:
   - ✅ `deleted_at` con fecha/hora actual
   - ✅ `deleted_by` con tu nombre de usuario
   - ✅ `deletion_reason` = "Eliminado desde show_events"

---

## ❓ Por Qué Pasa Esto

Cuando intentas ejecutar `safe_delete()`:

```python
# 1. INSERT funciona (copia a *_deleted)
INSERT INTO Eventos_deleted SELECT *, NOW(), user, reason FROM Eventos WHERE ID = 123;  ✅

# 2. DELETE falla por Foreign Keys
DELETE FROM Eventos WHERE ID = 123;  ❌ Error: Cannot delete parent row
```

**El error específico sería:**
```
Cannot delete or update a parent row: a foreign key constraint fails
```

Con `ON DELETE SET NULL`, cuando borras un registro:
- Se borra de `Eventos` ✅
- Las columnas FK que apuntaban a él se ponen NULL ✅
- No hay error de integridad ✅

---

## 🎯 Recomendación

**Usa la Opción 1 (Script Python)** porque:
- ✅ Es automático
- ✅ Muestra progreso en tiempo real
- ✅ Verifica que todo quedó bien
- ✅ Puedes ver exactamente qué pasó
- ✅ Maneja errores automáticamente

Para ejecutarlo:
```powershell
python fix_foreign_keys.py
```

Y cuando pregunte, escribe: **si**

---

## 📞 Si Algo Sale Mal

Si el script falla o da errores:

1. **Copia el mensaje de error completo**
2. **Ejecuta este SQL para ver las FKs actuales:**
   ```sql
   SELECT 
       kcu.TABLE_NAME,
       kcu.COLUMN_NAME,
       kcu.CONSTRAINT_NAME,
       rc.DELETE_RULE
   FROM
       INFORMATION_SCHEMA.KEY_COLUMN_USAGE kcu
       LEFT JOIN INFORMATION_SCHEMA.REFERENTIAL_CONSTRAINTS rc
         ON kcu.CONSTRAINT_NAME = rc.CONSTRAINT_NAME
         AND kcu.CONSTRAINT_SCHEMA = rc.CONSTRAINT_SCHEMA
   WHERE
       kcu.TABLE_SCHEMA = 'Daily'
       AND kcu.TABLE_NAME IN ('eventos', 'covers', 'sesiones', 'specials')
       AND kcu.REFERENCED_TABLE_NAME IS NOT NULL;
   ```

3. **Los nombres de constraints pueden ser diferentes** (no siempre `eventos_ibfk_1`)
4. Si el script da error en DROP FOREIGN KEY, reemplaza el nombre del constraint con el que muestre la consulta arriba

---

## ✅ Después de la Configuración

Una vez que las Foreign Keys estén configuradas:

1. ✅ Los borrados funcionarán correctamente
2. ✅ Los registros se moverán a `*_deleted` automáticamente
3. ✅ Podrás restaurar desde la Papelera
4. ✅ Tendrás auditoría completa de todos los borrados

**No necesitas volver a hacer esto**, es configuración **UNA SOLA VEZ**.

---

**Última actualización:** Noviembre 5, 2025
