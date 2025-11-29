"""
open_specials_window MODERNIZADA
- tksheet para tabla (comportamiento tipo Excel)
- CustomTkinter para UI
- Auto-refresh cada 5 segundos
- Marcas persistentes con colores de fondo
- Filtrado por shift (START SHIFT → ahora)
"""

def open_specials_window(username):
    """Muestra specials del supervisor filtrados por el turno actual (START SHIFT → ahora).
    Las marcas son persistentes en DB y visibles entre supervisores.
    VERSION MODERNIZADA con tksheet + CustomTkinter + auto-refresh"""
    try:
        ex = _focus_singleton('specials')
        if ex:
            return ex

        # Importar CustomTkinter
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

        # Importar tksheet
        USE_SHEET = False
        SheetClass = None
        try:
            from tksheet import Sheet as _Sheet
            SheetClass = _Sheet
            USE_SHEET = True
        except Exception:
            USE_SHEET = False
            SheetClass = None

        top_win = (UI.CTkToplevel() if UI is not None else tk.Toplevel())
        top_win.title(f"Specials de {username} - Turno actual")
        top_win.geometry("1380x600")
        try:
            if UI is None:
                top_win.configure(bg="#2c2f33")
            else:
                top_win.configure(fg_color="#2c2f33")
        except Exception:
            pass
        top_win.resizable(True, True)

        # Variables de estado
        unique_mode = tk.BooleanVar(value=True)  # True = marca única, False = múltiples
        auto_refresh_active = tk.BooleanVar(value=True)  # Auto-refresh activo
        refresh_job = None  # ID del job de after()
        
        cols = ["ID", "Fecha_hora", "ID_Sitio", "Nombre_Actividad", "Cantidad", "Camera", "Descripcion", "Usuario", "Time_Zone", "Marca"]
        
        # Frame principal para tabla
        table_frame = (UI.CTkFrame(top_win, fg_color="#2c2f33") if UI is not None else tk.Frame(top_win, bg="#2c2f33"))
        table_frame.pack(expand=True, fill="both", padx=10, pady=10)

        # Variable para almacenar referencia de sheet/tree
        sheet = None
        tree = None
        data_cache = []  # Cache de datos para sheet

        if USE_SHEET and SheetClass:
            # USAR TKSHEET (moderno)
            sheet = SheetClass(
                table_frame,
                headers=cols,
                theme="dark blue",
                height=500,
                width=1360,
                show_selected_cells_border=True,
                show_row_index=False,
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
                "edit_cell"
            ])
            sheet.pack(fill="both", expand=True)
            
            # Colores personalizados
            sheet.change_theme("dark blue")
            
        else:
            # FALLBACK A TREEVIEW (legacy)
            style = ttk.Style(top_win)
            style.configure("Specials.Treeview",
                            background="#23272a",
                            foreground="#e0e0e0",
                            fieldbackground="#23272a",
                            rowheight=26,
                            bordercolor="#23272a",
                            borderwidth=0)
            style.configure("Specials.Treeview.Heading",
                            background="#23272a",
                            foreground="#a3c9f9",
                            font=("Segoe UI", 10, "bold"))
            style.map("Specials.Treeview", background=[("selected", "#4a90e2")], foreground=[("selected", "#ffffff")])

            yscroll = tk.Scrollbar(table_frame, orient="vertical")
            yscroll.pack(side="right", fill="y")
            xscroll = tk.Scrollbar(table_frame, orient="horizontal")
            xscroll.pack(side="bottom", fill="x")
            
            tree = ttk.Treeview(table_frame, columns=cols, show="headings", 
                               yscrollcommand=yscroll.set, xscrollcommand=xscroll.set,
                               style="Specials.Treeview", selectmode="extended")
            yscroll.config(command=tree.yview)
            xscroll.config(command=tree.xview)
            
            col_widths = {
                "ID": 70, "Fecha_hora": 150, "ID_Sitio": 200, "Nombre_Actividad": 140,
                "Cantidad": 70, "Camera": 90, "Descripcion": 240, "Usuario": 110,
                "Time_Zone": 80, "Marca": 150
            }
            for c in cols:
                tree.heading(c, text=c, anchor="center")
                tree.column(c, width=col_widths.get(c, 100), 
                           anchor="center" if c in ("ID", "Cantidad", "Camera", "Time_Zone", "Marca") else "w")
            
            tree.pack(side="left", fill="both", expand=True)
            
            # Tags para marcas visuales
            tree.tag_configure("oddrow", background="#3a3f44", foreground="#e0e0e0")
            tree.tag_configure("evenrow", background="#2f343a", foreground="#e0e0e0")
            tree.tag_configure("flagged", background="#f5a623", foreground="#111111")  # ámbar
            tree.tag_configure("last", background="#00c853", foreground="#111111")     # verde

        # ============= FUNCIONES AUXILIARES =============
        
        def get_supervisor_shift_start(supervisor_name):
            """Obtiene el último START SHIFT del supervisor dado"""
            try:
                conn = under_super.get_connection()
                cur = conn.cursor()
                cur.execute("""
                    SELECT e.FechaHora
                    FROM Eventos e
                    INNER JOIN user u ON e.ID_Usuario = u.ID_Usuario
                    WHERE u.Nombre_Usuario = %s AND e.Nombre_Actividad = 'START SHIFT'
                    ORDER BY e.FechaHora DESC
                    LIMIT 1
                """, (supervisor_name,))
                row = cur.fetchone()
                cur.close()
                conn.close()
                return row[0] if row and row[0] else None
            except Exception as e:
                print(f"[ERROR] get_supervisor_shift_start: {e}")
                return None

        def load_specials():
            """Carga specials del supervisor desde el último START SHIFT hasta ahora"""
            nonlocal data_cache, refresh_job
            
            try:
                shift_start = get_supervisor_shift_start(username)
                if not shift_start:
                    if USE_SHEET and sheet:
                        sheet.set_sheet_data([["No hay shift activo"] + [""] * (len(cols)-1)])
                    elif tree:
                        tree.delete(*tree.get_children())
                        tree.insert("", "end", values=["No hay shift activo"] + [""] * (len(cols)-1), tags=("oddrow",))
                    return
                
                conn = under_super.get_connection()
                cur = conn.cursor()
                
                # Query: TODOS los specials desde START SHIFT hasta AHORA
                sql = """
                    SELECT ID_special, FechaHora, ID_Sitio, Nombre_Actividad, Cantidad, Camera,
                           Descripcion, Usuario, Time_Zone, marked_status, marked_by, marked_at
                    FROM specials
                    WHERE Supervisor = %s 
                    AND FechaHora >= %s
                    ORDER BY FechaHora DESC
                """
                params = (username, shift_start)
                window_title = f"Specials de {username} - Turno desde {shift_start.strftime('%d/%m/%Y %H:%M')}"
                
                top_win.title(window_title)
                
                cur.execute(sql, params)
                rows = cur.fetchall()
                
                # Resolver nombres de sitios y zonas horarias
                time_zone_cache = {}
                processed = []
                
                for r in rows:
                    rlist = list(r[:9])  # Primeras 9 columnas
                    id_sitio = rlist[2]
                    marked_status = r[9]
                    marked_by = r[10]
                    marked_at = r[11]
                    
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
                            except Exception as e:
                                print(f"[DEBUG] error fetching site for ID_Sitio={id_sitio}: {e}")
                                nombre_sitio = ""
                                tz = ""
                            time_zone_cache[id_sitio] = (nombre_sitio, tz)
                    
                    # Formato visual para ID_Sitio
                    if id_sitio and nombre_sitio:
                        display_site = f"{id_sitio} {nombre_sitio}"
                    elif id_sitio:
                        display_site = str(id_sitio)
                    else:
                        display_site = nombre_sitio or ""
                    
                    rlist[2] = display_site
                    rlist[8] = tz
                    
                    # Formato visual para la marca
                    if marked_status == 'last':
                        mark_display = f"✅ Tratado ({marked_by})" if marked_by else "✅ Tratado"
                    elif marked_status == 'flagged':
                        mark_display = f"🔄 En progreso ({marked_by})" if marked_by else "🔄 En progreso"
                    else:
                        mark_display = ""
                    
                    rlist.append(mark_display)
                    processed.append({
                        'id': r[0],
                        'values': rlist,
                        'marked_status': marked_status
                    })
                
                cur.close()
                conn.close()
                
                # Poblar UI
                if USE_SHEET and sheet:
                    # TKSHEET
                    if not processed:
                        data_cache = [["No hay specials en este turno"] + [""] * (len(cols)-1)]
                        sheet.set_sheet_data(data_cache)
                    else:
                        data_cache = [item['values'] for item in processed]
                        sheet.set_sheet_data(data_cache)
                        
                        # Aplicar colores de fondo según marca
                        for idx, item in enumerate(processed):
                            if item['marked_status'] == 'last':
                                # Verde (#00c853) para tratado
                                sheet.highlight_rows([idx], bg="#00c853", fg="#111111")
                            elif item['marked_status'] == 'flagged':
                                # Ámbar (#f5a623) para en progreso
                                sheet.highlight_rows([idx], bg="#f5a623", fg="#111111")
                        
                        # Ajustar anchos de columna
                        col_widths_list = [70, 150, 200, 140, 70, 90, 240, 110, 80, 150]
                        for idx, width in enumerate(col_widths_list):
                            sheet.set_column_width(idx, width)
                
                elif tree:
                    # TREEVIEW (fallback)
                    tree.delete(*tree.get_children())
                    if not processed:
                        tree.insert("", "end", values=["No hay specials en este turno"] + [""] * (len(cols)-1), tags=("oddrow",))
                    else:
                        for idx, item in enumerate(processed):
                            values = [str(v) if v is not None else "" for v in item['values']]
                            base_tag = "evenrow" if idx % 2 == 0 else "oddrow"
                            
                            if item['marked_status'] == 'last':
                                tags = (base_tag, "last")
                            elif item['marked_status'] == 'flagged':
                                tags = (base_tag, "flagged")
                            else:
                                tags = (base_tag,)
                            
                            tree.insert("", "end", iid=str(item['id']), values=values, tags=tags)
                
                print(f"[DEBUG] Loaded {len(processed)} specials for {username}")
                
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo cargar specials:\n{e}", parent=top_win)
                import traceback
                traceback.print_exc()
            
            # Programar siguiente refresh si auto-refresh está activo
            finally:
                if auto_refresh_active.get():
                    refresh_job = top_win.after(5000, load_specials)  # Refresh cada 5 segundos

        def get_selected_ids():
            """Obtiene los IDs de los registros seleccionados"""
            if USE_SHEET and sheet:
                selected_rows = sheet.get_selected_rows()
                if not selected_rows:
                    return []
                # Obtener IDs de la primera columna
                ids = []
                for row_idx in selected_rows:
                    try:
                        row_data = sheet.get_row_data(row_idx)
                        if row_data and len(row_data) > 0:
                            ids.append(row_data[0])  # Primera columna es ID
                    except Exception:
                        pass
                return ids
            elif tree:
                return list(tree.selection())
            return []

        def mark_selected():
            """Marca los registros seleccionados en la base de datos"""
            sel = get_selected_ids()
            if not sel:
                messagebox.showinfo("Marcas", "Selecciona uno o más specials para marcar.", parent=top_win)
                return
            
            try:
                conn = under_super.get_connection()
                cur = conn.cursor()
                
                if unique_mode.get():
                    # Modo único: desmarcar todos, marcar solo el último seleccionado
                    cur.execute("UPDATE specials SET marked_status = NULL, marked_at = NULL, marked_by = NULL WHERE Supervisor = %s", (username,))
                    last_id = sel[-1]
                    cur.execute("""
                        UPDATE specials 
                        SET marked_status = 'last', marked_at = NOW(), marked_by = %s
                        WHERE ID_Special = %s
                    """, (username, last_id))
                else:
                    # Modo múltiple: marcar todos como 'flagged'
                    for item_id in sel:
                        cur.execute("""
                            UPDATE specials 
                            SET marked_status = 'flagged', marked_at = NOW(), marked_by = %s
                            WHERE ID_Special = %s
                        """, (username, item_id))
                
                conn.commit()
                cur.close()
                conn.close()
                
                load_specials()
                messagebox.showinfo("Marcas", f"✅ {len(sel)} registro(s) marcado(s)", parent=top_win)
                
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo marcar:\n{e}", parent=top_win)
                import traceback
                traceback.print_exc()

        def unmark_selected():
            """Desmarca los registros seleccionados"""
            sel = get_selected_ids()
            if not sel:
                return
            
            try:
                conn = under_super.get_connection()
                cur = conn.cursor()
                
                for item_id in sel:
                    cur.execute("""
                        UPDATE specials 
                        SET marked_status = NULL, marked_at = NULL, marked_by = NULL
                        WHERE ID_Special = %s
                    """, (item_id,))
                
                conn.commit()
                cur.close()
                conn.close()
                
                load_specials()
                
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo desmarcar:\n{e}", parent=top_win)
                import traceback
                traceback.print_exc()

        def clear_marks():
            """Limpia todas las marcas del supervisor actual"""
            if not messagebox.askyesno("Limpiar marcas", 
                                       f"¿Desmarcar TODOS los specials de {username}?", 
                                       parent=top_win):
                return
            
            try:
                conn = under_super.get_connection()
                cur = conn.cursor()
                cur.execute("""
                    UPDATE specials 
                    SET marked_status = NULL, marked_at = NULL, marked_by = NULL
                    WHERE Supervisor = %s
                """, (username,))
                conn.commit()
                cur.close()
                conn.close()
                
                load_specials()
                messagebox.showinfo("Limpiar marcas", "✅ Todas las marcas han sido eliminadas", parent=top_win)
                
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo limpiar marcas:\n{e}", parent=top_win)

        def copy_to_clipboard(event=None):
            """Copia la selección al portapapeles"""
            try:
                if USE_SHEET and sheet:
                    sheet.copy()  # tksheet tiene copy integrado
                    messagebox.showinfo("Copiar", "✅ Datos copiados al portapapeles", parent=top_win)
                elif tree:
                    items = tree.selection() if tree.selection() else tree.get_children()
                    if not items:
                        messagebox.showinfo("Copiar", "No hay filas para copiar.", parent=top_win)
                        return "break"
                    
                    lines = ["\t".join(cols)]
                    for it in items:
                        vals = list(tree.item(it, 'values'))
                        clean = [str(v).replace("\t", " ").replace("\r", " ").replace("\n", " ") for v in vals[:len(cols)]]
                        lines.append("\t".join(clean))
                    
                    data = "\n".join(lines)
                    top_win.clipboard_clear()
                    top_win.clipboard_append(data)
                    top_win.update()
                    messagebox.showinfo("Copiar", f"✅ {len(items)} fila(s) copiadas", parent=top_win)
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo copiar:\n{e}", parent=top_win)
            return "break"

        def toggle_auto_refresh():
            """Activa/desactiva auto-refresh"""
            if auto_refresh_active.get():
                print("[DEBUG] Auto-refresh activado")
                load_specials()  # Iniciar ciclo
            else:
                print("[DEBUG] Auto-refresh desactivado")
                if refresh_job:
                    top_win.after_cancel(refresh_job)

        # ============= UI CONTROLS =============
        
        # Botonera principal
        btn_frame = (UI.CTkFrame(top_win, fg_color="#2c2f33") if UI is not None else tk.Frame(top_win, bg="#2c2f33"))
        btn_frame.pack(fill="x", padx=10, pady=(0,8))
        
        if UI is not None:
            UI.CTkButton(btn_frame, text="⟳ Refrescar Manual", fg_color="#13988e", hover_color="#0f7f76", 
                        command=load_specials).pack(side="left")
            UI.CTkButton(btn_frame, text="📋 Copiar", fg_color="#3b4754", hover_color="#4a5560", 
                        command=copy_to_clipboard).pack(side="left", padx=(8,0))
            UI.CTkCheckBox(btn_frame, text="Auto-refresh (5s)", variable=auto_refresh_active, 
                          fg_color="#4a90e2", text_color="#e0e0e0", command=toggle_auto_refresh).pack(side="left", padx=(12,0))
        else:
            tk.Button(btn_frame, text="⟳ Refrescar Manual", command=load_specials, bg="#13988e", fg="#fff", relief="flat").pack(side="left")
            tk.Button(btn_frame, text="📋 Copiar", command=copy_to_clipboard, bg="#3b4754", fg="#e0e0e0", relief="flat").pack(side="left", padx=(8,0))
            tk.Checkbutton(btn_frame, text="Auto-refresh (5s)", variable=auto_refresh_active, command=toggle_auto_refresh,
                          bg="#2c2f33", fg="#e0e0e0", selectcolor="#2c2f33").pack(side="left", padx=(12,0))

        # Controles de marcas
        marks_frame = (UI.CTkFrame(top_win, fg_color="#2c2f33") if UI is not None else tk.Frame(top_win, bg="#2c2f33"))
        marks_frame.pack(fill="x", padx=10, pady=(0,8))
        
        if UI is not None:
            UI.CTkCheckBox(marks_frame, text="Marca única (último tratado)", variable=unique_mode, 
                          fg_color="#4a90e2", text_color="#e0e0e0").pack(side="left")
            UI.CTkButton(marks_frame, text="✅ Marcar como tratado", fg_color="#00c853", hover_color="#00a043", 
                        command=mark_selected).pack(side="left", padx=(12,0))
            UI.CTkButton(marks_frame, text="❌ Desmarcar", fg_color="#3b4754", hover_color="#4a5560", 
                        command=unmark_selected).pack(side="left", padx=(8,0))
            UI.CTkButton(marks_frame, text="🗑️  Limpiar todo", fg_color="#d32f2f", hover_color="#b71c1c", 
                        command=clear_marks).pack(side="left", padx=(8,0))
        else:
            tk.Checkbutton(marks_frame, text="Marca única (último tratado)", variable=unique_mode,
                          bg="#2c2f33", fg="#e0e0e0", selectcolor="#2c2f33").pack(side="left")
            tk.Button(marks_frame, text="✅ Marcar como tratado", command=mark_selected, 
                     bg="#00c853", fg="#fff", relief="flat").pack(side="left", padx=(12,0))
            tk.Button(marks_frame, text="❌ Desmarcar", command=unmark_selected, 
                     bg="#3b4754", fg="#e0e0e0", relief="flat").pack(side="left", padx=(8,0))
            tk.Button(marks_frame, text="🗑️  Limpiar todo", command=clear_marks, 
                     bg="#d32f2f", fg="#fff", relief="flat").pack(side="left", padx=(8,0))

        # Info box
        info_frame = (UI.CTkFrame(top_win, fg_color="#1a1d21") if UI is not None else tk.Frame(top_win, bg="#1a1d21"))
        info_frame.pack(fill="x", padx=10, pady=(0,10))
        
        info_text = "💡 Las marcas son visibles para todos los supervisores. Auto-refresh actualiza cada 5 segundos."
        if UI is not None:
            UI.CTkLabel(info_frame, text=info_text, text_color="#a3c9f9", 
                       font=("Segoe UI", 9, "italic")).pack(pady=6)
        else:
            tk.Label(info_frame, text=info_text, bg="#1a1d21", fg="#a3c9f9",
                    font=("Segoe UI", 9, "italic")).pack(pady=6)

        # Atajos de teclado
        if tree:
            tree.bind("<Control-c>", copy_to_clipboard)
            tree.bind("<Control-C>", copy_to_clipboard)
            tree.bind("<Double-1>", lambda e: mark_selected())

        # Cleanup al cerrar
        def on_close():
            nonlocal refresh_job
            if refresh_job:
                top_win.after_cancel(refresh_job)
            top_win.destroy()
        
        top_win.protocol("WM_DELETE_WINDOW", on_close)

        # Registro singleton
        _register_singleton('specials', top_win)
        
        # Carga inicial
        load_specials()
        
        return top_win

    except Exception as e:
        messagebox.showerror("Error", f"No se pudo abrir la ventana:\n{e}")
        import traceback
        traceback.print_exc()
        return None
