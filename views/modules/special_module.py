"""
SpecialsModule - Módulo para gestionar eventos especiales del supervisor.
Muestra eventos de grupos especiales (AS, KG, HUD, PE, SCH, WAG, LT, DT).

Responsabilidades:
- Mostrar eventos especiales en tksheet (SOLO LECTURA)
- Aplicar colores según estado (verde=enviado, ámbar=pendiente)
- Permitir marcar eventos
- Enviar a supervisores
- Refrescar datos

IMPORTANTE: Este módulo es para SUPERVISORES, no Operadores.
"""
import tkinter as tk
from tkinter import messagebox, simpledialog
from tksheet import Sheet
import traceback
from datetime import datetime, timedelta
import re

from models.database import get_connection
from utils.ui_factory import UIFactory
from utils.date_formatter import format_friendly_datetime


class SpecialsModule:
    """
    Módulo Specials - Gestiona eventos especiales para supervisores.
    """
    
    # Configuración de columnas
    COLUMNS = ["Fecha Hora", "Sitio", "Actividad", "Cantidad", "Camera", "Descripción", "TZ", "Marca"]
    COLUMN_WIDTHS = {
        "Fecha Hora": 150,
        "Sitio": 270,
        "Actividad": 170,
        "Cantidad": 80,
        "Camera": 90,
        "Descripción": 320,
        "TZ": 50,
        "Marca": 100
    }
    
    # Grupos especiales a filtrar
    GRUPOS_ESPECIALES = ("AS", "KG", "HUD", "PE", "SCH", "WAG", "LT", "DT")
    
    def __init__(self, parent, username, session_id, role, UI=None):
        """
        Inicializa el módulo Specials
        
        Args:
            parent: Frame contenedor del módulo
            username: Nombre del supervisor
            session_id: ID de sesión activa
            role: Rol del usuario (debe ser Supervisor)
            UI: Módulo CustomTkinter (opcional)
        """
        self.parent = parent
        self.username = username
        self.session_id = session_id
        self.role = role
        self.UI = UI
        self.ui_factory = UIFactory(UI)
        
        # Componentes UI
        self.container = None
        self.toolbar = None
        self.sheet_frame = None
        self.sheet = None
        self.status_label = None
        
        # Estado
        self.row_data_cache = []
        self.row_ids = []
        
        # Renderizar
        self.render()
    
    def render(self):
        """Renderiza el módulo completo"""
        self._create_container()
        self._create_toolbar()
        self._create_sheet()
        self._setup_bindings()
        self.load_data()
    
    def _create_container(self):
        """Crea el contenedor principal del módulo"""
        self.container = self.ui_factory.frame(self.parent, fg_color="#1e1e1e")
        self.container.pack(fill="both", expand=True)
    
    def _create_toolbar(self):
        """Crea barra de herramientas con botones"""
        self.toolbar = self.ui_factory.frame(self.container, fg_color="#2c2f33")
        self.toolbar.pack(fill="x", padx=10, pady=(10, 5))
        
        # Botón Refrescar
        self.ui_factory.button(
            self.toolbar,
            text="🔄 Refrescar",
            command=self.load_data,
            width=120,
            fg_color="#4D6068",
            hover_color="#27a3e0"
        ).pack(side="left", padx=5, pady=5)
        
        # Botón Marcar
        self.ui_factory.button(
            self.toolbar,
            text="⭐ Marcar",
            command=self._mark_selected,
            width=120,
            fg_color="#f5a623",
            hover_color="#e89500"
        ).pack(side="left", padx=5, pady=5)
        
        # Botón Enviar
        self.ui_factory.button(
            self.toolbar,
            text="📤 Enviar",
            command=self._send_to_supervisors,
            width=120,
            fg_color="#00c853",
            hover_color="#00a043"
        ).pack(side="left", padx=5, pady=5)
        
        # Status label
        self.status_label = self.ui_factory.label(
            self.toolbar,
            text="Listo",
            font=("Segoe UI", 11),
            fg="#aaaaaa"
        )
        self.status_label.pack(side="right", padx=10)
    
    def _create_sheet(self):
        """Crea el tksheet para mostrar eventos especiales"""
        self.sheet_frame = self.ui_factory.frame(self.container, fg_color="#1e1e1e")
        self.sheet_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Crear tksheet con tema oscuro
        self.sheet = Sheet(
            self.sheet_frame,
            theme="dark blue",
            headers=self.COLUMNS,
            height=500,
            width=1000
        )
        self.sheet.pack(fill="both", expand=True)
        
        # Habilitar funcionalidades (SOLO LECTURA, no edición)
        self.sheet.enable_bindings(
            "single_select",
            "row_select",
            "column_width_resize",
            "double_click_column_resize",
            "arrowkeys",
            "right_click_popup_menu",
            "rc_select",
            "copy"
        )
        
        # Configurar anchos de columnas
        for idx, col_name in enumerate(self.COLUMNS):
            if col_name in self.COLUMN_WIDTHS:
                self.sheet.column_width(column=idx, width=self.COLUMN_WIDTHS[col_name])
    
    def _setup_bindings(self):
        """Configura event bindings del sheet"""
        # No hay edición directa en Specials (solo lectura)
        pass
    
    def load_data(self):
        """Carga eventos especiales desde el último START SHIFT"""
        try:
            self._update_status("Cargando eventos especiales...")
            
            # Obtener último START SHIFT
            last_shift_time = self._get_last_shift_start()
            if last_shift_time is None:
                self.sheet.set_sheet_data([["No hay shift activo"] + [""] * (len(self.COLUMNS)-1)])
                self.row_data_cache.clear()
                self.row_ids.clear()
                self._update_status("Sin shift activo")
                return
            
            # Cargar timezone config
            tz_adjust = self._load_tz_config()
            
            # Conectar a BD
            conn = get_connection()
            cur = conn.cursor()
            
            # Obtener ID_Usuario del supervisor
            cur.execute("SELECT ID_Usuario FROM user WHERE Nombre_Usuario = %s", (self.username,))
            user_row = cur.fetchone()
            if not user_row:
                messagebox.showerror("Error", f"Usuario '{self.username}' no encontrado.")
                cur.close()
                conn.close()
                return
            user_id = int(user_row[0])
            
            # Query: Eventos de grupos especiales
            query = """
                SELECT
                    e.ID_Eventos,
                    e.FechaHora,
                    e.ID_Sitio,
                    e.Nombre_Actividad,
                    e.Cantidad,
                    e.Camera,
                    e.Descripcion,
                    u.Nombre_Usuario
                FROM Eventos AS e
                INNER JOIN user u ON e.ID_Usuario = u.ID_Usuario
                WHERE u.Nombre_Usuario = %s
                AND e.ID_Sitio IN (
                    SELECT st.ID_Sitio
                    FROM Sitios st
                    WHERE st.ID_Grupo IN (%s, %s, %s, %s, %s, %s, %s, %s)
                )
                AND e.FechaHora >= %s
                ORDER BY e.FechaHora ASC
            """
            
            cur.execute(query, (self.username, *self.GRUPOS_ESPECIALES, last_shift_time))
            rows = cur.fetchall()
            
            # Procesar filas
            time_zone_cache = {}
            processed = []
            
            for r in rows:
                id_evento = r[0]
                fecha_hora = r[1]
                id_sitio = r[2]
                nombre_actividad = r[3]
                cantidad = r[4]
                camera = r[5]
                descripcion = r[6]
                usuario = r[7]
                
                # Resolver nombre de sitio y zona horaria
                nombre_sitio = ""
                tz = ""
                if id_sitio:
                    if id_sitio in time_zone_cache:
                        nombre_sitio, tz = time_zone_cache[id_sitio]
                    else:
                        try:
                            cur.execute("SELECT Nombre_Sitio, Time_Zone FROM Sitios WHERE ID_Sitio = %s", (id_sitio,))
                            sit = cur.fetchone()
                            nombre_sitio = sit[0] if sit and sit[0] else ""
                            tz = sit[1] if sit and len(sit) > 1 and sit[1] else ""
                        except Exception:
                            nombre_sitio = ""
                            tz = ""
                        time_zone_cache[id_sitio] = (nombre_sitio, tz)
                
                # Formato de sitio
                if id_sitio and nombre_sitio:
                    display_site = f"{nombre_sitio} ({id_sitio})"
                elif id_sitio:
                    display_site = str(id_sitio)
                else:
                    display_site = nombre_sitio or ""
                
                # Formatear fecha/hora con ajuste de timezone
                try:
                    tz_offset_hours = tz_adjust.get((tz or '').upper(), 0)
                    
                    if isinstance(fecha_hora, str):
                        fh = datetime.strptime(fecha_hora[:19], "%Y-%m-%d %H:%M:%S")
                    else:
                        fh = fecha_hora
                    
                    fh_adjusted = fh + timedelta(hours=tz_offset_hours)
                    fecha_str = format_friendly_datetime(fh_adjusted, show_seconds=False)
                except Exception:
                    fecha_str = format_friendly_datetime(fecha_hora, show_seconds=False) if fecha_hora else ""
                
                # Ajustar timestamps en descripción
                descripcion_display = self._adjust_description_timestamps(
                    descripcion, fh if 'fh' in locals() else None, tz_offset_hours if 'tz_offset_hours' in locals() else 0
                )
                
                # Verificar si existe en tabla specials (para marca)
                try:
                    cur.execute("""
                        SELECT id_special, marked_status, FechaHora_Supervisor, Descripcion_Supervisor
                        FROM specials
                        WHERE id_evento = %s
                    """, (id_evento,))
                    special_row = cur.fetchone()
                    
                    if special_row:
                        id_special = special_row[0]
                        marked_status = special_row[1]
                        fecha_supervisor = special_row[2]
                        desc_supervisor = special_row[3]
                        
                        # Si tiene valores de supervisor, usar esos (ya fue enviado)
                        if fecha_supervisor:
                            try:
                                fh_sup = datetime.strptime(str(fecha_supervisor)[:19], "%Y-%m-%d %H:%M:%S") if isinstance(fecha_supervisor, str) else fecha_supervisor
                                fh_sup_adjusted = fh_sup + timedelta(hours=tz_offset_hours)
                                fecha_str_display = format_friendly_datetime(fh_sup_adjusted, show_seconds=False)
                            except:
                                fecha_str_display = fecha_str
                        else:
                            fecha_str_display = fecha_str
                        
                        if desc_supervisor:
                            descripcion_display = desc_supervisor
                        
                        # Determinar marca y color
                        if marked_status in ('flagged', 'last'):
                            mark_display = "Enviado"
                            mark_color = 'green'
                        else:
                            mark_display = "Pendiente"
                            mark_color = 'amber'
                    else:
                        id_special = None
                        mark_display = ""
                        mark_color = None
                        fecha_str_display = fecha_str
                except Exception as e:
                    print(f"[DEBUG] Error verificando special: {e}")
                    id_special = None
                    mark_display = ""
                    mark_color = None
                    fecha_str_display = fecha_str
                
                # Fila para mostrar
                display_row = [
                    fecha_str_display,
                    display_site,
                    nombre_actividad or "",
                    str(cantidad) if cantidad is not None else "0",
                    camera or "",
                    descripcion_display,
                    tz or "",
                    mark_display
                ]
                
                processed.append({
                    'id': id_evento,
                    'id_special': id_special,
                    'values': display_row,
                    'mark_color': mark_color,
                    'id_sitio': id_sitio,
                    'nombre_actividad': nombre_actividad,
                    'cantidad': cantidad,
                    'camera': camera,
                    'descripcion': descripcion,
                    'usuario': usuario,
                    'time_zone': tz
                })
            
            cur.close()
            conn.close()
            
            # Actualizar cache
            self.row_data_cache = processed
            self.row_ids = [item['id'] for item in processed]
            
            # Poblar sheet
            if not processed:
                self.sheet.set_sheet_data([["No hay eventos de grupos especiales en este turno"] + [""] * (len(self.COLUMNS)-1)])
                self._update_status("Sin eventos especiales")
            else:
                data = [item['values'] for item in processed]
                self.sheet.set_sheet_data(data)
                
                # Aplicar colores según estado
                self.sheet.dehighlight_all()
                for idx, item in enumerate(processed):
                    mark_color = item.get('mark_color')
                    if mark_color == 'green':
                        self.sheet.highlight_rows([idx], bg="#00c853", fg="#111111")
                    elif mark_color == 'amber':
                        self.sheet.highlight_rows([idx], bg="#f5a623", fg="#111111")
                
                self._update_status(f"✅ {len(processed)} eventos cargados")
        
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo cargar eventos especiales:\n{e}")
            traceback.print_exc()
            self._update_status("❌ Error al cargar")
    
    def _mark_selected(self):
        """Marca los eventos seleccionados"""
        selected = self.sheet.get_selected_rows()
        if not selected:
            messagebox.showwarning("Selección", "Selecciona al menos un evento para marcar.")
            return
        
        # Pedir tipo de marca
        mark_type = simpledialog.askstring(
            "Marcar Evento",
            "Tipo de marca (flagged/last):",
            initialvalue="flagged"
        )
        
        if not mark_type or mark_type not in ('flagged', 'last'):
            return
        
        try:
            conn = get_connection()
            cur = conn.cursor()
            
            marked_count = 0
            for row_idx in selected:
                if row_idx >= len(self.row_data_cache):
                    continue
                
                item = self.row_data_cache[row_idx]
                id_evento = item['id']
                id_special = item.get('id_special')
                
                # Si no existe en specials, crearlo
                if not id_special:
                    cur.execute("""
                        INSERT INTO specials (
                            id_evento, Usuario, Time_Zone, Supervisor,
                            marked_status, marked_by, marked_at
                        ) VALUES (%s, %s, %s, %s, %s, %s, NOW())
                    """, (
                        id_evento,
                        item['usuario'],
                        item['time_zone'],
                        self.username,
                        mark_type,
                        self.username
                    ))
                else:
                    # Actualizar marca existente
                    cur.execute("""
                        UPDATE specials
                        SET marked_status = %s,
                            marked_by = %s,
                            marked_at = NOW()
                        WHERE id_special = %s
                    """, (mark_type, self.username, id_special))
                
                marked_count += 1
            
            conn.commit()
            cur.close()
            conn.close()
            
            messagebox.showinfo("Éxito", f"{marked_count} evento(s) marcado(s) como '{mark_type}'.")
            self.load_data()  # Recargar
        
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo marcar eventos:\n{e}")
            traceback.print_exc()
    
    def _send_to_supervisors(self):
        """Envía eventos seleccionados a supervisores"""
        selected = self.sheet.get_selected_rows()
        if not selected:
            messagebox.showwarning("Selección", "Selecciona al menos un evento para enviar.")
            return
        
        # Confirmación
        if not messagebox.askyesno("Confirmar", f"¿Enviar {len(selected)} evento(s) a supervisores?"):
            return
        
        try:
            conn = get_connection()
            cur = conn.cursor()
            
            sent_count = 0
            for row_idx in selected:
                if row_idx >= len(self.row_data_cache):
                    continue
                
                item = self.row_data_cache[row_idx]
                id_evento = item['id']
                id_special = item.get('id_special')
                
                # Obtener datos del evento original
                cur.execute("""
                    SELECT FechaHora, Descripcion
                    FROM Eventos
                    WHERE ID_Eventos = %s
                """, (id_evento,))
                evento_row = cur.fetchone()
                if not evento_row:
                    continue
                
                fecha_original = evento_row[0]
                desc_original = evento_row[1]
                
                # Si no existe en specials, crearlo
                if not id_special:
                    cur.execute("""
                        INSERT INTO specials (
                            id_evento, Usuario, Time_Zone, Supervisor,
                            FechaHora_Supervisor, Descripcion_Supervisor,
                            marked_status, marked_by, marked_at
                        ) VALUES (%s, %s, %s, %s, %s, %s, 'flagged', %s, NOW())
                    """, (
                        id_evento,
                        item['usuario'],
                        item['time_zone'],
                        self.username,
                        fecha_original,
                        desc_original,
                        self.username
                    ))
                else:
                    # Actualizar special existente
                    cur.execute("""
                        UPDATE specials
                        SET FechaHora_Supervisor = %s,
                            Descripcion_Supervisor = %s,
                            Supervisor = %s,
                            marked_status = 'flagged',
                            marked_by = %s,
                            marked_at = NOW()
                        WHERE id_special = %s
                    """, (fecha_original, desc_original, self.username, self.username, id_special))
                
                sent_count += 1
            
            conn.commit()
            cur.close()
            conn.close()
            
            messagebox.showinfo("Éxito", f"{sent_count} evento(s) enviado(s) a supervisores.")
            self.load_data()  # Recargar
        
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo enviar eventos:\n{e}")
            traceback.print_exc()
    
    def _get_last_shift_start(self):
        """Obtiene la fecha/hora del último START SHIFT"""
        try:
            conn = get_connection()
            cur = conn.cursor()
            
            cur.execute("""
                SELECT MAX(e.FechaHora)
                FROM Eventos e
                INNER JOIN user u ON e.ID_Usuario = u.ID_Usuario
                WHERE u.Nombre_Usuario = %s
                AND e.Nombre_Actividad = 'START SHIFT'
            """, (self.username,))
            
            result = cur.fetchone()
            cur.close()
            conn.close()
            
            return result[0] if result and result[0] else None
        
        except Exception as e:
            print(f"[ERROR] No se pudo obtener último START SHIFT: {e}")
            return None
    
    def _load_tz_config(self):
        """Carga configuración de timezone offsets"""
        # Valores por defecto (importar desde backend_super si existe)
        return {
            'CST': 0,
            'MST': 1,
            'PST': 2,
            'EST': -1
        }
    
    def _adjust_description_timestamps(self, descripcion, base_datetime, tz_offset_hours):
        """Ajusta timestamps dentro de la descripción según timezone"""
        if not descripcion:
            return descripcion
        
        try:
            desc_text = str(descripcion)
            
            # Normalizar formato
            desc_text = re.sub(r"\[?\s*Timestamp:\s*(\d{1,2}:\d{2}:\d{2})\s*\]?", r"[\1]", desc_text, flags=re.IGNORECASE)
            desc_text = re.sub(r"\[?\s*Timestamp:\s*(\d{1,2}:\d{2})\s*\]?", r"[\1]", desc_text, flags=re.IGNORECASE)
            
            def adjust_timestamp(match):
                raw_time = match.group(1) if match.lastindex >= 1 else match.group(0)
                has_brackets = match.group(0).startswith('[')
                
                try:
                    if base_datetime:
                        base_date = base_datetime.date() if isinstance(base_datetime, datetime) else datetime.now().date()
                    else:
                        base_date = datetime.now().date()
                    
                    time_parts = raw_time.split(":")
                    if len(time_parts) == 3:
                        hh, mm, ss = [int(x) for x in time_parts]
                    elif len(time_parts) == 2:
                        hh, mm = [int(x) for x in time_parts]
                        ss = 0
                    else:
                        return match.group(0)
                    
                    if not (0 <= hh <= 23 and 0 <= mm <= 59 and 0 <= ss <= 59):
                        return match.group(0)
                    
                    desc_dt = datetime.combine(base_date, datetime.min.time()) + timedelta(hours=hh, minutes=mm, seconds=ss)
                    desc_dt_adjusted = desc_dt + timedelta(hours=tz_offset_hours)
                    
                    if len(time_parts) == 3:
                        if len(time_parts[0]) == 1:
                            desc_time_str = f"{desc_dt_adjusted.hour}:{desc_dt_adjusted.minute:02d}:{desc_dt_adjusted.second:02d}"
                        else:
                            desc_time_str = desc_dt_adjusted.strftime("%H:%M:%S")
                    else:
                        if len(time_parts[0]) == 1:
                            desc_time_str = f"{desc_dt_adjusted.hour}:{desc_dt_adjusted.minute:02d}"
                        else:
                            desc_time_str = desc_dt_adjusted.strftime("%H:%M")
                    
                    return f"[{desc_time_str}]" if has_brackets else desc_time_str
                except Exception:
                    return match.group(0)
            
            # Aplicar ajustes
            desc_text = re.sub(r"\[(\d{1,2}:\d{2}:\d{2})\]", adjust_timestamp, desc_text)
            desc_text = re.sub(r"\[(\d{1,2}:\d{2})\]", adjust_timestamp, desc_text)
            desc_text = re.sub(r"(?<!\d)(\d{1,2}:\d{2}:\d{2})(?!\])", adjust_timestamp, desc_text)
            desc_text = re.sub(r"(?<!\d)(\d{1,2}:\d{2})(?!:\d|\])", adjust_timestamp, desc_text)
            
            return desc_text
        except Exception:
            return descripcion
    
    def _update_status(self, message):
        """Actualiza el mensaje de status"""
        if self.status_label:
            self.status_label.configure(text=message)