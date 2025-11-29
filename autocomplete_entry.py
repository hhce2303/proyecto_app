"""
AutoComplete Entry Widget - Entry con autocompletado inteligente
"""
import tkinter as tk
from tkinter import ttk
from difflib import get_close_matches

# ⭐ IMPORTAR FUNCIONES DE BASE DE DATOS
try:
    import under_super
except ImportError:
    under_super = None


class AutoCompleteEntry(tk.Entry):
    """
    Entry personalizado con autocompletado en tiempo real
    
    Características:
    - Muestra sugerencias mientras escribes
    - Ajuste automático al valor más cercano con Enter
    - Lista desplegable con opciones filtradas
    - Coincidencia difusa con difflib
    """
    
    def __init__(self, parent, values=None, textvariable=None,
                 raise_invalid=False, allow_reverse=True, numeric_auto_expand=True, **kwargs):
        """
        Args:
            parent: Widget padre
            values: Lista de valores posibles para autocompletar
            textvariable: Variable tk.StringVar para almacenar el valor
            **kwargs: Argumentos adicionales para tk.Entry
        """
        # Configurar textvariable
        if textvariable is None:
            textvariable = tk.StringVar()
        self.textvariable = textvariable
        
        # Inicializar Entry con textvariable
        super().__init__(parent, textvariable=self.textvariable, **kwargs)
        
        # Lista de valores para autocompletado
        self.values = values or []
        # Flags de comportamiento
        self.raise_invalid = raise_invalid          # Mostrar error si valor inválido
        self.allow_reverse = allow_reverse          # Habilitar coincidencias de derecha a izquierda (endswith / reversed)
        self.numeric_auto_expand = numeric_auto_expand  # Expansión directa para coincidencia única numérica
        
        # Ventana desplegable para sugerencias
        self.listbox = None
        self.listbox_visible = False
        
        # Última búsqueda para evitar duplicados
        self.last_search = ""
        
        # Configurar eventos
        self._setup_bindings()
    
    def _setup_bindings(self):
        """Configura los eventos del widget"""
        # Detectar escritura
        self.bind("<KeyRelease>", self._on_key_release)
        
        # Enter: Ajustar al valor más cercano
        self.bind("<Return>", self._on_enter)
        self.bind("<KP_Enter>", self._on_enter)
        
        # Tab: Autocompletar primera sugerencia
        self.bind("<Tab>", self._on_tab)
        
        # Escape: Cerrar sugerencias
        self.bind("<Escape>", self._hide_listbox)
        
        # Flechas: Navegar sugerencias
        self.bind("<Down>", self._on_arrow_down)
        self.bind("<Up>", self._on_arrow_up)
        
        # Perder foco: Ocultar sugerencias
        self.bind("<FocusOut>", self._on_focus_out)
    
    def _on_key_release(self, event):
        """Se ejecuta al escribir en el Entry"""
        # Ignorar teclas especiales
        if event.keysym in ("Return", "KP_Enter", "Tab", "Escape", 
                            "Up", "Down", "Left", "Right", 
                            "Shift_L", "Shift_R", "Control_L", "Control_R"):
            return
        
        current_text = self.get().strip()
        
        # Si está vacío, ocultar sugerencias
        if not current_text:
            self._hide_listbox()
            return

        # ⭐ AUTOCOMPLETAR DIRECTO POR ID (solo dígitos) (opcional)
        if current_text.isdigit():
            id_matches = [v for v in self.values if f"({current_text})" in str(v)]
            if not id_matches:
                # Formato fallback sin paréntesis "Nombre ID"
                id_matches = []
                for v in self.values:
                    parts = str(v).strip().split()
                    if parts and parts[-1].isdigit() and parts[-1] == current_text:
                        id_matches.append(v)
            # Expansión directa si única coincidencia y flag activo
            if self.numeric_auto_expand and len(id_matches) == 1:
                self.set_value(id_matches[0])
                # También mostrar la coincidencia en listbox para feedback visual
                self._show_suggestions(id_matches)
                self.last_search = id_matches[0]
                return
            # Si no expandimos directamente, continuamos para mostrar sugerencias múltiples o únicas
        
        # Evitar búsquedas duplicadas
        if current_text == self.last_search:
            return
        
        self.last_search = current_text
        
        # Buscar coincidencias
        matches = self._find_matches(current_text)
        
        if matches:
            self._show_suggestions(matches)
        else:
            self._hide_listbox()
    
    def _find_matches(self, text):
        """
        Encuentra valores que coincidan con el texto ingresado
        
        Usa múltiples estrategias en orden de prioridad:
        1. Coincidencia exacta (case-insensitive)
        2. Empieza con el texto
        3. Contiene el texto
        4. Contiene palabras del texto
        5. Coincidencia difusa
        """
        if not text or not self.values:
            return []
        
        text_lower = text.lower()
        text_words = text_lower.split()

        # ⭐ BÚSQUEDA POR ID DIRECTA (si el usuario escribe solo dígitos)
        # Permite que escribir "130" encuentre "Nombre Sitio (130)"
        if text.isdigit():
            id_matches = []
            for v in self.values:
                v_str = str(v)
                # Formato moderno con paréntesis: "Nombre (130)"
                if f"({text})" in v_str:
                    id_matches.append(v_str)
                else:
                    # Formato antiguo: último token numérico
                    parts = v_str.strip().split()
                    if parts and parts[-1].isdigit() and parts[-1] == text:
                        id_matches.append(v_str)
            if id_matches:
                # Limitar a 10 resultados y devolver inmediatamente (prioridad máxima)
                return id_matches[:10]
        
        exact_matches = []
        starts_with = []
        ends_with = []  # Para escritura "de derecha a izquierda" (coincidencia por sufijo)
        contains = []
        word_matches = []
        
        for v in self.values:
            v_lower = v.lower()
            
            # 1. Coincidencia exacta
            if v_lower == text_lower:
                exact_matches.append(v)
            # 2. Empieza con el texto
            elif v_lower.startswith(text_lower):
                starts_with.append(v)
            # 3. Termina con el texto (si allow_reverse)
            elif self.allow_reverse and v_lower.endswith(text_lower):
                ends_with.append(v)
            # 4. Contiene el texto
            elif text_lower in v_lower:
                contains.append(v)
            # 5. Contiene todas las palabras del texto
            elif all(word in v_lower for word in text_words):
                word_matches.append(v)
        
        # Combinar resultados en orden de prioridad
        results = exact_matches + starts_with + ends_with + contains + word_matches
        
        # Si no hay resultados, intentar coincidencia difusa
        if not results:
            results = get_close_matches(text, self.values, n=10, cutoff=0.3)
        
        # Limitar a 10 sugerencias y eliminar duplicados
        seen = set()
        unique_results = []
        for item in results:
            if item not in seen:
                seen.add(item)
                unique_results.append(item)
                if len(unique_results) >= 10:
                    break
        
        return unique_results
    
    def _show_suggestions(self, matches):
        """Muestra la lista desplegable con sugerencias"""
        # Crear listbox si no existe
        if self.listbox is None:
            self.listbox = tk.Listbox(
                self.master,
                height=min(8, len(matches)),
                bg="#2b2b2b",
                fg="#ffffff",
                selectbackground="#4a90e2",
                selectforeground="#ffffff",
                font=self.cget("font"),
                relief="solid",
                borderwidth=1
            )
            
            # Evento de selección con click
            self.listbox.bind("<Button-1>", self._on_listbox_click)
            self.listbox.bind("<Double-Button-1>", self._on_listbox_double_click)
        
        # Actualizar contenido
        self.listbox.delete(0, tk.END)
        for match in matches:
            self.listbox.insert(tk.END, match)
        
        # Posicionar debajo del Entry
        x = self.winfo_rootx()
        y = self.winfo_rooty() + self.winfo_height()
        width = self.winfo_width()
        
        self.listbox.place(x=x, y=y, width=width)
        
        # Ajustar altura
        self.listbox.config(height=min(8, len(matches)))
        
        self.listbox_visible = True
    
    def _hide_listbox(self, event=None):
        """Oculta la lista de sugerencias"""
        if self.listbox:
            self.listbox.place_forget()
            self.listbox_visible = False
    
    def _on_listbox_click(self, event):
        """Selecciona una sugerencia con un click"""
        if self.listbox:
            selection = self.listbox.curselection()
            if selection:
                value = self.listbox.get(selection[0])
                self.set_value(value)
    
    def _on_listbox_double_click(self, event):
        """Selecciona y cierra con doble click"""
        self._on_listbox_click(event)
        self._hide_listbox()
        # Propagar evento Enter para agregar
        self.event_generate("<Return>")
    
    def _on_enter(self, event):
        """Ajusta al valor más cercano al presionar Enter"""
        # Si hay sugerencias visibles, tomar la primera
        if self.listbox_visible and self.listbox:
            try:
                # Si hay algo seleccionado en el listbox, usar eso
                selection = self.listbox.curselection()
                if selection:
                    selected_value = self.listbox.get(selection[0])
                    self.set_value(selected_value)
                else:
                    # Si no hay selección, tomar el primer elemento
                    first_value = self.listbox.get(0)
                    self.set_value(first_value)
                self._hide_listbox()
                return "break"  # Detener propagación
            except:
                pass
        
        # Si no hay sugerencias, buscar la mejor coincidencia
        current_text = self.get().strip()
        if current_text:
            best_match = self._find_best_match(current_text)
            if best_match:
                self.set_value(best_match)
                print(f"[DEBUG] AutoComplete: ajustado '{current_text}' -> '{best_match}'")
            elif self.raise_invalid:
                # Lanzar error visual si no es válido
                from tkinter import messagebox
                messagebox.showerror("Sitio inválido", f"No se encontró coincidencia para: '{current_text}'")
                return "break"
        
        self._hide_listbox()
        # NO hacer break aquí - permitir propagación para agregar evento
    
    def _on_tab(self, event):
        """Autocompleta con la primera sugerencia al presionar Tab"""
        if self.listbox_visible and self.listbox:
            try:
                first_value = self.listbox.get(0)
                self.set_value(first_value)
                self._hide_listbox()
                return "break"
            except:
                pass
        return None
    
    def _on_arrow_down(self, event):
        """Navega hacia abajo en las sugerencias"""
        if self.listbox_visible and self.listbox:
            current = self.listbox.curselection()
            if current:
                next_index = current[0] + 1
                if next_index < self.listbox.size():
                    self.listbox.selection_clear(0, tk.END)
                    self.listbox.selection_set(next_index)
                    self.listbox.see(next_index)
            else:
                self.listbox.selection_set(0)
            return "break"
    
    def _on_arrow_up(self, event):
        """Navega hacia arriba en las sugerencias"""
        if self.listbox_visible and self.listbox:
            current = self.listbox.curselection()
            if current:
                prev_index = current[0] - 1
                if prev_index >= 0:
                    self.listbox.selection_clear(0, tk.END)
                    self.listbox.selection_set(prev_index)
                    self.listbox.see(prev_index)
            return "break"
    
    def _on_focus_out(self, event):
        """Oculta sugerencias al perder foco y valida si es requerido"""
        def _hide_and_validate():
            self._hide_listbox()
            if self.raise_invalid:
                current = self.get().strip()
                if current and self.validate_value() is None:
                    from tkinter import messagebox
                    messagebox.showerror("Sitio inválido", f"Valor no reconocido: '{current}'")
        self.after(200, _hide_and_validate)
    
    def _find_best_match(self, text):
        """
        Encuentra la mejor coincidencia usando múltiples estrategias
        """
        if not text or not self.values:
            return None
        
        text_lower = text.lower()

        # ⭐ Mejor coincidencia por ID si el input son solo dígitos
        if text.isdigit():
            for v in self.values:
                v_str = str(v)
                if f"({text})" in v_str:
                    return v_str
                parts = v_str.strip().split()
                if parts and parts[-1].isdigit() and parts[-1] == text:
                    return v_str
        
        # 1. Coincidencia exacta (case-insensitive)
        for v in self.values:
            if v.lower() == text_lower:
                return v
        
        # 2. Empieza con el texto
        for v in self.values:
            if v.lower().startswith(text_lower):
                return v
        # 3. Termina con el texto (reverse)
        if self.allow_reverse:
            for v in self.values:
                if v.lower().endswith(text_lower):
                    return v
        # 4. Contiene el texto
        for v in self.values:
            if text_lower in v.lower():
                return v
        # 5. Todas las palabras están contenidas
        text_words = text_lower.split()
        for v in self.values:
            v_lower = v.lower()
            if all(word in v_lower for word in text_words):
                return v
        
        # 6. Coincidencia difusa (más permisivo)
        matches = get_close_matches(text, self.values, n=1, cutoff=0.3)
        
        return matches[0] if matches else None
    
    def set_value(self, value):
        """Establece el valor del Entry"""
        self.delete(0, tk.END)
        self.insert(0, value)
    
    def set_values(self, values):
        """Actualiza la lista de valores posibles"""
        self.values = values or []
    
    def get_value(self):
        """Obtiene el valor actual del Entry"""
        return self.get().strip()
    
    def validate_value(self):
        """
        Valida si el valor actual está en la lista
        
        Returns:
            str or None: Valor ajustado o None si no es válido
        """
        current = self.get().strip()
        
        # Verificar coincidencia exacta (case-insensitive)
        for v in self.values:
            if v.lower() == current.lower():
                return v
        
        # Buscar mejor coincidencia
        best_match = self._find_best_match(current)
        return best_match


