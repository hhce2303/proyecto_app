# 📊 Lógica de Determinación de Estado en Specials

## 🎯 Resumen Ejecutivo

El módulo Specials determina automáticamente si un evento está **"Enviado"** o **"Pendiente"** comparando datos entre dos tablas:
- **Tabla `Eventos`**: Fuente de verdad (eventos actuales del operador)
- **Tabla `specials`**: Snapshot enviado al supervisor

Esta arquitectura **elimina el cache volátil** y garantiza que los cambios se rastrean en la base de datos.

---

## 🏗️ Arquitectura MVC

### **Flujo de datos**:
```
┌─────────────────────────────────────────────────────────────┐
│                    OPERATOR BLACKBOARD                      │
│  ┌────────────────────────────────────────────────────┐     │
│  │            SPECIALS MODULE (View)                  │     │
│  │  • Muestra eventos en tksheet                      │     │
│  │  • Color coding (verde/ámbar)                      │     │
│  │  • Botones "Enviar Seleccionados" / "Enviar Todos"│     │
│  └─────────────────┬──────────────────────────────────┘     │
│                    │                                         │
│                    ▼                                         │
│  ┌────────────────────────────────────────────────────┐     │
│  │    SPECIALS OPERATOR CONTROLLER (Controller)       │     │
│  │  • load_specials_data() → Consulta y compara      │     │
│  │  • send_to_supervisor() → INSERT o UPDATE          │     │
│  │  • get_active_supervisors() → Lista supervisores   │     │
│  └─────────────────┬──────────────────────────────────┘     │
│                    │                                         │
│                    ▼                                         │
│  ┌────────────────────────────────────────────────────┐     │
│  │         SPECIALS MODEL (Model)                     │     │
│  │  • get_specials_eventos() → Query Eventos          │     │
│  │  • get_special_by_evento_id() → Query specials     │     │
│  │  • insert_special() → INSERT                       │     │
│  │  • update_special() → UPDATE                       │     │
│  │  • get_active_supervisors() → Supervisores activos │     │
│  └─────────────────┬──────────────────────────────────┘     │
│                    │                                         │
│                    ▼                                         │
│            ┌──────────────────┐                             │
│            │   MySQL Database │                             │
│            │  • Eventos       │                             │
│            │  • specials      │                             │
│            │  • user          │                             │
│            │  • sesion        │                             │
│            └──────────────────┘                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔍 Lógica de Determinación de Estado

### **Método clave**: `SpecialsOperatorController.load_specials_data()`

### **Paso 1: Query de eventos especiales**
```python
# Obtener eventos desde el último START SHIFT
eventos = specials_model.get_specials_eventos(username, last_shift_time)

# Grupos especiales: AS, KG, HUD, PE, SCH, WAG, LT, DT
GRUPOS_ESPECIALES = ("AS", "KG", "HUD", "PE", "SCH", "WAG", "LT", "DT")
```

### **Paso 2: Para cada evento, buscar en tabla specials**
```python
special_data = specials_model.get_special_by_evento_id(id_evento)
```

### **Paso 3: Determinar estado según existencia y cambios**

#### **CASO A: NO existe en `specials`** (`special_data` es `None`)
```python
estado = ""  # Sin enviar
estado_color = None  # Sin color
```
**Significado**: Este evento **nunca ha sido enviado** al supervisor.

---

#### **CASO B: SÍ existe en `specials`** (tiene `ID_Special`)

**Subpaso B1**: Extraer datos de la tabla `specials`
```python
(
    id_special, special_fecha, special_sitio, special_actividad,
    special_cantidad, special_camera, special_desc, supervisor,
    special_tz, marked_status, marked_by, marked_at
) = special_data
```

**Subpaso B2**: Comparar **6 campos críticos**
```python
hay_cambios = (
    eventos_fechahora != specials_fechahora or  # 1. Fecha/Hora
    id_sitio != special_sitio or                # 2. Sitio
    nombre_actividad != special_actividad or    # 3. Actividad
    eventos_cantidad != especials_cantidad or   # 4. Cantidad
    eventos_camera != specials_camera or        # 5. Camera
    eventos_desc != specials_desc               # 6. Descripción
)
```

**Subpaso B3**: Asignar estado según resultado de comparación

##### **B3.1: Hay cambios** (`hay_cambios == True`)
```python
estado = "⏳ Pendiente por actualizar"
estado_color = "amber"  # Color ámbar/naranja (#f5a623)
```
**Significado**: El evento **ya fue enviado** pero el operador **hizo cambios después**. El supervisor verá datos desactualizados hasta que se envíe UPDATE.

##### **B3.2: NO hay cambios** (`hay_cambios == False`)
```python
estado = f"✅ Enviado a {supervisor}"
estado_color = "green"  # Color verde (#00c853)
```
**Significado**: El evento está **sincronizado** con el supervisor. No hay cambios pendientes.

---

## 🎨 Visualización en UI

### **Color Coding en tksheet**:
| Estado | Color | Código Hex | Icono |
|--------|-------|------------|-------|
| **Sin enviar** | Sin color | N/A | - |
| **Enviado (sincronizado)** | Verde | `#00c853` | ✅ |
| **Pendiente actualizar** | Ámbar | `#f5a623` | ⏳ |

