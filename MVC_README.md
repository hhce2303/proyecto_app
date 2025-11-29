"""
📝 README - Arquitectura MVC

# Estructura del Proyecto Daily Log System

Este proyecto ha sido migrado a una arquitectura **Modelo-Vista-Controlador (MVC)** para mejorar la mantenibilidad y escalabilidad.

## 📁 Estructura de Carpetas

```
proyecto_app/
├── models/              # Modelos de datos (acceso a BD)
├── views/               # Interfaces de usuario
│   └── components/      # Componentes UI reutilizables
├── controllers/         # Lógica de aplicación
├── utils/               # Utilidades y helpers
├── services/            # Servicios de negocio
├── config/              # Archivos de configuración
├── migrations/          # Migraciones de BD
├── tests/               # Pruebas unitarias
└── logs/                # Logs de la aplicación
```

## 🔄 Flujo de Datos MVC

1. **Usuario** interactúa con la **Vista**
2. **Vista** llama al **Controlador**
3. **Controlador** usa el **Modelo** para acceder a datos
4. **Modelo** retorna datos al **Controlador**
5. **Controlador** actualiza la **Vista**
6. **Vista** muestra el resultado al **Usuario**

## 🚀 Próximos Pasos de Migración

### Fase 1: Modelos ✅ (Estructura creada)
- [ ] Implementar DatabaseManager
- [ ] Migrar funciones de acceso a BD desde under_super.py
- [ ] Crear modelos para cada tabla

### Fase 2: Componentes UI
- [ ] Migrar FilteredCombobox a views/components/
- [ ] Migrar AutoCompleteEntry
- [ ] Crear DateTimePicker reutilizable

### Fase 3: Vistas
- [ ] Separar login.py en LoginView
- [ ] Separar main.py en MainView
- [ ] Separar ventanas de supervisor

### Fase 4: Controladores
- [ ] Implementar AuthController
- [ ] Implementar EventController
- [ ] Implementar SpecialController

## 📖 Convenciones de Código

- **Modelos**: Métodos estáticos, nombres en snake_case
- **Vistas**: Clases con métodos show(), close()
- **Controladores**: Coordinan entre vistas y modelos
- **Todos los archivos**: Docstrings detallados

## 🔗 Archivos Antiguos (Pendientes de Migración)

- `login.py` → `views/login_view.py` + `controllers/auth_controller.py`
- `main.py` → `views/main_view.py` + `controllers/event_controller.py`
- `backend_super.py` → Múltiples vistas y controladores
- `under_super.py` → `models/database.py` + `utils/helpers.py`

---

**Nota**: Los archivos antiguos NO deben ser modificados hasta completar la migración.
Una vez migrados, se marcarán como deprecated.
```
