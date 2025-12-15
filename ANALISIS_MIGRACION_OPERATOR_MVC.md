# 📊 Análisis Comparativo: operator_window.py vs operator_blackboard.py

## 🎯 Resumen Ejecutivo

**Migración**: De arquitectura monolítica (`operator_window.py` - 4306 líneas) a MVC modular (`operator_blackboard.py` - 1050 líneas)

**Reducción de código**: **75.6% menos líneas** en el blackboard principal gracias a la separación MVC.

**Estado actual**: ✅ Daily y Specials migrados | ⏳ Covers pendiente de migración completa

---

## 📋 Tabla de Comparación de Funcionalidades

| Funcionalidad | operator_window.py | operator_blackboard.py | Estado | Notas |
|---------------|-------------------|----------------------|--------|-------|
| **DAILY** |
| ✅ Mostrar eventos desde último START SHIFT | ✅ 4000+ líneas | ✅ 150 líneas (Blackboard) + 550 (DailyModule) | **MIGRADO** | MVC completo |
| ✅ Formulario de entrada inferior | ✅ Inline HTML-style | ✅ Mejorado con labels | **MIGRADO** | Mejor UX |
| ✅ Agregar evento con validación | ✅ Función inline | ✅ Controller | **MIGRADO** | Validación en controller |
| ✅ Edición inline (doble-click) | ✅ Hardcoded | ✅ Modular | **MIGRADO** | Picker reutilizable |
| ✅ Auto-save al editar | ✅ Sí | ✅ Sí (500ms delay) | **MEJORADO** | Más consistente |
| ✅ DateTime Picker | ✅ Función local 200 líneas | ✅ Blackboard method 250 líneas | **MIGRADO** | Reutilizable en todos los módulos |
| ✅ Site Picker (doble-click col 1) | ✅ Función local 150 líneas | ✅ DailyModule method 100 líneas | **MIGRADO** | FilteredCombobox |
| ✅ Activity Picker (doble-click col 2) | ✅ Función local 150 líneas | ✅ DailyModule method 100 líneas | **MIGRADO** | FilteredCombobox |
| ✅ Context Menu (4 opciones) | ✅ Sí | ✅ Sí | **MIGRADO** | Completo |
| ✅ Eliminar evento | ✅ Sí | ✅ Sí | **MIGRADO** | Con confirmación |
| ✅ Enter key binding en formulario | ✅ Sí | ✅ Sí | **MIGRADO** | Todos los campos |
| ⚠️ Ajuste de timezone en descripción | ✅ Regex timestamps [HH:MM:SS] | ❌ No implementado | **PENDIENTE** | Solo en Specials |
| **SPECIALS** |
| ✅ Mostrar eventos de grupos especiales | ✅ Hardcoded 300+ líneas | ✅ MVC (Controller 200 + Module 150) | **MIGRADO** | Grupos: AS, KG, HUD, PE, SCH, WAG, LT, DT |
| ✅ Comparación Eventos vs Specials | ✅ Cache volátil | ✅ FK ID_Eventos | **MEJORADO** | Sin cache, directo a BD |
| ✅ Estados: ✅ Enviado / ⏳ Pendiente / Sin enviar | ✅ Sí | ✅ Sí | **MIGRADO** | Comparación automática 6 campos |
| ✅ Color coding (verde/ámbar) | ✅ Sí | ✅ Sí | **MIGRADO** | Visual feedback |
| ✅ Ajuste de timezone (FechaHora + descripción) | ✅ Sí | ✅ Sí | **MIGRADO** | Regex timestamps |
| ✅ Selector de supervisor (CTkOptionMenu) | ✅ Sí | ✅ Sí | **MIGRADO** | Query supervisores activos |
| ✅ Enviar seleccionados | ✅ Sí | ✅ Sí | **MIGRADO** | INSERT/UPDATE automático |
| ✅ Enviar todos | ✅ Sí | ✅ Sí | **MIGRADO** | Procesa todas las filas |
| ✅ UPSERT inteligente (INSERT vs UPDATE) | ✅ Cache ID_special | ✅ Query by ID_Eventos FK | **MEJORADO** | Más confiable |
| ✅ Toolbar con botones de envío | ✅ 2 botones | ✅ 2 botones | **MIGRADO** | Mismo comportamiento |
| **COVERS** |
| ✅ Mostrar covers realizados | ✅ load_covers() 200 líneas | ❌ Placeholder | **PENDIENTE MIGRACIÓN** | Ver propuesta abajo |
| ✅ LEFT JOIN covers_programados | ✅ Sí | ❌ No | **PENDIENTE** | Incluir covers de emergencia |
| ✅ Filtrar por username | ✅ Sí | ❌ No | **PENDIENTE** | WHERE Nombre_usuarios |
| ✅ Columnas: [Nombre, Time Request, Cover in/out, Motivo, Covered by, Activo] | ✅ 7 columnas | ❌ Placeholder | **PENDIENTE** | Definir en CoversModule |
| ⚠️ **Duración del cover** | ❌ No | ❌ No | **NUEVA FEATURE** | Calcular Cover_out - Cover_in |
| ⚠️ **Posición en turno/cola** | ✅ update_cover_queue_position() 40 líneas | ❌ No | **PENDIENTE** | Mostrar "Turno X de Y" |
| ⚠️ **Cancelar cover solicitado** | ❌ No | ❌ No | **NUEVA FEATURE** | UPDATE is_Active = 0 en covers_programados |
| ✅ Modo solo lectura (no editable) | ✅ sheet.disable("edit_cell") | ❌ No implementado | **PENDIENTE** | Deshabilitar edición |
| ✅ Auto-refresh cada 30s | ✅ Sí | ❌ No | **PENDIENTE** | Para actualizar posición en cola |
| **HEADER / GLOBAL** |
| ✅ Botón Start/End Shift | ✅ Dinámico (verde/rojo) | ❌ No | **FUNCIONALIDAD PERDIDA** | Importante recuperar |
| ✅ Botón Registrar Cover | ✅ Abre cover_mode() | ❌ No | **FUNCIONALIDAD PERDIDA** | Importante recuperar |
| ✅ Botón Solicitar Cover | ✅ request_covers() | ❌ No | **FUNCIONALIDAD PERDIDA** | Importante recuperar |
| ✅ Botón Ver Covers | ✅ switch_to_covers() | ❌ No | **FUNCIONALIDAD PERDIDA** | Importante recuperar |
| ✅ Label próximo cover programado | ✅ get_next_cover_info() 70 líneas | ❌ No | **FUNCIONALIDAD PERDIDA** | Info útil para operador |
| ✅ Label covers asignados (covering) | ✅ get_covering_assignment() 60 líneas | ❌ No | **FUNCIONALIDAD PERDIDA** | Multi-línea con todos los covers |
| ✅ Auto-refresh labels cada 30s | ✅ auto_refresh_cover_labels() | ❌ No | **FUNCIONALIDAD PERDIDA** | Importante para covers |
| ✅ Panel lateral de noticias (SLC News) | ✅ create_news_panel() 200 líneas | ❌ No | **FUNCIONALIDAD PERDIDA** | Info de tabla `information` |
| ✅ Botón Refrescar | ✅ Header | ✅ Toolbar por módulo | **MIGRADO** | Cada módulo se refresca |
| ✅ Botón Eliminar | ✅ Header | ✅ DailyModule | **MIGRADO** | Solo en Daily |
| ✅ Toggle Daily/Specials | ✅ toggle_mode() | ✅ Tabs en Blackboard | **MEJORADO** | Arquitectura de tabs más limpia |
| **OTROS** |
| ✅ Singleton window management | ✅ _register_singleton() | ✅ Herencia de Blackboard | **MIGRADO** | Ventana única |
| ✅ CustomTkinter + Tkinter fallback | ✅ Sí | ✅ Sí | **MIGRADO** | UI moderna |
| ✅ Dark theme | ✅ Sí | ✅ Sí | **MIGRADO** | Consistente |