### **Ejemplo visual**:
```
┌────────────┬──────────┬──────────┬──────────┬──────────────────────────┐
│ Fecha Hora │ Sitio    │ Actividad│ Cantidad │ Estado                   │
├────────────┼──────────┼──────────┼──────────┼──────────────────────────┤
│ 2025-12-15 │ Site A   │ AS       │ 5        │ ✅ Enviado a SupervisorX │ ← Verde
│ 14:30:00   │          │          │          │                          │
├────────────┼──────────┼──────────┼──────────┼──────────────────────────┤
│ 2025-12-15 │ Site B   │ KG       │ 3        │ ⏳ Pendiente actualizar  │ ← Ámbar
│ 15:45:00   │          │          │          │                          │
├────────────┼──────────┼──────────┼──────────┼──────────────────────────┤
│ 2025-12-15 │ Site C   │ HUD      │ 8        │                          │ ← Sin color
│ 16:20:00   │          │          │          │                          │
└────────────┴──────────┴──────────┴──────────┴──────────────────────────┘
```

---

## 🔄 Operaciones INSERT vs UPDATE

### **Lógica en `send_to_supervisor(evento_ids, supervisor)`**:

```python
for evento_id in evento_ids:
    item = data_by_id.get(evento_id)
    
    if item['id_special']:
        # Ya existe en specials → UPDATE
        success, message = specials_model.update_special(
            id_special=item['id_special'],
            fecha_hora=item['fecha_hora'],
            id_sitio=item['id_sitio'],
            nombre_actividad=item['nombre_actividad'],
            cantidad=item['cantidad'],
            camera=item['camera'],
            descripcion=item['descripcion'],
            usuario=item['usuario'],
            time_zone=item['time_zone'],
            supervisor=supervisor
        )
        updated += 1
    else:
        # No existe en specials → INSERT
        success, message, id_special = specials_model.insert_special(
            evento_id=evento_id,  # FK a tabla Eventos
            fecha_hora=item['fecha_hora'],
            id_sitio=item['id_sitio'],
            nombre_actividad=item['nombre_actividad'],
            cantidad=item['cantidad'],
            camera=item['camera'],
            descripcion=item['descripcion'],
            usuario=item['usuario'],
            time_zone=item['time_zone'],
            supervisor=supervisor
        )
        inserted += 1
```

### **Resultado**:
```
Enviados a SupervisorX:
• 3 nuevos
• 2 actualizados
```

---

## 🗄️ Estructura de Base de Datos

### **Relación FK entre tablas**:
```sql
┌─────────────────────────────────────────────┐
│         Tabla: Eventos                      │
├──────────────────┬──────────────────────────┤
│ ID_Eventos (PK)  │ INT UNSIGNED AUTO_INC    │
│ FechaHora        │ DATETIME                 │
│ ID_Sitio         │ INT                      │
│ Nombre_Actividad │ VARCHAR(150)             │
│ Cantidad         │ INT                      │
│ Camera           │ VARCHAR(45)              │
│ Descripcion      │ TEXT                     │
│ ID_Usuario       │ INT                      │
│ Time_Zone        │ VARCHAR(15)              │
└──────────────────┴──────────────────────────┘
             │
             │ FK: ID_Eventos
             ▼
┌─────────────────────────────────────────────┐
│         Tabla: specials                     │
├──────────────────┬──────────────────────────┤
│ ID_Special (PK)  │ INT UNSIGNED AUTO_INC    │
│ ID_Eventos (FK)  │ INT UNSIGNED             │ ← Relación FK
│ FechaHora        │ DATETIME                 │
│ ID_Sitio         │ INT                      │
│ Nombre_Actividad │ VARCHAR(150)             │
│ Cantidad         │ INT                      │
│ Camera           │ VARCHAR(45)              │
│ Descripcion      │ TEXT                     │
│ Usuario          │ VARCHAR(75)              │
│ Time_Zone        │ VARCHAR(15)              │
│ Supervisor       │ VARCHAR(75)              │
│ marked_status    │ VARCHAR(50)              │
│ marked_by        │ VARCHAR(75)              │
│ marked_at        │ DATETIME                 │
└──────────────────┴──────────────────────────┘
```

