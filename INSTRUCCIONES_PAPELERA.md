# 📋 Instrucciones para Configurar el Sistema de Papelera

## ✅ Sistema Implementado

El sistema de Papelera (soft-delete) ha sido completamente integrado en tu aplicación Daily Log. Este sistema permite:

- ♻️ **Mover registros a papelera** en vez de borrarlos permanentemente
- 🔄 **Restaurar registros** borrados accidentalmente
- 🗑️ **Eliminar permanentemente** cuando sea necesario
- 📊 **Auditoría completa** (quién borró, cuándo, por qué)

---

## 🔧 Configuración Requerida

### Paso 1: Ejecutar Script SQL de Preparación

**IMPORTANTE:** Antes de usar el sistema de Papelera, debes ejecutar el script SQL para configurar las Foreign Keys.

#### Ubicación del script:
```
Other_Scripts/prepare_papelera_system.sql
```

#### Cómo ejecutarlo:

**Opción A - Desde MySQL Workbench:**
1. Abre MySQL Workbench
2. Conecta a tu servidor MySQL
3. Abre el archivo `prepare_papelera_system.sql`
4. Ejecuta el script completo (botón ⚡ o Ctrl+Shift+Enter)

**Opción B - Desde línea de comandos:**
```bash
mysql -u root -p Daily < "Other_Scripts/prepare_papelera_system.sql"
```

**Opción C - Desde Python (si prefieres):**
```python
import mysql.connector
import under_super

conn = under_super.get_connection()
cur = conn.cursor()

# Leer y ejecutar el script
with open('Other_Scripts/prepare_papelera_system.sql', 'r') as f:
    script = f.read()
    # Ejecutar cada statement
    for statement in script.split(';'):
        if statement.strip():
            cur.execute(statement)
conn.commit()
```

---

### Paso 2: Verificar Foreign Keys

Después de ejecutar el script, verifica que las Foreign Keys estén configuradas correctamente:

```sql
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
```

Deberías ver:
- `DELETE_RULE = 'SET NULL'` para todas las FKs
- Esto permite borrar registros sin errores de integridad

---

### Paso 3: Agregar Permiso de Papelera a Roles

Edita tu archivo `roles_config.json` para dar acceso a la Papelera:

```json
{
  "Admin": [
    "Register", 
    "Event", 
    "Report", 
    "Cover", 
    "Extra", 
    "Rol", 
    "View", 
    "Map", 
    "Specials", 
    "Audit", 
    "Time Zone", 
    "Cover Time", 
    "Papelera"
  ],
  "Supervisor": [
    "Register", 
    "Event", 
    "Report", 
    "Cover", 
    "Papelera"
  ],
  "User": [
    "Register", 
    "Event"
  ]
}
```

---

## 🎯 Cómo Usar el Sistema

### Borrar un Registro (Mover a Papelera)

1. Abre **Eventos** o **View**
2. Selecciona el registro a borrar
3. Haz clic en **Eliminar** o **Delete**
4. Confirma con **Sí**
5. El registro se mueve a la papelera automáticamente

**Nota:** El mensaje de confirmación ahora dice "¿Mover registro a Papelera?" en vez de "¿Eliminar registro?"

### Restaurar un Registro

1. Abre **Papelera** desde el menú principal
2. Selecciona la tabla (ej: `Eventos_deleted`)
3. Selecciona el registro a restaurar
4. Haz clic en **♻️ Restaurar**
5. Confirma con **Sí**
6. El registro vuelve a su tabla original

### Eliminar Permanentemente

⚠️ **PRECAUCIÓN: Esta acción es IRREVERSIBLE**

1. Abre **Papelera**
2. Selecciona el registro
3. Haz clic en **🗑️ Eliminar Permanente**
4. Confirma dos veces
5. El registro se borra permanentemente de la base de datos

---

## 📊 Tablas Creadas Automáticamente

Al iniciar la aplicación, se crean estas tablas de respaldo:

| Tabla Original | Tabla de Respaldo | Columnas Adicionales |
|---------------|-------------------|---------------------|
| `Eventos` | `Eventos_deleted` | `deleted_at`, `deleted_by`, `deletion_reason` |
| `Covers` | `Covers_deleted` | `deleted_at`, `deleted_by`, `deletion_reason` |
| `Sesiones` | `Sesiones_deleted` | `deleted_at`, `deleted_by`, `deletion_reason` |
| `Estaciones` | `Estaciones_deleted` | `deleted_at`, `deleted_by`, `deletion_reason` |
| `specials` | `specials_deleted` | `deleted_at`, `deleted_by`, `deletion_reason` |

---

## 🔍 Consultas SQL Útiles

### Ver todos los registros borrados
```sql
SELECT * FROM Eventos_deleted ORDER BY deleted_at DESC LIMIT 100;
```

