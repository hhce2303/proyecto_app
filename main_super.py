import tkinter as tk
from tkinter import ttk
from datetime import datetime, timedelta
from tkinter import ttk, messagebox, simpledialog
import re
import backend_super
import login  # ✅ para volver al login después de logout
import under_super
import json
import os
import tkcalendar

from PIL import Image, ImageTk


def open_main_window(username, station, role, session_id):
    global global_root, global_station
    # Intentar usar CustomTkinter para la ventana principal
    UI = None
    try:
        import importlib
        ctk = importlib.import_module('customtkinter')
        try:
            ctk.set_appearance_mode("dark")
            ctk.set_default_color_theme("dark-blue")
        except Exception:
            pass
        # Monkey-patch CTkScrollableFrame to guard against event.widget being a str (seen on some Tk/py versions)
        try:
            from customtkinter.windows.widgets import ctk_scrollable_frame as _csf
            if hasattr(_csf, "CTkScrollableFrame"):
                _orig_check = _csf.CTkScrollableFrame.check_if_master_is_canvas
                def _safe_check(self, widget):
                    try:
                        if not hasattr(widget, "master"):
                            return False
                    except Exception:
                        return False
                    return _orig_check(self, widget)
                _csf.CTkScrollableFrame.check_if_master_is_canvas = _safe_check

                _orig_wheel = _csf.CTkScrollableFrame._mouse_wheel_all
                def _safe_wheel(self, event):
                    try:
                        w = getattr(event, "widget", None)
                        if not hasattr(w, "master"):
                            return
                    except Exception:
                        return
                    return _orig_wheel(self, event)
                _csf.CTkScrollableFrame._mouse_wheel_all = _safe_wheel
        except Exception:
            pass
        UI = ctk
    except Exception:
        UI = None

    # Siempre usar Toplevel con un único root
    base_root = getattr(tk, '_default_root', None)
    try:
        base_exists = bool(base_root and base_root.winfo_exists())
    except Exception:
        base_exists = False

    created_own_root = False
    if not base_exists:
        # Crear un root oculto si no existe
        if UI is not None:
            base_root = UI.CTk()
        else:
            base_root = tk.Tk()
        try:
            base_root.withdraw()
        except Exception:
            pass
        created_own_root = True

    # Crear SIEMPRE una ventana Toplevel para el panel principal
    if UI is not None:
        root = UI.CTkToplevel(base_root)
    else:
        root = tk.Toplevel(base_root)
    
    # al inicio del archivo
    global_root = None
    global_station = None
    root.title(f"Daily Log")
    width, height = 340, 390
    root.geometry(f"{width}x{height}")
    try:
        root.configure(bg="#1f2227" if UI is None else None)
    except Exception:
        pass
    root.resizable(True, True)
    
    # Inicializar tablas de backup al inicio de la aplicación
    try:
        backend_super.create_backup_tables()
    except Exception as e:
        print(f"⚠️ Error al inicializar tablas de backup: {e}")

    # Header moderno con usuario y estado
    if UI is not None:
        header = UI.CTkFrame(root, fg_color="#23272a", corner_radius=0)
    else:
        header = tk.Frame(root, bg="#23272a")
    header.pack(fill="x", padx=0, pady=0)
    
    try:
        if UI is not None:
            # Botón pequeño de información usando el carácter ℹ en la parte superior derecha
            UI.CTkButton(
                header,
                text="ℹ",
                width=28,
                height=28,
                fg_color="#3a3f44",
                hover_color="#4a5560",
                corner_radius=6,
                command=backend_super.show_info,
            ).pack(side="right", padx=(0, 8), pady=8)

            UI.CTkLabel(header, text=f"{username}", font=("Segoe UI", 16, "bold"), text_color="#e0e0e0").pack(side="left", padx=20, pady=12)
            UI.CTkLabel(header, text=f"{role} | {station}", font=("Segoe UI", 15), text_color="#a3c9f9").pack(side="right", padx=(0,20), pady=12)
        else:
            # Botón pequeño de información usando el carácter ℹ en Tk clásico
            tk.Button(
                header,
                text="ℹ",
                width=2,
                bg="#3a3f44",
                fg="#e0e0e0",
                activebackground="#4a5560",
                relief="flat",
                command=backend_super.show_info,
            ).pack(side="right", padx=(0, 8), pady=8)

            tk.Label(header, text=f"Daily Log de, {username}", bg="#23272a", fg="#e0e0e0", font=("Segoe UI", 16, "bold")).pack(side="left", padx=20, pady=12)
            tk.Label(header, text=f"{role} | {station}", bg="#23272a", fg="#a3c9f9", font=("Segoe UI", 15)).pack(side="right", padx=(0,20), pady=12)
    except Exception:
        pass

    # Separador
    try:
        ttk.Separator(root, orient="horizontal").pack(fill="x")
    except Exception:
        pass

    # Frame principal para los tiles (grid de botones)
    if UI is not None:
        main_frame = UI.CTkScrollableFrame(root, fg_color="#2c2f33")
    else:
        main_frame = tk.Frame(root, bg="#2c2f33")
    main_frame.pack(fill="both", expand=True, padx=12, pady=12)

    # Cargar configuración de permisos del rol
    def load_role_permissions(role_name):
        try:
            with open(under_super.CONFIG_PATH, "r", encoding="utf-8") as f:
                role_permissions = json.load(f)
                return role_permissions.get(role_name, [])
        except Exception as e:
            print(f"⚠️ No se pudo cargar roles_config.json: {e}")
            return []

    # Diccionario completo de todos los botones disponibles (con lambdas para pasar parámetros)
    all_buttons = {
        "Registro Diario": {"command": lambda: backend_super.open_hybrid_events(username, session_id, station, root), "permission": "Register"},
        "Eventos": {"command": lambda: backend_super.show_events(username), "permission": "Event"},
        "Reporte": {"command": lambda: backend_super.open_report_window(username), "permission": "Report"},
        "Cover": {"command": lambda: backend_super.cover_mode(session_id, station, root, username), "permission": "Cover"},
        "Extra": {"command": lambda: backend_super.open_admin_window(root), "permission": "Extra"},
        "Rol": {"command": lambda: backend_super.open_rol_window(), "permission": "Rol"},
        "View": {"command": lambda: backend_super.open_view_window(), "permission": "View"},
        "Map": {"command": lambda: backend_super.show_map(), "permission": "Map"},
        "Specials": {"command": lambda: backend_super.open_hybrid_events_supervisor(username=username, root=root), "permission": "Specials"},
        "Lead Specials": {"command": lambda: backend_super.open_hybrid_events_lead_supervisor(username=username, root=root), "permission": "Lead Specials"},
        "Audit": {"command": lambda: backend_super.audit_view(parent=None), "permission": "Audit"},
        "Time Zone": {"command": lambda: backend_super.open_tz_editor(username, station, role, session_id), "permission": "Time Zone"},
        # Abrir la ventana de estadísticas de Cover (evita pasar argumentos no esperados a get_cover_stats)
        "Cover Time": {"command": lambda: backend_super.open_cover_stats_window(root), "permission": "Cover Time"},
        "Papelera": {"command": lambda: backend_super.open_trash_window(root), "permission": "Papelera"},
    }

    # Diccionario de mapeo de iconos disponibles (los que existen)
    icon_map = {
        "Registro Diario": "add.png",
        "Eventos": "event.png",
        "Reporte": "report.png",
        "Cover": "settings.png",
        "Extra": "extra.png",
        "Rol": "rol.png",
        "View": "view.png",
        "Map": "map.png",
        "Specials": "specials.png",
        "Lead Specials": "specials.png",  # Usar mismo ícono que Specials
        "Audit": "audit.png",
        "Time Zone": "Time_Zone.png",
        "Cover Time": "Cover_Time.png",
        "Papelera": "trash.png",
    }

    # Filtrar botones según permisos del rol (antes de cargar iconos)
    allowed = load_role_permissions(role)
    print(f"DEBUG: Role '{role}' tiene permisos: {allowed}")
    # Comparar exactamente como vienen del JSON (sin cambiar mayúsculas/minúsculas)
    filtered_buttons = {k: v for k, v in all_buttons.items() if v.get("permission") in allowed}
    print(f"DEBUG: Botones filtrados: {list(filtered_buttons.keys())}")
    print(f"DEBUG: Permisos en all_buttons: {[v.get('permission') for v in all_buttons.values()]}")

    # Cargar iconos disponibles desde la ruta de red
    icons_loaded = {}
    icons_dir = under_super.ICON_PATH  # Usar la ruta de red definida en under_super
    print(f"DEBUG: Buscando iconos en: {icons_dir}")
    if os.path.exists(icons_dir):
        for btn_name in filtered_buttons.keys():
            icon_file = icon_map.get(btn_name)
            if not icon_file:
                print(f"DEBUG: (i) Sin icono mapeado para: {btn_name}")
                continue
            icon_path = os.path.join(icons_dir, icon_file)
            if os.path.exists(icon_path):
                try:
                    
                    img = Image.open(icon_path).resize((40, 40), Image.Resampling.LANCZOS)
                    # Usar CTkImage si CustomTkinter está disponible
                    if UI is not None:
                        icons_loaded[btn_name] = UI.CTkImage(light_image=img, dark_image=img, size=(40, 40))
                    else:


                        icons_loaded[btn_name] = ImageTk.PhotoImage(img, master=root)
                except Exception as e:
                    print(f"DEBUG: ✗ Error cargando {icon_file}: {e}")
            else:
                print(f"DEBUG: ✗ Icono no encontrado en ruta: {icon_path}")
    else:
        print(f"DEBUG: ✗ Carpeta de iconos no existe: {icons_dir}")

    

    # Crear tiles en grid (2 columnas x 2 filas)
    row_idx, col_idx = 0, 0
    if not filtered_buttons:
        # Si no hay botones, mostrar mensaje
        no_perms_label = tk.Label(
            main_frame, 
            text="No tienes permisos asignados.\nContacta al administrador.",
            bg="#2c2f33",
            fg="#e0e0e0",
            font=("Segoe UI", 14),
            justify="center"
        )
        no_perms_label.pack(expand=True, pady=50)
    
    for btn_name, btn_data in filtered_buttons.items():
        icon_img = icons_loaded.get(btn_name)
        
        if UI is not None:
            # Tile con CustomTkinter (más pequeño: 140x110)
            tile = UI.CTkFrame(main_frame, fg_color="#3a3f44", corner_radius=8, width=140, height=110)
            tile.grid(row=row_idx, column=col_idx, padx=6, pady=6, sticky="nsew")
            tile.grid_propagate(False)
            
            if icon_img:
                # Botón con icono ocupando todo el tile (el botón es toda la superficie)
                btn = UI.CTkButton(
                    tile,
                    text="",
                    image=icon_img,
                    fg_color="#3a3f44",
                    hover_color="#4a5560",
                    corner_radius=8,
                    command=btn_data["command"]
                )
                btn.place(relx=0, rely=0, relwidth=1, relheight=1)
                btn.image = icon_img  # Referencia fuerte
            else:
                # Botón sin icono (solo texto)
                btn = UI.CTkButton(
                    tile,
                    text=btn_name,
                    font=("Segoe UI", 20, "bold"),
                    fg_color="#4a90e2",
                    hover_color="#357ABD",
                    corner_radius=6,
                    height=320,
                    command=btn_data["command"]
                )
                btn.pack(fill="both", expand=True, padx=1, pady=11)

        col_idx += 1
        if col_idx >= 2:  # 2 columnas en lugar de 3
            col_idx = 0
            row_idx += 1

    # Configurar peso de columnas para que se expandan uniformemente
    for c in range(2):  # 2 columnas
        main_frame.grid_columnconfigure(c, weight=1, uniform="tile")

    # Footer con botón de cerrar sesión
    if UI is not None:
        footer = UI.CTkFrame(root, fg_color="#23272a", corner_radius=0, height=60)
    else:
        footer = tk.Frame(root, bg="#23272a", height=60)
    footer.pack(fill="x", padx=0, pady=0)
    footer.pack_propagate(False)

    def do_logout_wrapper():
        try:
            # Delegar completamente el cierre de sesión al módulo login
            # (evita destruir la ventana antes de que login maneje el flujo)
            login.do_logout(session_id, station, root)
        except Exception:
            try:
                root.destroy()
            except Exception:
                pass

    if UI is not None:
        UI.CTkButton(
            footer,
            text="Cerrar Sesión (Ctrl+L)",
            font=("Segoe UI", 11),
            fg_color="#343F47",
            hover_color="#b71c1c",
            corner_radius=6,
            width=120,
            height=36,
            command=do_logout_wrapper
        ).pack(side="right", padx=6, pady=12)

        # Botón dinámico de Shift (Start/End)
        def update_shift_button():
            """Actualiza el botón de shift según el estado del turno"""
            try:
                # Consultar el estado actual (True = puede iniciar => mostrar Start Shift)
                can_start = backend_super.Dinamic_button_Shift(username)
                print(f"DEBUG: Dinamic_button_Shift returned: {can_start}")

                def on_start_click():
                    try:
                        backend_super.on_start_shift(username)
                    finally:
                        # refrescar estado del botón luego de insertar
                        root.after(50, update_shift_button)

                def on_end_click():
                    try:
                        backend_super.on_end_shift(username)
                    finally:
                        # refrescar estado del botón luego de insertar
                        root.after(50, update_shift_button)

                if can_start:
                    # Mostrar botón "Start Shift" en azul
                    if UI is not None:
                        shift_btn.configure(
                            text="Start Shift",
                            fg_color="#4a90e2",
                            hover_color="#357ABD"
                        )
                    else:
                        shift_btn.configure(
                            text="Start Shift",
                            bg="#4a90e2",
                            activebackground="#357ABD"
                        )
                    shift_btn.configure(command=on_start_click)
                else:
                    # Mostrar botón "End of Shift" en rojo
                    if UI is not None:
                        shift_btn.configure(
                            text="End of Shift",
                            fg_color="#343F47",
                            hover_color="#b71c1c"
                        )
                    else:
                        shift_btn.configure(
                            text="End of Shift",
                            bg="#d32f2f",
                            activebackground="#b71c1c"
                        )
                    shift_btn.configure(command=on_end_click)
            except Exception as e:
                print(f"DEBUG: Error actualizando botón de shift: {e}")

            
    
        
        # Crear el botón dinámico de shift
        if UI is not None:
            shift_btn = UI.CTkButton(
                footer,
                text="Loading...",
                font=("Segoe UI", 11),
                fg_color="#4a90e2",
                hover_color="#357ABD",
                corner_radius=6,
                width=120,
                height=36
            )
            shift_btn.pack(side="left", padx=6, pady=12)
        else:
            shift_btn = tk.Button(
                footer,
                text="Loading...",
                font=("Segoe UI", 11),
                bg="#4a90e2",
                fg="white",
                activebackground="#357ABD",
                relief="flat",
                cursor="hand2"
            )
            shift_btn.pack(side="left", padx=6, pady=12)
        
        # Actualizar el botón al iniciar
        update_shift_button()

    # Atajos de teclado
    def bind_shortcuts(event=None):
        # Ctrl+E: Eventos
        if "Eventos" in filtered_buttons:
            root.bind("<Control-e>", lambda e: filtered_buttons["Eventos"]["command"]())
        # Ctrl+R: Reporte
        if "Reporte" in filtered_buttons:
            root.bind("<Control-r>", lambda e: filtered_buttons["Reporte"]["command"]())
        # Ctrl+U: Specials
        if "Specials" in filtered_buttons:
            root.bind("<Control-s>", lambda e: filtered_buttons["Specials"]["command"]())
        # Ctrl+A: Cover
        if "Cover" in filtered_buttons:
            root.bind("<Control-a>", lambda e: filtered_buttons["Cover"]["command"]())
        # Ctrl+L: Logout
        root.bind("<Control-l>", lambda e: do_logout_wrapper())
        # Escape: Cerrar programa completo (no dejar root oculto colgado)
        root.bind("<Escape>", lambda e: close_program())

    bind_shortcuts()

    # Singleton window tracking
    backend_super._register_singleton("main", root)
    
    def close_program():
        try:
            # Ejecutar logout antes de cerrar
            login.do_logout(session_id, station, root)
        except Exception as e:
            print(f"DEBUG: Error en logout durante cierre: {e}")
            try:
                # Si falla el logout, destruir de todas formas
                base_root.destroy()
            except Exception:
                pass
    root.protocol("WM_DELETE_WINDOW", close_program)

    # Solo arrancar mainloop si creamos nuestro propio root oculto
    if created_own_root:
        root.mainloop()
