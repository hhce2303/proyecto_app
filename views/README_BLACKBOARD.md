# Blackboard - Documentación

## 📋 Concepto

**Blackboard** (pizarra) es la clase base para contenedores de tabs modulares.
Diseñada para reemplazar progresivamente el monolito `operator_window.py`.

## 🎯 Propósito

Modularizar `operator_window.py` sin romper funcionalidad existente:
- Extraer lógica de cada "modo" (daily, specials, covers) a módulos independientes
- Aplicar patrón MVC correctamente
- Mantener compatibilidad con sistema actual

## 🏗️ Arquitectura

```
Blackboard (clase padre)
└── OperatorBlackboard
    ├── Tab Daily → DailyModule ✅
    ├── Tab Specials → (pendiente)
    └── Tab Covers → (pendiente)
```

### Patrón: Template Method

**Blackboard** define estructura:
```python
def _build(self):
    self._create_window()      # Ventana base
    self._create_header()      # Header superior
    self._create_tabs()        # Tabs de navegación
    self._create_content_area() # Área de contenido
    
    # Hooks para subclases:
    self._setup_header_content()
    self._setup_tabs_content()
    self._setup_content()
```

**OperatorBlackboard** implementa hooks:
```python
def _setup_content(self, parent):
    daily_frame = self.ui_factory.frame(parent)
    
    self.daily_module = DailyModule(
        parent=daily_frame,
        username=self.username,
        # ...
    )
```

## 📁 Estructura de Archivos

```
views/
├── blackboard.py              # Clase base
├── operator_blackboard.py     # Para operadores
└── modules/
    ├── daily_module.py        # ✅ Módulo Daily (CRUD eventos)
    ├── specials_module.py     # ⏳ Pendiente
    └── covers_module.py       # ⏳ Pendiente
```

## ✅ Estado Actual

### Implementado
- ✅ `Blackboard` - Clase base con Template Method
- ✅ `OperatorBlackboard` - Contenedor para operadores
- ✅ `DailyModule` - Tab Daily completamente funcional
  - TkSheet con 6 columnas
  - CRUD completo
  - Auto-save (500ms)
  - Refrescar/Eliminar

### Pendiente
- ⏳ `SpecialsModule` - Para eventos especiales
- ⏳ `CoversModule` - Para solicitudes de cover
- ⏳ Migración completa de `operator_window.py`

## 🔧 Uso

### Crear Blackboard para operador

```python
from views.operator_blackboard import OperatorBlackboard

blackboard = OperatorBlackboard(
    username="operador1",
    role="Operador",
    session_id=123,
    station="ST-001",
    root=None  # Crea su propia ventana
)

blackboard.show()
```

### Integrar nuevo módulo

```python
# En operator_blackboard.py - _setup_content()

# Tab Specials
specials_frame = self.ui_factory.frame(parent)

self.specials_module = SpecialsModule(
    parent=specials_frame,
    username=self.username,
    session_id=self.session_id,
    role=self.role,
    UI=self.UI
)

self.tab_frames["Specials"] = specials_frame
```

## 🚫 Lo que NO es Blackboard

- ❌ NO reemplaza el sistema de supervisores (`backend_super.py`)
- ❌ NO incluye AdminDashboard ni SupervisorDashboard
- ❌ NO es un sistema completo de dashboards estadísticos

**Blackboard es SOLO para modularizar operator_window.py**

## 📝 Diferencias vs operator_window.py

### operator_window.py (Monolito)
```python
# Todo en un archivo de 3000+ líneas
class OperatorWindow:
    def toggle_mode(self, mode):
        if mode == "daily":
            self.load_daily()  # 200 líneas
        elif mode == "specials":
            self.load_specials()  # 300 líneas
        # ...
```

### OperatorBlackboard (Modular)
```python
# Dividido en módulos independientes
class OperatorBlackboard:
    def _setup_content(self):
        self.daily_module = DailyModule(...)
        self.specials_module = SpecialsModule(...)
```

## 🔄 Plan de Migración

1. ✅ **Fase 1:** DailyModule funcionando en OperatorBlackboard
2. ⏳ **Fase 2:** SpecialsModule
3. ⏳ **Fase 3:** CoversModule
4. ⏳ **Fase 4:** Migrar funciones restantes de operator_window.py
5. ⏳ **Fase 5:** Reemplazar operator_window.py por OperatorBlackboard

## 🧪 Testing

```bash
# Probar OperatorBlackboard con DailyModule
python test_operator_blackboard.py
```

## 📚 Referencias

- `views/modules/README_DAILY_MODULE.md` - Documentación de DailyModule
- `ROLES_Y_PERMISOS.md` - Permisos y roles del sistema
- `operator_window.py` - Sistema monolítico actual

---

**Última actualización:** 2025-12-14
**Estado:** Fase 1 completada - Daily funcionando
**Próximo:** SpecialsModule