### Ver quién ha borrado más registros
```sql
SELECT 
    deleted_by, 
    COUNT(*) as total_borrados
FROM Eventos_deleted 
GROUP BY deleted_by 
ORDER BY total_borrados DESC;
```

### Ver registros borrados hoy
```sql
SELECT * FROM Eventos_deleted 
WHERE DATE(deleted_at) = CURDATE();
```

### Restaurar manualmente un registro específico
```sql
-- 1. Copiar a tabla original
INSERT INTO Eventos 
SELECT 
    ID_Eventos, FechaHora, ID_Sitio, Nombre_Actividad, 
    Cantidad, Camera, Descripcion, ID_Usuario
FROM Eventos_deleted 
WHERE ID_Eventos = 12345;

-- 2. Borrar de papelera
DELETE FROM Eventos_deleted WHERE ID_Eventos = 12345;
```

---

## ⚙️ Opciones de Configuración

### Si NO quieres Foreign Keys (Opción 1 del script)

Descomentar las líneas de `DROP FOREIGN KEY` en el script:

```sql
ALTER TABLE Eventos DROP FOREIGN KEY IF EXISTS fk_eventos_sitio;
ALTER TABLE Eventos DROP FOREIGN KEY IF EXISTS fk_eventos_usuario;
-- etc...
```

**Ventajas:**
- No hay restricciones de integridad
- Borrados más rápidos

**Desventajas:**
- Puedes tener registros huérfanos
- No hay validación automática

### Si quieres Foreign Keys con SET NULL (Opción 2 - RECOMENDADO)

Mantener las secciones de `ADD CONSTRAINT ... ON DELETE SET NULL`:

```sql
ALTER TABLE Eventos
  ADD CONSTRAINT fk_eventos_sitio
  FOREIGN KEY (ID_Sitio) REFERENCES Sitios(ID_Sitio)
  ON DELETE SET NULL ON UPDATE CASCADE;
```

**Ventajas:**
- Mantiene integridad básica
- Permite borrados sin errores
- Los campos FK se ponen NULL automáticamente

**Desventajas:**
- Necesitas que las columnas FK acepten NULL

---

## 🐛 Troubleshooting

### Error: "Cannot delete or update a parent row"

**Causa:** Foreign Keys configuradas con `ON DELETE RESTRICT`

**Solución:** Ejecutar el script `prepare_papelera_system.sql`

### Error: "Column cannot be null"

**Causa:** Columnas FK no aceptan NULL

**Solución:** Ejecutar las líneas `MODIFY COLUMN` del script

### No veo el botón de Papelera

**Causa:** Tu rol no tiene el permiso "Papelera"

**Solución:** Agregar "Papelera" a tu rol en `roles_config.json`

### Los registros restaurados tienen FK = NULL

**Comportamiento esperado:** Al borrar con `ON DELETE SET NULL`, las FKs se ponen NULL. Al restaurar, el registro vuelve con esos campos NULL.

**Solución:** Editar manualmente las FKs después de restaurar, o restaurar también los registros relacionados.

---

## 📝 Notas Técnicas

### Flujo de safe_delete()

1. Conectar a MySQL
2. Iniciar transacción
3. `INSERT INTO tabla_deleted SELECT *, NOW(), user, reason FROM tabla WHERE pk = value`
4. `DELETE FROM tabla WHERE pk = value`
5. Commit
6. Si hay error, Rollback

### Flujo de restore_deleted()

1. Conectar a MySQL
2. Iniciar transacción
3. Obtener columnas de tabla original (sin `deleted_at`, etc.)
4. `INSERT INTO tabla SELECT [cols] FROM tabla_deleted WHERE pk = value`
5. `DELETE FROM tabla_deleted WHERE pk = value`
6. Commit
7. Si hay error, Rollback

### Seguridad

- ✅ Todas las operaciones usan transacciones
- ✅ Todas las consultas usan parámetros preparados (sin SQL injection)
- ✅ Los errores se registran en consola
- ✅ Los borrados requieren confirmación del usuario

---

## 📞 Soporte

Si encuentras algún problema:

1. Revisa la consola de Python para mensajes de error
2. Verifica que el script SQL se ejecutó correctamente
3. Confirma que tu rol tiene el permiso "Papelera"
4. Verifica que las tablas `*_deleted` existen en la BD

---

## 🎉 ¡Todo Listo!

El sistema de Papelera está completamente funcional. Recuerda:

- ♻️ Los borrados ahora son **reversibles**
- 📊 Tienes **auditoría completa** de todos los borrados
- 🔒 Los registros se **preservan** hasta que decidas eliminarlos permanentemente
- ⚡ Todo funciona **automáticamente** después de la configuración inicial

---

**Última actualización:** Noviembre 2025
**Versión:** Daily Log BETA 2.2+
