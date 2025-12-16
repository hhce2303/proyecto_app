# OperatorBlackboard - Documentación Completa

## 📋 Resumen General

`OperatorBlackboard` es el contenedor principal de la interfaz de operador en el sistema, implementado bajo los principios de POO, MVC y Buenas Prácticas de Programación (BPP). Hereda de `Blackboard` y organiza la experiencia del operador en tabs: **Daily**, **Specials**, **Covers** y **Lista Covers**. Cada tab es un módulo desacoplado, con lógica y UI propias, y la clase orquesta la navegación, control de turnos, y la integración de funcionalidades clave para la operación diaria.

---

## 🗂️ Estructura y Tabs

- **Daily**: Registro de eventos diarios del operador. Incluye formulario de alta, validación de turno activo, y visualización de eventos.
- **Specials**: Gestión de eventos especiales (grupos especiales). Permite enviar eventos al supervisor, muestra estado de sincronización (enviado/pendiente), y color coding.
- **Covers**: Visualización y gestión de covers realizados y programados. Incluye duración, posición en turno, cancelación de covers activos, y color coding.
- **Lista Covers**: Tab especial para visualizar covers programados, accesible solo si el usuario está "Activo".

---

## 🧩 Funcionalidades Principales

### 1. **Gestión de Tabs y Navegación**
- Tabs: Daily, Specials, Covers, Lista Covers.
- Botones de navegación con estilos dinámicos.
- Cambio de tab recarga datos del módulo correspondiente.
- Botón "Lista de Covers" solo visible si el usuario está activo (status 2), verificado cada 500ms.

### 2. **Control de Turnos (Shift)**
- **Start Shift**: Habilita el registro de eventos y covers. Cambia el estado de la UI y activa controles.
- **End Shift**: Finaliza el turno, deshabilita controles y oculta formularios.
- **shift_warning_label**: Mensaje visible cuando no hay turno activo.
- Validación de turno activo antes de permitir acciones críticas (registrar evento, solicitar/registrar cover).

### 3. **DailyModule**
- Visualización de eventos diarios en tksheet.
- Formulario de alta alineado con columnas del sheet.
- Campos: Fecha/Hora (con selector), Sitio, Actividad, Cantidad, Cámara, Descripción.
- Botón para agregar evento.
- Validación de campos y atajos de teclado (Enter para submit).

### 4. **SpecialsModule**
- Visualización de eventos especiales.
- Estado de sincronización con supervisor (enviado/pendiente) con color coding.
- Botones: "Enviar Seleccionados", "Enviar Todos".
- Toolbar para acciones rápidas.
- Recarga automática de datos al cambiar de tab.

### 5. **CoversModule**
- Visualización de covers realizados y programados desde el último Start Shift.
- Columnas: Usuario, Time Request, Cover In, Cover Out, Duración, Turno, Motivo, Covered By, Activo.
- Color coding: Verde para activos, gris para completados.
- Botón "Cancelar Cover" para covers activos.
- Info label con estadísticas de covers.
- Recarga automática de datos al cambiar de tab.

### 6. **Lista Covers (CoversListModule)**
- Tab especial para visualizar covers programados.
- Acceso restringido a usuarios activos.
- Botón en toolbar que cambia de visibilidad según estado del usuario.

### 7. **Solicitar y Registrar Cover**
- **Solicitar Cover**: Abre diálogo para solicitar un cover, validando turno activo.
- **Registrar Cover**: Abre diálogo para registrar un cover realizado, con cambio de sesión automático.
- Validaciones y manejo de errores en ambos flujos.

### 8. **Auto-Refresh y Actualización de UI**
- Actualización periódica de controles y botones según estado del usuario y del turno.
- Recarga de datos en módulos al cambiar de tab.
- Refresco automático de estadísticas y listas.

### 9. **Manejo de Sesión y Logout**
- Handler para logout con confirmación.
- Handler para cierre de ventana con confirmación.

---

## 🏗️ Arquitectura y Principios

- **POO**: Cada módulo/tab es una clase independiente.
- **MVC**: Separación clara entre vista (módulos), controlador (controllers), y modelo (models/BD).
- **BPP**: Sin duplicación de lógica, validaciones centralizadas, UI desacoplada de la lógica de negocio.
- **Extensibilidad**: Fácil agregar nuevos tabs o funcionalidades sin romper lo existente.

---

## 🔄 Métodos Clave

- `__init__`: Inicializa el Blackboard, módulos, y controles de turno.
- `_build`: Construye la UI y arranca el auto-refresh.
- `_setup_tabs_content`: Crea los botones de tabs y toolbar.
- `_setup_content`: Instancia los módulos y frames de cada tab.
- `_switch_tab`: Cambia de tab y recarga datos.
- `_show_current_tab`: Muestra el frame del tab activo.
- `_update_tab_buttons`: Actualiza el estilo de los botones de tabs.
- `_request_cover`: Lógica para solicitar un cover.
- `_register_cover`: Lógica para registrar un cover realizado.
- `_start_shift` / `_end_shift`: Control de inicio y fin de turno.
- `_update_shift_controls`: Habilita/deshabilita controles según estado del turno.
- `_start_auto_refresh` / `_auto_refresh_cycle` / `_stop_auto_refresh`: Control de refresco automático de UI.

---

## 📝 Notas de Uso y Extensión

- Para agregar un nuevo tab, crear el módulo correspondiente y agregarlo en `_setup_content` y `_setup_tabs_content`.
- Para modificar la lógica de covers, modificar `CoversModule` y su controller, sin tocar OperatorBlackboard.
- Para cambiar la lógica de visibilidad de botones, ajustar la función de verificación periódica en `_setup_tabs_content`.

---

## 📊 Métricas y Mantenimiento

- **Líneas de código**: ~1600 (incluyendo métodos heredados y comentarios)
- **Tabs implementados**: 4
- **Módulos desacoplados**: 4
- **Controladores asociados**: 3 (Daily, Specials, Covers)
- **Dependencias externas**: tksheet, tkcalendar, modelos y controladores propios

---

## 🚀 Conclusión

`OperatorBlackboard` es el núcleo de la experiencia de operador, integrando todas las funcionalidades críticas en una interfaz modular, extensible y robusta. Su diseño permite mantener y evolucionar el sistema fácilmente, garantizando una experiencia de usuario fluida y segura.