---

## 🔍 Análisis de Lógica de Negocio en operator_blackboard.py

### ✅ **Aspectos Positivos**:

1. **Separación MVC correcta**:
   - ✅ Vista (Blackboard): Solo UI, eventos, referencias
   - ✅ Controlador (DailyController): Validaciones, transformaciones
   - ✅ Modelo (daily_model): Solo queries SQL

2. **Reutilización de código**:
   - ✅ `_show_datetime_picker()`: Método del Blackboard reutilizable por todos los módulos
   - ✅ `UIFactory`: Capa de abstracción para CustomTkinter/Tkinter
   - ✅ `FilteredCombobox`: Importado de under_super.py

3. **Blackboard como Template Method**:
   - ✅ Métodos abstractos: `_setup_tabs_content()`, `_setup_content()`
   - ✅ Herencia: OperatorBlackboard, SupervisorBlackboard, LeadBlackboard
   - ✅ Factory: `open_blackboard_by_role()`

4. **Referencias bidireccionales limpias**:
   ```python
   self.daily_module.blackboard = self  # Módulo accede a _show_datetime_picker()
   ```

### ⚠️ **Áreas que necesitan limpieza**:

#### **1. Lógica de negocio residual en Blackboard (Líneas 330-600)**:

**Problema**: Método `_create_event_form()` tiene **270 líneas** con:
- Creación de formulario (OK - es UI)
- Métodos `_get_sites()`, `_get_activities()` → ❌ **DEBERÍAN estar en Controller**
- Método `_add_event()` con validaciones → ❌ **DEBERÍA estar en Controller**

