# 🎯 AutoComplete Entry - Guía de Uso

## 📝 Descripción

El `AutoCompleteEntry` es un widget personalizado que reemplaza los combobox tradicionales con un sistema inteligente de autocompletado y ajuste automático.

## ✨ Características Principales

### 1. **Sugerencias en Tiempo Real**
- Mientras escribes, aparece una lista desplegable con valores que coinciden
- Filtra por coincidencia parcial (case-insensitive)
- Muestra máximo 10 sugerencias a la vez

### 2. **Ajuste Automático Inteligente**
- Al presionar **Enter**: Ajusta automáticamente al valor más cercano
- Usa coincidencia difusa (`difflib.get_close_matches`)
- Cutoff de 40% de similitud mínima

### 3. **Navegación con Teclado**
| Tecla | Acción |
|-------|--------|
| `Enter` | Ajustar al valor más cercano / Seleccionar sugerencia |
| `Tab` | Autocompletar con primera sugerencia |
| `↓ Flecha Abajo` | Navegar a siguiente sugerencia |
| `↑ Flecha Arriba` | Navegar a anterior sugerencia |
| `Esc` | Cerrar lista de sugerencias |

### 4. **Interacción con Mouse**
- **Click simple**: Selecciona una sugerencia
- **Doble click**: Selecciona y agrega el evento automáticamente

## 🔧 Implementación en backend_super.py

### Código Actual (Sitio y Actividad)

```python
# ⭐ IMPORTAR AUTOCOMPLETE ENTRY
from autocomplete_entry import AutoCompleteEntry, AutoCompleteEntryCTk

# Crear widget con CustomTkinter
if UI is not None and AutoCompleteEntryCTk:
    sitio_combo = AutoCompleteEntryCTk(
        sitio_frame, textvariable=sitio_var, values=sites_list,
        font=("Segoe UI", 11), height=30,
        fg_color="#2b2b2b", text_color="#ffffff",
        border_width=2, border_color="#4a90e2",
        corner_radius=5
    )
else:
    # Fallback Tkinter
    sitio_combo = AutoCompleteEntry(
        sitio_frame, textvariable=sitio_var, values=sites_list,
        font=("Segoe UI", 11), bg="#2b2b2b", fg="#ffffff"
    )
sitio_combo.pack(fill="x", expand=False, padx=2, pady=0)
```

## 🎨 Personalización

### Cambiar el Número de Sugerencias

En `autocomplete_entry.py`, línea ~101:
```python
# Limitar a 10 sugerencias
if len(direct_matches) > 10:
    direct_matches = direct_matches[:10]
```

Cambia `10` al número deseado.

### Ajustar la Similitud Mínima

En `autocomplete_entry.py`, línea ~259:
```python
# cutoff=0.4 = 40% similitud mínima
matches = get_close_matches(text, self.values, n=1, cutoff=0.4)
```

- `cutoff=0.4`: Más permisivo (acepta coincidencias del 40%)
- `cutoff=0.6`: Más estricto (requiere 60% de similitud)
- `cutoff=0.8`: Muy estricto (requiere 80% de similitud)

### Cambiar Altura de la Lista

En `autocomplete_entry.py`, línea ~112:
```python
self.listbox = tk.Listbox(
    self.master,
    height=min(8, len(matches)),  # Máximo 8 filas visibles
    ...
)
```

Cambia `8` al número de filas deseado.

## 🧪 Ejemplos de Uso

### Ejemplo 1: Escritura Parcial
```
Usuario escribe: "SOUTH"
Sugerencias:
- 401 SOUTH PINE ST
- 502 SOUTH ELM AVE  
- 603 SOUTHBOUND HWY
```

### Ejemplo 2: Ajuste Automático con Enter
```
Usuario escribe: "pine st"
Presiona Enter
Resultado: "401 SOUTH PINE ST" (coincidencia exacta encontrada)
```

### Ejemplo 3: Coincidencia Difusa
```
Usuario escribe: "outh pine"
Presiona Enter
Resultado: "401 SOUTH PINE ST" (ajustado con difflib)
```

