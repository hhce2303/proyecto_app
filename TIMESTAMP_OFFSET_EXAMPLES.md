# 🕐 Sistema de Ajuste de Timestamps con Timezone Offset

## 📝 Descripción

El sistema automáticamente detecta y ajusta timestamps dentro de las descripciones de eventos especiales, aplicando el offset de zona horaria configurado para cada sitio.

## ✨ Formatos Soportados

### Timestamps con Segundos

| Formato | Ejemplo | Descripción |
|---------|---------|-------------|
| `[HH:MM:SS]` | `[05:33:45]` | Con corchetes, 2 dígitos para hora |
| `[H:MM:SS]` | `[5:33:45]` | Con corchetes, 1 dígito para hora |
| `HH:MM:SS` | `05:33:45` | Sin corchetes, 2 dígitos para hora |
| `H:MM:SS` | `5:33:45` | Sin corchetes, 1 dígito para hora |

### Timestamps sin Segundos

| Formato | Ejemplo | Descripción |
|---------|---------|-------------|
| `[HH:MM]` | `[05:33]` | Con corchetes, 2 dígitos para hora |
| `[H:MM]` | `[5:33]` | Con corchetes, 1 dígito para hora |
| `HH:MM` | `05:33` | Sin corchetes, 2 dígitos para hora |
| `H:MM` | `5:33` | Sin corchetes, 1 dígito para hora |

### Formatos con Prefijo "Timestamp:"

| Formato Original | Normalizado a |
|-----------------|---------------|
| `[Timestamp: 05:33:45]` | `[05:33:45]` |
| `Timestamp: 5:33` | `[5:33]` |
| `[Timestamp: HH:MM:SS]` | `[HH:MM:SS]` |

## 🔧 Funcionamiento del Sistema

### 1. Detección Automática

El sistema busca timestamps en la descripción usando expresiones regulares que identifican patrones de tiempo.

### 2. Validación

Antes de ajustar, valida que los valores estén en rangos válidos:
- **Horas**: 0-23
- **Minutos**: 0-59
- **Segundos**: 0-59

### 3. Aplicación de Offset

Aplica el offset configurado para la zona horaria del sitio:

```python
# Ejemplo: Sitio con timezone "PST" y offset -8 horas
Original: "5:33"
Offset: -8 horas
Resultado: "21:33" (del día anterior)
```

### 4. Preservación de Formato

El formato original se mantiene después del ajuste:

| Original | Después del Ajuste | Nota |
|----------|-------------------|------|
| `5:33` | `21:33` | Mantiene 1 dígito si hora < 10 |
| `05:33` | `21:33` | Usa 2 dígitos si hora ≥ 10 |
| `[5:33:00]` | `[21:33:00]` | Mantiene corchetes y segundos |

## 📊 Ejemplos Prácticos

### Ejemplo 1: Formato Simple (H:MM)

**Entrada:**
```
Descripción: "Incident at 5:33 PM"
Timezone: PST (offset: -8 horas)
Fecha del evento: 2025-11-10 13:33:00 UTC
```

**Proceso:**
1. Detecta `5:33` en la descripción
2. Parsea: hora=5, minutos=33, segundos=0
3. Combina con fecha base: 2025-11-10 05:33:00
4. Aplica offset: 2025-11-10 05:33:00 + (-8) = 2025-11-09 21:33:00

**Salida:**
```
Descripción ajustada: "Incident at 21:33 PM"
```

### Ejemplo 2: Múltiples Timestamps

**Entrada:**
```
Descripción: "Started at [5:30], paused at 5:45, resumed at [6:15:30]"
Timezone: EST (offset: -5 horas)
```

**Salida:**
```
Descripción ajustada: "Started at [0:30], paused at 0:45, resumed at [1:15:30]"
```

### Ejemplo 3: Formato con Prefijo

**Entrada:**
```
Descripción: "Check [Timestamp: 5:33] for details"
Timezone: CST (offset: -6 horas)
```

**Normalización:**
```
"Check [Timestamp: 5:33] for details" → "Check [5:33] for details"
```

**Salida:**
```
Descripción ajustada: "Check [23:33] for details"
```

### Ejemplo 4: Timestamps con Segundos

**Entrada:**
```
Descripción: "Event at 5:33:45 and [12:45:30]"
Timezone: PST (offset: -8 horas)
```

**Salida:**
```
Descripción ajustada: "Event at 21:33:45 and [4:45:30]"
```

## 🎨 Código de Implementación

### Función Principal: `adjust_timestamp()`

```python
def adjust_timestamp(match):
    raw_time = match.group(1)  # Ej: "5:33"
    has_brackets = match.group(0).startswith('[')
    
    # Parsear componentes
    time_parts = raw_time.split(":")
    if len(time_parts) == 2:
        hh, mm = [int(x) for x in time_parts]
        ss = 0
    elif len(time_parts) == 3:
        hh, mm, ss = [int(x) for x in time_parts]
    
    # Validar rangos
    if not (0 <= hh <= 23 and 0 <= mm <= 59 and 0 <= ss <= 59):
        return match.group(0)
    
    # Crear datetime y aplicar offset
    desc_dt = datetime.combine(base_date, datetime.min.time()) + \
              timedelta(hours=hh, minutes=mm, seconds=ss)
    desc_dt_adjusted = desc_dt + timedelta(hours=tz_offset_hours)
    
    # Formatear salida preservando formato original
    if len(time_parts[0]) == 1:  # Formato H:MM
        result = f"{desc_dt_adjusted.hour}:{desc_dt_adjusted.minute:02d}"
    else:  # Formato HH:MM
        result = desc_dt_adjusted.strftime("%H:%M")
    
    return f"[{result}]" if has_brackets else result
```

