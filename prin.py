def create_user_table_tab(self, tab, tabla, data, rol):
        # Crear frame para tksheet
        import customtkinter as ctk
        from tksheet import Sheet
        
        # Si no hay tab (modo standalone), crear ventana
        if tab is None:
            win = ctk.CTk()
            win.title("User Board")
            win.geometry("1100x600")
            parent = win
        else:
            # Usar el tab proporcionado
            parent = tab
            win = None
        
        # Crear frame principal
        sheet_frame = ctk.CTkFrame(parent, fg_color="#2c2f33")
        sheet_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Agregar título (siempre visible para debug)
        title_text = f"Tabla de {tabla} - Rol: {rol}" if tabla else "User Board - Vista de Datos"
        ctk.CTkLabel(sheet_frame, text=title_text, 
                     text_color="#00bfae",
                     font=ctk.CTkFont(size=16, weight="bold")).pack(pady=10)
        
        sheet_tools_frame = ctk.CTkFrame(parent, fg_color="#23272a")
        sheet_tools_frame.pack(fill="both", expand=True, padx=10, pady=10)


        # Crear tksheet
        sheet = Sheet(
        sheet_frame,
        headers= data['headers'],
        theme="dark blue",
        height=450,
        width=1020,
        show_selected_cells_border=True,
        show_row_index=True,
        show_top_left=False,
        empty_horizontal=0,
        empty_vertical=0
        )
        # Configurar bindings (solo lectura con selección)
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
        self.sheet = sheet  # Guardar referencia a la hoja
        sheet.pack(fill="both", expand=True)
        sheet.change_theme("dark blue")
        # Cargar datos
        sheet.set_sheet_data(data['rows'])
        
        # Si es modo standalone, ejecutar mainloop
        if tab is None:
            win.mainloop()
        
        return sheet