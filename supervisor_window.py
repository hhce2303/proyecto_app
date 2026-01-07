"""
Ventana de Supervisor - Interfaz principal para supervisores y lead supervisors
Implementa patrón MVC con contenedores modulares para:
- Supervisor: Specials, Audit, Cover Time, Breaks, Rol de Cover, News
- Lead Supervisor: + Admin, Unassigned Specials (además de los anteriores)
"""
import tkinter as tk
from tkinter import messagebox
import traceback

# Backend core
import backend_super
import login
from controllers.healthcheck_controller import HealthcheckController
import under_super
from backend_super import _focus_singleton

# Views (todas las vistas MVC)
from views.modules.healthcheck_module import HealthcheckModule
from views.specials_view import render_specials_container
from views.audit_view import render_audit_container
from views.breaks_view import render_breaks_container
from views.cover_time_view import render_cover_time_container
from views.rol_cover_view import render_rol_cover_container
from views.news_view import render_news_container_mvc
from views.admin_view import render_admin_container_mvc
from views.unassigned_specials_view import render_unassigned_specials_container
from views import status_views

# Utils
from utils.ui_factory import UIFactory


class SupervisorWindow:
    """
    Ventana principal de supervisor con sistema de tabs para múltiples módulos.
    Implementa patrón de clase para mejor organización y testability.
    """
    
    def __init__(self, username, role="Supervisor", session_id=None, station=None, root=None):
        """
        Inicializa la ventana de supervisor/lead supervisor
        
        Args:
            username: Nombre del supervisor
            role: Rol del usuario ("Supervisor" o "Lead Supervisor")
            session_id: ID de sesión activa
            station: Estación de trabajo
            root: Ventana raíz de tkinter (opcional)
        """
        self.username = username
        self.role = role
        self.session_id = session_id
        self.station = station
        self.root = root
        
        # Setup UI libraries
        self.UI = self._setup_ui_library()
        self.SheetClass = self._setup_sheet_library()
        if not self.SheetClass:
            return  # No se puede continuar sin tksheet
            
        self.ui_factory = UIFactory(self.UI)
        
        # Variables de estado
        self.current_mode = 'specials'
        self.containers = {}
        self.mode_buttons = {}
        
        # Crear ventana
        self.window = self._create_window()
        
        # Setup componentes
        self._setup_header()
        self._setup_mode_selector()
        self._init_all_containers()
        self._configure_close_handler()


    def _setup_ui_library(self):
        """Detecta y configura CustomTkinter o retorna None para tkinter"""
        try:
            import importlib
            ctk = importlib.import_module('customtkinter')
            try:
                ctk.set_appearance_mode("dark")
                ctk.set_default_color_theme("dark-blue")
            except:
                pass
            return ctk
        except:
            return None
    
    def _setup_sheet_library(self):
        """Carga tksheet library o muestra error"""
        try:
            from tksheet import Sheet
            return Sheet
        except:
            messagebox.showerror("Error", "tksheet no está instalado.\nInstala con: pip install tksheet")
            return None
    
    def _create_window(self):
        """Crea la ventana principal toplevel"""
        win = self.ui_factory.toplevel(bg="#1e1e1e")
        
        # Título dinámico según rol
        title_prefix = "👔" if self.role == "Lead Supervisor" else "📊"
        win.title(f"{title_prefix} {self.role} - {self.username}")
        
        win.geometry("1340x800")
        win.resizable(True, True)
        return win
    
    def _setup_header(self):
        """Configura el header con botones y status indicator"""
        header = self.ui_factory.frame(self.window, bg="#23272a", corner_radius=0)
        header.pack(fill="x", padx=0, pady=0)
        
        # Botón Refrescar
        self.refresh_btn = self.ui_factory.button(
            header, "🔄  Refrescar", 
            lambda: self._refresh_current_mode(),
            bg="#4D6068", hover="#27a3e0",
            width=120, height=40,
            font=("Segoe UI", 12, "bold")
        )
        self.refresh_btn.pack(side="left", padx=(20, 5), pady=15)
        
        # Botón Eliminar
        def eliminar_special():
            # Obtener el controller y sheet de specials
            specials_container = self.containers.get('specials')
            if not specials_container:
                messagebox.showerror("Error", "No se encontró el container de specials.")
                return
            controller = specials_container.get('controller')
            sheet = specials_container.get('sheet')
            if not controller or not sheet:
                messagebox.showerror("Error", "No se encontró la vista de specials.")
                return
            selected = sheet.get_selected_rows() if hasattr(sheet, 'get_selected_rows') else []
            if not selected:
                messagebox.showwarning("Eliminar Special", "Selecciona un registro para eliminar.")
                return
            # Solo se permite eliminar uno a la vez
            idx = selected[0]
            # Obtener datos del registro
            try:
                row_ids = getattr(sheet, 'row_ids', None)
                if row_ids and idx < len(row_ids):
                    special_id = row_ids[idx]
                else:
                    # Fallback: intentar obtener el ID de la celda
                    special_id = sheet.get_cell_data(idx, 0)
                # Obtener el registro completo
                registro = controller.get_special_by_id(special_id) if hasattr(controller, 'get_special_by_id') else None
                if not registro:
                    messagebox.showerror("Error", "No se pudo obtener el registro seleccionado.")
                    return
                # Verificar si tiene ID_Evento
                id_evento = registro.get('ID_Eventos') if isinstance(registro, dict) else None
                if id_evento:
                    messagebox.showinfo("No permitido", "No se puede eliminar un special que tiene ID_Evento.")
                    return
                # Llamar a safe_delete
                backend_super.safe_delete(
                    table_name="specials",
                    pk_column="ID_special",
                    pk_value=special_id,
                    deleted_by=self.username
                )
                messagebox.showinfo("Eliminado", "Special eliminado correctamente.")
                # Refrescar vista
                self._refresh_current_mode()
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo eliminar el registro:\n{e}")
                traceback.print_exc()
        self.delete_btn = self.ui_factory.button(
            header, "🗑️ Eliminar",
            eliminar_special,
            bg="#d32f2f", hover="#b71c1c",
            width=120, height=40,
            font=("Segoe UI", 12, "bold")
        )
        self.delete_btn.pack(side="left", padx=5, pady=15)
        
        # Status indicator
        status_views.render_status_header(
            parent_frame=header,
            username=self.username,
            controller=None,
            UI=self.UI
        )
    
    def _get_modes_config(self):
        """
        Retorna la configuración de modos según el rol del usuario.
        Lead Supervisors tienen acceso a Admin y Unassigned Specials adicionales.
        
        Returns:
            Lista de tuplas (mode_id, label, width)
        """
        # Modos base para todos los supervisores
        base_modes = [
            ('specials', '📋 Specials', 130),
            ('audit', '📊 Audit', 130),
            ('cover_time', '⏱️ Cover Time', 140),
            ('breaks', '☕ Breaks', 130),
            ('rol_cover', '🎭 Rol de Cover', 150),
            ('news', '📰 News', 130),
            ('healthcheck', '✅ Healthcheck', 150)
        ]
        
        # Modos adicionales para Lead Supervisor
        if self.role == "Lead Supervisor":
            lead_modes = [
                ('unassigned_specials', '⚠️ Sin Marcar', 140),
                ('admin', '🔧 Admin', 130)
            ]
            # Insertar antes de 'news' para mejor orden visual
            return base_modes[:-1] + lead_modes + [base_modes[-1]]
        
        return base_modes
    
    def _setup_mode_selector(self):
        """Configura el selector de tabs/modos dinámicamente según rol"""
        mode_frame = self.ui_factory.frame(
            self.window, 
            bg="#23272a", 
            corner_radius=0, 
            height=50
        )
        mode_frame.pack(fill="x", padx=0, pady=0)
        mode_frame.pack_propagate(False)
        
        # Obtener configuración de modos según rol
        modes = self._get_modes_config()
        
        # Crear botones de modo
        for mode_id, label, width in modes:
            # Primer botón activo, resto inactivos
            if mode_id == 'specials':
                bg_color = "#4a90e2"
                hover_color = "#357ABD"
            else:
                bg_color = "#3b4754"
                hover_color = "#4a5560"
            
            btn = self.ui_factory.button(
                mode_frame,
                label,
                lambda m=mode_id: self.switch_mode(m),
                bg=bg_color,
                hover=hover_color,
                width=width,
                height=35,
                font=("Segoe UI", 12, "bold")
            )
            btn.pack(side="left", padx=(20 if mode_id == 'specials' else 5), pady=8)
            self.mode_buttons[mode_id] = btn
    
    def _init_all_containers(self):
        """Inicializa todos los containers con vistas MVC según el rol"""
        # Containers base (todos los roles)
        self._init_base_containers()
        
        # Containers adicionales para Lead Supervisor
        if self.role == "Lead Supervisor":
            self._init_lead_supervisor_containers()
    
    def _init_base_containers(self):
        """Inicializa containers base disponibles para todos los supervisores"""
        # Specials
        specials_widgets = render_specials_container(
            parent=self.window,
            username=self.username,
            UI=self.UI,
            SheetClass=self.SheetClass
        )
        self.containers['specials'] = specials_widgets
        # Agregar botón "Otros Specials" al marks_frame
        self._add_otros_specials_button(specials_widgets['marks_frame'])

        # Audit
        audit_widgets = render_audit_container(
            parent=self.window,
            UI=self.UI,
            SheetClass=self.SheetClass
        )
        self.containers['audit'] = audit_widgets

        # Breaks
        breaks_widgets = render_breaks_container(
            parent=self.window,
            username=self.username,
            UI=self.UI,
            SheetClass=self.SheetClass,
            under_super=under_super
        )
        self.containers['breaks'] = breaks_widgets

        # Cover Time
        cover_widgets = render_cover_time_container(
            parent=self.window,
            UI=self.UI,
            SheetClass=self.SheetClass
        )
        self.containers['cover_time'] = cover_widgets

        # Rol de Cover
        rol_widgets = render_rol_cover_container(
            parent=self.window,
            UI=self.UI
        )
        self.containers['rol_cover'] = rol_widgets

        # News
        news_widgets = render_news_container_mvc(
            parent=self.window,
            username=self.username,
            UI=self.UI,
            SheetClass=self.SheetClass
        )
        self.containers['news'] = news_widgets

        # Healthcheck: solo placeholder, no instancia el módulo aún
        self.containers['healthcheck'] = None
    
    def _init_lead_supervisor_containers(self):
        """Inicializa containers adicionales exclusivos para Lead Supervisors"""
        # Unassigned Specials
        unassigned_widgets = render_unassigned_specials_container(
            parent=self.window,
            username=self.username,
            UI=self.UI,
            SheetClass=self.SheetClass
        )
        self.containers['unassigned_specials'] = unassigned_widgets
        
        # Admin
        admin_widgets = render_admin_container_mvc(
            parent=self.window,
            username=self.username,
            UI=self.UI if self.UI else "tkinter",
            SheetClass=self.SheetClass
        )
        self.containers['admin'] = admin_widgets
    
    def _add_otros_specials_button(self, marks_frame):
        """Agrega botón 'Otros Specials' al frame de marcas"""
        btn = self.ui_factory.button(
            marks_frame,
            "📋 Otros Specials",
            self.open_otros_specials,
            bg="#4a5f7a",
            hover="#3a4f6a",
            width=150,
            height=35,
            font=("Segoe UI", 11, "bold")
        )
        btn.pack(side="left", padx=5, pady=10)
    
    def switch_mode(self, new_mode):
        """Cambia entre modos ocultando/mostrando containers"""
        self.current_mode = new_mode

        # Ocultar todos los containers
        for container_data in self.containers.values():
            if container_data and 'container' in container_data:
                container_data['container'].pack_forget()

        # Resetear colores de botones (inactivos)
        inactive_color = "#3b4754"
        inactive_hover = "#4a5560"
        for btn in self.mode_buttons.values():
            self.ui_factory.set_widget_color(btn, bg=inactive_color, hover=inactive_hover)

        # Mostrar container activo y resaltar botón
        if new_mode in self.containers:
            # Si el módulo healthcheck no está instanciado, créalo aquí
            if new_mode == 'healthcheck' and self.containers['healthcheck'] is None:
                from views.modules.healthcheck_module import HealthcheckModule
                healthcheck_widgets = HealthcheckModule(
                    parent=self.window,
                    username=self.username,
                    UI=self.UI
                ).__dict__
                self.containers['healthcheck'] = healthcheck_widgets

            container_data = self.containers[new_mode]
            if container_data and 'container' in container_data:
                container_data['container'].pack(fill="both", expand=True, padx=10, pady=10)

                # Botón activo
                active_color = "#4a90e2"
                active_hover = "#357ABD"
                self.ui_factory.set_widget_color(
                    self.mode_buttons[new_mode], 
                    bg=active_color, 
                    hover=active_hover
                )

                # Ejecutar refresh si existe
                if 'refresh' in container_data:
                    container_data['refresh']()
    
    def _refresh_current_mode(self):
        """Refresca el modo/container actual"""
        if self.current_mode in self.containers:
            if 'refresh' in self.containers[self.current_mode]:
                self.containers[self.current_mode]['refresh']()
    
    def open_otros_specials(self):
        """Abre ventana para ver y tomar specials de otros supervisores"""
        specials_controller = self.containers['specials']['controller']
        
        # Ventana de selección de supervisor
        sel_win = self.ui_factory.toplevel(self.window, bg="#2c2f33")
        sel_win.title("Otros Specials - Selecciona Supervisor")
        sel_win.geometry("380x340")
        sel_win.resizable(False, False)
        
        # Label
        label = self.ui_factory.label(
            sel_win,
            "Supervisor (origen):",
            fg="#00bfae",
            font=("Segoe UI", 13, "bold")
        )
        label.pack(pady=(14, 6))
        
        # Frame para listbox
        list_frame = self.ui_factory.frame(sel_win, bg="#2c2f33")
        list_frame.pack(fill="both", expand=True, padx=14, pady=(4, 12))
        
        # Scrollbar y Listbox
        yscroll = tk.Scrollbar(list_frame, orient="vertical")
        yscroll.pack(side="right", fill="y")
        
        sup_listbox = tk.Listbox(
            list_frame, height=10, selectmode="browse",
            bg="#262a31", fg="#00bfae", font=("Segoe UI", 12),
            yscrollcommand=yscroll.set, activestyle="dotbox",
            selectbackground="#14414e"
        )
        sup_listbox.pack(side="left", fill="both", expand=True)
        yscroll.config(command=sup_listbox.yview)
        
        # Cargar supervisores
        supervisores = specials_controller.get_all_supervisors()
        if not supervisores:
            sup_listbox.insert("end", "No hay supervisores disponibles")
        else:
            for sup in supervisores:
                sup_listbox.insert("end", sup)
        
        # Handler para abrir lista de specials
        def abrir_lista_specials():
            idx = sup_listbox.curselection()
            if not idx:
                messagebox.showwarning("Otros Specials", "Selecciona un supervisor.", parent=sel_win)
                return
            
            old_sup = sup_listbox.get(idx[0])
            if old_sup == "No hay supervisores disponibles":
                return
            
            try:
                sel_win.destroy()
            except:
                pass
            
            self._show_otros_specials_list(old_sup, specials_controller)
        
        # Botón Abrir
        btn = self.ui_factory.button(
            sel_win,
            "Abrir",
            abrir_lista_specials,
            bg="#00c853",
            hover="#00a043",
            width=140,
            height=35,
            font=("Segoe UI", 12, "bold")
        )
        btn.pack(pady=12)
    
    def _show_otros_specials_list(self, supervisor, controller):
        """Muestra ventana con specials de otro supervisor"""
        lst_win = self.ui_factory.toplevel(self.window, bg="#2c2f33")
        lst_win.title(f"Otros Specials - {supervisor}")
        lst_win.geometry("1350x600")
        lst_win.resizable(True, True)
        
        # Variables locales
        row_ids_otros = []
        
        # Frame para tabla
        frame2 = self.ui_factory.frame(lst_win, bg="#2c2f33")
        frame2.pack(expand=True, fill="both", padx=12, pady=10)
        
        # Crear tksheet
        cols2 = ["ID", "Fecha_hora", "ID_Sitio", "Nombre_Actividad", "Cantidad", 
                "Camera", "Descripcion", "Usuario", "Time_Zone", "Marca"]
        
        custom_widths_otros = {
            "ID": 60, "Fecha_hora": 150, "ID_Sitio": 220, "Nombre_Actividad": 150,
            "Cantidad": 70, "Camera": 80, "Descripcion": 190, "Usuario": 100,
            "Time_Zone": 90, "Marca": 180
        }
        
        sheet2 = self.SheetClass(
            frame2, headers=cols2, theme="dark blue", height=400, width=1160,
            show_selected_cells_border=True, show_row_index=True, show_top_left=False
        )
        sheet2.enable_bindings([
            "single_select", "drag_select", "column_select", "row_select",
            "column_width_resize", "double_click_column_resize", "row_height_resize",
            "arrowkeys", "right_click_popup_menu", "rc_select", "copy"
        ])
        sheet2.pack(fill="both", expand=True)
        sheet2.change_theme("dark blue")
        
        def apply_widths():
            for idx, col in enumerate(cols2):
                if col in custom_widths_otros:
                    try:
                        sheet2.column_width(idx, custom_widths_otros[col])
                    except:
                        pass
            sheet2.redraw()
        
        def cargar_lista():
            nonlocal row_ids_otros
            try:
                snapshot = controller.load_otros_specials_snapshot(supervisor)
                
                if snapshot is None:
                    sheet2.set_sheet_data([[f"{supervisor} no tiene shift activo"] + [""] * (len(cols2)-1)])
                    apply_widths()
                    row_ids_otros.clear()
                    return
                
                row_ids_otros[:] = snapshot['row_ids']
                
                if snapshot['row_count'] == 0:
                    sheet2.set_sheet_data([["No hay specials"] + [""] * (len(cols2)-1)])
                else:
                    sheet2.set_sheet_data(snapshot['rows'])
                    sheet2.dehighlight_all()
                    for idx, meta in enumerate(snapshot['row_metadata']):
                        if meta['marked_status'] == 'done':
                            sheet2.highlight_rows([idx], bg="#00c853", fg="#111111")
                        elif meta['marked_status'] == 'flagged':
                            sheet2.highlight_rows([idx], bg="#f5a623", fg="#111111")
                
                apply_widths()
                
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo cargar specials:\n{e}", parent=lst_win)
                traceback.print_exc()
        
        def tomar_specials():
            try:
                selected = sheet2.get_selected_rows()
                if not selected:
                    messagebox.showwarning("Tomar Specials", "Selecciona registros.", parent=lst_win)
                    return
                
                ids = [row_ids_otros[i] for i in selected if i < len(row_ids_otros)]
                if not ids:
                    return
                
                success = controller.transfer_specials(ids, self.username)
                
                if success:
                    messagebox.showinfo("Tomar Specials", f"✅ {len(ids)} special(s) transferido(s)", parent=lst_win)
                    cargar_lista()
                    self.containers['specials']['refresh']()
                else:
                    messagebox.showerror("Error", "No se pudo transferir specials", parent=lst_win)
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo tomar specials:\n{e}", parent=lst_win)
                traceback.print_exc()
        
        # Botones
        btn_frame = self.ui_factory.frame(lst_win, bg="#23272a")
        btn_frame.pack(fill="x", padx=10, pady=10)
        
        btn_refresh = self.ui_factory.button(
            btn_frame, "🔄 Refrescar",
            cargar_lista,
            bg="#4D6068", hover="#27a3e0",
            width=120, height=35,
            font=("Segoe UI", 11, "bold")
        )
        btn_refresh.pack(side="left", padx=5)
        
        btn_take = self.ui_factory.button(
            btn_frame, "📥 Tomar Seleccionados",
            tomar_specials,
            bg="#00c853", hover="#00a043",
            width=180, height=35,
            font=("Segoe UI", 11, "bold")
        )
        btn_take.pack(side="left", padx=5)
        
        cargar_lista()
    
    def _configure_close_handler(self):
        """Configura el handler para cerrar la ventana"""
        def on_window_close():
            try:
                if self.session_id and self.station:
                    login.do_logout(self.session_id, self.station, self.window)
                if not self.session_id:
                    try:
                        login.show_login()
                        self.window.destroy()
                    except Exception as e:
                        print(f"[ERROR] Error during logout: {e}")
            except Exception as e:
                print(f"[ERROR] Error destroying window: {e}")
        
        self.window.protocol("WM_DELETE_WINDOW", on_window_close)
    
    def show(self):
        """Muestra la ventana y activa el modo inicial"""
        self.switch_mode('specials')
        return self.window


def open_hybrid_events_supervisor(username, role="Supervisor", session_id=None, station=None, root=None):
    """
    Función de entrada para abrir ventana de supervisor/lead supervisor.
    Mantiene compatibilidad con código legacy.
    
    Args:
        username: Nombre del supervisor
        role: Rol del usuario ("Supervisor" o "Lead Supervisor")
        session_id: ID de sesión
        station: Estación de trabajo
        root: Ventana raíz (opcional)
    
    Returns:
        Ventana toplevel creada
    """
    # Singleton check - diferente key por rol para permitir ambas ventanas
    singleton_key = f'hybrid_events_{"lead_" if role == "Lead Supervisor" else ""}supervisor'
    ex = _focus_singleton(singleton_key)
    if ex:
        return ex
    
    # Crear y mostrar ventana
    window_instance = SupervisorWindow(username, role, session_id, station, root)
    return window_instance.show()
