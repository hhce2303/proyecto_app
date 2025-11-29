# 🚀 Diseño de Ventana Híbrida: Eventos con Edición Inline

## Concepto
Combinar `open_register_form()` y `show_events()` en una sola ventana tipo Excel donde:
- Se visualizan todos los eventos del turno actual
- Se puede agregar nuevos eventos como filas nuevas
- Se puede editar inline con doble-click
- Se puede eliminar con clic derecho
- Columnas inteligentes según tipo de dato

## Características Principales

### 1. **Tksheet como Base**
- Grid editable tipo Excel
- Selección de celdas/filas
- Copy/Paste nativo
- Atajos de teclado

### 2. **Columnas con Widgets Especializados**
| Columna | Tipo | Widget | Funcionalidad |
|---------|------|--------|---------------|
| FechaHora | datetime | DateTimePicker | Selector visual de fecha/hora |
| Sitio | text | FilteredCombobox | Búsqueda con autocompletado |
| Actividad | text | FilteredCombobox | Búsqueda con autocompletado |
| Cantidad | number | Spinbox | +/- rápido |
| Camera | text | Entry | Texto libre |
| Descripción | text | Entry | Texto libre |

### 3. **Modos de Edición**
- **Doble-click en celda**: Abre widget especializado según columna
- **Enter**: Confirma cambio y guarda en BD
- **Esc**: Cancela cambio
- **Tab**: Siguiente celda
- **Shift+Tab**: Celda anterior

### 4. **Barra de Herramientas**
```
[➕ Nuevo] [💾 Guardar Todo] [🔄 Refrescar] [🗑️ Eliminar]  [Auto-refresh: ☑ 30s]
```

### 5. **Validaciones en Tiempo Real**
- **Actividad**: Obligatoria (columna resaltada si vacía)
- **Sitio**: Debe existir en BD
- **Cantidad**: Solo números
- **FechaHora**: No puede ser futura

### 6. **Indicadores Visuales**
- **Fila nueva**: Fondo azul claro (#E3F2FD)
- **Fila editada**: Fondo amarillo (#FFF9C4)
- **Fila guardada**: Fondo blanco/gris alternado
- **Error de validación**: Borde rojo

### 7. **Menú Contextual (Clic Derecho)**
```
✏️ Editar
🗑️ Eliminar
📋 Copiar fila
📄 Duplicar fila
---
🔄 Refrescar
```

## Flujo de Trabajo

### Agregar Nuevo Evento
1. Click en botón "➕ Nuevo"
2. Se agrega fila vacía al final (fondo azul claro)
3. Doble-click en cada celda para editar
4. Al completar Actividad (obligatoria), botón "💾 Guardar" se activa
5. Click "💾 Guardar" → INSERT en BD → Fila cambia a color normal

### Editar Evento Existente
1. Doble-click en celda
2. Widget aparece sobre la celda
3. Modificar valor
4. Enter → UPDATE en BD → Fila cambia a amarillo momentáneamente
5. Auto-refresh confirma cambio

### Eliminar Evento
1. Clic derecho en fila → "🗑️ Eliminar"
2. Confirmación
3. DELETE en BD
4. Fila se elimina del grid

## Implementación Técnica

### Estructura de Datos Interna
```python
row_data = {
    'id': ID_Eventos,           # None si es nuevo
    'fecha_hora': datetime,
    'sitio_id': int,
    'sitio_nombre': str,
    'actividad': str,
    'cantidad': float,
    'camera': str,
    'descripcion': str,
    'status': 'saved'|'new'|'edited'  # Estado de la fila
}
```

### Widgets Emergentes
```python
def show_datetime_picker(row, col):
    # Ventana emergente con tkcalendar.DateEntry + spinboxes para hora
    pass

def show_filtered_combo(row, col, values):
    # Combobox flotante sobre la celda
    pass
```

### Auto-save vs Guardar Explícito
- **Opción 1**: Auto-save al salir de celda (Excel-like)
- **Opción 2**: Botón "Guardar" manual (más control)
- **Recomendación**: Opción 2 con indicador visual de cambios pendientes

## Ventajas sobre Sistema Actual
1. ✅ **Una sola ventana** en lugar de dos separadas
2. ✅ **Edición rápida** sin formularios modales
3. ✅ **Vista completa** del contexto del turno
4. ✅ **Copy/Paste** entre filas
5. ✅ **Menos clicks** para operaciones comunes
6. ✅ **Experiencia tipo Excel** familiar para usuarios

## Desafíos Técnicos
1. **Widgets sobre tksheet**: Coordenadas precisas
2. **Sincronización BD**: Manejar conflictos de concurrencia
3. **Performance**: Con muchos eventos (>100)
4. **Validación**: Rollback si falla SQL

## Roadmap de Implementación
1. ✅ Diseño conceptual
2. ⏳ Función base con tksheet + carga de datos
3. ⏳ Editor inline básico (Entry)
4. ⏳ Widgets especializados (DatePicker, ComboBox)
5. ⏳ Sistema de guardado con validación
6. ⏳ Menú contextual y atajos
7. ⏳ Auto-refresh y manejo de errores
8. ⏳ Testing con múltiples usuarios