**Propuesta**:
```python
# ACTUAL (operator_blackboard.py líneas 420-470)
def _add_event(self):
    # Validar campos obligatorios
    if not site_text or not activity:
        messagebox.showwarning(...)  # ❌ Lógica en Vista
    
    # Extraer ID del sitio
    try:
        site_id = int(site_text.split("(")[-1].split(")")[0])  # ❌ Parsing en Vista
    
    # Validar cantidad
    try:
        quantity_val = int(quantity)  # ❌ Validación en Vista
    
    # Llamar al controller (OK)
    success, message = self.controller.create_event(...)

# DEBERÍA SER:
def _add_event(self):
    # Solo obtener valores del formulario
    form_data = {
        'site': self.site_combo.get(),
        'activity': self.activity_combo.get(),
        'quantity': self.quantity_entry.get(),
        'camera': self.camera_entry.get(),
        'description': self.description_entry.get()
    }
    
    # Delegar TODO al controller
    success, message = self.controller.create_event_from_form(form_data)
    
    if success:
        self._clear_form()
        self.daily_module.load_data()
    else:
        messagebox.showerror("Error", message, parent=self.window)
```

**Beneficio**: Vista solo maneja UI, Controller valida y parsea.

---

#### **2. Método `_show_datetime_picker()` demasiado largo (250 líneas)**:

**Problema**: Método en Blackboard con lógica de UI compleja.

**Propuesta**: Extraer a clase separada `DateTimePickerDialog`:
```python
# views/dialogs/datetime_picker_dialog.py
class DateTimePickerDialog:
    def __init__(self, parent, ui_factory, callback, initial_datetime=None):
        self.parent = parent
        self.ui_factory = ui_factory
        self.callback = callback
        self.initial_dt = initial_datetime or datetime.now()
        self._create_dialog()
    
    def _create_dialog(self):
        # 250 líneas de creación de ventana modal
        ...
    
    def show(self):
        self.dialog.transient(self.parent)
        self.dialog.grab_set()

# Uso en Blackboard (1 línea):
def _show_datetime_picker(self, callback, initial_datetime=None):
    DateTimePickerDialog(self.window, self.ui_factory, callback, initial_datetime).show()
```

**Beneficio**: Blackboard más legible, diálogo reutilizable y testeable.

---

#### **3. Métodos de Supervisores en Blackboard (Líneas 850-1050)**:

**Problema**: Métodos `_send_selected_specials()`, `_send_all_specials()`, `_show_supervisor_selector()` tienen **200 líneas** en Blackboard.

**Propuesta**: Ya están bien separados, pero `_show_supervisor_selector()` debería extraerse:
```python
# views/dialogs/supervisor_selector_dialog.py
class SupervisorSelectorDialog:
    def __init__(self, parent, ui_factory, controller, evento_ids):
        # Lógica de ventana modal
        ...

# Uso en Blackboard:
def _show_supervisor_selector(self, evento_ids):
    SupervisorSelectorDialog(
        self.window, 
        self.ui_factory, 
        self.specials_module.controller, 
        evento_ids
    ).show()
```

---

### 📏 **Métrica de limpieza actual**:

| Archivo | Líneas | Lógica UI | Lógica Negocio | Ratio UI/Negocio |
|---------|--------|-----------|----------------|------------------|
| **operator_window.py** | 4306 | ~3500 | ~800 | 81% UI / 19% Negocio ❌ |
| **operator_blackboard.py** | 1050 | ~900 | ~150 | 86% UI / 14% Negocio ⚠️ |
| **DailyModule** | 550 | ~500 | ~50 | 91% UI / 9% Negocio ✅ |
| **DailyController** | 200 | 0 | ~200 | 0% UI / 100% Negocio ✅ |
| **SpecialsOperatorController** | 414 | 0 | ~414 | 0% UI / 100% Negocio ✅ |

**Objetivo**: Reducir lógica de negocio en Blackboard a **< 5%** (50 líneas máximo).

---

## 🚀 Propuesta: Migración Completa de COVERS con MVC

### **Arquitectura propuesta**:

```
views/operator_blackboard.py (Blackboard)
    │
    ├─ views/modules/daily_module.py ✅
    │   └─ controllers/daily_controller.py
    │       └─ models/daily_model.py
    │
    ├─ views/modules/specials_module.py ✅
    │   └─ controllers/specials_operator_controller.py
    │       └─ models/specials_model.py
    │
    └─ views/modules/covers_module.py ⏳ NUEVO
        └─ controllers/covers_operator_controller.py ⏳ NUEVO
            └─ models/cover_model.py ✅ YA EXISTE (reusar)
            └─ models/cover_time_model.py ✅ YA EXISTE (reusar)
```

---

### **1. Crear CoversModule** (`views/modules/covers_module.py`):

