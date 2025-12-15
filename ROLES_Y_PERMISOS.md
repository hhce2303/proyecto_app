# ⚠️ ROLES Y PERMISOS - PERSISTENCIA DEL PROYECTO

**NOTA:** Este documento solo cubre la parte modularizada (Blackboard + DailyModule).
El sistema completo de supervisores usa `backend_super.py` y `main_super.py`.

## 🎯 REGLA FUNDAMENTAL

### **DAILY (Eventos) = OPERADOR**
- ✅ **Operadores** crean, editan y gestionan eventos en Daily
- ✅ **Operadores** tienen acceso completo a DailyModule
- ❌ **Supervisores NO gestionan Daily directamente**

### **SPECIALS = SUPERVISOR**
- ✅ **Supervisores** revisan y aprueban eventos especiales
- ✅ **Supervisores** marcan y gestionan specials
- ❌ **Operadores NO tienen acceso a Specials**

---

## 📊 Matriz de Permisos por Rol

| Módulo/Tab | Operador | Supervisor | Lead Supervisor | Admin |
|------------|----------|------------|-----------------|-------|
| **Daily** | ✅ Crear/Editar | ❌ No | ❌ No | ✅ Ver |
| **Specials** | ✅ Crear | ✅ Revisar/Aprobar | ✅ Revisar/Aprobar | ✅ Ver |
| **Covers** | ✅ Solicitar | ✅ Aprobar | ✅ Gestionar | ✅ Completo |
| **Reports** | ❌ No | ❌ No | ✅ Completo | ✅ Completo |
| **Admin Panel** | ❌ No | ❌ No | ❌ No | ✅ Completo |

---

## 🏗️ Arquitectura Modularizada

### **OperatorBlackboard** (Contenedor de tabs)
```
Tabs:
├── 📝 Daily         # ⭐ Crear eventos regulares - DailyModule
├── ⭐ Specials      # ⭐ Crear eventos especiales - SpecialsModule
└── 🔄 Covers        # Solicitar covers
```

**Funcionalidades Daily:**
- Crear eventos (START SHIFT, Break, Delivery, etc.)
- Editar eventos propios
- Eliminar eventos propios

**Funcionalidades Specials:**
- Crear eventos de grupos especiales (AS, KG, HUD, PE, etc.)
- Ver sus propios eventos especiales
- Esperar aprobación de supervisores
- Ver historial desde START SHIFT

### **SupervisorDashboard**
```
Tabs: (Supervisor):**
- Ver eventos especiales de TODOS los operadores
- Marcar eventos como flagged/last
- Enviar a otros supervisores
- Aprobar/rechazar eventos
- NO puede crear, solo supervis
**Funcionalidades Specials:**
- Ver eventos de grupos especiales (AS, KG, HUD, PE, etc.)
- Marcar eventos como flagged/last
- Enviar a supervisores
- Aprobar/rechazar

### **AdminDashboard**
```
Tabs:
├── 👥 Users
├── 📍 Sites
├── 📋 Activities
├── 📊 Reports
└── ⚙️ Config
```

---

## 📝 Flujo de Eventos

### **1. Operador Crea Evento (Daily)**
```
Operador → DailyModule → Eventos table
    ↓
Evento guardado con ID_Usuario del operador
    ↓
Aparece en tksheet de Daily
```
Operador Crea Evento Especial**
```
Operador → SpecialsModule → Crea evento especial
    ↓
Evento guardado en tabla specials
    ↓
Espera revisión de supervisor
```

### **3. Supervisor Revisa Specials**
```
SupervisorDashboard → SpecialsModule
    ↓
Query eventos especiales de TODOS los operadores
    ↓
Supervisor marca/aprueba
    ↓
Actualiza estado
Se guarda en tabla specials
```

### **3. Admin Ve Todo**
```
AdminDashboard → Acceso completo
    ↓
Puede ver Daily, Specials, Covers, Reports
    ↓
