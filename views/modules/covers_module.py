"""
CoversModule - Módulo para visualizar y gestionar covers del operador.
Muestra covers realizados con duración, posición en turno y opción de cancelar.

Responsabilidades:
- Mostrar covers en tksheet (solo lectura)
- Calcular y mostrar duración de covers
- Mostrar posición en turno/cola
- Permitir cancelar covers programados activos
- Refrescar datos automáticamente
"""
import tkinter as tk
from tkinter import messagebox
from tksheet import Sheet
import traceback
from datetime import datetime

from controllers.covers_operator_controller import CoversOperatorController
from utils.ui_factory import UIFactory
from utils.date_formatter import format_friendly_datetime


class CoversModule:
    """
    Módulo Covers - Gestiona visualización de covers realizados y programados.
    Modo solo lectura con opción de cancelar covers activos.
    """
    
    # Configuración de columnas
    COLUMNS = [
        "Nombre Usuario",
        "Time Request",
        "Cover In",
        "Cover Out",
        "Duración",
        "Turno",
        "Motivo",
        "Covered By",
        "Activo"
    ]
    
    COLUMN_WIDTHS = {
        "Nombre Usuario": 150,
        "Time Request": 150,
        "Cover In": 140,
        "Cover Out": 140,
        "Duración": 100,
        "Turno": 80,
        "Motivo": 180,
        "Covered By": 150,
        "Activo": 80
    }
    
    def __init__(self, container, username, ui_factory, UI=None):
        """
        Inicializa el módulo Covers
        
        Args:
            container: Frame contenedor del módulo
            username: Nombre del usuario
            ui_factory: Factory para crear widgets
            UI: Módulo CustomTkinter (opcional)
        """
        self.container = container
        self.username = username
        self.ui_factory = ui_factory
        self.UI = UI
        
        # Referencia al blackboard (se establecerá desde OperatorBlackboard)
        self.blackboard = None
        
        # Componentes UI
        self.toolbar = None
        self.position_frame = None
        self.position_label = None
        self.sheet_frame = None
        self.sheet = None
        self.info_label = None
        
        # Estado
        self.row_data = []
        self.row_ids = []  # IDs de covers_realizados
        self.programados_ids = []  # IDs de covers_programados (para cancelar)
        self.refresh_job = None  # ID del job de auto-refresh
        
        # Controller
        self.controller = CoversOperatorController(username)
        
        # Renderizar
        self.render()
    
    def render(self):
        """Renderiza el módulo completo"""
        self._create_toolbar()
        self._create_position_label()
        self._create_sheet()
        self.load_data()
        self._start_auto_refresh()
    
    def _create_toolbar(self):
        """Crea toolbar con botones de acción"""
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
        ).pack(side="left", padx=5)
        
        # Botón Cancelar Cover (solo covers con Activo=1)
        self.ui_factory.button(
            self.toolbar,
            text="❌ Cancelar Cover",
            command=self._cancel_selected_cover,
            width=150,
            fg_color="#d32f2f",
            hover_color="#b71c1c"
        ).pack(side="left", padx=5)
        
        # Label de información
        self.info_label = self.ui_factory.label(
            self.toolbar,
            text="Cargando...",
            text_color="#00bfae",
            font=("Segoe UI", 12)
        )
        self.info_label.pack(side="right", padx=10)
    
    def _create_position_label(self):
        """Crea label prominente con posición en turno (auto-refresh cada 10s)"""
        self.position_frame = self.ui_factory.frame(
            self.container,
            fg_color="#1e3a5f",
            border_width=2,
            border_color="#4a90e2"
        )
        self.position_frame.pack(fill="x", padx=10, pady=(5, 10))
        
        self.position_label = self.ui_factory.label(
            self.position_frame,
            text="🎯 Calculando tu posición...",
            text_color="#ffffff",
            font=("Segoe UI", 16, "bold")
        )
        self.position_label.pack(pady=10)
    
    def _create_sheet(self):
        """Crea tksheet para mostrar covers (modo solo lectura)"""
        self.sheet_frame = self.ui_factory.frame(self.container, fg_color="#2c2f33")
        self.sheet_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        
        self.sheet = Sheet(
            self.sheet_frame,
            headers=self.COLUMNS,
            theme="dark blue",
            show_row_index=True,
            show_top_left=False,
            empty_horizontal=0,
            empty_vertical=0
        )
        
        # ⭐ MODO SOLO LECTURA - No se puede editar
        self.sheet.enable_bindings([
            "single_select",
            "drag_select",
            "column_select",
            "row_select",
            "column_width_resize",
            "double_click_column_resize",
            "arrowkeys",
            "right_click_popup_menu",
            "rc_select",
            "undo"  # Solo UNDO (Ctrl+Z)
        ])
        # ❌ NO habilitar "edit_cell" - es solo lectura
        
        self.sheet.pack(fill="both", expand=True)
        self.sheet.change_theme("dark blue")
        
        # Aplicar anchos personalizados
        for idx, col_name in enumerate(self.COLUMNS):
            width = self.COLUMN_WIDTHS.get(col_name, 100)
            self.sheet.column_width(column=idx, width=width)
    
    def load_data(self):
        """Carga covers desde el controller"""
        try:
            print(f"[DEBUG] CoversModule: Cargando covers para {self.username}")
            
            # Obtener datos del controller
            data = self.controller.load_covers_data()
            
            # Limpiar sheet
            self.sheet.set_sheet_data([[]])
            self.row_data = []
            self.row_ids = []
            self.programados_ids = []
            
            if not data:
                self.info_label.configure(text="📋 No hay covers para mostrar")
                print("[DEBUG] CoversModule: No hay covers")
                return
            
            # Preparar datos para sheet
            sheet_data = []
            for item in data:
                sheet_data.append([
                    item['nombre_usuario'],
                    item['time_request'],
                    item['cover_in'],
                    item['cover_out'],
                    item['duracion'],
                    item['turno'],
                    item['motivo'],
                    item['covered_by'],
                    item['activo']
                ])
                
                self.row_data.append(item)
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
            
            # Actualizar posición en turno
            self._update_position_label()
            
            print(f"[DEBUG] CoversModule: Cargados {len(data)} covers")
            
        except Exception as e:
            print(f"[ERROR] CoversModule.load_data: {e}")
            traceback.print_exc()
            self.info_label.configure(text="❌ Error al cargar covers")
    
    def _apply_row_colors(self, data):
        """Aplica colores según estado del cover"""
        for idx, item in enumerate(data):
            try:
                if item['activo'] == 'Sí':
                    # Cover activo/programado - verde
                    self.sheet.highlight_rows(
                        rows=[idx],
                        bg="#1b4d3e",
                        fg="#00c853",
                        highlight_index=False
                    )
                elif item['cover_out'] and item['cover_out'] != "En progreso":
                    # Cover completado - gris
                    self.sheet.highlight_rows(
                        rows=[idx],
                        bg="#2b2b2b",
                        fg="#999999",
                        highlight_index=False
                    )
            except Exception as e:
                print(f"[ERROR] Error aplicando color a fila {idx}: {e}")
    
    def _cancel_selected_cover(self):
        """Cancela el cover programado activo del usuario (sin necesidad de selección)"""
        try:
            # Obtener cover programado activo del usuario
            user_cover = self.controller.get_user_active_cover()
            
            if not user_cover:
                messagebox.showinfo(
                    "Sin cover activo",
                    "No tienes ningún cover programado activo para cancelar.\n\n"
                    "Solo puedes cancelar covers que hayas solicitado y aún no se hayan procesado.",
                    parent=self.container
                )
                return
            
            # Extraer información del cover
            programado_id, time_request, reason = user_cover
            
            # Formatear fecha para mostrar
            if isinstance(time_request, datetime):
                time_str = format_friendly_datetime(time_request, show_seconds=False)
            else:
                time_str = str(time_request)
            
            # Confirmar cancelación
            confirm = messagebox.askyesno(
                "Confirmar Cancelación",
                f"¿Cancelar tu cover programado?\n\n"
                f"📅 Solicitado: {time_str}\n"
                f"📝 Motivo: {reason or 'N/A'}\n\n"
                f"Esta acción no se puede deshacer.",
                parent=self.container
            )
            
            if not confirm:
                return
            
            # Cancelar a través del controller
            success, message = self.controller.cancel_cover(programado_id)
            
            if success:
                messagebox.showinfo(
                    "Éxito",
                    message,
                    parent=self.container
                )
                # Recargar datos y actualizar label de posición
                self.load_data()
            else:
                messagebox.showerror(
                    "Error",
                    f"No se pudo cancelar el cover:\n{message}",
                    parent=self.container
                )
        
        except Exception as e:
            messagebox.showerror(
                "Error",
                f"No se pudo cancelar el cover:\n{e}",
                parent=self.container
            )
            print(f"[ERROR] _cancel_selected_cover: {e}")
            traceback.print_exc()
    
    def get_selected_rows(self):
        """
        Obtiene las filas seleccionadas en el sheet.
        
        Returns:
            list: Lista de índices de filas seleccionadas
        """
        try:
            selected = self.sheet.get_selected_rows()
            return list(selected) if selected else []
        except Exception as e:
            print(f"[ERROR] get_selected_rows: {e}")
            return []
    
    def get_total_rows(self):
        """
        Obtiene el total de filas en el sheet.
        
        Returns:
            int: Número total de filas
        """
        try:
            return self.sheet.get_total_rows()
        except Exception:
            return len(self.row_data)
    
    def _update_position_label(self):
        """Actualiza el label de posición en turno"""
        try:
            position_info = self.controller.get_user_position_in_queue()
            message = position_info.get('message', '❓ Estado desconocido')
            
            # Cambiar color según estado
            if self.position_label:
                if position_info.get('position'):
                    # Usuario tiene cover activo - amarillo/naranja
                    self.position_label.configure(text=message, text_color="#ffeb3b")
                elif position_info.get('total') > 0:
                    # Hay covers activos pero usuario no está en cola - azul
                    self.position_label.configure(text=message, text_color="#4a90e2")
                else:
                    # No hay covers activos - verde
                    self.position_label.configure(text=message, text_color="#00c853")
        
        except Exception as e:
            print(f"[ERROR] _update_position_label: {e}")
            if self.position_label:
                self.position_label.configure(
                    text="❌ Error calculando posición",
                    text_color="#ff5252"
                )
    
    def _start_auto_refresh(self):
        """Inicia auto-refresh cada 10 segundos"""
        self._auto_refresh_cycle()
    
    def _auto_refresh_cycle(self):
        """Ciclo de auto-refresh recursivo"""
        try:
            # Actualizar solo el label de posición (más ligero que load_data completo)
            self._update_position_label()
            
            # Programar próxima actualización en 10 segundos
            if self.container.winfo_exists():
                self.refresh_job = self.container.after(10000, self._auto_refresh_cycle)
        
        except Exception as e:
            print(f"[ERROR] _auto_refresh_cycle: {e}")
            # Reintentar en 10 segundos de todos modos
            if self.container.winfo_exists():
                self.refresh_job = self.container.after(10000, self._auto_refresh_cycle)
    
    def stop_auto_refresh(self):
        """Detiene el auto-refresh (llamar al destruir el módulo)"""
        if self.refresh_job:
            try:
                self.container.after_cancel(self.refresh_job)
                self.refresh_job = None
            except Exception as e:
                print(f"[ERROR] stop_auto_refresh: {e}")
    
    def refresh(self):
        """Recarga los datos del módulo"""
        self.load_data()