### **Query clave**:
```sql
-- Buscar special por ID_Eventos (FK)
SELECT 
    ID_Special, FechaHora, ID_Sitio, Nombre_Actividad, 
    Cantidad, Camera, Descripcion, Supervisor, Time_Zone,
    marked_status, marked_by, marked_at
FROM specials
WHERE ID_Eventos = %s
ORDER BY ID_Special DESC
LIMIT 1
```

---

## ✅ Beneficios de esta Arquitectura

### **1. Sin cache volátil**
- ❌ **Antes**: `pending_changes` en memoria → se pierde en crash
- ✅ **Ahora**: Todo en BD → persistencia garantizada

### **2. Detección automática de cambios**
- Sistema compara 6 campos automáticamente
- No requiere intervención manual del operador
- Estados visuales inmediatos (verde/ámbar)

### **3. UPSERT inteligente**
- Si `ID_Special` existe → UPDATE
- Si `ID_Special` es NULL → INSERT
- No hay ambigüedad en la operación

### **4. Rastreabilidad completa**
- Columna `Supervisor`: Quién recibió el evento
- Columna `marked_status/marked_by/marked_at`: Marcas de supervisor
- Relación FK `ID_Eventos`: Trazabilidad hacia tabla Eventos

### **5. Timezone adjustments**
- FechaHora ajustada según zona horaria del sitio
- Timestamps en descripción ajustados ([HH:MM:SS])
- Consistencia en todo el sistema

---

## 🔧 Ejemplo de Flujo Completo

### **Escenario**: Operador edita un evento ya enviado

1. **Operador crea evento** en Daily:
   ```
   Fecha: 2025-12-15 14:00:00
   Sitio: Site A (123)
   Actividad: AS
   Cantidad: 5
   ```

2. **Operador envía a supervisor** (primera vez):
   - Sistema ejecuta **INSERT** en `specials`
   - `ID_Special` = 1001
   - `ID_Eventos` = 5678 (FK)
   - `Supervisor` = "SupervisorX"
   - Estado: **✅ Enviado a SupervisorX** (verde)

3. **Operador edita cantidad** de 5 a 8:
   - Cambio guardado en tabla `Eventos`
   - Sistema compara en próxima carga:
     ```python
     eventos_cantidad = 8
     especials_cantidad = 5
     hay_cambios = True
     ```
   - Estado cambia a: **⏳ Pendiente por actualizar** (ámbar)

4. **Operador reenvía**:
   - Sistema ejecuta **UPDATE** en `specials` (ID_Special=1001)
   - Actualiza Cantidad = 8
   - Estado vuelve a: **✅ Enviado a SupervisorX** (verde)

---

## 📝 Mantenimiento y Debug

### **Queries útiles para debug**:

```sql
-- Ver todos los specials pendientes de actualizar
SELECT e.ID_Eventos, e.FechaHora as EventoFH, s.FechaHora as SpecialFH,
       e.Cantidad as EventoCant, s.Cantidad as SpecialCant
FROM Eventos e
LEFT JOIN specials s ON e.ID_Eventos = s.ID_Eventos
WHERE s.ID_Special IS NOT NULL
  AND (e.FechaHora != s.FechaHora 
       OR e.Cantidad != s.Cantidad
       OR e.ID_Sitio != s.ID_Sitio);

-- Ver eventos NO enviados (sin registro en specials)
SELECT e.ID_Eventos, e.FechaHora, e.Nombre_Actividad
FROM Eventos e
LEFT JOIN specials s ON e.ID_Eventos = s.ID_Eventos
WHERE s.ID_Special IS NULL
  AND e.Nombre_Actividad IN ('AS', 'KG', 'HUD', 'PE', 'SCH', 'WAG', 'LT', 'DT');
```

### **Logs de debug**:
```python
[DEBUG] Procesando evento 0: ID=5678, Sitio=123, Actividad=AS
[DEBUG] Evento 5678 existe en specials (ID_Special=1001)
[DEBUG] Comparación: hay_cambios=True
[DEBUG] Estado asignado: ⏳ Pendiente por actualizar
[DEBUG] SpecialsOperatorController: Procesados 15 eventos
```

---

## 🎓 Conclusión

Esta arquitectura MVC garantiza:
- ✅ **Persistencia**: Sin cache volátil
- ✅ **Consistencia**: Comparación automática de 6 campos
- ✅ **Trazabilidad**: FK ID_Eventos conecta tablas
- ✅ **Usabilidad**: Estados visuales (verde/ámbar) intuitivos
- ✅ **Mantenibilidad**: Separación clara Modelo-Vista-Controlador

El sistema determina automáticamente INSERT vs UPDATE basándose en la presencia de `ID_Special`, eliminando la necesidad de lógica compleja de caché.