Solo con propósito de auditoría/configuración
```

---Operador)**
1. Crea eventos de grupos especiales (AS, KG, HUD, PE, SCH, WAG, LT, DT)
2. Ve solo sus propios eventos especiales
3. No puede aprobar, solo crear
4. Espera validación de supervisor

### **Specials (Supervisor)**
1. Ve eventos especiales de TODOS los operadores
2. Solo de grupos especiales (AS, KG, HUD, PE, SCH, WAG, LT, DT)
3. No puede cre
### **Daily (Operador)**
1. Solo puede ver sus propios eventos
2. Puede editar eventos desde último START SHIFT
3. No puede editar eventos de otros operadores
4. Debe tener START SHIFT activo para crear eventos

### **Specials (Supervisor)**
1. Ve eventos de TODOS los operadores
2. Solo de grupos especiales (AS, KG, HUD, PE, SCH, WAG, LT, DT)
3. No puede editar, solo marcar/aprobar
4. Puede enviar a otros supervisores

### **Covers (Ambos)**
1. Operador: Solicita cover
2. Supervisor: Aprueba/asigna cover
3. Sistema: Tracking en gestion_breaks_programados

---

## 🎨 Blackboard Implementado

### **✅ OperatorBlackboard**
- Archivo: `views/operator_blackboard.py`
- Hereda de: `Blackboard` (clase base)
- Tabs: Daily (✅), Specials (⏳), Covers (⏳)
- DailyModule: ✅ Integrado y funcional
- **ENFOQUE ACTUAL:** Solo Daily trabajando

---

## 📁 MódOPERADOR (crear) + SUPERVISOR (revisar)**
- Estado: ⏳ Pendiente
- Funcionalidades planificadas:
  - TkSheet con 8 columnas (+ Time_Zone, Marca)
  - **Vista Operador:** Crear eventos, editar propios
  - **Vista Supervisor:** Solo lectura, marcar, aprobar
  - Colores por estado
  - Botones diferentes por rols
  - Edición directa
  - Auto-save
  - Eliminar eventos
  - Refrescar datos

### **⏳ SpecialsModule**
- Archivo: `views/modules/specials_module.py`
- Rol: **SUPERVISOR**
- Estado: ⏳ Pendiente
- Funcionalidades planificadas:
  - TkSheet con 8 columnas (+ Time_Zone, Marca)
  - Solo lectura
  - Colores por estado
  - Marcar eventos
  - Enviar a supervisores

---

## 🚀 Próximos Pasos (En Orden)

1. **SpecialsModule para Supervisor**
   - Migrar lógica de `load_specials()` de operator_window.py
   - Integrar en SupervisorDashboard
   - Testing completo

2. **CoversModule para ambos roles**
   - Vista para Operador (solicitar)
   - Vista para Supervisor (aprobar)
   - Integración con gestion_breaks_programados

3. **BaseSheetModule (Abstracción)**
   - Identificar código común
   - Crear clase base
   - Refactorizar Daily y Specials

---(crear)              ║
║  SPECIALS = OPERADOR (crear)           ║
║           + SUPERVISOR (revisar)       ║
║                                        ║
║  Operadores CREAN en Daily y Specials  ║
║  Supervisores REVISAN Specials   
╔════════════════════════════════════════╗
║  DAILY = OPERADOR                      ║
║  SPECIALS = SUPERVISOR                 ║
║                                        ║
║  Operadores crean eventos en Daily     ║
║  Supervisores revisan en Specials      ║
╚════════════════════════════════════════╝
```

---
OperatorDashboard (crear) + SupervisorDashboard (revisar/aprobar)
## 📞 Referencias Rápidas

### **¿Quién usa DailyModule?**
→ **OperatorDashboard ÚNICAMENTE**

### **¿Quién usa SpecialsModule?**
→ **SupervisorDashboard y LeadSupervisorDashboard**

### **¿Operadores crean eventos?**
→ **Sí, en Daily (tabla Eventos)**
Operadores crean eventos especiales?**
→ **Sí, en Specials (tabla specials)**

### **¿Supervisores crean eventos?**
→ **No, solo revisan y aprueban en Specials
→ **No, solo revisan en Specials (tabla specials)**

---

**Última actualización:** 2025-12-14
**Estado de memoria:** ✅ PERSISTENTE PARA TODO EL PROYECTO