```python
"""
CoversModule - Módulo para visualizar y gestionar covers del operador.
Muestra covers realizados con duración, posición en turno y opción de cancelar.
"""
import tkinter as tk
from tksheet import Sheet
from datetime import datetime, timedelta
from controllers.covers_operator_controller import CoversOperatorController
from utils.ui_factory import UIFactory


class CoversModule:
    """
    Módulo Covers - Gestiona visualización de covers realizados y programados.
    """
    
    # Configuración de columnas
    COLUMNS = [
        "Nombre Usuario",
        "Time Request",
        "Cover In",
        "Cover Out",
        "Duración",  # ⭐ NUEVA
        "Turno",     # ⭐ NUEVA
        "Motivo",
        "Covered By",
        "Activo"
    ]
    
    COLUMN_WIDTHS = {
        "Nombre Usuario": 150,
        "Time Request": 150,
        "Cover In": 140,
        "Cover Out": 140,
        "Duración": 100,  # ⭐ NUEVA - "45 min", "1h 20min"
        "Turno": 80,      # ⭐ NUEVA - "3/7" (turno 3 de 7)
        "Motivo": 180,
        "Covered By": 150,
        "Activo": 80
    }
    
    def __init__(self, container, username, ui_factory, UI=None):
        self.container = container
        self.username = username
        self.ui_factory = ui_factory
        self.UI = UI
        
        # Referencia al blackboard
        self.blackboard = None
        
        # Estado
        self.row_data = []
        self.row_ids = []  # IDs de covers_realizados
        self.programados_ids = []  # IDs de covers_programados (para cancelar)
        
        # Controller
        self.controller = CoversOperatorController(username)
        
        # Renderizar
        self.render()
    
    def render(self):
        """Renderiza el módulo completo"""
        self._create_toolbar()
        self._create_sheet()
        self.load_data()
    
    def _create_toolbar(self):
        """Crea toolbar con botones de acción"""
        toolbar = self.ui_factory.frame(self.container, fg_color="#2c2f33")
        toolbar.pack(fill="x", padx=10, pady=(10, 5))
        
        # Botón Refrescar
        self.ui_factory.button(
            toolbar,
            text="🔄 Refrescar",
            command=self.load_data,
            width=120
        ).pack(side="left", padx=5)
        
        # Botón Cancelar Cover (solo covers con Activo=1)
        self.ui_factory.button(
            toolbar,
            text="❌ Cancelar Cover",
            command=self._cancel_selected_cover,
            width=150,
            fg_color="#d32f2f",
            hover_color="#b71c1c"
        ).pack(side="left", padx=5)
        
        # Label de información
        self.info_label = self.ui_factory.label(
            toolbar,
            text="",
            fg="#00bfae",
            font=("Segoe UI", 12)
        )
        self.info_label.pack(side="right", padx=10)
    
    def _create_sheet(self):
        """Crea tksheet para mostrar covers"""
        sheet_frame = self.ui_factory.frame(self.container, fg_color="#2c2f33")
        sheet_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        
        self.sheet = Sheet(
            sheet_frame,
            headers=self.COLUMNS,
            theme="dark blue",
            show_row_index=True,
            show_top_left=False
        )
        
        # ⭐ MODO SOLO LECTURA - No se puede editar
        self.sheet.enable_bindings([
            "single_select",
            "drag_select",
            "column_select",
            "row_select",
            "column_width_resize",
            "arrowkeys",
            "right_click_popup_menu",
            "copy"
        ])
        # ❌ NO habilitar "edit_cell" - es solo lectura
        
        self.sheet.pack(fill="both", expand=True)
        
        # Aplicar anchos
        for idx, col_name in enumerate(self.COLUMNS):
            width = self.COLUMN_WIDTHS.get(col_name, 100)
            self.sheet.column_width(column=idx, width=width)
    
    def load_data(self):
        """Carga covers desde el controller"""
        try:
            # Obtener datos del controller
            data = self.controller.load_covers_data()
            
            # Limpiar sheet
            self.sheet.set_sheet_data([[]])
            self.row_data = []
            self.row_ids = []
            self.programados_ids = []
            
            if not data:
                self.info_label.configure(text="No hay covers para mostrar")
                return
            
            # Preparar datos para sheet
            sheet_data = []
            for item in data:
                sheet_data.append([
                    item['nombre_usuario'],
                    item['time_request'],
                    item['cover_in'],
                    item['cover_out'],
                    item['duracion'],      # ⭐ NUEVA - "45 min"
                    item['turno'],         # ⭐ NUEVA - "3/7"
                    item['motivo'],
                    item['covered_by'],
                    item['activo']
                ])
                
                self.row_ids.append(item['id_cover_realizado'])
                self.programados_ids.append(item['id_cover_programado'])
            
            # Actualizar sheet
            self.sheet.set_sheet_data(sheet_data)
            
            # Color coding por estado
            self._apply_row_colors(data)
            
            # Actualizar info
            activos = sum(1 for item in data if item['activo'] == 'Sí')
            self.info_label.configure(
                text=f"📊 {len(data)} covers | ✅ {activos} activos"
            )
            
            print(f"[DEBUG] CoversModule: Cargados {len(data)} covers")
            
        except Exception as e:
            print(f"[ERROR] CoversModule.load_data: {e}")
            import traceback
            traceback.print_exc()
    
    def _apply_row_colors(self, data):
        """Aplica colores según estado del cover"""
        for idx, item in enumerate(data):
            if item['activo'] == 'Sí':
                # Cover activo/programado - verde
                self.sheet.highlight_rows(
                    rows=[idx],
                    bg="#1b4d3e",
                    fg="#00c853",
                    highlight_index=False
                )
            elif item['cover_out']:
                # Cover completado - gris
                self.sheet.highlight_rows(
                    rows=[idx],
                    bg="#2b2b2b",
                    fg="#999999",
                    highlight_index=False
                )
    
    def _cancel_selected_cover(self):
        """Cancela el cover programado seleccionado"""
        from tkinter import messagebox
        
        try:
            # Obtener fila seleccionada
            selected = self.sheet.get_selected_rows()
            if not selected:
                messagebox.showwarning(
                    "Sin selección",
                    "Selecciona un cover para cancelar",
                    parent=self.container
                )
                return
            
            row_idx = list(selected)[0]
            
            # Verificar que tenga ID de cover programado
            if row_idx >= len(self.programados_ids):
                return
            
            programado_id = self.programados_ids[row_idx]
            if not programado_id:
                messagebox.showinfo(
                    "Cover no cancelable",
                    "Este cover ya fue realizado y no puede cancelarse",
                    parent=self.container
                )
                return
            
            # Confirmar cancelación
            row_data_dict = self.row_data[row_idx] if row_idx < len(self.row_data) else {}
            time_request = row_data_dict.get('time_request', 'N/A')
            
            confirm = messagebox.askyesno(
                "Confirmar Cancelación",
                f"¿Cancelar cover solicitado a las {time_request}?\n\n"
                f"Esta acción no se puede deshacer.",
                parent=self.container
            )
            
            if not confirm:
                return
            
            # Cancelar a través del controller
            success, message = self.controller.cancel_cover(programado_id)
            
            if success:
                messagebox.showinfo("Éxito", message, parent=self.container)
                self.load_data()  # Recargar
            else:
                messagebox.showerror("Error", message, parent=self.container)
        
        except Exception as e:
            messagebox.showerror(
                "Error",
                f"No se pudo cancelar el cover:\n{e}",
                parent=self.container
            )
            print(f"[ERROR] _cancel_selected_cover: {e}")
    
    def get_selected_rows(self):
        """Obtiene filas seleccionadas"""
        try:
            selected = self.sheet.get_selected_rows()
            return list(selected) if selected else []
        except Exception:
            return []
    
    def get_total_rows(self):
        """Obtiene total de filas"""
        try:
            return self.sheet.get_total_rows()
        except Exception:
            return len(self.row_data)
    
    def refresh(self):
        """Recarga datos"""
        self.load_data()
```

