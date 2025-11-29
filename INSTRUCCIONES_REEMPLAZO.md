# INSTRUCCIONES PARA ACTUALIZAR open_specials_window

## Paso 1: Agregar columnas a la base de datos
Ejecutar en terminal:
```powershell
python add_marks_columns.py
```

Este script agrega 3 columnas a la tabla `specials`:
- `marked_status` VARCHAR(20) - Estado de marca ('flagged' o 'last')
- `marked_at` TIMESTAMP - Cuándo se marcó
- `marked_by` VARCHAR(100) - Quién lo marcó

## Paso 2: Reemplazar función en backend_super.py

### Opción A: Reemplazo automático (recomendado)
1. Abrir backend_super.py en VS Code
2. Buscar la función `def open_specials_window(username):` (línea ~2961)
3. Seleccionar TODO el código de la función hasta antes de `def audit_view(parent=None):` (hasta línea ~3641)
4. Copiar el contenido completo de `new_open_specials.py` (sin las líneas de comentarios iniciales 1-8)
5. Pegar, reemplazando la selección

### Opción B: Guardar backup y reemplazar manualmente
```powershell
# Crear backup
cp backend_super.py backend_super.py.backup

# Editar manualmente con VS Code
code backend_super.py
```

Luego:
1. Ir a línea 2961 (Ctrl+G → 2961)
2. Seleccionar desde `def open_specials_window(username):` hasta la línea antes de `def audit_view(parent=None):`
3. Eliminar
4. Pegar el contenido de `new_open_specials.py` (líneas 10 en adelante)

## Paso 3: Verificar que no hay errores de sintaxis
En VS Code, revisar que no hay errores (subrayados rojos).

## Paso 4: Reiniciar la aplicación
Cerrar y volver a abrir la aplicación Daily Log.

## Paso 5: Probar funcionalidad

### Test 1: Filtro por shift
1. Hacer login como supervisor
2. Registrar "START SHIFT"
3. Abrir "Specials"
4. Verificar que el título dice "Turno actual (desde HH:MM)"
5. Verificar que solo aparecen specials posteriores al START SHIFT

### Test 2: Marcas persistentes
1. Seleccionar un special
2. Click en "✅ Marcar como tratado"
3. Verificar que aparece "✅ Tratado (tu_nombre)" en la columna Marca
4. Verificar que la fila se pinta de verde
5. Cerrar y volver a abrir Specials → la marca debe persistir

### Test 3: Visibilidad entre supervisores
1. Login como Supervisor A
2. Marcar un special como "Tratado"
3. Logout
4. Login como Supervisor B
5. Click en "👥 Otros Specials"
6. Seleccionar al Supervisor A
7. Verificar que se ve la marca "✅ Tratado (Supervisor A)"

### Test 4: Modo múltiple
1. Desmarcar checkbox "Marca única (último tratado)"
2. Seleccionar varios specials (Ctrl+Click)
3. Click en "✅ Marcar como tratado"
4. Verificar que todos se marcan con "🔄 En progreso"

## Errores comunes y soluciones

### Error: "marked_status column doesn't exist"
**Solución**: Ejecutar `python add_marks_columns.py` primero

### Error: "No hay shift activo"
**Solución**: Hacer "START SHIFT" desde la ventana de Eventos antes de abrir Specials

### La ventana muestra TODO el historial
**Solución**: Verificar que el filtro de shift está aplicándose correctamente. Revisar logs en consola.

## Diferencias principales con versión anterior

| Característica | Antes | Ahora |
|----------------|-------|-------|
| Marcas | Solo en memoria | Persistentes en DB |
| Visibilidad | Solo del usuario actual | Visible entre supervisores |
| Alcance temporal | Todo el historial | Solo turno actual (START→END SHIFT) |
| Columna Marca | No existía | Muestra estado y quién marcó |
| Otros Specials | Todo el historial | Filtrado por turno del supervisor |
| Info tooltip | No | Sí, explica funcionamiento |

## Archivos creados
- `add_marks_columns.py` - Script de migración de DB
- `new_open_specials.py` - Código nuevo de la función
- `CAMBIOS_SPECIALS.md` - Resumen de cambios
- `INSTRUCCIONES_REEMPLAZO.md` - Este archivo
