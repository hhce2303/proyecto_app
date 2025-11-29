# 📊 Guía del Sistema de Status para Supervisores

## 🎯 Descripción General

El sistema de status permite a los supervisores y lead supervisors controlar su disponibilidad para recibir eventos especiales. Los operadores solo verán supervisores con status "Disponible" al asignar eventos.

---

## 🔧 Características Implementadas

### ✅ **1. Indicador Visual de Status**
- **Ubicación**: Header de las ventanas de supervisores y lead supervisors
- **Posición**: Entre los botones de acción y el botón de Start/End Shift
- **Componentes**:
  - 📊 Label con emoji y texto del status actual
  - ⚙️ Botón de configuración para cambiar status

### ✅ **2. Estados Disponibles**

| Valor DB | Status         | Color  | Emoji | Descripción                           |
|----------|----------------|--------|-------|---------------------------------------|
| `1`      | Disponible     | Verde  | 🟢    | Supervisor puede recibir eventos      |
| `0`      | Ocupado        | Amarillo| 🟡   | Supervisor visible pero ocupado       |
| `-1`     | No disponible  | Rojo   | 🔴    | Supervisor NO recibirá eventos        |

### ✅ **3. Interfaz de Cambio de Status**
- Ventana modal con 3 botones grandes
- Colores distintivos para cada opción
- Confirmación visual al cambiar status
- Actualización en tiempo real del indicador

---

## 🚀 Cómo Usar

### **Para Supervisores**

1. **Ver tu status actual**:
   - Mira el indicador en el header: `🟢 Disponible`, `🟡 Ocupado` o `🔴 No disponible`

2. **Cambiar tu status**:
   - Haz clic en el botón **⚙️** junto al indicador
   - Selecciona el nuevo status deseado
   - El indicador se actualizará automáticamente

3. **Recibir eventos**:
   - Solo con status `🟢 Disponible` recibirás nuevos eventos de operadores
   - Con `🟡 Ocupado` estarás visible pero no recibirás asignaciones automáticas
   - Con `🔴 No disponible` NO aparecerás en la lista de supervisores disponibles

### **Para Lead Supervisors**

- Misma funcionalidad que supervisores
- Pueden ver y cambiar su propio status
- Interfaz idéntica en su ventana de gestión

### **Para Operadores**

- Solo ven supervisores con status `🟢 Disponible`
- Si no hay supervisores disponibles, reciben una advertencia
- No pueden cambiar el status de los supervisores

---

## 💾 Base de Datos

### **Tabla**: `sesion`
### **Campo**: `Active`

```sql
-- Valores posibles:
Active = 1   -- Disponible (🟢)
Active = 0   -- Ocupado (🟡)
Active = -1  -- No disponible (🔴)
```

### **Query para verificar status**:
```sql
SELECT ID_user, Active 
FROM sesion 
WHERE ID_user = 'nombre_usuario' 
ORDER BY ID DESC 
LIMIT 1
```

### **Query para cambiar status**:
```sql
UPDATE sesion 
SET Active = ? 
WHERE ID_user = ? 
ORDER BY ID DESC 
LIMIT 1
```

---

## 🔍 Funciones Implementadas

### **En `backend_super.py`:**

1. **`get_user_status(username)`**
   - Obtiene el status actual del usuario
   - Retorna texto formateado con emoji: `"🟢 Disponible"`

2. **`refresh_status(label_status, username)`**
   - Actualiza el label visual con el nuevo status
   - Se ejecuta automáticamente al cambiar status

### **En `under_super.py`:**

1. **`get_user_status_bd(username)`**
   - Consulta directa a la base de datos
   - Retorna valor numérico: `1`, `0`, o `-1`

2. **`get_available_supervisors()`** *(Para operadores)*
   - Retorna solo supervisores con `Active = 1`
   - Usado en ventanas de asignación de eventos

---

## 🎨 Diseño Visual

### **CustomTkinter (Preferido)**:
```python
# Indicador de status
status_frame = UI.CTkFrame(header, fg_color="transparent")
status_label = UI.CTkLabel(status_frame, text="🟢 Disponible", 
                           font=("Segoe UI", 12, "bold"))

# Botón de configuración
UI.CTkButton(status_frame, text="⚙️", 
            fg_color="#3b4754", hover_color="#4a5560",
            width=40, height=32)
```

### **Tkinter (Fallback)**:
```python
# Indicador de status
status_frame = tk.Frame(header, bg="#23272a")
status_label = tk.Label(status_frame, text="🟢 Disponible", 
                       bg="#23272a", fg="#e0e0e0",
                       font=("Segoe UI", 12, "bold"))

# Botón de configuración
tk.Button(status_frame, text="⚙️", 
         bg="#3b4754", fg="white",
         relief="flat", width=3)
```

---

## 🧪 Testing

### **Script de Prueba**: `test_status_interface.py`

Ejecutar para probar:
1. Funciones de base de datos
2. Mapeo de valores
3. Interfaz gráfica
4. Cambio de status

```bash
python test_status_interface.py
```

---

## 📝 Notas Importantes

### ⚠️ **Importante para Administradores**:
- El status se guarda en la tabla `sesion`, no en `user`
- Cada sesión de usuario tiene su propio status
- El status NO afecta la capacidad de login
- Solo afecta la visibilidad en asignación de eventos

### ✅ **Mejores Prácticas**:
1. **Al iniciar turno**: Cambiar a `🟢 Disponible`
2. **En reuniones**: Cambiar a `🟡 Ocupado`
3. **En break/almuerzo**: Cambiar a `🔴 No disponible`
4. **Al finalizar turno**: Cambiar a `🔴 No disponible`

### 🔄 **Auto-refresh**:
- El sistema NO actualiza automáticamente el status desde la BD
- Para ver cambios de otros supervisores, usar botón "🔄 Refrescar"
- El indicador local se actualiza inmediatamente al cambiar

---

## 🐛 Troubleshooting

### **Problema**: El status no cambia
**Solución**: 
- Verificar conexión a la base de datos
- Revisar permisos de escritura en tabla `sesion`
- Consultar logs en consola `[ERROR]`

### **Problema**: Operadores no ven supervisores disponibles
**Solución**:
- Verificar que al menos un supervisor tenga `Active = 1`
- Ejecutar query manual: `SELECT * FROM sesion WHERE Active = 1`
- Supervisores deben cambiar su status a `🟢 Disponible`

### **Problema**: El indicador muestra "❌ Usuario no encontrado"
**Solución**:
- Usuario no tiene registro en tabla `sesion`
- Hacer login completo para crear sesión
- Verificar que el username sea correcto

---

## 📞 Soporte

Para problemas o dudas:
- Revisar logs en consola (buscar `[DEBUG]`, `[ERROR]`, `[WARN]`)
- Verificar estructura de tabla `sesion`
- Contactar con el equipo IT

---

**Última actualización**: Noviembre 2025  
**Versión**: 1.0  
**Autor**: Hector Cruz & Yonier Angulo
