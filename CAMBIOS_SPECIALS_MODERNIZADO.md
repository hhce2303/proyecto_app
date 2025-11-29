# 🎨 Open Specials Window - MODERNIZADA

## ✨ Cambios Implementados

### 1. **tksheet en lugar de Treeview**
- ✅ Tabla moderna estilo Excel
- ✅ Mejor rendimiento con grandes datasets
- ✅ Funcionalidades built-in: copy, paste, edit, resize columns
- ✅ Selección múltiple más intuitiva
- ✅ Fallback automático a Treeview si tksheet no está instalado

### 2. **CustomTkinter para toda la UI**
- ✅ Botones modernos con hover effects
- ✅ Checkboxes mejorados
- ✅ Frames con colores consistentes
- ✅ Tema dark mode nativo

### 3. **Auto-refresh cada 5 segundos**
- ✅ Checkbox "Auto-refresh (5s)" para activar/desactivar
- ✅ Actualización automática de datos sin intervención manual
- ✅ Ver nuevos specials en tiempo real
- ✅ Cleanup correcto al cerrar ventana (cancela job de refresh)

### 4. **Marcas con colores de fondo**
- ✅ Verde (#00c853) para "Tratado" (marked_status='last')
- ✅ Ámbar (#f5a623) para "En progreso" (marked_status='flagged')
- ✅ Aplicado con `sheet.highlight_rows()` en tksheet
- ✅ Fallback a tags de Treeview

### 5. **Funciones auxiliares mejoradas**
- ✅ `get_selected_ids()`: Detecta automáticamente si usa sheet o tree
- ✅ `toggle_auto_refresh()`: Activa/desactiva refresh automático
- ✅ `on_close()`: Cleanup al cerrar (cancela refresh_job)

### 6. **Ventana más grande**
- ✅ Geometría: `1380x600` (antes era 1280x520)
- ✅ Más espacio para tabla y controles

### 7. **Mejor debugging**
- ✅ Print statement: `[DEBUG] Loaded X specials for {username}`
- ✅ Print statements para auto-refresh activado/desactivado

---

## 📋 Características Mantenidas

✅ Filtrado por shift (START SHIFT → ahora)  
✅ Marcas persistentes en BD  
✅ Modo único vs múltiple  
✅ Botones: Marcar, Desmarcar, Limpiar todo  
✅ Copiar al portapapeles (Ctrl+C)  
✅ Doble-click para marcar rápido  
✅ Función "Otros Specials" (sin modificar)  
✅ Resolución de nombres de sitios y time zones  

---

## 🎯 Cómo Probarlo

### Paso 1: Ejecutar el script de columnas (si no lo has hecho)
```powershell
python add_marks_columns.py
```

### Paso 2: Reiniciar la aplicación
```powershell
python main_super.py
# o
python backend_super.py
```

### Paso 3: Probar funcionalidades

1. **Login como Supervisor**
2. **Hacer START SHIFT**
3. **Crear algunos specials de prueba**
4. **Abrir ventana "Specials"**
5. **Verificar que aparezcan los specials**
6. **Seleccionar un special y hacer doble-click** → Debe marcarse en verde
7. **Esperar 5 segundos** → Debe refrescarse automáticamente
8. **Crear otro special desde otra sesión** → Debe aparecer en 5 segundos
9. **Desactivar "Auto-refresh (5s)"** → No debe refrescarse más
10. **Clickear "⟳ Refrescar Manual"** → Debe refrescar inmediatamente

---

## 🔧 Requisitos

### Paquetes Python
```bash
pip install tksheet customtkinter
```

Si tksheet no está instalado, la función automáticamente usa Treeview (fallback).

---

## 🐛 Problemas Potenciales y Soluciones

### Problema: "No se reflejan los specials de prueba"
**Causa**: Probablemente no has hecho START SHIFT  
**Solución**: 
1. Verifica que tengas un START SHIFT registrado para tu usuario
2. Consulta la BD directamente:
   ```sql
   SELECT * FROM Eventos 
   WHERE Nombre_Actividad = 'START SHIFT' 
   AND ID_Usuario = (SELECT ID_Usuario FROM user WHERE Nombre_Usuario = 'TU_USUARIO')
   ORDER BY FechaHora DESC 
   LIMIT 1;
   ```

### Problema: "La tabla se ve igual (no usa tksheet)"
**Causa**: tksheet no está instalado  
**Solución**:
```powershell
pip install tksheet
```

### Problema: "Los botones no se ven modernos"
**Causa**: CustomTkinter no está instalado  
**Solución**:
```powershell
pip install customtkinter
```

### Problema: "No se actualizan automáticamente los specials"
**Causa**: Auto-refresh desactivado o refresh_job no se está ejecutando  
**Solución**:
1. Verifica que el checkbox "Auto-refresh (5s)" esté marcado
2. Revisa la consola para mensajes `[DEBUG] Auto-refresh activado`
3. Cierra y vuelve a abrir la ventana

### Problema: "Las marcas no persisten al cerrar ventana"
**Causa**: Las columnas marked_* no existen en la tabla specials  
**Solución**:
```powershell
python add_marks_columns.py
```

---

## 📊 Comparación Antes vs Ahora

| Característica | ANTES (Treeview) | AHORA (tksheet) |
|---|---|---|
| **Tabla** | ttk.Treeview (básico) | tksheet (Excel-like) |
| **UI** | Tkinter estándar | CustomTkinter moderno |
| **Refresh** | Manual solamente | Auto + Manual |
| **Colores marcas** | Tags de tree | highlight_rows() |
| **Copy/Paste** | Custom implementation | Built-in en tksheet |
| **Resize columns** | Limitado | Doble-click auto-resize |
| **Edición** | No | Sí (deshabilitado por defecto) |
| **Performance** | Lento con >100 rows | Rápido con >1000 rows |

---

## 🎨 Paleta de Colores

```python
Background principal: #2c2f33
Background tabla: #23272a
Background info: #1a1d21
Texto: #e0e0e0
Accent azul: #4a90e2
Verde (tratado): #00c853
Ámbar (en progreso): #f5a623
Rojo (limpiar): #d32f2f
Turquesa (refrescar): #13988e
Gris (otros): #3b4754
```

---

## 📝 Notas de Desarrollo

- La función `open_specials_window()` ahora tiene ~650 líneas (antes ~650)
- Se agregó variable `nonlocal` para `refresh_job` y `data_cache`
- Se mantiene compatibilidad con versión antigua (fallback a Treeview)
- El auto-refresh se cancela correctamente al cerrar ventana (`on_close()`)
- No se modificó la función `otros_specials()` (mantiene Treeview)

---

## 🚀 Próximas Mejoras Sugeridas

1. **Modernizar "Otros Specials"** con tksheet también
2. **Agregar filtros por fecha** (calendarios)
3. **Exportar a Excel** (usando openpyxl)
4. **Gráficas de specials por día** (matplotlib)
5. **Notificaciones push** cuando hay nuevo special
6. **Modo compacto** (toggle para ver más filas)

---

## ✅ Testing Checklist

- [ ] Instalado tksheet y customtkinter
- [ ] Ejecutado add_marks_columns.py
- [ ] Reiniciado aplicación
- [ ] Login como Supervisor
- [ ] START SHIFT registrado
- [ ] Specials aparecen en ventana
- [ ] Auto-refresh funciona (5s)
- [ ] Marcar special → color verde
- [ ] Desmarcar special → color normal
- [ ] Limpiar todo → todos sin marca
- [ ] Copiar al portapapeles (Ctrl+C)
- [ ] Ventana se cierra sin errores
- [ ] No quedan procesos zombie (refresh_job cancelado)

---

**Fecha de actualización**: 5 de noviembre de 2025  
**Versión**: BETA 2.3 - MODERNIZADA  
**Autor**: GitHub Copilot + hcruz
