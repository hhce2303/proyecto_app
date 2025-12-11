import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from backend_super import _focus_singleton, _register_singleton, load_tz_config, on_start_shift, on_end_shift, Dinamic_button_Shift, cover_mode, safe_delete, show_covers_programados_panel
#

import under_super

from models.database import get_connection
from models.user_model import get_user_status_bd
from models.site_model import get_sites, get_activities
from models.cover_model import insertar_cover, request_covers
#
import traceback
import tkcalendar
import re
from datetime import datetime, timedelta
import login

def open_hybrid_events(username, session_id=None, station=None, root=None):
    print(f"[info] abriendo desde nuevo script operator_window.py")
    station = station or under_super.get_station(username)
    """
    🚀 VENTANA HÍBRIDA: Registro + Visualización de Eventos
    
    Combina funcionalidad de registro y edición en una sola ventana tipo Excel:
    - Visualización de eventos del turno actual en tksheet
    - Edición inline con doble-click
    - Widgets especializados por columna (DatePicker, FilteredCombobox, etc.)
    - Botones: Nuevo, Guardar, Eliminar, Refrescar
    - Auto-refresh configurable
    - Validaciones en tiempo real
    - Incluye botones Cover y Start/End Shift en header
    """
    # Singleton
    ex = _focus_singleton('hybrid_events')
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
    # ⭐ Asegurar que existe un root oculto antes de crear Toplevel
    if tk._default_root is None:
        hidden_root = tk.Tk()
        hidden_root.withdraw()  # Ocultar completamente
        tk._default_root = hidden_root
    
    if UI is not None:
        top = UI.CTkToplevel()
        top.configure(fg_color="#1e1e1e")
    else:
        top = tk.Toplevel()
        top.configure(bg="#1e1e1e")
    
    top.title(f"📊 Eventos - {username}")
    top.geometry("1410x800")  # Ancho reducido al eliminar columna "Out at"
    top.resizable(True, True)

    # ⭐ VARIABLE DE MODO: 'daily', 'specials' o 'covers'
    current_mode = tk.StringVar(value='daily')  # Estado del toggle
    
    # Variables de estado
    row_data_cache = []  # Lista de diccionarios con datos de cada fila
    row_ids = []  # IDs de eventos (None para nuevos)
    pending_changes = []  # Lista de índices de filas con cambios sin guardar

    # Columnas de la hoja (DAILY)
    columns_daily = ["Fecha Hora", "Sitio", "Actividad", "Cantidad", "Camera", "Descripción"]
    
    # Columnas para SPECIALS (sin ID ni Usuario - son irrelevantes)
    columns_specials = ["Fecha Hora", "Sitio", "Actividad", "Cantidad", "Camera", "Descripcion", "TZ", "Marca"]
    
    # Columnas para COVERS (sin ID - solo información relevante)
    columns_covers = ["Nombre Usuarios", "Time Request", "Cover in", "Cover out", "Motivo", "Covered by", "Activo"]
    
    # Columnas activas (inicia con daily)
    columns = columns_daily
    
    # Anchos personalizados para DAILY
    custom_widths_daily = {
        "Fecha Hora": 160,
        "Sitio": 260,
        "Actividad": 170,
        "Cantidad": 80,
        "Camera": 90,
        "Descripción": 330  # Ampliado al eliminar "Out at"
    }
    
    # Anchos personalizados para SPECIALS (sin ID ni Usuario)
    custom_widths_specials = {
        "Fecha Hora": 140,
        "Sitio": 277,
        "Actividad": 150,
        "Cantidad": 60,
        "Camera": 60,
        "Descripcion": 210,
        "TZ": 70,  # Aumentado de 40 a 80 para mejor visibilidad
        "Marca": 180
    }
    
    # Anchos personalizados para COVERS (sin ID_Covers)
    custom_widths_covers = {
        "Nombre Usuarios": 150,
        "Time Request": 150,
        "Cover in": 150,
        "Cover out": 150,
        "Motivo": 200,
        "Covered by": 150,
        "Activo": 80
    }
    
    # Anchos activos (inicia con daily)
    custom_widths = custom_widths_daily

    # Header
    if UI is not None:
        header = UI.CTkFrame(top, fg_color="#23272a", corner_radius=0)
    else:
        header = tk.Frame(top, bg="#23272a")
    header.pack(fill="x", padx=0, pady=0)

    # ⭐ FUNCIÓN: Manejar Start/End Shift
    def handle_shift_button():
        """Maneja el click en el botón Start/End Shift"""
        try:
            # Verificar estado actual
            is_start = Dinamic_button_Shift(username)
            
            if is_start:
                # Iniciar turno
                success = on_start_shift(username, parent_window=top)
                if success:
                    # Actualizar el botón
                    update_shift_button()
                    # Recargar datos (el nuevo evento START/END debe aparecer)
                    load_data()
            else:
                # Finalizar turno
                on_end_shift(username)
                # Actualizar el botón
                update_shift_button()
                # Recargar datos (el nuevo evento START/END debe aparecer)
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
                # Mostrar "Start Shift"
                if UI is not None:
                    shift_btn.configure(text="🚀 Start Shift", 
                                       fg_color="#00c853", 
                                       hover_color="#00a043")
                else:
                    shift_btn.configure(text="🚀 Start Shift", bg="#00c853")
            else:
                # Mostrar "End of Shift"
                if UI is not None:
                    shift_btn.configure(text="🏁 End of Shift", 
                                       fg_color="#d32f2f", 
                                       hover_color="#b71c1c")
                else:
                    shift_btn.configure(text="🏁 End of Shift", bg="#d32f2f")
        except Exception as e:
            print(f"[ERROR] update_shift_button: {e}")
    
    # ⭐ FUNCIÓN: Manejar botón Cover
    def handle_cover_button(username):
        """Abre la ventana de Cover mode"""
        try:
            # Llamar a cover_mode con los parámetros necesarios
            # Si no tenemos session_id/station/root, usar valores por defecto
            cover_mode(username, session_id, station, root=top)

        except Exception as e:
            messagebox.showerror("Error", f"Error al abrir Cover:\n{e}", parent=top)
            print(f"[ERROR] handle_cover_button: {e}")
            traceback.print_exc()

    if UI is not None:
        # ⭐ Botones Refrescar y Eliminar a la izquierda (movidos desde toolbar)
        UI.CTkButton(header, text="🔄  Refrescar", command=lambda: load_data(),
                    fg_color="#4D6068", hover_color="#27a3e0", 
                    width=120, height=40,
                    font=("Segoe UI", 12, "bold")).pack(side="left", padx=(20, 5), pady=15)
        
        delete_btn_header = UI.CTkButton(header, text="🗑️ Eliminar", command=lambda: None,  # Se asignará después
                    fg_color="#d32f2f", hover_color="#b71c1c", 
                    width=120, height=40,
                    font=("Segoe UI", 12, "bold"))
        delete_btn_header.pack(side="left", padx=5, pady=15)

        # ⭐ Función para obtener próximo cover programado
        def get_next_cover_info():
            """Obtiene el próximo cover programado del usuario desde gestion_breaks_programados"""
            try:
                conn = get_connection()
                cur = conn.cursor()
                
                # Obtener ID_Usuario del username
                cur.execute("SELECT ID_Usuario FROM user WHERE Nombre_Usuario = %s", (username,))
                user_row = cur.fetchone()
                if not user_row:
                    print(f"[DEBUG] Usuario '{username}' no encontrado en tabla user")
                    cur.close()
                    conn.close()
                    return None
                
                id_usuario = user_row[0]
                print(f"[DEBUG] ID_Usuario obtenido: {id_usuario} para username: {username}")
                
                # Buscar cover más próximo (futuro o más reciente pasado)
                # Prioridad: covers futuros ordenados por cercanía, luego el más reciente pasado
                query = """
                    SELECT 
                        gbp.Fecha_hora_cover,
                        u_covering.Nombre_Usuario as covering_name,
                        gbp.User_covered,
                        gbp.User_covering,
                        gbp.is_Active
                    FROM gestion_breaks_programados gbp
                    INNER JOIN user u_covering ON gbp.User_covering = u_covering.ID_Usuario
                    WHERE gbp.User_covered = %s 
                    AND gbp.is_Active = 1
                    ORDER BY 
                        CASE 
                            WHEN gbp.Fecha_hora_cover >= NOW() THEN 0
                            ELSE 1
                        END,
                        ABS(TIMESTAMPDIFF(MINUTE, gbp.Fecha_hora_cover, NOW())) ASC
                    LIMIT 1
                """
                
                print(f"[DEBUG] Ejecutando query con id_usuario={id_usuario}")
                cur.execute(query, (id_usuario,))
                result = cur.fetchone()
                
                print(f"[DEBUG] Resultado de query: {result}")
                
                # Debug: Mostrar todos los covers activos sin filtro de usuario
                cur.execute("""
                    SELECT User_covered, User_covering, Fecha_hora_cover, is_Active 
                    FROM gestion_breaks_programados 
                    WHERE is_Active = 1
                """)
                all_active = cur.fetchall()
                print(f"[DEBUG] Todos los covers activos en BD: {all_active}")
                
                cur.close()
                conn.close()
                
                if result:
                    fecha_hora_cover, covering_name, user_covered_id, user_covering_id, is_active = result
                    print(f"[DEBUG] Cover encontrado: hora={fecha_hora_cover}, covering={covering_name}, user_covered={user_covered_id}, user_covering={user_covering_id}, active={is_active}")
                    # Formatear hora como HH:MM
                    hora_str = fecha_hora_cover.strftime("%H:%M") if fecha_hora_cover else ""
                    return {
                        'hora': hora_str,
                        'covering': covering_name,
                        'covered': username
                    }
                
                print(f"[DEBUG] No se encontró cover para id_usuario={id_usuario}")
                return None
                
            except Exception as e:
                print(f"[ERROR] get_next_cover_info: {e}")
                traceback.print_exc()
                return None
        
        def update_cover_label():
            """Actualiza el texto del label con la información del próximo cover"""
            try:
                cover_info = get_next_cover_info()
                if cover_info:
                    texto = f"☕ Break: {cover_info['hora']} | Cubierto por: {cover_info['covering']}"
                    cover_label.configure(text=texto)
                else:
                    cover_label.configure(text="☕ No hay covers programados")
            except Exception as e:
                print(f"[ERROR] update_cover_label: {e}")
                cover_label.configure(text="☕ Error al cargar cover")
        
        # ⭐ Función para obtener si el usuario debe cubrir a alguien
        def get_covering_assignment():
            """Obtiene TODOS los covers que el usuario debe realizar (activos y futuros)"""
            try:
                conn = get_connection()
                cur = conn.cursor()
                
                # Obtener ID_Usuario del username
                cur.execute("SELECT ID_Usuario FROM user WHERE Nombre_Usuario = %s", (username,))
                user_row = cur.fetchone()
                if not user_row:
                    print(f"[DEBUG] Usuario '{username}' no encontrado en tabla user para covering")
                    cur.close()
                    conn.close()
                    return None
                
                id_usuario = user_row[0]
                print(f"[DEBUG] Buscando TODOS los covers asignados para ID_Usuario: {id_usuario} (covering)")
                
                # Buscar TODOS los covers activos donde user_covering = username
                # Ordenados por hora (los más próximos primero)
                query = """
                    SELECT 
                        gbp.Fecha_hora_cover,
                        u_covered.Nombre_Usuario as covered_name,
                        gbp.User_covered,
                        gbp.User_covering,
                        gbp.is_Active
                    FROM gestion_breaks_programados gbp
                    INNER JOIN user u_covered ON gbp.User_covered = u_covered.ID_Usuario
                    WHERE gbp.User_covering = %s 
                    AND gbp.is_Active = 1
                    ORDER BY gbp.Fecha_hora_cover ASC
                """
                
                print(f"[DEBUG] Ejecutando query covering con id_usuario={id_usuario}")
                cur.execute(query, (id_usuario,))
                results = cur.fetchall()
                
                print(f"[DEBUG] Resultados de query covering: {len(results)} covers encontrados")
                
                cur.close()
                conn.close()
                
                if results:
                    # Formatear todos los covers encontrados
                    covers_list = []
                    for row in results:
                        fecha_hora_cover, covered_name, user_covered_id, user_covering_id, is_active = row
                        hora_str = fecha_hora_cover.strftime("%H:%M") if fecha_hora_cover else ""
                        covers_list.append({
                            'hora': hora_str,
                            'covered': covered_name,
                            'covering': username
                        })
                        print(f"[DEBUG] Cover #{len(covers_list)}: hora={hora_str}, cubriendo a={covered_name}")
                    
                    return covers_list if len(covers_list) > 0 else None
                
                print(f"[DEBUG] No se encontraron asignaciones de cover para id_usuario={id_usuario} como covering")
                return None
                
            except Exception as e:
                print(f"[ERROR] get_covering_assignment: {e}")
                traceback.print_exc()
                return None
        
        def update_covering_label():
            """Actualiza el texto del label con TODOS los covers que el usuario debe realizar (formato multi-línea)"""
            try:
                covering_list = get_covering_assignment()
                print(f"[DEBUG] update_covering_label - covering_list: {covering_list}")
                
                if covering_list and len(covering_list) > 0:
                    # Construir texto con formato de 2 columnas por línea
                    if len(covering_list) == 1:
                        # Un solo cover
                        cover = covering_list[0]
                        texto = f"👤 Cubres a: {cover['covered']} ({cover['hora']})"
                    else:
                        # Múltiples covers - 2 por línea, saltos de línea para el resto
                        lines = []
                        for i in range(0, len(covering_list), 2):
                            # Tomar 2 covers por línea
                            pair = covering_list[i:i+2]
                            if len(pair) == 2:
                                line_text = f"{pair[0]['covered']} ({pair[0]['hora']})  •  {pair[1]['covered']} ({pair[1]['hora']})"
                            else:
                                line_text = f"{pair[0]['covered']} ({pair[0]['hora']})"
                            lines.append(line_text)
                        
                        # Primera línea con el encabezado
                        texto = f"👤 Cubres a: {lines[0]}"
                        # Agregar líneas adicionales con indentación
                        if len(lines) > 1:
                            for line in lines[1:]:
                                texto += f"\n                    {line}"
                    
                    covering_label.configure(text=texto)
                    # Asegurar que el label esté visible
                    if not covering_label.winfo_ismapped():
                        covering_label.pack(side="left", padx=(0, 20), pady=15)
                    print(f"[DEBUG] Label actualizado con {len(covering_list)} cover(s) en formato multi-línea")
                else:
                    print(f"[DEBUG] No hay asignaciones de cover, ocultando label")
                    if covering_label.winfo_ismapped():
                        covering_label.pack_forget()
            except Exception as e:
                print(f"[ERROR] update_covering_label: {e}")
                traceback.print_exc()
                if covering_label.winfo_ismapped():
                    covering_label.pack_forget()
        
        # ⭐ Frame contenedor para los dos labels (uno arriba del otro)
        cover_labels_frame = UI.CTkFrame(header, fg_color="transparent")
        cover_labels_frame.pack(side="left", padx=20, pady=15)
        
        # ⭐ Label de información de cover recibido (arriba)
        cover_label = UI.CTkLabel(
            cover_labels_frame,
            text="☕ Cargando...",
            text_color="#00bfae",
            font=("Segoe UI", 13, "bold")
        )
        cover_label.pack(anchor="w")
        
        # ⭐ Label de asignación de cover (abajo - solo se muestra si debe cubrir a alguien)
        covering_label = UI.CTkLabel(
            cover_labels_frame,
            text="",
            text_color="#ffa500",
            font=("Segoe UI", 13, "bold")
        )
        # NO hacer pack() aquí - se mostrará solo si hay asignación
        
        # Actualizar labels al iniciar
        update_cover_label()
        update_covering_label()
        
        # ⭐ AUTO-REFRESH: Actualizar labels cada 30 segundos (30000 ms) para pruebas
        def auto_refresh_cover_labels():
            """Refresca automáticamente los labels de cover cada 30 segundos"""
            from datetime import datetime as dt_now
            try:
                print(f"[DEBUG] ===== Iniciando auto-refresh de cover labels a las {dt_now.now().strftime('%H:%M:%S')} =====")
                update_cover_label()
                update_covering_label()
                print(f"[DEBUG] Cover labels actualizados automáticamente a las {dt_now.now().strftime('%H:%M:%S')}")
            except Exception as e:
                print(f"[ERROR] auto_refresh_cover_labels: {e}")
                traceback.print_exc()
            
            # Programar siguiente actualización (30 segundos = 30000 ms)
            top.after(30000, auto_refresh_cover_labels)
        
        # Iniciar auto-refresh
        auto_refresh_cover_labels()
        
        # ⭐ Botón Start/End Shift a la derecha
        shift_btn = UI.CTkButton(
            header, 
            text="🚀 Start Shift",  # Texto por defecto, se actualizará
            command=handle_shift_button,
            width=160, 
            height=40,
            font=("Segoe UI", 14, "bold"),
            fg_color="#00c853",
            hover_color="#00a043"
        )
        shift_btn.pack(side="right", padx=(5, 20), pady=15)
        
        # ⭐ Botón Ver Covers a la derecha (al lado de Start/End Shift)
        def switch_to_covers():
            """Cambia al modo Covers actualizando headers y datos"""
            nonlocal columns, custom_widths
            current_mode.set('covers')
            columns = columns_covers
            custom_widths = custom_widths_covers
            sheet.headers(columns_covers)
            toggle_btn.configure(text="📅 Daily")
            
            # ⭐ DESHABILITAR EDICIÓN en sheet (modo solo lectura)
            try:
                sheet.disable_bindings("edit_cell")
            except Exception as e:
                print(f"[DEBUG] No se pudo deshabilitar edit_cell: {e}")
            
            # Ocultar formulario y botones de envío
            entry_frame.pack_forget()
            if enviar_btn:
                enviar_btn.pack_forget()
            if accion_btn:
                accion_btn.pack_forget()
            
            # ⭐ Mostrar frame de posición en cola
            cover_queue_frame.pack(fill="x", padx=10, pady=(10, 5), before=main_content_container)
            
            load_data()
        
        UI.CTkButton(header, text="📋 Ver Covers", 
                    command=switch_to_covers,
                    fg_color="#4D6068", hover_color="#7b1fa2", 
                    width=130, height=40,
                    font=("Segoe UI", 12, "bold")).pack(side="right", padx=5, pady=15)
        
        # ⭐ Botón Registrar Cover a la derecha (al lado de Ver Covers)
        UI.CTkButton(header, text="👥 Registrar Cover", command=lambda: handle_cover_button(username),
                    fg_color="#4D6068", hover_color="#f57c00", 
                    width=150, height=40,
                    font=("Segoe UI", 12, "bold")).pack(side="right", padx=5, pady=15)
        
                # ⭐ Botón Solicitar Cover a la derecha (al lado de Ver Covers)
        from datetime import datetime
        UI.CTkButton(header, text="❓ Solicitar Cover", 
                    command=lambda: request_covers(
                        username, 
                        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "Necesito un cover", 
                        1  # aprvoved=1 porque es una solicitud aprobada, pero con posibilidad de denegar
                    ),
                    fg_color="#4D6068", hover_color="#f57c00", 
                    width=150, height=40,
                    font=("Segoe UI", 12, "bold")).pack(side="right", padx=5, pady=15)
        
    else:
        # Fallback Tkinter
        # ⭐ Botones Refrescar y Eliminar a la izquierda (movidos desde toolbar)
        tk.Button(header, text="� Refrescar", command=lambda: load_data(), 
                 bg="#666666", fg="white",
                 font=("Segoe UI", 12, "bold"), relief="flat",
                 width=12).pack(side="left", padx=(20, 5), pady=15)
        
        delete_btn_header = tk.Button(header, text="🗑️ Eliminar", command=lambda: None,  # Se asignará después
                 bg="#d32f2f", fg="white",
                 font=("Segoe UI", 12, "bold"), relief="flat",
                 width=12)
        delete_btn_header.pack(side="left", padx=5, pady=15)
        
        # ⭐ Botón Start/End Shift a la derecha (Tkinter)
        shift_btn = tk.Button(
            header,
            text="🚀 Start Shift",
            command=handle_shift_button,
            bg="#00c853",
            fg="white",
            font=("Segoe UI", 12, "bold"),
            relief="flat",
            width=15
        )
        shift_btn.pack(side="right", padx=(5, 20), pady=15)
        
        # ⭐ Botón Ver Covers a la derecha (al lado de Start/End Shift)
        def switch_to_covers_tk():
            """Cambia al modo Covers actualizando headers y datos (Tkinter fallback)"""
            nonlocal columns, custom_widths
            current_mode.set('covers')
            columns = columns_covers
            custom_widths = custom_widths_covers
            sheet.headers(columns_covers)
            toggle_btn.configure(text="📅 Daily", bg="#4D6068")
            
            # ⭐ DESHABILITAR EDICIÓN en sheet (modo solo lectura)
            try:
                sheet.disable_bindings("edit_cell")
            except Exception as e:
                print(f"[DEBUG] No se pudo deshabilitar edit_cell: {e}")
            
            # Ocultar formulario y botones de envío
            entry_frame.pack_forget()
            if enviar_btn:
                enviar_btn.pack_forget()
            if accion_btn:
                accion_btn.pack_forget()
            
            # ⭐ Mostrar frame de posición en cola
            cover_queue_frame.pack(fill="x", padx=10, pady=(10, 5), before=main_content_container)
            
            load_data()
        
        tk.Button(header, text="📋 Ver Covers",
                 command=switch_to_covers_tk,
                 bg="#9c27b0", fg="white",
                 font=("Segoe UI", 12, "bold"), relief="flat",
                 width=13).pack(side="right", padx=5, pady=15)
        
        # ⭐ Botón Registrar Cover a la derecha (al lado de Ver Covers)
        tk.Button(header, text="⚙️ Registrar Cover", command=handle_cover_button,
                 bg="#ff9800", fg="white",
                 font=("Segoe UI", 12, "bold"), relief="flat",
                 width=16).pack(side="right", padx=5, pady=15)
    
    # Actualizar botón al iniciar
    update_shift_button()

    # Separador
    try:
        ttk.Separator(top, orient="horizontal").pack(fill="x")
    except Exception:
        pass

    # ⭐ Frame para Label de posición en cola de covers
    if UI is not None:
        cover_queue_frame = UI.CTkFrame(top, fg_color="#1e3a4c", corner_radius=8, height=50)
    else:
        cover_queue_frame = tk.Frame(top, bg="#1e3a4c", height=50)
    cover_queue_frame.pack(fill="x", padx=10, pady=(10, 5))
    cover_queue_frame.pack_propagate(False)

    # Label de posición en cola (se mostrará solo en modo covers)
    if UI is not None:
        cover_queue_label = UI.CTkLabel(
            cover_queue_frame,
            text="Calculando posición en cola...",
            text_color="#00bfae",
            font=("Segoe UI", 13, "bold")
        )
    else:
        cover_queue_label = tk.Label(
            cover_queue_frame,
            text="Calculando posición en cola...",
            bg="#1e3a4c",
            fg="#00bfae",
            font=("Segoe UI", 13, "bold")
        )
    cover_queue_label.pack(pady=10)
    
    # Ocultar el frame inicialmente (solo se muestra en modo covers)
    cover_queue_frame.pack_forget()

    # Contenedor principal horizontal (sheet + panel de noticias)
    if UI is not None:
        main_content_container = UI.CTkFrame(top, fg_color="#2c2f33")
    else:
        main_content_container = tk.Frame(top, bg="#2c2f33")
    main_content_container.pack(fill="both", expand=True, padx=10, pady=3)
    
    # Frame para tksheet (lado izquierdo)
    if UI is not None:
        sheet_frame = UI.CTkFrame(main_content_container, fg_color="#2c2f33")
    else:
        sheet_frame = tk.Frame(main_content_container, bg="#2c2f33")
    sheet_frame.pack(side="left", fill="both", expand=True, padx=(0, 5))

    # Crear tksheet
    sheet = SheetClass(
        sheet_frame,
        headers=columns,
        theme="dark blue",
        height=500,
        width=1000,  # Reducido al eliminar columna "Out at"
        show_selected_cells_border=True,
        show_row_index=True,
        show_top_left=False,
        empty_horizontal=0,
        empty_vertical=0
    )
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
        "copy",
        "cut",
        "paste",
        "delete",
        "undo",
        "edit_cell"  # CRÍTICO: Permite editar celdas con doble-click
    ])
    sheet.pack(fill="both", expand=True)
    sheet.change_theme("dark blue")

    # ⭐ FORMULARIO DE ENTRADA - Simula una fila editable del sheet
    # Frame contenedor con estilo similar al sheet
    if UI is not None:
        entry_frame = UI.CTkFrame(sheet_frame, fg_color="#23272a", corner_radius=0, height=90)
    else:
        entry_frame = tk.Frame(sheet_frame, bg="#23272a", height=90)
    entry_frame.pack(fill="x", side="bottom", padx=0, pady=0)
    entry_frame.pack_propagate(False)  # Mantener altura fija
    
    # Variables para los campos
    fecha_var = tk.StringVar()
    sitio_var = tk.StringVar()
    actividad_var = tk.StringVar()
    cantidad_var = tk.StringVar(value="0")
    camera_var = tk.StringVar()
    descripcion_var = tk.StringVar()
    
    # ==================== PANEL DE NOTICIAS/INFORMACIÓN (Lado Derecho) ====================
    def create_news_panel():
        """Crea el panel lateral de noticias e información relevante"""
        if UI is not None:
            news_frame = UI.CTkFrame(main_content_container, fg_color="#1e1e1e", 
                                     corner_radius=10, width=240)
        else:
            news_frame = tk.Frame(main_content_container, bg="#1e1e1e", width=240)
        news_frame.pack(side="right", fill="both", padx=(3, 0))
        news_frame.pack_propagate(False)  # Mantener ancho fijo
        
        # Header del panel
        if UI is not None:
            header = UI.CTkFrame(news_frame, fg_color="#2d333b", corner_radius=8, height=50)
        else:
            header = tk.Frame(news_frame, bg="#2d333b", height=50)
        header.pack(fill="x", padx=10, pady=(10, 5))
        header.pack_propagate(False)
        
        if UI is not None:
            UI.CTkLabel(header, text="📰 SLC - News", 
                       font=("Segoe UI", 14, "bold"),
                       text_color="#ffffff").pack(side="left", padx=10, pady=10)
            
            refresh_news_btn = UI.CTkButton(header, text="🔄", width=30, height=30,
                                           font=("Segoe UI", 12),
                                           fg_color="#4a90e2", hover_color="#357abd",
                                           corner_radius=5,
                                           command=lambda: load_news_data())
            refresh_news_btn.pack(side="right", padx=(1, 10), pady=10)
        else:
            tk.Label(header, text="📰 News", bg="#2d333b", fg="#ffffff",
                    font=("Segoe UI", 12, "bold")).pack(side="left", padx=10, pady=10)
        
        # Scrollable container para noticias
        if UI is not None:
            news_scroll = UI.CTkScrollableFrame(news_frame, fg_color="transparent",
                                               scrollbar_button_color="#2d333b",
                                               scrollbar_button_hover_color="#3d444d")
        else:
            news_scroll_canvas = tk.Canvas(news_frame, bg="#1e1e1e", highlightthickness=0)
            news_scroll_scrollbar = tk.Scrollbar(news_frame, orient="vertical", 
                                                command=news_scroll_canvas.yview)
            news_scroll = tk.Frame(news_scroll_canvas, bg="#1e1e1e")
            news_scroll_canvas.configure(yscrollcommand=news_scroll_scrollbar.set)
            news_scroll_scrollbar.pack(side="right", fill="y")
            news_scroll_canvas.pack(side="left", fill="both", expand=True)
            news_scroll_canvas.create_window((0, 0), window=news_scroll, anchor="nw")
            news_scroll.bind("<Configure>", lambda e: news_scroll_canvas.configure(
                scrollregion=news_scroll_canvas.bbox("all")))
        
        news_scroll.pack(fill="both", expand=True, padx=10, pady=(5, 10))
        
        return news_scroll
    
    def load_news_data():
        """Carga información activa de la tabla 'information'"""
        try:
            conn = get_connection()
            cur = conn.cursor()
            
            # Obtener información activa ordenada por urgencia y fecha
            query = """
                SELECT ID_information, info_type, name_info, urgency, 
                       publish_by, fechahora_in, fechahora_out
                FROM information
                WHERE is_Active = 1
                ORDER BY 
                    FIELD(urgency, 'HIGH', 'MID', 'LOW'),
                    fechahora_in DESC
                LIMIT 50
            """
            cur.execute(query)
            news_items = cur.fetchall()
            
            cur.close()
            conn.close()
            
            # Limpiar container anterior
            for widget in news_container.winfo_children():
                widget.destroy()
            
            if not news_items:
                if UI is not None:
                    UI.CTkLabel(news_container, text="📭 No hay información disponible",
                               font=("Segoe UI", 12),
                               text_color="#7d8590").pack(pady=20)
                else:
                    tk.Label(news_container, text="📭 No hay información disponible",
                            bg="#1e1e1e", fg="#7d8590",
                            font=("Segoe UI", 12)).pack(pady=20)
                return
            
            # Crear cards para cada noticia
            for item in news_items:
                id_info, tipo, nombre, urgencia, publicado_por, fecha_in, fecha_out = item
                create_news_card(news_container, id_info, tipo, nombre, urgencia, 
                               publicado_por, fecha_in, fecha_out)
            
            print(f"[INFO] Cargadas {len(news_items)} noticias activas")
            
        except Exception as e:
            print(f"[ERROR] load_news_data: {e}")
            traceback.print_exc()
            if UI is not None:
                UI.CTkLabel(news_container, text=f"❌ Error al cargar noticias:\n{str(e)[:50]}",
                           font=("Segoe UI", 12),
                           text_color="#e74c3c").pack(pady=10)
    
    def create_news_card(parent, id_info, tipo, nombre, urgencia, publicado_por, fecha_in, fecha_out):
        """Crea una tarjeta visual para una noticia"""
        # Colores según urgencia
        urgency_colors = {
            'HIGH': '#e74c3c',
            'MID': '#f39c12',
            'LOW': '#3498db',
            None: '#7d8590'
        }
        color = urgency_colors.get(urgencia, '#7d8590')
        
        # Iconos según tipo
        type_icons = {
            'SITE DOWN': '🔴',
            'MAINTENANCE': '🔧',
            'UPDATE': '🆕',
            'ALERT': '⚠️',
            'INFO': '📌',
            'REMINDER': '⏰',
            None: '📝'
        }
        icon = type_icons.get(tipo, '📝')
        
        # Card container
        if UI is not None:
            card = UI.CTkFrame(parent, fg_color="#2b2b2b", corner_radius=8, 
                               border_width=1, border_color="#444444")
            card.pack(fill="x", pady=8, padx=5)
        else:
            pass
        
        # Barra de color izquierda (urgencia)
        if UI is not None:
            urgency_bar = UI.CTkFrame(card, fg_color=color, width=5, height=20, corner_radius=0)
        else:
            urgency_bar = tk.Frame(card, bg=color, width=5)
        urgency_bar.pack(side="left", fill="both")
        
        # Contenido
        if UI is not None:
            content = UI.CTkFrame(card, fg_color="transparent")
        else:
            content = tk.Frame(card, bg="#2b2b2b")
        content.pack(side="left", fill="both", expand=True, padx=10, pady=3)
        
        # Header: icono + tipo + urgencia
        if UI is not None:
            header_frame = UI.CTkFrame(content, fg_color="transparent")
        else:
            header_frame = tk.Frame(content, bg="#2b2b2b")
        header_frame.pack(fill="x", pady=0)
        
        if UI is not None:
            UI.CTkLabel(header_frame, text=f"{icon} {tipo or 'Info'}", 
                       font=("Segoe UI", 12, "bold"),
                       text_color="#ffffff").pack(side="left")
            
            if urgencia:
                UI.CTkLabel(header_frame, text=urgencia,
                           font=("Segoe UI", 12, "bold"),
                           text_color=color,
                           fg_color="#1e1e1e",
                           corner_radius=5,
                           padx=8, pady=2).pack(side="right")
        else:
            tk.Label(header_frame, text=f"{icon} {tipo or 'Info'}", bg="#2b2b2b", fg="#ffffff",
                    font=("Segoe UI", 12, "bold")).pack(side="left")
        
        # Título/Nombre
        if UI is not None:
            UI.CTkLabel(content, text=nombre or "Sin título",
                       font=("Segoe UI", 12, "bold"),
                       text_color="#e0e0e0",
                       wraplength=260,
                       anchor="w",
                       justify="left").pack(fill="x", pady=0)
        else:
            tk.Label(content, text=nombre or "Sin título", bg="#2b2b2b", fg="#e0e0e0",
                    font=("Segoe UI", 12, "bold"),
                    wraplength=260, anchor="w", justify="left").pack(fill="x", pady=(0, 3))
        
        # Footer: publicado por y fecha
        if UI is not None:
            footer_frame = UI.CTkFrame(content, fg_color="transparent")
        else:
            footer_frame = tk.Frame(content, bg="#2b2b2b")
        footer_frame.pack(fill="x", pady=0)
        
        fecha_str = fecha_in.strftime("%d/%m %H:%M") if fecha_in else "N/A"
        footer_text = f"👤 {publicado_por or 'Sistema'} • 📅 {fecha_str}"
        
        if UI is not None:
            UI.CTkLabel(footer_frame, text=footer_text,
                       font=("Segoe UI", 12),
                       text_color="#7d8590").pack(side="left")
        else:
            tk.Label(footer_frame, text=footer_text, bg="#2b2b2b", fg="#7d8590",
                    font=("Segoe UI", 12)).pack(side="left")
        
        # Si hay fecha de vencimiento, mostrarla
        if fecha_out:
            dias_restantes = (fecha_out - datetime.now()).days
            if dias_restantes >= 0:
                expiry_text = f"⏳ Vence en {dias_restantes} días" if dias_restantes > 0 else "⏳ Vence hoy"
                if UI is not None:
                    UI.CTkLabel(footer_frame, text=expiry_text,
                               font=("Segoe UI", 12),
                               text_color="#f39c12").pack(side="right")
    
    # Crear panel de noticias
    news_container = create_news_panel()
    
    # Cargar datos iniciales
    load_news_data()
    
    # Auto-refresh cada 5 minutos
    def auto_refresh_news():
        load_news_data()
        top.after(300000, auto_refresh_news)  # 5 minutos
    
    top.after(300000, auto_refresh_news)  # Programar primera actualización
    
    # Obtener listas de valores
    sites_list = get_sites()
    activities_list = get_activities()
    
    # ⭐ Configurar estilo oscuro para combobox
    try:
        from tkinter import ttk
        style = ttk.Style()
        style.theme_use('default')
        
        # Estilo para combobox con fondo oscuro
        style.configure('Dark.TCombobox',
                       fieldbackground='#2b2b2b',
                       background='#2b2b2b',
                       foreground='#ffffff',
                       arrowcolor='#ffffff',
                       bordercolor='#4a90e2',
                       lightcolor='#2b2b2b',
                       darkcolor='#2b2b2b',
                       selectbackground='#4a90e2',
                       selectforeground='#ffffff')
        
        style.map('Dark.TCombobox',
                 fieldbackground=[('readonly', '#2b2b2b'), ('disabled', '#1a1a1a')],
                 selectbackground=[('readonly', '#4a90e2')],
                 selectforeground=[('readonly', '#ffffff')],
                 foreground=[('readonly', '#ffffff'), ('disabled', '#666666')])
    except Exception as e:
        print(f"[DEBUG] Could not configure combobox style: {e}")
    
    # ⭐ Espaciador reducido para mover entries a la izquierda
    spacer = tk.Frame(entry_frame, bg="#23272a", width=25)  # Reducido de 45px a 25px
    spacer.pack(side="left", padx=0, pady=0)
    spacer.pack_propagate(False)

    # Campo   (150px) - Exacto al ancho de columna
    fecha_frame = tk.Frame(entry_frame, bg="#23272a", width=150, height=57)
    fecha_frame.pack(side="left", padx=0, pady=5)
    fecha_frame.pack_propagate(False)
    
    # Label para   (centrado)
    tk.Label(fecha_frame, text="Fecha/Hora", bg="#23272a", fg="#a3c9f9",
            font=("Segoe UI", 9, "bold")).pack(anchor="center", padx=2, pady=(0, 2))
    
    if UI is not None:
        fecha_entry = UI.CTkEntry(fecha_frame, textvariable=fecha_var, 
                                  font=("Segoe UI", 11), height=30,
                                  fg_color="#242629", text_color="#ffffff",
                                  border_width=2, border_color="#4a90e2",
                                  corner_radius=5)
        fecha_entry.pack(fill="x", expand=False, padx=1, pady=0)
        # Botón para abrir DateTimePicker (pequeño)
        fecha_btn = UI.CTkButton(fecha_frame, text="📅", width=37, height=27,
                                fg_color="#383f47", hover_color="#3a7bc2",
                                corner_radius=5,
                                command=lambda: None)  # Definiremos después
        fecha_btn.place(relx=1.0, rely=1.0, anchor="se", x=-2, y=-4)
    else:
        fecha_entry = tk.Entry(fecha_frame, textvariable=fecha_var, 
                              font=("Segoe UI", 11), bg="#2b4a6f", fg="#686666")
        fecha_entry.pack(fill="x", expand=False, padx=1, pady=0)

    # Campo Sitio (270px) - Exacto al ancho de columna con Entry + Autocompletado
    sitio_frame = tk.Frame(entry_frame, bg="#23272a", width=270, height=60)
    sitio_frame.pack(side="left", padx=0, pady=5)
    sitio_frame.pack_propagate(False)
    
    # Label para Sitio (centrado)
    tk.Label(sitio_frame, text="Sitio", bg="#23272a", fg="#a3c9f9",
            font=("Segoe UI", 9, "bold")).pack(anchor="center", padx=2, pady=(0, 2))
    
    # ⭐ FilteredCombobox con borde azul prominente
    sitio_combo = under_super.FilteredCombobox(
        sitio_frame, textvariable=sitio_var, values=sites_list,
        font=("Segoe UI", 11), width=32,
        background='#2b2b2b', foreground='#ffffff',
        fieldbackground='#2b2b2b',
        bordercolor='#5ab4ff', arrowcolor='#ffffff',
        borderwidth=3
    )
    sitio_combo.pack(fill="x", expand=False, padx=2, pady=0)
    
    # Campo Actividad (160px) - Exacto al ancho de columna con Entry + Autocompletado
    actividad_frame = tk.Frame(entry_frame, bg="#23272a", width=170, height=60)
    actividad_frame.pack(side="left", padx=0, pady=5)
    actividad_frame.pack_propagate(False)
    
    # Label para Actividad (centrado)
    tk.Label(actividad_frame, text="Actividad", bg="#23272a", fg="#a3c9f9",
            font=("Segoe UI", 9, "bold")).pack(anchor="center", padx=2, pady=(0, 2))
    
    # ⭐ FilteredCombobox con borde azul prominente
    actividad_combo = under_super.FilteredCombobox(
        actividad_frame, textvariable=actividad_var, values=activities_list,
        font=("Segoe UI", 11), width=18,
        background='#2b2b2b', foreground='#ffffff',
        fieldbackground='#2b2b2b',
        bordercolor='#5ab4ff', arrowcolor='#ffffff',
        borderwidth=3
    )
    actividad_combo.pack(fill="x", expand=False, padx=2, pady=0)
    
    # Campo Cantidad (80px) - Exacto al ancho de columna
    cantidad_frame = tk.Frame(entry_frame, bg="#23272a", width=80, height=60)
    cantidad_frame.pack(side="left", padx=0, pady=5)
    cantidad_frame.pack_propagate(False)
    
    # Label para Cantidad (centrado)
    tk.Label(cantidad_frame, text="Cantidad", bg="#23272a", fg="#a3c9f9",
            font=("Segoe UI", 9, "bold")).pack(anchor="center", padx=2, pady=(0, 2))
    
    if UI is not None:
        cantidad_entry = UI.CTkEntry(cantidad_frame, textvariable=cantidad_var,
                                     font=("Segoe UI", 11), height=30,
                                     fg_color="#23272a", text_color="#ffffff",
                                     border_width=2, border_color="#4a90e2",
                                     corner_radius=5)
    else:
        cantidad_entry = tk.Entry(cantidad_frame, textvariable=cantidad_var,
                                 font=("Segoe UI", 11), bg="#23272a", fg="#ffffff")
    cantidad_entry.pack(fill="x", expand=False, padx=1, pady=0)
    
    # Campo Camera (90px) - Exacto al ancho de columna
    camera_frame = tk.Frame(entry_frame, bg="#23272a", width=90, height=60)
    camera_frame.pack(side="left", padx=0, pady=5)
    camera_frame.pack_propagate(False)
    
    # Label para Camera (centrado)
    tk.Label(camera_frame, text="Camera", bg="#23272a", fg="#a3c9f9",
            font=("Segoe UI", 9, "bold")).pack(anchor="center", padx=2, pady=(0, 2))
    
    if UI is not None:
        camera_entry = UI.CTkEntry(camera_frame, textvariable=camera_var,
                                   font=("Segoe UI", 11), height=30,
                                   fg_color="#23272a", text_color="#ffffff",
                                   border_width=2, border_color="#4a90e2",
                                   corner_radius=5)
    else:
        camera_entry = tk.Entry(camera_frame, textvariable=camera_var,
                               font=("Segoe UI", 11), bg="#23272a", fg="#ffffff")
    camera_entry.pack(fill="x", expand=False, padx=1, pady=0)
    
    # Campo Descripción (320px) - Ampliado al eliminar "Out at"
    descripcion_frame = tk.Frame(entry_frame, bg="#23272a", width=320, height=60)
    descripcion_frame.pack(side="left", padx=0, pady=5)
    descripcion_frame.pack_propagate(False)
    
    # Label para Descripción (centrado)
    tk.Label(descripcion_frame, text="Descripción", bg="#23272a", fg="#a3c9f9",
            font=("Segoe UI", 9, "bold")).pack(anchor="center", padx=2, pady=(0, 2))
    
    if UI is not None:
        descripcion_entry = UI.CTkEntry(descripcion_frame, textvariable=descripcion_var,
                                        font=("Segoe UI", 11), height=30,
                                        fg_color="#23272a", text_color="#ffffff",
                                        border_width=2, border_color="#4a90e2",
                                        corner_radius=5,
                                        placeholder_text="Escribe timestamp en formato HH:MM o HH:MM:SS")
        descripcion_entry.pack(fill="x", expand=False, padx=1, pady=0)
    else:
        descripcion_entry = tk.Entry(descripcion_frame, textvariable=descripcion_var,
                                     font=("Segoe UI", 11), bg="#2b4a6f", fg="#ffffff")
        descripcion_entry.pack(fill="x", expand=False, padx=1, pady=0)
    
    # Botón Agregar (al final, después de todas las columnas)
    if UI is not None:
        add_btn = UI.CTkButton(entry_frame, text="➕", width=35, height=35,
                              font=("Segoe UI", 15, "bold"),
                              fg_color="#00c853", hover_color="#00a043",
                              corner_radius=5,
                              command=lambda: None)  # Definiremos después
        add_btn.pack(side="left", padx=5, pady=5)
        add_btn.place(anchor="se", x=-2, y=-4)
    else:
        add_btn = tk.Button(entry_frame, text="➕", bg="#00c853", fg="white",
                           font=("Segoe UI", 15, "bold"), width=3, height=2,
                           command=lambda: None)
    add_btn.pack(side="left", padx=5, pady=5)
    
    # ⭐ FUNCIÓN: Agregar nuevo evento desde el formulario
    def add_event_from_form():
        """Agrega un nuevo evento al sheet desde el formulario de entrada Y LO GUARDA EN LA BD"""
        try:
            # Validar campos obligatorios
            if not sitio_var.get().strip():
                messagebox.showwarning("Campo requerido", "Debes seleccionar un Sitio.", parent=top)
                sitio_combo.focus_set()
                return
            
            if not actividad_var.get().strip():
                messagebox.showwarning("Campo requerido", "Debes seleccionar una Actividad.", parent=top)
                actividad_combo.focus_set()
                return
            
            # Obtener valores
            fecha_str = fecha_var.get().strip()
            if not fecha_str:
                # Usar fecha/hora actual si está vacío
                fecha_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                fecha_var.set(fecha_str)
            
            sitio_str = sitio_var.get().strip()
            actividad_str = actividad_var.get().strip()
            cantidad_str = cantidad_var.get().strip() or "0"
            camera_str = camera_var.get().strip()
            descripcion_str = descripcion_var.get().strip()
            
            # ⭐ GUARDAR DIRECTAMENTE EN LA BASE DE DATOS
            try:
                conn = get_connection()
                if not conn:
                    messagebox.showerror("Error", "No se pudo conectar a la base de datos.", parent=top)
                    return
                
                cur = conn.cursor()
                
                # Obtener ID_Usuario
                cur.execute("SELECT ID_Usuario FROM user WHERE Nombre_Usuario=%s", (username,))
                user_row = cur.fetchone()
                if not user_row:
                    messagebox.showerror("Error", "Usuario no encontrado.", parent=top)
                    cur.close()
                    conn.close()
                    return
                
                id_usuario = user_row[0]
                
                # Parsear fecha/hora
                try:
                    fecha_dt = datetime.strptime(fecha_str, "%Y-%m-%d %H:%M:%S")
                except:
                    messagebox.showerror("Error", "Formato de fecha inválido.\nUsa: YYYY-MM-DD HH:MM:SS", parent=top)
                    cur.close()
                    conn.close()
                    return
                
                # Extraer ID_Sitio del nombre (formato "Nombre (ID)" o "Nombre ID")
                sitio_id = None
                if sitio_str:
                    try:
                        # ⭐ Método 1: Buscar ID entre paréntesis "Nombre (123)"
                        import re
                        match = re.search(r'\((\d+)\)', sitio_str)
                        if match:
                            sitio_id = int(match.group(1))
                        else:
                            # ⭐ Método 2: Formato antiguo "Nombre 123" (fallback)
                            parts = sitio_str.split()
                            if parts:
                                sitio_id = int(parts[-1])
                    except:
                        messagebox.showerror("Error", "Formato de sitio inválido.", parent=top)
                        cur.close()
                        conn.close()
                        return
                
                # Convertir cantidad
                try:
                    cantidad_float = float(cantidad_str) if cantidad_str else 0.0
                except:
                    cantidad_float = 0.0
                
                # ⭐ INSERTAR EN LA BASE DE DATOS
                cur.execute("""
                    INSERT INTO Eventos 
                    (FechaHora, ID_Sitio, Nombre_Actividad, Cantidad, Camera, Descripcion, ID_Usuario)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (fecha_dt, sitio_id, actividad_str, cantidad_float, camera_str, descripcion_str, id_usuario))
                
                conn.commit()
                nuevo_id = cur.lastrowid
                
                cur.close()
                conn.close()
                
                print(f"[DEBUG] Evento guardado en BD con ID: {nuevo_id}")
                
                # Agregar al sheet con el ID real
                new_row = [fecha_str, sitio_str, actividad_str, cantidad_str, camera_str, 
                          descripcion_var.get().strip()]  # Sin columna "Out at"
                current_data = sheet.get_sheet_data()
                
                # Si solo hay mensaje "No hay eventos", limpiar primero
                if len(current_data) == 1 and "No hay" in str(current_data[0][0]):
                    current_data = []
                    row_data_cache.clear()
                    row_ids.clear()
                
                current_data.append(new_row)
                sheet.set_sheet_data(current_data)
                apply_sheet_widths()
                
                # Agregar a cache con status 'saved' (ya está en BD)
                row_data_cache.append({
                    'id': nuevo_id,
                    'fecha_hora': fecha_dt,
                    'sitio_id': sitio_id,
                    'sitio_nombre': sitio_str,
                    'actividad': actividad_str,
                    'cantidad': cantidad_float,
                    'camera': camera_str,
                    'descripcion': descripcion_str,
                    'status': 'saved'  # ⭐ Ya guardado
                })
                row_ids.append(nuevo_id)
                
                # Resaltar fila como guardada (sin highlight especial)
                new_idx = len(current_data) - 1
                sheet.see(row=new_idx, column=0, keep_yscroll=False, keep_xscroll=True)
                
                print(f"[DEBUG] Evento agregado y guardado: fila {new_idx}, ID: {nuevo_id}")
                
                # Limpiar formulario
                fecha_var.set("")
                sitio_var.set("")
                actividad_var.set("")
                cantidad_var.set("0")
                camera_var.set("")
                descripcion_var.set("")
                
                # Focus en Sitio para siguiente entrada
                sitio_combo.focus_set()
                
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo guardar en la BD:\n{e}", parent=top)
                import traceback
                traceback.print_exc()
                
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo agregar el evento:\n{e}", parent=top)
            import traceback
            traceback.print_exc()
            
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo agregar el evento:\n{e}", parent=top)
            import traceback
            traceback.print_exc()
    
    # Conectar el botón
    add_btn.configure(command=add_event_from_form)
    
    # ⭐ FUNCIÓN: DateTimePicker para el formulario
    def open_form_datetime_picker():
        """Abre el selector de fecha/hora para el formulario"""
        show_datetime_picker_form()
    
    fecha_btn.configure(command=open_form_datetime_picker)
    
    def show_datetime_picker_for_edit(row_idx):
        """Selector moderno de fecha/hora para editar registros existentes"""
        try:
            # Verificar que sea una fila válida
            if row_idx >= len(row_data_cache):
                return
            
            # Obtener valor actual
            current_value = sheet.get_cell_data(row_idx, 0)
            if current_value and current_value.strip():
                try:
                    current_dt = datetime.strptime(current_value, "%Y-%m-%d %H:%M:%S")
                except:
                    current_dt = datetime.now()
            else:
                current_dt = datetime.now()
            
            # Crear ventana con CustomTkinter
            if UI is not None:
                picker_win = UI.CTkToplevel(top)
                picker_win.title("Editar Fecha y Hora")
                picker_win.geometry("500x450")
                picker_win.resizable(False, False)
                picker_win.transient(top)
                picker_win.grab_set()
                
                # Header con icono
                header = UI.CTkFrame(picker_win, fg_color="#1a1a1a", corner_radius=0, height=60)
                header.pack(fill="x", padx=0, pady=0)
                header.pack_propagate(False)
                
                UI.CTkLabel(header, text="📅 Editar Fecha y Hora", 
                           font=("Segoe UI", 20, "bold"),
                           text_color="#4a90e2").pack(pady=15)
                
                # Contenido principal
                content = UI.CTkFrame(picker_win, fg_color="transparent")
                content.pack(fill="both", expand=True, padx=20, pady=20)
                
                # Sección de Fecha
                date_section = UI.CTkFrame(content, fg_color="#2b2b2b", corner_radius=10)
                date_section.pack(fill="x", pady=(0, 15))
                
                UI.CTkLabel(date_section, text="📅 Fecha:", 
                           font=("Segoe UI", 14, "bold"),
                           text_color="#e0e0e0").pack(anchor="w", padx=15, pady=(15, 10))
                
                # Frame para calendario (tkcalendar)
                cal_wrapper = tk.Frame(date_section, bg="#2b2b2b")
                cal_wrapper.pack(padx=15, pady=(0, 15))
                
                cal = tkcalendar.DateEntry(cal_wrapper, width=30, background='#4a90e2',
                                           foreground='white', borderwidth=2,
                                           year=current_dt.year, month=current_dt.month, day=current_dt.day,
                                           date_pattern='yyyy-mm-dd',
                                           font=("Segoe UI", 11))
                cal.pack()
                
                # Sección de Hora
                time_section = UI.CTkFrame(content, fg_color="#2b2b2b", corner_radius=10)
                time_section.pack(fill="x", pady=(0, 15))
                
                UI.CTkLabel(time_section, text="🕐 Hora:", 
                           font=("Segoe UI", 14, "bold"),
                           text_color="#e0e0e0").pack(anchor="w", padx=15, pady=(15, 10))
                
                # Variables para hora
                hour_var = tk.IntVar(value=current_dt.hour)
                minute_var = tk.IntVar(value=current_dt.minute)
                second_var = tk.IntVar(value=current_dt.second)
                
                # Frame para spinboxes
                spinbox_container = tk.Frame(time_section, bg="#2b2b2b")
                spinbox_container.pack(padx=15, pady=(0, 10))
                
                # Hora
                tk.Label(spinbox_container, text="Hora:", bg="#2b2b2b", fg="#a3c9f9",
                        font=("Segoe UI", 11)).grid(row=0, column=0, padx=5, pady=5)
                hour_spin = tk.Spinbox(spinbox_container, from_=0, to=23, textvariable=hour_var,
                                      width=8, font=("Segoe UI", 12), justify="center")
                hour_spin.grid(row=0, column=1, padx=5, pady=5)
                
                # Minuto
                tk.Label(spinbox_container, text="Min:", bg="#2b2b2b", fg="#a3c9f9",
                        font=("Segoe UI", 11)).grid(row=0, column=2, padx=5, pady=5)
                minute_spin = tk.Spinbox(spinbox_container, from_=0, to=59, textvariable=minute_var,
                                        width=8, font=("Segoe UI", 12), justify="center")
                minute_spin.grid(row=0, column=3, padx=5, pady=5)
                
                # Segundo
                tk.Label(spinbox_container, text="Seg:", bg="#2b2b2b", fg="#a3c9f9",
                        font=("Segoe UI", 11)).grid(row=0, column=4, padx=5, pady=5)
                second_spin = tk.Spinbox(spinbox_container, from_=0, to=59, textvariable=second_var,
                                        width=8, font=("Segoe UI", 12), justify="center")
                second_spin.grid(row=0, column=5, padx=5, pady=5)
                
                # Botón "Ahora"
                def set_now():
                    now = datetime.now()
                    cal.set_date(now.date())
                    hour_var.set(now.hour)
                    minute_var.set(now.minute)
                    second_var.set(now.second)
                
                UI.CTkButton(time_section, text="⏰ Establecer Hora Actual", command=set_now,
                            fg_color="#4a90e2", hover_color="#3a7bc2",
                            font=("Segoe UI", 11),
                            width=200, height=35).pack(pady=(5, 15))
                
                # Botones Aceptar/Cancelar
                btn_frame = UI.CTkFrame(content, fg_color="transparent")
                btn_frame.pack(pady=10)
                
                def accept():
                    try:
                        selected_date = cal.get_date()
                        selected_time = datetime.strptime(
                            f"{selected_date} {hour_var.get():02d}:{minute_var.get():02d}:{second_var.get():02d}",
                            "%Y-%m-%d %H:%M:%S"
                        )
                        
                        # Actualizar celda
                        formatted = selected_time.strftime("%Y-%m-%d %H:%M:%S")
                        sheet.set_cell_data(row_idx, 0, formatted)
                        
                        # Agregar a pending_changes para auto-guardado
                        if row_idx not in pending_changes:
                            pending_changes.append(row_idx)
                        
                        row_data_cache[row_idx]['fecha_hora'] = selected_time
                        
                        # Guardar automáticamente
                        top.after(500, auto_save_pending)
                        
                        picker_win.destroy()
                    except Exception as e:
                        messagebox.showerror("Error", f"Error al establecer fecha/hora:\n{e}", parent=picker_win)
                
                UI.CTkButton(btn_frame, text="✅ Aceptar", command=accept,
                            fg_color="#00c853", hover_color="#00a043",
                            font=("Segoe UI", 12, "bold"),
                            width=120, height=40).pack(side="left", padx=10)
                
                UI.CTkButton(btn_frame, text="❌ Cancelar", command=picker_win.destroy,
                            fg_color="#666666", hover_color="#555555",
                            font=("Segoe UI", 12),
                            width=120, height=40).pack(side="left", padx=10)
            else:
                # Fallback sin CustomTkinter
                picker_win = tk.Toplevel(top)
                picker_win.title("Editar Fecha y Hora")
                picker_win.geometry("400x400")
                picker_win.transient(top)
                picker_win.grab_set()
                content = tk.Frame(picker_win, bg="#2b2b2b")
                content.pack(fill="both", expand=True, padx=20, pady=20)
                
                tk.Label(content, text="Fecha:", bg="#2b2b2b", fg="#ffffff",
                        font=("Segoe UI", 12, "bold")).pack(anchor="w", pady=(10,5))
                
                cal = tkcalendar.DateEntry(content, width=25, background='#4a90e2',
                                          foreground='white', borderwidth=2,
                                          year=current_dt.year, month=current_dt.month, day=current_dt.day)
                cal.pack(pady=5, fill="x")
                
                tk.Label(content, text="Hora:", bg="#2b2b2b", fg="#ffffff",
                        font=("Segoe UI", 12, "bold")).pack(anchor="w", pady=(20,5))
                
                time_frame = tk.Frame(content, bg="#2b2b2b")
                time_frame.pack(fill="x", pady=5)
                
                hour_var = tk.IntVar(value=current_dt.hour)
                minute_var = tk.IntVar(value=current_dt.minute)
                second_var = tk.IntVar(value=current_dt.second)
                
                hour_spin = tk.Spinbox(time_frame, from_=0, to=23, textvariable=hour_var, width=8)
                hour_spin.pack(side="left", padx=5)
                minute_spin = tk.Spinbox(time_frame, from_=0, to=59, textvariable=minute_var, width=8)
                minute_spin.pack(side="left", padx=5)
                second_spin = tk.Spinbox(time_frame, from_=0, to=59, textvariable=second_var, width=8)
                second_spin.pack(side="left", padx=5)
                
                def accept():
                    selected_date = cal.get_date()
                    selected_time = datetime.strptime(
                        f"{selected_date} {hour_var.get():02d}:{minute_var.get():02d}:{second_var.get():02d}",
                        "%Y-%m-%d %H:%M:%S"
                    )
                    formatted = selected_time.strftime("%Y-%m-%d %H:%M:%S")
                    sheet.set_cell_data(row_idx, 0, formatted)
                    
                    if row_idx not in pending_changes:
                        pending_changes.append(row_idx)
                    row_data_cache[row_idx]['fecha_hora'] = selected_time
                    
                    # Guardar automáticamente
                    top.after(500, auto_save_pending)
                    
                    picker_win.destroy()
                
                btn_frame = tk.Frame(content, bg="#2b2b2b")
                btn_frame.pack(side="bottom", pady=20)
                tk.Button(btn_frame, text="Aceptar", command=accept, bg="#00c853", fg="white", width=10).pack(side="left", padx=5)
                tk.Button(btn_frame, text="Cancelar", command=picker_win.destroy, bg="#666666", fg="white", width=10).pack(side="left", padx=5)
            
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo abrir selector:\n{e}", parent=top)
            import traceback
            traceback.print_exc()
    
    def show_datetime_picker_form():
        """Selector moderno de fecha/hora para el formulario de entrada"""
        try:
            # Fecha actual como defecto
            now = datetime.now()
            
            # Crear ventana con CustomTkinter
            if UI is not None:
                picker_win = UI.CTkToplevel(top)
                picker_win.title("Seleccionar Fecha y Hora")
                picker_win.geometry("500x450")
                picker_win.resizable(False, False)
                picker_win.transient(top)
                picker_win.grab_set()
                
                # Header con icono
                header = UI.CTkFrame(picker_win, fg_color="#1a1a1a", corner_radius=0, height=60)
                header.pack(fill="x", padx=0, pady=0)
                header.pack_propagate(False)
                
                UI.CTkLabel(header, text="📅 Seleccionar Fecha y Hora", 
                           font=("Segoe UI", 20, "bold"),
                           text_color="#4a90e2").pack(pady=15)
                
                # Contenido principal
                content = UI.CTkFrame(picker_win, fg_color="transparent")
                content.pack(fill="both", expand=True, padx=20, pady=20)
                
                # Sección de Fecha
                date_section = UI.CTkFrame(content, fg_color="#2b2b2b", corner_radius=10)
                date_section.pack(fill="x", pady=(0, 15))
                
                UI.CTkLabel(date_section, text="📅 Fecha:", 
                           font=("Segoe UI", 14, "bold"),
                           text_color="#e0e0e0").pack(anchor="w", padx=15, pady=(15, 10))
                
                # Frame para calendario (tkcalendar)
                cal_wrapper = tk.Frame(date_section, bg="#2b2b2b")
                cal_wrapper.pack(padx=15, pady=(0, 15))
                
                cal = tkcalendar.DateEntry(cal_wrapper, width=30, background='#4a90e2',
                                           foreground='white', borderwidth=2,
                                           year=now.year, month=now.month, day=now.day,
                                           date_pattern='yyyy-mm-dd',
                                           font=("Segoe UI", 11))
                cal.pack()
                
                # Sección de Hora
                time_section = UI.CTkFrame(content, fg_color="#2b2b2b", corner_radius=10)
                time_section.pack(fill="x", pady=(0, 15))
                
                UI.CTkLabel(time_section, text="🕐 Hora:", 
                           font=("Segoe UI", 14, "bold"),
                           text_color="#e0e0e0").pack(anchor="w", padx=15, pady=(15, 10))
                
                # Variables para hora
                hour_var = tk.IntVar(value=now.hour)
                minute_var = tk.IntVar(value=now.minute)
                second_var = tk.IntVar(value=now.second)
                
                # Frame para spinboxes
                spinbox_container = tk.Frame(time_section, bg="#2b2b2b")
                spinbox_container.pack(padx=15, pady=(0, 10))
                
                # Hora
                tk.Label(spinbox_container, text="Hora:", bg="#2b2b2b", fg="#a3c9f9",
                        font=("Segoe UI", 11)).grid(row=0, column=0, padx=5, pady=5)
                hour_spin = tk.Spinbox(spinbox_container, from_=0, to=23, textvariable=hour_var,
                                      width=8, font=("Segoe UI", 12), justify="center")
                hour_spin.grid(row=0, column=1, padx=5, pady=5)
                
                # Minuto
                tk.Label(spinbox_container, text="Min:", bg="#2b2b2b", fg="#a3c9f9",
                        font=("Segoe UI", 11)).grid(row=0, column=2, padx=5, pady=5)
                minute_spin = tk.Spinbox(spinbox_container, from_=0, to=59, textvariable=minute_var,
                                        width=8, font=("Segoe UI", 12), justify="center")
                minute_spin.grid(row=0, column=3, padx=5, pady=5)
                
                # Segundo
                tk.Label(spinbox_container, text="Seg:", bg="#2b2b2b", fg="#a3c9f9",
                        font=("Segoe UI", 11)).grid(row=0, column=4, padx=5, pady=5)
                second_spin = tk.Spinbox(spinbox_container, from_=0, to=59, textvariable=second_var,
                                        width=8, font=("Segoe UI", 12), justify="center")
                second_spin.grid(row=0, column=5, padx=5, pady=5)
                
                # Botón "Ahora"
                def set_now():
                    current = datetime.now()
                    cal.set_date(current.date())
                    hour_var.set(current.hour)
                    minute_var.set(current.minute)
                    second_var.set(current.second)
                
                UI.CTkButton(time_section, text="⏰ Establecer Hora Actual", command=set_now,
                            fg_color="#4a90e2", hover_color="#3a7bc2",
                            font=("Segoe UI", 11),
                            width=200, height=35).pack(pady=(5, 15))
                
                # Botones Aceptar/Cancelar
                btn_frame = UI.CTkFrame(content, fg_color="transparent")
                btn_frame.pack(pady=10)
                
                def accept():
                    try:
                        selected_date = cal.get_date()
                        selected_time = datetime.strptime(
                            f"{selected_date} {hour_var.get():02d}:{minute_var.get():02d}:{second_var.get():02d}",
                            "%Y-%m-%d %H:%M:%S"
                        )
                        
                        # Establecer en el formulario
                        fecha_var.set(selected_time.strftime("%Y-%m-%d %H:%M:%S"))
                        picker_win.destroy()
                    except Exception as e:
                        messagebox.showerror("Error", f"Error al establecer fecha/hora:\n{e}", parent=picker_win)
                
                UI.CTkButton(btn_frame, text="✅ Aceptar", command=accept,
                            fg_color="#00c853", hover_color="#00a043",
                            font=("Segoe UI", 12, "bold"),
                            width=120, height=40).pack(side="left", padx=10)
                
                UI.CTkButton(btn_frame, text="❌ Cancelar", command=picker_win.destroy,
                            fg_color="#666666", hover_color="#555555",
                            font=("Segoe UI", 12),
                            width=120, height=40).pack(side="left", padx=10)
            else:
                # Fallback sin CustomTkinter
                picker_win = tk.Toplevel(top)
                picker_win.title("Seleccionar Fecha y Hora")
                picker_win.geometry("400x400")
                picker_win.transient(top)
                picker_win.grab_set()
                content = tk.Frame(picker_win, bg="#2b2b2b")
                content.pack(fill="both", expand=True, padx=20, pady=20)
                
                tk.Label(content, text="Fecha:", bg="#2b2b2b", fg="#ffffff",
                        font=("Segoe UI", 12, "bold")).pack(anchor="w", pady=(10,5))
                
                cal = tkcalendar.DateEntry(content, width=25, background='#4a90e2',
                                          foreground='white', borderwidth=2,
                                          year=now.year, month=now.month, day=now.day)
                cal.pack(pady=5, fill="x")
                
                tk.Label(content, text="Hora:", bg="#2b2b2b", fg="#ffffff",
                        font=("Segoe UI", 12, "bold")).pack(anchor="w", pady=(20,5))
                
                time_frame = tk.Frame(content, bg="#2b2b2b")
                time_frame.pack(fill="x", pady=5)
                
                hour_var = tk.IntVar(value=now.hour)
                minute_var = tk.IntVar(value=now.minute)
                second_var = tk.IntVar(value=now.second)
                
                hour_spin = tk.Spinbox(time_frame, from_=0, to=23, textvariable=hour_var, width=8)
                hour_spin.pack(side="left", padx=5)
                minute_spin = tk.Spinbox(time_frame, from_=0, to=59, textvariable=minute_var, width=8)
                minute_spin.pack(side="left", padx=5)
                second_spin = tk.Spinbox(time_frame, from_=0, to=59, textvariable=second_var, width=8)
                second_spin.pack(side="left", padx=5)
                
                def accept():
                    selected_date = cal.get_date()
                    selected_time = datetime.strptime(
                        f"{selected_date} {hour_var.get():02d}:{minute_var.get():02d}:{second_var.get():02d}",
                        "%Y-%m-%d %H:%M:%S"
                    )
                    fecha_var.set(selected_time.strftime("%Y-%m-%d %H:%M:%S"))
                    picker_win.destroy()
                
                btn_frame = tk.Frame(content, bg="#2b2b2b")
                btn_frame.pack(side="bottom", pady=20)
                tk.Button(btn_frame, text="Aceptar", command=accept, bg="#00c853", fg="white", width=10).pack(side="left", padx=5)
                tk.Button(btn_frame, text="Cancelar", command=picker_win.destroy, bg="#666666", fg="white", width=10).pack(side="left", padx=5)
            
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo abrir selector:\n{e}", parent=top)
            import traceback
            traceback.print_exc()
    
    # ⭐ VINCULAR ENTER EN TODOS LOS CAMPOS DEL FORMULARIO
    def on_form_enter(event):
        """Ejecuta agregar cuando se presiona Enter en el formulario"""
        add_event_from_form()
        return "break"
    
    # Aplicar binding a todos los campos
    fecha_entry.bind("<Return>", on_form_enter)
    fecha_entry.bind("<KP_Enter>", on_form_enter)
    sitio_combo.bind("<Return>", on_form_enter)
    sitio_combo.bind("<KP_Enter>", on_form_enter)
    actividad_combo.bind("<Return>", on_form_enter)
    actividad_combo.bind("<KP_Enter>", on_form_enter)
    cantidad_entry.bind("<Return>", on_form_enter)
    cantidad_entry.bind("<KP_Enter>", on_form_enter)
    camera_entry.bind("<Return>", on_form_enter)
    camera_entry.bind("<KP_Enter>", on_form_enter)
    descripcion_entry.bind("<Return>", on_form_enter)
    descripcion_entry.bind("<KP_Enter>", on_form_enter)
    
    # Focus inicial en Sitio
    sitio_combo.focus_set()

    def apply_sheet_widths():
        """Aplica anchos personalizados a las columnas"""
        for idx, col_name in enumerate(columns):
            if col_name in custom_widths:
                sheet.column_width(idx, custom_widths[col_name])
        sheet.redraw()

    def get_last_shift_start():
        """Obtiene la última hora de inicio de shift del usuario"""
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
            print(f"[ERROR] get_last_shift_start: {e}")
            return None

    def load_daily():
        """Carga eventos del turno actual desde la base de datos (MODO DAILY)"""
        nonlocal row_data_cache, row_ids, pending_changes
        
        try:
            last_shift_time = get_last_shift_start()
            if last_shift_time is None:
                data = [["No hay shift activo"] + [""] * (len(columns)-1)]
                sheet.set_sheet_data(data)
                apply_sheet_widths()
                row_data_cache.clear()
                row_ids.clear()
                pending_changes.clear()
                return

            conn = get_connection()
            cur = conn.cursor()
            
            # Obtener eventos del usuario desde el último shift
            cur.execute("""
                SELECT 
                    e.ID_Eventos,
                    e.FechaHora,
                    e.ID_Sitio,
                    e.Nombre_Actividad,
                    e.Cantidad,
                    e.Camera,
                    e.Descripcion
                FROM Eventos e
                INNER JOIN user u ON e.ID_Usuario = u.ID_Usuario
                WHERE u.Nombre_Usuario = %s AND e.FechaHora >= %s
                ORDER BY e.FechaHora ASC
            """, (username, last_shift_time))

            eventos = cur.fetchall()
            
            row_data_cache.clear()
            row_ids.clear()
            display_rows = []

            for evento in eventos:
                (id_evento, fecha_hora, id_sitio, nombre_actividad, cantidad, camera, descripcion) = evento

                # Resolver Nombre_Sitio desde ID_Sitio
                try:
                    cur.execute("SELECT Nombre_Sitio FROM Sitios WHERE ID_Sitio = %s", (id_sitio,))
                    sit_row = cur.fetchone()
                    # ⭐ Formato consistente: "Nombre (ID)" igual que en load_specials
                    nombre_sitio = f"{sit_row[0]} ({id_sitio})" if sit_row else f"ID: {id_sitio}"
                except Exception:
                    nombre_sitio = f"ID: {id_sitio}"

                # Formatear fecha/hora
                fecha_str = fecha_hora.strftime("%Y-%m-%d %H:%M:%S") if fecha_hora else ""

                # Guardar en cache
                row_data_cache.append({
                    'id': id_evento,
                    'fecha_hora': fecha_hora,
                    'sitio_id': id_sitio,
                    'sitio_nombre': nombre_sitio,
                    'actividad': nombre_actividad or "",
                    'cantidad': cantidad or 0,
                    'camera': camera or "",
                    'descripcion': descripcion or "",
                    'status': 'saved'
                })
                row_ids.append(id_evento)

                # Fila para mostrar
                display_rows.append([
                    fecha_str,
                    nombre_sitio,
                    nombre_actividad or "",
                    str(cantidad) if cantidad is not None else "0",
                    camera or "",
                    descripcion or ""
                ])

            cur.close()
            conn.close()

            if not display_rows:
                display_rows = [["No hay eventos en este turno"] + [""] * (len(columns)-1)]
                row_data_cache.clear()
                row_ids.clear()

            sheet.set_sheet_data(display_rows)
            
            # ⭐ LIMPIAR COLORES (solo Specials tiene colores)
            sheet.dehighlight_all()
            
            apply_sheet_widths()
            pending_changes.clear()

            print(f"[DEBUG] Loaded {len(row_ids)} events for {username}")

        except Exception as e:
            messagebox.showerror("Error", f"No se pudo cargar eventos:\n{e}", parent=top)
            traceback.print_exc()

    def load_specials():
            """Carga eventos de grupos especiales (AS, KG, HUD, PE, SCH, WAG, LT, DT) desde el último START SHIFT (MODO SPECIALS)"""
            nonlocal row_data_cache, row_ids, pending_changes
            
            try:
                # Obtener último START SHIFT del supervisor
                last_shift_time = get_last_shift_start()
                if last_shift_time is None:
                    data = [["No hay shift activo"] + [""] * (len(columns)-1)]
                    sheet.set_sheet_data(data)
                    apply_sheet_widths()
                    row_data_cache.clear()
                    row_ids.clear()
                    pending_changes.clear()
                    return

                # Grupos especiales a filtrar (como open_report_window)
                grupos_especiales = ("AS", "KG", "HUD", "PE", "SCH", "WAG", "LT", "DT")
                
                conn = get_connection()
                cur = conn.cursor()
                
                # Obtener ID_Usuario del supervisor
                cur.execute("SELECT ID_Usuario FROM user WHERE Nombre_Usuario = %s", (username,))
                user_row = cur.fetchone()
                if not user_row:
                    messagebox.showerror("Error", f"Usuario '{username}' no encontrado.", parent=top)
                    cur.close()
                    conn.close()
                    return
                user_id = int(user_row[0])
                
                # Query: EVENTOS de grupos especiales desde START SHIFT hasta AHORA
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
                
                cur.execute(query, (username, *grupos_especiales, last_shift_time))
                rows = cur.fetchall()
                
                # ⭐ Load timezone offset configuration
                tz_adjust = load_tz_config()
                
                # Resolver nombres de sitios y zonas horarias
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
                    
                    # ⭐ GUARDAR VALORES ORIGINALES (antes de ajustes de timezone)
                    fecha_hora_original = r[1]  # Fecha original de BD
                    descripcion_original = str(r[6]) if r[6] else ""  # Guardar copia del valor original
                    usuario_original = usuario  # Usuario original de BD
                    
                    # Resolver nombre de sitio y zona horaria
                    nombre_sitio = ""
                    tz = ""
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
                    
                    # Formato visual para ID_Sitio (mostrar nombre + ID)
                    if id_sitio and nombre_sitio:
                        display_site = f"{nombre_sitio} ({id_sitio})"
                    elif id_sitio:
                        display_site = str(id_sitio)
                    else:
                        display_site = nombre_sitio or ""
                    
                    # ⭐ Formatear fecha/hora CON ajuste de zona horaria
                    try:
                        # Get timezone offset for this site
                        tz_offset_hours = tz_adjust.get((tz or '').upper(), 0)
                        
                        # Apply offset to datetime
                        if isinstance(fecha_hora, str):
                            fh = datetime.strptime(fecha_hora[:19], "%Y-%m-%d %H:%M:%S")
                        else:
                            fh = fecha_hora
                        
                        fh_adjusted = fh + timedelta(hours=tz_offset_hours)
                        fecha_str = fh_adjusted.strftime("%Y-%m-%d %H:%M:%S")
                    except Exception:
                        fecha_str = fecha_hora.strftime("%Y-%m-%d %H:%M:%S") if fecha_hora else ""
                    
                    # ⭐ Ajustar timestamps dentro de la descripción
                    # Soporta formatos: [HH:MM:SS], [H:MM:SS], HH:MM:SS, H:MM:SS, [HH:MM], [H:MM], HH:MM, H:MM
                    if descripcion:
                        try:
                            desc_text = str(descripcion)
                            
                            # Normalizar formato: convertir [Timestamp: XX:XX:XX] a [XX:XX:XX]
                            # Soporta HH:MM:SS y H:MM:SS
                            desc_text = re.sub(r"\[?\s*Timestamp:\s*(\d{1,2}:\d{2}:\d{2})\s*\]?", r"[\1]", desc_text, flags=re.IGNORECASE)
                            # Soporta HH:MM y H:MM
                            desc_text = re.sub(r"\[?\s*Timestamp:\s*(\d{1,2}:\d{2})\s*\]?", r"[\1]", desc_text, flags=re.IGNORECASE)
                            
                            # Función para ajustar un timestamp (soporta H:MM, HH:MM, H:MM:SS, HH:MM:SS)
                            def adjust_timestamp(match):
                                raw_time = match.group(1) if match.lastindex >= 1 else match.group(0)
                                # Guardar si tiene corchetes al inicio
                                has_brackets = match.group(0).startswith('[')
                                
                                try:
                                    # Usar la fecha del evento como base
                                    base_date = fh.date() if 'fh' in locals() and isinstance(fh, datetime) else datetime.now().date()
                                    
                                    # Parsear el tiempo (puede ser H:MM:SS, HH:MM:SS, H:MM o HH:MM)
                                    time_parts = raw_time.split(":")
                                    if len(time_parts) == 3:
                                        # Formato H:MM:SS o HH:MM:SS
                                        hh, mm, ss = [int(x) for x in time_parts]
                                    elif len(time_parts) == 2:
                                        # Formato H:MM o HH:MM (asumir segundos = 00)
                                        hh, mm = [int(x) for x in time_parts]
                                        ss = 0
                                    elif len(time_parts) == 1:
                                        # Formato H (solo hora, asumir minutos y segundos = 00)
                                        hh = int(time_parts[0])
                                        mm = 0
                                        ss = 0
                                    else:
                                        return match.group(0)  # Formato no reconocido
                                    
                                    # Validar rangos
                                    if not (0 <= hh <= 23 and 0 <= mm <= 59 and 0 <= ss <= 59):
                                        return match.group(0)  # Valores fuera de rango
                                    
                                    desc_dt = datetime.combine(base_date, datetime.min.time()) + timedelta(hours=hh, minutes=mm, seconds=ss)
                                    
                                    # Aplicar el mismo offset de zona horaria
                                    desc_dt_adjusted = desc_dt + timedelta(hours=tz_offset_hours)
                                    
                                    # Mantener el formato original (con o sin ceros a la izquierda)
                                    if len(time_parts) == 3:
                                        # Formato con segundos
                                        if len(time_parts[0]) == 1:
                                            # Formato H:MM:SS (sin cero a la izquierda)
                                            desc_time_adjusted_str = f"{desc_dt_adjusted.hour}:{desc_dt_adjusted.minute:02d}:{desc_dt_adjusted.second:02d}"
                                        else:
                                            # Formato HH:MM:SS (con cero a la izquierda)
                                            desc_time_adjusted_str = desc_dt_adjusted.strftime("%H:%M:%S")
                                    elif len(time_parts) == 2:
                                        # Formato sin segundos
                                        if len(time_parts[0]) == 1:
                                            # Formato H:MM (sin cero a la izquierda)
                                            desc_time_adjusted_str = f"{desc_dt_adjusted.hour}:{desc_dt_adjusted.minute:02d}"
                                        else:
                                            # Formato HH:MM (con cero a la izquierda)
                                            desc_time_adjusted_str = desc_dt_adjusted.strftime("%H:%M")
                                    else:
                                        # Formato solo hora
                                        desc_time_adjusted_str = desc_dt_adjusted.strftime("%H:%M")
                                    
                                    # Mantener el formato original (con o sin corchetes)
                                    if has_brackets:
                                        return f"[{desc_time_adjusted_str}]"
                                    else:
                                        return desc_time_adjusted_str
                                except Exception as e:
                                    print(f"[DEBUG] Error ajustando timestamp '{raw_time}': {e}")
                                    return match.group(0)  # Retornar original si hay error
                            
                            # ⭐ ORDEN DE PROCESAMIENTO: Del más específico al más general
                            
                            # 1. Timestamps con corchetes y segundos: [HH:MM:SS] o [H:MM:SS]
                            desc_text_adjusted = re.sub(r"\[(\d{1,2}:\d{2}:\d{2})\]", adjust_timestamp, desc_text)
                            
                            # 2. Timestamps con corchetes sin segundos: [HH:MM] o [H:MM]
                            desc_text_adjusted = re.sub(r"\[(\d{1,2}:\d{2})\]", adjust_timestamp, desc_text_adjusted)
                            
                            # 3. Timestamps SIN corchetes con segundos: HH:MM:SS o H:MM:SS
                            # Lookahead/lookbehind para evitar coincidir con fechas completas o timestamps ya procesados
                            desc_text_adjusted = re.sub(
                                r"(?<!\d)(\d{1,2}:\d{2}:\d{2})(?!\])",  # No debe tener ] después
                                adjust_timestamp,
                                desc_text_adjusted
                            )
                            
                            # 4. Timestamps SIN corchetes sin segundos: HH:MM o H:MM
                            # Evitar coincidir con HH:MM:SS (que ya fueron procesados)
                            desc_text_adjusted = re.sub(
                                r"(?<!\d)(\d{1,2}:\d{2})(?!:\d|\])",  # No debe tener :dígito después ni ]
                                adjust_timestamp,
                                desc_text_adjusted
                            )
                            
                            descripcion = desc_text_adjusted
                            
                        except Exception:
                            # Mantener descripción original si hay error
                            pass
                    
                    # ⭐ VERIFICAR ESTADO EN TABLA SPECIALS (3 estados posibles)
                    mark_display = ""  # Por defecto: vacío (sin enviar)
                    mark_color = None  # None = sin color, "green" = enviado, "amber" = pendiente
                    
                    try:
                        # ⭐ Buscar usando la fecha AJUSTADA (con timezone) porque así se guarda en specials
                        # fecha_str ya tiene el ajuste de timezone aplicado
                        
                        # Buscar si existe en specials (MISMO CRITERIO que on_window_close y accion_supervisores)
                        cur.execute(
                            """
                            SELECT ID_special, Supervisor, FechaHora, ID_Sitio, Nombre_Actividad, 
                                Cantidad, Camera, Descripcion
                            FROM specials
                            WHERE FechaHora = %s
                            AND Usuario = %s
                            AND Nombre_Actividad = %s
                            AND IFNULL(ID_Sitio, 0) = IFNULL(%s, 0)
                            LIMIT 1
                            """,
                            (fecha_str, usuario_original, nombre_actividad, id_sitio),
                        )
                        special_row = cur.fetchone()
                        
                        if special_row:
                            # Existe en specials - USAR VALORES DE SPECIALS para mostrar
                            special_supervisor = special_row[1]
                            special_fechahora = special_row[2]
                            special_id_sitio = special_row[3]
                            special_actividad = special_row[4]
                            special_cantidad = special_row[5]
                            special_camera = special_row[6]
                            special_desc = special_row[7]
                            
                            # ⭐ IMPORTANTE: Para comparar, usar valores AJUSTADOS de Eventos
                            # (porque accion_supervisores() y on_window_close() guardan valores ajustados en specials)
                            
                            # Normalizar valores de Eventos (con ajuste de timezone aplicado)
                            try:
                                eventos_cantidad = int(cantidad) if cantidad is not None and str(cantidad).strip() else 0
                            except (ValueError, TypeError):
                                eventos_cantidad = 0
                            eventos_camera = str(camera).strip() if camera else ""
                            eventos_desc = str(descripcion).strip() if descripcion else ""  # ⭐ Usar descripcion AJUSTADA
                            
                            # Normalizar valores de specials (convertir a tipos comparables)
                            try:
                                specials_cantidad = int(special_cantidad) if special_cantidad is not None and str(special_cantidad).strip() else 0
                            except (ValueError, TypeError):
                                specials_cantidad = 0
                            specials_camera = str(special_camera).strip() if special_camera else ""
                            specials_desc = str(special_desc).strip() if special_desc else ""
                            
                            # Comparar valores normalizados
                            if (eventos_cantidad != specials_cantidad or 
                                eventos_camera != specials_camera or 
                                eventos_desc != specials_desc):
                                # HAY CAMBIOS: Estado "Pendiente por actualizar"
                                mark_display = "⏳ Pendiente por actualizar"
                                mark_color = "amber"
                                
                                # USAR VALORES DE EVENTOS (ajustados) para mostrar cuando hay cambios pendientes
                                fecha_str_display = fecha_str
                                descripcion_display = descripcion
                            else:
                                # SIN CAMBIOS: Estado "Enviado a @supervisor"
                                mark_display = f"✅ Enviado a {special_supervisor}"
                                mark_color = "green"
                                
                                # USAR VALORES DE SPECIALS para mostrar cuando está enviado sin cambios
                                fecha_str_display = special_fechahora if special_fechahora else fecha_str
                                descripcion_display = special_desc if special_desc else descripcion
                        else:
                            # NO EXISTE EN SPECIALS: Estado vacío (sin enviar)
                            mark_display = ""
                            mark_color = None
                            
                            # USAR VALORES DE EVENTOS (ajustados) para mostrar
                            fecha_str_display = fecha_str
                            descripcion_display = descripcion
                            
                    except Exception:
                        mark_display = ""
                        mark_color = None
                        fecha_str_display = fecha_str
                        descripcion_display = descripcion
                    
                    # Fila para mostrar (SIN columnas ID y Usuario)
                    # Columnas: ["Fecha_hora", "ID_Sitio", "Nombre_Actividad", "Cantidad", "Camera", "Descripcion", "Time_Zone", "Marca"]
                    display_row = [
                        fecha_str_display,        # Fecha_hora (de specials si enviado, de eventos si no)
                        display_site,             # ID_Sitio
                        nombre_actividad or "",   # Nombre_Actividad
                        str(cantidad) if cantidad is not None else "0",  # Cantidad
                        camera or "",             # Camera
                        descripcion_display,      # Descripcion (de specials si enviado, de eventos si no)
                        tz or "",                 # Time_Zone
                        mark_display              # Marca (vacío, enviado, o pendiente)
                    ]
                    
                    processed.append({
                        'id': id_evento,
                        'values': display_row,
                        'mark_color': mark_color  # Para aplicar color después
                    })
                
                cur.close()
                conn.close()
                
                # Actualizar cache
                row_data_cache = processed
                row_ids = [item['id'] for item in processed]
                
                # Poblar sheet
                if not processed:
                    data = [["No hay eventos de grupos especiales en este turno"] + [""] * (len(columns)-1)]
                    sheet.set_sheet_data(data)
                else:
                    data = [item['values'] for item in processed]
                    sheet.set_sheet_data(data)
                    
                    # ⭐ APLICAR COLORES según estado de marca
                    sheet.dehighlight_all()  # Limpiar colores anteriores
                    
                    for idx, item in enumerate(processed):
                        mark_color = item.get('mark_color')
                        if mark_color == 'green':
                            # Verde (#00c853) para "Enviado"
                            sheet.highlight_rows([idx], bg="#00c853", fg="#111111")
                        elif mark_color == 'amber':
                            # Ámbar (#f5a623) para "Pendiente por actualizar"
                            sheet.highlight_rows([idx], bg="#f5a623", fg="#111111")
                        # Sin color si mark_color es None (sin enviar)
                
                apply_sheet_widths()
                pending_changes.clear()
                
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo cargar eventos especiales:\n{e}", parent=top)
                traceback.print_exc()
                pending_changes.clear()
                
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo cargar specials:\n{e}", parent=top)
                traceback.print_exc()
    
    def load_covers():
        """Carga covers desde el último START SHIFT filtrados por username (MODO COVERS)
        Incluye covers normales (con programación) y covers de emergencia (sin programación)"""
        nonlocal row_data_cache, row_ids, pending_changes
        
        try:
            # Obtener último START SHIFT del usuario
            last_shift_time = get_last_shift_start()
            if last_shift_time is None:
                sheet.set_sheet_data([["No hay START SHIFT registrado. Inicia un turno primero.", "", "", "", "", ""]])
                row_data_cache.clear()
                row_ids.clear()
                apply_sheet_widths()
                return
            
            conn = get_connection()
            cur = conn.cursor()
            
            # Query: Covers del usuario desde START SHIFT hasta AHORA, ordenados de más antiguo a más reciente
            # ⭐ LEFT JOIN con covers_programados para incluir covers de emergencia (ID_programacion_covers NULL)
            query = """
                SELECT 
                    cr.ID_Covers,
                    cr.Nombre_usuarios,
                    cr.Cover_in,
                    cr.Cover_out,
                    cr.Covered_by,
                    cr.Motivo,
                    cp.Time_request,
                    cr.ID_programacion_covers
                FROM Covers_realizados cr
                LEFT JOIN covers_programados cp ON cr.ID_programacion_covers = cp.ID_Cover
                WHERE cr.Nombre_Usuarios = %s
                    AND cr.Cover_in >= %s
                ORDER BY cr.Cover_in ASC
            """
            
            cur.execute(query, (username, last_shift_time))
            rows = cur.fetchall()
            
            row_data_cache.clear()
            row_ids.clear()
            display_rows = []
            
            for r in rows:
                id_cover = r[0]
                nombre_usuario = r[1] if r[1] else ""
                cover_in = r[2]
                cover_out = r[3]
                covered_by = r[4] if r[4] else ""
                motivo = r[5] if r[5] else ""
                time_request = r[6]  # Time_request de covers_programados (puede ser NULL en emergencias)
                id_programacion = r[7]  # ID_programacion_covers para detectar emergencias
                
                # ⭐ Detectar cover de emergencia (sin programación)
                is_emergency = (id_programacion is None)
                
                # Formatear fechas
                if is_emergency:
                    time_request_str = "⚠️ EMERGENCIA"  # Marcador visual para covers de emergencia
                else:
                    time_request_str = time_request.strftime("%Y-%m-%d %H:%M:%S") if time_request else ""
                
                cover_in_str = cover_in.strftime("%Y-%m-%d %H:%M:%S") if cover_in else ""
                cover_out_str = cover_out.strftime("%Y-%m-%d %H:%M:%S") if cover_out else ""
                
                # Covers realizados siempre están cerrados (no tienen campo Activo en la tabla)
                activo_str = "Cerrado"
                
                # Construir fila SIN ID_Covers (no se muestra al usuario)
                # Ahora incluye Time_request al inicio (o "EMERGENCIA" si es cover de emergencia)
                display_row = [
                    nombre_usuario,
                    time_request_str,
                    cover_in_str,
                    cover_out_str,
                    motivo,
                    covered_by,
                    activo_str
                ]
                
                display_rows.append(display_row)
                
                # Guardar en cache con indicador de emergencia
                row_data_cache.append({
                    'id_cover': id_cover,
                    'cover_in': cover_in,
                    'cover_out': cover_out,
                    'motivo': motivo,
                    'covered_by': covered_by,
                    'is_emergency': is_emergency,
                    'status': 'saved'
                })
                row_ids.append(id_cover)
            
            cur.close()
            conn.close()
            
            if not display_rows:
                sheet.set_sheet_data([["No hay covers registrados desde el último START SHIFT.", "", "", "", "", ""]])
                row_data_cache.clear()
                row_ids.clear()
            else:
                sheet.set_sheet_data(display_rows)
            
            # Limpiar colores (no se aplica highlight a covers de emergencia)
            sheet.dehighlight_all()
            
            apply_sheet_widths()
            pending_changes.clear()
            
            print(f"[DEBUG] Loaded {len(row_ids)} covers for {username} (includes emergency covers)")
            
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo cargar covers:\n{e}", parent=top)
            traceback.print_exc()
            pending_changes.clear()

    def update_cover_queue_position():
        """Calcula y muestra cuántos turnos faltan para el cover del usuario"""
        try:
            conn = get_connection()
            cur = conn.cursor()
            
            # Buscar todos los covers programados activos (is_Active = 1) ordenados por Time_request
            cur.execute("""
                SELECT ID_user, Time_request, is_Active 
                FROM covers_programados 
                WHERE is_Active = 1 
                ORDER BY Time_request ASC
            """)
            active_covers = cur.fetchall()
            
            # Buscar si el usuario actual tiene un cover programado activo
            user_position = None
            for idx, row in enumerate(active_covers):
                if row[0] == username:  # ID_user == username
                    user_position = idx + 1  # Posición 1-indexed
                    break
            
            cur.close()
            conn.close()
            
            # Actualizar el label
            if user_position is not None:
                if user_position == 1:
                    text = "⭐ ¡Eres el siguiente! Estás en turno #1 para tu cover"
                else:
                    text = f"📋 Estás a {user_position} turnos para tu cover"
                
                if UI is not None:
                    cover_queue_label.configure(text=text, text_color="#00ff88")
                else:
                    cover_queue_label.configure(text=text, fg="#00ff88")
            else:
                text = "ℹ️ No tienes covers programados activos"
                if UI is not None:
                    cover_queue_label.configure(text=text, text_color="#ffa500")
                else:
                    cover_queue_label.configure(text=text, fg="#ffa500")
            
            print(f"[DEBUG] Cover queue position for {username}: {user_position}")
            
        except Exception as e:
            print(f"[ERROR] update_cover_queue_position: {e}")
            traceback.print_exc()
            text = "❌ Error calculando posición en cola"
            if UI is not None:
                cover_queue_label.configure(text=text, text_color="#ff4444")
            else:
                cover_queue_label.configure(text=text, fg="#ff4444")
        
        # Auto-refresh cada 30 segundos si estamos en modo covers
        if current_mode.get() == 'covers':
            top.after(30000, update_cover_queue_position)

    def load_data():
        """Wrapper que llama a load_daily(), load_specials() o load_covers() según el modo activo"""
        mode = current_mode.get()
        if mode == 'daily':
            load_daily()
        elif mode == 'specials':
            load_specials()
        elif mode == 'covers':
            load_covers()
            # Actualizar posición en cola cuando se cargan covers
            update_cover_queue_position()
    
    def toggle_mode():
        """Alterna entre modo DAILY ↔ SPECIALS (Covers tiene su propio botón)"""
        nonlocal columns, custom_widths
        
        mode = current_mode.get()
        
        if mode == 'daily':
            # Cambiar a SPECIALS
            current_mode.set('specials')
            columns = columns_specials
            custom_widths = custom_widths_specials
            
            # Actualizar headers del sheet
            sheet.headers(columns_specials)
            
            # ⭐ DESHABILITAR EDICIÓN DIRECTA en sheet (modo solo lectura)
            try:
                sheet.disable_bindings("edit_cell")
            except Exception as e:
                print(f"[DEBUG] No se pudo deshabilitar edit_cell: {e}")
            
            # Ocultar formulario de entrada (no se usa en specials)
            entry_frame.pack_forget()
            
            # Ocultar frame de posición en cola (solo para covers)
            cover_queue_frame.pack_forget()
            
            # Mostrar botones de envío
            if enviar_btn:
                enviar_btn.pack(side="left", padx=5, pady=12)
            if accion_btn:
                accion_btn.pack(side="left", padx=5, pady=12)
            
            # Actualizar botón toggle
            if UI is not None:
                toggle_btn.configure(text="📝 Daily", fg_color="#4D6068", hover_color="#CC43CC")
            else:
                toggle_btn.configure(text="📝 Daily", bg="#CC43CC")

            # Cargar datos de specials
            load_specials()
            
        elif mode == 'specials':
            # Cambiar a DAILY
            current_mode.set('daily')
            columns = columns_daily
            custom_widths = custom_widths_daily
            
            # Actualizar headers del sheet
            sheet.headers(columns_daily)
            
            # ⭐ HABILITAR EDICIÓN DIRECTA en sheet (modo editable)
            try:
                sheet.enable_bindings("edit_cell")
            except Exception as e:
                print(f"[DEBUG] No se pudo habilitar edit_cell: {e}")
            
            # Mostrar formulario de entrada
            entry_frame.pack(fill="x", side="bottom", padx=0, pady=0)
            
            # Ocultar frame de posición en cola (solo para covers)
            cover_queue_frame.pack_forget()
            
            # Ocultar botones de envío (solo en Specials)
            if enviar_btn:
                enviar_btn.pack_forget()
            if accion_btn:
                accion_btn.pack_forget()
            
            # Actualizar botón toggle
            if UI is not None:
                toggle_btn.configure(text="⭐ Specials", fg_color="#4D6068", hover_color="#3a7bc2")
            else:
                toggle_btn.configure(text="⭐ Specials", bg="#4D6068")

            # Cargar datos de daily
            load_daily()
        
        else:  # mode == 'covers' - volver a daily
            # Cambiar a DAILY
            current_mode.set('daily')
            columns = columns_daily
            custom_widths = custom_widths_daily
            
            # Actualizar headers del sheet
            sheet.headers(columns_daily)
            
            # ⭐ HABILITAR EDICIÓN DIRECTA en sheet (modo editable)
            try:
                sheet.enable_bindings("edit_cell")
            except Exception as e:
                print(f"[DEBUG] No se pudo habilitar edit_cell: {e}")
            
            # Mostrar formulario de entrada
            entry_frame.pack(fill="x", side="bottom", padx=0, pady=0)
            
            # ⭐ Ocultar frame de posición en cola
            cover_queue_frame.pack_forget()
            
            # Ocultar botones de envío
            if enviar_btn:
                enviar_btn.pack_forget()
            if accion_btn:
                accion_btn.pack_forget()
            
            # Actualizar botón toggle
            if UI is not None:
                toggle_btn.configure(text="⭐ Specials", fg_color="#4D6068", hover_color="#3a7bc2")
            else:
                toggle_btn.configure(text="⭐ Specials", bg="#4D6068")

            # Cargar datos de daily
            load_daily()
    
    # ⭐ FUNCIONES PARA MODO SPECIALS: Envío a supervisores (estilo open_report_window)
    
    def enviar_todos():
        """Selecciona todas las filas y las envía a un supervisor"""
        if current_mode.get() != 'specials':
            messagebox.showinfo("Modo incorrecto", "Esta función solo está disponible en modo Specials.", parent=top)
            return
        
        try:
            # Seleccionar todas las filas
            try:
                sheet.select_all()
            except Exception:
                try:
                    total = sheet.get_total_rows()
                    sheet.select_rows(list(range(total)))
                except Exception:
                    pass
        except Exception:
            pass
        
        # Llamar al flujo de supervisores indicando que se procesen todas las filas
        accion_supervisores(process_all=True)
    
    def accion_supervisores(process_all=False):
        """Muestra ventana para seleccionar supervisor y enviar eventos especiales"""
        if current_mode.get() != 'specials':
            messagebox.showinfo("Modo incorrecto", "Esta función solo está disponible en modo Specials.", parent=top)
            return
        
        # Ventana modal para elegir supervisor
        if UI is not None:
            supervisor_win = UI.CTkToplevel(top)
            try:
                supervisor_win.configure(fg_color="#2c2f33")
            except Exception:
                pass
        else:
            supervisor_win = tk.Toplevel(top)
            supervisor_win.configure(bg="#2c2f33")
        
        supervisor_win.title("Selecciona un Supervisor")
        supervisor_win.geometry("360x220")
        supervisor_win.resizable(False, False)
        
        if UI is not None:
            UI.CTkLabel(supervisor_win, text="Supervisores disponibles:", 
                       text_color="#00bfae", font=("Segoe UI", 16, "bold")).pack(pady=(18, 8))
            container = UI.CTkFrame(supervisor_win, fg_color="#2c2f33")
            container.pack(fill="both", expand=True, padx=16, pady=(0, 12))
        else:
            tk.Label(supervisor_win, text="Supervisores disponibles:", bg="#2c2f33", fg="#00bfae", 
                    font=("Segoe UI", 13, "bold")).pack(pady=(18, 4))
            container = tk.Frame(supervisor_win, bg="#2c2f33")
            container.pack(fill="both", expand=True, padx=14, pady=(4, 16))
        
        # Consultar lista de supervisores
        supervisores = []
        try:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("""
            SELECT u.Nombre_Usuario 
            FROM user u
            WHERE u.Rol IN (%s, %s)
            AND EXISTS (
                SELECT 1 
                FROM sesion s 
                WHERE s.ID_user = u.Nombre_Usuario 
                AND s.Active IN (1, 2)
                ORDER BY s.ID DESC 
                LIMIT 1
            )
            AND (
                SELECT s2.Active
                FROM sesion s2
                WHERE s2.ID_user = u.Nombre_Usuario
                ORDER BY s2.ID DESC
                LIMIT 1
            ) <> 0
        """, ("Supervisor", "Lead Supervisor"))
            supervisores = [row[0] for row in cur.fetchall()]
            cur.close()
            conn.close()
        except Exception as e:
            print(f"[ERROR] al consultar supervisores: {e}")
        
        # Control de selección
        sup_var = tk.StringVar()
        if UI is not None:
            if not supervisores:
                supervisores = ["No hay supervisores disponibles"]
            try:
                opt = UI.CTkOptionMenu(container, variable=sup_var, values=supervisores, 
                                      fg_color="#262a31", button_color="#14414e", text_color="#00bfae")
            except Exception:
                opt = UI.CTkOptionMenu(container, variable=sup_var, values=supervisores)
            if supervisores:
                try:
                    sup_var.set(supervisores[0])
                except Exception:
                    pass
            opt.pack(fill="x", padx=6, pady=6)
        else:
            yscroll_sup = tk.Scrollbar(container, orient="vertical")
            yscroll_sup.pack(side="right", fill="y")
            sup_listbox = tk.Listbox(container, height=10, selectmode="browse", bg="#262a31", fg="#00bfae", 
                                     font=("Segoe UI", 12), yscrollcommand=yscroll_sup.set, 
                                     activestyle="dotbox", selectbackground="#14414e")
            sup_listbox.pack(side="left", fill="both", expand=True)
            yscroll_sup.config(command=sup_listbox.yview)
            if not supervisores:
                sup_listbox.insert("end", "No hay supervisores disponibles")
            else:
                for sup in supervisores:
                    sup_listbox.insert("end", sup)
        
        def aceptar_supervisor():
            """Procesa el envío de eventos al supervisor seleccionado"""
            # Obtener selección de filas
            selected_rows = []
            if process_all:
                # Procesar todas las filas visibles
                try:
                    total = sheet.get_total_rows()
                except Exception:
                    try:
                        total = len(sheet.get_sheet_data())
                    except Exception:
                        total = 0
                selected_rows = list(range(total))
            else:
                try:
                    sel = sheet.get_selected_rows()
                except Exception:
                    sel = []
                
                # Si no hay filas seleccionadas, intentar con selección actual
                if not sel:
                    try:
                        cur_sel = sheet.get_currently_selected()
                        if cur_sel and cur_sel.row is not None:
                            sel = {cur_sel.row}
                    except Exception:
                        pass
                
                if not sel:
                    messagebox.showwarning("Sin selección", "No hay filas seleccionadas.", parent=supervisor_win)
                    return
                
                try:
                    selected_rows = list(sel)
                except Exception:
                    selected_rows = [next(iter(sel))]
            
            # Supervisor seleccionado
            if UI is not None:
                supervisor = (sup_var.get() or "").strip()
                if not supervisor or supervisor == "No hay supervisores disponibles":
                    messagebox.showwarning("Sin supervisor", "Debes seleccionar un supervisor.", parent=supervisor_win)
                    return
            else:
                selected_indices = sup_listbox.curselection()
                if not selected_indices or (sup_listbox.get(selected_indices[0]) == "No hay supervisores disponibles"):
                    messagebox.showwarning("Sin supervisor", "Debes seleccionar un supervisor.", parent=supervisor_win)
                    return
                supervisor = sup_listbox.get(selected_indices[0])
            
            try:
                conn = get_connection()
                cur = conn.cursor()
                inserted = 0
                updated = 0
                
                for r in selected_rows:
                    try:
                        valores = sheet.get_row_data(r)
                    except Exception:
                        valores = []
                    
                    # ⭐ Extraer valores según NUEVAS columnas (sin ID ni Usuario)
                    # Columnas: ["Fecha_hora", "ID_Sitio", "Nombre_Actividad", "Cantidad", "Camera", "Descripcion", "Time_Zone", "Marca"]
                    fecha_hora = valores[0] if len(valores) > 0 else None
                    id_sitio_str = valores[1] if len(valores) > 1 else None
                    nombre_actividad = valores[2] if len(valores) > 2 else None
                    cantidad = valores[3] if len(valores) > 3 else None
                    camera = valores[4] if len(valores) > 4 else None
                    descripcion = valores[5] if len(valores) > 5 else None
                    time_zone = valores[6] if len(valores) > 6 else None
                    # valores[7] es "Marca" - no lo necesitamos
                    
                    # Usuario actual (el que está enviando)
                    usuario_evt = username
                    
                    # Resolver ID_Sitio (puede venir como "Nombre (ID)" o solo "ID")
                    id_sitio = None
                    try:
                        if id_sitio_str:
                            # Intentar extraer ID de formato "Nombre (ID)"
                            if '(' in str(id_sitio_str) and ')' in str(id_sitio_str):
                                id_sitio = int(str(id_sitio_str).split('(')[1].split(')')[0])
                            else:
                                id_sitio = int(id_sitio_str)
                    except Exception:
                        id_sitio = None
                    
                    # Normalizar valores antes de guardar
                    cantidad_normalizada = int(cantidad) if cantidad is not None and str(cantidad).strip() else 0
                    camera_normalizada = str(camera).strip() if camera else ""
                    descripcion_normalizada = str(descripcion).strip() if descripcion else ""

                    
                    # Upsert en tabla specials
                    try:
                        # Verificar si ya existe en specials (buscar SOLO por campos clave)
                        cur.execute(
                            """
                            SELECT ID_special
                            FROM specials
                            WHERE FechaHora = %s
                              AND Usuario = %s
                              AND Nombre_Actividad = %s
                              AND IFNULL(ID_Sitio, 0) = IFNULL(%s, 0)
                            LIMIT 1
                            """,
                            (fecha_hora, usuario_evt, nombre_actividad, id_sitio),
                        )
                        row_exist = cur.fetchone()
                        
                        if row_exist:
                            # Actualizar registro existente (SIEMPRE actualizar con los valores actuales de Eventos)
                            special_id = row_exist[0]
                            try:
                                cur.execute(
                                    """
                                    UPDATE specials
                                    SET FechaHora = %s,
                                        ID_Sitio = %s,
                                        Nombre_Actividad = %s,
                                        Cantidad = %s,
                                        Camera = %s,
                                        Descripcion = %s,
                                        Usuario = %s,
                                        Time_Zone = %s,
                                        marked_status = NULL,
                                        marked_at = NULL,
                                        marked_by = NULL,
                                        Supervisor = %s
                                    WHERE ID_Special = %s
                                    """,
                                    (fecha_hora, id_sitio, nombre_actividad, cantidad_normalizada, 
                                     camera_normalizada, descripcion_normalizada, 
                                     usuario_evt, time_zone, supervisor, special_id),
                                )
                                updated += 1
                                print(f"  -> ACTUALIZADO en specials (ID={special_id})")
                            except Exception as ue:
                                print(f"[ERROR] al actualizar fila en specials (ID={special_id}): {ue}")
                        else:
                            # Insertar nuevo registro (con campos marked_* inicializados a NULL)
                            try:
                                cur.execute(
                                    """
                                    INSERT INTO specials
                                        (FechaHora, ID_Sitio, Nombre_Actividad, Cantidad, Camera, Descripcion, 
                                         Usuario, Time_Zone, Supervisor, marked_status, marked_by, marked_at)
                                    VALUES
                                        (%s, %s, %s, %s, %s, %s, %s, %s, %s, NULL, NULL, NULL)
                                    """,
                                    (fecha_hora, id_sitio, nombre_actividad, cantidad_normalizada, 
                                     camera_normalizada, descripcion_normalizada, 
                                     usuario_evt, time_zone, supervisor),
                                )
                                inserted += 1
                                print(f"  -> INSERTADO en specials (nuevo registro)")
                            except Exception as ie:
                                print(f"[ERROR] al insertar fila en specials (Fecha_hora={fecha_hora}, Usuario={usuario_evt}): {ie}")
                    except Exception as e_row:
                        print(f"[ERROR] al procesar fila para specials (Usuario={usuario_evt}, Fecha_hora={fecha_hora}): {e_row}")
                
                conn.commit()
                cur.close()
                conn.close()
                
                
                
                supervisor_win.destroy()
                
                # Recargar datos para actualizar columna "Marca"
                load_specials()
                
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo enviar eventos:\n{e}", parent=supervisor_win)
                print(f"[ERROR] accion_supervisores: {e}")
                import traceback
                traceback.print_exc()
        
        # Botones Aceptar/Cancelar
        if UI is not None:
            btn_frame = UI.CTkFrame(supervisor_win, fg_color="transparent")
            btn_frame.pack(pady=(8, 16))
            
            UI.CTkButton(btn_frame, text="✅ Aceptar", command=aceptar_supervisor,
                        fg_color="#00c853", hover_color="#00a043",
                        font=("Segoe UI", 12, "bold"),
                        width=120, height=36).pack(side="left", padx=10)
            
            UI.CTkButton(btn_frame, text="❌ Cancelar", command=supervisor_win.destroy,
                        fg_color="#666666", hover_color="#555555",
                        font=("Segoe UI", 12),
                        width=120, height=36).pack(side="left", padx=10)
        else:
            btn_frame = tk.Frame(supervisor_win, bg="#2c2f33")
            btn_frame.pack(pady=(8, 16))
            
            tk.Button(btn_frame, text="✅ Aceptar", command=aceptar_supervisor,
                     bg="#00c853", fg="white", relief="flat",
                     width=12, font=("Segoe UI", 11, "bold")).pack(side="left", padx=10)
            tk.Button(btn_frame, text="❌ Cancelar", command=supervisor_win.destroy,
                     bg="#666666", fg="white", relief="flat",
                     width=12, font=("Segoe UI", 11)).pack(side="left", padx=10)
        
        supervisor_win.transient(top)
        supervisor_win.grab_set()
        supervisor_win.focus_set()

    # ⭐ NOTA: add_new_row() eliminada - ahora se usa el formulario inferior


    def delete_selected():
        """Elimina la fila seleccionada (SOLO EN MODO DAILY)"""
        # ⭐ BLOQUEAR ELIMINACIÓN en modos Specials y Covers
        mode = current_mode.get()
        if mode == 'specials':
            messagebox.showinfo("Información", 
                               "No se puede eliminar desde el modo Specials.\n"
                               "Usa el modo Daily para eliminar eventos.",
                               parent=top)
            return
        elif mode == 'covers':
            messagebox.showinfo("Información", 
                               "No se puede eliminar desde el modo Covers.\n"
                               "Esta función estará disponible próximamente.",
                               parent=top)
            return
        
        selected = sheet.get_currently_selected()
        if not selected:
            messagebox.showwarning("Advertencia", "No hay fila seleccionada.", parent=top)
            return

        # Obtener índice de fila seleccionada
        if selected.row is None:
            messagebox.showwarning("Advertencia", "Selecciona una fila completa.", parent=top)
            return

        row_idx = selected.row

        try:
            # Verificar si la fila existe en el cache
            if row_idx >= len(row_data_cache):
                messagebox.showwarning("Advertencia", "Índice de fila inválido.", parent=top)
                return

            cached_data = row_data_cache[row_idx]
            event_id = cached_data.get('id')

            # Si es una fila nueva (sin ID), solo quitarla del sheet
            if event_id is None:
                # Confirmar eliminación
                if not messagebox.askyesno("Confirmar", 
                                          "¿Eliminar esta fila nueva sin guardar?",
                                          parent=top):
                    return

                # Quitar del sheet
                current_data = sheet.get_sheet_data()
                current_data.pop(row_idx)
                sheet.set_sheet_data(current_data)
                apply_sheet_widths()

                # Quitar del cache
                row_data_cache.pop(row_idx)
                row_ids.pop(row_idx)

                # Actualizar pending_changes
                if row_idx in pending_changes:
                    pending_changes.remove(row_idx)
                # Ajustar índices mayores
                pending_changes[:] = [i-1 if i > row_idx else i for i in pending_changes]

                messagebox.showinfo("Eliminado", "Fila nueva eliminada.", parent=top)
                return

            # Si es una fila guardada, usar safe_delete
            if not messagebox.askyesno("Confirmar Eliminación", 
                                      f"¿Eliminar evento '{cached_data.get('actividad', '')}'?\n\n"
                                      "Será movido a la papelera.",
                                      parent=top):
                return

            # Pedir razón de eliminación
            reason = simpledialog.askstring("Razón de Eliminación", 
                                           "Ingresa la razón de eliminación:",
                                           parent=top)
            if not reason:
                reason = "Eliminación manual desde ventana híbrida"

            # Usar safe_delete para mover a papelera
            safe_delete("Eventos", "ID_Eventos", event_id, username, reason)

            # Quitar del sheet
            current_data = sheet.get_sheet_data()
            current_data.pop(row_idx)
            sheet.set_sheet_data(current_data)
            apply_sheet_widths()

            # Quitar del cache
            row_data_cache.pop(row_idx)
            row_ids.pop(row_idx)

            # Actualizar pending_changes
            if row_idx in pending_changes:
                pending_changes.remove(row_idx)
            pending_changes[:] = [i-1 if i > row_idx else i for i in pending_changes]

            messagebox.showinfo("Eliminado", "Evento eliminado y movido a la papelera.", parent=top)

        except Exception as e:
            messagebox.showerror("Error", f"Error al eliminar:\n{e}", parent=top)
            traceback.print_exc()
    
    # ⭐ Asignar comando delete_selected al botón del header
    try:
        delete_btn_header.configure(command=delete_selected)
    except:
        pass  # Si no existe el botón (fallback Tkinter), no hay problema

    def on_cell_edit(event):
        """Callback cuando se edita una celda - GUARDA AUTOMÁTICAMENTE"""
        try:
            # Obtener celda actualmente seleccionada (la que acaba de ser editada)
            selected = sheet.get_currently_selected()
            
            if selected and selected.row is not None:
                row_idx = selected.row
                col_idx = selected.column if selected.column is not None else -1
                # Verificar que sea una fila válida
                if row_idx < len(row_data_cache):
                    # Agregar a pending_changes si no está (para procesamiento)
                    if row_idx not in pending_changes:
                        pending_changes.append(row_idx)
                    
                    print(f"[DEBUG] Cell edited: row={row_idx}, col={col_idx}")
                    
                    # ⭐ GUARDAR AUTOMÁTICAMENTE después de un breve delay
                    top.after(500, auto_save_pending)
        except Exception as e:
            print(f"[DEBUG] on_cell_edit error: {e}")
            import traceback
            traceback.print_exc()
    
    def auto_save_pending():
        """Guarda automáticamente los cambios pendientes sin mostrar mensajes"""
        if not pending_changes:
            return
        
        try:
            conn = get_connection()
            if not conn:
                return
            
            cur = conn.cursor()
            
            # Obtener ID_Usuario
            cur.execute("SELECT ID_Usuario FROM user WHERE Nombre_Usuario=%s", (username,))
            user_row = cur.fetchone()
            if not user_row:
                cur.close()
                conn.close()
                return
            user_id = int(user_row[0])

            for idx in list(pending_changes):  # Copiar lista para evitar modificación durante iteración
                try:
                    # Obtener datos de la fila desde el sheet
                    row_data = sheet.get_row_data(idx)
                    if not row_data or len(row_data) < 6:  # Esperamos 6 columnas
                        continue

                    fecha_str, sitio_str, actividad, cantidad_str, camera, descripcion = row_data

                    # Validación básica - Actividad es obligatoria
                    if not actividad or not actividad.strip():
                        continue

                    # Fecha/Hora
                    if not fecha_str or not fecha_str.strip():
                        fecha_hora = datetime.now()
                    else:
                        try:
                            fecha_hora = datetime.strptime(fecha_str, "%Y-%m-%d %H:%M:%S")
                        except Exception:
                            continue

                    # Sitio - extraer ID_Sitio del formato "Nombre (ID)" o "Nombre ID"
                    sitio_id = None
                    if sitio_str and sitio_str.strip():
                        try:
                            # ⭐ Método 1: Buscar ID entre paréntesis "Nombre (123)"
                            import re
                            match = re.search(r'\((\d+)\)', sitio_str)
                            if match:
                                sitio_id = int(match.group(1))
                            else:
                                # ⭐ Método 2: Formato antiguo "Nombre 123" (fallback)
                                parts = sitio_str.strip().split()
                                sitio_id = int(parts[-1])
                            
                            # Verificar que existe
                            cur.execute("SELECT ID_Sitio FROM Sitios WHERE ID_Sitio=%s", (sitio_id,))
                            if not cur.fetchone():
                                continue
                        except Exception as e:
                            print(f"[DEBUG] Error extrayendo ID_Sitio de '{sitio_str}': {e}")
                            continue

                    # Cantidad
                    try:
                        cantidad = float(cantidad_str) if cantidad_str and cantidad_str.strip() else 0
                    except Exception:
                        continue

                    # Determinar si es INSERT o UPDATE
                    cached_data = row_data_cache[idx]
                    event_id = cached_data.get('id')

                    if cached_data['status'] == 'new' or event_id is None:
                        # INSERT - Nuevo evento
                        cur.execute("""
                            INSERT INTO Eventos (FechaHora, ID_Sitio, Nombre_Actividad, Cantidad, Camera, Descripcion, ID_Usuario)
                            VALUES (%s, %s, %s, %s, %s, %s, %s)
                        """, (fecha_hora, sitio_id, actividad.strip(), cantidad, camera.strip() if camera else "", 
                              descripcion.strip() if descripcion else "", user_id))
                        
                        new_id = cur.lastrowid
                        row_data_cache[idx]['id'] = new_id
                        row_ids[idx] = new_id
                        
                    else:
                        # UPDATE - Evento existente
                        cur.execute("""
                            UPDATE Eventos 
                            SET FechaHora=%s, ID_Sitio=%s, Nombre_Actividad=%s, Cantidad=%s, Camera=%s, Descripcion=%s
                            WHERE ID_Eventos=%s
                        """, (fecha_hora, sitio_id, actividad.strip(), cantidad, camera.strip() if camera else "",
                              descripcion.strip() if descripcion else "", event_id))

                    # Actualizar cache
                    row_data_cache[idx].update({
                        'fecha_hora': fecha_hora,
                        'sitio_id': sitio_id,
                        'sitio_nombre': sitio_str,
                        'actividad': actividad.strip(),
                        'cantidad': cantidad,
                        'camera': camera.strip() if camera else "",
                        'descripcion': descripcion.strip() if descripcion else "",
                        'status': 'saved'
                    })
                    
                    # Remover de pending_changes
                    if idx in pending_changes:
                        pending_changes.remove(idx)
                    
                    print(f"[DEBUG] Auto-saved row {idx}")

                except Exception as e:
                    print(f"[DEBUG] Error auto-saving row {idx}: {e}")
                    continue

            conn.commit()
            cur.close()
            conn.close()
            
        except Exception as e:
            print(f"[DEBUG] auto_save_pending error: {e}")
            import traceback
            traceback.print_exc()

    # Vincular evento de edición de celda
    sheet.bind("<<SheetModified>>", on_cell_edit, add=True)
    
    # ⭐ BINDING ADICIONAL: Capturar ediciones cuando se pierde el foco de la celda
    def on_cell_deselect(event):
        """Agrega la fila a pending_changes cuando se pierde el foco"""
        try:
            selected = sheet.get_currently_selected()
            if selected and selected.row is not None and selected.row < len(row_data_cache):
                row_idx = selected.row
                
                # Solo si no está ya marcada como pendiente
                if row_idx not in pending_changes:
                    # Verificar si realmente cambió algo comparando con cache
                    current_row = sheet.get_row_data(row_idx)
                    if current_row and len(current_row) >= 6:
                        # Agregar a pending changes
                        pending_changes.append(row_idx)
                        print(f"[DEBUG] Cell deselect - fila {row_idx} agregada a pendientes")
        except Exception as e:
            print(f"[DEBUG] on_cell_deselect error: {e}")
    
    sheet.bind("<<SheetSelect>>", on_cell_deselect, add=True)

    # Handler para bloquear edición por teclado en columnas protegidas
    def check_protected_edit(event):
        """Bloquea edición por teclado en columnas Sitio y Actividad"""
        try:
            # Bloquear CUALQUIER tecla en columnas protegidas
            if event.char and event.char.isprintable():
                selected = sheet.get_currently_selected()
                if selected and selected.column in [1, 2]:
                    # Bloquear la tecla completamente
                    return "break"
        except Exception as e:
            print(f"[DEBUG] check_protected_edit error: {e}")
    
    # Vincular evento para detectar intentos de edición POR TECLADO
    sheet.bind("<Key>", check_protected_edit, add=True)

    # ⭐ FUNCIÓN: Abrir ventana emergente para seleccionar Sitio
    def open_site_selector(row_idx):
        """Abre ventana emergente para seleccionar sitio"""
        try:
            if row_idx >= len(row_data_cache):
                return
            
            # Crear ventana de selección
            if UI is not None:
                sel_win = UI.CTkToplevel(top)
                sel_win.title("Seleccionar Sitio")
                sel_win.geometry("500x400")
                sel_win.configure(fg_color="#2c2f33")
            else:
                sel_win = tk.Toplevel(top)
                sel_win.title("Seleccionar Sitio")
                sel_win.geometry("500x400")
                sel_win.configure(bg="#2c2f33")
            
            sel_win.transient(top)
            sel_win.grab_set()
            
            # Header
            if UI is not None:
                UI.CTkLabel(sel_win, text="🏢 Seleccionar Sitio",
                           font=("Segoe UI", 16, "bold"),
                           text_color="#4a90e2").pack(pady=(15, 10))
            else:
                tk.Label(sel_win, text="🏢 Seleccionar Sitio",
                        bg="#2c2f33", fg="#4a90e2",
                        font=("Segoe UI", 16, "bold")).pack(pady=(15, 10))
            
            # Frame para búsqueda
            if UI is not None:
                search_frame = UI.CTkFrame(sel_win, fg_color="#23272a")
            else:
                search_frame = tk.Frame(sel_win, bg="#23272a")
            search_frame.pack(fill="x", padx=15, pady=(0, 10))
            
            # Campo de búsqueda
            search_var = tk.StringVar()
            if UI is not None:
                UI.CTkLabel(search_frame, text="Buscar:",
                           text_color="#c9d1d9",
                           font=("Segoe UI", 11)).pack(side="left", padx=(10, 5))
                search_entry = UI.CTkEntry(search_frame, textvariable=search_var,
                                          width=350, height=32)
            else:
                tk.Label(search_frame, text="Buscar:",
                        bg="#23272a", fg="#c9d1d9",
                        font=("Segoe UI", 11)).pack(side="left", padx=(10, 5))
                search_entry = tk.Entry(search_frame, textvariable=search_var,
                                       width=40, font=("Segoe UI", 11))
            search_entry.pack(side="left", padx=5, pady=8)
            search_entry.focus_set()
            
            # Frame para listbox
            list_frame = tk.Frame(sel_win, bg="#2c2f33")
            list_frame.pack(fill="both", expand=True, padx=15, pady=(0, 10))
            
            # Scrollbar y Listbox
            scrollbar = tk.Scrollbar(list_frame, orient="vertical")
            scrollbar.pack(side="right", fill="y")
            
            listbox = tk.Listbox(list_frame, yscrollcommand=scrollbar.set,
                                bg="#262a31", fg="#ffffff",
                                font=("Segoe UI", 11),
                                selectbackground="#4a90e2",
                                selectforeground="#ffffff",
                                activestyle="none")
            listbox.pack(side="left", fill="both", expand=True)
            scrollbar.config(command=listbox.yview)
            
            # Obtener lista de sitios
            sites_list = get_sites()
            
            def update_list(filter_text=""):
                """Actualiza la lista según el filtro"""
                listbox.delete(0, tk.END)
                filter_text = filter_text.lower()
                for site in sites_list:
                    if filter_text in site.lower():
                        listbox.insert(tk.END, site)
            
            def on_search_change(*args):
                """Callback cuando cambia el texto de búsqueda"""
                update_list(search_var.get())
            
            search_var.trace_add("write", on_search_change)
            update_list()  # Llenar inicialmente
            
            def on_select():
                """Callback cuando se selecciona un sitio"""
                selection = listbox.curselection()
                if not selection:
                    return
                
                selected_site = listbox.get(selection[0])
                
                # Actualizar celda en el sheet
                sheet.set_cell_data(row_idx, 1, selected_site)
                
                # Marcar como cambio pendiente
                if row_idx not in pending_changes:
                    pending_changes.append(row_idx)
                
                # Guardar automáticamente
                auto_save_pending()
                
                sel_win.destroy()
            
            def on_double_click(event):
                """Double-click para seleccionar"""
                on_select()
            
            def on_enter(event):
                """Enter para seleccionar"""
                on_select()
            
            listbox.bind("<Double-Button-1>", on_double_click)
            listbox.bind("<Return>", on_enter)
            search_entry.bind("<Return>", lambda e: on_select())
            
            # Botones
            if UI is not None:
                btn_frame = UI.CTkFrame(sel_win, fg_color="transparent")
            else:
                btn_frame = tk.Frame(sel_win, bg="#2c2f33")
            btn_frame.pack(fill="x", padx=15, pady=(0, 15))
            
            if UI is not None:
                UI.CTkButton(btn_frame, text="✅ Seleccionar",
                            command=on_select,
                            fg_color="#00c853", hover_color="#00a043",
                            width=120, height=35).pack(side="left", padx=(0, 10))
                UI.CTkButton(btn_frame, text="❌ Cancelar",
                            command=sel_win.destroy,
                            fg_color="#666666", hover_color="#555555",
                            width=120, height=35).pack(side="left")
            else:
                tk.Button(btn_frame, text="✅ Seleccionar",
                         command=on_select,
                         bg="#00c853", fg="white",
                         font=("Segoe UI", 11, "bold"),
                         relief="flat", width=12).pack(side="left", padx=(0, 10))
                tk.Button(btn_frame, text="❌ Cancelar",
                         command=sel_win.destroy,
                         bg="#666666", fg="white",
                         font=("Segoe UI", 11),
                         relief="flat", width=12).pack(side="left")
            
        except Exception as e:
            print(f"[ERROR] open_site_selector: {e}")
            import traceback
            traceback.print_exc()
    
    # ⭐ FUNCIÓN: Abrir ventana emergente para seleccionar Actividad
    def open_activity_selector(row_idx):
        """Abre ventana emergente para seleccionar actividad"""
        try:
            if row_idx >= len(row_data_cache):
                return
            
            # Crear ventana de selección
            if UI is not None:
                sel_win = UI.CTkToplevel(top)
                sel_win.title("Seleccionar Actividad")
                sel_win.geometry("500x400")
                sel_win.configure(fg_color="#2c2f33")
            else:
                sel_win = tk.Toplevel(top)
                sel_win.title("Seleccionar Actividad")
                sel_win.geometry("500x400")
                sel_win.configure(bg="#2c2f33")
            
            sel_win.transient(top)
            sel_win.grab_set()
            
            # Header
            if UI is not None:
                UI.CTkLabel(sel_win, text="📋 Seleccionar Actividad",
                           font=("Segoe UI", 16, "bold"),
                           text_color="#4a90e2").pack(pady=(15, 10))
            else:
                tk.Label(sel_win, text="📋 Seleccionar Actividad",
                        bg="#2c2f33", fg="#4a90e2",
                        font=("Segoe UI", 16, "bold")).pack(pady=(15, 10))
            
            # Frame para búsqueda
            if UI is not None:
                search_frame = UI.CTkFrame(sel_win, fg_color="#23272a")
            else:
                search_frame = tk.Frame(sel_win, bg="#23272a")
            search_frame.pack(fill="x", padx=15, pady=(0, 10))
            
            # Campo de búsqueda
            search_var = tk.StringVar()
            if UI is not None:
                UI.CTkLabel(search_frame, text="Buscar:",
                           text_color="#c9d1d9",
                           font=("Segoe UI", 11)).pack(side="left", padx=(10, 5))
                search_entry = UI.CTkEntry(search_frame, textvariable=search_var,
                                          width=350, height=32)
            else:
                tk.Label(search_frame, text="Buscar:",
                        bg="#23272a", fg="#c9d1d9",
                        font=("Segoe UI", 11)).pack(side="left", padx=(10, 5))
                search_entry = tk.Entry(search_frame, textvariable=search_var,
                                       width=40, font=("Segoe UI", 11))
            search_entry.pack(side="left", padx=5, pady=8)
            search_entry.focus_set()
            
            # Frame para listbox
            list_frame = tk.Frame(sel_win, bg="#2c2f33")
            list_frame.pack(fill="both", expand=True, padx=15, pady=(0, 10))
            
            # Scrollbar y Listbox
            scrollbar = tk.Scrollbar(list_frame, orient="vertical")
            scrollbar.pack(side="right", fill="y")
            
            listbox = tk.Listbox(list_frame, yscrollcommand=scrollbar.set,
                                bg="#262a31", fg="#ffffff",
                                font=("Segoe UI", 11),
                                selectbackground="#4a90e2",
                                selectforeground="#ffffff",
                                activestyle="none")
            listbox.pack(side="left", fill="both", expand=True)
            scrollbar.config(command=listbox.yview)
            
            # Obtener lista de actividades
            activities_list = get_activities()
            
            def update_list(filter_text=""):
                """Actualiza la lista según el filtro"""
                listbox.delete(0, tk.END)
                filter_text = filter_text.lower()
                for activity in activities_list:
                    if filter_text in activity.lower():
                        listbox.insert(tk.END, activity)
            
            def on_search_change(*args):
                """Callback cuando cambia el texto de búsqueda"""
                update_list(search_var.get())
            
            search_var.trace_add("write", on_search_change)
            update_list()  # Llenar inicialmente
            
            def on_select():
                """Callback cuando se selecciona una actividad"""
                selection = listbox.curselection()
                if not selection:
                    return
                
                selected_activity = listbox.get(selection[0])
                
                # Actualizar celda en el sheet
                sheet.set_cell_data(row_idx, 2, selected_activity)
                
                # Marcar como cambio pendiente
                if row_idx not in pending_changes:
                    pending_changes.append(row_idx)
                
                # Guardar automáticamente
                auto_save_pending()
                
                sel_win.destroy()
            
            def on_double_click(event):
                """Double-click para seleccionar"""
                on_select()
            
            def on_enter(event):
                """Enter para seleccionar"""
                on_select()
            
            listbox.bind("<Double-Button-1>", on_double_click)
            listbox.bind("<Return>", on_enter)
            search_entry.bind("<Return>", lambda e: on_select())
            
            # Botones
            if UI is not None:
                btn_frame = UI.CTkFrame(sel_win, fg_color="transparent")
            else:
                btn_frame = tk.Frame(sel_win, bg="#2c2f33")
            btn_frame.pack(fill="x", padx=15, pady=(0, 15))
            
            if UI is not None:
                UI.CTkButton(btn_frame, text="✅ Seleccionar",
                            command=on_select,
                            fg_color="#00c853", hover_color="#00a043",
                            width=120, height=35).pack(side="left", padx=(0, 10))
                UI.CTkButton(btn_frame, text="❌ Cancelar",
                            command=sel_win.destroy,
                            fg_color="#666666", hover_color="#555555",
                            width=120, height=35).pack(side="left")
            else:
                tk.Button(btn_frame, text="✅ Seleccionar",
                         command=on_select,
                         bg="#00c853", fg="white",
                         font=("Segoe UI", 11, "bold"),
                         relief="flat", width=12).pack(side="left", padx=(0, 10))
                tk.Button(btn_frame, text="❌ Cancelar",
                         command=sel_win.destroy,
                         bg="#666666", fg="white",
                         font=("Segoe UI", 11),
                         relief="flat", width=12).pack(side="left")
            
        except Exception as e:
            print(f"[ERROR] open_activity_selector: {e}")
            import traceback
            traceback.print_exc()
    
    # ⭐ BINDING: Doble click para DateTimePicker en   y ventanas emergentes para Sitio/Actividad
    def on_cell_double_click(event):
        """Detecta DOBLE click y abre ventanas emergentes de selección"""
        try:
            mode = current_mode.get()
            if mode in ('specials', 'covers'):
                return
            
            selected = sheet.get_currently_selected()
            
            if selected and selected.row is not None and selected.column is not None:
                col = selected.column
                row = selected.row
                
                # Columna 0:   → DateTimePicker
                if row < len(row_data_cache) and col == 0:
                    print(f"[DEBUG] Doble click en  ")
                    top.after(100, lambda: show_datetime_picker_for_edit(row))
                # Columna 1: Sitio → Ventana emergente de selección
                elif row < len(row_data_cache) and col == 1:
                    print(f"[DEBUG] Doble click en Sitio - abriendo ventana de selección")
                    top.after(50, lambda: open_site_selector(row))
                    return "break"
                # Columna 2: Actividad → Ventana emergente de selección
                elif row < len(row_data_cache) and col == 2:
                    print(f"[DEBUG] Doble click en Actividad - abriendo ventana de selección")
                    top.after(50, lambda: open_activity_selector(row))
                    return "break"
                    
        except Exception as e:
            print(f"[DEBUG] on_cell_double_click error: {e}")
    
    # Vincular eventos
    sheet.bind("<Double-Button-1>", on_cell_double_click, add=True)


    def show_datetime_picker():
        """Muestra selector moderno de fecha/hora usando CustomTkinter"""
        selected = sheet.get_currently_selected()
        if not selected or selected.row is None:
            messagebox.showinfo("Info", "Selecciona una fila primero.", parent=top)
            return

        row_idx = selected.row
        
        # Verificar que sea una fila válida
        if row_idx >= len(row_data_cache):
            return

        # Obtener valor actual
        current_value = sheet.get_cell_data(row_idx, 0)
        if current_value and current_value.strip():
            try:
                current_dt = datetime.strptime(current_value, "%Y-%m-%d %H:%M:%S")
            except:
                current_dt = datetime.now()
        else:
            current_dt = datetime.now()

        # Crear ventana con CustomTkinter si está disponible
        if UI is not None:
            picker_win = UI.CTkToplevel(top)
            picker_win.title("Seleccionar Fecha y Hora")
            picker_win.geometry("500x450")
            picker_win.resizable(False, False)
            
            # Header con icono
            header = UI.CTkFrame(picker_win, fg_color="#1a1a1a", corner_radius=0, height=60)
            header.pack(fill="x", padx=0, pady=0)
            header.pack_propagate(False)
            
            UI.CTkLabel(header, text="📅 Seleccionar Fecha y Hora", 
                       font=("Segoe UI", 20, "bold"),
                       text_color="#4a90e2").pack(pady=15)
            
            # Contenido principal
            content = UI.CTkFrame(picker_win, fg_color="transparent")
            content.pack(fill="both", expand=True, padx=20, pady=20)
            
            # Sección de Fecha
            date_section = UI.CTkFrame(content, fg_color="#2b2b2b", corner_radius=10)
            date_section.pack(fill="x", pady=(0, 15))
            
            UI.CTkLabel(date_section, text="📅 Fecha:", 
                       font=("Segoe UI", 14, "bold"),
                       text_color="#e0e0e0").pack(anchor="w", padx=15, pady=(15, 10))
            
            # Frame para calendario (tkcalendar no es CTk, lo envolvemos)
            cal_wrapper = tk.Frame(date_section, bg="#2b2b2b")
            cal_wrapper.pack(padx=15, pady=(0, 15))
            
            cal = tkcalendar.DateEntry(cal_wrapper, width=30, background='#4a90e2',
                                       foreground='white', borderwidth=2,
                                       year=current_dt.year, month=current_dt.month, day=current_dt.day,
                                       date_pattern='yyyy-mm-dd',
                                       font=("Segoe UI", 11))
            cal.pack()
            
            # Sección de Hora
            time_section = UI.CTkFrame(content, fg_color="#2b2b2b", corner_radius=10)
            time_section.pack(fill="x", pady=(0, 15))
            
            UI.CTkLabel(time_section, text="🕐 Hora:", 
                       font=("Segoe UI", 14, "bold"),
                       text_color="#e0e0e0").pack(anchor="w", padx=15, pady=(15, 10))
            
            # Variables para hora
            hour_var = tk.IntVar(value=current_dt.hour)
            minute_var = tk.IntVar(value=current_dt.minute)
            second_var = tk.IntVar(value=current_dt.second)
            
            # Frame para spinboxes (usando tk.Frame dentro de CTkFrame)
            spinbox_container = tk.Frame(time_section, bg="#2b2b2b")
            spinbox_container.pack(padx=15, pady=(0, 10))
            
            # Hora
            tk.Label(spinbox_container, text="Hora:", bg="#2b2b2b", fg="#a3c9f9",
                    font=("Segoe UI", 11)).grid(row=0, column=0, padx=5, pady=5)
            hour_spin = tk.Spinbox(spinbox_container, from_=0, to=23, textvariable=hour_var,
                                  width=8, font=("Segoe UI", 12), justify="center")
            hour_spin.grid(row=0, column=1, padx=5, pady=5)
            
            # Minuto
            tk.Label(spinbox_container, text="Min:", bg="#2b2b2b", fg="#a3c9f9",
                    font=("Segoe UI", 11)).grid(row=0, column=2, padx=5, pady=5)
            minute_spin = tk.Spinbox(spinbox_container, from_=0, to=59, textvariable=minute_var,
                                    width=8, font=("Segoe UI", 12), justify="center")
            minute_spin.grid(row=0, column=3, padx=5, pady=5)
            
            # Segundo
            tk.Label(spinbox_container, text="Seg:", bg="#2b2b2b", fg="#a3c9f9",
                    font=("Segoe UI", 11)).grid(row=0, column=4, padx=5, pady=5)
            second_spin = tk.Spinbox(spinbox_container, from_=0, to=59, textvariable=second_var,
                                    width=8, font=("Segoe UI", 12), justify="center")
            second_spin.grid(row=0, column=5, padx=5, pady=5)
            
            # Botón "Ahora"
            def set_now():
                now = datetime.now()
                cal.set_date(now.date())
                hour_var.set(now.hour)
                minute_var.set(now.minute)
                second_var.set(now.second)
            
            UI.CTkButton(time_section, text="⏰ Establecer Hora Actual", command=set_now,
                        fg_color="#4a90e2", hover_color="#3a7bc2",
                        font=("Segoe UI", 11),
                        width=200, height=35).pack(pady=(5, 15))
            
            # Botones Aceptar/Cancelar
            btn_frame = UI.CTkFrame(content, fg_color="transparent")
            btn_frame.pack(pady=10)
            
            def accept():
                try:
                    selected_date = cal.get_date()
                    selected_time = datetime.strptime(
                        f"{selected_date} {hour_var.get():02d}:{minute_var.get():02d}:{second_var.get():02d}",
                        "%Y-%m-%d %H:%M:%S"
                    )
                    
                    # Actualizar celda
                    formatted = selected_time.strftime("%Y-%m-%d %H:%M:%S")
                    sheet.set_cell_data(row_idx, 0, formatted)
                    
                    # Agregar a pending_changes para auto-guardado
                    if row_idx not in pending_changes:
                        pending_changes.append(row_idx)
                    
                    # Guardar automáticamente
                    top.after(500, auto_save_pending)
                    
                    picker_win.destroy()
                except Exception as e:
                    messagebox.showerror("Error", f"Error al establecer fecha/hora:\n{e}", parent=picker_win)
            
            UI.CTkButton(btn_frame, text="✅ Aceptar", command=accept,
                        fg_color="#00c853", hover_color="#00a043",
                        font=("Segoe UI", 12, "bold"),
                        width=120, height=40).pack(side="left", padx=10)
            
            UI.CTkButton(btn_frame, text="❌ Cancelar", command=picker_win.destroy,
                        fg_color="#666666", hover_color="#555555",
                        font=("Segoe UI", 12),
                        width=120, height=40).pack(side="left", padx=10)
        
        else:
            # Fallback a Tkinter estándar (mejorado)
            picker_win = tk.Toplevel(top)
            picker_win.title("Selector de Fecha/Hora")
            picker_win.geometry("400x400")
            picker_win.resizable(False, False)
            picker_win.configure(bg="#2c2f33")
            
            # Header
            tk.Label(picker_win, text="📅 Seleccionar Fecha y Hora", bg="#2c2f33", fg="#4a90e2",
                    font=("Segoe UI", 16, "bold")).pack(pady=15)
            
            # Frame superior para calendario
            cal_frame = tk.Frame(picker_win, bg="#2c2f33")
            cal_frame.pack(pady=10, padx=10)

            tk.Label(cal_frame, text="📅 Fecha:", bg="#2c2f33", fg="#e0e0e0",
                    font=("Segoe UI", 11, "bold")).pack(anchor="w")

            cal = tkcalendar.DateEntry(cal_frame, width=25, background='#4a90e2',
                                       foreground='white', borderwidth=2,
                                       year=current_dt.year, month=current_dt.month, day=current_dt.day,
                                       date_pattern='yyyy-mm-dd')
            cal.pack(pady=5)

            # Frame para hora
            time_frame = tk.Frame(picker_win, bg="#2c2f33")
            time_frame.pack(pady=10, padx=10)

            tk.Label(time_frame, text="🕐 Hora:", bg="#2c2f33", fg="#e0e0e0",
                    font=("Segoe UI", 11, "bold")).pack(anchor="w")

            # Spinboxes para hora, minuto, segundo
            spinbox_frame = tk.Frame(time_frame, bg="#2c2f33")
            spinbox_frame.pack(pady=5)

            hour_var = tk.IntVar(value=current_dt.hour)
            minute_var = tk.IntVar(value=current_dt.minute)
            second_var = tk.IntVar(value=current_dt.second)

            tk.Label(spinbox_frame, text="H:", bg="#2c2f33", fg="#a3c9f9",
                    font=("Segoe UI", 10)).grid(row=0, column=0, padx=2)
            hour_spin = tk.Spinbox(spinbox_frame, from_=0, to=23, textvariable=hour_var,
                                  width=5, font=("Segoe UI", 10))
            hour_spin.grid(row=0, column=1, padx=2)

            tk.Label(spinbox_frame, text="M:", bg="#2c2f33", fg="#a3c9f9",
                    font=("Segoe UI", 10)).grid(row=0, column=2, padx=2)
            minute_spin = tk.Spinbox(spinbox_frame, from_=0, to=59, textvariable=minute_var,
                                    width=5, font=("Segoe UI", 10))
            minute_spin.grid(row=0, column=3, padx=2)

            tk.Label(spinbox_frame, text="S:", bg="#2c2f33", fg="#a3c9f9",
                    font=("Segoe UI", 10)).grid(row=0, column=4, padx=2)
            second_spin = tk.Spinbox(spinbox_frame, from_=0, to=59, textvariable=second_var,
                                    width=5, font=("Segoe UI", 10))
            second_spin.grid(row=0, column=5, padx=2)

            # Botón "Ahora"
            def set_now():
                now = datetime.now()
                cal.set_date(now.date())
                hour_var.set(now.hour)
                minute_var.set(now.minute)
                second_var.set(now.second)

            tk.Button(time_frame, text="⏰ Ahora", command=set_now, bg="#4a90e2", fg="white",
                     relief="flat", font=("Segoe UI", 10)).pack(pady=5)

            # Botones Aceptar/Cancelar
            btn_frame = tk.Frame(picker_win, bg="#2c2f33")
            btn_frame.pack(pady=15)

            def accept():
                try:
                    selected_date = cal.get_date()
                    selected_time = datetime.strptime(
                        f"{selected_date} {hour_var.get():02d}:{minute_var.get():02d}:{second_var.get():02d}",
                        "%Y-%m-%d %H:%M:%S"
                    )
                    
                    # Actualizar celda
                    formatted = selected_time.strftime("%Y-%m-%d %H:%M:%S")
                    sheet.set_cell_data(row_idx, 0, formatted)
                    
                    # Agregar a pending_changes para auto-guardado
                    if row_idx not in pending_changes:
                        pending_changes.append(row_idx)
                    
                    # Guardar automáticamente
                    top.after(500, auto_save_pending)
                    
                    picker_win.destroy()
                except Exception as e:
                    messagebox.showerror("Error", f"Error al establecer fecha/hora:\n{e}", parent=picker_win)

            tk.Button(btn_frame, text="✅ Aceptar", command=accept, bg="#00c853", fg="white",
                     relief="flat", width=12, font=("Segoe UI", 11, "bold")).pack(side="left", padx=10)
            tk.Button(btn_frame, text="❌ Cancelar", command=picker_win.destroy, bg="#666666", fg="white",
                     relief="flat", width=12, font=("Segoe UI", 11)).pack(side="left", padx=10)
        
        picker_win.transient(top)
        picker_win.grab_set()
        picker_win.focus_set()

    # FUNCIONES POPUP DE RESPALDO (si dropdowns integrados no funcionan)
    def show_site_picker():
        """Muestra popup moderno para seleccionar sitio usando CustomTkinter"""
        selection = sheet.get_currently_selected()
        if not selection or selection.row is None:
            messagebox.showwarning("Advertencia", "Selecciona una fila primero", parent=top)
            return
        
        row_idx = selection.row
        
        # Crear ventana con CustomTkinter si está disponible
        if UI is not None:
            picker_win = UI.CTkToplevel(top)
            picker_win.title("Seleccionar Sitio")
            picker_win.geometry("500x250")
            
            # Header con icono
            header = UI.CTkFrame(picker_win, fg_color="#1a1a1a", corner_radius=0, height=60)
            header.pack(fill="x", padx=0, pady=0)
            header.pack_propagate(False)
            
            UI.CTkLabel(header, text="🏢 Seleccionar Sitio", 
                       font=("Segoe UI", 20, "bold"),
                       text_color="#4a90e2").pack(pady=15)
            
            # Contenido principal
            content = UI.CTkFrame(picker_win, fg_color="transparent")
            content.pack(fill="both", expand=True, padx=20, pady=20)
            
            UI.CTkLabel(content, text="Buscar y seleccionar un sitio:",
                       font=("Segoe UI", 12),
                       text_color="#e0e0e0").pack(anchor="w", pady=(0, 10))
            
            # ⭐ FilteredCombobox oscuro con borde prominente
            sites = get_sites()
            combo_var = tk.StringVar()
            combo = under_super.FilteredCombobox(
                content, textvariable=combo_var, values=sites,
                font=("Segoe UI", 11), width=50,
                background='#2b2b2b', foreground='#ffffff',
                fieldbackground='#2b2b2b',
                bordercolor='#5ab4ff', arrowcolor='#ffffff',
                borderwidth=3
            )
            combo.pack(fill="x", pady=(0, 20))
            combo.focus_set()
            
            # Botones
            btn_frame = UI.CTkFrame(content, fg_color="transparent")
            btn_frame.pack(pady=10)
            
            def accept():
                selected = combo_var.get().strip()
                if selected:
                    sheet.set_cell_data(row_idx, 1, selected)
                    if row_idx not in pending_changes:
                        pending_changes.append(row_idx)
                    
                    # Guardar automáticamente
                    top.after(500, auto_save_pending)
                    
                    picker_win.destroy()
                else:
                    messagebox.showwarning("Advertencia", "Selecciona un sitio primero", parent=picker_win)
            
            UI.CTkButton(btn_frame, text="✅ Aceptar", command=accept,
                        fg_color="#00c853", hover_color="#00a043",
                        font=("Segoe UI", 12, "bold"),
                        width=120, height=40).pack(side="left", padx=10)
            
            UI.CTkButton(btn_frame, text="❌ Cancelar", command=picker_win.destroy,
                        fg_color="#666666", hover_color="#555555",
                        font=("Segoe UI", 12),
                        width=120, height=40).pack(side="left", padx=10)
        else:
            # Fallback a Tkinter estándar
            picker_win = tk.Toplevel(top)
            picker_win.title("Seleccionar Sitio")
            picker_win.geometry("450x200")
            picker_win.configure(bg="#2c2f33")
            picker_win.transient(top)
            picker_win.grab_set()
            
            tk.Label(picker_win, text="🏢 Seleccionar Sitio", bg="#2c2f33", fg="#4a90e2",
                    font=("Segoe UI", 16, "bold")).pack(pady=15)
            
            tk.Label(picker_win, text="Buscar y seleccionar sitio:", bg="#2c2f33", fg="#e0e0e0",
                    font=("Segoe UI", 11)).pack(pady=10)
            
            # ⭐ FilteredCombobox oscuro con borde prominente
            sites = get_sites()
            combo_var = tk.StringVar()
            combo = under_super.FilteredCombobox(
                picker_win, textvariable=combo_var, values=sites,
                font=("Segoe UI", 10), width=50,
                background='#2b2b2b', foreground='#ffffff',
                fieldbackground='#2b2b2b',
                bordercolor='#5ab4ff', arrowcolor='#ffffff',
                borderwidth=3
            )
            combo.pack(pady=10, fill="x", padx=20)
            combo.focus_set()
            
            def accept():
                selected = combo_var.get().strip()
                if selected:
                    sheet.set_cell_data(row_idx, 1, selected)
                    if row_idx not in pending_changes:
                        pending_changes.append(row_idx)
                    
                    # Guardar automáticamente
                    top.after(500, auto_save_pending)
                    
                    picker_win.destroy()
                else:
                    messagebox.showwarning("Advertencia", "Selecciona un sitio primero", parent=picker_win)
            
            btn_frame = tk.Frame(picker_win, bg="#2c2f33")
            btn_frame.pack(pady=15)
            
            tk.Button(btn_frame, text="✅ Aceptar", command=accept, bg="#00c853", fg="white",
                     relief="flat", width=12, font=("Segoe UI", 11, "bold")).pack(side="left", padx=10)
            tk.Button(btn_frame, text="❌ Cancelar", command=picker_win.destroy, bg="#666666", fg="white",
                     relief="flat", width=12, font=("Segoe UI", 11)).pack(side="left", padx=10)
        
        picker_win.transient(top)
        picker_win.grab_set()
        picker_win.focus_set()

    def show_activity_picker():
        """Muestra popup moderno para seleccionar actividad usando CustomTkinter"""
        selection = sheet.get_currently_selected()
        if not selection or selection.row is None:
            messagebox.showwarning("Advertencia", "Selecciona una fila primero", parent=top)
            return
        
        row_idx = selection.row
        
        # Crear ventana con CustomTkinter si está disponible
        if UI is not None:
            picker_win = UI.CTkToplevel(top)
            picker_win.title("Seleccionar Actividad")
            picker_win.geometry("500x250")
            
            # Header con icono
            header = UI.CTkFrame(picker_win, fg_color="#1a1a1a", corner_radius=0, height=60)
            header.pack(fill="x", padx=0, pady=0)
            header.pack_propagate(False)
            
            UI.CTkLabel(header, text="📋 Seleccionar Actividad", 
                       font=("Segoe UI", 20, "bold"),
                       text_color="#4a90e2").pack(pady=15)
            
            # Contenido principal
            content = UI.CTkFrame(picker_win, fg_color="transparent")
            content.pack(fill="both", expand=True, padx=20, pady=20)
            
            UI.CTkLabel(content, text="Buscar y seleccionar una actividad:",
                       font=("Segoe UI", 12),
                       text_color="#e0e0e0").pack(anchor="w", pady=(0, 10))
            
            # ⭐ FilteredCombobox oscuro con borde prominente
            activities = get_activities()
            combo_var = tk.StringVar()
            combo = under_super.FilteredCombobox(
                content, textvariable=combo_var, values=activities,
                font=("Segoe UI", 11), width=50,
                background='#2b2b2b', foreground='#ffffff',
                fieldbackground='#2b2b2b',
                bordercolor='#5ab4ff', arrowcolor='#ffffff',
                borderwidth=3
            )
            combo.pack(fill="x", pady=(0, 20))
            combo.focus_set()
            
            # Botones
            btn_frame = UI.CTkFrame(content, fg_color="transparent")
            btn_frame.pack(pady=10)
            
            def accept():
                selected = combo_var.get().strip()
                if selected:
                    sheet.set_cell_data(row_idx, 2, selected)
                    if row_idx not in pending_changes:
                        pending_changes.append(row_idx)
                    
                    # Guardar automáticamente
                    top.after(500, auto_save_pending)
                    
                    picker_win.destroy()
                else:
                    messagebox.showwarning("Advertencia", "Selecciona una actividad primero", parent=picker_win)
            
            UI.CTkButton(btn_frame, text="✅ Aceptar", command=accept,
                        fg_color="#00c853", hover_color="#00a043",
                        font=("Segoe UI", 12, "bold"),
                        width=120, height=40).pack(side="left", padx=10)
            
            UI.CTkButton(btn_frame, text="❌ Cancelar", command=picker_win.destroy,
                        fg_color="#666666", hover_color="#555555",
                        font=("Segoe UI", 12),
                        width=120, height=40).pack(side="left", padx=10)
        else:
            # Fallback a Tkinter estándar
            picker_win = tk.Toplevel(top)
            picker_win.title("Seleccionar Actividad")
            picker_win.geometry("450x200")
            picker_win.configure(bg="#2c2f33")
            picker_win.transient(top)
            picker_win.grab_set()
            
            tk.Label(picker_win, text="📋 Seleccionar Actividad", bg="#2c2f33", fg="#4a90e2",
                    font=("Segoe UI", 16, "bold")).pack(pady=15)
            
            tk.Label(picker_win, text="Buscar y seleccionar actividad:", bg="#2c2f33", fg="#e0e0e0",
                    font=("Segoe UI", 11)).pack(pady=10)
            
            # ⭐ FilteredCombobox oscuro con borde prominente
            activities = get_activities()
            combo_var = tk.StringVar()
            combo = under_super.FilteredCombobox(
                picker_win, textvariable=combo_var, values=activities,
                font=("Segoe UI", 10), width=50,
                background='#2b2b2b', foreground='#ffffff',
                fieldbackground='#2b2b2b',
                bordercolor='#5ab4ff', arrowcolor='#ffffff',
                borderwidth=3
            )
            combo.pack(pady=10, fill="x", padx=20)
            combo.focus_set()
            
            def accept():
                selected = combo_var.get().strip()
                if selected:
                    sheet.set_cell_data(row_idx, 2, selected)
                    if row_idx not in pending_changes:
                        pending_changes.append(row_idx)
                    
                    # Guardar automáticamente
                    top.after(500, auto_save_pending)
                    
                    picker_win.destroy()
                else:
                    messagebox.showwarning("Advertencia", "Selecciona una actividad primero", parent=picker_win)
            
            btn_frame = tk.Frame(picker_win, bg="#2c2f33")
            btn_frame.pack(pady=15)
            
            tk.Button(btn_frame, text="✅ Aceptar", command=accept, bg="#00c853", fg="white",
                     relief="flat", width=12, font=("Segoe UI", 11, "bold")).pack(side="left", padx=10)
            tk.Button(btn_frame, text="❌ Cancelar", command=picker_win.destroy, bg="#666666", fg="white",
                     relief="flat", width=12, font=("Segoe UI", 11)).pack(side="left", padx=10)
        
        picker_win.transient(top)
        picker_win.grab_set()
        picker_win.focus_set()

    # Menú contextual (clic derecho)
    def show_context_menu(event):
        """Muestra menú contextual con opciones"""
        context_menu = tk.Menu(top, tearoff=0, bg="#2c2f33", fg="#e0e0e0",
                              activebackground="#4a90e2", activeforeground="#ffffff",
                              font=("Segoe UI", 10))
        
        # Opciones de edición rápida - MÁS PROMINENTES
        context_menu.add_command(label="🏢 Seleccionar Sitio", command=show_site_picker)
        context_menu.add_command(label="📋 Seleccionar Actividad", command=show_activity_picker)
        context_menu.add_command(label="⌚ Seleccionar Fecha/Hora", command=show_datetime_picker)
        context_menu.add_separator()
        context_menu.add_command(label="🗑️ Eliminar Fila", command=delete_selected)

        
        
        try:
            context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            context_menu.grab_release()

    # Vincular menú contextual
    sheet.bind("<Button-3>", show_context_menu)

    # Barra de herramientas
    if UI is not None:
        toolbar = UI.CTkFrame(top, fg_color="#23272a", corner_radius=0, height=60)
    else:
        toolbar = tk.Frame(top, bg="#23272a", height=60)
    toolbar.pack(fill="x", padx=0, pady=0)
    toolbar.pack_propagate(False)

    if UI is not None:
        # ⭐ BOTÓN TOGGLE DAILY/SPECIALS (ciclo entre dos modos)
        toggle_btn = UI.CTkButton(
            toolbar, text="⭐ Specials", command=toggle_mode,
            fg_color="#4D6068", hover_color="#3a7bc2", 
            width=140, height=36,
            font=("Segoe UI", 12, "bold")
        )
        toggle_btn.pack(side="left", padx=5, pady=12)
        
        # ⭐ BOTONES DE ENVÍO (solo visibles en modo Specials)
        enviar_btn = UI.CTkButton(toolbar, text="📤 Enviar Todos", command=enviar_todos,
                    fg_color="#4D6068", hover_color="#009688", width=130, height=36)
        accion_btn = UI.CTkButton(toolbar, text="👥 Enviar individual", command=accion_supervisores,
                    fg_color="#4D6068", hover_color="#009688", width=160, height=36)

        # ⭐ BOTÓN LISTA DE COVERS (solo visible cuando Active = 2)
        def open_covers_list():
            """Abre panel integrado de lista de covers programados"""
            show_covers_programados_panel(top, UI, username)
        
        lista_covers_btn = UI.CTkButton(
            toolbar, 
            text="📋 Lista de Covers", 
            command=open_covers_list,
            fg_color="#4D6068", 
            hover_color="#ffa726", 
            width=160, 
            height=36
        )
        
        # Función para verificar y actualizar visibilidad del botón
        def check_and_update_covers_button():
            """Verifica si Active = 2 y muestra/oculta el botón según corresponda"""
            try:
                active_status = get_user_status_bd(username)
                if active_status == 2:
                    # Usuario ocupado - mostrar botón
                    if not lista_covers_btn.winfo_ismapped():
                        lista_covers_btn.pack(side="left", padx=5, pady=12)
                else:
                    # Usuario disponible u otro estado - ocultar botón
                    if lista_covers_btn.winfo_ismapped():
                        lista_covers_btn.pack_forget()
            except Exception as e:
                print(f"[ERROR] Error checking covers button visibility: {e}")
            
            # Programar siguiente verificación (cada 5 segundos)
            top.after(5000, check_and_update_covers_button)
        
        # Inicialmente oculto (se mostrará si Active = 2)
        lista_covers_btn.pack_forget()
        
        # Iniciar verificación periódica
        check_and_update_covers_button()
        
        # Inicialmente ocultos (modo daily) - se mostrarán en toggle_mode
        
    else:
        # ⭐ BOTÓN TOGGLE DAILY/SPECIALS (fallback Tkinter)
        toggle_btn = tk.Button(toolbar, text="📊 Specials", command=toggle_mode, 
                               bg="#4a90e2", fg="white", relief="flat", 
                               width=14, font=("Segoe UI", 10, "bold"))
        toggle_btn.pack(side="left", padx=5, pady=12)
        
        # ⭐ BOTONES DE ENVÍO (fallback Tkinter - solo modo Specials)
        enviar_btn = tk.Button(toolbar, text="📤 Enviar Todos", command=enviar_todos,
                            bg="#00bfae", fg="white", relief="flat", width=14)
        accion_btn = tk.Button(toolbar, text="👥 Acción Supervisores", command=accion_supervisores,
                            bg="#00bfae", fg="white", relief="flat", width=18)
        
        # ⭐ BOTÓN LISTA DE COVERS (fallback tkinter - solo visible cuando Active = 2)
        def open_covers_list():
            """Abre panel integrado de lista de covers programados"""
            show_covers_programados_panel(top, None, username)
        
        lista_covers_btn = tk.Button(
            toolbar, 
            text="📋 Lista de Covers", 
            command=open_covers_list,
            bg="#00bfae", 
            fg="white", 
            relief="flat", 
            width=18
        )
        
        # Función para verificar y actualizar visibilidad del botón (tkinter)
        def check_and_update_covers_button():
            """Verifica si Active = 2 y muestra/oculta el botón según corresponda"""
            try:
                active_status = get_user_status_bd(username)
                if active_status == 2:
                    # Usuario ocupado - mostrar botón
                    try:
                        lista_covers_btn.pack_info()
                    except:
                        lista_covers_btn.pack(side="left", padx=5, pady=12)
                else:
                    # Usuario disponible u otro estado - ocultar botón
                    try:
                        lista_covers_btn.pack_info()
                        lista_covers_btn.pack_forget()
                    except:
                        pass
            except Exception as e:
                print(f"[ERROR] Error checking covers button visibility: {e}")
            
            # Programar siguiente verificación (cada 5 segundos)
            top.after(5000, check_and_update_covers_button)
        
        # Inicialmente oculto
        lista_covers_btn.pack_forget()
        
        # Iniciar verificación periódica
        check_and_update_covers_button()

    # ⭐ CONFIGURAR CIERRE DE VENTANA: Ejecutar logout automáticamente
    def on_window_close():
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
    top.protocol("WM_DELETE_WINDOW", on_window_close)
    # Configurar protocolo de cierre (botón X)
    top.protocol("WM_DELETE_WINDOW", on_window_close)

    # ⭐ RECARGA AUTOMÁTICA: Listener para evento de reenfoque
    def on_window_refocused(event=None):
        """Recarga datos automáticamente cuando la ventana vuelve a ganar foco"""
        try:
            print(f"[DEBUG] Window refocused - Reloading data for {username}...")
            load_data()
        except Exception as e:
            print(f"[ERROR] Failed to reload data on refocus: {e}")
    
    # Vincular evento personalizado
    top.bind("<<WindowRefocused>>", on_window_refocused)

    # Registrar ventana y cargar datos iniciales
    _register_singleton('hybrid_events', top)
    load_data()

    print(f"[DEBUG] Hybrid events window opened for {username}")


def cover_mode(username, session_id, station, root=None):

    # Intentar usar CustomTkinter para modernizar la UI (fallback a Tk)
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

    # Crear ventana Cover como Toplevel (CTk si está disponible)
    if UI is not None:
        cover_form = UI.CTkToplevel(root)
        try:
            cover_form.configure(fg_color="#2c2f33")
        except Exception:
            pass
    else:
        cover_form = tk.Toplevel(root)
        cover_form.configure(bg="#2c2f33")
    cover_form.title("Registrar Evento")
    cover_form.geometry("360x240")
    cover_form.resizable(False, False)

    # Forzar que la ventana quede al frente y con foco
    try:
        cover_form.update_idletasks()
        cover_form.deiconify()
    except Exception:
        pass
    try:
        # Mantener relación con la ventana principal
        cover_form.transient(root)
    except Exception:
        pass
    try:
        cover_form.lift()
    except Exception:
        pass
    try:
        # Ponerla temporalmente como 'topmost' para que aparezca delante y luego revertir
        cover_form.attributes("-topmost", True)
        cover_form.after(200, lambda: cover_form.attributes("-topmost", False))
    except Exception:
        pass
    try:
        cover_form.focus_force()
    except Exception:
        pass
    try:
        # Evitar que quede detrás al interactuar con otras ventanas
        cover_form.grab_set()
    except Exception:
        pass

    # Encabezado
    if UI is not None:
        UI.CTkLabel(
            cover_form,
            text="Modo de Cover",
            text_color="#e0e0e0",
            font=("Segoe UI", 16, "bold"),
            anchor="w",
        ).place(x=20, y=12)
        UI.CTkLabel(
            cover_form,
            text="Motivo*:",
            text_color="#a3c9f9",
            font=("Segoe UI", 12, "bold"),
            anchor="w",
        ).place(x=20, y=58)
    else:
        tk.Label(
            cover_form,
            text="Modo de Cover",
            bg="#2c2f33",
            fg="#d0d0d0",
            font=("Segoe UI", 13, "bold"),
        ).place(x=30, y=10)
        tk.Label(
            cover_form,
            text="Motivo*:",
            bg="#2c2f33",
            fg="#d0d0d0",
            font=("Segoe UI", 11, "bold"),
        ).place(x=30, y=70)

    cover_form_var = tk.StringVar()
    if UI is not None:
        try:
            cover_form_menu = under_super.FilteredCombobox(
                cover_form,
                textvariable=cover_form_var,
                values=("Cover Baño", "Cover Daily", "Break", "Trainning", "Otro"),
                font=("Segoe UI", 10),
            )
        except Exception:
            pass
    cover_form_menu.place(x=150, y=50)

    if UI is not None:
        UI.CTkLabel(
            cover_form,
            text="Covered By:",
            text_color="#a3c9f9",
            font=("Segoe UI", 12, "bold"),
            anchor="w",
        ).place(x=20, y=102)
    else:
        tk.Label(
            cover_form,
            text="Covered By:",
            bg="#2c2f33",
            fg="#d0d0d0",
            font=("Segoe UI", 11, "bold"),
        ).place(x=30, y=100)

    covered_by_var = tk.StringVar()
    
    # Obtener usuarios con rol Operador y Supervisor
    covered_by_users = []
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            "SELECT Nombre_Usuario FROM user WHERE Rol = %s ORDER BY Nombre_Usuario",
            ("Operador",)
        )
        covered_by_users = [row[0] for row in cur.fetchall()]
        cur.close()
        conn.close()
    except Exception as e:
        print(f"[ERROR] al cargar usuarios para Covered By: {e}")
    
    if UI is not None:
        try:
            covered_by_combo = under_super.FilteredCombobox(
                    cover_form,
                    textvariable=covered_by_var,
                    values=covered_by_users,
                    font=("Segoe UI", 10)
            )
        except Exception:
            pass
    
    covered_by_combo.place(x=150, y=100)

    # Preferencia: cerrar sesión al guardar (para reducir clicks)
    logout_after_var = tk.BooleanVar(value=True)
    if UI is not None:
        try:
            UI.CTkCheckBox(
                cover_form,
                text="Cerrar sesión automáticamente",
                variable=logout_after_var,
                text_color="#e0e0e0",
            ).place(x=20, y=140)
        except Exception:
            pass
    
    def on_registrar_cover():
        try:
            insertar_cover(username, covered_by_var.get(), cover_form_var.get(), session_id, station)
            print("[DEBUG] Cover registrado correctamente.")
            print("[DEBUG] logout_after_var.get():", logout_after_var.get())
            if logout_after_var.get():
                try:
                    login.logout_silent(session_id, station)
                except Exception as e:
                    print(f"[WARN] logout_silent falló: {e}")
                target_user = (covered_by_var.get() or '').strip()
                if not target_user:
                    messagebox.showwarning("Cover", "Debes indicar 'Covered By' para continuar al main.")
                    return  # Mantener el formulario abierto para que el usuario complete el campo
                ok, sid2, role2 = login.auto_login(target_user, station, password="1234", parent=root, silent=True)
                if not ok:
                    # Mantener el formulario abierto si el login automático falla
                    messagebox.showerror("Auto Login", "No fue posible hacer login automático.")
                    return

            # Cerrar el formulario (flujo normal o cuando el auto-login ya abrió el main)
            try:
                cover_form.destroy()
            except Exception:
                pass

        except Exception as e:
            print("[ERROR] insert cover:", e)

    

    
    # Registrar Cover (se cerrará sesión automáticamente al insertar)
    if UI is not None:
        UI.CTkButton(
            cover_form,
            text="Registrar Cover",
            command=lambda: on_registrar_cover(),
            fg_color="#4a90e2",
            hover_color="#357ABD",
            width=160,
    ).place(x=150, y=180)
    else:
        cover_form_btn = tk.Button(cover_form, text="Registrar Cover", command=lambda: on_registrar_cover())
        cover_form_btn.place(x=30, y=160, width=120)

    _register_singleton('cover_mode', cover_form)
    # No mainloop aquí; es un Toplevel dentro de la app