---

### **2. Crear CoversOperatorController** (`controllers/covers_operator_controller.py`):

```python
"""
CoversOperatorController - Controlador para lógica de covers del operador.
Maneja carga, cálculo de duración, posición en turno y cancelación.
"""
from datetime import datetime, timedelta
from models import cover_model, cover_time_model


class CoversOperatorController:
    """
    Controller para módulo Covers de operador.
    """
    
    def __init__(self, username):
        self.username = username
    
    def load_covers_data(self):
        """
        Carga covers realizados con información enriquecida.
        
        Returns:
            list: Lista de dicts con campos:
                - id_cover_realizado (int)
                - id_cover_programado (int or None)
                - nombre_usuario (str)
                - time_request (str)
                - cover_in (str)
                - cover_out (str or "En progreso")
                - duracion (str) - "45 min", "1h 20min"
                - turno (str) - "3/7" (posición/total)
                - motivo (str)
                - covered_by (str)
                - activo (str) - "Sí" o "No"
        """
        try:
            # Obtener último START SHIFT
            last_shift = self._get_last_shift_start()
            if not last_shift:
                print("[DEBUG] No hay último shift")
                return []
            
            # Query covers realizados desde último shift
            covers = cover_model.get_covers_realizados_by_user(
                username=self.username,
                fecha_desde=last_shift
            )
            
            if not covers:
                return []
            
            # Obtener posiciones en turno
            turnos_dict = self._calculate_turnos(covers)
            
            # Procesar cada cover
            processed = []
            for cover in covers:
                try:
                    # Extraer datos del cover
                    (
                        id_realizado, nombre_usuario, cover_in, cover_out,
                        motivo, covered_by, activo, id_programado, time_request
                    ) = cover
                    
                    # ⭐ CALCULAR DURACIÓN
                    duracion_str = self._calculate_duration(cover_in, cover_out)
                    
                    # ⭐ OBTENER TURNO
                    turno_str = turnos_dict.get(id_realizado, "N/A")
                    
                    # Formatear fechas
                    time_request_str = time_request.strftime("%Y-%m-%d %H:%M:%S") if time_request else "N/A"
                    cover_in_str = cover_in.strftime("%Y-%m-%d %H:%M:%S") if cover_in else "N/A"
                    cover_out_str = cover_out.strftime("%Y-%m-%d %H:%M:%S") if cover_out else "En progreso"
                    
                    activo_str = "Sí" if activo == 1 else "No"
                    
                    processed.append({
                        'id_cover_realizado': id_realizado,
                        'id_cover_programado': id_programado,
                        'nombre_usuario': nombre_usuario or "",
                        'time_request': time_request_str,
                        'cover_in': cover_in_str,
                        'cover_out': cover_out_str,
                        'duracion': duracion_str,
                        'turno': turno_str,
                        'motivo': motivo or "",
                        'covered_by': covered_by or "",
                        'activo': activo_str
                    })
                
                except Exception as e:
                    print(f"[ERROR] Error procesando cover: {e}")
                    continue
            
            return processed
        
        except Exception as e:
            print(f"[ERROR] load_covers_data: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def _get_last_shift_start(self):
        """Obtiene timestamp del último START SHIFT"""
        from models.database import get_connection
        
        try:
            conn = get_connection()
            if not conn:
                return None
            
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT MAX(FechaHora)
                FROM Eventos
                WHERE ID_Usuario = (SELECT ID_Usuario FROM user WHERE Nombre_Usuario = %s)
                AND Nombre_Actividad = 'START SHIFT'
            """, (self.username,))
            
            result = cursor.fetchone()
            
            cursor.close()
            conn.close()
            
            return result[0] if result and result[0] else None
        
        except Exception as e:
            print(f"[ERROR] _get_last_shift_start: {e}")
            return None
    
    def _calculate_duration(self, cover_in, cover_out):
        """
        Calcula duración del cover en formato legible.
        
        Args:
            cover_in (datetime): Inicio del cover
            cover_out (datetime or None): Fin del cover
        
        Returns:
            str: "45 min", "1h 20min", "En progreso"
        """
        if not cover_in:
            return "N/A"
        
        if not cover_out:
            # Cover en progreso - calcular desde ahora
            duration = datetime.now() - cover_in
            total_minutes = int(duration.total_seconds() / 60)
            
            if total_minutes < 60:
                return f"{total_minutes} min (en progreso)"
            else:
                hours = total_minutes // 60
                minutes = total_minutes % 60
                return f"{hours}h {minutes}min (en progreso)"
        
        # Cover completado
        duration = cover_out - cover_in
        total_minutes = int(duration.total_seconds() / 60)
        
        if total_minutes < 60:
            return f"{total_minutes} min"
        else:
            hours = total_minutes // 60
            minutes = total_minutes % 60
            if minutes == 0:
                return f"{hours}h"
            return f"{hours}h {minutes}min"
    
    def _calculate_turnos(self, covers):
        """
        Calcula posición en turno para cada cover.
        
        Lógica: Ordenar covers por Cover_in, asignar posición secuencial.
        
        Args:
            covers (list): Lista de tuplas de covers
        
        Returns:
            dict: {id_realizado: "3/7", ...}
        """
        try:
            # Ordenar por Cover_in
            sorted_covers = sorted(covers, key=lambda x: x[2] if x[2] else datetime.min)
            
            total = len(sorted_covers)
            turnos = {}
            
            for idx, cover in enumerate(sorted_covers, start=1):
                id_realizado = cover[0]
                turnos[id_realizado] = f"{idx}/{total}"
            
            return turnos
        
        except Exception as e:
            print(f"[ERROR] _calculate_turnos: {e}")
            return {}
    
    def cancel_cover(self, programado_id):
        """
        Cancela un cover programado (UPDATE is_Active = 0).
        
        Args:
            programado_id (int): ID del cover programado
        
        Returns:
            tuple: (success: bool, message: str)
        """
        try:
            success, message = cover_model.cancel_cover_programado(programado_id)
            return success, message
        
        except Exception as e:
            print(f"[ERROR] cancel_cover: {e}")
            import traceback
            traceback.print_exc()
            return False, str(e)
```

