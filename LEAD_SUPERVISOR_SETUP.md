# 🎯 Configuración de Lead Supervisor

## Descripción General

Se ha creado una nueva ventana híbrida específica para usuarios con rol **"Lead Supervisor"**. Esta ventana es similar a la de supervisores regulares pero con permisos adicionales de eliminación.

## ✨ Características Principales

### Lead Supervisor Window
- **Visualización**: Misma vista de Specials que supervisores
- **Botones**: 
  - 🚀 **Start Shift / 🏁 End of Shift**: Botón dinámico que cambia según el estado del turno
  - 🔄 **Refrescar**: Recarga los datos actualizados
  - 🗑️ **Eliminar**: Permite eliminar specials seleccionados (CON permisos completos)
- **Auto-logout**: Al cerrar la ventana **cierra automáticamente la ventana principal** (equivalente a logout completo)
- **Auto-redirect**: Al iniciar sesión va directamente a la ventana de Lead Supervisor
- **Gestión de turnos**: Botón Start/End Shift integrado con colores dinámicos:
  - 🟢 Verde (`#00c853`) cuando puede iniciar turno
  - 🔴 Rojo (`#d32f2f`) cuando puede finalizar turno

### SQL Actualizado
La consulta SQL ahora reconoce eventos desde el último START SHIFT del usuario:

**⚠️ IMPORTANTE**: La base de datos actual NO tiene la columna `Enviado_A_Rol` en la tabla `Eventos`, por lo que la ventana muestra **TODOS los eventos** desde el último START SHIFT, sin filtrar por rol específico.

```sql
SELECT 
    e.ID_Eventos,
    e.FechaHora,
    s.Nombre_Sitio,
    e.Nombre_Actividad,
    e.Cantidad,
    e.Camera,
    e.Descripcion,
    u.Nombre_Usuario
FROM Eventos e
LEFT JOIN Sitios s ON e.ID_Sitio = s.ID_Sitio
LEFT JOIN user u ON e.ID_Usuario = u.ID_Usuario
WHERE e.FechaHora >= %s  -- Fecha del último START SHIFT
ORDER BY e.FechaHora DESC
```

**Nota**: Si se desea filtrar eventos específicos para supervisores, será necesario agregar una columna `Enviado_A_Rol` a la tabla `Eventos` con el siguiente comando:

```sql
ALTER TABLE Eventos 
ADD COLUMN Enviado_A_Rol VARCHAR(50) NULL;
```

## 🔧 Configuración en Base de Datos

### 1. Crear el Rol en la tabla `user`
Asegúrate de que el rol "Lead Supervisor" existe en la base de datos:

```sql
-- Verificar roles existentes
SELECT DISTINCT Rol FROM user;

-- Crear usuario con rol Lead Supervisor (ejemplo)
INSERT INTO user (Nombre_Usuario, Password, Rol, Estacion, Activo)
VALUES ('nombre_lead', 'password_hash', 'Lead Supervisor', 'Station Name', 1);

-- O actualizar un usuario existente
UPDATE user 
SET Rol = 'Lead Supervisor' 
WHERE Nombre_Usuario = 'nombre_usuario';
```

### 2. Configurar Permisos en `roles_config.json`
Edita el archivo `roles_config.json` y agrega la configuración para "Lead Supervisor":

```json
{
  "Operador": [...],
  "Supervisor": [...],
  "Lead Supervisor": [
    "Lead Specials",
    "Audit",
    "Time Zone",
    "Cover Time",
    "View",
    "Report",
    "Event"
  ],
  "Administrator": [...]
}
```

**Nota**: El permiso clave es `"Lead Specials"` que abre la ventana específica de Lead Supervisor.

### 3. Verificar Tabla `Eventos`
La ventana de Lead Supervisor funciona con la estructura actual de la tabla `Eventos`:

```sql
-- Verificar estructura actual
DESCRIBE Eventos;
```

**Columnas opcionales que NO son requeridas** (pero mejorarían la funcionalidad):

1. **`Enviado_A_Rol`** (para filtrar eventos por rol):
```sql
ALTER TABLE Eventos 
ADD COLUMN Enviado_A_Rol VARCHAR(50) NULL;

-- Luego actualizar eventos existentes
UPDATE Eventos 
SET Enviado_A_Rol = 'Lead Supervisor' 
WHERE [condición apropiada];
```

2. **`Time_Zone`** (para mostrar zona horaria):
```sql
ALTER TABLE Eventos 
ADD COLUMN Time_Zone VARCHAR(50) NULL;
```