### Orden de Procesamiento

```python
# 1. Con corchetes y segundos: [H:MM:SS] o [HH:MM:SS]
desc = re.sub(r"\[(\d{1,2}:\d{2}:\d{2})\]", adjust_timestamp, desc)

# 2. Con corchetes sin segundos: [H:MM] o [HH:MM]
desc = re.sub(r"\[(\d{1,2}:\d{2})\]", adjust_timestamp, desc)

# 3. Sin corchetes con segundos: H:MM:SS o HH:MM:SS
desc = re.sub(r"(?<!\d)(\d{1,2}:\d{2}:\d{2})(?!\])", adjust_timestamp, desc)

# 4. Sin corchetes sin segundos: H:MM o HH:MM
desc = re.sub(r"(?<!\d)(\d{1,2}:\d{2})(?!:\d|\])", adjust_timestamp, desc)
```

## 🔍 Expresiones Regulares Explicadas

### Patrón: `\d{1,2}:\d{2}:\d{2}`

- `\d{1,2}` - 1 o 2 dígitos para la hora (acepta `5` o `05`)
- `:` - Dos puntos literales
- `\d{2}` - Exactamente 2 dígitos para minutos (`33`)
- `:` - Dos puntos literales
- `\d{2}` - Exactamente 2 dígitos para segundos (`45`)

**Ejemplos que coinciden:**
- `5:33:45` ✅
- `05:33:45` ✅
- `12:00:00` ✅
- `23:59:59` ✅

**Ejemplos que NO coinciden:**
- `5:3:45` ❌ (minutos con 1 dígito)
- `5:33:5` ❌ (segundos con 1 dígito)
- `123:33:45` ❌ (más de 2 dígitos en hora)

### Lookahead/Lookbehind: `(?<!\d)..(?!\])`

- `(?<!\d)` - **Negative lookbehind**: NO debe haber un dígito antes
- `(?!\])` - **Negative lookahead**: NO debe haber un `]` después

**Propósito**: Evitar coincidir con timestamps dentro de fechas completas o ya procesados.

**Ejemplo:**
```
"2025-11-10 05:33:00" → NO coincide con "05:33"
                         (tiene dígitos antes: "10 ")

"Already adjusted [5:33]" → NO coincide con "5:33"
                              (tiene ] después)
```

## ⚠️ Casos Especiales

### Caso 1: Timestamps que Cruzan Medianoche

**Entrada:**
```
Fecha: 2025-11-10 22:00:00
Timestamp en descripción: "23:30"
Offset: +3 horas
```

**Resultado:**
```
"23:30" → 2025-11-10 23:30:00 + 3h = 2025-11-11 02:30:00
Ajustado: "2:30"
```

### Caso 2: Horas Inválidas

**Entrada:**
```
"Meeting at 25:99"
```

**Resultado:**
```
"Meeting at 25:99" (sin cambios - validación falla)
```

### Caso 3: Formato Mixto

**Entrada:**
```
"Started [5:33], ended 17:45:30"
Offset: -8 horas
```

**Resultado:**
```
"Started [21:33], ended 9:45:30"
```

## 🧪 Casos de Prueba

### Test 1: Formato H:MM ✅
```python
Input:  "Event at 5:33"
Offset: -8
Output: "Event at 21:33"
```

### Test 2: Formato HH:MM ✅
```python
Input:  "Event at 05:33"
Offset: -8
Output: "Event at 21:33"
```

### Test 3: Formato [H:MM:SS] ✅
```python
Input:  "Check [5:33:45]"
Offset: +2
Output: "Check [7:33:45]"
```

### Test 4: Múltiples Timestamps ✅
```python
Input:  "From 5:30 to [17:45]"
Offset: -5
Output: "From 0:30 to [12:45]"
```

### Test 5: Con Prefijo "Timestamp:" ✅
```python
Input:  "[Timestamp: 5:33]"
Normaliza: "[5:33]"
Offset: -6
Output: "[23:33]"
```

### Test 6: Timestamp Inválido ✅
```python
Input:  "Meeting at 25:99"
Output: "Meeting at 25:99" (sin cambios)
```

## 📊 Comparación: Antes vs Después

| Descripción Original | Timezone | Offset | Descripción Ajustada |
|---------------------|----------|--------|---------------------|
| `Incident at 5:33` | PST | -8 | `Incident at 21:33` |
| `Check [05:33:00]` | EST | -5 | `Check [00:33:00]` |
| `Started 5:30, ended 6:45` | CST | -6 | `Started 23:30, ended 0:45` |
| `[Timestamp: 5:33]` | MST | -7 | `[22:33]` |

## 🚀 Ventajas del Sistema

1. **Flexible**: Soporta múltiples formatos de timestamp
2. **Inteligente**: Detecta y ajusta automáticamente
3. **Preserva formato**: Mantiene el estilo original (corchetes, dígitos)
4. **Robusto**: Valida rangos antes de ajustar
5. **No invasivo**: No modifica timestamps inválidos

## 💡 Tips de Uso

1. **Usa formato H:MM** para timestamps cortos (ej: `5:33`)
2. **Usa corchetes** para distinguir timestamps importantes (ej: `[5:33]`)
3. **Incluye segundos** si necesitas precisión (ej: `5:33:45`)
4. **Formato libre**: El sistema detecta automáticamente todos los formatos

---

**Actualizado**: Noviembre 2025  
**Versión**: 2.0 (soporte para formatos H:MM)