---

### **3. Extender cover_model.py** con funciones necesarias:

```python
# Agregar a models/cover_model.py

def get_covers_realizados_by_user(username, fecha_desde=None):
    """
    Obtiene covers realizados por usuario desde fecha específica.
    LEFT JOIN con covers_programados para incluir covers de emergencia.
    
    Args:
        username (str): Nombre del usuario
        fecha_desde (datetime): Fecha de inicio (por defecto último START SHIFT)
    
    Returns:
        list: Lista de tuplas (id_realizado, nombre_usuario, cover_in, cover_out,
                              motivo, covered_by, activo, id_programado, time_request)
    """
    try:
        conn = get_connection()
        if not conn:
            return []
        
        cursor = conn.cursor()
        
        query = """
            SELECT 
                cr.ID_Covers_realizados,
                cr.Nombre_usuarios,
                cr.Cover_in,
                cr.Cover_out,
                cr.Motivo,
                cr.Covered_by,
                cr.Activo,
                cr.ID_programacion_covers,
                cp.Time_request
            FROM covers_realizados cr
            LEFT JOIN covers_programados cp ON cr.ID_programacion_covers = cp.ID_Cover
            WHERE cr.Nombre_usuarios = %s
        """
        
        params = [username]
        
        if fecha_desde:
            query += " AND cr.Cover_in >= %s"
            params.append(fecha_desde)
        
        query += " ORDER BY cr.Cover_in DESC"
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return rows
    
    except Exception as e:
        print(f"[ERROR] get_covers_realizados_by_user: {e}")
        return []


def cancel_cover_programado(programado_id):
    """
    Cancela un cover programado (UPDATE is_Active = 0).
    
    Args:
        programado_id (int): ID del cover programado
    
    Returns:
        tuple: (success: bool, message: str)
    """
    try:
        conn = get_connection()
        if not conn:
            return False, "No hay conexión a la base de datos"
        
        cursor = conn.cursor()
        
        # Verificar que el cover esté activo
        cursor.execute("""
            SELECT is_Active, Time_request
            FROM covers_programados
            WHERE ID_Cover = %s
        """, (programado_id,))
        
        cover = cursor.fetchone()
        
        if not cover:
            cursor.close()
            conn.close()
            return False, "Cover no encontrado"
        
        if cover[0] == 0:
            cursor.close()
            conn.close()
            return False, "Este cover ya está cancelado"
        
        # Cancelar cover
        cursor.execute("""
            UPDATE covers_programados
            SET is_Active = 0
            WHERE ID_Cover = %s
        """, (programado_id,))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return True, "Cover cancelado exitosamente"
    
    except Exception as e:
        print(f"[ERROR] cancel_cover_programado: {e}")
        import traceback
        traceback.print_exc()
        return False, str(e)
```

