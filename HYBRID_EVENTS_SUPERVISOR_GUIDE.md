# 👨‍💼 Guía: Hybrid Events para Supervisores

## 📝 Descripción

`open_hybrid_events_supervisor()` es una versión especializada de la ventana híbrida diseñada específicamente para **supervisores**. Muestra únicamente los **Specials** que han sido enviados al supervisor, permitiendo visualizarlos, marcarlos y gestionarlos sin necesidad de registrar eventos nuevos.

## 🆚 Diferencias con `open_hybrid_events` (Operadores)

| Característica | Operadores | Supervisores |
|----------------|-----------|--------------|
| **Formulario de registro** | ✅ Sí | ❌ No |
| **Botón Cover** | ✅ Sí | ❌ No |
| **Botón Start/End Shift** | ✅ Sí | ✅ Sí |
| **Botón Refrescar** | ✅ Sí | ✅ Sí |
| **Botón Eliminar** | ✅ Sí | ✅ Sí |
| **Modos (Daily/Specials/Covers)** | ✅ 3 modos | ❌ Solo Specials |
| **Edición de celdas** | ✅ Sí (Daily) | ❌ No (solo lectura) |
| **Marcas (Registrado/En Progreso)** | ❌ No | ✅ Sí |
| **Auto-refresh** | ❌ No | ✅ Sí (2 min) |
| **Menú contextual** | ❌ No | ✅ Sí |
| **Doble-click** | ✅ Editar celda | ✅ Marcar como Registrado |

## 🎯 Funcionalidades Principales

### 1. **Visualización de Specials**

Los supervisores ven todos los specials que les han sido enviados durante su turno actual (desde el último START SHIFT).

**Columnas mostradas:**
- `ID`: ID del special
- `FechaHora`: Fecha y hora del evento
- `Sitio`: ID y nombre del sitio
- `Actividad`: Nombre de la actividad
- `Cantidad`: Cantidad registrada
- `Camera`: Número de cámara
- `Descripcion`: Descripción del evento
- `Usuario`: Operador que generó el evento
- `TZ`: Zona horaria del sitio
- `Marca`: Estado de revisión (vacío, En Progreso, Registrado)

### 2. **Sistema de Marcas Persistentes**

Los supervisores pueden marcar los specials para llevar control de su progreso:

| Marca | Color | Significado | Ícono |
|-------|-------|-------------|-------|
| **Sin marca** | Sin color | No revisado aún | - |
| **En Progreso** | 🟠 Ámbar (#f5a623) | Revisándose actualmente | 🔄 |
| **Registrado** | 🟢 Verde (#00c853) | Completado y registrado | ✅ |

**Características:**
- Las marcas se guardan en la base de datos (columnas `marked_status`, `marked_by`, `marked_at`)
- Son persistentes entre sesiones
- Visibles para todos los supervisores
- Incluyen quién marcó y cuándo

### 3. **Botones del Header**

#### 🔄 Refrescar
- Recarga los specials desde la base de datos
- Actualiza las marcas y cambios realizados por otros supervisores

#### 🗑️ Eliminar
- Elimina los specials seleccionados de la base de datos
- Requiere confirmación
- Acción irreversible

#### 🚀 Start Shift / 🏁 End of Shift
- Inicia o finaliza el turno del supervisor
- Cambia de color según el estado (verde = Start, rojo = End)
- Afecta el filtro de specials mostrados

### 4. **Botones de Marcado**

#### ✅ Marcar como Registrado
- Marca los specials seleccionados como completados
- Aplica color verde a las filas
- Guarda el nombre del supervisor y la fecha/hora

#### 🔄 Marcar como En Progreso
- Marca los specials seleccionados como en revisión
- Aplica color ámbar a las filas
- Útil para indicar que se está trabajando en ellos

#### ❌ Desmarcar
- Elimina la marca de los specials seleccionados
- Quita el color de la fila
- Restaura al estado "no revisado"

#### ☑️ Auto-refresh (2 min)
- Checkbox para activar/desactivar actualización automática
- Cuando está activo, recarga los specials cada 2 minutos
- Útil para ver cambios realizados por otros supervisores

### 5. **Menú Contextual (Click Derecho)**

Al hacer click derecho sobre una fila, aparece un menú con opciones:
- ✅ Marcar como Registrado
- 🔄 Marcar como En Progreso
- ❌ Desmarcar
- 🗑️ Eliminar

### 6. **Atajos de Teclado**

| Atajo | Acción |
|-------|--------|
| **Doble-click** | Marca la fila como "Registrado" |
| **Click derecho** | Abre menú contextual |
| **Ctrl+C** | Copia selección al portapapeles |

## 🔧 Implementación Técnica

### Función Principal

```python
def open_hybrid_events_supervisor(username, session_id=None, station=None, root=None):
    """
    Ventana híbrida para supervisores que muestra solo Specials
    """
```

### Singleton

La ventana usa el patrón singleton con la clave `'hybrid_events_supervisor'` para evitar duplicados:

```python
ex = _focus_singleton('hybrid_events_supervisor')
if ex:
    return ex
```

### Query Principal

```sql
SELECT ID_special, FechaHora, ID_Sitio, Nombre_Actividad, Cantidad, Camera,
       Descripcion, Usuario, Time_Zone, marked_status, marked_by, marked_at
FROM specials
WHERE Supervisor = %s 
AND FechaHora >= %s
ORDER BY FechaHora DESC
```

**Parámetros:**
- `Supervisor`: Nombre del supervisor actual
- `FechaHora >=`: Desde el último START SHIFT

### Estructura de Datos

**row_data_cache:**
```python
[
    {
        'id': 123,
        'values': [id, fecha, sitio, actividad, cantidad, camera, desc, usuario, tz, marca],
        'marked_status': 'done' | 'flagged' | None
    },
    ...
]
```

**row_ids:**
```python
[123, 124, 125, ...]  # IDs de specials en el mismo orden que las filas
```

### Aplicación de Colores

```python
# Limpiar colores existentes
sheet.dehighlight_all()

# Aplicar colores según marca
for idx, item in enumerate(processed):
    if item['marked_status'] == 'done':
        sheet.highlight_rows([idx], bg="#00c853", fg="#111111")  # Verde
    elif item['marked_status'] == 'flagged':
        sheet.highlight_rows([idx], bg="#f5a623", fg="#111111")  # Ámbar
    # Sin marca = sin color
```

## 📊 Flujo de Trabajo Típico

### Escenario: Supervisor revisa specials del turno

1. **Inicio del turno**
   - Supervisor hace click en "🚀 Start Shift"
   - Sistema registra START SHIFT en la tabla Eventos

2. **Visualización de specials**
   - Se cargan automáticamente todos los specials enviados al supervisor desde el START SHIFT
   - Aparecen sin marca (sin color)

3. **Revisión de specials**
   - Supervisor selecciona un special
   - Doble-click o click derecho → "🔄 Marcar como En Progreso"
   - La fila se pone color ámbar

4. **Registro completado**
   - Al terminar de registrar el evento en el sistema externo
   - Supervisor selecciona la fila
   - Click en "✅ Marcar como Registrado"
   - La fila se pone color verde

5. **Correcciones**
   - Si se cometió un error
   - Seleccionar fila → "❌ Desmarcar"
   - La marca se elimina

6. **Eliminación de duplicados**
   - Si hay un special duplicado o erróneo
   - Seleccionar fila → "🗑️ Eliminar"
   - Confirmar → Se elimina de la BD

7. **Fin del turno**
   - Supervisor hace click en "🏁 End of Shift"
   - Sistema registra END SHIFT en la tabla Eventos

## 🎨 Personalización

### Cambiar Colores de Marca

En `load_data()`, modifica los colores:

```python
if item['marked_status'] == 'done':
    sheet.highlight_rows([idx], bg="#00c853", fg="#111111")  # Verde
elif item['marked_status'] == 'flagged':
    sheet.highlight_rows([idx], bg="#f5a623", fg="#111111")  # Ámbar
```

**Colores sugeridos:**
- Verde: `#00c853`, `#4caf50`, `#66bb6a`
- Ámbar: `#f5a623`, `#ff9800`, `#ffb74d`
- Azul: `#4a90e2`, `#2196f3`, `#42a5f5`

### Cambiar Intervalo de Auto-refresh

En `load_data()`, al final:

```python
if auto_refresh_active.get():
    refresh_job = top.after(120000, load_data)  # 120000 ms = 2 minutos
```

**Intervalos comunes:**
- 1 minuto: `60000`
- 2 minutos: `120000`
- 5 minutos: `300000`
- 10 minutos: `600000`

### Cambiar Anchos de Columnas

En `custom_widths_specials`:

```python
custom_widths_specials = {
    "ID": 60,
    "FechaHora": 150,
    "Sitio": 220,           # Aumentar si hay nombres de sitios largos
    "Actividad": 150,
    "Cantidad": 70,
    "Camera": 80,
    "Descripcion": 190,     # Aumentar si hay descripciones largas
    "Usuario": 100,
    "TZ": 90,
    "Marca": 180
}
```

## 🐛 Solución de Problemas

### Problema 1: No aparecen specials

**Causa**: No hay shift activo o no se han enviado specials
**Solución**: 
1. Verificar que el supervisor haya hecho START SHIFT
2. Verificar que los operadores hayan enviado specials a este supervisor

### Problema 2: Marcas no se guardan

**Causa**: Error de conexión a BD o columnas faltantes
**Solución**:
1. Verificar que la tabla `specials` tenga las columnas:
   - `marked_status` (ENUM('flagged', 'done') o VARCHAR)
   - `marked_by` (VARCHAR)
   - `marked_at` (DATETIME)

### Problema 3: Auto-refresh no funciona

**Causa**: Checkbox desactivado o error en el job
**Solución**:
1. Verificar que el checkbox esté marcado
2. Revisar consola por errores en `load_data()`

### Problema 4: Colores no se aplican

**Causa**: `marked_status` NULL o valores incorrectos
**Solución**:
1. Verificar que los valores en BD sean exactamente `'done'` o `'flagged'`
2. Revisar que `dehighlight_all()` se ejecute antes de aplicar colores

## 📋 Casos de Uso

### Caso 1: Supervisor con múltiples operadores

**Situación**: Supervisor recibe specials de 5 operadores diferentes

**Flujo:**
1. Abre `open_hybrid_events_supervisor()`
2. Ve todos los specials mezclados (columna "Usuario" muestra quién lo envió)
3. Ordena por "Usuario" o "FechaHora" usando los headers del sheet
4. Marca cada uno según su estado de revisión

### Caso 2: Supervisor trabaja con otro supervisor

**Situación**: Dos supervisores comparten la revisión de specials

**Flujo:**
1. Supervisor A marca algunos specials como "En Progreso"
2. Supervisor B abre su ventana (con auto-refresh activo)
3. Ve los specials marcados por A con su nombre en la columna "Marca"
4. Supervisor B trabaja en los que no están marcados

### Caso 3: Revisar specials del turno anterior

**Situación**: Supervisor quiere ver specials de un turno pasado

**Limitación**: La función actual solo muestra desde el último START SHIFT
**Alternativa**: Usar `open_specials_window()` que tiene más opciones de filtrado

## 🚀 Próximas Mejoras

- [ ] Filtros por Usuario, Actividad, Sitio
- [ ] Exportar a Excel/CSV
- [ ] Notificaciones cuando llegan nuevos specials
- [ ] Estadísticas: Total marcados, pendientes, etc.
- [ ] Búsqueda rápida en descripciones
- [ ] Ordenamiento persistente entre sesiones

---

**Creado por**: GitHub Copilot  
**Fecha**: Noviembre 2025  
**Versión**: 1.0