### Ejemplo 4: Navegación con Teclado
```
Usuario escribe: "SOUTH"
Presiona ↓ dos veces
Presiona Enter
Resultado: Tercera sugerencia seleccionada
```

## 🔍 Cómo Funciona el Ajuste Automático

### 1. **Filtrado Directo** (Primera Prioridad)
```python
text_lower = "south"
direct_matches = [v for v in values if text_lower in v.lower()]
# Resultado: ["401 SOUTH PINE ST", "502 SOUTH ELM AVE"]
```

### 2. **Coincidencia Difusa** (Segunda Prioridad)
Si no hay coincidencias directas, usa `difflib`:
```python
from difflib import get_close_matches
matches = get_close_matches("outh pin", values, n=1, cutoff=0.4)
# Resultado: ["401 SOUTH PINE ST"]
```

### 3. **Validación Final**
```python
def validate_value(self):
    current = self.get().strip()
    
    # 1. Buscar coincidencia exacta (case-insensitive)
    for v in self.values:
        if v.lower() == current.lower():
            return v
    
    # 2. Buscar mejor coincidencia difusa
    best_match = self._find_best_match(current)
    return best_match
```

## 🚀 Ventajas vs Combobox

| Característica | Combobox | AutoCompleteEntry |
|----------------|----------|-------------------|
| Escritura libre | ❌ No | ✅ Sí |
| Sugerencias en tiempo real | ❌ No | ✅ Sí |
| Ajuste automático | ❌ No | ✅ Sí |
| Coincidencia difusa | ❌ No | ✅ Sí |
| Navegación con flechas | ✅ Sí | ✅ Sí |
| Validación automática | ⚠️ Manual | ✅ Automática |
| Estilo oscuro en Windows | ⚠️ Problemático | ✅ Nativo |

## 🐛 Solución de Problemas

### Problema 1: Listbox no aparece
**Causa**: Posición incorrecta del widget padre
**Solución**: Verifica que el frame padre esté correctamente empaquetado

### Problema 2: Sugerencias no coinciden
**Causa**: Valores no cargados en la lista
**Solución**: 
```python
sitio_combo.set_values(sites_list)  # Actualizar valores manualmente
```

### Problema 3: Enter no funciona
**Causa**: Binding sobrescrito por otro evento
**Solución**: Asegúrate que el binding de Enter del formulario NO haga `return "break"` antes

## 📊 Pruebas Realizadas

### Test 1: Coincidencia Exacta ✅
```
Input: "401 SOUTH PINE ST"
Output: "401 SOUTH PINE ST"
```

### Test 2: Coincidencia Parcial ✅
```
Input: "south pine"
Output: "401 SOUTH PINE ST"
```

### Test 3: Typo Pequeño ✅
```
Input: "401 sout pine"
Output: "401 SOUTH PINE ST" (ajustado con difflib)
```

### Test 4: Sin Coincidencias ✅
```
Input: "xxxxx"
Output: None (no ajusta nada)
```

## 🔐 Validación en Base de Datos

El widget asegura que solo se guarden valores válidos:

```python
def add_event_from_form():
    # Validar antes de guardar
    sitio_str = sitio_combo.validate_value()
    if not sitio_str:
        messagebox.showwarning("Sitio inválido", 
                              "No se encontró coincidencia para el sitio ingresado.")
        return
    
    # Continuar con inserción en BD...
```

## 📝 Próximas Mejoras

- [ ] Agregar highlighting de texto coincidente en sugerencias
- [ ] Soporte para múltiples columnas en lista desplegable
- [ ] Historial de valores usados recientemente
- [ ] Sugerencias ponderadas por frecuencia de uso
- [ ] Caché de coincidencias para mejor performance

## 💡 Tips de Uso

1. **Escribe rápido**: No esperes a que aparezcan sugerencias, sigue escribiendo
2. **Usa Tab**: Más rápido que Enter para autocompletar
3. **Navega con flechas**: Si hay varias opciones, usa ↓ y ↑ antes de Enter
4. **Doble click directo**: Para seleccionar y agregar en un solo movimiento

---

**Creado por**: GitHub Copilot  
**Fecha**: Noviembre 2025  
**Versión**: 1.0