---

### **4. Integrar en operator_blackboard.py**:

```python
# En _setup_content() de OperatorBlackboard

# ========== TAB COVERS (OPERADOR - VER COVERS) ==========
covers_frame = self.ui_factory.frame(parent, fg_color="#1e1e1e")

# CoversModule para mostrar covers realizados
try:
    self.covers_module = CoversModule(
        container=covers_frame,
        username=self.username,
        ui_factory=self.ui_factory,
        UI=self.UI
    )
    self.covers_module.blackboard = self
    print(f"[DEBUG] CoversModule inicializado para OPERADOR: {self.username}")
except Exception as e:
    print(f"[ERROR] No se pudo inicializar CoversModule: {e}")
    import traceback
    traceback.print_exc()
    self.ui_factory.label(
        covers_frame,
        text=f"Error al cargar Covers: {e}",
        font=("Segoe UI", 12),
        fg="#ff4444"
    ).pack(pady=20)

self.tab_frames["Covers"] = covers_frame
```

---

### **5. Agregar funcionalidades del header que se perdieron**:

```python
# En _setup_tabs_content() de OperatorBlackboard

# Después de los tabs, agregar botones del header:

# Botón Start/End Shift
self._create_shift_button(parent)

# Botones de Covers
self._create_cover_buttons(parent)

# Labels informativos
self._create_info_labels(parent)

# Métodos auxiliares:
def _create_shift_button(self, parent):
    """Crea botón Start/End Shift dinámico"""
    from backend_super import Dinamic_button_Shift, on_start_shift, on_end_shift
    
    def handle_shift():
        is_start = Dinamic_button_Shift(self.username)
        if is_start:
            on_start_shift(self.username, self.session_id, self.station)
        else:
            on_end_shift(self.username, self.session_id)
        update_button()
    
    def update_button():
        is_start = Dinamic_button_Shift(self.username)
        if is_start:
            self.shift_btn.configure(
                text="🚀 Start Shift",
                fg_color="#00c853"
            )
        else:
            self.shift_btn.configure(
                text="🛑 End Shift",
                fg_color="#d32f2f"
            )
    
    self.shift_btn = self.ui_factory.button(
        parent,
        text="🚀 Start Shift",
        command=handle_shift,
        width=160,
        height=40
    )
    self.shift_btn.pack(side="right", padx=20, pady=15)
    
    update_button()

def _create_cover_buttons(self, parent):
    """Crea botones de Cover: Registrar, Solicitar, Ver"""
    from backend_super import cover_mode
    from models.cover_model import request_covers
    
    # Botón Ver Covers
    self.ui_factory.button(
        parent,
        text="📋 Ver Covers",
        command=lambda: self._switch_tab("Covers"),
        width=130,
        height=40
    ).pack(side="right", padx=5, pady=15)
    
    # Botón Registrar Cover
    self.ui_factory.button(
        parent,
        text="👥 Registrar Cover",
        command=lambda: cover_mode(self.username, self.session_id, self.station, self.window),
        width=150,
        height=40
    ).pack(side="right", padx=5, pady=15)
    
    # Botón Solicitar Cover
    self.ui_factory.button(
        parent,
        text="❓ Solicitar Cover",
        command=lambda: request_covers(
            self.username,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "Necesito un cover",
            1
        ),
        width=150,
        height=40
    ).pack(side="right", padx=5, pady=15)

def _create_info_labels(self, parent):
    """Crea labels informativos de covers"""
    # Implementar get_next_cover_info() y get_covering_assignment()
    # Similar a operator_window.py líneas 225-420
    pass
```