**⚠️ IMPORTANTE**: La función de Lead Supervisor NO utiliza una tabla `turno` separada. En su lugar, detecta el turno activo buscando el último evento `'START SHIFT'` del usuario en la tabla `Eventos`:

```sql
-- Así se obtiene el inicio del turno
SELECT e.FechaHora
FROM Eventos e
INNER JOIN user u ON e.ID_Usuario = u.ID_Usuario
WHERE u.Nombre_Usuario = 'username' 
  AND e.Nombre_Actividad = 'START SHIFT'
ORDER BY e.FechaHora DESC
LIMIT 1
```

Esto significa que el Lead Supervisor debe tener un evento `'START SHIFT'` registrado para que la ventana muestre datos.

## 📋 Flujo de Login

### Comportamiento Automático
Cuando un usuario con rol "Lead Supervisor" inicia sesión:

1. ✅ El sistema detecta el rol automáticamente
2. ✅ **Salta el menú principal** 
3. ✅ Abre directamente `open_hybrid_events_lead_supervisor()`
4. ✅ Muestra la ventana con título: **"👔 Lead Supervisor - Specials - {username}"**

### Código Aplicado
En `login.py` (funciones `do_login` y `auto_login`):

```python
if role == "Operador":
    backend_super.open_hybrid_events(username, session_id, station, win)
elif role == "Supervisor":
    backend_super.open_hybrid_events_supervisor(username=username, root=win)
elif role == "Lead Supervisor":
    backend_super.open_hybrid_events_lead_supervisor(username=username, root=win)
else:
    main_super.open_main_window(username, station, role, session_id)
```

## 🗑️ Permisos de Eliminación

### Lead Supervisor vs Supervisor Regular

| Característica | Supervisor | Lead Supervisor |
|----------------|------------|-----------------|
| Ver Specials | ✅ | ✅ |
| Refrescar | ✅ | ✅ |
| Start/End Shift | ✅ | ✅ |
| Marcar (Registrado/En Progreso) | ✅ | ⚠️ (Por implementar) |
| **Eliminar Specials** | ❌ | ✅ |
| Auto-logout al cerrar | ❌ | ✅ |

### Función de Eliminación
```python
def delete_selected():
    """Elimina los specials seleccionados (con permisos de Lead Supervisor)"""
    # 1. Obtener filas seleccionadas
    # 2. Confirmar con usuario
    # 3. Eliminar evento directamente (tabla Eventos)
    # 4. Recargar datos
```

**⚠️ IMPORTANTE**: La eliminación es directa sobre la tabla `Eventos`. No se eliminan marcas asociadas porque la tabla `marks` no existe en la base de datos actual.

## 🎨 Interfaz de Usuario

### Elementos Visuales
- **Título**: `👔 Lead Supervisor - Specials - {username}`
- **Header Color**: `#23272a` (gris oscuro)
- **Botones**:
  - Start Shift: `#00c853` (verde) / End of Shift: `#d32f2f` (rojo)
  - Refrescar: `#4D6068` (gris azulado)
  - Eliminar: `#d32f2f` (rojo)
- **Tema tksheet**: `dark blue`

**Layout del Header**:
```
[👔 Lead Supervisor: username]    [🗑️ Eliminar] [🔄 Refrescar] [🚀 Start Shift]
```

### Columnas Mostradas
1. **ID**: ID del evento
2. **FechaHora**: Fecha y hora del evento
3. **Sitio**: Nombre del sitio
4. **Actividad**: Tipo de actividad
5. **Cantidad**: Cantidad registrada
6. **Camera**: Cámara utilizada
7. **Descripcion**: Descripción del evento
8. **Usuario**: Usuario que registró
9. **TZ**: Time Zone (vacío - columna no existe en BD)
10. **Marca**: Estado (siempre "Sin Marca" - tabla marks no existe)

### Colores de Marcas
- **Sin Marca**: Color por defecto del tema (sin coloreo especial)
- **Nota**: La tabla `marks` no existe en la base de datos actual, por lo que todas las filas muestran "Sin Marca" y no tienen colores especiales aplicados.

## 📂 Archivos Modificados

### 1. `backend_super.py`
- ✅ Nueva función: `open_hybrid_events_lead_supervisor(username, root=None)`
- ✅ SQL simplificado: **NO requiere columnas `Enviado_A_Rol`, `Time_Zone`, ni tabla `marks`**
- ✅ Muestra todos los eventos desde el último START SHIFT del usuario
- ✅ Función `delete_selected()` elimina directamente de `Eventos`
- ✅ Handler `on_close()` simplificado
- ✅ Botones Start/End Shift integrados con funciones dinámicas

