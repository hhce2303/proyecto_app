



import tkinter as tk
from tkinter import ttk
import traceback
import backend_super
# 
from models.site_model import get_sites
import under_super

from models.database import get_connection
from models.user_model import load_users, get_user_status_bd

#
from tkinter import messagebox
import login
from backend_super import Dinamic_button_Shift, on_start_shift, on_end_shift, _focus_singleton, get_user_status
from views import status_views
from controllers.status_controller import StatusController




def open_hybrid_events_supervisor(username, session_id=None, station=None, root=None):
    # CREAR VARIABLES PRIMERO (aunque sean None)
    specials_container = None
    audit_container = None
    cover_container = None
    breaks_container = None
    rol_cover_container = None
    news_container = None
    """
    🚀 VENTANA HÍBRIDA PARA SUPERVISORES: Visualización de Specials
    
    Versión simplificada para supervisores que muestra solo los Specials enviados a ellos:
    - Visualización de specials del turno actual en tksheet
    - Botones: Start/End Shift, Refrescar, Eliminar
    - Marcas persistentes (Registrado, En Progreso)
    - Sin formulario de registro de eventos
    - Sin botones de Cover
    - Modo solo lectura con opciones de marcado
    """
    # Singleton
    ex = _focus_singleton('hybrid_events_supervisor')
    if ex:
        return ex

    # CustomTkinter setup
    UI = None
    try:
        import importlib
        ctk = importlib.import_module('customtkinter')
        try:
            ctk.set_appearance_mode("dark")
            ctk.set_default_color_theme("dark-blue")
        except Exception:
            pass
        UI = ctk
    except Exception:
        UI = None

    # tksheet setup
    USE_SHEET = False
    SheetClass = None
    try:
        from tksheet import Sheet as _Sheet
        SheetClass = _Sheet
        USE_SHEET = True
    except Exception:
        messagebox.showerror("Error", "tksheet no está instalado.\nInstala con: pip install tksheet")
        return

    # Crear ventana principal
    if UI is not None:
        top = UI.CTkToplevel()
        top.configure(fg_color="#1e1e1e")
    else:
        top = tk.Toplevel()
        top.configure(bg="#1e1e1e")
    
    top.title(f"📊 Specials - {username}")
    top.geometry("1320x800")
    top.resizable(True, True)

    # Variables de estado
    row_data_cache = []  # Cache de datos
    row_ids = []  # IDs de specials
    auto_refresh_active = tk.BooleanVar(value=True)
    refresh_job = None

    # Columnas para SPECIALS
    columns_specials = ["ID", "Fecha Hora", "Sitio", "Actividad", "Cantidad", "Camera", "Descripcion", "Usuario", "TZ", "Marca"]
    columns = columns_specials
    
    # Anchos personalizados para SPECIALS
    custom_widths_specials = {
        "ID": 60,
        "Fecha Hora": 150,
        "Sitio": 220,
        "Actividad": 150,
        "Cantidad": 70,
        "Camera": 80,
        "Descripcion": 190,
        "Usuario": 100,
        "TZ": 90,
        "Marca": 180
    }
    custom_widths = custom_widths_specials

    # Header
    if UI is not None:
        header = UI.CTkFrame(top, fg_color="#23272a", corner_radius=0)
    else:
        header = tk.Frame(top, bg="#23272a")
    header.pack(fill="x", padx=0, pady=0)
   
    if UI is not None:
        # ⭐ Botones Refrescar y Eliminar a la izquierda
        UI.CTkButton(header, text="🔄  Refrescar", command=lambda: load_data(),
                    fg_color="#4D6068", hover_color="#27a3e0", 
                    width=120, height=40,
                    font=("Segoe UI", 12, "bold")).pack(side="left", padx=(20, 5), pady=15)
        
        delete_btn_header = UI.CTkButton(header, text="🗑️ Eliminar", command=lambda: None,
                    fg_color="#d32f2f", hover_color="#b71c1c", 
                    width=120, height=40,
                    font=("Segoe UI", 12, "bold"))
        delete_btn_header.pack(side="left", padx=5, pady=15)
        
        # ⭐ INDICADOR DE STATUS (a la derecha, antes del botón Shift)
        status_widgets = status_views.render_status_header(
            parent_frame=header,
            username=username,
            controller=None,  # Se crea automáticamente
            UI=UI
        )

    # ==================== MODO SELECTOR (Specials / Audit / Cover Time / Breaks / Rol de Cover) ====================
    current_mode = {'value': 'specials'}  # 'specials', 'audit', 'cover_time', 'breaks', 'rol_cover'
    
    if UI is not None:
        mode_frame = UI.CTkFrame(top, fg_color="#23272a", corner_radius=0, height=50)
    else:
        mode_frame = tk.Frame(top, bg="#23272a", height=50)
    mode_frame.pack(fill="x", padx=0, pady=0)
    mode_frame.pack_propagate(False)

    def switch_mode(new_mode):
        """Cambia entre modo Specials, Audit, Cover Time, Breaks, Rol de Cover y News"""
        current_mode['value'] = new_mode
        
        # Ocultar todos los contenedores (con validación de None)
        if specials_container is not None:
            specials_container.pack_forget()
        if audit_container is not None:
            audit_container.pack_forget()
        if cover_container is not None:
            cover_container.pack_forget()
        if breaks_container is not None:
            breaks_container.pack_forget()
        if rol_cover_container is not None:
            rol_cover_container.pack_forget()
        if news_container is not None:
            news_container.pack_forget()
        
        
        # Resetear colores de todos los botones
        inactive_color = "#3b4754"
        inactive_hover = "#4a5560"
        active_color = "#4a90e2"
        active_hover = "#357ABD"
        
        if UI is not None:
            btn_specials.configure(fg_color=inactive_color, hover_color=inactive_hover)
            btn_audit.configure(fg_color=inactive_color, hover_color=inactive_hover)
            btn_cover.configure(fg_color=inactive_color, hover_color=inactive_hover)
            btn_breaks.configure(fg_color=inactive_color, hover_color=inactive_hover)
            btn_rol_cover.configure(fg_color=inactive_color, hover_color=inactive_hover)
            btn_news.configure(fg_color=inactive_color, hover_color=inactive_hover)
        else:
            btn_specials.configure(bg=inactive_color, activebackground=inactive_hover)
            btn_audit.configure(bg=inactive_color, activebackground=inactive_hover)
            btn_cover.configure(bg=inactive_color, activebackground=inactive_hover)
            btn_breaks.configure(bg=inactive_color, activebackground=inactive_hover)
            btn_rol_cover.configure(bg=inactive_color, activebackground=inactive_hover)
            btn_news.configure(bg=inactive_color, activebackground=inactive_hover)
        
        # Mostrar contenedor activo y resaltar botón
        if new_mode == 'specials':
            specials_container.pack(fill="both", expand=True, padx=10, pady=10)
            if UI is not None:
                btn_specials.configure(fg_color=active_color, hover_color=active_hover)
            else:
                btn_specials.configure(bg=active_color, activebackground=active_hover)
            load_data()
        elif new_mode == 'audit':
            audit_container.pack(fill="both", expand=True, padx=10, pady=10)
            if UI is not None:
                btn_audit.configure(fg_color=active_color, hover_color=active_hover)
            else:
                btn_audit.configure(bg=active_color, activebackground=active_hover)
        elif new_mode == 'cover_time':
            cover_container.pack(fill="both", expand=True, padx=10, pady=10)
            if UI is not None:
                btn_cover.configure(fg_color=active_color, hover_color=active_hover)
            else:
                btn_cover.configure(bg=active_color, activebackground=active_hover)
        elif new_mode == 'breaks':
            breaks_container.pack(fill="both", expand=True, padx=10, pady=10)
            if UI is not None:
                btn_breaks.configure(fg_color=active_color, hover_color=active_hover)
            else:
                btn_breaks.configure(bg=active_color, activebackground=active_hover)
            
        elif new_mode == 'rol_cover':
            rol_cover_container.pack(fill="both", expand=True, padx=10, pady=10)
            if UI is not None:
                btn_rol_cover.configure(fg_color=active_color, hover_color=active_hover)
            else:
                btn_rol_cover.configure(bg=active_color, activebackground=active_hover)
        elif new_mode == 'news':
            news_container.pack(fill="both", expand=True, padx=10, pady=10)
            if UI is not None:
                btn_news.configure(fg_color=active_color, hover_color=active_hover)
            else:
                btn_news.configure(bg=active_color, activebackground=active_hover)

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
    if UI is not None:
        specials_container = UI.CTkFrame(top, fg_color="#2c2f33")
    else:
        specials_container = tk.Frame(top, bg="#2c2f33")
    specials_container.pack(fill="both", expand=True, padx=10, pady=10)

    # Frame para tksheet de Specials
    if UI is not None:
        sheet_frame = UI.CTkFrame(specials_container, fg_color="#2c2f33")
    else:
        sheet_frame = tk.Frame(specials_container, bg="#2c2f33")
    sheet_frame.pack(fill="both", expand=True)

    # Crear tksheet
    sheet = SheetClass(
        sheet_frame,
        headers=columns,
        theme="dark blue",
        height=600,
        width=1350,
        show_selected_cells_border=True,
        show_row_index=True,
        show_top_left=False,
        empty_horizontal=0,
        empty_vertical=0
    )
    # ⭐ DESHABILITAR EDICIÓN - Solo visualización y marcado
    sheet.enable_bindings([
        "single_select",
        "drag_select",
        "column_select",
        "row_select",
        "column_width_resize",
        "double_click_column_resize",
        "row_height_resize",
        "arrowkeys",
        "right_click_popup_menu",
        "rc_select",
        "copy"
    ])
    sheet.pack(fill="both", expand=True)
    sheet.change_theme("dark blue")

    # Frame para botones de marcado (debajo del sheet de Specials)
    if UI is not None:
        marks_frame = UI.CTkFrame(specials_container, fg_color="#23272a", corner_radius=0)
    else:
        marks_frame = tk.Frame(specials_container, bg="#23272a")
    marks_frame.pack(fill="x", padx=0, pady=(5, 0))

    def apply_sheet_widths():
        """Aplica anchos personalizados a las columnas"""
        for idx, col_name in enumerate(columns):
            if col_name in custom_widths:
                try:
                    sheet.column_width(idx, int(custom_widths[col_name]))
                except Exception:
                    try:
                        sheet.set_column_width(idx, int(custom_widths[col_name]))
                    except Exception:
                        pass
        sheet.redraw()

    def get_supervisor_shift_start():
        """Obtiene la última hora de inicio de shift del supervisor"""
        try:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("""
                SELECT e.FechaHora 
                FROM Eventos e
                INNER JOIN user u ON e.ID_Usuario = u.ID_Usuario
                WHERE u.Nombre_Usuario = %s AND e.Nombre_Actividad = %s
                ORDER BY e.FechaHora DESC
                LIMIT 1
            """, (username, "START SHIFT"))
            row = cur.fetchone()
            cur.close()
            conn.close()
            return row[0] if row and row[0] else None
        except Exception as e:
            print(f"[ERROR] get_supervisor_shift_start: {e}")
            return None

    def load_data():
        """Carga solo specials sin marca (NULL) y en progreso (flagged), excluyendo los registrados (done)"""
        nonlocal row_data_cache, row_ids, refresh_job
        
        try:
            conn = get_connection()
            cur = conn.cursor()
            
            # Mostrar solo specials sin marca o en progreso, excluyendo los marcados como 'done'
            sql = """
                SELECT ID_special, FechaHora, ID_Sitio, Nombre_Actividad, Cantidad, Camera,
                       Descripcion, Usuario, Time_Zone, marked_status, marked_by, marked_at
                FROM specials
                WHERE Supervisor = %s 
                AND (marked_status IS NULL OR marked_status = '' OR marked_status = 'flagged')
                ORDER BY FechaHora DESC
            """
            cur.execute(sql, (username,))
            
            rows = cur.fetchall()
            
            # Resolver nombres de sitios y zonas horarias
            time_zone_cache = {}
            processed = []
            
            for r in rows:
                id_special = r[0]
                fecha_hora = r[1]
                id_sitio = r[2]
                nombre_actividad = r[3]
                cantidad = r[4]
                camera = r[5]
                descripcion = r[6]
                usuario = r[7]
                time_zone = r[8]
                marked_status = r[9]
                marked_by = r[10]
                marked_at = r[11]
                
                # Resolver nombre de sitio
                nombre_sitio = ""
                tz = time_zone or ""
                if id_sitio is not None and str(id_sitio).strip() != "":
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
                
                # Formato visual para Sitio (ID + Nombre)
                if id_sitio and nombre_sitio:
                    display_site = f"{id_sitio} {nombre_sitio}"
                elif id_sitio:
                    display_site = str(id_sitio)
                else:
                    display_site = nombre_sitio or ""
                
                # Formato visual para la marca
                if marked_status == 'done':
                    mark_display = f"✅ Registrado ({marked_by})" if marked_by else "✅ Registrado"
                elif marked_status == 'flagged':
                    mark_display = f"🔄 En Progreso ({marked_by})" if marked_by else "🔄 En Progreso"
                else:
                    mark_display = ""
                
                # Formatear fecha
                fecha_str = fecha_hora.strftime("%Y-%m-%d %H:%M:%S") if fecha_hora else ""
                
                # Fila para mostrar
                display_row = [
                    str(id_special),
                    fecha_str,
                    display_site,
                    nombre_actividad or "",
                    str(cantidad) if cantidad is not None else "0",
                    camera or "",
                    descripcion or "",
                    usuario or "",
                    tz,
                    mark_display
                ]
                
                processed.append({
                    'id': id_special,
                    'values': display_row,
                    'marked_status': marked_status
                })
            
            cur.close()
            conn.close()
            
            # Actualizar cache
            row_data_cache = processed
            row_ids = [item['id'] for item in processed]
            
            # Poblar sheet
            if not processed:
                data = [["No hay specials en este turno"] + [""] * (len(columns)-1)]
                sheet.set_sheet_data(data)
            else:
                data = [item['values'] for item in processed]
                sheet.set_sheet_data(data)
                
                # Aplicar anchos personalizados
                apply_sheet_widths()
                
                # Limpiar colores primero
                sheet.dehighlight_all()
                
                # Aplicar colores según marca
                for idx, item in enumerate(processed):
                    if item['marked_status'] == 'done':
                        sheet.highlight_rows([idx], bg="#00c853", fg="#111111")
                    elif item['marked_status'] == 'flagged':
                        sheet.highlight_rows([idx], bg="#f5a623", fg="#111111")
            
            apply_sheet_widths()
            
            print(f"[DEBUG] Loaded {len(row_ids)} specials for {username}")

        except Exception as e:
            messagebox.showerror("Error", f"No se pudo cargar specials:\n{e}", parent=top)
            traceback.print_exc()
        
        # Programar siguiente refresh si auto-refresh está activo
        finally:
            if auto_refresh_active.get():
                refresh_job = top.after(120000, load_data)  # Refresh cada 2 minutos

    def get_selected_ids():
        """Obtiene los IDs de los registros seleccionados"""
        selected_rows = sheet.get_selected_rows()
        if not selected_rows:
            return []
        ids = []
        for row_idx in selected_rows:
            try:
                if row_idx < len(row_ids):
                    ids.append(row_ids[row_idx])
            except Exception:
                pass
        return ids

    def mark_as_done():
        """Marca los registros seleccionados como 'Registrado'"""
        sel = get_selected_ids()
        if not sel:
            return
        
        try:
            conn = get_connection()
            cur = conn.cursor()
            
            for item_id in sel:
                cur.execute("""
                    UPDATE specials 
                    SET marked_status = 'done', marked_at = NOW(), marked_by = %s
                    WHERE ID_special = %s
                """, (username, item_id))
            
            conn.commit()
            cur.close()
            conn.close()
            
            load_data()

            
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo marcar:\n{e}", parent=top)
            traceback.print_exc()

    def mark_as_progress():
        """Marca los registros seleccionados como 'En Progreso'"""
        sel = get_selected_ids()
        if not sel:
            messagebox.showinfo("Marcar", "Selecciona uno o más specials para marcar como En Progreso.", parent=top)
            return
        
        try:
            conn = get_connection()
            cur = conn.cursor()
            
            for item_id in sel:
                cur.execute("""
                    UPDATE specials 
                    SET marked_status = 'flagged', marked_at = NOW(), marked_by = %s
                    WHERE ID_special = %s
                """, (username, item_id))
            
            conn.commit()
            cur.close()
            conn.close()
            
            load_data()
            
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo marcar:\n{e}", parent=top)
            traceback.print_exc()

    def unmark_selected():
        """Desmarca los registros seleccionados"""
        sel = get_selected_ids()
        if not sel:
            return
        
        try:
            conn = get_connection()
            cur = conn.cursor()
            
            for item_id in sel:
                cur.execute("""
                    UPDATE specials 
                    SET marked_status = NULL, marked_at = NULL, marked_by = NULL
                    WHERE ID_special = %s
                """, (item_id,))
            
            conn.commit()
            cur.close()
            conn.close()
            
            load_data()
            
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo desmarcar:\n{e}", parent=top)
            traceback.print_exc()

    def delete_selected():
        """Elimina los registros seleccionados de specials"""
        sel = get_selected_ids()
        if not sel:
            messagebox.showwarning("Eliminar", "Selecciona uno o más specials para eliminar.", parent=top)
            return
        
        if not messagebox.askyesno("Eliminar", 
                                   f"¿Eliminar {len(sel)} special(s) de la base de datos?",
                                   parent=top):
            return
        
        try:
            conn = get_connection()
            cur = conn.cursor()
            
            for item_id in sel:
                cur.execute("DELETE FROM specials WHERE ID_special = %s", (item_id,))
            
            conn.commit()
            cur.close()
            conn.close()
            
            load_data()

            
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo eliminar:\n{e}", parent=top)
            traceback.print_exc()
    
    # Asignar comando delete_selected al botón del header
    try:
        delete_btn_header.configure(command=backend_super.safe_delete)
    except:
        pass

    def show_context_menu(event):
        """Muestra menú contextual al hacer clic derecho"""
        context_menu = tk.Menu(top, tearoff=0, bg="#2c2f33", fg="#e0e0e0", 
                              activebackground="#4a90e2", activeforeground="#ffffff",
                              font=("Segoe UI", 10))
        
        context_menu.add_command(label="✅ Marcar como Registrado", command=mark_as_done)
        context_menu.add_command(label="🔄 Marcar como En Progreso", command=mark_as_progress)
        context_menu.add_separator()
        context_menu.add_command(label="❌ Desmarcar", command=unmark_selected)
        context_menu.add_command(label="🗑️ Eliminar", command=delete_selected)
        
        try:
            context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            context_menu.grab_release()

    def toggle_auto_refresh():
        """Activa/desactiva auto-refresh"""
        if auto_refresh_active.get():
            print("[DEBUG] Auto-refresh activado")
            load_data()
        else:
            print("[DEBUG] Auto-refresh desactivado")
            if refresh_job:
                top.after_cancel(refresh_job)

    # ⭐ FUNCIÓN: Abrir ventana de Otros Specials
    def open_otros_specials():
        """Ver y tomar specials de otros supervisores"""
        # Importar función auxiliar para obtener shift start de otros supervisores
        def get_supervisor_shift_start_otros(sup_name):
            """Obtiene la última hora de inicio de shift de un supervisor específico"""
            try:
                conn = get_connection()
                cur = conn.cursor()
                cur.execute("""
                    SELECT e.FechaHora 
                    FROM Eventos e
                    INNER JOIN user u ON e.ID_Usuario = u.ID_Usuario
                    WHERE u.Nombre_Usuario = %s AND e.Nombre_Actividad = %s
                    ORDER BY e.FechaHora DESC
                    LIMIT 1
                """, (sup_name, "START SHIFT"))
                row = cur.fetchone()
                cur.close()
                conn.close()
                return row[0] if row and row[0] else None
            except Exception as e:
                print(f"[ERROR] get_supervisor_shift_start_otros: {e}")
                return None
        
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

        # Cargar supervisores
        supervisores = []
        try:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("SELECT Nombre_Usuario FROM user WHERE Rol = %s ORDER BY Nombre_Usuario", ("Supervisor",))
            supervisores = [r[0] for r in cur.fetchall()]
            cur.close()
            conn.close()
        except Exception as e:
            print(f"[ERROR] otros_specials list: {e}")
        
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

            # Variables
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
                    shift_start = get_supervisor_shift_start_otros(old_sup)
                    if not shift_start:
                        sheet2.set_sheet_data([[f"{old_sup} no tiene shift activo"] + [""] * (len(cols2)-1)])
                        apply_widths()
                        row_ids_otros.clear()
                        return
                    
                    conn = get_connection()
                    cur = conn.cursor()
                    
                    cur.execute("""
                        SELECT ID_special, FechaHora, ID_Sitio, Nombre_Actividad, Cantidad, Camera,
                               Descripcion, Usuario, Time_Zone, marked_status, marked_by
                        FROM specials
                        WHERE Supervisor = %s AND FechaHora >= %s
                        ORDER BY FechaHora DESC
                    """, (old_sup, shift_start))
                    
                    rows = cur.fetchall()
                    processed = []
                    time_zone_cache = {}
                    
                    for r in rows:
                        id_sitio = r[2]
                        nombre_sitio = ""
                        tz = ""
                        
                        if id_sitio:
                            if id_sitio in time_zone_cache:
                                nombre_sitio, tz = time_zone_cache[id_sitio]
                            else:
                                try:
                                    cur.execute("SELECT Nombre_Sitio, Time_Zone FROM Sitios WHERE ID_Sitio = %s", (id_sitio,))
                                    sit = cur.fetchone()
                                    nombre_sitio = sit[0] if sit else ""
                                    tz = sit[1] if sit and len(sit) > 1 else ""
                                    time_zone_cache[id_sitio] = (nombre_sitio, tz)
                                except:
                                    pass
                        
                        display_site = f"{id_sitio} {nombre_sitio}" if id_sitio and nombre_sitio else str(id_sitio or "")
                        
                        mark_display = ""
                        if r[9] == 'done':
                            mark_display = f"✅ Registrado ({r[10]})" if r[10] else "✅ Registrado"
                        elif r[9] == 'flagged':
                            mark_display = f"🔄 En Progreso ({r[10]})" if r[10] else "🔄 En Progreso"
                        
                        fecha_str = r[1].strftime("%Y-%m-%d %H:%M:%S") if r[1] else ""
                        
                        processed.append({
                            'id': r[0],
                            'values': [str(r[0]), fecha_str, display_site, r[3] or "", 
                                     str(r[4] or 0), r[5] or "", r[6] or "", r[7] or "", 
                                     tz, mark_display],
                            'marked_status': r[9]
                        })
                    
                    cur.close()
                    conn.close()
                    
                    if not processed:
                        sheet2.set_sheet_data([["No hay specials"] + [""] * (len(cols2)-1)])
                        row_ids_otros.clear()
                    else:
                        sheet2.set_sheet_data([p['values'] for p in processed])
                        row_ids_otros[:] = [p['id'] for p in processed]
                        sheet2.dehighlight_all()
                        for idx, p in enumerate(processed):
                            if p['marked_status'] == 'done':
                                sheet2.highlight_rows([idx], bg="#00c853", fg="#111111")
                            elif p['marked_status'] == 'flagged':
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
                    
                    conn = get_connection()
                    cur = conn.cursor()
                    for sid in ids:
                        cur.execute("UPDATE specials SET Supervisor = %s WHERE ID_special = %s", (username, sid))
                    conn.commit()
                    cur.close()
                    conn.close()
                    
                    messagebox.showinfo("Tomar Specials", f"✅ {len(ids)} special(s) transferido(s)", parent=lst_win)
                    cargar_lista()
                    load_data()  # Recargar datos principales
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

    # Botones de marcado
    if UI is not None:
        UI.CTkButton(marks_frame, text="✅ Marcar como Registrado", 
                    command=mark_as_done,
                    fg_color="#00c853", hover_color="#00a043",
                    width=180, height=35,
                    font=("Segoe UI", 11, "bold")).pack(side="left", padx=(15, 5), pady=10)
        
        UI.CTkButton(marks_frame, text="🔄 Marcar como En Progreso", 
                    command=mark_as_progress,
                    fg_color="#f5a623", hover_color="#e69515",
                    width=200, height=35,
                    font=("Segoe UI", 11, "bold")).pack(side="left", padx=5, pady=10)
        
        UI.CTkButton(marks_frame, text="❌ Desmarcar", 
                    command=unmark_selected,
                    fg_color="#3b4754", hover_color="#4a5560",
                    width=120, height=35,
                    font=("Segoe UI", 11, "bold")).pack(side="left", padx=5, pady=10)
        
        UI.CTkButton(marks_frame, text="📋 Otros Specials", 
                    command=open_otros_specials,
                    fg_color="#4a5f7a", hover_color="#3a4f6a",
                    width=150, height=35,
                    font=("Segoe UI", 11, "bold")).pack(side="left", padx=5, pady=10)
        
        UI.CTkCheckBox(marks_frame, text="Auto-refresh (2 min)", 
                      variable=auto_refresh_active,
                      fg_color="#4a90e2", text_color="#e0e0e0",
                      command=toggle_auto_refresh,
                      font=("Segoe UI", 10)).pack(side="right", padx=(5, 15), pady=10)
    else:
        tk.Button(marks_frame, text="✅ Marcar como Registrado", 
                 command=mark_as_done,
                 bg="#00c853", fg="white",
                 font=("Segoe UI", 11, "bold"), relief="flat",
                 width=20).pack(side="left", padx=(15, 5), pady=10)
        
        tk.Button(marks_frame, text="🔄 Marcar como En Progreso", 
                 command=mark_as_progress,
                 bg="#f5a623", fg="white",
                 font=("Segoe UI", 11, "bold"), relief="flat",
                 width=22).pack(side="left", padx=5, pady=10)
        
        tk.Button(marks_frame, text="❌ Desmarcar", 
                 command=unmark_selected,
                 bg="#3b4754", fg="white",
                 font=("Segoe UI", 11, "bold"), relief="flat",
                 width=12).pack(side="left", padx=5, pady=10)
        
        tk.Button(marks_frame, text="📋 Otros Specials", 
                 command=open_otros_specials,
                 bg="#4a5f7a", fg="white",
                 font=("Segoe UI", 11, "bold"), relief="flat",
                 width=15).pack(side="left", padx=5, pady=10)
        
        tk.Checkbutton(marks_frame, text="Auto-refresh (2 min)", 
                      variable=auto_refresh_active,
                      command=toggle_auto_refresh,
                      bg="#23272a", fg="#e0e0e0", selectcolor="#23272a",
                      font=("Segoe UI", 10)).pack(side="right", padx=(5, 15), pady=10)

    # ==================== AUDIT CONTAINER ====================
    if UI is not None:
        audit_container = UI.CTkFrame(top, fg_color="#2c2f33")
    else:
        audit_container = tk.Frame(top, bg="#2c2f33")
    # NO hacer pack() aquí - se mostrará solo cuando se cambie a modo Audit

    # Frame de filtros de Audit
    if UI is not None:
        audit_filters = UI.CTkFrame(audit_container, fg_color="#23272a", corner_radius=8)
    else:
        audit_filters = tk.Frame(audit_container, bg="#23272a")
    audit_filters.pack(fill="x", padx=10, pady=10)

    # Fila 1: Usuario y Sitio
    if UI is not None:
        UI.CTkLabel(audit_filters, text="Usuario:", text_color="#c9d1d9", 
                   font=("Segoe UI", 11)).grid(row=0, column=0, sticky="w", padx=(15, 5), pady=10)
    else:
        tk.Label(audit_filters, text="Usuario:", bg="#23272a", fg="#c9d1d9", 
                font=("Segoe UI", 11)).grid(row=0, column=0, sticky="w", padx=(15, 5), pady=10)
    
    audit_user_var = tk.StringVar()
    # Obtener usuarios
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT `Nombre_Usuario` FROM `user` ORDER BY `Nombre_Usuario`")
        audit_users = [r[0] for r in cur.fetchall()]
        cur.close()
        conn.close()
    except Exception:
        audit_users = []
    
    try:
        audit_user_cb = under_super.FilteredCombobox(audit_filters, textvariable=audit_user_var, 
                                                     values=audit_users, width=25)
    except Exception:
        audit_user_cb = ttk.Combobox(audit_filters, textvariable=audit_user_var, 
                                     values=audit_users, width=25)
    audit_user_cb.grid(row=0, column=1, sticky="w", padx=5, pady=10)

    if UI is not None:
        UI.CTkLabel(audit_filters, text="Sitio:", text_color="#c9d1d9", 
                   font=("Segoe UI", 11)).grid(row=0, column=2, sticky="w", padx=(15, 5), pady=10)
    else:
        tk.Label(audit_filters, text="Sitio:", bg="#23272a", fg="#c9d1d9", 
                font=("Segoe UI", 11)).grid(row=0, column=2, sticky="w", padx=(15, 5), pady=10)
    
    audit_site_var = tk.StringVar()
    try:
        audit_sites = get_sites()
    except Exception:
        audit_sites = []
    
    try:
        audit_site_cb = under_super.FilteredCombobox(audit_filters, textvariable=audit_site_var, 
                                                     values=audit_sites, width=35)
    except Exception:
        audit_site_cb = ttk.Combobox(audit_filters, textvariable=audit_site_var, 
                                     values=audit_sites, width=35)
    audit_site_cb.grid(row=0, column=3, sticky="w", padx=5, pady=10)

    # Fila 2: Fecha y botones
    if UI is not None:
        UI.CTkLabel(audit_filters, text="Fecha:", text_color="#c9d1d9", 
                   font=("Segoe UI", 11)).grid(row=1, column=0, sticky="w", padx=(15, 5), pady=10)
    else:
        tk.Label(audit_filters, text="Fecha:", bg="#23272a", fg="#c9d1d9", 
                font=("Segoe UI", 11)).grid(row=1, column=0, sticky="w", padx=(15, 5), pady=10)
    
    audit_fecha_var = tk.StringVar()
    try:
        from tkcalendar import DateEntry
        audit_fecha_entry = DateEntry(
            audit_filters,
            textvariable=audit_fecha_var,
            date_pattern="yyyy-mm-dd",
            width=23
        )
    except Exception:
        audit_fecha_entry = tk.Entry(audit_filters, textvariable=audit_fecha_var, width=25)
    audit_fecha_entry.grid(row=1, column=1, sticky="w", padx=5, pady=10)

    # Botones de búsqueda y limpiar
    audit_btn_frame = tk.Frame(audit_filters, bg="#23272a")
    audit_btn_frame.grid(row=1, column=2, columnspan=2, sticky="e", padx=(15, 15), pady=10)

    def audit_search():
        """Busca eventos con los filtros especificados"""
        try:
            user_filter = audit_user_var.get().strip()
            site_filter_raw = audit_site_var.get().strip()
            fecha_filter = audit_fecha_var.get().strip()
            
            conn = get_connection()
            cur = conn.cursor()
            
            sql = """
                SELECT e.ID_Eventos, e.FechaHora, s.Nombre_Sitio, e.Nombre_Actividad, 
                       e.Cantidad, e.Camera, e.Descripcion, u.Nombre_Usuario
                FROM Eventos e
                LEFT JOIN Sitios s ON e.ID_Sitio = s.ID_Sitio
                LEFT JOIN user u ON e.ID_Usuario = u.ID_Usuario
                WHERE 1=1
            """
            params = []
            
            if user_filter:
                sql += " AND u.Nombre_Usuario = %s"
                params.append(user_filter)
            
            # ⭐ USAR HELPER para deconstruir formato "Nombre (ID)"
            if site_filter_raw:
                site_name, site_id = under_super.parse_site_filter(site_filter_raw)
                
                if site_name and site_id:
                    # Buscar por nombre (más preciso cuando tenemos ambos)
                    sql += " AND s.Nombre_Sitio = %s"
                    params.append(site_name)
                elif site_id:
                    # Buscar solo por ID
                    sql += " AND s.ID_Sitio = %s"
                    params.append(site_id)
                elif site_name:
                    # Buscar solo por nombre
                    sql += " AND s.Nombre_Sitio = %s"
                    params.append(site_name)
            
            if fecha_filter:
                sql += " AND DATE(e.FechaHora) = %s"
                params.append(fecha_filter)
            
            sql += " ORDER BY e.FechaHora DESC LIMIT 500"
            
            cur.execute(sql, params)
            rows = cur.fetchall()
            cur.close()
            conn.close()
            
            # Mostrar resultados en audit_sheet
            data = []
            for r in rows:
                data.append([
                    r[0] or "",  # ID_Eventos
                    str(r[1]) if r[1] else "",  #  
                    r[2] or "",  # Nombre_Sitio
                    r[3] or "",  # Nombre_Actividad
                    r[4] or "",  # Cantidad
                    r[5] or "",  # Camera
                    r[6] or "",  # Descripcion
                    r[7] or ""   # Usuario
                ])
            
            audit_sheet.set_sheet_data(data)
            
            # Aplicar anchos personalizados
            audit_widths = {
                "ID_Evento": 80,
                " ": 150,
                "Nombre_Sitio": 220,
                "Nombre_Actividad": 150,
                "Cantidad": 70,
                "Camera": 70,
                "Descripcion": 200,
                "Usuario": 100
            }
            cols = ["ID_Evento", " ", "Nombre_Sitio", "Nombre_Actividad", 
                   "Cantidad", "Camera", "Descripcion", "Usuario"]
            for idx, col_name in enumerate(cols):
                if col_name in audit_widths:
                    try:
                        audit_sheet.column_width(idx, int(audit_widths[col_name]))
                    except Exception:
                        pass
            audit_sheet.redraw()
            
            print(f"[DEBUG] Audit search returned {len(rows)} results")
            
        except Exception as e:
            messagebox.showerror("Error", f"Error en búsqueda:\n{e}", parent=top)
            traceback.print_exc()

    def audit_clear():
        """Limpia los filtros de búsqueda"""
        audit_user_var.set("")
        audit_site_var.set("")
        audit_fecha_var.set("")
        audit_sheet.set_sheet_data([[]])

    if UI is not None:
        UI.CTkButton(
            audit_btn_frame,
            text="� Buscar",
            command=audit_search,
            fg_color="#4a90e2",
            hover_color="#357ABD",
            width=100,
            height=32,
            font=("Segoe UI", 11, "bold")
        ).pack(side="left", padx=(0, 8))
        
        UI.CTkButton(
            audit_btn_frame,
            text="🗑️ Limpiar",
            command=audit_clear,
            fg_color="#3b4754",
            hover_color="#4a5560",
            width=100,
            height=32,
            font=("Segoe UI", 11, "bold")
        ).pack(side="left")
    else:
        tk.Button(
            audit_btn_frame,
            text="🔍 Buscar",
            command=audit_search,
            bg="#4a90e2",
            fg="white",
            activebackground="#357ABD",
            font=("Segoe UI", 11, "bold"),
            relief="flat",
            width=10
        ).pack(side="left", padx=(0, 8))
        
        tk.Button(
            audit_btn_frame,
            text="🗑️ Limpiar",
            command=audit_clear,
            bg="#3b4754",
            fg="white",
            activebackground="#4a5560",
            font=("Segoe UI", 11, "bold"),
            relief="flat",
            width=10
        ).pack(side="left")

    # Frame para tksheet de Audit
    if UI is not None:
        audit_sheet_frame = UI.CTkFrame(audit_container, fg_color="#2c2f33")
    else:
        audit_sheet_frame = tk.Frame(audit_container, bg="#2c2f33")
    audit_sheet_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))

    # Crear tksheet para Audit
    audit_columns = ["ID_Evento", " ", "Nombre_Sitio", "Nombre_Actividad", 
                    "Cantidad", "Camera", "Descripcion", "Usuario"]
    audit_sheet = SheetClass(audit_sheet_frame, data=[[]], headers=audit_columns)
    audit_sheet.enable_bindings([
        "single_select",
        "row_select",
        "column_width_resize",
        "rc_select",
        "copy",
        "select_all"
    ])
    audit_sheet.pack(fill="both", expand=True)
    audit_sheet.change_theme("dark blue")

    # ==================== NEWS CONTAINER ====================

    # supervisor_window.py
    from views.news_view import create_news_container
    from controllers.news_controller import NewsController

    # Crear instancia del controlador
    news_controller = NewsController(username=username)

    # Pasar controller a la vista
    news_container = create_news_container(
        top, 
        username=username,
        controller=news_controller,
        UI=UI
    )

    # ==================== BREAKS CONTAINER ====================
    from views.breaks_view import render_breaks_container

    breaks_widgets = render_breaks_container(
        parent=top,
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
    if UI is not None:
        cover_container = UI.CTkFrame(top, fg_color="#2c2f33")
    else:
        cover_container = tk.Frame(top, bg="#2c2f33")
    # NO hacer pack() aquí - se mostrará solo cuando se cambie a modo Cover Time

    # Frame de filtros para covers_realizados
    if UI is not None:
        cover_filters_frame = UI.CTkFrame(cover_container, fg_color="#23272a", corner_radius=8)
    else:
        cover_filters_frame = tk.Frame(cover_container, bg="#23272a")
    cover_filters_frame.pack(fill="x", padx=10, pady=10)

    # Variables de filtros
    cover_user_var = tk.StringVar()
    cover_desde_var = tk.StringVar()
    cover_hasta_var = tk.StringVar()

    # Fila de filtros
    if UI is not None:
        UI.CTkLabel(cover_filters_frame, text="Usuario:", text_color="#c9d1d9", 
                   font=("Segoe UI", 11)).grid(row=0, column=0, sticky="w", padx=(15, 5), pady=10)
    else:
        tk.Label(cover_filters_frame, text="Usuario:", bg="#23272a", fg="#c9d1d9", 
                font=("Segoe UI", 11)).grid(row=0, column=0, sticky="w", padx=(15, 5), pady=10)

    # Obtener usuarios para el filtro
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT DISTINCT Nombre_usuarios FROM covers_realizados WHERE Nombre_usuarios IS NOT NULL ORDER BY Nombre_usuarios")
        cover_users = ["Todos"] + [r[0] for r in cur.fetchall()]
        cur.close()
        conn.close()
    except Exception:
        cover_users = ["Todos"]

    cover_user_cb = ttk.Combobox(cover_filters_frame, textvariable=cover_user_var, 
                                 values=cover_users, width=20, state="readonly")
    cover_user_cb.set("Todos")
    cover_user_cb.grid(row=0, column=1, sticky="w", padx=5, pady=10)

    if UI is not None:
        UI.CTkLabel(cover_filters_frame, text="Desde:", text_color="#c9d1d9", 
                   font=("Segoe UI", 11)).grid(row=0, column=2, sticky="w", padx=(15, 5), pady=10)
    else:
        tk.Label(cover_filters_frame, text="Desde:", bg="#23272a", fg="#c9d1d9", 
                font=("Segoe UI", 11)).grid(row=0, column=2, sticky="w", padx=(15, 5), pady=10)

    try:
        from tkcalendar import DateEntry
        cover_desde_entry = DateEntry(
            cover_filters_frame,
            textvariable=cover_desde_var,
            date_pattern="yyyy-mm-dd",
            width=15
        )
    except Exception:
        cover_desde_entry = tk.Entry(cover_filters_frame, textvariable=cover_desde_var, width=17)
    cover_desde_entry.grid(row=0, column=3, sticky="w", padx=5, pady=10)

    if UI is not None:
        UI.CTkLabel(cover_filters_frame, text="Hasta:", text_color="#c9d1d9", 
                   font=("Segoe UI", 11)).grid(row=0, column=4, sticky="w", padx=(15, 5), pady=10)
    else:
        tk.Label(cover_filters_frame, text="Hasta:", bg="#23272a", fg="#c9d1d9", 
                font=("Segoe UI", 11)).grid(row=0, column=4, sticky="w", padx=(15, 5), pady=10)

    try:
        from tkcalendar import DateEntry
        cover_hasta_entry = DateEntry(
            cover_filters_frame,
            textvariable=cover_hasta_var,
            date_pattern="yyyy-mm-dd",
            width=15
        )
    except Exception:
        cover_hasta_entry = tk.Entry(cover_filters_frame, textvariable=cover_hasta_var, width=17)
    cover_hasta_entry.grid(row=0, column=5, sticky="w", padx=5, pady=10)

    # Configuración de tablas y columnas
    candidate_tables = ["covers_programados", "covers_realizados"]
    Columnas_deseadas_covers = {
        "covers_programados": ["ID_user", "Time_request", "Station", "Reason", "Approved", "is_Active"],
        "covers_realizados": ["Nombre_usuarios", "Cover_in", "Cover_out", "Covered_by", "Motivo"]
    }

    # Variable para guardar referencia al sheet de covers_realizados
    cover_realizados_sheet_ref = None

    def load_cover_table(tabla):
        """Carga datos de una tabla de covers desde la BD"""
        try:
            conn = get_connection()
            cur = conn.cursor()
            query = f"SELECT * FROM {tabla}"
            cur.execute(query)
            rows = cur.fetchall()
            col_names = [desc[0] for desc in cur.description]
            cur.close()
            conn.close()
            return col_names, rows
        except Exception as e:
            print(f"[ERROR] load_cover_table({tabla}): {e}")
            return [], []

    def apply_cover_filters():
        """Aplica filtros a la tabla covers_realizados"""
        nonlocal cover_realizados_sheet_ref
        
        if cover_realizados_sheet_ref is None:
            messagebox.showwarning("Filtrar", "No hay datos de covers realizados cargados.", parent=top)
            return
        
        try:
            user_filter = cover_user_var.get().strip()
            desde_filter = cover_desde_var.get().strip()
            hasta_filter = cover_hasta_var.get().strip()
            
            conn = get_connection()
            cur = conn.cursor()
            
            sql = "SELECT Nombre_usuarios, Cover_in, Cover_out, Covered_by, Motivo FROM covers_realizados WHERE 1=1"
            params = []
            
            if user_filter and user_filter != "Todos":
                sql += " AND Nombre_usuarios = %s"
                params.append(user_filter)
            
            if desde_filter:
                sql += " AND DATE(Cover_in) >= %s"
                params.append(desde_filter)
            
            if hasta_filter:
                sql += " AND DATE(Cover_in) <= %s"
                params.append(hasta_filter)
            
            sql += " ORDER BY Cover_in DESC"
            
            cur.execute(sql, params)
            rows = cur.fetchall()
            cur.close()
            conn.close()
            
            # Procesar datos con duración
            filtered_data = []
            for idx, row in enumerate(rows, start=1):
                nombre_usuarios = row[0] if row[0] else ""
                cover_in = row[1]
                cover_out = row[2]
                covered_by = row[3] if row[3] else ""
                motivo = row[4] if row[4] else ""
                
                # Calcular duración
                duration_str = ""
                if cover_in and cover_out:
                    try:
                        from datetime import datetime, timedelta
                        if isinstance(cover_in, str):
                            cover_in = datetime.strptime(cover_in, "%Y-%m-%d %H:%M:%S")
                        if isinstance(cover_out, str):
                            cover_out = datetime.strptime(cover_out, "%Y-%m-%d %H:%M:%S")
                        
                        delta = cover_out - cover_in
                        hours, remainder = divmod(int(delta.total_seconds()), 3600)
                        minutes, seconds = divmod(remainder, 60)
                        duration_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
                    except Exception as e:
                        print(f"[ERROR] Error calculando duración: {e}")
                        duration_str = "Error"
                
                # Formatear datos para mostrar (con índice "#" al inicio)
                filtered_data.append([
                    str(idx),  # Índice #
                    nombre_usuarios,
                    str(cover_in) if cover_in else "",
                    duration_str,
                    str(cover_out) if cover_out else "",
                    covered_by,
                    motivo
                ])
            
            if not filtered_data:
                filtered_data = [["", "No hay resultados con estos filtros"] + [""] * 5]
            
            cover_realizados_sheet_ref.set_sheet_data(filtered_data)
            cover_realizados_sheet_ref.redraw()
            
            print(f"[DEBUG] Cover filters applied: {len(rows)} results")
            
        except Exception as e:
            messagebox.showerror("Error", f"Error aplicando filtros:\n{e}", parent=top)
            traceback.print_exc()

    def clear_cover_filters():
        """Limpia los filtros y recarga todos los datos"""
        nonlocal cover_realizados_sheet_ref
        
        cover_user_var.set("Todos")
        cover_desde_var.set("")
        cover_hasta_var.set("")
        
        if cover_realizados_sheet_ref is None:
            return
        
        # Recargar todos los datos
        try:
            col_names, rows = load_cover_table("covers_realizados")
            
            indices = [col_names.index(c) for c in Columnas_deseadas_covers["covers_realizados"] if c in col_names]
            
            cover_in_idx = None
            cover_out_idx = None
            if "Cover_in" in col_names:
                cover_in_idx = col_names.index("Cover_in")
            if "Cover_out" in col_names:
                cover_out_idx = col_names.index("Cover_out")
            
            filtered_data = []
            for idx_num, row in enumerate(rows, start=1):
                filtered_row = [row[idx] for idx in indices]
                
                if cover_in_idx is not None and cover_out_idx is not None:
                    cover_in = row[cover_in_idx]
                    cover_out = row[cover_out_idx]
                    
                    duration_str = ""
                    if cover_in and cover_out:
                        try:
                            from datetime import datetime, timedelta
                            if isinstance(cover_in, str):
                                cover_in = datetime.strptime(cover_in, "%Y-%m-%d %H:%M:%S")
                            if isinstance(cover_out, str):
                                cover_out = datetime.strptime(cover_out, "%Y-%m-%d %H:%M:%S")
                            
                            delta = cover_out - cover_in
                            hours, remainder = divmod(int(delta.total_seconds()), 3600)
                            minutes, seconds = divmod(remainder, 60)
                            duration_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
                        except Exception as e:
                            print(f"[ERROR] Error calculando duración: {e}")
                            duration_str = "Error"
                    
                    filtered_row = ["" if v is None else str(v) for v in filtered_row]
                    filtered_row.insert(2, duration_str)
                    filtered_row.insert(0, str(idx_num))  # Agregar índice al inicio
                else:
                    filtered_row = ["" if v is None else str(v) for v in filtered_row]
                    filtered_row.insert(0, str(idx_num))  # Agregar índice al inicio
                
                filtered_data.append(filtered_row)
            
            cover_realizados_sheet_ref.set_sheet_data(filtered_data)
            cover_realizados_sheet_ref.redraw()
            
        except Exception as e:
            print(f"[ERROR] clear_cover_filters: {e}")
            traceback.print_exc()

    # Botones de filtro
    cover_btn_frame = tk.Frame(cover_filters_frame, bg="#23272a")
    cover_btn_frame.grid(row=0, column=6, sticky="e", padx=(15, 15), pady=10)

    if UI is not None:
        UI.CTkButton(
            cover_btn_frame,
            text="🔍 Filtrar",
            command=apply_cover_filters,
            fg_color="#4a90e2",
            hover_color="#357ABD",
            width=100,
            height=32,
            font=("Segoe UI", 11, "bold")
        ).pack(side="left", padx=(0, 8))
        
        UI.CTkButton(
            cover_btn_frame,
            text="🗑️ Limpiar",
            command=clear_cover_filters,
            fg_color="#3b4754",
            hover_color="#4a5560",
            width=100,
            height=32,
            font=("Segoe UI", 11, "bold")
        ).pack(side="left")
    else:
        tk.Button(
            cover_btn_frame,
            text="🔍 Filtrar",
            command=apply_cover_filters,
            bg="#4a90e2",
            fg="white",
            activebackground="#357ABD",
            font=("Segoe UI", 11, "bold"),
            relief="flat",
            width=10
        ).pack(side="left", padx=(0, 8))
        
        tk.Button(
            cover_btn_frame,
            text="🗑️ Limpiar",
            command=clear_cover_filters,
            bg="#3b4754",
            fg="white",
            activebackground="#4a5560",
            font=("Segoe UI", 11, "bold"),
            relief="flat",
            width=10
        ).pack(side="left")

    # Crear TabView para covers_programados y covers_realizados
    if UI is not None:
        cover_notebook = UI.CTkTabview(cover_container, width=1280, height=650)
    else:
        cover_notebook = ttk.Notebook(cover_container)
    cover_notebook.pack(padx=10, pady=10, fill="both", expand=True)

    # Crear pestaña para cada tabla
    for tabla in candidate_tables:
        col_names, rows = load_cover_table(tabla)
        
        # Filtrar solo las columnas deseadas
        indices = [col_names.index(c) for c in Columnas_deseadas_covers[tabla] if c in col_names]
        filtered_col_names = [col_names[i] for i in indices]
        
        if not filtered_col_names:
            continue

        # Crear pestaña con nombres descriptivos
        tab_name = "Lista de Covers" if tabla == "covers_programados" else "Covers Completados"
        
        if UI is not None:
            tab = cover_notebook.add(tab_name)
        else:
            tab = tk.Frame(cover_notebook, bg="#2c2f33")
            cover_notebook.add(tab, text=tab_name)
        
        # Frame para el tksheet
        if UI is not None:
            sheet_frame_cover = UI.CTkFrame(tab, fg_color="#2c2f33")
        else:
            sheet_frame_cover = tk.Frame(tab, bg="#2c2f33")
        sheet_frame_cover.pack(fill="both", expand=True, padx=10, pady=10)

        # Headers personalizados en español con índice "#"
        program_headers = ["#", "Usuario", "Hora solicitud", "Estación", "Razón", "Aprobación", "Estado"]
        realized_headers = ["#", "Usuario", "Inicio Cover", "Duracion", "Fin Cover", "Cubierto por", "Motivo"]
        headers = program_headers if tabla == "covers_programados" else realized_headers

        # Crear tksheet
        cover_tab_sheet = SheetClass(
            sheet_frame_cover,
            headers=headers,
            theme="dark blue",
            height=550,
            width=1220,
            show_selected_cells_border=True,
            show_row_index=False,  # Desactivar índice automático, usaremos columna #
            show_top_left=False,
            empty_horizontal=0,
            empty_vertical=0
        )
        
        # Configurar bindings (solo lectura con selección)
        cover_tab_sheet.enable_bindings([
            "single_select",
            "drag_select",
            "row_select",
            "column_select",
            "column_width_resize",
            "double_click_column_resize",
            "arrowkeys",
            "copy",
            "select_all"
        ])
        
        cover_tab_sheet.pack(fill="both", expand=True)
        cover_tab_sheet.change_theme("dark blue")
        
        # Guardar referencia al sheet de covers_realizados
        if tabla == "covers_realizados":
            cover_realizados_sheet_ref = cover_tab_sheet

        # Preparar datos filtrados
        filtered_data = []
        orig_is_idx = None
        if 'is_Active' in Columnas_deseadas_covers.get(tabla, []) and 'is_Active' in col_names:
            try:
                orig_is_idx = col_names.index('is_Active')
            except Exception:
                orig_is_idx = None

        # Para covers_realizados, necesitamos calcular la duración
        cover_in_idx = None
        cover_out_idx = None
        if tabla == "covers_realizados":
            try:
                if "Cover_in" in col_names:
                    cover_in_idx = col_names.index("Cover_in")
                if "Cover_out" in col_names:
                    cover_out_idx = col_names.index("Cover_out")
            except Exception:
                pass

        for row_idx, row in enumerate(rows, start=1):
            filtered_row = [row[idx] for idx in indices]
            
            # Si es covers_realizados, calcular e insertar duración
            if tabla == "covers_realizados" and cover_in_idx is not None and cover_out_idx is not None:
                cover_in = row[cover_in_idx]
                cover_out = row[cover_out_idx]
                
                # Calcular duración
                duration_str = ""
                if cover_in and cover_out:
                    try:
                        from datetime import datetime, timedelta
                        # Si son strings, convertir a datetime
                        if isinstance(cover_in, str):
                            cover_in = datetime.strptime(cover_in, "%Y-%m-%d %H:%M:%S")
                        if isinstance(cover_out, str):
                            cover_out = datetime.strptime(cover_out, "%Y-%m-%d %H:%M:%S")
                        
                        delta = cover_out - cover_in
                        hours, remainder = divmod(int(delta.total_seconds()), 3600)
                        minutes, seconds = divmod(remainder, 60)
                        duration_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
                    except Exception as e:
                        print(f"[ERROR] Error calculando duración: {e}")
                        duration_str = "Error"
                
                # Convertir valores None a string vacío
                filtered_row = ["" if v is None else str(v) for v in filtered_row]
                
                # Insertar duración en la posición correcta (después de Cover_in, antes de Cover_out)
                # Headers: ["#", "Usuario", "Inicio Cover", "Duracion", "Fin Cover", "Cubierto por", "Motivo"]
                # filtered_row: [Usuario, Cover_in, Cover_out, Covered_by, Motivo]
                # Necesitamos insertar duration_str en el índice 2
                filtered_row.insert(2, duration_str)
                # Agregar índice al inicio
                filtered_row.insert(0, str(row_idx))
            else:
                # Convertir valores None a string vacío
                filtered_row = ["" if v is None else str(v) for v in filtered_row]
                
                # Convertir Approved (índice 4) e is_Active (índice 5) a texto descriptivo
                if len(filtered_row) > 4:
                    # Approved: 1 = Aprobado, 0 = No Aprobado
                    try:
                        approved_val = int(filtered_row[4]) if filtered_row[4] and filtered_row[4] != "" else 0
                        filtered_row[4] = "Aprobado" if approved_val == 1 else "No Aprobado"
                    except (ValueError, IndexError):
                        filtered_row[4] = "No Aprobado"
                
                if len(filtered_row) > 5:
                    # is_Active: 1 = Abierto, 0 = Cerrado
                    try:
                        active_val = int(filtered_row[5]) if filtered_row[5] and filtered_row[5] != "" else 0
                        filtered_row[5] = "Abierto" if active_val == 1 else "Cerrado"
                    except (ValueError, IndexError):
                        filtered_row[5] = "Cerrado"
                
                # Agregar índice al inicio
                filtered_row.insert(0, str(row_idx))
            
            filtered_data.append(filtered_row)

        # Insertar datos en el sheet
        cover_tab_sheet.set_sheet_data(filtered_data)

        # Aplicar formato a filas inactivas (is_Active == 0)
        if orig_is_idx is not None:
            try:
                filtered_is_idx = indices.index(orig_is_idx)
                for i, row in enumerate(rows):
                    if row[orig_is_idx] == 0:
                        # Aplicar resaltado gris a toda la fila
                        cover_tab_sheet.highlight_rows([i], bg="#3a3a3a", fg="#808080")
            except (ValueError, Exception):
                pass
        
        # Ajustar anchos de columna con índice "#" incluido
        if tabla == "covers_programados":
            # ["#", "Usuario", "Hora solicitud", "Estación", "Razón", "Aprobación", "Estado"]
            cover_tab_sheet.column_width(column=0, width=50)   # #
            cover_tab_sheet.column_width(column=1, width=150)  # Usuario
            cover_tab_sheet.column_width(column=2, width=180)  # Hora solicitud
            cover_tab_sheet.column_width(column=3, width=100)  # Estación
            cover_tab_sheet.column_width(column=4, width=300)  # Razón
            cover_tab_sheet.column_width(column=5, width=110)  # Aprobación
            cover_tab_sheet.column_width(column=6, width=90)   # Estado
        else:  # covers_realizados
            # ["#", "Usuario", "Inicio Cover", "Duracion", "Fin Cover", "Cubierto por", "Motivo"]
            cover_tab_sheet.column_width(column=0, width=50)   # #
            cover_tab_sheet.column_width(column=1, width=150)  # Usuario
            cover_tab_sheet.column_width(column=2, width=160)  # Inicio Cover
            cover_tab_sheet.column_width(column=3, width=100)  # Duracion
            cover_tab_sheet.column_width(column=4, width=160)  # Fin Cover
            cover_tab_sheet.column_width(column=5, width=150)  # Cubierto por
            cover_tab_sheet.column_width(column=6, width=250)  # Motivo
        
        cover_tab_sheet.redraw()
    
    # Frame de filtros de Cover Time (lo dejamos oculto ya que ahora tenemos tabs)
    if UI is not None:
        cover_filters = UI.CTkFrame(cover_container, fg_color="#23272a", corner_radius=8)
    else:
        cover_filters = tk.Frame(cover_container, bg="#23272a")
    # NO hacer pack - los filtros ya no se usan con el nuevo diseño de tabs
    
    # ⭐ El código antiguo de filtros y búsqueda ha sido reemplazado por el sistema de tabs con tksheet

    # ==================== TOOLBAR (Footer) - Eliminado, Cover Time ahora es modo integrado ====================
    # Ya no necesitamos toolbar, Cover Time es un modo como Audit

    # Vincular eventos
    sheet.bind("<Button-3>", show_context_menu)  # Menú contextual
    sheet.bind("<Double-Button-1>", lambda e: mark_as_done())  # Doble-click marca como "Registrado"

    
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

