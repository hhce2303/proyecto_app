



"""
Ventana de Supervisor - Interfaz principal para supervisores
Implementa patrón MVC con contenedores modulares para:
- Specials, Audit, Cover Time, Breaks, Rol de Cover, News
"""
import tkinter as tk
from tkinter import messagebox
import traceback

# Backend core
import backend_super
import login
import under_super
from backend_super import _focus_singleton

# Views (todas las vistas MVC)
from views.specials_view import render_specials_container
from views.audit_view import render_audit_container
from views.breaks_view import render_breaks_container
from views.cover_time_view import render_cover_time_container
from views.rol_cover_view import render_rol_cover_container
from views.news_view import render_news_container
from views import status_views

# Utils
from utils.ui_factory import UIFactory


class SupervisorWindow:
    """
    Ventana principal de supervisor con sistema de tabs para múltiples módulos.
    Implementa patrón de clase para mejor organización y testability.
    """
    
    def __init__(self, username, session_id=None, station=None, root=None):
        """
        Inicializa la ventana de supervisor
        
        Args:
            username: Nombre del supervisor
            session_id: ID de sesión activa
            station: Estación de trabajo
            root: Ventana raíz de tkinter (opcional)
        """
        self.username = username
        self.session_id = session_id
        self.station = station
        self.root = root
        
        # Setup UI libraries
        self.UI = self._setup_ui_library()
        self.SheetClass = self._setup_sheet_library()
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
        win.title(f"📊 Specials - {self.username}")
        win.geometry("1320x800")
        win.resizable(True, True)
        return win
    
    def _setup_header(self):
        """Configura el header con botones y status indicator"""
        header = self.ui_factory.frame(self.window, bg="#23272a", corner_radius=0)
        header.pack(fill="x", padx=0, pady=0)
        
        # Botón Refrescar (temporal - load_data se asigna después)
        self.refresh_btn = self.ui_factory.button(
            header, "🔄  Refrescar", 
            lambda: self._refresh_current_mode(),
            bg="#4D6068", hover="#27a3e0",
            width=120, height=40,
            font=("Segoe UI", 12, "bold")
        )
        self.refresh_btn.pack(side="left", padx=(20, 5), pady=15)
        
        # Botón Eliminar (temporal - se conecta después)
        self.delete_btn = self.ui_factory.button(
            header, "🗑️ Eliminar",
            lambda: None,  # Se conecta dinámicamente por modo
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

    
    def _setup_mode_selector(self):
        """Configura el selector de tabs/modos"""
        mode_frame = self.ui_factory.frame(
            self.window, 
            bg="#23272a", 
            corner_radius=0, 
            height=50
        )
        mode_frame.pack(fill="x", padx=0, pady=0)
        mode_frame.pack_propagate(False)
        
        # Definir modos y sus labels
        modes = [
            ('specials', '📋 Specials', 130),
            ('audit', '📊 Audit', 130),
            ('cover_time', '⏱️ Cover Time', 140),
            ('breaks', '☕ Breaks', 130),
            ('rol_cover', '🎭 Rol de Cover', 150),
            ('news', '📰 News', 130)
        ]
        
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
    
    def switch_mode(self, new_mode):
        """Cambia entre modos ocultando/mostrando containers"""
        self.current_mode = new_mode
        
        # Ocultar todos los containers
        for container_data in self.containers.values():
            container_data['container'].pack_forget()
        
        # Resetear colores de botones (inactivos)
        inactive_color = "#3b4754"
        inactive_hover = "#4a5560"
        
        for btn in self.mode_buttons.values():
            self.ui_factory.set_widget_color(btn, bg=inactive_color, hover=inactive_hover)
        
        # Mostrar container activo y resaltar botón
        if new_mode in self.containers:
            self.containers[new_mode]['container'].pack(fill="both", expand=True, padx=10, pady=10)
            
            # Botón activo
            active_color = "#4a90e2"
            active_hover = "#357ABD"
            self.ui_factory.set_widget_color(
                self.mode_buttons[new_mode], 
                bg=active_color, 
                hover=active_hover
            )
            
            # Ejecutar refresh si existe
            if 'refresh' in self.containers[new_mode]:
                self.containers[new_mode]['refresh']()

    # Botones de modo
    if UI is not None:
        btn_specials = UI.CTkButton(
            mode_frame, 
            text="📋 Specials", 
            command=lambda: switch_mode('specials'),
            fg_color="#4a90e2",
            hover_color="#357ABD",
            width=130,
            height=35,
            font=("Segoe UI", 12, "bold")
        )
        btn_specials.pack(side="left", padx=(20, 5), pady=8)
        
        btn_audit = UI.CTkButton(
            mode_frame, 
            text="📊 Audit", 
            command=lambda: switch_mode('audit'),
            fg_color="#3b4754",
            hover_color="#4a5560",
            width=130,
            height=35,
            font=("Segoe UI", 12, "bold")
        )
        btn_audit.pack(side="left", padx=5, pady=8)
        
        btn_cover = UI.CTkButton(
            mode_frame, 
            text="⏱️ Cover Time", 
            command=lambda: switch_mode('cover_time'),
            fg_color="#3b4754",
            hover_color="#4a5560",
            width=140,
            height=35,
            font=("Segoe UI", 12, "bold")
        )
        btn_cover.pack(side="left", padx=5, pady=8)
        
        btn_breaks = UI.CTkButton(
            mode_frame, 
            text="☕ Breaks", 
            command=lambda: switch_mode('breaks'),
            fg_color="#3b4754",
            hover_color="#4a5560",
            width=130,
            height=35,
            font=("Segoe UI", 12, "bold")
        )
        btn_breaks.pack(side="left", padx=5, pady=8)
        
        btn_rol_cover = UI.CTkButton(
            mode_frame, 
            text="🎭 Rol de Cover", 
            command=lambda: switch_mode('rol_cover'),
            fg_color="#3b4754",
            hover_color="#4a5560",
            width=150,
            height=35,
            font=("Segoe UI", 12, "bold")
        )
        btn_rol_cover.pack(side="left", padx=5, pady=8)
        
        btn_news = UI.CTkButton(
            mode_frame, 
            text="📰 News", 
            command=lambda: switch_mode('news'),
            fg_color="#3b4754",
            hover_color="#4a5560",
            width=130,
            height=35,
            font=("Segoe UI", 12, "bold")
        )
        btn_news.pack(side="left", padx=5, pady=8)
    else:
        btn_specials = tk.Button(
            mode_frame,
            text="📋 Specials",
            command=lambda: switch_mode('specials'),
            bg="#4a90e2",
            fg="white",
            activebackground="#357ABD",
            font=("Segoe UI", 12, "bold"),
            relief="flat",
            width=11
        )
        btn_specials.pack(side="left", padx=(20, 5), pady=8)
        
        btn_audit = tk.Button(
            mode_frame,
            text="📊 Audit",
            command=lambda: switch_mode('audit'),
            bg="#3b4754",
            fg="white",
            activebackground="#4a5560",
            font=("Segoe UI", 12, "bold"),
            relief="flat",
            width=11
        )
        btn_audit.pack(side="left", padx=5, pady=8)
        
        btn_cover = tk.Button(
            mode_frame,
            text="⏱️ Cover Time",
            command=lambda: switch_mode('cover_time'),
            bg="#3b4754",
            fg="white",
            activebackground="#4a5560",
            font=("Segoe UI", 12, "bold"),
            relief="flat",
            width=13
        )
        btn_cover.pack(side="left", padx=5, pady=8)
        
        btn_breaks = tk.Button(
            mode_frame,
            text="☕ Breaks",
            command=lambda: switch_mode('breaks'),
            bg="#3b4754",
            fg="white",
            activebackground="#4a5560",
            font=("Segoe UI", 12, "bold"),
            relief="flat",
            width=11
        )
        btn_breaks.pack(side="left", padx=5, pady=8)
        
        btn_rol_cover = tk.Button(
            mode_frame,
            text="🎭 Rol de Cover",
            command=lambda: switch_mode('rol_cover'),
            bg="#3b4754",
            fg="white",
            activebackground="#4a5560",
            font=("Segoe UI", 12, "bold"),
            relief="flat",
            width=14
        )
        btn_rol_cover.pack(side="left", padx=5, pady=8)
        
        btn_news = tk.Button(
            mode_frame,
            text="📰 News",
            command=lambda: switch_mode('news'),
            bg="#3b4754",
            fg="white",
            activebackground="#4a5560",
            font=("Segoe UI", 12, "bold"),
            relief="flat",
            width=11
        )
        btn_news.pack(side="left", padx=5, pady=8)

    # ==================== SPECIALS CONTAINER ====================
    from views.specials_view import render_specials_container
    
    specials_widgets = render_specials_container(
        parent=top,
        username=username,
        UI=UI,
        SheetClass=SheetClass
    )
    
    specials_container = specials_widgets['container']
    sheet = specials_widgets['sheet']
    marks_frame = specials_widgets['marks_frame']
    load_data = specials_widgets['refresh']
    specials_controller = specials_widgets['controller']
    
    # ⭐ FUNCIÓN: Abrir ventana de Otros Specials (mantiene funcionalidad original)
    def open_otros_specials():
        """Ver y tomar specials de otros supervisores"""
        # Ventana de selección de supervisor
        if UI is not None:
            sel_win = UI.CTkToplevel(top)
            sel_win.configure(fg_color="#2c2f33")
        else:
            sel_win = tk.Toplevel(top)
            sel_win.configure(bg="#2c2f33")
        
        sel_win.title("Otros Specials - Selecciona Supervisor")
        sel_win.geometry("380x340")
        sel_win.resizable(False, False)

        if UI is not None:
            UI.CTkLabel(sel_win, text="Supervisor (origen):", text_color="#00bfae",
                       font=("Segoe UI", 13, "bold")).pack(pady=(14, 6))
        else:
            tk.Label(sel_win, text="Supervisor (origen):", bg="#2c2f33", fg="#00bfae",
                    font=("Segoe UI", 13, "bold")).pack(pady=(14, 6))

        if UI is not None:
            list_frame = UI.CTkFrame(sel_win, fg_color="#2c2f33")
        else:
            list_frame = tk.Frame(sel_win, bg="#2c2f33")
        list_frame.pack(fill="both", expand=True, padx=14, pady=(4,12))
        
        yscroll_sup = tk.Scrollbar(list_frame, orient="vertical")
        yscroll_sup.pack(side="right", fill="y")
        sup_listbox = tk.Listbox(list_frame, height=10, selectmode="browse",
                                 bg="#262a31", fg="#00bfae", font=("Segoe UI", 12),
                                 yscrollcommand=yscroll_sup.set, activestyle="dotbox",
                                 selectbackground="#14414e")
        sup_listbox.pack(side="left", fill="both", expand=True)
        yscroll_sup.config(command=sup_listbox.yview)

        # Cargar supervisores usando el controlador
        supervisores = specials_controller.get_all_supervisors()
        
        if not supervisores:
            sup_listbox.insert("end", "No hay supervisores disponibles")
        else:
            for sup in supervisores:
                sup_listbox.insert("end", sup)

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
            except Exception:
                pass

            # Ventana de specials del otro supervisor
            if UI is not None:
                lst_win = UI.CTkToplevel(top)
                lst_win.configure(fg_color="#2c2f33")
            else:
                lst_win = tk.Toplevel(top)
                lst_win.configure(bg="#2c2f33")
            
            lst_win.title(f"Otros Specials - {old_sup}")
            lst_win.geometry("1350x600")
            lst_win.resizable(True, True)

            # Variables locales
            row_ids_otros = []
            
            # Frame para tabla
            if UI is not None:
                frame2 = UI.CTkFrame(lst_win, fg_color="#2c2f33")
            else:
                frame2 = tk.Frame(lst_win, bg="#2c2f33")
            frame2.pack(expand=True, fill="both", padx=12, pady=10)
            
            # Crear tksheet
            cols2 = ["ID", "Fecha_hora", "ID_Sitio", "Nombre_Actividad", "Cantidad", "Camera", 
                    "Descripcion", "Usuario", "Time_Zone", "Marca"]
            
            custom_widths_otros = {
                "ID": 60, "Fecha_hora": 150, "ID_Sitio": 220, "Nombre_Actividad": 150,
                "Cantidad": 70, "Camera": 80, "Descripcion": 190, "Usuario": 100,
                "Time_Zone": 90, "Marca": 180
            }
            
            sheet2 = SheetClass(
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
                    # Usar controlador para obtener snapshot de otros specials
                    snapshot = specials_controller.load_otros_specials_snapshot(old_sup)
                    
                    if snapshot is None:
                        sheet2.set_sheet_data([[f"{old_sup} no tiene shift activo"] + [""] * (len(cols2)-1)])
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
                    
                    # Usar controlador para transferir
                    success = specials_controller.transfer_specials(ids, username)
                    
                    if success:
                        messagebox.showinfo("Tomar Specials", f"✅ {len(ids)} special(s) transferido(s)", parent=lst_win)
                        cargar_lista()
                        load_data()  # Recargar datos principales
                    else:
                        messagebox.showerror("Error", "No se pudo transferir specials", parent=lst_win)
                except Exception as e:
                    messagebox.showerror("Error", f"No se pudo tomar specials:\n{e}", parent=lst_win)
                    traceback.print_exc()
            
            # Botones
            if UI is not None:
                btn_frame = UI.CTkFrame(lst_win, fg_color="#23272a")
            else:
                btn_frame = tk.Frame(lst_win, bg="#23272a")
            btn_frame.pack(fill="x", padx=10, pady=10)
            
            if UI is not None:
                UI.CTkButton(btn_frame, text="🔄 Refrescar", command=cargar_lista,
                            fg_color="#4D6068", hover_color="#27a3e0", width=120, height=35,
                            font=("Segoe UI", 11, "bold")).pack(side="left", padx=5)
                UI.CTkButton(btn_frame, text="📥 Tomar Seleccionados", command=tomar_specials,
                            fg_color="#00c853", hover_color="#00a043", width=180, height=35,
                            font=("Segoe UI", 11, "bold")).pack(side="left", padx=5)
            else:
                tk.Button(btn_frame, text="🔄 Refrescar", command=cargar_lista,
                         bg="#4D6068", fg="white", relief="flat", width=12).pack(side="left", padx=5)
                tk.Button(btn_frame, text="📥 Tomar Seleccionados", command=tomar_specials,
                         bg="#00c853", fg="white", relief="flat", width=18).pack(side="left", padx=5)
            
            cargar_lista()
        
        # Botón abrir
        if UI is not None:
            UI.CTkButton(sel_win, text="Abrir", command=abrir_lista_specials,
                        fg_color="#00c853", hover_color="#00a043", width=140, height=35,
                        font=("Segoe UI", 12, "bold")).pack(pady=12)
        else:
            tk.Button(sel_win, text="Abrir", command=abrir_lista_specials,
                     bg="#00c853", fg="white", relief="flat", width=12).pack(pady=12)
    
    # Agregar botón "Otros Specials" al marks_frame
    if UI is not None:
        UI.CTkButton(marks_frame, text="📋 Otros Specials", 
                    command=open_otros_specials,
                    fg_color="#4a5f7a", hover_color="#3a4f6a",
                    width=150, height=35,
                    font=("Segoe UI", 11, "bold")).pack(side="left", padx=5, pady=10)
    else:
        tk.Button(marks_frame, text="📋 Otros Specials", 
                 command=open_otros_specials,
                 bg="#4a5f7a", fg="white",
                 font=("Segoe UI", 11, "bold"), relief="flat",
                 width=15).pack(side="left", padx=5, pady=10)
        
        
    # ==================== Audit CONTAINER ====================
    from views.audit_view import render_audit_container
    
    audit_widgets = render_audit_container(
        parent=top,
        UI=UI,
        SheetClass=SheetClass
    )
    
    audit_container = audit_widgets['container']


    # ==================== BREAKS CONTAINER ====================
    from views.breaks_view import render_breaks_container

    breaks_widgets = render_breaks_container(
        parent=top,
        username=username,
        UI=UI,
        SheetClass=SheetClass,
        under_super=under_super
    )
    
    breaks_container = breaks_widgets['container']

    # ===================== Rol de Cover =====================

    from views.rol_cover_view import render_rol_cover_container
    rol_cover_refs = render_rol_cover_container(
        parent=top,
        UI=UI
    )

    rol_cover_container = rol_cover_refs['container']

    # ==================== COVER TIME CONTAINER ====================
    from views.cover_time_view import render_cover_time_container
    cover_time_widgets = render_cover_time_container(
        parent=top,
        UI=UI,
        SheetClass=SheetClass
    )
    cover_container = cover_time_widgets['container']
    # ==================== NEWS CONTAINER ====================
    from views.news_view import render_news_container
    news_widgets = render_news_container(
        parent=top,
        UI=UI,
        SheetClass=SheetClass
    )
    news_container = news_widgets['container']

    # Iniciar en modo Specials
    switch_mode('specials')
    # ==================== CONFIGURAR CIERRE DE VENTANA ====================
 
# ⭐ CONFIGURAR CIERRE DE VENTANA: Ejecutar logout automáticamente
    def on_window_close_super():
        """Maneja el cierre de la ventana principal ejecutando logout y mostrando login"""
        try:
            if session_id and station:
                login.do_logout(session_id, station, top)
            if not session_id:
                try:
                    login.show_login()
                    top.destroy()
                except Exception as e:
                    print(f"[ERROR] Error during logout: {e}")
        except Exception as e:
            print(f"[ERROR] Error destroying window: {e}")
    # Configurar protocolo de cierre (botón X)
    top.protocol("WM_DELETE_WINDOW", on_window_close_super)

