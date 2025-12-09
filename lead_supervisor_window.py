import under_super

from models.database  import get_connection
from models.user_model import load_users, get_user_status_bd
from models.site_model import get_sites
#
import login
import tkinter as tk
import re
import traceback
from tkinter import font as tkfont
from backend_super import safe_delete, _focus_singleton, Dinamic_button_Shift, on_start_shift, on_end_shift
from tksheet import Sheet
import login
from tkinter import ttk, messagebox





def open_hybrid_events_lead_supervisor(username, session_id=None, station=None, root=None):
    """
    🚀 VENTANA HÍBRIDA PARA LEAD SUPERVISORS: Visualización de Specials con permisos de eliminación
    
    Similar a supervisores pero con permisos adicionales:
    - Visualización de specials del turno actual
    - Botones: Refrescar, Eliminar (con permisos completos)
    - Marcas persistentes (Registrado, En Progreso)
    - Auto-logout al cerrar ventana
    """
    # Singleton
    ex = _focus_singleton('hybrid_events_lead_supervisor')
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
    
    top.title(f"👔 Lead Supervisor - Specials - {username}")
    top.geometry("1350x800")
    top.resizable(True, True)

    # Variables de estado
    row_data_cache = []  # Cache de datos
    row_ids = []  # IDs de specials
    auto_refresh_active = tk.BooleanVar(value=True)
    refresh_job = None

    # Columnas
    columns = [" ", "Sitio", "Actividad", "Cantidad", "Camera", "Descripcion", "Usuario", "TZ", "Marca", "Marcado Por"]
    
    # Anchos personalizados
    custom_widths = {
        " ": 150,
        "Sitio": 220,
        "Actividad": 150,
        "Cantidad": 70,
        "Camera": 80,
        "Descripcion": 160,
        "Usuario": 100,
        "TZ": 90,
        "Marca": 150,
        "Marcado Por": 150
    }

    # ==================== FUNCIONES DE DATOS ====================
    
    def load_data():
        """Carga los specials desde el ID más antiguo sin marca hasta el más reciente"""
        try:
            conn = get_connection()
            cursor = conn.cursor()
            
            # Obtener el ID más antiguo sin marca (done o flagged) del Lead Supervisor
            cursor.execute("""
                SELECT MIN(ID_special) 
                FROM specials 
                WHERE Supervisor = %s 
                AND (marked_status IS NULL OR marked_status = '')
            """, (username,))
            oldest_unmarked_row = cursor.fetchone()
            oldest_id = oldest_unmarked_row[0] if oldest_unmarked_row and oldest_unmarked_row[0] else None
            
            if oldest_id is None:
                # No hay specials sin marca, mostrar todos los del Lead Supervisor
                sql = """
                    SELECT 
                        s.ID_special,
                        s.FechaHora,
                        s.ID_Sitio,
                        s.Nombre_Actividad,
                        s.Cantidad,
                        s.Camera,
                        s.Descripcion,
                        s.Usuario,
                        s.Time_Zone,
                        s.marked_status,
                        s.marked_by
                    FROM specials s
                    WHERE s.Supervisor = %s
                    ORDER BY s.FechaHora DESC
                """
                cursor.execute(sql, (username,))
            else:
                # Mostrar desde el ID más antiguo sin marca hasta el más reciente
                sql = """
                    SELECT 
                        s.ID_special,
                        s.FechaHora,
                        s.ID_Sitio,
                        s.Nombre_Actividad,
                        s.Cantidad,
                        s.Camera,
                        s.Descripcion,
                        s.Usuario,
                        s.Time_Zone,
                        s.marked_status,
                        s.marked_by
                    FROM specials s
                    WHERE s.Supervisor = %s
                      AND s.ID_special >= %s
                    ORDER BY s.FechaHora DESC
                """
                cursor.execute(sql, (username, oldest_id))
            
            rows = cursor.fetchall()
            
            # Formatear datos
            data = []
            row_ids.clear()
            row_status = []  # Para almacenar el estado de marca de cada fila
            
            for row in rows:
                row_ids.append(row[0])  # ID_special
                row_status.append(row[9])  # marked_status (para coloreo)
                
                # Resolver nombre de sitio si es ID numérico
                sitio_display = ""
                if row[2]:  # ID_Sitio
                    try:
                        cursor.execute("SELECT Nombre_Sitio FROM Sitios WHERE ID_Sitio = %s", (row[2],))
                        sitio_row = cursor.fetchone()
                        if sitio_row:
                            sitio_display = f"{row[2]} {sitio_row[0]}"
                        else:
                            sitio_display = str(row[2])
                    except Exception:
                        sitio_display = str(row[2]) if row[2] else ""
                
                # Determinar estado de marca
                marca_status = "Sin Marca"
                if row[9]:  # marked_status
                    if row[9] == 'done':
                        marca_status = "✅ Registrado"
                    elif row[9] == 'flagged':
                        marca_status = "🔄 En Progreso"
                    else:
                        marca_status = str(row[9])
                
                # ⭐ Mostrar quién marcó el evento (marked_by)
                marked_by_display = ""
                if row[10]:  # marked_by (quien lo marcó)
                    marked_by_display = str(row[10])
                else:
                    marked_by_display = "Sin Marcar"
                
                formatted_row = [
                    str(row[1]) if row[1] else "",  #  
                    sitio_display,  # Sitio (resuelto)
                    str(row[3]) if row[3] else "",  # Actividad
                    str(row[4]) if row[4] else "",  # Cantidad
                    str(row[5]) if row[5] else "",  # Camera
                    str(row[6]) if row[6] else "",  # Descripcion
                    str(row[7]) if row[7] else "",  # Usuario
                    str(row[8]) if row[8] else "",  # Time_Zone
                    marca_status,  # Marca (procesada)
                    marked_by_display  # ⭐ NUEVO: Quién marcó el evento
                ]
                data.append(formatted_row)
            
            row_data_cache.clear()
            # Actualizar tksheet
            sheet.set_sheet_data(data if data else [["No hay specials asignados"] + [""] * (len(columns)-1)])
            
            # Aplicar anchos personalizados
            for col_idx, col_name in enumerate(columns):
                if col_name in custom_widths:
                    sheet.column_width(column=col_idx, width=custom_widths[col_name])
            
            # ⭐ CRÍTICO: Limpiar TODOS los colores antes de aplicar nuevos
            sheet.dehighlight_all()
            
            # Aplicar coloreo de filas según marked_status
            # Solo colorear filas que tienen marca, las nuevas (sin marca) quedan sin color
            for row_idx, status in enumerate(row_status):
                if status == 'done':
                    # Verde para registrado
                    sheet.highlight_rows(rows=[row_idx], bg="#00c853", fg="#111111", redraw=False)
                elif status == 'flagged':
                    # Ámbar/Naranja para en progreso
                    sheet.highlight_rows(rows=[row_idx], bg="#f5a623", fg="#111111", redraw=False)
                # Sin marca (None o NULL) = color por defecto del tema (no aplicar highlight)
            
            sheet.refresh()  # Refrescar una sola vez al final
            
            cursor.close()
            conn.close()
            
            print(f"[INFO] Cargados {len(data)} specials para Lead Supervisor {username}")
            
            print(f"[INFO] Cargados {len(data)} specials para Lead Supervisor {username}")
            
        except Exception as e:
            print(f"[ERROR] load_data: {e}")
            traceback.print_exc()
            messagebox.showerror("Error", f"Error al cargar datos:\n{e}", parent=top)

    def delete_selected():
        """Elimina los specials seleccionados (con permisos de Lead Supervisor) usando safe_delete"""
        try:
            selected = sheet.get_selected_rows()
            if not selected:
                messagebox.showwarning("Advertencia", "Selecciona al menos una fila para eliminar", parent=top)
                return
            
            # Confirmar eliminación
            count = len(selected)
            confirm = messagebox.askyesno(
                "Confirmar Eliminación",
                f"¿Mover {count} special(s) a la papelera?\n\n💡 Podrán ser recuperados desde el sistema de auditoría.",
                parent=top
            )
            
            if not confirm:
                return
            
            deleted_count = 0
            failed_count = 0
            
            for row_idx in selected:
                if row_idx < len(row_ids):
                    special_id = row_ids[row_idx]
                    try:
                        # ⭐ Usar safe_delete para mover a papelera
                        success = safe_delete(
                            table_name="specials",
                            pk_column="ID_special",
                            pk_value=special_id,
                            deleted_by=username,
                            reason=f"Eliminado por Lead Supervisor desde 'Todos los eventos'"
                        )
                        
                        if success:
                            deleted_count += 1
                        else:
                            failed_count += 1
                            print(f"[WARN] No se pudo mover special {special_id} a papelera")
                            
                    except Exception as e:
                        failed_count += 1
                        print(f"[ERROR] Error al eliminar special {special_id}: {e}")
            
            # Mostrar resultado
            if deleted_count > 0:
                if failed_count > 0:
                    messagebox.showinfo("Éxito", 
                                       f"✅ {deleted_count} special(s) movido(s) a papelera correctamente", 
                                       parent=top)
            else:
                messagebox.showerror("Error", "No se pudo eliminar ningún registro", parent=top)
            
            load_data()
            
        except Exception as e:
            print(f"[ERROR] delete_selected: {e}")
            traceback.print_exc()
            messagebox.showerror("Error", f"Error al eliminar:\n{e}", parent=top)

    # ==================== UI COMPONENTS ====================
    
    # ⭐ FUNCIÓN: Manejar Start/End Shift
    def handle_shift_button():
        """Maneja el click en el botón Start/End Shift"""
        try:
            is_start = Dinamic_button_Shift(username)
            
            if is_start:
                success = on_start_shift(username, parent_window=top)
                if success:
                    update_shift_button()
                    load_data()
            else:
                on_end_shift(username)
                update_shift_button()
                load_data()
            
        except Exception as e:
            messagebox.showerror("Error", f"Error al cambiar turno:\n{e}", parent=top)
            print(f"[ERROR] handle_shift_button: {e}")
            traceback.print_exc()
    
    def update_shift_button():
        """Actualiza el texto y color del botón según el estado del turno"""
        try:
            is_start = Dinamic_button_Shift(username)
            
            if is_start:
                if UI is not None:
                    shift_btn.configure(text="🚀 Start Shift", 
                                       fg_color="#00c853", 
                                       hover_color="#00a043")
                else:
                    shift_btn.configure(text="🚀 Start Shift", bg="#00c853")
            else:
                if UI is not None:
                    shift_btn.configure(text="🏁 End of Shift", 
                                       fg_color="#d32f2f", 
                                       hover_color="#b71c1c")
                else:
                    shift_btn.configure(text="🏁 End of Shift", bg="#d32f2f")
        except Exception as e:
            print(f"[ERROR] update_shift_button: {e}")
    
    # Header
    if UI is not None:
        header = UI.CTkFrame(top, fg_color="#23272a", corner_radius=0)
    else:
        header = tk.Frame(top, bg="#23272a")
    header.pack(fill="x", padx=0, pady=0)

    if UI is not None:
        UI.CTkLabel(header, text=f"👔 Lead Supervisor: {username}", 
                   font=("Segoe UI", 16, "bold"), 
                   text_color="#e0e0e0").pack(side="left", padx=20, pady=15)
        
        # ⭐ INDICADOR DE STATUS CON DROPDOWN (a la derecha, antes del botón Shift)
        status_frame = UI.CTkFrame(header, fg_color="transparent")
        status_frame.pack(side="right", padx=(5, 10), pady=15)
        
        # Obtener status actual del usuario
        current_status_bd = get_user_status_bd(username)
        
        # Mapear el status a texto legible
        if current_status_bd == 0:
            status_text = "🟢 Disponible"
        elif current_status_bd == 1 :
            status_text = "🟡 Ocupado"
        elif current_status_bd == -1:
            status_text = "🔴 No disponible"
        else:
            status_text = "⚪ Desconocido"
        
        status_label = UI.CTkLabel(status_frame, text=status_text, 
                                   font=("Segoe UI", 12, "bold"))
        status_label.pack(side="left", padx=(0, 8))
        
        btn_emoji_green = "🟢"
        btn_emoji_yellow = "🟡"
        btn_emoji_red = "🔴"
        
        def update_status_label(new_value):
            """Actualiza el label y el status en la BD"""
            under_super.set_new_status(new_value, username)
            # Actualizar el texto del label
            if new_value == 1:
                status_label.configure(text="🟢 Disponible")
            elif new_value == 2:
                status_label.configure(text="🟡 Ocupado")
            elif new_value == -1:
                status_label.configure(text="🔴 No disponible")
        
        status_btn_green = UI.CTkButton(status_frame, text=btn_emoji_green, command=lambda:(update_status_label(1), username),
                    fg_color="#00c853", hover_color="#00a043",
                    width=45, height=38,
                    font=("Segoe UI", 16, "bold"))
        status_btn_green.pack(side="left")    

        status_btn_yellow = UI.CTkButton(status_frame, text=btn_emoji_yellow, command=lambda: (update_status_label(2), username),
                    fg_color="#f5a623", hover_color="#e69515",
                    width=45, height=38,
                    font=("Segoe UI", 16, "bold"))
        status_btn_yellow.pack(side="left")

        status_btn_red = UI.CTkButton(status_frame, text=btn_emoji_red, command=lambda: (update_status_label(-1), username),
                    fg_color="#d32f2f", hover_color="#b71c1c",
                    width=45, height=38,
                    font=("Segoe UI", 16, "bold"))
        status_btn_red.pack(side="left")
        
        # ⭐ Botón Start/End Shift a la derecha
        shift_btn = UI.CTkButton(
            header, 
            text="🚀 Start Shift",
            command=handle_shift_button,
            width=160, 
            height=40,
            font=("Segoe UI", 14, "bold"),
            fg_color="#00c853",
            hover_color="#00a043"
        )
        shift_btn.pack(side="right", padx=(5, 20), pady=15)
        
        # Botones de acción
        UI.CTkButton(header, text="🔄 Refrescar", command=load_data,
                    fg_color="#4D6068", hover_color="#27a3e0", 
                    width=120, height=40,
                    font=("Segoe UI", 12, "bold")).pack(side="right", padx=5, pady=15)
        
        UI.CTkButton(header, text="🗑️ Eliminar", command=delete_selected,
                    fg_color="#d32f2f", hover_color="#b71c1c", 
                    width=120, height=40,
                    font=("Segoe UI", 12, "bold")).pack(side="right", padx=5, pady=15)
    else:
        tk.Label(header, text=f"👔 Lead Supervisor: {username}", 
                bg="#23272a", fg="#e0e0e0",
                font=("Segoe UI", 16, "bold")).pack(side="left", padx=20, pady=15)
        
        # ⭐ Botón Start/End Shift (Tkinter fallback)
        shift_btn = tk.Button(
            header,
            text="� Start Shift",
            command=handle_shift_button,
            bg="#00c853",
            fg="white",
            font=("Segoe UI", 12, "bold"),
            relief="flat",
            width=15
        )
        shift_btn.pack(side="right", padx=(5, 20), pady=15)
        
        tk.Button(header, text="�🔄 Refrescar", command=load_data,
                 bg="#666666", fg="white",
                 font=("Segoe UI", 12, "bold"), relief="flat",
                 width=12).pack(side="right", padx=5, pady=15)
        
        tk.Button(header, text="🗑️ Eliminar", command=delete_selected,
                 bg="#d32f2f", fg="white",
                 font=("Segoe UI", 12, "bold"), relief="flat",
                 width=12).pack(side="right", padx=5, pady=15)
    
    # Actualizar botón al iniciar
    update_shift_button()

    # Separador
    try:
        ttk.Separator(top, orient="horizontal").pack(fill="x")
    except Exception:
        pass

    # ==================== BARRA DE NAVEGACIÓN TIPO TABS ====================
    current_view = {'value': 'all_events'}  # 'all_events', 'unassigned_specials', 'audit', 'cover_time', 'admin'
    
    if UI is not None:
        nav_frame = UI.CTkFrame(top, fg_color="#23272a", corner_radius=0, height=50)
    else:
        nav_frame = tk.Frame(top, bg="#23272a", height=50)
    nav_frame.pack(fill="x", padx=0, pady=0)
    nav_frame.pack_propagate(False)

    def switch_view(new_view):
        """Cambia entre las 8 vistas disponibles"""
        current_view['value'] = new_view
        
        # Ocultar todos los containers
        main_container.pack_forget()
        unassigned_container.pack_forget()
        audit_container.pack_forget()
        cover_container.pack_forget()
        admin_container.pack_forget()
        rol_cover_container.pack_forget()
        breaks_container.pack_forget()
        news_container.pack_forget()
        
        # Resetear colores de botones
        inactive_color = "#3b4754"
        inactive_hover = "#4a5560"
        active_color = "#4a90e2"
        active_hover = "#357ABD"
        # Mostrar container activo y resaltar botón
        if new_view == 'all_events':
            main_container.pack(fill="both", expand=True, padx=10, pady=10)
            if UI is not None:
                btn_all_events.configure(fg_color=active_color, hover_color=active_hover)
            else:
                btn_all_events.configure(bg=active_color, activebackground=active_hover)
            # Forzar actualización del sheet para evitar desalineamiento
            top.update_idletasks()
            sheet.refresh()
            load_data()
        elif new_view == 'unassigned_specials':
            unassigned_container.pack(fill="both", expand=True, padx=10, pady=10)
            if UI is not None:
                btn_unassigned.configure(fg_color=active_color, hover_color=active_hover)
            else:
                btn_unassigned.configure(bg=active_color, activebackground=active_hover)
            # Forzar actualización del sheet para evitar desalineamiento
            top.update_idletasks()
            unassigned_sheet.refresh()
            load_unassigned_specials()
        elif new_view == 'audit':
            audit_container.pack(fill="both", expand=True, padx=10, pady=10)
            if UI is not None:
                btn_audit.configure(fg_color=active_color, hover_color=active_hover)
            else:
                btn_audit.configure(bg=active_color, activebackground=active_hover)
            # Forzar actualización del sheet para evitar desalineamiento
            top.update_idletasks()
            audit_sheet.refresh()
            # No auto-cargar audit, usuario debe usar filtros
        elif new_view == 'cover_time':
            cover_container.pack(fill="both", expand=True, padx=10, pady=10)
            if UI is not None:
                btn_cover.configure(fg_color=active_color, hover_color=active_hover)
            else:
                btn_cover.configure(bg=active_color, activebackground=active_hover)
            # Forzar actualización del sheet para evitar desalineamiento
            top.update_idletasks()
            cover_sheet.refresh()
            # No auto-cargar cover time, usuario debe usar filtros
        elif new_view == 'admin':
            admin_container.pack(fill="both", expand=True, padx=10, pady=10)
            if UI is not None:
                btn_admin.configure(fg_color=active_color, hover_color=active_hover)
            else:
                btn_admin.configure(bg=active_color, activebackground=active_hover)
            # Forzar actualización
            top.update_idletasks()
            # No auto-cargar, el usuario selecciona qué tabla ver
        elif new_view == 'rol_cover':
            rol_cover_container.pack(fill="both", expand=True, padx=10, pady=10)
            if UI is not None:
                btn_rol_cover.configure(fg_color=active_color, hover_color=active_hover)
            else:
                btn_rol_cover.configure(bg=active_color, activebackground=active_hover)
            # Cargar operadores al mostrar la vista
            top.update_idletasks()
            cargar_operadores_rol()
        elif new_view == 'breaks':
            breaks_container.pack(fill="both", expand=True, padx=10, pady=10)
            if UI is not None:
                btn_breaks.configure(fg_color=active_color, hover_color=active_hover)
            else:
                btn_breaks.configure(bg=active_color, activebackground=active_hover)
            # Forzar actualización y refrescar tabla de breaks
            top.update_idletasks()
            if USE_SHEET:
                breaks_sheet.refresh()
                refrescar_tabla_breaks()
        elif new_view == 'news':
            news_container.pack(fill="both", expand=True, padx=10, pady=10)
            if UI is not None:
                btn_news.configure(fg_color=active_color, hover_color=active_hover)
            else:
                btn_news.configure(bg=active_color, activebackground=active_hover)
            top.update_idletasks()

    # Botones de navegación
    if UI is not None:
        btn_all_events = UI.CTkButton(
            nav_frame, 
            text="📊 Todos los Eventos", 
            command=lambda: switch_view('all_events'),
            fg_color="#4a90e2",
            hover_color="#357ABD",
            width=150,
            height=35,
            font=("Segoe UI", 12, "bold")
        )
        btn_all_events.pack(side="left", padx=(20, 5), pady=8)
        
        btn_unassigned = UI.CTkButton(
            nav_frame, 
            text="⚠️ Specials Sin Marcar", 
            command=lambda: switch_view('unassigned_specials'),
            fg_color="#3b4754",
            hover_color="#4a5560",
            width=180,
            height=35,
            font=("Segoe UI", 12, "bold")
        )
        btn_unassigned.pack(side="left", padx=5, pady=8)
        
        btn_audit = UI.CTkButton(
            nav_frame, 
            text="📋 Audit", 
            command=lambda: switch_view('audit'),
            fg_color="#3b4754",
            hover_color="#4a5560",
            width=120,
            height=35,
            font=("Segoe UI", 12, "bold")
        )
        btn_audit.pack(side="left", padx=5, pady=8)
        
        btn_cover = UI.CTkButton(
            nav_frame, 
            text="⏰ Cover Time", 
            command=lambda: switch_view('cover_time'),
            fg_color="#3b4754",
            hover_color="#4a5560",
            width=140,
            height=35,
            font=("Segoe UI", 12, "bold")
        )
        btn_cover.pack(side="left", padx=5, pady=8)
        
        btn_admin = UI.CTkButton(
            nav_frame, 
            text="🔧 Admin", 
            command=lambda: switch_view('admin'),
            fg_color="#3b4754",
            hover_color="#4a5560",
            width=120,
            height=35,
            font=("Segoe UI", 12, "bold")
        )
        btn_admin.pack(side="left", padx=5, pady=8)
        
        btn_rol_cover = UI.CTkButton(
            nav_frame, 
            text="🎭 Rol de Cover", 
            command=lambda: switch_view('rol_cover'),
            fg_color="#3b4754",
            hover_color="#4a5560",
            width=140,
            height=35,
            font=("Segoe UI", 12, "bold")
        )
        btn_rol_cover.pack(side="left", padx=5, pady=8)
        
        btn_breaks = UI.CTkButton(
            nav_frame, 
            text="☕ Breaks", 
            command=lambda: switch_view('breaks'),
            fg_color="#3b4754",
            hover_color="#4a5560",
            width=120,
            height=35,
            font=("Segoe UI", 12, "bold")
        )
        btn_breaks.pack(side="left", padx=5, pady=8)
        
        btn_news = UI.CTkButton(
            nav_frame, 
            text="📰 News", 
            command=lambda: switch_view('news'),
            fg_color="#3b4754",
            hover_color="#4a5560",
            width=120,
            height=35,
            font=("Segoe UI", 12, "bold")
        )
        btn_news.pack(side="left", padx=5, pady=8)
    else:
        btn_all_events = tk.Button(
            nav_frame,
            text="📊 Todos los Eventos",
            command=lambda: switch_view('all_events'),
            bg="#4a90e2",
            fg="white",
            activebackground="#357ABD",
            font=("Segoe UI", 12, "bold"),
            relief="flat",
            width=17
        )
        btn_all_events.pack(side="left", padx=(20, 5), pady=8)
        
        btn_unassigned = tk.Button(
            nav_frame,
            text="⚠️ Specials Sin Marcar",
            command=lambda: switch_view('unassigned_specials'),
            bg="#3b4754",
            fg="white",
            activebackground="#4a5560",
            font=("Segoe UI", 12, "bold"),
            relief="flat",
            width=20
        )
        btn_unassigned.pack(side="left", padx=5, pady=8)
        
        btn_audit = tk.Button(
            nav_frame,
            text="📋 Audit",
            command=lambda: switch_view('audit'),
            bg="#3b4754",
            fg="white",
            activebackground="#4a5560",
            font=("Segoe UI", 12, "bold"),
            relief="flat",
            width=12
        )
        btn_audit.pack(side="left", padx=5, pady=8)
        
        btn_cover = tk.Button(
            nav_frame,
            text="⏰ Cover Time",
            command=lambda: switch_view('cover_time'),
            bg="#3b4754",
            fg="white",
            activebackground="#4a5560",
            font=("Segoe UI", 12, "bold"),
            relief="flat",
            width=15
        )
        btn_cover.pack(side="left", padx=5, pady=8)
        
        btn_admin = tk.Button(
            nav_frame,
            text="🔧 Admin",
            command=lambda: switch_view('admin'),
            bg="#3b4754",
            fg="white",
            activebackground="#4a5560",
            font=("Segoe UI", 12, "bold"),
            relief="flat",
            width=12
        )
        btn_admin.pack(side="left", padx=5, pady=8)
        
        btn_rol_cover = tk.Button(
            nav_frame,
            text="🎭 Rol de Cover",
            command=lambda: switch_view('rol_cover'),
            bg="#3b4754",
            fg="white",
            activebackground="#4a5560",
            font=("Segoe UI", 12, "bold"),
            relief="flat",
            width=15
        )
        btn_rol_cover.pack(side="left", padx=5, pady=8)
        
        btn_breaks = tk.Button(
            nav_frame,
            text="☕ Breaks",
            command=lambda: switch_view('breaks'),
            bg="#3b4754",
            fg="white",
            activebackground="#4a5560",
            font=("Segoe UI", 12, "bold"),
            relief="flat",
            width=12
        )
        btn_breaks.pack(side="left", padx=5, pady=8)
        
        btn_news = tk.Button(
            nav_frame,
            text="📰 News",
            command=lambda: switch_view('news'),
            bg="#3b4754",
            fg="white",
            activebackground="#4a5560",
            font=("Segoe UI", 12, "bold"),
            relief="flat",
            width=12
        )
        btn_news.pack(side="left", padx=5, pady=8)
        btn_cover.pack(side="left", padx=5, pady=8)
        
        btn_admin = tk.Button(
            nav_frame,
            text="🔧 Admin",
            command=lambda: switch_view('admin'),
            bg="#3b4754",
            fg="white",
            activebackground="#4a5560",
            font=("Segoe UI", 12, "bold"),
            relief="flat",
            width=12
        )
        btn_admin.pack(side="left", padx=5, pady=8)
        
        btn_rol_cover = tk.Button(
            nav_frame,
            text="🎭 Rol de Cover",
            command=lambda: switch_view('rol_cover'),
            bg="#3b4754",
            fg="white",
            activebackground="#4a5560",
            font=("Segoe UI", 12, "bold"),
            relief="flat",
            width=15
        )
        btn_rol_cover.pack(side="left", padx=5, pady=8)

    # Separador después de navegación
    try:
        ttk.Separator(top, orient="horizontal").pack(fill="x")
    except Exception:
        pass

    # Container principal (todos los eventos)
    if UI is not None:
        main_container = UI.CTkFrame(top, fg_color="#2c2f33")
    else:
        main_container = tk.Frame(top, bg="#2c2f33")
    # No hacer pack aquí, se hace en switch_view()
    
    # Frame para el sheet dentro del main_container
    if UI is not None:
        sheet_frame = UI.CTkFrame(main_container, fg_color="#2c2f33")
    else:
        sheet_frame = tk.Frame(main_container, bg="#2c2f33")
    sheet_frame.pack(fill="both", expand=True)

    # Crear tksheet para eventos
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
        empty_vertical=0,
        auto_resize_columns=False,
        auto_resize_rows=False
    )
    # Deshabilitar menú contextual - solo permitir selección y navegación
    sheet.enable_bindings([
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
    sheet.pack(fill="both", expand=True)

    # Aplicar anchos iniciales
    for col_idx, col_name in enumerate(columns):
        if col_name in custom_widths:
            sheet.column_width(column=col_idx, width=custom_widths[col_name])

    # ==================== TOOLBAR DE MARCAS (Para "Todos los Eventos") ====================
    
    if UI is not None:
        marks_toolbar = UI.CTkFrame(main_container, fg_color="#23272a", corner_radius=0, height=60)
    else:
        marks_toolbar = tk.Frame(main_container, bg="#23272a", height=60)
    marks_toolbar.pack(fill="x", side="bottom", padx=0, pady=0)
    marks_toolbar.pack_propagate(False)
    
    def mark_selected_as_done():
        """Marca los eventos seleccionados como 'Registrado'"""
        try:
            selected = sheet.get_selected_rows()
            if not selected:
                messagebox.showwarning("Advertencia", "Selecciona al menos un evento para marcar", parent=top)
                return
            
            conn = get_connection()
            cursor = conn.cursor()
            
            marked_count = 0
            for row_idx in selected:
                if row_idx < len(row_ids):
                    event_id = row_ids[row_idx]
                    try:
                        # Marcar en tabla specials (si existe)
                        cursor.execute("""
                            UPDATE specials 
                            SET marked_status = 'done', marked_at = NOW(), marked_by = %s
                            WHERE ID_special = %s
                        """, (username, event_id))
                        marked_count += cursor.rowcount
                    except Exception as e:
                        print(f"[WARNING] No se pudo marcar evento {event_id}: {e}")
            
            conn.commit()
            cursor.close()
            conn.close()
            
            if marked_count > 0:
                load_data()
            else:
                messagebox.showinfo("Info", "Los eventos seleccionados no están en la tabla specials", parent=top)
            
        except Exception as e:
            print(f"[ERROR] mark_selected_as_done: {e}")
            traceback.print_exc()
            messagebox.showerror("Error", f"Error al marcar:\n{e}", parent=top)
    
    def mark_selected_as_progress():
        """Marca los eventos seleccionados como 'En Progreso'"""
        try:
            selected = sheet.get_selected_rows()
            if not selected:
                messagebox.showwarning("Advertencia", "Selecciona al menos un evento para marcar", parent=top)
                return
            
            conn = get_connection()
            cursor = conn.cursor()
            
            marked_count = 0
            for row_idx in selected:
                if row_idx < len(row_ids):
                    event_id = row_ids[row_idx]
                    try:
                        # Marcar en tabla specials (si existe)
                        cursor.execute("""
                            UPDATE specials 
                            SET marked_status = 'flagged', marked_at = NOW(), marked_by = %s
                            WHERE ID_special = %s
                        """, (username, event_id))
                        marked_count += cursor.rowcount
                    except Exception as e:
                        print(f"[WARNING] No se pudo marcar evento {event_id}: {e}")
            
            conn.commit()
            cursor.close()
            conn.close()
            
            if marked_count > 0:
                load_data()
            else:
                messagebox.showinfo("Info", "Los eventos seleccionados no están en la tabla specials", parent=top)
            
        except Exception as e:
            print(f"[ERROR] mark_selected_as_progress: {e}")
            traceback.print_exc()
            messagebox.showerror("Error", f"Error al marcar:\n{e}", parent=top)
    
    # Botones del toolbar de marcas
    if UI is not None:
        UI.CTkButton(marks_toolbar, text="✅ Marcar como Registrado", 
                    command=mark_selected_as_done,
                    fg_color="#00c853", hover_color="#00a043",
                    width=180, height=40, font=("Segoe UI", 11, "bold")).pack(side="left", padx=(20, 10), pady=10)
        
        UI.CTkButton(marks_toolbar, text="🔄 Marcar como En Progreso", 
                    command=mark_selected_as_progress,
                    fg_color="#ff9800", hover_color="#f57c00",
                    width=200, height=40, font=("Segoe UI", 11, "bold")).pack(side="left", padx=10, pady=10)
    else:
        tk.Button(marks_toolbar, text="✅ Marcar como Registrado", 
                 command=mark_selected_as_done,
                 bg="#00c853", fg="white", font=("Segoe UI", 11, "bold"),
                 relief="flat", width=20).pack(side="left", padx=(20, 10), pady=10)
        
        tk.Button(marks_toolbar, text="🔄 Marcar como En Progreso", 
                 command=mark_selected_as_progress,
                 bg="#ff9800", fg="white", font=("Segoe UI", 11, "bold"),
                 relief="flat", width=22).pack(side="left", padx=10, pady=10)

    # ==================== CONTAINER DE SPECIALS SIN ASIGNAR ====================
    
    if UI is not None:
        unassigned_container = UI.CTkFrame(top, fg_color="#2c2f33")
    else:
        unassigned_container = tk.Frame(top, bg="#2c2f33")
    # No hacer pack aquí, se hace en switch_view()
    
    # Columnas para specials (basado en tabla specials)
    columns_specials = ["ID", " ", "Sitio", "Actividad", "Cantidad", "Camera", "Descripcion", "Usuario", "TZ", "Supervisor"]
    custom_widths_specials = {
        "ID": 60,
        " ": 150,
        "Sitio": 220,
        "Actividad": 150,
        "Cantidad": 70,
        "Camera": 80,
        "Descripcion": 190,
        "Usuario": 100,
        "TZ": 90,
        "Supervisor": 150
    }
    
    # Variables para specials sin asignar
    unassigned_row_ids = []
    unassigned_row_cache = []
    
    def load_unassigned_specials():
        """Carga specials sin marcar (marked_status vacío) desde el último START SHIFT"""
        try:
            conn = get_connection()
            cursor = conn.cursor()
            
            # Obtener el último START SHIFT del Lead Supervisor
            cursor.execute("""
                SELECT e.FechaHora 
                FROM Eventos e
                INNER JOIN user u ON e.ID_Usuario = u.ID_Usuario
                WHERE u.Nombre_Usuario = %s AND e.Nombre_Actividad = 'START SHIFT'
                ORDER BY e.FechaHora DESC
                LIMIT 1
            """, (username,))
            result = cursor.fetchone()
            
            if not result:
                print(f"[INFO] No hay turno activo para {username}")
                unassigned_sheet.set_sheet_data([["No hay shift activo"] + [""] * (len(columns_specials)-1)])
                unassigned_row_ids.clear()
                unassigned_row_cache.clear()
                cursor.close()
                conn.close()
                return
            
            fecha_inicio = result[0]
            
            # Query: Specials sin marcar (marked_status IS NULL o vacío)
            # Estos son specials que aún NO han sido revisados/marcados por ningún supervisor
            sql = """
                SELECT 
                    s.ID_special,
                    s.FechaHora,
                    s.ID_Sitio,
                    s.Nombre_Actividad,
                    s.Cantidad,
                    s.Camera,
                    s.Descripcion,
                    s.Usuario,
                    s.Time_Zone,
                    s.Supervisor
                FROM specials s
                WHERE (s.marked_status IS NULL OR s.marked_status = '')
                  AND s.FechaHora >= %s
                ORDER BY s.FechaHora ASC
            """
            
            cursor.execute(sql, (fecha_inicio,))
            rows = cursor.fetchall()
            
            # Formatear datos
            data = []
            unassigned_row_ids.clear()
            for row in rows:
                unassigned_row_ids.append(row[0])  # ID_special
                
                # Resolver nombre de sitio si es ID
                sitio_display = ""
                if row[2]:  # ID_Sitio
                    try:
                        cursor.execute("SELECT Nombre_Sitio FROM Sitios WHERE ID_Sitio = %s", (row[2],))
                        sitio_row = cursor.fetchone()
                        if sitio_row:
                            sitio_display = f"{row[2]} {sitio_row[0]}"
                        else:
                            sitio_display = str(row[2])
                    except Exception:
                        sitio_display = str(row[2]) if row[2] else ""
                
                formatted_row = [
                    str(row[0]),  # ID
                    str(row[1]) if row[1] else "",  #  
                    sitio_display,  # Sitio
                    str(row[3]) if row[3] else "",  # Actividad
                    str(row[4]) if row[4] else "",  # Cantidad
                    str(row[5]) if row[5] else "",  # Camera
                    str(row[6]) if row[6] else "",  # Descripcion
                    str(row[7]) if row[7] else "",  # Usuario
                    str(row[8]) if row[8] else "",  # TZ
                    str(row[9]) if row[9] else "Sin Asignar"  # Supervisor
                ]
                data.append(formatted_row)
            
            unassigned_row_cache.clear()
            unassigned_row_cache.extend(data)
            
            # Actualizar tksheet
            unassigned_sheet.set_sheet_data(data if data else [["No hay specials sin asignar"] + [""] * (len(columns_specials)-1)])
            
            # Aplicar anchos personalizados
            for col_idx, col_name in enumerate(columns_specials):
                if col_name in custom_widths_specials:
                    unassigned_sheet.column_width(column=col_idx, width=custom_widths_specials[col_name])
            
            cursor.close()
            conn.close()
            
            print(f"[INFO] Cargados {len(data)} specials sin asignar")
            
        except Exception as e:
            print(f"[ERROR] load_unassigned_specials: {e}")
            traceback.print_exc()
            messagebox.showerror("Error", f"Error al cargar specials sin asignar:\n{e}", parent=top)
    
    def assign_supervisor_to_selected():
        """Abre ventana para asignar supervisor a los specials seleccionados"""
        try:
            selected = unassigned_sheet.get_selected_rows()
            if not selected:
                messagebox.showwarning("Advertencia", "Selecciona al menos un special para asignar", parent=top)
                return
            
            # Ventana modal para seleccionar supervisor (reutilización de accion_supervisores)
            if UI is not None:
                assign_win = UI.CTkToplevel(top)
                try:
                    assign_win.configure(fg_color="#2c2f33")
                except Exception:
                    pass
            else:
                assign_win = tk.Toplevel(top)
                assign_win.configure(bg="#2c2f33")
            
            assign_win.title("Asignar Supervisor")
            assign_win.geometry("400x250")
            assign_win.resizable(False, False)
            assign_win.transient(top)
            assign_win.grab_set()
            
            if UI is not None:
                UI.CTkLabel(assign_win, text="Selecciona un Supervisor:", 
                           text_color="#00bfae", 
                           font=("Segoe UI", 16, "bold")).pack(pady=(20, 10))
                container = UI.CTkFrame(assign_win, fg_color="#2c2f33")
                container.pack(fill="both", expand=True, padx=20, pady=(0, 15))
            else:
                tk.Label(assign_win, text="Selecciona un Supervisor:", 
                        bg="#2c2f33", fg="#00bfae", 
                        font=("Segoe UI", 14, "bold")).pack(pady=(20, 10))
                container = tk.Frame(assign_win, bg="#2c2f33")
                container.pack(fill="both", expand=True, padx=20, pady=(0, 15))
            
            # Consultar supervisores disponibles
            supervisores = []
            try:
                conn = get_connection()
                cur = conn.cursor()
                # Buscar usuarios con rol "Supervisor" o "Lead Supervisor"
                cur.execute("SELECT Nombre_Usuario FROM user WHERE Rol IN ('Supervisor', 'Lead Supervisor')")
                supervisores = [row[0] for row in cur.fetchall()]
                cur.close()
                conn.close()
            except Exception as e:
                print(f"[ERROR] Error al consultar supervisores: {e}")
            
            sup_var = tk.StringVar()
            if UI is not None:
                if not supervisores:
                    supervisores = ["No hay supervisores disponibles"]
                opt = UI.CTkOptionMenu(container, variable=sup_var, values=supervisores, 
                                      fg_color="#262a31", button_color="#14414e", 
                                      text_color="#00bfae",
                                      font=("Segoe UI", 13))
                if supervisores and supervisores[0] != "No hay supervisores disponibles":
                    sup_var.set(supervisores[0])
                opt.pack(fill="x", padx=10, pady=10)
            else:
                yscroll_sup = tk.Scrollbar(container, orient="vertical")
                yscroll_sup.pack(side="right", fill="y")
                sup_listbox = tk.Listbox(container, height=8, selectmode="browse", 
                                        bg="#262a31", fg="#00bfae", 
                                        font=("Segoe UI", 12), 
                                        yscrollcommand=yscroll_sup.set)
                sup_listbox.pack(side="left", fill="both", expand=True)
                yscroll_sup.config(command=sup_listbox.yview)
                if not supervisores:
                    sup_listbox.insert("end", "No hay supervisores disponibles")
                else:
                    for sup in supervisores:
                        sup_listbox.insert("end", sup)
            
            def confirm_assignment():
                try:
                    # Obtener supervisor seleccionado
                    if UI is not None:
                        supervisor_name = sup_var.get()
                    else:
                        sel_idx = sup_listbox.curselection()
                        if not sel_idx:
                            messagebox.showwarning("Sin selección", "Selecciona un supervisor", parent=assign_win)
                            return
                        supervisor_name = sup_listbox.get(sel_idx[0])
                    
                    if not supervisor_name or supervisor_name == "No hay supervisores disponibles":
                        messagebox.showwarning("Sin selección", "Selecciona un supervisor válido", parent=assign_win)
                        return
                    
                    # Actualizar base de datos
                    conn = get_connection()
                    cursor = conn.cursor()
                    
                    updated_count = 0
                    for row_idx in selected:
                        if row_idx < len(unassigned_row_ids):
                            special_id = unassigned_row_ids[row_idx]
                            try:
                                cursor.execute(
                                    "UPDATE specials SET Supervisor = %s WHERE ID_special = %s",
                                    (supervisor_name, special_id)
                                )
                                updated_count += 1
                            except Exception as e:
                                print(f"[ERROR] No se pudo asignar supervisor al special {special_id}: {e}")
                    
                    conn.commit()
                    cursor.close()
                    conn.close()
                    
                    assign_win.destroy()
                    load_unassigned_specials()  # Recargar lista
                    
                except Exception as e:
                    print(f"[ERROR] confirm_assignment: {e}")
                    traceback.print_exc()
                    messagebox.showerror("Error", f"Error al asignar supervisor:\n{e}", parent=assign_win)
            
            # Botones
            if UI is not None:
                btn_frame = UI.CTkFrame(assign_win, fg_color="#2c2f33")
                btn_frame.pack(fill="x", padx=20, pady=(0, 20))
                
                UI.CTkButton(btn_frame, text="✅ Asignar", 
                            command=confirm_assignment,
                            fg_color="#00c853", hover_color="#00a043",
                            font=("Segoe UI", 12, "bold"),
                            width=150).pack(side="left", padx=(0, 10))
                
                UI.CTkButton(btn_frame, text="❌ Cancelar", 
                            command=assign_win.destroy,
                            fg_color="#d32f2f", hover_color="#b71c1c",
                            font=("Segoe UI", 12, "bold"),
                            width=150).pack(side="right")
            else:
                btn_frame = tk.Frame(assign_win, bg="#2c2f33")
                btn_frame.pack(fill="x", padx=20, pady=(0, 20))
                
                tk.Button(btn_frame, text="✅ Asignar", 
                         command=confirm_assignment,
                         bg="#00c853", fg="white",
                         font=("Segoe UI", 12, "bold"),
                         width=15).pack(side="left", padx=(0, 10))
                
                tk.Button(btn_frame, text="❌ Cancelar", 
                         command=assign_win.destroy,
                         bg="#d32f2f", fg="white",
                         font=("Segoe UI", 12, "bold"),
                         width=15).pack(side="right")
            
        except Exception as e:
            print(f"[ERROR] assign_supervisor_to_selected: {e}")
            traceback.print_exc()
            messagebox.showerror("Error", f"Error al abrir ventana de asignación:\n{e}", parent=top)
    
    # Frame superior para botones de acción
    if UI is not None:
        unassigned_actions = UI.CTkFrame(unassigned_container, fg_color="#23272a", corner_radius=0, height=60)
    else:
        unassigned_actions = tk.Frame(unassigned_container, bg="#23272a", height=60)
    unassigned_actions.pack(fill="x", padx=0, pady=0)
    unassigned_actions.pack_propagate(False)
    
    if UI is not None:
        UI.CTkLabel(unassigned_actions, text="⚠️ Specials Sin Marcar (Pendientes de Revisión)", 
                   font=("Segoe UI", 14, "bold"), 
                   text_color="#ffa726").pack(side="left", padx=20, pady=15)
        
        UI.CTkButton(unassigned_actions, text="👤 Asignar Supervisor", 
                    command=assign_supervisor_to_selected,
                    fg_color="#00c853", hover_color="#00a043",
                    width=160, height=35,
                    font=("Segoe UI", 12, "bold")).pack(side="right", padx=(5, 20), pady=12)
        
        UI.CTkButton(unassigned_actions, text="🔄 Refrescar", 
                    command=load_unassigned_specials,
                    fg_color="#4D6068", hover_color="#27a3e0",
                    width=120, height=35,
                    font=("Segoe UI", 12, "bold")).pack(side="right", padx=5, pady=12)
    else:
        tk.Label(unassigned_actions, text="⚠️ Specials Sin Marcar (Pendientes de Revisión)", 
                bg="#23272a", fg="#ffa726",
                font=("Segoe UI", 14, "bold")).pack(side="left", padx=20, pady=15)
        
        tk.Button(unassigned_actions, text="👤 Asignar Supervisor", 
                 command=assign_supervisor_to_selected,
                 bg="#00c853", fg="white",
                 font=("Segoe UI", 12, "bold"),
                 width=18).pack(side="right", padx=(5, 20), pady=12)
        
        tk.Button(unassigned_actions, text="🔄 Refrescar", 
                 command=load_unassigned_specials,
                 bg="#666666", fg="white",
                 font=("Segoe UI", 12, "bold"),
                 width=12).pack(side="right", padx=5, pady=12)
    
    # Frame para tksheet de specials sin asignar
    if UI is not None:
        unassigned_sheet_frame = UI.CTkFrame(unassigned_container, fg_color="#2c2f33")
    else:
        unassigned_sheet_frame = tk.Frame(unassigned_container, bg="#2c2f33")
    unassigned_sheet_frame.pack(fill="both", expand=True, padx=0, pady=10)
    
    # Crear tksheet para specials sin asignar
    unassigned_sheet = SheetClass(
        unassigned_sheet_frame,
        headers=columns_specials,
        theme="dark blue",
        height=550,
        width=1350,
        show_selected_cells_border=True,
        show_row_index=True,
        show_top_left=False,
        empty_horizontal=0,
        empty_vertical=0,
        auto_resize_columns=False,
        auto_resize_rows=False
    )
    # ⭐ DESHABILITAR opciones de edición del menú contextual
    # Solo permitir: selección, redimensión, copiar y deshacer
    unassigned_sheet.enable_bindings([
        "single_select",
        "drag_select",
        "column_select",
        "row_select",
        "column_width_resize",
        "double_click_column_resize",
        "arrowkeys",
        "copy",
        "select_all"
    ])
    unassigned_sheet.pack(fill="both", expand=True)
    
    # Aplicar anchos iniciales para specials
    for col_idx, col_name in enumerate(columns_specials):
        if col_name in custom_widths_specials:
            unassigned_sheet.column_width(column=col_idx, width=custom_widths_specials[col_name])

    # ==================== CONTAINERS ADICIONALES: AUDIT Y COVER TIME ====================
    
    # ⭐ Importar tkcalendar para DateEntry (usado en Audit y Cover Time)
    try:
        import tkcalendar
    except ImportError:
        tkcalendar = None
    
    # ⭐ Configurar estilo oscuro para FilteredCombobox (ttk widgets)
    try:
        dark_combo_style = ttk.Style()
        dark_combo_style.theme_use('clam')  # Tema base compatible
        
        # Configurar estilo dark para combobox
        dark_combo_style.configure('Dark.TCombobox',
                                   fieldbackground='#2b2b2b',
                                   background='#2b2b2b',
                                   foreground='#ffffff',
                                   arrowcolor='#ffffff',
                                   bordercolor='#4a90e2',
                                   lightcolor='#2b2b2b',
                                   darkcolor='#2b2b2b',
                                   selectbackground='#4a90e2',
                                   selectforeground='#ffffff')
        
        dark_combo_style.map('Dark.TCombobox',
                            fieldbackground=[('readonly', '#2b2b2b'), ('disabled', '#1a1a1a')],
                            selectbackground=[('readonly', '#4a90e2')],
                            selectforeground=[('readonly', '#ffffff')],
                            foreground=[('readonly', '#ffffff'), ('disabled', '#666666')])
        
        # Configurar estilo para el listbox del dropdown
        top.option_add('*TCombobox*Listbox.background', '#2b2b2b')
        top.option_add('*TCombobox*Listbox.foreground', '#ffffff')
        top.option_add('*TCombobox*Listbox.selectBackground', '#4a90e2')
        top.option_add('*TCombobox*Listbox.selectForeground', '#ffffff')
    except Exception as e:
        print(f"[DEBUG] No se pudo configurar estilo dark para combobox: {e}")
    
    # ===== AUDIT CONTAINER =====
    if UI is not None:
        audit_container = UI.CTkFrame(top, fg_color="#2c2f33")
    else:
        audit_container = tk.Frame(top, bg="#2c2f33")
    # No hacer pack aquí, se hace en switch_view()
    
    # Filtros de Audit
    if UI is not None:
        audit_filters = UI.CTkFrame(audit_container, fg_color="#23272a", corner_radius=0, height=120)
    else:
        audit_filters = tk.Frame(audit_container, bg="#23272a", height=120)
    audit_filters.pack(fill="x", padx=0, pady=0)
    audit_filters.pack_propagate(False)
    
    # Variables de filtros
    audit_user_var = tk.StringVar()
    audit_site_var = tk.StringVar()
    audit_fecha_var = tk.StringVar()
    
    # Obtener usuarios y sitios de la BD
    try:
        conn_temp = get_connection()
        cur_temp = conn_temp.cursor()
        
        # Usuarios
        cur_temp.execute("SELECT Nombre_Usuario FROM user ORDER BY Nombre_Usuario")
        audit_users_list = ["Todos"] + [row[0] for row in cur_temp.fetchall()]
        
        cur_temp.close()
        conn_temp.close()
        
        # ⭐ Sitios con formato "Nombre (ID)" usando helper con cache
        audit_sites_raw = get_sites()
        audit_sites_list = ["Todos"] + audit_sites_raw
        
    except Exception as e:
        print(f"[ERROR] Error al cargar usuarios/sitios para audit: {e}")
        audit_users_list = ["Todos"]
        audit_sites_list = ["Todos"]
    
    # Labels y controles de filtros Audit
    if UI is not None:
        UI.CTkLabel(audit_filters, text="📋 Auditoría de Eventos", 
                   font=("Segoe UI", 14, "bold"), text_color="#e0e0e0").pack(side="top", padx=20, pady=(10, 5))
        
        filter_row1 = UI.CTkFrame(audit_filters, fg_color="transparent")
        filter_row1.pack(fill="x", padx=20, pady=5)
        
        UI.CTkLabel(filter_row1, text="Usuario:", text_color="#e0e0e0").pack(side="left", padx=5)
        audit_user_cb = under_super.FilteredCombobox(
            filter_row1, textvariable=audit_user_var, values=audit_users_list,
            font=("Segoe UI", 10), width=25,
            background='#2b2b2b', foreground='#ffffff', 
            bordercolor='#4a90e2', arrowcolor='#ffffff'
        )
        audit_user_cb.pack(side="left", padx=5)
        
        UI.CTkLabel(filter_row1, text="Sitio:", text_color="#e0e0e0").pack(side="left", padx=5)
        audit_site_cb = under_super.FilteredCombobox(
            filter_row1, textvariable=audit_site_var, values=audit_sites_list,
            font=("Segoe UI", 10), width=32,
            background='#2b2b2b', foreground='#ffffff',
            bordercolor='#4a90e2', arrowcolor='#ffffff'
        )
        audit_site_cb.pack(side="left", padx=5)
        
        UI.CTkLabel(filter_row1, text="Fecha:", text_color="#e0e0e0").pack(side="left", padx=(15, 5))
        # Frame contenedor para DateEntry (tkcalendar no es compatible directo con CTk)
        audit_fecha_frame = tk.Frame(filter_row1, bg="#23272a")
        audit_fecha_frame.pack(side="left", padx=5)
        if tkcalendar:
            audit_fecha_entry = tkcalendar.DateEntry(audit_fecha_frame, textvariable=audit_fecha_var,
                                                     width=13, background='#4a90e2', foreground='white',
                                                     borderwidth=2, date_pattern='yyyy-mm-dd',
                                                     font=("Segoe UI", 10))
            audit_fecha_entry.pack()
        else:
            audit_fecha_entry = tk.Entry(audit_fecha_frame, textvariable=audit_fecha_var, width=13,
                                        bg="#2b2b2b", fg="#ffffff", font=("Segoe UI", 10))
            audit_fecha_entry.pack()
        
        filter_row2 = UI.CTkFrame(audit_filters, fg_color="transparent")
        filter_row2.pack(fill="x", padx=20, pady=5)
    else:
        tk.Label(audit_filters, text="📋 Auditoría de Eventos", 
                bg="#23272a", fg="#e0e0e0", font=("Segoe UI", 14, "bold")).pack(side="top", padx=20, pady=(10, 5))
        
        filter_row1 = tk.Frame(audit_filters, bg="#23272a")
        filter_row1.pack(fill="x", padx=20, pady=5)
        
        tk.Label(filter_row1, text="Usuario:", bg="#23272a", fg="#e0e0e0").pack(side="left", padx=5)
        audit_user_cb = under_super.FilteredCombobox(
            filter_row1, textvariable=audit_user_var, values=audit_users_list,
            font=("Segoe UI", 10), width=25
        )
        try:
            audit_user_cb.configure(style='Dark.TCombobox')
        except:
            pass
        audit_user_cb.pack(side="left", padx=5)
        
        tk.Label(filter_row1, text="Sitio:", bg="#23272a", fg="#e0e0e0").pack(side="left", padx=5)
        audit_site_cb = under_super.FilteredCombobox(
            filter_row1, textvariable=audit_site_var, values=audit_sites_list,
            font=("Segoe UI", 10), width=32
        )
        try:
            audit_site_cb.configure(style='Dark.TCombobox')
        except:
            pass
        audit_site_cb.pack(side="left", padx=5)
        
        tk.Label(filter_row1, text="Fecha:", bg="#23272a", fg="#e0e0e0").pack(side="left", padx=(15, 5))
        if tkcalendar:
            audit_fecha_entry = tkcalendar.DateEntry(filter_row1, textvariable=audit_fecha_var,
                                                     width=13, background='#4a90e2', foreground='white',
                                                     borderwidth=2, date_pattern='yyyy-mm-dd',
                                                     font=("Segoe UI", 10))
            audit_fecha_entry.pack(side="left", padx=5)
        else:
            audit_fecha_entry = tk.Entry(filter_row1, textvariable=audit_fecha_var, width=13,
                                        bg="#2b2b2b", fg="#ffffff", font=("Segoe UI", 10))
            audit_fecha_entry.pack(side="left", padx=5)
        
        filter_row2 = tk.Frame(audit_filters, bg="#23272a")
        filter_row2.pack(fill="x", padx=20, pady=5)
    
    def search_audit():
        """Busca eventos según filtros"""
        try:
            conn = get_connection()
            cursor = conn.cursor()
            
            # ⭐ Usar INNER JOIN para obtener nombres en lugar de IDs
            sql = """
                SELECT e.ID_Eventos, e.FechaHora, s.Nombre_Sitio, e.Nombre_Actividad, 
                       e.Cantidad, e.Camera, e.Descripcion, u.Nombre_Usuario
                FROM Eventos e
                INNER JOIN user u ON e.ID_Usuario = u.ID_Usuario
                LEFT JOIN Sitios s ON e.ID_Sitio = s.ID_Sitio
                WHERE 1=1
            """
            params = []
            
            if audit_user_var.get() and audit_user_var.get() != "Todos":
                sql += " AND u.Nombre_Usuario = %s"
                params.append(audit_user_var.get())
            
            # ⭐ USAR HELPER para deconstruir formato "Nombre (ID)"
            if audit_site_var.get() and audit_site_var.get() != "Todos":
                site_filter_raw = audit_site_var.get()
                site_name, site_id = under_super.parse_site_filter(site_filter_raw)
                
                if site_name and site_id:
                    # Buscar por nombre (más preciso cuando tenemos ambos)
                    sql += " AND s.Nombre_Sitio = %s"
                    params.append(site_name)
                elif site_id:
                    # Buscar solo por ID
                    sql += " AND e.ID_Sitio = %s"
                    params.append(site_id)
                elif site_name:
                    # Buscar solo por nombre
                    sql += " AND s.Nombre_Sitio = %s"
                    params.append(site_name)
            
            if audit_fecha_var.get():
                sql += " AND DATE(e.FechaHora) = %s"
                params.append(audit_fecha_var.get())
            
            sql += " ORDER BY e.FechaHora DESC LIMIT 500"
            
            cursor.execute(sql, params)
            rows = cursor.fetchall()
            
            # Formatear datos - ahora los nombres ya vienen directamente del JOIN
            data = []
            for row in rows:
                data.append([
                    str(row[0]),  # ID_Eventos
                    str(row[1]) if row[1] else "",  # FechaHora
                    str(row[2]) if row[2] else "",  # Nombre_Sitio
                    str(row[3]) if row[3] else "",  # Nombre_Actividad
                    str(row[4]) if row[4] else "",  # Cantidad
                    str(row[5]) if row[5] else "",  # Camera
                    str(row[6]) if row[6] else "",  # Descripcion
                    str(row[7]) if row[7] else ""   # Nombre_Usuario
                ])
            
            audit_sheet.set_sheet_data(data if data else [["No se encontraron resultados"] + [""] * 7])
            
            cursor.close()
            conn.close()
            
        except Exception as e:
            print(f"[ERROR] search_audit: {e}")
            traceback.print_exc()
            messagebox.showerror("Error", f"Error al buscar:\n{e}", parent=top)
    
    def clear_audit_filters():
        """Limpia los filtros de audit"""
        audit_user_var.set("")
        audit_site_var.set("")
        audit_fecha_var.set("")
        audit_sheet.set_sheet_data([[""] * 8])
    
    # Botones de Audit
    if UI is not None:
        UI.CTkButton(filter_row2, text="🔍 Buscar", command=search_audit,
                    fg_color="#4a90e2", hover_color="#357ABD",
                    width=100, height=32, font=("Segoe UI", 11, "bold")).pack(side="left", padx=5)
        UI.CTkButton(filter_row2, text="🗑️ Limpiar", command=clear_audit_filters,
                    fg_color="#3b4754", hover_color="#4a5560",
                    width=100, height=32, font=("Segoe UI", 11, "bold")).pack(side="left", padx=5)
    else:
        tk.Button(filter_row2, text="🔍 Buscar", command=search_audit,
                 bg="#4a90e2", fg="white", font=("Segoe UI", 11, "bold"),
                 relief="flat", width=10).pack(side="left", padx=5)
        tk.Button(filter_row2, text="🗑️ Limpiar", command=clear_audit_filters,
                 bg="#3b4754", fg="white", font=("Segoe UI", 11, "bold"),
                 relief="flat", width=10).pack(side="left", padx=5)
    
    # Frame para tksheet de Audit
    if UI is not None:
        audit_sheet_frame = UI.CTkFrame(audit_container, fg_color="#2c2f33")
    else:
        audit_sheet_frame = tk.Frame(audit_container, bg="#2c2f33")
    audit_sheet_frame.pack(fill="both", expand=True, padx=10, pady=10)
    
    # Crear tksheet de Audit
    audit_columns = ["ID", " ", "Sitio", "Actividad", "Cantidad", "Camera", "Descripcion", "Usuario"]
    audit_sheet = SheetClass(
        audit_sheet_frame,
        data=[[""] * len(audit_columns)],
        headers=audit_columns,
        theme="dark blue",
        height=500,
        width=1330,
        show_selected_cells_border=True,
        show_row_index=True,
        show_top_left=False,
        empty_horizontal=0,
        empty_vertical=0,
        auto_resize_columns=False,
        auto_resize_rows=False
    )
    audit_sheet.enable_bindings(
    )
    audit_sheet.enable_bindings([
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
    audit_sheet.pack(fill="both", expand=True)
    audit_widths = {
        "ID": 60,
        " ": 150,
        "Sitio": 180,
        "Actividad": 140,
        "Cantidad": 80,
        "Camera": 80,
        "Descripcion": 200,
        "Usuario": 120
    }
    for col_idx, col_name in enumerate(audit_columns):
        if col_name in audit_widths:
            audit_sheet.column_width(column=col_idx, width=audit_widths[col_name])
    
    # ===== COVER TIME CONTAINER =====
    if UI is not None:
        cover_container = UI.CTkFrame(top, fg_color="#2c2f33")
    else:
        cover_container = tk.Frame(top, bg="#2c2f33")
    # No hacer pack aquí, se hace en switch_view()
    
    # Filtros de Cover Time
    if UI is not None:
        cover_filters = UI.CTkFrame(cover_container, fg_color="#23272a", corner_radius=0, height=170)
    else:
        cover_filters = tk.Frame(cover_container, bg="#23272a", height=170)
    cover_filters.pack(fill="x", padx=0, pady=0)
    cover_filters.pack_propagate(False)
    
    # Variables de Cover Time
    cover_user_var = tk.StringVar()
    cover_station_var = tk.StringVar()
    cover_desde_var = tk.StringVar()
    cover_hasta_var = tk.StringVar()
    
    # Obtener usuarios y estaciones para Cover Time
    try:
        conn_temp = get_connection()
        cur_temp = conn_temp.cursor()
        
        # Usuarios
        cur_temp.execute("SELECT Nombre_Usuario FROM user ORDER BY Nombre_Usuario")
        cover_users_list = ["Todos"] + [row[0] for row in cur_temp.fetchall()]
        
        # Estaciones
        cur_temp.execute("SELECT DISTINCT Station FROM covers_programados WHERE Station IS NOT NULL ORDER BY Station")
        cover_stations_list = ["Todos"] + [row[0] for row in cur_temp.fetchall()]
        
        cur_temp.close()
        conn_temp.close()
    except Exception as e:
        print(f"[ERROR] Error al cargar usuarios/estaciones para cover: {e}")
        cover_users_list = ["Todos"]
        cover_stations_list = ["Todos"]
    
    # Labels y controles de Cover Time
    if UI is not None:
        UI.CTkLabel(cover_filters, text="⏰ Covers Programados y Realizados", 
                   font=("Segoe UI", 14, "bold"), text_color="#e0e0e0").pack(side="top", padx=20, pady=(10, 5))
        
        cover_summary_label = UI.CTkLabel(cover_filters, text="Total: 0 covers cargados",
                                         font=("Segoe UI", 12, "bold"), text_color="#00bfae")
        cover_summary_label.pack(side="top", pady=5)
        
        cover_filter_row1 = UI.CTkFrame(cover_filters, fg_color="transparent")
        cover_filter_row1.pack(fill="x", padx=20, pady=5)
        
        UI.CTkLabel(cover_filter_row1, text="Usuario:", text_color="#e0e0e0").pack(side="left", padx=5)
        cover_user_cb = under_super.FilteredCombobox(
            cover_filter_row1, textvariable=cover_user_var, values=cover_users_list,
            font=("Segoe UI", 10), width=22,
            background='#2b2b2b', foreground='#ffffff',
            bordercolor='#4a90e2', arrowcolor='#ffffff'
        )
        cover_user_cb.pack(side="left", padx=5)
        
        UI.CTkLabel(cover_filter_row1, text="Estación:", text_color="#e0e0e0").pack(side="left", padx=(10, 5))
        cover_station_cb = under_super.FilteredCombobox(
            cover_filter_row1, textvariable=cover_station_var, values=cover_stations_list,
            font=("Segoe UI", 10), width=22,
            background='#2b2b2b', foreground='#ffffff',
            bordercolor='#4a90e2', arrowcolor='#ffffff'
        )
        cover_station_cb.pack(side="left", padx=5)
        
        UI.CTkLabel(cover_filter_row1, text="Desde:", text_color="#e0e0e0").pack(side="left", padx=(15, 5))
        # Frame contenedor para DateEntry (tkcalendar no es compatible directo con CTk)
        cover_desde_frame = tk.Frame(cover_filter_row1, bg="#23272a")
        cover_desde_frame.pack(side="left", padx=5)
        if tkcalendar:
            cover_desde_entry = tkcalendar.DateEntry(cover_desde_frame, textvariable=cover_desde_var,
                                                     width=13, background='#4a90e2', foreground='white',
                                                     borderwidth=2, date_pattern='yyyy-mm-dd',
                                                     font=("Segoe UI", 10))
            cover_desde_entry.pack()
        else:
            cover_desde_entry = tk.Entry(cover_desde_frame, textvariable=cover_desde_var, width=13,
                                        bg="#2b2b2b", fg="#ffffff", font=("Segoe UI", 10))
            cover_desde_entry.pack()
        
        UI.CTkLabel(cover_filter_row1, text="Hasta:", text_color="#e0e0e0").pack(side="left", padx=(15, 5))
        # Frame contenedor para DateEntry
        cover_hasta_frame = tk.Frame(cover_filter_row1, bg="#23272a")
        cover_hasta_frame.pack(side="left", padx=5)
        if tkcalendar:
            cover_hasta_entry = tkcalendar.DateEntry(cover_hasta_frame, textvariable=cover_hasta_var,
                                                     width=13, background='#4a90e2', foreground='white',
                                                     borderwidth=2, date_pattern='yyyy-mm-dd',
                                                     font=("Segoe UI", 10))
            cover_hasta_entry.pack()
        else:
            cover_hasta_entry = tk.Entry(cover_hasta_frame, textvariable=cover_hasta_var, width=13,
                                        bg="#2b2b2b", fg="#ffffff", font=("Segoe UI", 10))
            cover_hasta_entry.pack()
        
        cover_filter_row2 = UI.CTkFrame(cover_filters, fg_color="transparent")
        cover_filter_row2.pack(fill="x", padx=20, pady=5)
    else:
        tk.Label(cover_filters, text="⏰ Covers Programados y Realizados", 
                bg="#23272a", fg="#e0e0e0", font=("Segoe UI", 14, "bold")).pack(side="top", padx=20, pady=(10, 5))
        
        cover_summary_label = tk.Label(cover_filters, text="Total: 0 covers cargados",
                                      bg="#23272a", fg="#00bfae", font=("Segoe UI", 12, "bold"))
        cover_summary_label.pack(side="top", pady=5)
        
        cover_filter_row1 = tk.Frame(cover_filters, bg="#23272a")
        cover_filter_row1.pack(fill="x", padx=20, pady=5)
        
        tk.Label(cover_filter_row1, text="Usuario:", bg="#23272a", fg="#e0e0e0").pack(side="left", padx=5)
        cover_user_cb = under_super.FilteredCombobox(
            cover_filter_row1, textvariable=cover_user_var, values=cover_users_list,
            font=("Segoe UI", 10), width=22
        )
        try:
            cover_user_cb.configure(style='Dark.TCombobox')
        except:
            pass
        cover_user_cb.pack(side="left", padx=5)
        
        tk.Label(cover_filter_row1, text="Estación:", bg="#23272a", fg="#e0e0e0").pack(side="left", padx=(10, 5))
        cover_station_cb = under_super.FilteredCombobox(
            cover_filter_row1, textvariable=cover_station_var, values=cover_stations_list,
            font=("Segoe UI", 10), width=22
        )
        try:
            cover_station_cb.configure(style='Dark.TCombobox')
        except:
            pass
        cover_station_cb.pack(side="left", padx=5)
        
        tk.Label(cover_filter_row1, text="Desde:", bg="#23272a", fg="#e0e0e0").pack(side="left", padx=(15, 5))
        if tkcalendar:
            cover_desde_entry = tkcalendar.DateEntry(cover_filter_row1, textvariable=cover_desde_var,
                                                     width=13, background='#4a90e2', foreground='white',
                                                     borderwidth=2, date_pattern='yyyy-mm-dd',
                                                     font=("Segoe UI", 10))
            cover_desde_entry.pack(side="left", padx=5)
        else:
            cover_desde_entry = tk.Entry(cover_filter_row1, textvariable=cover_desde_var, width=13,
                                        bg="#2b2b2b", fg="#ffffff", font=("Segoe UI", 10))
            cover_desde_entry.pack(side="left", padx=5)
        
        tk.Label(cover_filter_row1, text="Hasta:", bg="#23272a", fg="#e0e0e0").pack(side="left", padx=(15, 5))
        if tkcalendar:
            cover_hasta_entry = tkcalendar.DateEntry(cover_filter_row1, textvariable=cover_hasta_var,
                                                     width=13, background='#4a90e2', foreground='white',
                                                     borderwidth=2, date_pattern='yyyy-mm-dd',
                                                     font=("Segoe UI", 10))
            cover_hasta_entry.pack(side="left", padx=5)
        else:
            cover_hasta_entry = tk.Entry(cover_filter_row1, textvariable=cover_hasta_var, width=13,
                                        bg="#2b2b2b", fg="#ffffff", font=("Segoe UI", 10))
            cover_hasta_entry.pack(side="left", padx=5)
        
        cover_filter_row2 = tk.Frame(cover_filters, bg="#23272a")
        cover_filter_row2.pack(fill="x", padx=20, pady=5)
    
    def search_covers():
        """Busca covers según filtros usando load_combined_covers()"""
        try:
            # Obtener filtros
            usuario = cover_user_var.get().strip()
            estacion = cover_station_var.get().strip()
            fecha_desde = cover_desde_var.get().strip()
            fecha_hasta = cover_hasta_var.get().strip()
            
            # Validar fechas
            if fecha_desde and fecha_hasta:
                try:
                    from datetime import datetime
                    d1 = datetime.strptime(fecha_desde, "%Y-%m-%d")
                    d2 = datetime.strptime(fecha_hasta, "%Y-%m-%d")
                    if d1 > d2:
                        messagebox.showwarning("Advertencia", "La fecha 'Desde' no puede ser mayor que 'Hasta'", parent=top)
                        return
                except:
                    messagebox.showerror("Error", "Formato de fecha inválido. Use YYYY-MM-DD", parent=top)
                    return
            
            # Cargar todos los covers desde la función combinada
            col_names, rows = under_super.load_combined_covers()
            
            if not rows:
                cover_sheet.set_sheet_data([["No hay datos disponibles"] + [""] * 11])
                cover_summary_label.configure(text="Total: 0 covers cargados")
                return
            
            # Aplicar filtros
            filtered_rows = []
            for row in rows:
                # Filtro por usuario (columna 1: Usuario)
                if usuario and usuario != "Todos":
                    if row[1] != usuario:
                        continue
                
                # Filtro por estación (columna 3: Estacion)
                if estacion and estacion != "Todos":
                    if row[3] != estacion:
                        continue
                
                # Filtro por fecha (columna 2: Hora_Programada)
                if fecha_desde or fecha_hasta:
                    try:
                        from datetime import datetime
                        fecha_cover = row[2]  # Hora_Programada
                        if fecha_cover:
                            if isinstance(fecha_cover, str):
                                fecha_cover_dt = datetime.strptime(fecha_cover.split()[0], "%Y-%m-%d")
                            else:
                                fecha_cover_dt = datetime.combine(fecha_cover.date() if hasattr(fecha_cover, 'date') else fecha_cover, datetime.min.time())
                            
                            if fecha_desde:
                                fecha_d = datetime.strptime(fecha_desde, "%Y-%m-%d")
                                if fecha_cover_dt < fecha_d:
                                    continue
                            
                            if fecha_hasta:
                                fecha_h = datetime.strptime(fecha_hasta, "%Y-%m-%d")
                                if fecha_cover_dt > fecha_h:
                                    continue
                    except Exception as e:
                        print(f"[DEBUG] Error al filtrar fecha: {e}")
                        pass
                
                filtered_rows.append(row)
            
            # Formatear datos para mostrar
            data = []
            for row in filtered_rows:
                formatted_row = [str(cell) if cell is not None else "" for cell in row]
                data.append(formatted_row)
            
            # Actualizar sheet
            cover_sheet.set_sheet_data(data if data else [["No hay resultados con esos filtros"] + [""] * 11])
            
            # Actualizar resumen
            summary_text = f"Total: {len(data)} covers cargados"
            cover_summary_label.configure(text=summary_text)
            
            print(f"[INFO] Cover Time: {len(data)} covers encontrados")
            
        except Exception as e:
            print(f"[ERROR] search_covers: {e}")
            traceback.print_exc()
            messagebox.showerror("Error", f"Error al buscar covers:\n{e}", parent=top)
    
    def clear_cover_filters():
        """Limpia filtros de cover"""
        cover_user_var.set("")
        cover_station_var.set("")
        cover_desde_var.set("")
        cover_hasta_var.set("")
        cover_sheet.set_sheet_data([[""] * 12])
        cover_summary_label.configure(text="Total: 0 covers cargados")
    
    # Botones de Cover Time
    if UI is not None:
        UI.CTkButton(cover_filter_row2, text="🔍 Buscar", command=search_covers,
                    fg_color="#4a90e2", hover_color="#357ABD",
                    width=100, height=32, font=("Segoe UI", 11, "bold")).pack(side="left", padx=5)
        UI.CTkButton(cover_filter_row2, text="🗑️ Limpiar", command=clear_cover_filters,
                    fg_color="#3b4754", hover_color="#4a5560",
                    width=100, height=32, font=("Segoe UI", 11, "bold")).pack(side="left", padx=5)
    else:
        tk.Button(cover_filter_row2, text="🔍 Buscar", command=search_covers,
                 bg="#4a90e2", fg="white", font=("Segoe UI", 11, "bold"),
                 relief="flat", width=10).pack(side="left", padx=5)
        tk.Button(cover_filter_row2, text="🗑️ Limpiar", command=clear_cover_filters,
                 bg="#3b4754", fg="white", font=("Segoe UI", 11, "bold"),
                 relief="flat", width=10).pack(side="left", padx=5)
    
    # Frame para tksheet de Cover Time
    if UI is not None:
        cover_sheet_frame = UI.CTkFrame(cover_container, fg_color="#2c2f33")
    else:
        cover_sheet_frame = tk.Frame(cover_container, bg="#2c2f33")
    cover_sheet_frame.pack(fill="both", expand=True, padx=10, pady=10)
    
    # Crear tksheet de Cover Time con columnas de load_combined_covers
    cover_columns = ["ID_Cover", "Usuario", "Hora_Programada", "Estacion", "Razon_Solicitud", 
                     "Aprobado", "Activo", "Cover_Inicio", "Cover_Fin", "Cubierto_Por", "Motivo_Real", "Estado"]
    cover_sheet = SheetClass(
        cover_sheet_frame,
        data=[[""] * len(cover_columns)],
        headers=cover_columns,
        theme="dark blue",
        height=500,
        width=1330,
        show_selected_cells_border=True,
        show_row_index=True,
        show_top_left=False,
        empty_horizontal=0,
        empty_vertical=0,
        auto_resize_columns=False,
        auto_resize_rows=False
    )
    cover_sheet.enable_bindings([
        
   
        "single_select",

         ],
    )
    cover_sheet.enable_bindings([
        "single_select",
        "drag_select",
        "row_select",
        "column_select",
        "column_width_resize",
        "double_click_column_resize",
        "arrowkeys",
        "copy",
        "select_all"
        ],
    )
    cover_sheet.pack(fill="both", expand=True)

    cover_widths = {
        "ID_Cover": 70,
        "Usuario": 110,
        "Hora_Programada": 150,
        "Estacion": 100,
        "Razon_Solicitud": 150,
        "Aprobado": 80,
        "Activo": 80,
        "Cover_Inicio": 150,
        "Cover_Fin": 150,
        "Cubierto_Por": 110,
        "Motivo_Real": 150,
        "Estado": 150
    }
    for col_idx, col_name in enumerate(cover_columns):
        if col_name in cover_widths:
            cover_sheet.column_width(column=col_idx, width=cover_widths[col_name])

    # ==================== ROL DE COVER CONTAINER ====================
    if UI is not None:
        rol_cover_container = UI.CTkFrame(top, fg_color="#2c2f33")
    else:
        rol_cover_container = tk.Frame(top, bg="#2c2f33")
    # NO hacer pack() aquí - se mostrará solo cuando se cambie a modo Rol de Cover

    # Frame de instrucciones
    if UI is not None:
        info_frame_rol = UI.CTkFrame(rol_cover_container, fg_color="#23272a", corner_radius=8)
    else:
        info_frame_rol = tk.Frame(rol_cover_container, bg="#23272a")
    info_frame_rol.pack(fill="x", padx=10, pady=10)

    if UI is not None:
        UI.CTkLabel(info_frame_rol, 
                   text="🎭 Gestión de Rol de Cover - Habilitar operadores que pueden ver la lista de covers",
                   text_color="#00bfae", 
                   font=("Segoe UI", 14, "bold")).pack(pady=15)
    else:
        tk.Label(info_frame_rol, 
                text="🎭 Gestión de Rol de Cover - Habilitar operadores que pueden ver la lista de covers",
                bg="#23272a", fg="#00bfae", 
                font=("Segoe UI", 14, "bold")).pack(pady=15)

    # Frame principal con dos columnas
    if UI is not None:
        main_frame_rol = UI.CTkFrame(rol_cover_container, fg_color="#2c2f33")
    else:
        main_frame_rol = tk.Frame(rol_cover_container, bg="#2c2f33")
    main_frame_rol.pack(fill="both", expand=True, padx=10, pady=10)

    # Columna izquierda: Operadores disponibles (Active = 1)
    if UI is not None:
        left_frame_rol = UI.CTkFrame(main_frame_rol, fg_color="#23272a", corner_radius=8)
    else:
        left_frame_rol = tk.Frame(main_frame_rol, bg="#23272a")
    left_frame_rol.pack(side="left", fill="both", expand=True, padx=(0, 5))

    if UI is not None:
        UI.CTkLabel(left_frame_rol, 
                   text="👤 Operadores Activos (Sin acceso a covers)",
                   text_color="#ffffff", 
                   font=("Segoe UI", 13, "bold")).pack(pady=10)
    else:
        tk.Label(left_frame_rol, 
                text="👤 Operadores Activos (Sin acceso a covers)",
                bg="#23272a", fg="#ffffff", 
                font=("Segoe UI", 13, "bold")).pack(pady=10)

    # Listbox para operadores sin acceso
    list_frame_sin_acceso = tk.Frame(left_frame_rol, bg="#23272a")
    list_frame_sin_acceso.pack(fill="both", expand=True, padx=15, pady=(0, 15))

    scroll_sin_acceso = tk.Scrollbar(list_frame_sin_acceso, orient="vertical")
    scroll_sin_acceso.pack(side="right", fill="y")

    listbox_sin_acceso = tk.Listbox(list_frame_sin_acceso, 
                                    selectmode="extended",
                                    bg="#262a31", 
                                    fg="#ffffff", 
                                    font=("Segoe UI", 11),
                                    yscrollcommand=scroll_sin_acceso.set,
                                    selectbackground="#4a90e2",
                                    height=20)
    listbox_sin_acceso.pack(side="left", fill="both", expand=True)
    scroll_sin_acceso.config(command=listbox_sin_acceso.yview)

    # Columna derecha: Operadores con acceso (Active = 2)
    if UI is not None:
        right_frame_rol = UI.CTkFrame(main_frame_rol, fg_color="#23272a", corner_radius=8)
    else:
        right_frame_rol = tk.Frame(main_frame_rol, bg="#23272a")
    right_frame_rol.pack(side="left", fill="both", expand=True, padx=(5, 0))

    if UI is not None:
        UI.CTkLabel(right_frame_rol, 
                   text="✅ Operadores con Acceso a Covers",
                   text_color="#00c853", 
                   font=("Segoe UI", 13, "bold")).pack(pady=10)
    else:
        tk.Label(right_frame_rol, 
                text="✅ Operadores con Acceso a Covers",
                bg="#23272a", fg="#00c853", 
                font=("Segoe UI", 13, "bold")).pack(pady=10)

    # Listbox para operadores con acceso
    list_frame_con_acceso = tk.Frame(right_frame_rol, bg="#23272a")
    list_frame_con_acceso.pack(fill="both", expand=True, padx=15, pady=(0, 15))

    scroll_con_acceso = tk.Scrollbar(list_frame_con_acceso, orient="vertical")
    scroll_con_acceso.pack(side="right", fill="y")

    listbox_con_acceso = tk.Listbox(list_frame_con_acceso, 
                                    selectmode="extended",
                                    bg="#262a31", 
                                    fg="#00c853", 
                                    font=("Segoe UI", 11),
                                    yscrollcommand=scroll_con_acceso.set,
                                    selectbackground="#4a90e2",
                                    height=20)
    listbox_con_acceso.pack(side="left", fill="both", expand=True)
    scroll_con_acceso.config(command=listbox_con_acceso.yview)

    # Frame de botones entre las dos columnas
    if UI is not None:
        buttons_frame_rol = UI.CTkFrame(rol_cover_container, fg_color="#2c2f33")
    else:
        buttons_frame_rol = tk.Frame(rol_cover_container, bg="#2c2f33")
    buttons_frame_rol.pack(fill="x", padx=10, pady=10)

    def cargar_operadores_rol():
        """Carga operadores separados por su estado Statuses en sesiones activas"""
        try:
            conn = get_connection()
            cur = conn.cursor()
            
            # Limpiar listboxes
            listbox_sin_acceso.delete(0, tk.END)
            listbox_con_acceso.delete(0, tk.END)
            
            # Operadores con Active = 1 y Statuses IS NULL o != 2 (sin acceso a covers)
            cur.execute("""
                SELECT DISTINCT s.ID_user 
                FROM sesion s
                INNER JOIN user u ON s.ID_user = u.Nombre_Usuario
                WHERE s.Active = 1 
                  AND (s.Statuses IS NULL OR s.Statuses != 2) 
                  AND u.Rol = 'Operador'
                ORDER BY s.ID_user
            """)
            sin_acceso = cur.fetchall()
            
            for row in sin_acceso:
                listbox_sin_acceso.insert(tk.END, row[0])
            
            # Operadores con Active = 1 y Statuses = 2 (con acceso a covers)
            cur.execute("""
                SELECT DISTINCT s.ID_user 
                FROM sesion s
                INNER JOIN user u ON s.ID_user = u.Nombre_Usuario
                WHERE s.Active = 1 
                  AND s.Statuses = 2 
                  AND u.Rol = 'Operador'
                ORDER BY s.ID_user
            """)
            con_acceso = cur.fetchall()
            
            for row in con_acceso:
                listbox_con_acceso.insert(tk.END, row[0])
            
            cur.close()
            conn.close()
            
            print(f"[DEBUG] Operadores cargados: {len(sin_acceso)} sin acceso, {len(con_acceso)} con acceso")
            
        except Exception as e:
            print(f"[ERROR] cargar_operadores_rol: {e}")
            traceback.print_exc()
            messagebox.showerror("Error", f"Error al cargar operadores:\n{e}", parent=top)

    def habilitar_acceso():
        """Cambia Statuses a 2 para los operadores seleccionados (habilitar acceso a covers)"""
        seleccion = listbox_sin_acceso.curselection()
        if not seleccion:
            messagebox.showwarning("Selección", "Selecciona uno o más operadores para habilitar.", parent=top)
            return
        
        operadores = [listbox_sin_acceso.get(i) for i in seleccion]
        
        if not messagebox.askyesno("Confirmar", 
                                   f"¿Habilitar acceso a covers para {len(operadores)} operador(es)?",
                                   parent=top):
            return
        
        try:
            conn = get_connection()
            cur = conn.cursor()
            
            for operador in operadores:
                cur.execute("""
                    UPDATE sesion 
                    SET Statuses = 2 
                    WHERE ID_user = %s AND Active = 1
                """, (operador,))
            
            conn.commit()
            cur.close()
            conn.close()
            
            cargar_operadores_rol()
            messagebox.showinfo("Éxito", f"✅ {len(operadores)} operador(es) habilitado(s) para ver covers", parent=top)
            
        except Exception as e:
            print(f"[ERROR] habilitar_acceso: {e}")
            traceback.print_exc()
            messagebox.showerror("Error", f"Error al habilitar acceso:\n{e}", parent=top)

    def deshabilitar_acceso():
        """Cambia Active de 2 a 1 para los operadores seleccionados (quitar acceso a covers)"""
        seleccion = listbox_con_acceso.curselection()
        if not seleccion:
            messagebox.showwarning("Selección", "Selecciona uno o más operadores para deshabilitar.", parent=top)
            return
        
        operadores = [listbox_con_acceso.get(i) for i in seleccion]
        
        if not messagebox.askyesno("Confirmar", 
                                   f"¿Quitar acceso a covers para {len(operadores)} operador(es)?",
                                   parent=top):
            return
        
        try:
            conn = get_connection()
            cur = conn.cursor()
            
            for operador in operadores:
                cur.execute("""
                    UPDATE sesion 
                    SET Statuses = NULL 
                    WHERE ID_user = %s AND Active = 1 AND Statuses = 2
                """, (operador,))
            
            conn.commit()
            cur.close()
            conn.close()
            
            cargar_operadores_rol()
            messagebox.showinfo("Éxito", f"❌ {len(operadores)} operador(es) deshabilitado(s) para ver covers", parent=top)
            
        except Exception as e:
            print(f"[ERROR] deshabilitar_acceso: {e}")
            traceback.print_exc()
            messagebox.showerror("Error", f"Error al deshabilitar acceso:\n{e}", parent=top)

    def refrescar_lista_operadores():
        """Wrapper para refrescar la lista"""
        cargar_operadores_rol()

    # Botones de acción
    if UI is not None:
        UI.CTkButton(buttons_frame_rol, 
                    text="➡️ Habilitar Acceso a Covers",
                    command=habilitar_acceso,
                    fg_color="#00c853",
                    hover_color="#00a043",
                    width=220,
                    height=40,
                    font=("Segoe UI", 13, "bold")).pack(side="left", padx=10, pady=5)
        
        UI.CTkButton(buttons_frame_rol, 
                    text="⬅️ Quitar Acceso a Covers",
                    command=deshabilitar_acceso,
                    fg_color="#f04747",
                    hover_color="#d84040",
                    width=220,
                    height=40,
                    font=("Segoe UI", 13, "bold")).pack(side="left", padx=10, pady=5)
        
        UI.CTkButton(buttons_frame_rol, 
                    text="🔄 Refrescar Lista",
                    command=refrescar_lista_operadores,
                    fg_color="#4a90e2",
                    hover_color="#357ABD",
                    width=180,
                    height=40,
                    font=("Segoe UI", 13, "bold")).pack(side="left", padx=10, pady=5)
    else:
        tk.Button(buttons_frame_rol, 
                 text="➡️ Habilitar Acceso a Covers",
                 command=habilitar_acceso,
                 bg="#00c853",
                 fg="white",
                 font=("Segoe UI", 13, "bold"),
                 relief="flat",
                 width=24).pack(side="left", padx=10, pady=5)
        
        tk.Button(buttons_frame_rol, 
                 text="⬅️ Quitar Acceso a Covers",
                 command=deshabilitar_acceso,
                 bg="#f04747",
                 fg="white",
                 font=("Segoe UI", 13, "bold"),
                 relief="flat",
                 width=24).pack(side="left", padx=10, pady=5)
        
        tk.Button(buttons_frame_rol, 
                 text="🔄 Refrescar Lista",
                 command=refrescar_lista_operadores,
                 bg="#4a90e2",
                 fg="white",
                 font=("Segoe UI", 13, "bold"),
                 relief="flat",
                 width=18).pack(side="left", padx=10, pady=5)

    # ==================== BREAKS CONTAINER ====================
    if UI is not None:
        breaks_container = UI.CTkFrame(top, fg_color="#2c2f33")
    else:
        breaks_container = tk.Frame(top, bg="#2c2f33")
    # NO hacer pack() aquí - se mostrará solo cuando se cambie a modo Breaks

    # Frame de controles (comboboxes y botones) para Breaks
    if UI is not None:
        breaks_controls_frame = UI.CTkFrame(breaks_container, fg_color="#23272a", corner_radius=8)
    else:
        breaks_controls_frame = tk.Frame(breaks_container, bg="#23272a")
    breaks_controls_frame.pack(fill="x", padx=10, pady=10)

    # Función para cargar usuarios desde la BD
    def load_users_breaks():
        """Carga lista de usuarios desde la base de datos"""
        try:
            users = load_users()
            return users if users else []
        except Exception as e:
            print(f"[ERROR] load_users_breaks: {e}")
            traceback.print_exc()
            return []

    # Función para cargar covers desde la BD
    def load_covers_from_db():
        """Carga covers activos desde gestion_breaks_programados con nombres de usuario"""
        try:
            conn = get_connection()
            cur = conn.cursor()
            query = """
                SELECT 
                    u_covered.Nombre_Usuario as usuario_cubierto,
                    u_covering.Nombre_Usuario as usuario_cubre,
                    TIME(gbp.Fecha_hora_cover) as hora
                FROM gestion_breaks_programados gbp
                INNER JOIN user u_covered ON gbp.User_covered = u_covered.ID_Usuario
                INNER JOIN user u_covering ON gbp.User_covering = u_covering.ID_Usuario
                WHERE gbp.is_Active = 1
                ORDER BY gbp.Fecha_hora_cover
            """
            cur.execute(query)
            rows = cur.fetchall()
            cur.close()
            conn.close()
            
            # Debug: Imprimir los datos cargados
            print(f"[DEBUG] Covers cargados desde BD: {len(rows)} registros")
            for row in rows:
                print(f"[DEBUG] Cover: {row[0]} cubierto por {row[1]} a las {row[2]}")
            
            return rows
        except Exception as e:
            print(f"[ERROR] load_covers_from_db: {e}")
            traceback.print_exc()
            return []

    # Variables para comboboxes
    usuario_a_cubrir_var = tk.StringVar()
    cubierto_por_var = tk.StringVar()
    hora_var = tk.StringVar()

    # Cargar usuarios
    users_list = load_users_breaks()

    # Primera fila: Usuario a cubrir
    row1_frame_breaks = tk.Frame(breaks_controls_frame, bg="#23272a")
    row1_frame_breaks.pack(fill="x", padx=20, pady=(15, 5))

    if UI is not None:
        UI.CTkLabel(row1_frame_breaks, text="👤 Usuario a Cubrir:", 
                   text_color="#ffffff", font=("Segoe UI", 14, "bold")).pack(side="left", padx=(0, 10))
    else:
        tk.Label(row1_frame_breaks, text="👤 Usuario a Cubrir:", bg="#23272a", fg="#ffffff", 
                font=("Segoe UI", 14, "bold")).pack(side="left", padx=(0, 10))

    if UI is not None:
        usuario_combo_breaks = under_super.FilteredCombobox(row1_frame_breaks, textvariable=usuario_a_cubrir_var,
                                                     values=users_list, width=40,
                                                     font=("Segoe UI", 11))
        usuario_combo_breaks.set("")  # Establecer vacío inicialmente
    else:
        usuario_combo_breaks = ttk.Combobox(row1_frame_breaks, textvariable=usuario_a_cubrir_var,
                                           values=users_list, width=25)
    usuario_combo_breaks.pack(side="left", padx=5)

    # Segunda fila: Cubierto por
    row2_frame_breaks = tk.Frame(breaks_controls_frame, bg="#23272a")
    row2_frame_breaks.pack(fill="x", padx=20, pady=5)

    if UI is not None:
        UI.CTkLabel(row2_frame_breaks, text="🔄 Cubierto Por:", 
                   text_color="#ffffff", font=("Segoe UI", 14, "bold")).pack(side="left", padx=(0, 10))
    else:
        tk.Label(row2_frame_breaks, text="🔄 Cubierto Por:", bg="#23272a", fg="#ffffff", 
                font=("Segoe UI", 14, "bold")).pack(side="left", padx=(0, 10))

    if UI is not None:
        cover_by_combo_breaks = under_super.FilteredCombobox(row2_frame_breaks, textvariable=cubierto_por_var,
                                              values=users_list, width=40,
                                              font=("Segoe UI", 11))
        cover_by_combo_breaks.set("")  # Establecer vacío inicialmente
    else:
        cover_by_combo_breaks = ttk.Combobox(row2_frame_breaks, textvariable=cubierto_por_var,
                                            values=users_list, width=25)
    cover_by_combo_breaks.pack(side="left", padx=5)

    # Generar lista de horas en formato HH:00:00 (cada hora del día)
    horas_disponibles = [f"{h:02d}:00:00" for h in range(24)]

    # Tercera fila: Hora
    row3_frame_breaks = tk.Frame(breaks_controls_frame, bg="#23272a")
    row3_frame_breaks.pack(fill="x", padx=20, pady=5)

    if UI is not None:
        UI.CTkLabel(row3_frame_breaks, text="🕐 Hora Programada:", 
                   text_color="#ffffff", font=("Segoe UI", 14, "bold")).pack(side="left", padx=(0, 10))
    else:
        tk.Label(row3_frame_breaks, text="🕐 Hora Programada:", bg="#23272a", fg="#ffffff", 
                font=("Segoe UI", 14, "bold")).pack(side="left", padx=(0, 10))

    if UI is not None:
        hora_combo_breaks = under_super.FilteredCombobox(
            row3_frame_breaks, 
            textvariable=hora_var,
            values=horas_disponibles,
            width=25,
            font=("Segoe UI", 13),
            background='#2b2b2b', 
            foreground='#ffffff',
            bordercolor='#4a90e2', 
            arrowcolor='#ffffff'
        )
        hora_combo_breaks.pack(side="left", padx=5)
    else:
        hora_entry_breaks = tk.Entry(row3_frame_breaks, textvariable=hora_var, width=27)
        hora_entry_breaks.pack(side="left", padx=5)

    # Función para cargar datos agrupados (matriz)
    def cargar_datos_agrupados_breaks():
        """Carga datos agrupados por quien cubre (covered_by como columnas)"""
        try:
            rows = load_covers_from_db()
            
            # Obtener lista única de "Cubierto Por" (nombres) para las columnas
            covered_by_set = sorted(set(row[1] for row in rows if row[1]))
            
            # Headers: hora primero + columnas de personas que cubren (nombres)
            headers = ["Hora Programada"]
            for cb in covered_by_set:
                headers.append(cb)  # Ya son nombres de usuario
            
            # Agrupar por hora - solo el PRIMER usuario por covered_by y hora
            horas_dict = {}
            for row in rows:
                usuario_cubierto = row[0]  # Nombre del usuario a cubrir
                usuario_cubre = row[1]     # Nombre del usuario que cubre
                hora = str(row[2])          # Hora en formato HH:MM:SS
                
                if hora not in horas_dict:
                    horas_dict[hora] = {cb: "" for cb in covered_by_set}
                
                # Solo asignar si la celda está vacía (un usuario por celda)
                if usuario_cubre in horas_dict[hora] and not horas_dict[hora][usuario_cubre]:
                    horas_dict[hora][usuario_cubre] = usuario_cubierto
            
            # Convertir a lista de filas para el sheet
            data = []
            for hora in sorted(horas_dict.keys()):
                fila = [hora]
                for covered_by in covered_by_set:
                    fila.append(horas_dict[hora][covered_by])
                data.append(fila)
            
            print(f"[DEBUG] Headers construidos para breaks: {headers}")
            print(f"[DEBUG] Data construida: {len(data)} filas")
            
            return headers, data
            
        except Exception as e:
            print(f"[ERROR] cargar_datos_agrupados_breaks: {e}")
            traceback.print_exc()
            return ["Hora Programada"], [[]]

    # Función para limpiar formulario
    def limpiar_breaks():
        usuario_combo_breaks.set("")
        cover_by_combo_breaks.set("")
        hora_var.set("")
    
    # Función wrapper para eliminar cover
    def eliminar_cover_breaks():
        """Wrapper que llama a under_super.eliminar_cover_breaks con todos los parámetros necesarios"""
        if not USE_SHEET:
            return
        
        success, mensaje, rows = under_super.eliminar_cover_breaks(
            breaks_sheet=breaks_sheet,
            parent_window=top
        )
        
        # Si fue exitoso, refrescar la tabla
        if success:
            refrescar_tabla_breaks()

    # Función para refrescar tabla
    def refrescar_tabla_breaks():
        if not USE_SHEET:
            return
        headers, data = cargar_datos_agrupados_breaks()
        breaks_sheet.headers(headers)
        breaks_sheet.set_sheet_data(data)
        # Reajustar anchos después de refrescar
        for i in range(len(headers)):
            breaks_sheet.column_width(column=i, width=120)
        breaks_sheet.redraw()

    # Función wrapper para agregar y refrescar
    def agregar_y_refrescar():
        """Agrega un cover y luego refresca la tabla"""
        try:
            under_super.select_covered_by(
                username, 
                hora=hora_var.get(), 
                usuario=cubierto_por_var.get(),
                cover=usuario_a_cubrir_var.get()
            )
            # Refrescar tabla y limpiar formulario después de agregar
            limpiar_breaks()
            refrescar_tabla_breaks()
        except Exception as e:
            print(f"[ERROR] agregar_y_refrescar: {e}")
            traceback.print_exc()

    # Cuarta fila: Botones
    row4_frame_breaks = tk.Frame(breaks_controls_frame, bg="#23272a")
    row4_frame_breaks.pack(fill="x", padx=20, pady=(5, 15))

    if UI is not None:
        UI.CTkButton(row4_frame_breaks, text="➕ Agregar",
                    command=agregar_y_refrescar,
                    fg_color="#28a745", hover_color="#218838",
                    font=("Segoe UI", 13, "bold"),
                    width=150).pack(side="left", padx=5)
        
        UI.CTkButton(row4_frame_breaks, text="🔄 Limpiar",
                    command=limpiar_breaks,
                    fg_color="#6c757d", hover_color="#5a6268",
                    font=("Segoe UI", 13),
                    width=120).pack(side="left", padx=5)
        
        UI.CTkButton(row4_frame_breaks, text="🗑️ Eliminar Cover Seleccionado",
                    command=eliminar_cover_breaks,
                    fg_color="#dc3545", hover_color="#c82333",
                    font=("Segoe UI", 13),
                    width=220).pack(side="left", padx=5)
    else:
        tk.Button(row4_frame_breaks, text="➕ Agregar",
                 command=agregar_y_refrescar,
                 bg="#28a745", fg="white",
                 font=("Segoe UI", 13, "bold"),
                 relief="flat", width=12).pack(side="left", padx=5)
        
        tk.Button(row4_frame_breaks, text="🔄 Limpiar",
                 command=limpiar_breaks,
                 bg="#6c757d", fg="white",
                 font=("Segoe UI", 13),
                 relief="flat", width=10).pack(side="left", padx=5)
        
        tk.Button(row4_frame_breaks, text="🗑️ Eliminar Cover Seleccionado",
                 command=eliminar_cover_breaks,
                 bg="#dc3545", fg="white",
                 font=("Segoe UI", 13),
                 relief="flat", width=24).pack(side="left", padx=5)

    # Frame para tksheet de Breaks
    if UI is not None:
        breaks_sheet_frame = UI.CTkFrame(breaks_container, fg_color="#2c2f33")
    else:
        breaks_sheet_frame = tk.Frame(breaks_container, bg="#2c2f33")
    breaks_sheet_frame.pack(fill="both", expand=True, padx=10, pady=10)

    if USE_SHEET:
        headers, data = cargar_datos_agrupados_breaks()
        
        breaks_sheet = SheetClass(breaks_sheet_frame,
                                 headers=headers,
                                 theme="dark blue",
                                 width=1280,
                                 height=450)
        breaks_sheet.enable_bindings([
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
        breaks_sheet.pack(fill="both", expand=True)
        
        breaks_sheet.set_sheet_data(data)
        breaks_sheet.change_theme("dark blue")
        
        # Ajustar anchos de columnas
        for i in range(len(headers)):
            breaks_sheet.column_width(column=i, width=120)
        
        # Función para editar celda con doble clic
        def editar_celda_breaks(event):
            try:
                # Obtener la celda seleccionada
                selection = breaks_sheet.get_currently_selected()
                if not selection:
                    return
                
                row, col = selection.row, selection.column
                
                # Ignorar primera columna (hora) y primera fila (headers)
                if col == 0 or row < 0:
                    return
                
                # Obtener datos de la celda
                current_data = breaks_sheet.get_sheet_data()
                if row >= len(current_data):
                    return
                
                hora_actual = current_data[row][0]  # Primera columna es la hora
                usuario_cubierto_actual = current_data[row][col] if col < len(current_data[row]) else ""  # El que ESTÁ cubierto
                
                # ⭐ OBTENER HEADERS DEL BREAKS_SHEET DIRECTAMENTE (no usar variable 'headers' que puede ser de otra tabla)
                breaks_headers = breaks_sheet.headers()
                usuario_cubre_actual = breaks_headers[col]  # El header es el usuario que HACE el cover
                
                # Si la celda está vacía, no permitir edición
                if not usuario_cubierto_actual or usuario_cubierto_actual.strip() == "":
                    messagebox.showinfo("Información", 
                                      "No hay cover asignado en esta celda.\n\nUsa el botón 'Añadir' para crear un nuevo cover.",
                                      parent=top)
                    return
                
                # Crear ventana de edición
                if UI is not None:
                    edit_win = UI.CTkToplevel(top)
                    edit_win.title("Editar Cover")
                    edit_win.geometry("500x400")
                    edit_win.configure(fg_color="#2c2f33")
                else:
                    edit_win = tk.Toplevel(top)
                    edit_win.title("Editar Cover")
                    edit_win.geometry("500x400")
                    edit_win.configure(bg="#2c2f33")
                
                edit_win.transient(top)
                edit_win.grab_set()
                
                # Frame principal
                if UI is not None:
                    main_frame = UI.CTkFrame(edit_win, fg_color="#23272a", corner_radius=10)
                else:
                    main_frame = tk.Frame(edit_win, bg="#23272a")
                main_frame.pack(fill="both", expand=True, padx=20, pady=20)
                
                # Título
                if UI is not None:
                    UI.CTkLabel(main_frame, text="✏️ Editar Cover de Break", 
                               font=("Segoe UI", 20, "bold"),
                               text_color="#ffffff").pack(pady=(10, 20))
                else:
                    tk.Label(main_frame, text="✏️ Editar Cover de Break", 
                            font=("Segoe UI", 20, "bold"),
                            bg="#23272a", fg="#ffffff").pack(pady=(10, 20))
                
                # Información del cover con mejor formato
                if UI is not None:
                    info_frame = UI.CTkFrame(main_frame, fg_color="#2c2f33", corner_radius=8)
                else:
                    info_frame = tk.Frame(main_frame, bg="#2c2f33")
                info_frame.pack(fill="x", padx=10, pady=10)
                
                # Fila 1: Hora
                hora_row = tk.Frame(info_frame, bg="#2c2f33")
                hora_row.pack(fill="x", padx=15, pady=8)
                if UI is not None:
                    UI.CTkLabel(hora_row, text="🕐 Hora:", 
                               font=("Segoe UI", 13, "bold"),
                               text_color="#99aab5", width=150).pack(side="left")
                    UI.CTkLabel(hora_row, text=hora_actual, 
                               font=("Segoe UI", 13),
                               text_color="#ffffff").pack(side="left")
                else:
                    tk.Label(hora_row, text="🕐 Hora:", 
                            font=("Segoe UI", 13, "bold"),
                            bg="#2c2f33", fg="#99aab5", width=15, anchor="w").pack(side="left")
                    tk.Label(hora_row, text=hora_actual, 
                            font=("Segoe UI", 13),
                            bg="#2c2f33", fg="#ffffff").pack(side="left")
                
                # Fila 2: Usuario que hace el cover
                covering_row = tk.Frame(info_frame, bg="#2c2f33")
                covering_row.pack(fill="x", padx=15, pady=8)
                if UI is not None:
                    UI.CTkLabel(covering_row, text="👤 Usuario que cubre:", 
                               font=("Segoe UI", 13, "bold"),
                               text_color="#99aab5", width=150).pack(side="left")
                    UI.CTkLabel(covering_row, text=usuario_cubre_actual, 
                               font=("Segoe UI", 13),
                               text_color="#4aa3ff").pack(side="left")
                else:
                    tk.Label(covering_row, text="👤 Usuario que cubre:", 
                            font=("Segoe UI", 13, "bold"),
                            bg="#2c2f33", fg="#99aab5", width=15, anchor="w").pack(side="left")
                    tk.Label(covering_row, text=usuario_cubre_actual, 
                            font=("Segoe UI", 13),
                            bg="#2c2f33", fg="#4aa3ff").pack(side="left")
                
                # Fila 3: Usuario cubierto actual
                actual_row = tk.Frame(info_frame, bg="#2c2f33")
                actual_row.pack(fill="x", padx=15, pady=8)
                if UI is not None:
                    UI.CTkLabel(actual_row, text="📋 Usuario cubierto:", 
                               font=("Segoe UI", 13, "bold"),
                               text_color="#99aab5", width=150).pack(side="left")
                    UI.CTkLabel(actual_row, text=usuario_cubierto_actual, 
                               font=("Segoe UI", 13, "bold"),
                               text_color="#7289da").pack(side="left")
                else:
                    tk.Label(actual_row, text="📋 Usuario cubierto:", 
                            font=("Segoe UI", 13, "bold"),
                            bg="#2c2f33", fg="#99aab5", width=15, anchor="w").pack(side="left")
                    tk.Label(actual_row, text=usuario_cubierto_actual, 
                            font=("Segoe UI", 13, "bold"),
                            bg="#2c2f33", fg="#7289da").pack(side="left")
                
                # Selector de nuevo usuario cubierto
                if UI is not None:
                    UI.CTkLabel(main_frame, text="➡️ Cambiar a (nuevo usuario cubierto):", 
                               font=("Segoe UI", 13, "bold"),
                               text_color="#ffffff").pack(anchor="w", padx=10, pady=(15, 5))
                else:
                    tk.Label(main_frame, text="➡️ Cambiar a (nuevo usuario cubierto):", 
                            font=("Segoe UI", 13, "bold"),
                            bg="#23272a", fg="#ffffff").pack(anchor="w", padx=10, pady=(15, 5))
                
                # Obtener lista de usuarios
                usuarios_disponibles = []
                try:
                    conn = get_connection()
                    cur = conn.cursor()
                    cur.execute("SELECT Nombre_Usuario FROM user ORDER BY Nombre_Usuario")
                    usuarios_disponibles = [row[0] for row in cur.fetchall()]
                    cur.close()
                    conn.close()
                except Exception as e:
                    print(f"[ERROR] No se pudieron cargar usuarios: {e}")
                
                nuevo_usuario_cubierto_var = tk.StringVar(value=usuario_cubierto_actual)
                
                # Usar FilteredCombobox para mejor búsqueda
                usuario_combo = under_super.FilteredCombobox(
                    main_frame,
                    textvariable=nuevo_usuario_cubierto_var,
                    values=usuarios_disponibles,
                    width=35,
                    font=("Segoe UI", 12),
                    bordercolor="#5ab4ff",
                    borderwidth=2,
                    background="#2b2b2b",
                    foreground="#ffffff",
                    fieldbackground="#2b2b2b"
                )
                usuario_combo.pack(padx=10, pady=5, fill="x")
                
                # Función para guardar cambios
                def guardar_cambios():
                    nuevo_usuario_cubierto = nuevo_usuario_cubierto_var.get().strip()
                    if not nuevo_usuario_cubierto:
                        messagebox.showwarning("Advertencia", "Debe seleccionar un usuario", parent=edit_win)
                        return
                    
                    # Llamar a la función de under_super para actualizar el cover
                    # Parámetros: supervisor, hora, quien_cubre, usuario_cubierto_anterior, nuevo_usuario_cubierto
                    exito = under_super.actualizar_cover_breaks(
                        username=username,
                        hora_actual=hora_actual,
                        covered_by_actual=usuario_cubre_actual,
                        usuario_actual=usuario_cubierto_actual,
                        nuevo_usuario=nuevo_usuario_cubierto
                    )
                    
                    if exito:
                        edit_win.destroy()
                        refrescar_tabla_breaks()
                    else:
                        messagebox.showerror("Error", "No se pudo actualizar el cover", parent=edit_win)
                
                # Botones
                if UI is not None:
                    buttons_frame = UI.CTkFrame(main_frame, fg_color="transparent")
                else:
                    buttons_frame = tk.Frame(main_frame, bg="#23272a")
                buttons_frame.pack(pady=20)
                
                if UI is not None:
                    UI.CTkButton(buttons_frame, text="💾 Guardar", 
                                command=guardar_cambios,
                                fg_color="#43b581",
                                hover_color="#3ca374",
                                width=120,
                                font=("Segoe UI", 12, "bold")).pack(side="left", padx=5)
                    UI.CTkButton(buttons_frame, text="❌ Cancelar", 
                                command=edit_win.destroy,
                                fg_color="#f04747",
                                hover_color="#d84040",
                                width=120,
                                font=("Segoe UI", 12, "bold")).pack(side="left", padx=5)
                else:
                    tk.Button(buttons_frame, text="💾 Guardar", 
                             command=guardar_cambios,
                             bg="#43b581",
                             fg="white",
                             font=("Segoe UI", 12, "bold"),
                             width=12).pack(side="left", padx=5)
                    tk.Button(buttons_frame, text="❌ Cancelar", 
                             command=edit_win.destroy,
                             bg="#f04747",
                             fg="white",
                             font=("Segoe UI", 12, "bold"),
                             width=12).pack(side="left", padx=5)
                
            except Exception as e:
                print(f"[ERROR] editar_celda_breaks: {e}")
                traceback.print_exc()
                messagebox.showerror("Error", f"Error al editar celda: {e}")
        
        # Vincular evento de doble clic
        breaks_sheet.bind("<Double-Button-1>", editar_celda_breaks)
        
    else:
        if UI is not None:
            UI.CTkLabel(breaks_sheet_frame, text="⚠️ tksheet no instalado", 
                       text_color="#ff6b6b", font=("Segoe UI", 16)).pack(pady=20)
        else:
            tk.Label(breaks_sheet_frame, text="⚠️ tksheet no instalado", 
                    bg="#2c2f33", fg="#ff6b6b", font=("Segoe UI", 16)).pack(pady=20)

    # ==================== NEWS CONTAINER ====================
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
    # ==================== ADMIN CONTAINER ====================
    
    if UI is not None:
        admin_container = UI.CTkFrame(top, fg_color="#2c2f33")
    else:
        admin_container = tk.Frame(top, bg="#2c2f33")
    # No hacer pack aquí, se hace en switch_view()
    
    # Frame superior para selección de tabla
    if UI is not None:
        admin_toolbar = UI.CTkFrame(admin_container, fg_color="#23272a", corner_radius=0, height=100)
    else:
        admin_toolbar = tk.Frame(admin_container, bg="#23272a", height=100)
    admin_toolbar.pack(fill="x", padx=0, pady=0)
    admin_toolbar.pack_propagate(False)
    
    if UI is not None:
        UI.CTkLabel(admin_toolbar, text="🔧 Administración de Base de Datos", 
                   font=("Segoe UI", 14, "bold"), text_color="#e0e0e0").pack(side="top", padx=20, pady=(10, 5))
    else:
        tk.Label(admin_toolbar, text="🔧 Administración de Base de Datos", 
                bg="#23272a", fg="#e0e0e0", font=("Segoe UI", 14, "bold")).pack(side="top", padx=20, pady=(10, 5))
    
    # Frame para controles
    if UI is not None:
        admin_controls = UI.CTkFrame(admin_toolbar, fg_color="transparent")
    else:
        admin_controls = tk.Frame(admin_toolbar, bg="#23272a")
    admin_controls.pack(fill="x", padx=20, pady=5)
    
    # Variable y selector de tabla
    admin_table_var = tk.StringVar()
    admin_tables_list = ["Sitios", "user", "Actividades", "gestion_breaks_programados", "Covers_realizados", "Covers_programados", "sesion", "Estaciones", "Specials", "eventos"]
    
    # Variables de filtro de fechas
    admin_fecha_desde_var = tk.StringVar()
    admin_fecha_hasta_var = tk.StringVar()
    admin_columna_fecha_var = tk.StringVar()
    admin_tipo_evento_var = tk.StringVar()  # Nuevo: filtro de tipo de evento
    
    if UI is not None:
        UI.CTkLabel(admin_controls, text="Tabla:", text_color="#e0e0e0").pack(side="left", padx=5)
        admin_table_cb = UI.CTkComboBox(
            admin_controls, variable=admin_table_var, values=admin_tables_list,
            font=("Segoe UI", 10), width=200
        )
        admin_table_cb.pack(side="left", padx=5)
        
        # Combobox para tipo de evento (solo visible para tabla 'eventos')
        admin_tipo_evento_label = UI.CTkLabel(admin_controls, text="Tipo Evento:", text_color="#e0e0e0")
        admin_tipo_evento_cb = UI.CTkComboBox(
            admin_controls, variable=admin_tipo_evento_var,
            values=["Todos", "Start Shift", "End of Shift"],
            font=("Segoe UI", 10), width=150
        )
        admin_tipo_evento_var.set("Todos")
        
        UI.CTkLabel(admin_controls, text="Columna Fecha:", text_color="#e0e0e0").pack(side="left", padx=(15, 5))
        admin_columna_fecha_cb = UI.CTkComboBox(
            admin_controls, variable=admin_columna_fecha_var, values=["Auto"],
            font=("Segoe UI", 10), width=150
        )
        admin_columna_fecha_cb.pack(side="left", padx=5)
        
        UI.CTkLabel(admin_controls, text="Desde:", text_color="#e0e0e0").pack(side="left", padx=(15, 5))
        admin_fecha_desde_frame = tk.Frame(admin_controls, bg="#23272a")
        admin_fecha_desde_frame.pack(side="left", padx=5)
        if tkcalendar:
            admin_fecha_desde_entry = tkcalendar.DateEntry(
                admin_fecha_desde_frame, textvariable=admin_fecha_desde_var,
                date_pattern='yyyy-mm-dd', width=12
            )
            admin_fecha_desde_entry.pack()
        else:
            tk.Entry(admin_fecha_desde_frame, textvariable=admin_fecha_desde_var, width=12).pack()
        
        UI.CTkLabel(admin_controls, text="Hasta:", text_color="#e0e0e0").pack(side="left", padx=(15, 5))
        admin_fecha_hasta_frame = tk.Frame(admin_controls, bg="#23272a")
        admin_fecha_hasta_frame.pack(side="left", padx=5)
        if tkcalendar:
            admin_fecha_hasta_entry = tkcalendar.DateEntry(
                admin_fecha_hasta_frame, textvariable=admin_fecha_hasta_var,
                date_pattern='yyyy-mm-dd', width=12
            )
            admin_fecha_hasta_entry.pack()
        else:
            tk.Entry(admin_fecha_hasta_frame, textvariable=admin_fecha_hasta_var, width=12).pack()
    else:
        tk.Label(admin_controls, text="Tabla:", bg="#23272a", fg="#e0e0e0").pack(side="left", padx=5)
        admin_table_cb = under_super.FilteredCombobox(
            admin_controls, textvariable=admin_table_var, values=admin_tables_list,
            font=("Segoe UI", 10), width=25,
            background='#2b2b2b', foreground='#ffffff',
            bordercolor='#4a90e2', arrowcolor='#ffffff'
        )
        admin_table_cb.pack(side="left", padx=5)
        
        # Combobox para tipo de evento (solo visible para tabla 'eventos')
        admin_tipo_evento_label = tk.Label(admin_controls, text="Tipo Evento:", bg="#23272a", fg="#e0e0e0")
        admin_tipo_evento_cb = under_super.FilteredCombobox(
            admin_controls, textvariable=admin_tipo_evento_var,
            values=["Todos", "Start Shift", "End of Shift"],
            font=("Segoe UI", 10), width=20,
            background='#2b2b2b', foreground='#ffffff',
            bordercolor='#4a90e2', arrowcolor='#ffffff'
        )
        admin_tipo_evento_var.set("Todos")
        
        tk.Label(admin_controls, text="Columna Fecha:", bg="#23272a", fg="#e0e0e0").pack(side="left", padx=(15, 5))
        admin_columna_fecha_cb = under_super.FilteredCombobox(
            admin_controls, textvariable=admin_columna_fecha_var, values=["Auto"],
            font=("Segoe UI", 10), width=20,
            background='#2b2b2b', foreground='#ffffff',
            bordercolor='#4a90e2', arrowcolor='#ffffff'
        )
        admin_columna_fecha_cb.pack(side="left", padx=5)
        
        tk.Label(admin_controls, text="Desde:", bg="#23272a", fg="#e0e0e0").pack(side="left", padx=(15, 5))
        if tkcalendar:
            admin_fecha_desde_entry = tkcalendar.DateEntry(
                admin_controls, textvariable=admin_fecha_desde_var,
                date_pattern='yyyy-mm-dd', width=12
            )
            admin_fecha_desde_entry.pack(side="left", padx=5)
        else:
            tk.Entry(admin_controls, textvariable=admin_fecha_desde_var, width=12).pack(side="left", padx=5)
        
        tk.Label(admin_controls, text="Hasta:", bg="#23272a", fg="#e0e0e0").pack(side="left", padx=(15, 5))
        if tkcalendar:
            admin_fecha_hasta_entry = tkcalendar.DateEntry(
                admin_controls, textvariable=admin_fecha_hasta_var,
                date_pattern='yyyy-mm-dd', width=12
            )
            admin_fecha_hasta_entry.pack(side="left", padx=5)
        else:
            tk.Entry(admin_controls, textvariable=admin_fecha_hasta_var, width=12).pack(side="left", padx=5)
    
    # Metadata de tablas cargadas
    admin_metadata = {
        'current_table': None,
        'col_names': [],
        'pk': None,
        'rows': []
    }
    
    # Funciones auxiliares para Admin
    def sanitize_col_id(name, used):
        cid = re.sub(r'[^0-9A-Za-z_]', '_', str(name))
        if re.match(r'^\d', cid):
            cid = "_" + cid
        base = cid
        i = 1
        while cid in used or cid == "":
            cid = f"{base}_{i}"
            i += 1
        used.add(cid)
        return cid
    
    def guess_pk(col_names):
        candidates = [c for c in col_names if c.lower() in ("id", "id_") or c.lower().endswith("_id") or c.lower().startswith("id_")]
        if candidates:
            return candidates[0]
        for c in col_names:
            if 'id' in c.lower():
                return c
        return col_names[0] if col_names else None
    
    def load_admin_table():
        """Carga la tabla seleccionada en el tksheet de admin con filtros de fecha"""
        tabla = admin_table_var.get()
        if not tabla:
            messagebox.showwarning("Atención", "Seleccione una tabla para cargar.", parent=top)
            return
        
        # Mostrar/ocultar combobox de tipo de evento según la tabla
        if tabla == "eventos":
            admin_tipo_evento_label.pack(side="left", padx=(15, 5))
            admin_tipo_evento_cb.pack(side="left", padx=5)
        else:
            admin_tipo_evento_label.pack_forget()
            admin_tipo_evento_cb.pack_forget()
        
        try:
            conn = get_connection()
            cursor = conn.cursor()
            
            # ⭐ Para tabla eventos, usar JOIN para mostrar nombres de usuario
            if tabla == "eventos":
                # Primero obtener columnas ORIGINALES de la tabla (sin JOIN) para edición
                cursor.execute(f"SELECT * FROM `{tabla}` LIMIT 0")
                col_names_original = [desc[0] for desc in cursor.description]
                
                # Obtener columnas con JOIN para MOSTRAR
                cursor.execute("""
                    SELECT e.ID_Eventos, e.FechaHora, e.ID_Sitio, e.Nombre_Actividad, 
                           e.Cantidad, e.Camera, e.Descripcion, e.ID_Usuario, u.Nombre_Usuario
                    FROM Eventos e
                    INNER JOIN user u ON e.ID_Usuario = u.ID_Usuario
                    LIMIT 0
                """)
                col_names = [desc[0] for desc in cursor.description]
                
                # Detectar columnas de fecha
                fecha_cols = [col for col in col_names if any(keyword in col.lower() for keyword in 
                             ['fecha', 'date', 'log_in', 'log_out', 'hora', 'time', 'timestamp', 'created', 'updated'])]
                
                # Actualizar combobox de columnas de fecha
                if fecha_cols:
                    fecha_options = ["Auto"] + fecha_cols
                    if UI is not None:
                        admin_columna_fecha_cb.configure(values=fecha_options)
                    else:
                        admin_columna_fecha_cb['values'] = fecha_options
                
                # Construir query con JOIN (incluir ID_Usuario para edición)
                query = """
                    SELECT e.ID_Eventos, e.FechaHora, e.ID_Sitio, e.Nombre_Actividad, 
                           e.Cantidad, e.Camera, e.Descripcion, e.ID_Usuario, u.Nombre_Usuario
                    FROM Eventos e
                    INNER JOIN user u ON e.ID_Usuario = u.ID_Usuario
                """
                where_clauses = []
                params = []
                
                fecha_desde = admin_fecha_desde_var.get()
                fecha_hasta = admin_fecha_hasta_var.get()
                columna_fecha = admin_columna_fecha_var.get()
                
                if (fecha_desde or fecha_hasta) and fecha_cols:
                    if not columna_fecha or columna_fecha == "Auto":
                        columna_fecha = fecha_cols[0]
                    
                    if columna_fecha in col_names:
                        if fecha_desde:
                            where_clauses.append(f"DATE(e.{columna_fecha}) >= %s")
                            params.append(fecha_desde)
                        if fecha_hasta:
                            where_clauses.append(f"DATE(e.{columna_fecha}) <= %s")
                            params.append(fecha_hasta)
                
                # Filtro de tipo de evento
                tipo_evento = admin_tipo_evento_var.get()
                if tipo_evento and tipo_evento != "Todos":
                    where_clauses.append("e.Nombre_Actividad = %s")
                    params.append(tipo_evento)
                
                if where_clauses:
                    query += " WHERE " + " AND ".join(where_clauses)
                
                query += " ORDER BY e.ID_Eventos DESC LIMIT 1000"
                
            elif tabla == "gestion_breaks_programados":
                # Para gestion_breaks_programados, obtener columnas originales
                cursor.execute(f"SELECT * FROM `{tabla}` LIMIT 0")
                col_names_original = [desc[0] for desc in cursor.description]
                
                # Obtener columnas con JOINs para MOSTRAR nombres de usuario (sin IDs)
                cursor.execute("""
                    SELECT gbp.ID_cover, 
                           uc.Nombre_Usuario as User_covering, 
                           uv.Nombre_Usuario as User_covered,
                           gbp.Fecha_hora_cover, gbp.is_Active,
                           us.Nombre_Usuario as Supervisor,
                           gbp.Fecha_creacion
                    FROM gestion_breaks_programados gbp
                    LEFT JOIN user uc ON gbp.User_covering = uc.ID_Usuario
                    LEFT JOIN user uv ON gbp.User_covered = uv.ID_Usuario
                    LEFT JOIN user us ON gbp.Supervisor = us.ID_Usuario
                    LIMIT 0
                """)
                col_names = [desc[0] for desc in cursor.description]
                
                # Detectar columnas de fecha
                fecha_cols = [col for col in col_names if any(keyword in col.lower() for keyword in 
                             ['fecha', 'date', 'hora', 'time', 'timestamp', 'created', 'updated'])]
                
                # Actualizar combobox de columnas de fecha
                if fecha_cols:
                    fecha_options = ["Auto"] + fecha_cols
                    if UI is not None:
                        admin_columna_fecha_cb.configure(values=fecha_options)
                    else:
                        admin_columna_fecha_cb['values'] = fecha_options
                
                # Query con JOINs para mostrar nombres (sin columnas de IDs)
                query = """
                    SELECT gbp.ID_cover, 
                           uc.Nombre_Usuario as User_covering, 
                           uv.Nombre_Usuario as User_covered,
                           gbp.Fecha_hora_cover, gbp.is_Active,
                           us.Nombre_Usuario as Supervisor,
                           gbp.Fecha_creacion
                    FROM gestion_breaks_programados gbp
                    LEFT JOIN user uc ON gbp.User_covering = uc.ID_Usuario
                    LEFT JOIN user uv ON gbp.User_covered = uv.ID_Usuario
                    LEFT JOIN user us ON gbp.Supervisor = us.ID_Usuario
                """
                where_clauses = []
                params = []
                
                fecha_desde = admin_fecha_desde_var.get()
                fecha_hasta = admin_fecha_hasta_var.get()
                columna_fecha = admin_columna_fecha_var.get()
                
                if (fecha_desde or fecha_hasta) and fecha_cols:
                    if not columna_fecha or columna_fecha == "Auto":
                        columna_fecha = fecha_cols[0]
                    
                    if columna_fecha in col_names:
                        if fecha_desde:
                            where_clauses.append(f"DATE(gbp.{columna_fecha}) >= %s")
                            params.append(fecha_desde)
                        if fecha_hasta:
                            where_clauses.append(f"DATE(gbp.{columna_fecha}) <= %s")
                            params.append(fecha_hasta)
                
                if where_clauses:
                    query += " WHERE " + " AND ".join(where_clauses)
                
                query += " ORDER BY gbp.ID_cover DESC LIMIT 1000"
                
            elif tabla == "Covers_realizados":
                # Para Covers_realizados, obtener columnas originales
                cursor.execute(f"SELECT * FROM `{tabla}` LIMIT 0")
                col_names_original = [desc[0] for desc in cursor.description]
                col_names = col_names_original  # Por ahora sin JOIN, solo columnas originales
                
                # Detectar columnas de fecha
                fecha_cols = [col for col in col_names if any(keyword in col.lower() for keyword in 
                             ['fecha', 'date', 'log_in', 'log_out', 'hora', 'time', 'timestamp', 'created', 'updated', 'cover_in', 'cover_out'])]
                
                # Actualizar combobox de columnas de fecha
                if fecha_cols:
                    fecha_options = ["Auto"] + fecha_cols
                    if UI is not None:
                        admin_columna_fecha_cb.configure(values=fecha_options)
                    else:
                        admin_columna_fecha_cb['values'] = fecha_options
                
                # Query normal para Covers_realizados
                query = f"SELECT * FROM `{tabla}`"
                where_clauses = []
                params = []
                
                fecha_desde = admin_fecha_desde_var.get()
                fecha_hasta = admin_fecha_hasta_var.get()
                columna_fecha = admin_columna_fecha_var.get()
                
                if (fecha_desde or fecha_hasta) and fecha_cols:
                    if not columna_fecha or columna_fecha == "Auto":
                        columna_fecha = fecha_cols[0]
                    
                    if columna_fecha in col_names:
                        if fecha_desde:
                            where_clauses.append(f"DATE({columna_fecha}) >= %s")
                            params.append(fecha_desde)
                        if fecha_hasta:
                            where_clauses.append(f"DATE({columna_fecha}) <= %s")
                            params.append(fecha_hasta)
                
                if where_clauses:
                    query += " WHERE " + " AND ".join(where_clauses)
                
                query += f" ORDER BY {col_names[0]} DESC LIMIT 1000"
                
            else:
                # Para otras tablas, query normal
                cursor.execute(f"SELECT * FROM {tabla} LIMIT 0")
                col_names = [desc[0] for desc in cursor.description]
                col_names_original = col_names  # Para otras tablas son las mismas
                
                # Detectar columnas de fecha automáticamente
                fecha_cols = [col for col in col_names if any(keyword in col.lower() for keyword in 
                             ['fecha', 'date', 'log_in', 'log_out', 'hora', 'time', 'timestamp', 'created', 'updated'])]
                
                # Actualizar combobox de columnas de fecha
                if fecha_cols:
                    fecha_options = ["Auto"] + fecha_cols
                    if UI is not None:
                        admin_columna_fecha_cb.configure(values=fecha_options)
                    else:
                        admin_columna_fecha_cb['values'] = fecha_options
                
                # Construir query con filtros de fecha
                query = f"SELECT * FROM {tabla}"
                where_clauses = []
                params = []
                
                fecha_desde = admin_fecha_desde_var.get()
                fecha_hasta = admin_fecha_hasta_var.get()
                columna_fecha = admin_columna_fecha_var.get()
                
                if (fecha_desde or fecha_hasta) and fecha_cols:
                    # Si columna_fecha es "Auto" o vacío, usar la primera columna de fecha detectada
                    if not columna_fecha or columna_fecha == "Auto":
                        columna_fecha = fecha_cols[0]
                    
                    if columna_fecha in col_names:
                        if fecha_desde:
                            where_clauses.append(f"DATE({columna_fecha}) >= %s")
                            params.append(fecha_desde)
                        if fecha_hasta:
                            where_clauses.append(f"DATE({columna_fecha}) <= %s")
                            params.append(fecha_hasta)
                
                if where_clauses:
                    query += " WHERE " + " AND ".join(where_clauses)
                
                query += f" ORDER BY {col_names[0]} DESC LIMIT 1000"  # Limitar a 1000 registros
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            # Formatear datos para tksheet
            data = []
            for row in rows:
                row_data = []
                for v in row:
                    if v is None:
                        row_data.append("")
                    else:
                        try:
                            if isinstance(v, (bytes, bytearray, memoryview)):
                                row_data.append(v.hex())
                            else:
                                row_data.append(str(v))
                        except Exception:
                            row_data.append(repr(v))
                data.append(row_data)
            
            # Actualizar metadata
            admin_metadata['current_table'] = tabla
            admin_metadata['col_names'] = col_names
            admin_metadata['col_names_original'] = col_names_original  # Columnas para edición
            admin_metadata['pk'] = guess_pk(col_names_original)  # PK de tabla original
            admin_metadata['rows'] = rows
            admin_metadata['fecha_cols'] = fecha_cols
            
            # Configurar tksheet
            admin_sheet.set_sheet_data(data if data else [["No hay datos"] + [""] * (len(col_names)-1)])
            admin_sheet.headers(col_names)
            
            # Ajustar anchos de columna
            for col_idx in range(len(col_names)):
                admin_sheet.column_width(column=col_idx, width=150)
            
            admin_sheet.refresh()
            
            cursor.close()
            conn.close()
            
            filtro_msg = ""
            if where_clauses:
                filtro_msg = f" (filtrado: {len(data)} registros)"
            print(f"[INFO] Tabla {tabla} cargada: {len(data)} registros{filtro_msg}")
            
        except Exception as e:
            print(f"[ERROR] load_admin_table: {e}")
            traceback.print_exc()
            messagebox.showerror("Error", f"Error al cargar tabla:\n{e}", parent=top)
    
    def delete_admin_selected():
        """Elimina el registro seleccionado (usando sistema de papelera)"""
        tabla = admin_metadata['current_table']
        if not tabla:
            messagebox.showwarning("Atención", "Primero cargue una tabla.", parent=top)
            return
        
        selected = admin_sheet.get_selected_rows()
        if not selected:
            messagebox.showwarning("Atención", "Seleccione un registro para eliminar.", parent=top)
            return
        
        # Convertir a lista si es un set
        if isinstance(selected, set):
            selected = list(selected)
        
        pk_name = admin_metadata.get('pk')
        col_names = admin_metadata.get('col_names', [])
        if not pk_name or pk_name not in col_names:
            messagebox.showwarning("No PK", "No se pudo determinar la columna primaria.", parent=top)
            return
        
        if not messagebox.askyesno("Confirmar", "¿Mover el registro a Papelera?", parent=top):
            return
        
        try:
            pk_idx = col_names.index(pk_name)
            row_idx = selected[0]
            row_data = admin_sheet.get_row_data(row_idx)
            
            # Convertir a lista si es un set
            if isinstance(row_data, set):
                row_data = list(row_data)
            
            pk_value = row_data[pk_idx] if row_data and pk_idx < len(row_data) else None
            
            if pk_value is None:
                messagebox.showerror("Error", "No se pudo leer el valor de la PK.", parent=top)
                return
            
            ok = safe_delete(
                table_name=tabla,
                pk_column=pk_name,
                pk_value=pk_value,
                deleted_by=username,
                reason=f"Eliminado desde Admin ({tabla})"
            )
            
            if ok:
                load_admin_table()
                messagebox.showinfo("Éxito", "✅ Registro movido a Papelera.", parent=top)
            else:
                messagebox.showerror("Error", "No se pudo mover el registro a Papelera", parent=top)
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo eliminar:\n{e}", parent=top)
            traceback.print_exc()
    
    def edit_admin_selected():
        """Edita el registro seleccionado"""
        tabla = admin_metadata['current_table']
        if not tabla:
            messagebox.showwarning("Atención", "Primero cargue una tabla.", parent=top)
            return
        
        selected = admin_sheet.get_selected_rows()
        if not selected:
            messagebox.showwarning("Atención", "Seleccione un registro para editar.", parent=top)
            return
        
        # Convertir a lista si es un set
        if isinstance(selected, set):
            selected = list(selected)
        
        # Usar columnas ORIGINALES para editar (sin JOIN)
        col_names_display = admin_metadata.get('col_names', [])
        col_names_original = admin_metadata.get('col_names_original', col_names_display)
        pk_name = admin_metadata.get('pk')
        
        if not pk_name or pk_name not in col_names_original:
            messagebox.showwarning("No PK", "No se pudo determinar la columna primaria.", parent=top)
            return
        
        pk_idx = col_names_display.index(pk_name)
        row_idx = selected[0]
        row_data = admin_sheet.get_row_data(row_idx)
        
        # Convertir a lista si es un set
        if isinstance(row_data, set):
            row_data = list(row_data)
        
        if not row_data or pk_idx >= len(row_data):
            messagebox.showerror("Error", "No se pudo leer el registro.", parent=top)
            return
        pk_value = row_data[pk_idx]
        
        # Para eventos, Covers_realizados y gestion_breaks_programados, necesitamos recargar el registro con las columnas originales
        if tabla in ["eventos", "Covers_realizados", "gestion_breaks_programados"]:
            try:
                conn = get_connection()
                cur = conn.cursor()
                cur.execute(f"SELECT * FROM `{tabla}` WHERE `{pk_name}` = %s", (pk_value,))
                original_row = cur.fetchone()
                cur.close()
                conn.close()
                if original_row:
                    row_data = [str(v) if v is not None else "" for v in original_row]
                else:
                    messagebox.showerror("Error", "No se pudo cargar el registro.", parent=top)
                    return
            except Exception as e:
                messagebox.showerror("Error", f"Error al cargar registro:\n{e}", parent=top)
                traceback.print_exc()
                return
        
        # Ventana de edición con CustomTkinter
        if UI is not None:
            edit_win = UI.CTkToplevel(top)
            edit_win.configure(fg_color="#2c2f33")
        else:
            edit_win = tk.Toplevel(top)
            edit_win.configure(bg="#2c2f33")
        
        edit_win.title(f"Editar registro de {tabla}")
        win_height = min(130 + 60 * len(col_names_original), 850)
        edit_win.geometry(f"550x{win_height}")
        edit_win.resizable(False, False)
        
        # Título
        if UI is not None:
            UI.CTkLabel(edit_win, text=f"✏️ Editar: {tabla}", 
                       font=("Segoe UI", 14, "bold"), text_color="#e0e0e0").pack(pady=(10, 20))
        else:
            tk.Label(edit_win, text=f"✏️ Editar: {tabla}", 
                    bg="#2c2f33", fg="#e0e0e0", font=("Segoe UI", 14, "bold")).pack(pady=(10, 20))
        
        # Frame inferior para botón (crear PRIMERO para que aparezca al fondo)
        if UI is not None:
            button_frame = UI.CTkFrame(edit_win, fg_color="#2c2f33")
            button_frame.pack(side="bottom", fill="x", pady=(10, 15))
        else:
            button_frame = tk.Frame(edit_win, bg="#2c2f33")
            button_frame.pack(side="bottom", fill="x", pady=(10, 15))
        
        # Frame scrollable para campos
        if UI is not None:
            fields_container = UI.CTkScrollableFrame(edit_win, fg_color="transparent")
            fields_container.pack(fill="both", expand=True, padx=20, pady=(0, 10))
            fields_frame = fields_container
        else:
            canvas = tk.Canvas(edit_win, bg="#2c2f33", highlightthickness=0)
            scrollbar = tk.Scrollbar(edit_win, orient="vertical", command=canvas.yview)
            fields_frame = tk.Frame(canvas, bg="#2c2f33")
            canvas.configure(yscrollcommand=scrollbar.set)
            canvas.pack(side="left", fill="both", expand=True, padx=20)
            scrollbar.pack(side="right", fill="y")
            canvas.create_window((0, 0), window=fields_frame, anchor="nw")
            fields_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        
        # Para gestion_breaks_programados, cargar lista de usuarios y crear mapeo ID->Nombre
        users_list = []
        id_to_name = {}
        if tabla == "gestion_breaks_programados":
            try:
                conn_users = get_connection()
                cur_users = conn_users.cursor()
                cur_users.execute("SELECT ID_Usuario, Nombre_Usuario FROM user ORDER BY Nombre_Usuario")
                for id_user, nombre in cur_users.fetchall():
                    users_list.append(nombre)
                    id_to_name[str(id_user)] = nombre  # Mapeo ID -> Nombre
                cur_users.close()
                conn_users.close()
            except Exception as e:
                print(f"[WARN] No se pudieron cargar usuarios: {e}")
        
        entries = {}
        for i, cname in enumerate(col_names_original):
            if UI is not None:
                UI.CTkLabel(fields_frame, text=f"{cname}:", text_color="#a3c9f9", 
                           font=("Segoe UI", 12, "bold")).grid(row=i, column=0, sticky="w", padx=10, pady=8)
            else:
                tk.Label(fields_frame, text=f"{cname}:", bg="#2c2f33", fg="#a3c9f9", 
                        font=("Segoe UI", 12, "bold")).grid(row=i, column=0, sticky="w", padx=10, pady=8)
            
            # Para gestion_breaks_programados, usar comboboxes para campos de usuario
            if tabla == "gestion_breaks_programados" and cname in ["User_covering", "User_covered", "Supervisor"]:
                var = tk.StringVar()
                cb = ttk.Combobox(fields_frame, textvariable=var, values=users_list, 
                                 width=35, font=("Segoe UI", 11), state="readonly")
                cb.grid(row=i, column=1, padx=10, pady=8, sticky="ew")
                # Convertir ID a Nombre para mostrar en el combobox
                if i < len(row_data):
                    id_value = str(row_data[i])
                    nombre_usuario = id_to_name.get(id_value, id_value)  # Si no existe, mostrar el ID
                    var.set(nombre_usuario)
                entries[cname] = var  # Guardar la variable, no el combobox
            else:
                # Campo normal (Entry)
                if UI is not None:
                    e = UI.CTkEntry(fields_frame, width=280, font=("Segoe UI", 12))
                    e.grid(row=i, column=1, padx=10, pady=8)
                else:
                    e = tk.Entry(fields_frame, width=38, font=("Segoe UI", 12))
                    e.grid(row=i, column=1, padx=10, pady=8)
                
                if i < len(row_data):
                    e.insert(0, row_data[i])
                
                # PK de solo lectura
                if cname == pk_name:
                    if UI is not None:
                        e.configure(state="disabled")
                    else:
                        e.config(state="readonly")
                
                entries[cname] = e
        
        def save_changes():
            new_values = {}
            for c in col_names_original:
                try:
                    # Para campos deshabilitados, usar el valor original
                    if c == pk_name:
                        new_values[c] = pk_value
                    else:
                        # Obtener valor del Entry o StringVar (combobox)
                        widget = entries[c]
                        if isinstance(widget, tk.StringVar):
                            new_values[c] = widget.get()
                        else:
                            new_values[c] = widget.get()
                except:
                    new_values[c] = ""
            
            try:
                conn = get_connection()
                cur = conn.cursor()
                
                # Para gestion_breaks_programados, convertir nombres de usuario a IDs
                if tabla == "gestion_breaks_programados":
                    for field in ["User_covering", "User_covered", "Supervisor"]:
                        if field in new_values and new_values[field]:
                            username = new_values[field]
                            cur.execute("SELECT ID_Usuario FROM user WHERE Nombre_Usuario = %s", (username,))
                            result = cur.fetchone()
                            if result:
                                new_values[field] = result[0]  # Convertir a ID
                            else:
                                messagebox.showerror("Error", 
                                    f"Usuario '{username}' no encontrado en la base de datos.", 
                                    parent=edit_win)
                                cur.close()
                                conn.close()
                                return
                
                set_clause = ", ".join(f"`{c}` = %s" for c in col_names_original if c != pk_name)
                sql = f"UPDATE `{tabla}` SET {set_clause} WHERE `{pk_name}` = %s"
                
                params = []
                for c in col_names_original:
                    if c != pk_name:
                        value = new_values[c]
                        # Convertir cadenas vacías a NULL para campos específicos
                        if value is None or value == "":
                            # Campos que deben ser NULL cuando están vacíos:
                            # - IDs foráneos: id_, _id
                            # - Fechas/tiempos: fecha, date, time, hora, timestamp, _at, created, updated, modified, deleted
                            # - Campos de entrada/salida: _in, _out, cover_in, cover_out, log_
                            # - Campos especiales: user_logged
                            null_keywords = ['id_', '_id', 'user_logged', 'fecha', 'date', 'time', 
                                           'hora', 'timestamp', '_in', '_out', 'cover_', '_at',
                                           'created', 'updated', 'modified', 'deleted', 'log_']
                            if any(keyword in c.lower() for keyword in null_keywords):
                                value = None
                        params.append(value)
                params.append(pk_value)
                
                cur.execute(sql, params)
                conn.commit()
                cur.close()
                conn.close()
                
                load_admin_table()
                edit_win.destroy()
            except Exception as e:
                error_msg = str(e)
                # Mensajes de error más claros para el usuario
                if "foreign key constraint fails" in error_msg.lower():
                    if "Covered_by" in error_msg or "covered" in error_msg:
                        messagebox.showerror("Error de Validación", 
                            "El usuario ingresado en 'Covered_by' no existe en la tabla de usuarios.\n\n"
                            "Verifica que el nombre de usuario sea correcto y exista en el sistema.", 
                            parent=edit_win)
                    elif "ID_Usuario" in error_msg or "user" in error_msg:
                        messagebox.showerror("Error de Validación",
                            "El ID de usuario ingresado no existe en la tabla de usuarios.\n\n"
                            "Verifica que el ID sea correcto.",
                            parent=edit_win)
                    else:
                        messagebox.showerror("Error de Validación",
                            "El valor ingresado no cumple con las restricciones de la base de datos.\n\n"
                            "Verifica que todos los valores de referencia (IDs, nombres) existan en sus tablas correspondientes.",
                            parent=edit_win)
                elif "Incorrect datetime value" in error_msg:
                    messagebox.showerror("Error de Formato",
                        "Formato de fecha/hora incorrecto.\n\n"
                        "Use el formato: YYYY-MM-DD HH:MM:SS\n"
                        "Ejemplo: 2025-12-04 14:30:00\n\n"
                        "O deje el campo vacío si no tiene valor.",
                        parent=edit_win)
                else:
                    messagebox.showerror("Error", f"No se pudo actualizar:\n{error_msg}", parent=edit_win)
                traceback.print_exc()
        
        # Botón guardar (agregar al frame que ya fue creado)
        if UI is not None:
            UI.CTkButton(button_frame, text="💾 Guardar", command=save_changes,
                        fg_color="#4a90e2", hover_color="#357ABD",
                        width=200, height=40, font=("Segoe UI", 12, "bold")).pack(pady=5)
        else:
            tk.Button(button_frame, text="💾 Guardar", bg="#4aa3ff", fg="white", 
                     font=("Segoe UI", 11, "bold"), command=save_changes, width=20, height=2).pack(pady=5)
    
    def create_admin_record():
        """Crea un nuevo registro en la tabla actual"""
        tabla = admin_metadata['current_table']
        if not tabla:
            messagebox.showwarning("Atención", "Primero cargue una tabla.", parent=top)
            return
        
        col_names = admin_metadata.get('col_names', [])
        pk_name = admin_metadata.get('pk')
        
        # Determinar qué columnas mostrar
        # Para Sitios: mostrar todo (ID no es autoincremental)
        # Para otras tablas: omitir columnas ID autoincrementales
        if tabla == "Sitios":
            visible_cols = col_names
        else:
            # Omitir columnas que terminan con _id o son ID, excepto FK importantes
            visible_cols = []
            for c in col_names:
                c_lower = c.lower()
                # Omitir IDs autoincrementales pero mantener FKs importantes
                if c_lower in ('id_eventos', 'id_usuario', 'id_special', 'id_cover', 'id_sesion', 'id_estacion'):
                    # Es un ID autoincremental, omitir
                    continue
                # Mantener FKs como ID_Sitio, ID_Usuario (sin guion bajo al inicio)
                visible_cols.append(c)
        
        # Ventana de creación con CustomTkinter
        if UI is not None:
            create_win = UI.CTkToplevel(top)
            create_win.configure(fg_color="#2c2f33")
        else:
            create_win = tk.Toplevel(top)
            create_win.configure(bg="#2c2f33")
        
        create_win.title(f"Crear registro en {tabla}")
        win_height = min(120 + 50 * len(visible_cols), 750)
        create_win.geometry(f"550x{win_height}")
        create_win.resizable(False, False)
        
        # Título
        if UI is not None:
            UI.CTkLabel(create_win, text=f"➕ Crear en: {tabla}", 
                       font=("Segoe UI", 14, "bold"), text_color="#e0e0e0").pack(pady=(10, 20))
        else:
            tk.Label(create_win, text=f"➕ Crear en: {tabla}", 
                    bg="#2c2f33", fg="#e0e0e0", font=("Segoe UI", 14, "bold")).pack(pady=(10, 20))
        
        # Frame inferior para botón (crear PRIMERO para que aparezca al fondo)
        if UI is not None:
            button_frame = UI.CTkFrame(create_win, fg_color="#2c2f33")
            button_frame.pack(side="bottom", fill="x", pady=(10, 15))
        else:
            button_frame = tk.Frame(create_win, bg="#2c2f33")
            button_frame.pack(side="bottom", fill="x", pady=(10, 15))
        
        # Frame scrollable para campos
        if UI is not None:
            fields_container = UI.CTkScrollableFrame(create_win, fg_color="transparent")
            fields_container.pack(fill="both", expand=True, padx=20, pady=(0, 10))
            fields_frame = fields_container
        else:
            canvas = tk.Canvas(create_win, bg="#2c2f33", highlightthickness=0)
            scrollbar = tk.Scrollbar(create_win, orient="vertical", command=canvas.yview)
            fields_frame = tk.Frame(canvas, bg="#2c2f33")
            canvas.configure(yscrollcommand=scrollbar.set)
            canvas.pack(side="left", fill="both", expand=True, padx=20)
            scrollbar.pack(side="right", fill="y")
            canvas.create_window((0, 0), window=fields_frame, anchor="nw")
            fields_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        
        entries = {}
        for i, cname in enumerate(visible_cols):
            if UI is not None:
                UI.CTkLabel(fields_frame, text=f"{cname}:", text_color="#a3c9f9", 
                           font=("Segoe UI", 12, "bold")).grid(row=i, column=0, sticky="w", padx=10, pady=8)
                e = UI.CTkEntry(fields_frame, width=280, font=("Segoe UI", 12))
                e.grid(row=i, column=1, padx=10, pady=8)
            else:
                tk.Label(fields_frame, text=f"{cname}:", bg="#2c2f33", fg="#a3c9f9", 
                        font=("Segoe UI", 12, "bold")).grid(row=i, column=0, sticky="w", padx=10, pady=8)
                e = tk.Entry(fields_frame, width=38, font=("Segoe UI", 12))
                e.grid(row=i, column=1, padx=10, pady=8)
            
            entries[cname] = e
        
        def save_new():
            new_values = {}
            for c in visible_cols:
                try:
                    new_values[c] = entries[c].get()
                except:
                    new_values[c] = ""
            
            try:
                conn = get_connection()
                cur = conn.cursor()
                
                # Construir INSERT solo con columnas visibles
                columns = ", ".join(f"`{c}`" for c in visible_cols)
                placeholders = ", ".join(["%s"] * len(visible_cols))
                sql = f"INSERT INTO `{tabla}` ({columns}) VALUES ({placeholders})"
                
                params = []
                for c in visible_cols:
                    value = new_values[c]
                    if value == "":
                        value = None
                    params.append(value)
                
                cur.execute(sql, params)
                conn.commit()
                cur.close()
                conn.close()
                
                load_admin_table()
                create_win.destroy()
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo crear:\n{e}", parent=create_win)
                traceback.print_exc()
        
        # Botón guardar (agregar al frame que ya fue creado)
        if UI is not None:
            UI.CTkButton(button_frame, text="💾 Guardar", command=save_new,
                        fg_color="#00c853", hover_color="#00a043",
                        width=200, height=40, font=("Segoe UI", 12, "bold")).pack(pady=5)
        else:
            tk.Button(button_frame, text="💾 Guardar", bg="#00c853", fg="white", 
                     font=("Segoe UI", 11, "bold"), command=save_new, width=20, height=2).pack(pady=5)
    
    # Botones de acción en admin_controls
    if UI is not None:
        UI.CTkButton(admin_controls, text="🔄 Cargar", command=load_admin_table,
                    fg_color="#4a90e2", hover_color="#357ABD",
                    width=100, height=32, font=("Segoe UI", 11, "bold")).pack(side="left", padx=5)
        UI.CTkButton(admin_controls, text="➕ Crear", command=create_admin_record,
                    fg_color="#00c853", hover_color="#00a043",
                    width=100, height=32, font=("Segoe UI", 11, "bold")).pack(side="left", padx=5)
        UI.CTkButton(admin_controls, text="✏️ Editar", command=edit_admin_selected,
                    fg_color="#f0ad4e", hover_color="#ec971f",
                    width=100, height=32, font=("Segoe UI", 11, "bold")).pack(side="left", padx=5)
        UI.CTkButton(admin_controls, text="🗑️ Eliminar", command=delete_admin_selected,
                    fg_color="#d32f2f", hover_color="#b71c1c",
                    width=100, height=32, font=("Segoe UI", 11, "bold")).pack(side="left", padx=5)
    else:
        tk.Button(admin_controls, text="🔄 Cargar", command=load_admin_table,
                 bg="#4a90e2", fg="white", font=("Segoe UI", 11, "bold"),
                 relief="flat", width=10).pack(side="left", padx=5)
        tk.Button(admin_controls, text="➕ Crear", command=create_admin_record,
                 bg="#00c853", fg="white", font=("Segoe UI", 11, "bold"),
                 relief="flat", width=10).pack(side="left", padx=5)
        tk.Button(admin_controls, text="✏️ Editar", command=edit_admin_selected,
                 bg="#f0ad4e", fg="white", font=("Segoe UI", 11, "bold"),
                 relief="flat", width=10).pack(side="left", padx=5)
        tk.Button(admin_controls, text="🗑️ Eliminar", command=delete_admin_selected,
                 bg="#d32f2f", fg="white", font=("Segoe UI", 11, "bold"),
                 relief="flat", width=10).pack(side="left", padx=5)
    
    # Frame para tksheet de Admin
    if UI is not None:
        admin_sheet_frame = UI.CTkFrame(admin_container, fg_color="#2c2f33")
    else:
        admin_sheet_frame = tk.Frame(admin_container, bg="#2c2f33")
    admin_sheet_frame.pack(fill="both", expand=True, padx=10, pady=10)
    
    # Crear tksheet de Admin
    admin_sheet = SheetClass(
        admin_sheet_frame,
        data=[["Seleccione una tabla y presione 'Cargar'"]],
        headers=["Datos"],
        theme="dark blue",
        height=500,
        width=1330,
        show_selected_cells_border=True,
        show_row_index=True,
        show_top_left=False,
        empty_horizontal=0,
        empty_vertical=0,
        auto_resize_columns=False,
        auto_resize_rows=False
    )
    admin_sheet.enable_bindings([
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
    admin_sheet.pack(fill="both", expand=True)

    # ==================== CLOSE HANDLER ====================
    
    # ⭐ CONFIGURAR CIERRE DE VENTANA: Ejecutar logout automáticamente
    def on_window_close_leadsuper():
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
    top.protocol("WM_DELETE_WINDOW", on_window_close_leadsuper)

