
import tkinter as tk
from tkinter import messagebox
from controllers.rol_cover_controller import RolCoverController


def render_rol_cover_container(parent, UI=None):
    """Renderiza el contenedor de gestión de Rol de Cover"""
    # Instanciar controlador
    controller = RolCoverController()
    if UI is not None:
        rol_cover_container = UI.CTkFrame(parent, fg_color="#2c2f33")
    else:
        rol_cover_container = tk.Frame(parent, bg="#2c2f33")
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

    # ========== FUNCIONES INTERNAS (CLOSURES) ==========
    # Estas funciones tienen acceso a las variables locales (listboxes, controller)
    # y delegan toda la lógica al controlador
    
    def refrescar_lista_operadores():
        """Refresca ambas listas desde la BD a través del controlador"""
        try:
            con_acceso, sin_acceso = controller.get_operators_covers_statuses()
            
            # Limpiar listboxes
            listbox_sin_acceso.delete(0, tk.END)
            listbox_con_acceso.delete(0, tk.END)
            
            # Poblar listbox sin acceso (Statuses != 2)
            for operador in sorted(sin_acceso):
                listbox_sin_acceso.insert(tk.END, operador)
            
            # Poblar listbox con acceso (Statuses == 2)
            for operador in sorted(con_acceso):
                listbox_con_acceso.insert(tk.END, operador)
            
            print(f"[DEBUG] Lista refrescada: {len(sin_acceso)} sin acceso, {len(con_acceso)} con acceso")
        
        except Exception as e:
            print(f"[ERROR] refrescar_lista_operadores: {e}")
            messagebox.showerror("Error", f"No se pudo refrescar la lista:\n{str(e)}")
    
    def habilitar_acceso():
        """Habilita acceso a covers para los operadores seleccionados (Statuses -> 2)"""
        seleccionados_indices = listbox_sin_acceso.curselection()
        
        if not seleccionados_indices:
            messagebox.showwarning("Advertencia", "Selecciona al menos un operador de la lista izquierda")
            return
        
        # Obtener nombres de operadores seleccionados
        operadores_seleccionados = [listbox_sin_acceso.get(i) for i in seleccionados_indices]
        
        try:
            # Delegar al controlador (Statuses = 2 significa acceso a covers)
            success = controller.en_dis_able_access_covers(operadores_seleccionados, new_status=2)
            
            if success:
                messagebox.showinfo("Éxito", f"✅ Acceso habilitado para {len(operadores_seleccionados)} operador(es)")
                refrescar_lista_operadores()
            else:
                messagebox.showerror("Error", "No se pudo habilitar el acceso")
        
        except Exception as e:
            print(f"[ERROR] habilitar_acceso: {e}")
            messagebox.showerror("Error", f"Error al habilitar acceso:\n{str(e)}")
    
    def deshabilitar_acceso():
        """Quita acceso a covers para los operadores seleccionados (Statuses -> 1)"""
        seleccionados_indices = listbox_con_acceso.curselection()
        
        if not seleccionados_indices:
            messagebox.showwarning("Advertencia", "Selecciona al menos un operador de la lista derecha")
            return
        
        # Obtener nombres de operadores seleccionados
        operadores_seleccionados = [listbox_con_acceso.get(i) for i in seleccionados_indices]
        
        try:
            # Delegar al controlador (Statuses = 1 significa sin acceso a covers)
            success = controller.en_dis_able_access_covers(operadores_seleccionados, new_status=1)
            
            if success:
                messagebox.showinfo("Éxito", f"🚫 Acceso removido para {len(operadores_seleccionados)} operador(es)")
                refrescar_lista_operadores()
            else:
                messagebox.showerror("Error", "No se pudo remover el acceso")
        
        except Exception as e:
            print(f"[ERROR] deshabilitar_acceso: {e}")
            messagebox.showerror("Error", f"Error al remover acceso:\n{str(e)}")

    # ========== BOTONES DE ACCIÓN ==========

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
                 font=("Segoe UI", 13, "bold")).pack(side="left", padx=10, pady=5)
        
        tk.Button(buttons_frame_rol, 
                 text="⬅️ Quitar Acceso a Covers",
                 command=deshabilitar_acceso,
                 bg="#f04747",
                 fg="white",
                 font=("Segoe UI", 13, "bold")).pack(side="left", padx=10, pady=5)
        
        tk.Button(buttons_frame_rol, 
                 text="🔄 Refrescar Lista",
                 command=refrescar_lista_operadores,
                 bg="#4a90e2",
                 fg="white",
                 font=("Segoe UI", 13, "bold")).pack(side="left", padx=10, pady=5)
    
    # ========== INICIALIZACIÓN ==========
    # Cargar datos iniciales
    refrescar_lista_operadores()
    
    # ========== RETORNO ==========
    # Retornar referencias para uso externo si es necesario
    return {
        'container': rol_cover_container,
        'listbox_sin_acceso': listbox_sin_acceso,
        'listbox_con_acceso': listbox_con_acceso,
        'controller': controller,
        'refresh': refrescar_lista_operadores
    }