# ⭐ VERSION PARA CUSTOMTKINTER
try:
    import customtkinter as ctk
    
    class AutoCompleteEntryCTk(ctk.CTkEntry):
        """Versión CustomTkinter del AutoCompleteEntry"""
        
        def __init__(self, parent, values=None, textvariable=None,
                 raise_invalid=False, allow_reverse=True, numeric_auto_expand=True, **kwargs):
            if textvariable is None:
                textvariable = tk.StringVar()
            self.textvariable = textvariable
            
            super().__init__(parent, textvariable=self.textvariable, **kwargs)
            
            self.values = values or []
            self.raise_invalid = raise_invalid
            self.allow_reverse = allow_reverse
            self.numeric_auto_expand = numeric_auto_expand
            self.listbox = None
            self.listbox_visible = False
            self.last_search = ""
            
            self._setup_bindings()
        
        def _setup_bindings(self):
            """Configura los eventos del widget"""
            self.bind("<KeyRelease>", self._on_key_release)
            self.bind("<Return>", self._on_enter)
            self.bind("<KP_Enter>", self._on_enter)
            self.bind("<Tab>", self._on_tab)
            self.bind("<Escape>", self._hide_listbox)
            self.bind("<Down>", self._on_arrow_down)
            self.bind("<Up>", self._on_arrow_up)
            self.bind("<FocusOut>", self._on_focus_out)
        
        def _on_key_release(self, event):
            if event.keysym in ("Return", "KP_Enter", "Tab", "Escape", 
                                "Up", "Down", "Left", "Right", 
                                "Shift_L", "Shift_R", "Control_L", "Control_R"):
                return
            
            current_text = self.get().strip()
            
            if not current_text:
                self._hide_listbox()
                return
            
            # ⭐ AUTOCOMPLETAR DIRECTO POR ID (solo dígitos) (opcional)
            if current_text.isdigit():
                id_matches = [v for v in self.values if f"({current_text})" in str(v)]
                if not id_matches:
                    id_matches = []
                    for v in self.values:
                        parts = str(v).strip().split()
                        if parts and parts[-1].isdigit() and parts[-1] == current_text:
                            id_matches.append(v)
                if self.numeric_auto_expand and len(id_matches) == 1:
                    self.set_value(id_matches[0])
                    self._show_suggestions(id_matches)
                    self.last_search = id_matches[0]
                    return

            if current_text == self.last_search:
                return
            
            self.last_search = current_text
            matches = self._find_matches(current_text)
            
            if matches:
                self._show_suggestions(matches)
            else:
                self._hide_listbox()
        
        def _find_matches(self, text):
            """Búsqueda mejorada con múltiples estrategias"""
            if not text or not self.values:
                return []
            
            text_lower = text.lower()
            text_words = text_lower.split()

            # ⭐ BÚSQUEDA POR ID DIRECTA (input solo dígitos)
            if text.isdigit():
                id_matches = []
                for v in self.values:
                    v_str = str(v)
                    if f"({text})" in v_str:
                        id_matches.append(v_str)
                    else:
                        parts = v_str.strip().split()
                        if parts and parts[-1].isdigit() and parts[-1] == text:
                            id_matches.append(v_str)
                if id_matches:
                    return id_matches[:10]
            
            exact_matches = []
            starts_with = []
            ends_with = []
            contains = []
            word_matches = []
            
            for v in self.values:
                v_lower = v.lower()
                
                if v_lower == text_lower:
                    exact_matches.append(v)
                elif v_lower.startswith(text_lower):
                    starts_with.append(v)
                elif self.allow_reverse and v_lower.endswith(text_lower):
                    ends_with.append(v)
                elif text_lower in v_lower:
                    contains.append(v)
                elif all(word in v_lower for word in text_words):
                    word_matches.append(v)
            
            results = exact_matches + starts_with + ends_with + contains + word_matches
            
            if not results:
                results = get_close_matches(text, self.values, n=10, cutoff=0.3)
            
            seen = set()
            unique_results = []
            for item in results:
                if item not in seen:
                    seen.add(item)
                    unique_results.append(item)
                    if len(unique_results) >= 10:
                        break
            
            return unique_results
        
        def _show_suggestions(self, matches):
            if self.listbox is None:
                self.listbox = tk.Listbox(
                    self.master,
                    height=min(8, len(matches)),
                    bg="#2b2b2b",
                    fg="#ffffff",
                    selectbackground="#4a90e2",
                    selectforeground="#ffffff",
                    font=("Segoe UI", 11),
                    relief="solid",
                    borderwidth=1
                )
                self.listbox.bind("<Button-1>", self._on_listbox_click)
                self.listbox.bind("<Double-Button-1>", self._on_listbox_double_click)
            
            self.listbox.delete(0, tk.END)
            for match in matches:
                self.listbox.insert(tk.END, match)
            
            x = self.winfo_rootx()
            y = self.winfo_rooty() + self.winfo_height()
            width = self.winfo_width()
            
            self.listbox.place(x=x, y=y, width=width)
            self.listbox.config(height=min(8, len(matches)))
            self.listbox_visible = True
        
        def _hide_listbox(self, event=None):
            if self.listbox:
                self.listbox.place_forget()
                self.listbox_visible = False
        
        def _on_listbox_click(self, event):
            if self.listbox:
                selection = self.listbox.curselection()
                if selection:
                    value = self.listbox.get(selection[0])
                    self.set_value(value)
        
        def _on_listbox_double_click(self, event):
            self._on_listbox_click(event)
            self._hide_listbox()
            self.event_generate("<Return>")
        
        def _on_enter(self, event):
            if self.listbox_visible and self.listbox:
                try:
                    # Si hay algo seleccionado, usar eso
                    selection = self.listbox.curselection()
                    if selection:
                        selected_value = self.listbox.get(selection[0])
                        self.set_value(selected_value)
                    else:
                        # Si no, usar el primero
                        first_value = self.listbox.get(0)
                        self.set_value(first_value)
                    self._hide_listbox()
                    return "break"
                except:
                    pass
            
            current_text = self.get().strip()
            if current_text:
                best_match = self._find_best_match(current_text)
                if best_match:
                    self.set_value(best_match)
                    print(f"[DEBUG] AutoCompleteCTk: ajustado '{current_text}' -> '{best_match}'")
                elif self.raise_invalid:
                    from tkinter import messagebox
                    messagebox.showerror("Sitio inválido", f"No se encontró coincidencia para: '{current_text}'")
                    return "break"
            
            self._hide_listbox()
        
        def _on_tab(self, event):
            if self.listbox_visible and self.listbox:
                try:
                    first_value = self.listbox.get(0)
                    self.set_value(first_value)
                    self._hide_listbox()
                    return "break"
                except:
                    pass
            return None
        
        def _on_arrow_down(self, event):
            if self.listbox_visible and self.listbox:
                current = self.listbox.curselection()
                if current:
                    next_index = current[0] + 1
                    if next_index < self.listbox.size():
                        self.listbox.selection_clear(0, tk.END)
                        self.listbox.selection_set(next_index)
                        self.listbox.see(next_index)
                else:
                    self.listbox.selection_set(0)
                return "break"
        
        def _on_arrow_up(self, event):
            if self.listbox_visible and self.listbox:
                current = self.listbox.curselection()
                if current:
                    prev_index = current[0] - 1
                    if prev_index >= 0:
                        self.listbox.selection_clear(0, tk.END)
                        self.listbox.selection_set(prev_index)
                        self.listbox.see(prev_index)
                return "break"
        
        def _on_focus_out(self, event):
            def _hide_and_validate():
                self._hide_listbox()
                if self.raise_invalid:
                    current = self.get().strip()
                    if current and self.validate_value() is None:
                        from tkinter import messagebox
                        messagebox.showerror("Sitio inválido", f"Valor no reconocido: '{current}'")
            self.after(200, _hide_and_validate)
        
        def _find_best_match(self, text):
            """Encuentra la mejor coincidencia con múltiples estrategias"""
            if not text or not self.values:
                return None
            
            text_lower = text.lower()

            # ⭐ Mejor coincidencia por ID si el usuario escribe solo dígitos
            if text.isdigit():
                for v in self.values:
                    v_str = str(v)
                    if f"({text})" in v_str:
                        return v_str
                    parts = v_str.strip().split()
                    if parts and parts[-1].isdigit() and parts[-1] == text:
                        return v_str
            
            # 1. Coincidencia exacta
            for v in self.values:
                if v.lower() == text_lower:
                    return v
            
            # 2. Empieza con
            for v in self.values:
                if v.lower().startswith(text_lower):
                    return v
            # 3. Termina con
            if self.allow_reverse:
                for v in self.values:
                    if v.lower().endswith(text_lower):
                        return v
            # 4. Contiene
            for v in self.values:
                if text_lower in v.lower():
                    return v
            # 5. Palabras contenidas
            text_words = text_lower.split()
            for v in self.values:
                v_lower = v.lower()
                if all(word in v_lower for word in text_words):
                    return v
            
            # 6. Difusa
            matches = get_close_matches(text, self.values, n=1, cutoff=0.3)
            return matches[0] if matches else None
        
        def set_value(self, value):
            self.delete(0, tk.END)
            self.insert(0, value)
        
        def set_values(self, values):
            self.values = values or []
        
        def get_value(self):
            return self.get().strip()
        
        def validate_value(self):
            current = self.get().strip()
            for v in self.values:
                if v.lower() == current.lower():
                    return v
            best_match = self._find_best_match(current)
            return best_match

except ImportError:
    AutoCompleteEntryCTk = None
