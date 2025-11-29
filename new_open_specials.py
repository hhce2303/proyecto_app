"""
Nueva versión de open_specials_window con:
1. Marcas persistentes en DB (visibles entre supervisores)
2. Filtro por shift (START SHIFT a END SHIFT o ahora)

Copiar este código a backend_super.py reemplazando la función open_specials_window
"""

def open_specials_window(username):
    """Muestra specials del supervisor filtrados por el turno actual (START SHIFT → END SHIFT/ahora).
    Las marcas son persistentes en DB y visibles entre supervisores."""
    try:
        ex = _focus_singleton('specials')
        if ex:
            return ex

        # Intentar UI moderna
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

        top_win = (UI.CTkToplevel() if UI is not None else tk.Toplevel())
        top_win.title(f"Specials de {username} - Turno actual")
        top_win.geometry("1280x520")
        try:
            if UI is None:
                top_win.configure(bg="#2c2f33")
            else:
                top_win.configure(fg_color="#2c2f33")
        except Exception:
            pass
        top_win.resizable(True, True)

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

        cols = ("ID", "Fecha_hora", "ID_Sitio", "Nombre_Actividad", "Cantidad", "Camera", "Descripcion", "Usuario", "Time_Zone", "Marca")
        
        # Treeview principal
        table_frame = (UI.CTkFrame(top_win, fg_color="#2c2f33") if UI is not None else tk.Frame(top_win, bg="#2c2f33"))
        table_frame.pack(expand=True, fill="both", padx=10, pady=10)

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
            "Time_Zone": 80, "Marca": 120
        }
        for c in cols:
            tree.heading(c, text=c, anchor="center")
            tree.column(c, width=col_widths.get(c, 100), anchor="center" if c in ("ID", "Cantidad", "Camera", "Time_Zone", "Marca") else "w")
        
        tree.pack(side="left", fill="both", expand=True)
        
        # Tags para marcas visuales
        tree.tag_configure("oddrow", background="#3a3f44", foreground="#e0e0e0")
        tree.tag_configure("evenrow", background="#2f343a", foreground="#e0e0e0")
        tree.tag_configure("flagged", background="#f5a623", foreground="#111111")  # ámbar (en progreso)
        tree.tag_configure("last", background="#00c853", foreground="#111111")     # verde (tratado/completado)
        
        unique_mode = tk.BooleanVar(value=True)  # True = marca única (último), False = múltiples

        def get_supervisor_shift_start(supervisor_name):
            """Obtiene el último START SHIFT del supervisor dado"""
            try:
                conn = under_super.get_connection()
                cur = conn.cursor()
                # Buscar el START SHIFT más reciente del supervisor
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
            try:
                shift_start = get_supervisor_shift_start(username)
                if not shift_start:
                    tree.delete(*tree.get_children())
                    tree.insert("", "end", values=["No hay shift activo"] + [""] * (len(cols)-1), tags=("oddrow",))
                    return
                
                conn = under_super.get_connection()
                cur = conn.cursor()
                
                # Mostrar TODOS los specials desde START SHIFT hasta AHORA
                # (sin importar si ya hizo END SHIFT, porque los specials se trabajan durante el turno)
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
                    # r: (ID, FechaHora, ID_Sitio, Nombre_Actividad, Cantidad, Camera, Descripcion, Usuario, Time_Zone, marked_status, marked_by, marked_at)
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
                
                # Poblar Treeview
                tree.delete(*tree.get_children())
                if not processed:
                    tree.insert("", "end", values=["No hay specials en este turno"] + [""] * (len(cols)-1), tags=("oddrow",))
                else:
                    for idx, item in enumerate(processed):
                        values = [str(v) if v is not None else "" for v in item['values']]
                        base_tag = "evenrow" if idx % 2 == 0 else "oddrow"
                        
                        # Aplicar tag de marca si existe
                        if item['marked_status'] == 'last':
                            tags = (base_tag, "last")
                        elif item['marked_status'] == 'flagged':
                            tags = (base_tag, "flagged")
                        else:
                            tags = (base_tag,)
                        
                        tree.insert("", "end", iid=str(item['id']), values=values, tags=tags)
                
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo cargar specials:\n{e}", parent=top_win)
                import traceback
                traceback.print_exc()

        def mark_selected():
            """Marca los registros seleccionados en la base de datos"""
            sel = tree.selection()
            if not sel:
                messagebox.showinfo("Marcas", "Selecciona uno o más specials para marcar.", parent=top_win)
                return
            
            try:
                conn = under_super.get_connection()
                cur = conn.cursor()
                
                if unique_mode.get():
                    # Modo único: desmarcar todos los previos del supervisor, marcar solo el último seleccionado como 'last'
                    # Primero desmarcar todos
                    cur.execute("UPDATE specials SET marked_status = NULL, marked_at = NULL, marked_by = NULL WHERE Supervisor = %s", (username,))
                    # Marcar solo el último seleccionado
                    last_id = sel[-1]
                    cur.execute("""
                        UPDATE specials 
                        SET marked_status = 'last', marked_at = NOW(), marked_by = %s
                        WHERE ID_Special = %s
                    """, (username, last_id))
                else:
                    # Modo múltiple: agregar marca 'flagged' a los seleccionados
                    for item_id in sel:
                        cur.execute("""
                            UPDATE specials 
                            SET marked_status = 'flagged', marked_at = NOW(), marked_by = %s
                            WHERE ID_Special = %s
                        """, (username, item_id))
                
                conn.commit()
                cur.close()
                conn.close()
                
                load_specials()  # Recargar para mostrar cambios
                messagebox.showinfo("Marcas", f"✅ {len(sel)} registro(s) marcado(s)", parent=top_win)
                
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo marcar:\n{e}", parent=top_win)
                import traceback
                traceback.print_exc()

        def unmark_selected():
            """Desmarca los registros seleccionados"""
            sel = tree.selection()
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

        # Atajos de teclado
        tree.bind("<Control-c>", copy_to_clipboard)
        tree.bind("<Control-C>", copy_to_clipboard)
        tree.bind("<Double-1>", lambda e: mark_selected())

        # Botonera principal
        btn_frame = (UI.CTkFrame(top_win, fg_color="#2c2f33") if UI is not None else tk.Frame(top_win, bg="#2c2f33"))
        btn_frame.pack(fill="x", padx=10, pady=(0,8))
        
        if UI is not None:
            UI.CTkButton(btn_frame, text="⟳ Refrescar", fg_color="#13988e", hover_color="#0f7f76", command=load_specials).pack(side="left")
            UI.CTkButton(btn_frame, text="📋 Copiar", fg_color="#3b4754", hover_color="#4a5560", command=copy_to_clipboard).pack(side="left", padx=(8,0))
        else:
            tk.Button(btn_frame, text="⟳ Refrescar", command=load_specials, bg="#13988e", fg="#fff", relief="flat").pack(side="left")
            tk.Button(btn_frame, text="📋 Copiar", command=copy_to_clipboard, bg="#3b4754", fg="#e0e0e0", relief="flat").pack(side="left", padx=(8,0))

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
                          bg="#2c2f33", fg="#e0e0e0", selectcolor="#2c2f33", activebackground="#2c2f33",
                          anchor='w').pack(side="left")
            tk.Button(marks_frame, text="✅ Marcar como tratado", command=mark_selected, 
                     bg="#00c853", fg="#fff", relief="flat").pack(side="left", padx=(12,0))
            tk.Button(marks_frame, text="❌ Desmarcar", command=unmark_selected, 
                     bg="#3b4754", fg="#e0e0e0", relief="flat").pack(side="left", padx=(8,0))
            tk.Button(marks_frame, text="🗑️  Limpiar todo", command=clear_marks, 
                     bg="#d32f2f", fg="#fff", relief="flat").pack(side="left", padx=(8,0))

        # Info box
        info_frame = (UI.CTkFrame(top_win, fg_color="#1a1d21") if UI is not None else tk.Frame(top_win, bg="#1a1d21"))
        info_frame.pack(fill="x", padx=10, pady=(0,10))
        
        info_text = "💡 Las marcas son visibles para todos los supervisores. Doble-click para marcar rápido."
        if UI is not None:
            UI.CTkLabel(info_frame, text=info_text, text_color="#a3c9f9", 
                       font=("Segoe UI", 9, "italic")).pack(pady=6)
        else:
            tk.Label(info_frame, text=info_text, bg="#1a1d21", fg="#a3c9f9",
                    font=("Segoe UI", 9, "italic")).pack(pady=6)

        # Función "Otros Specials" con filtro de shift
        def _user_is_supervisor(uname: str) -> bool:
            try:
                conn = under_super.get_connection()
                cur = conn.cursor()
                cur.execute("SELECT Rol FROM user WHERE Nombre_Usuario = %s LIMIT 1", (uname,))
                row = cur.fetchone()
                cur.close()
                conn.close()
                return (row and str(row[0]).strip().lower() == 'supervisor')
            except Exception:
                return False

        def otros_specials():
            """Ver y tomar specials de otros supervisores (filtrados por turno)"""
            sel_win = tk.Toplevel(top_win)
            sel_win.title("Otros Specials - Selecciona Supervisor")
            sel_win.configure(bg="#2c2f33")
            sel_win.geometry("380x340")
            sel_win.resizable(False, False)

            tk.Label(sel_win, text="Supervisor (origen):", bg="#2c2f33", fg="#00bfae",
                    font=("Segoe UI", 13, "bold")).pack(pady=(14, 6))

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
                conn = under_super.get_connection()
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

                # Ventana de specials del otro supervisor (con filtro de shift)
                key = f"otros_specials_{old_sup}"
                ex = _focus_singleton(key)
                if ex:
                    return ex

                lst_win = tk.Toplevel(top_win)
                lst_win.title(f"Otros Specials - {old_sup}")
                lst_win.configure(bg="#2c2f33")
                lst_win.geometry("1200x540")
                lst_win.resizable(True, True)

                # Tabla
                frame2 = tk.Frame(lst_win, bg="#2c2f33")
                frame2.pack(expand=True, fill="both", padx=12, pady=10)
                yscroll2 = tk.Scrollbar(frame2, orient="vertical")
                yscroll2.pack(side="right", fill="y")
                xscroll2 = tk.Scrollbar(frame2, orient="horizontal")
                xscroll2.pack(side="bottom", fill="x")
                
                cols2 = ("ID", "FechaHora", "ID_Sitio", "Nombre_Actividad", "Cantidad", "Camera", 
                        "Descripcion", "Usuario", "Time_Zone", "Marca")
                tree2 = ttk.Treeview(frame2, columns=cols2, show="headings", 
                                    yscrollcommand=yscroll2.set, xscrollcommand=xscroll2.set,
                                    selectmode="extended")
                yscroll2.config(command=tree2.yview)
                xscroll2.config(command=tree2.xview)
                
                for c in cols2:
                    tree2.heading(c, text=c, anchor="center")
                    tree2.column(c, width=col_widths.get(c, 100), anchor="center" if c in ("ID", "Cantidad", "Camera", "Time_Zone", "Marca") else "w")
                
                tree2.pack(side="left", expand=True, fill="both")
                tree2.tag_configure("flagged", background="#f5a623", foreground="#111111")
                tree2.tag_configure("last", background="#00c853", foreground="#111111")

                def cargar_lista():
                    """Cargar specials del otro supervisor filtrados por su turno"""
                    try:
                        shift_start = get_supervisor_shift_start(old_sup)
                        if not shift_start:
                            tree2.delete(*tree2.get_children())
                            tree2.insert("", "end", values=[f"{old_sup} no tiene shift activo"] + [""] * (len(cols2)-1))
                            return
                        
                        shift_end = get_supervisor_shift_end(old_sup, shift_start)
                        
                        conn = under_super.get_connection()
                        cur = conn.cursor()
                        
                        if shift_end:
                            sql = """
                                SELECT ID_Special, FechaHora, ID_Sitio, Nombre_Actividad, Cantidad, Camera,
                                       Descripcion, Usuario, Time_Zone, marked_status, marked_by
                                FROM specials
                                WHERE Supervisor = %s AND FechaHora >= %s AND FechaHora <= %s
                                ORDER BY FechaHora DESC
                            """
                            params = (old_sup, shift_start, shift_end)
                            title = f"Otros Specials - {old_sup} (Turno {shift_start.strftime('%H:%M')} a {shift_end.strftime('%H:%M')})"
                        else:
                            sql = """
                                SELECT ID_Special, FechaHora, ID_Sitio, Nombre_Actividad, Cantidad, Camera,
                                       Descripcion, Usuario, Time_Zone, marked_status, marked_by
                                FROM specials
                                WHERE Supervisor = %s AND FechaHora >= %s
                                ORDER BY FechaHora DESC
                            """
                            params = (old_sup, shift_start)
                            title = f"Otros Specials - {old_sup} (Turno desde {shift_start.strftime('%H:%M')})"
                        
                        lst_win.title(title)
                        cur.execute(sql, params)
                        rows = cur.fetchall()
                        
                        tree2.delete(*tree2.get_children())
                        for r in rows:
                            values = list(r[:9])
                            marked_status = r[9]
                            marked_by = r[10]
                            
                            # Formato de marca
                            if marked_status == 'last':
                                mark_display = f"✅ Tratado ({marked_by})" if marked_by else "✅ Tratado"
                                tag = "last"
                            elif marked_status == 'flagged':
                                mark_display = f"🔄 En progreso ({marked_by})" if marked_by else "🔄 En progreso"
                                tag = "flagged"
                            else:
                                mark_display = ""
                                tag = ""
                            
                            values.append(mark_display)
                            values_str = ["" if v is None else str(v) for v in values]
                            tree2.insert("", "end", values=values_str, iid=str(r[0]), tags=(tag,) if tag else ())
                        
                        cur.close()
                        conn.close()
                    except Exception as e:
                        messagebox.showerror("Error", f"No se pudo cargar specials:\n{e}", parent=lst_win)

                def tomar_specials():
                    """Tomar specials seleccionados para el supervisor actual"""
                    sel = tree2.selection()
                    if not sel:
                        messagebox.showwarning("Tomar Specials", "Selecciona uno o más registros.", parent=lst_win)
                        return
                    
                    ids = []
                    for item in sel:
                        try:
                            ids.append(int(item))
                        except Exception:
                            vals = tree2.item(item, 'values')
                            if vals:
                                try:
                                    ids.append(int(vals[0]))
                                except Exception:
                                    pass
                    
                    if not ids:
                        messagebox.showwarning("Tomar Specials", "No se pudieron leer los IDs.", parent=lst_win)
                        return
                    
                    if not messagebox.askyesno("Tomar Specials", 
                                               f"¿Reasignar {len(ids)} special(s) de {old_sup} a {username}?",
                                               parent=lst_win):
                        return
                    
                    try:
                        conn = under_super.get_connection()
                        cur = conn.cursor()
                        updated = 0
                        for sid in ids:
                            cur.execute("UPDATE specials SET Supervisor = %s WHERE ID_Special = %s", (username, sid))
                            updated += cur.rowcount
                        conn.commit()
                        cur.close()
                        conn.close()
                        
                        messagebox.showinfo("Tomar Specials", f"✅ {updated} registro(s) reasignados a {username}", parent=lst_win)
                        cargar_lista()
                        load_specials()  # Refrescar ventana principal
                    except Exception as e:
                        messagebox.showerror("Error", f"No se pudo reasignar:\n{e}", parent=lst_win)

                # Botonera
                btns2 = tk.Frame(lst_win, bg="#2c2f33")
                btns2.pack(fill="x", padx=12, pady=(0,10))
                tk.Button(btns2, text="⟳ Refrescar", bg="#13988e", fg="#fff", relief="flat", command=cargar_lista).pack(side="left")
                tk.Button(btns2, text="📥 Tomar Specials", bg="#4a90e2", fg="#fff", relief="flat", command=tomar_specials).pack(side="left", padx=8)

                _register_singleton(key, lst_win)
                cargar_lista()

            tk.Button(sel_win, text="Aceptar", bg="#13988e", fg="#fff", relief="flat", command=abrir_lista_specials).pack(pady=8)

        # Mostrar botón "Otros Specials" solo si es Supervisor
        if _user_is_supervisor(username):
            if UI is not None:
                UI.CTkButton(btn_frame, text="👥 Otros Specials", fg_color="#3b4754", hover_color="#4a5560", 
                            command=otros_specials).pack(side="left", padx=(8,0))
            else:
                tk.Button(btn_frame, text="👥 Otros Specials", command=otros_specials, 
                         bg="#3b4754", fg="#e0e0e0", relief="flat").pack(side="left", padx=(8,0))

        # Cargar inicialmente
        _register_singleton('specials', top_win)
        top_win.after_idle(load_specials)
        
    except Exception as e:
        print(f"[ERROR] open_specials_window: {e}")
        import traceback
        traceback.print_exc()