---

## 📊 Resumen de Propuestas

### **Prioridad ALTA** (Críticas para completar migración):

1. ✅ **Crear CoversModule** siguiendo patrón MVC
   - Mostrar covers con 9 columnas (incluye Duración y Turno)
   - Modo solo lectura (no editable)
   - Botón "Cancelar Cover" con confirmación

2. ✅ **Crear CoversOperatorController**
   - `load_covers_data()`: Query + cálculos
   - `_calculate_duration()`: Formateo legible
   - `_calculate_turnos()`: Posición en cola
   - `cancel_cover()`: UPDATE is_Active = 0

3. ✅ **Extender cover_model.py**
   - `get_covers_realizados_by_user()`: LEFT JOIN covers_programados
   - `cancel_cover_programado()`: Cancelar solicitud

4. ⚠️ **Recuperar funcionalidades del header**:
   - Botón Start/End Shift
   - Botones de Cover (Registrar, Solicitar, Ver)
   - Labels informativos (próximo cover, asignaciones)

### **Prioridad MEDIA** (Mejora de código):

5. ✅ **Extraer DateTimePickerDialog** a clase separada
   - Reducir Blackboard de 1050 a ~800 líneas
   - Reutilizable en múltiples ventanas

6. ✅ **Extraer SupervisorSelectorDialog** a clase separada
   - Reutilizable entre módulos

7. ✅ **Mover validaciones a DailyController**
   - `create_event_from_form(form_data)`: Parseo + validación completa
   - Blackboard solo maneja UI

### **Prioridad BAJA** (Opcional, mejoras futuras):

8. 📰 **Panel de Noticias (SLC News)**
   - Extraer a módulo separado `NewsPanel`
   - Reutilizable en otros blackboards

9. 🔄 **Auto-refresh mejorado**
   - Implementar sistema de eventos/observers
   - Notificaciones de cambios en BD

10. 📊 **Métricas y analytics**
    - Dashboard con estadísticas de covers
    - Gráficos de duración promedio por operador

---

## ✅ Checklist de Migración Completa

### **Código limpio**:
- [x] Daily migrado a MVC (DailyModule + DailyController + daily_model)
- [x] Specials migrado a MVC (SpecialsModule + SpecialsOperatorController + specials_model)
- [ ] Covers migrado a MVC (CoversModule + CoversOperatorController + cover_model ✅ ya existe)
- [ ] DateTimePickerDialog extraído a clase separada
- [ ] SupervisorSelectorDialog extraído a clase separada
- [ ] Validaciones movidas de Blackboard a Controllers

### **Funcionalidades recuperadas**:
- [ ] Botón Start/End Shift en header
- [ ] Botones de Cover (Registrar, Solicitar, Ver)
- [ ] Labels informativos de covers
- [ ] Panel de Noticias (SLC News)
- [ ] Auto-refresh de labels cada 30s

### **Nuevas funcionalidades (Covers)**:
- [ ] Columna "Duración" con formato legible
- [ ] Columna "Turno" con posición en cola (3/7)
- [ ] Botón "Cancelar Cover" funcional
- [ ] Modo solo lectura (no editable)
- [ ] Color coding por estado

---

## 🎓 Conclusión

**Estado actual**: ✅ **Daily y Specials tienen arquitectura MVC excelente**. Blackboard está **86% limpio** pero puede mejorarse a **95%+**.

**Próximos pasos**:
1. Implementar CoversModule (3-4 horas)
2. Extraer diálogos a clases separadas (2 horas)
3. Recuperar funcionalidades del header (2 horas)
4. Testing y refinamiento (2 horas)

**Total estimado**: ~10 horas para completar migración MVC al 100% con todas las funcionalidades.

**Beneficios finales**:
- ✅ **Código 80% más limpio** vs operator_window.py
- ✅ **Reutilización** de componentes (pickers, diálogos, módulos)
- ✅ **Escalabilidad** para agregar nuevos módulos
- ✅ **Mantenibilidad** con separación clara de responsabilidades
- ✅ **Testeable** - Controllers sin dependencias de UI