### 2. `login.py`
- ✅ Detección de rol "Lead Supervisor" en `do_login()`
- ✅ Detección de rol "Lead Supervisor" en `auto_login()`
- ✅ Auto-redirect directo a ventana Lead Supervisor

### 3. `main_super.py`
- ✅ Nuevo botón: `"Lead Specials"` con permiso `"Lead Specials"`
- ✅ Ícono mapeado: Usa mismo ícono que "Specials" (`specials.png`)
- ✅ Comando: `backend_super.open_hybrid_events_lead_supervisor(username=username, root=root)`

## 🧪 Testing

### Pruebas Recomendadas

1. **Login con Lead Supervisor**
   ```
   - Usuario con rol "Lead Supervisor" debe ir directo a ventana
   - Verificar que título muestre "👔 Lead Supervisor"
   - Verificar que botones Refrescar y Eliminar estén visibles
   ```

2. **Visualización de Specials**
   ```
   - Verificar que se carguen specials con Enviado_A_Rol = 'Lead Supervisor'
   - Verificar que también se carguen specials con Enviado_A_Rol = 'Supervisor'
   - Verificar colores de marcas
   ```

3. **Eliminación de Specials**
   ```
   - Seleccionar 1 special → Eliminar → Confirmar → Verificar eliminación
   - Seleccionar múltiples → Eliminar → Verificar eliminación en lote
   - Verificar que se eliminen marcas asociadas
   ```

4. **Cerrar Ventana**
   ```
   - Cerrar ventana con X → Verificar que SE ejecute logout cerrando ventana principal
   - Verificar que ambas ventanas se cierren correctamente
   - Verificar que regrese a pantalla de login
   ```

## ⚠️ Notas Importantes

1. **Columna `Enviado_A_Rol` no existe**: La tabla `Eventos` NO tiene esta columna, por lo que:
   - Se muestran **TODOS los eventos** desde el último START SHIFT
   - NO hay filtrado por rol específico (Supervisor/Lead Supervisor)
   - Para agregar filtrado por rol, se debe crear la columna en la BD

2. **Tabla `marks` no existe**: La base de datos actual no tiene la tabla `marks`, por lo que:
   - Todas las filas muestran "Sin Marca" en la columna de Marca
   - No hay colores especiales aplicados a las filas
   - La funcionalidad de marcado NO está disponible para Lead Supervisors
   - La eliminación es directa sobre `Eventos` (sin eliminar marcas)

3. **Columna `Time_Zone` no existe**: La tabla `Eventos` no tiene columna `Time_Zone`, por lo que:
   - La columna TZ siempre está vacía
   - No se muestra información de zona horaria para los eventos
4. **Detección de turno**: Se usa la tabla `Eventos` para detectar el último `'START SHIFT'` en lugar de una tabla `turno` separada.

5. **Auto-logout implementado**: El handler `on_close()` ahora **cierra la ventana principal (root)** cuando se cierra la ventana de Lead Supervisor, ejecutando un logout completo del sistema. El flujo es:
   - Usuario cierra ventana Lead Supervisor (X)
   - Se ejecuta `on_close()`
   - Se cierra la ventana del Lead Supervisor
   - Se cierra la ventana principal (`root.destroy()`)
   - Sistema regresa a pantalla de login

6. **Singleton Window**: Solo se permite una ventana de Lead Supervisor abierta a la vez (patrón singleton).
6. **Singleton Window**: Solo se permite una ventana de Lead Supervisor abierta a la vez (patrón singleton).

7. **Compatibilidad**: La función está diseñada para trabajar con o sin CustomTkinter (fallback a Tkinter estándar).

## 🔄 Próximos Pasos (Opcional)

- [ ] Implementar funcionalidad de marcado (Registrado/En Progreso) para Lead Supervisors
- [ ] Agregar modo Audit y Cover Time (similar a Supervisor regular)
- [ ] Implementar auto-logout completo al cerrar ventana
- [ ] Agregar estadísticas en tiempo real
- [ ] Implementar filtros personalizados

## 📞 Soporte

Si encuentras errores o necesitas agregar funcionalidades:
1. Verificar logs en consola con `[DEBUG]`, `[INFO]`, `[ERROR]`
2. Revisar tabla `Eventos` para confirmar campo `Enviado_A_Rol`
3. Verificar `roles_config.json` tenga permiso `"Lead Specials"`
4. Confirmar que usuario tenga rol exacto: `"Lead Supervisor"` (case-sensitive)

---

**Fecha de Creación**: 2025-01-11  
**Versión**: 1.0  
**Estado**: ✅ Implementado y Funcional
