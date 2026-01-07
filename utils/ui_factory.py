"""
UI Factory - Abstracción para crear widgets con CustomTkinter o Tkinter
Elimina duplicación de código if UI is not None / else
"""
import tkinter as tk


class UIFactory:
    """
    Factory para crear widgets abstrayendo CustomTkinter vs Tkinter.
    Elimina la necesidad de bloques if/else duplicados en toda la aplicación.
    
    Uso:
        factory = UIFactory(UI=customtkinter_module)  # o None para tkinter
        frame = factory.frame(parent, bg="#2c2f33")
        button = factory.button(parent, "Texto", command_func, bg="#4D6068")
    """
    
    def __init__(self, UI=None):
        """
        Args:
            UI: Módulo CustomTkinter o None para usar tkinter estándar
        """
        self.UI = UI
        self.is_custom = UI is not None
    
    def frame(self, parent, **kwargs):
        """
        Crea un frame abstrayendo CustomTkinter/Tkinter
        
        Args:
            parent: Widget padre
            **kwargs: 
                - bg/fg_color: Color de fondo
                - corner_radius: Radio de esquinas (solo CustomTkinter)
                - height/width: Dimensiones
        
        Returns:
            CTkFrame o tk.Frame
        """
        if self.is_custom:
            ctk_kwargs = {}
            if 'bg' in kwargs:
                ctk_kwargs['fg_color'] = kwargs['bg']
            if 'fg_color' in kwargs:
                ctk_kwargs['fg_color'] = kwargs['fg_color']
            if 'corner_radius' in kwargs:
                ctk_kwargs['corner_radius'] = kwargs['corner_radius']
            if 'height' in kwargs:
                ctk_kwargs['height'] = kwargs['height']
            if 'width' in kwargs:
                ctk_kwargs['width'] = kwargs['width']
            
            return self.UI.CTkFrame(parent, **ctk_kwargs)
        else:
            tk_kwargs = {}
            if 'bg' in kwargs:
                tk_kwargs['bg'] = kwargs['bg']
            if 'fg_color' in kwargs:
                tk_kwargs['bg'] = kwargs['fg_color']
            if 'height' in kwargs:
                tk_kwargs['height'] = kwargs['height']
            if 'width' in kwargs:
                tk_kwargs['width'] = kwargs['width']
            
            return tk.Frame(parent, **tk_kwargs)
        
    def scrollable_frame(self, parent, **kwargs):
        """
        Crea un frame scrollable abstrayendo CustomTkinter/Tkinter
        
        Args:
            parent: Widget padre
            **kwargs: 
                - bg/fg_color: Color de fondo
                """
        if self.is_custom:
            ctk_kwargs = {}
            if 'bg' in kwargs:
                ctk_kwargs['fg_color'] = kwargs['bg']
            if 'fg_color' in kwargs:
                ctk_kwargs['fg_color'] = kwargs['fg_color']
            
            return self.UI.CTkScrollableFrame(parent, **ctk_kwargs)
        else:
            tk_kwargs = {}
            if 'bg' in kwargs:
                tk_kwargs['bg'] = kwargs['bg']
            if 'fg_color' in kwargs:
                tk_kwargs['bg'] = kwargs['fg_color']
            
            # Implementación básica de frame scrollable con Tkinter
            canvas = tk.Canvas(parent, **tk_kwargs)
            scrollbar = tk.Scrollbar(parent, command=canvas.yview)
            scrollable_frame = tk.Frame(canvas, **tk_kwargs)

            scrollable_frame.bind(
                "<Configure>",
                lambda e: canvas.configure(
                    scrollregion=canvas.bbox("all")
                )
            )

            canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
            canvas.configure(yscrollcommand=scrollbar.set)

            container = tk.Frame(parent)
            canvas.pack(side="left", fill="both", expand=True)
            scrollbar.pack(side="right", fill="y")

            return container

        
    
    def button(self, parent, text, command, **kwargs):
        """
        Crea un botón abstrayendo CustomTkinter/Tkinter
        
        Args:
            parent: Widget padre
            text: Texto del botón
            command: Función callback
            **kwargs:
                - bg/fg_color: Color de fondo
                - hover/hover_color: Color al pasar mouse
                - width/height: Dimensiones
                - font: Tupla (familia, tamaño, peso)
        
        Returns:
            CTkButton o tk.Button
        """
        if self.is_custom:
            ctk_kwargs = {
                'text': text,
                'command': command
            }
            
            if 'bg' in kwargs:
                ctk_kwargs['fg_color'] = kwargs['bg']
            if 'fg_color' in kwargs:
                ctk_kwargs['fg_color'] = kwargs['fg_color']
            if 'hover' in kwargs:
                ctk_kwargs['hover_color'] = kwargs['hover']
            if 'hover_color' in kwargs:
                ctk_kwargs['hover_color'] = kwargs['hover_color']
            if 'width' in kwargs:
                ctk_kwargs['width'] = kwargs['width']
            if 'height' in kwargs:
                ctk_kwargs['height'] = kwargs['height']
            if 'font' in kwargs:
                ctk_kwargs['font'] = kwargs['font']
            
            return self.UI.CTkButton(parent, **ctk_kwargs)
        else:
            tk_kwargs = {
                'text': text,
                'command': command,
                'fg': 'white',
                'relief': 'flat'
            }
            
            if 'bg' in kwargs:
                tk_kwargs['bg'] = kwargs['bg']
            if 'fg_color' in kwargs:
                tk_kwargs['bg'] = kwargs['fg_color']
            if 'hover' in kwargs:
                tk_kwargs['activebackground'] = kwargs['hover']
            if 'hover_color' in kwargs:
                tk_kwargs['activebackground'] = kwargs['hover_color']
            if 'width' in kwargs:
                # tkinter usa caracteres, CustomTkinter usa pixeles
                # Conversión aproximada: pixels / 8
                tk_kwargs['width'] = max(1, kwargs['width'] // 8)
            if 'font' in kwargs:
                tk_kwargs['font'] = kwargs['font']
            
            return tk.Button(parent, **tk_kwargs)
    
    def label(self, parent, text, **kwargs):
        """
        Crea un label abstrayendo CustomTkinter/Tkinter
        
        Args:
            parent: Widget padre
            text: Texto del label
            **kwargs:
                - bg/fg_color: Color de fondo
                - fg/text_color: Color del texto
                - font: Tupla (familia, tamaño, peso)
        
        Returns:
            CTkLabel o tk.Label
        """
        if self.is_custom:
            ctk_kwargs = {
                'text': text
            }
            
            if 'fg' in kwargs:
                ctk_kwargs['text_color'] = kwargs['fg']
            if 'text_color' in kwargs:
                ctk_kwargs['text_color'] = kwargs['text_color']
            if 'font' in kwargs:
                ctk_kwargs['font'] = kwargs['font']
            
            return self.UI.CTkLabel(parent, **ctk_kwargs)
        else:
            tk_kwargs = {
                'text': text
            }
            
            if 'bg' in kwargs:
                tk_kwargs['bg'] = kwargs['bg']
            if 'fg_color' in kwargs:
                tk_kwargs['bg'] = kwargs['fg_color']
            if 'fg' in kwargs:
                tk_kwargs['fg'] = kwargs['fg']
            if 'text_color' in kwargs:
                tk_kwargs['fg'] = kwargs['text_color']
            if 'font' in kwargs:
                tk_kwargs['font'] = kwargs['font']
            
            return tk.Label(parent, **tk_kwargs)
    
    def toplevel(self, parent=None, **kwargs):
        """
        Crea una ventana toplevel abstrayendo CustomTkinter/Tkinter
        
        Args:
            parent: Ventana padre (opcional)
            **kwargs:
                - bg/fg_color: Color de fondo
        
        Returns:
            CTkToplevel o tk.Toplevel
        """
        if self.is_custom:
            if parent:
                win = self.UI.CTkToplevel(parent)
            else:
                win = self.UI.CTkToplevel()
            
            if 'bg' in kwargs:
                win.configure(fg_color=kwargs['bg'])
            if 'fg_color' in kwargs:
                win.configure(fg_color=kwargs['fg_color'])
            
            return win
        else:
            if parent:
                win = tk.Toplevel(parent)
            else:
                win = tk.Toplevel()
            
            if 'bg' in kwargs:
                win.configure(bg=kwargs['bg'])
            if 'fg_color' in kwargs:
                win.configure(bg=kwargs['fg_color'])
            
            return win
    
    def set_widget_color(self, widget, **kwargs):
        """
        Cambia el color de un widget existente
        
        Args:
            widget: Widget a modificar
            **kwargs:
                - bg/fg_color: Color de fondo
                - hover/hover_color: Color hover (solo CustomTkinter)
        """
        if self.is_custom:
            if 'bg' in kwargs:
                widget.configure(fg_color=kwargs['bg'])
            if 'fg_color' in kwargs:
                widget.configure(fg_color=kwargs['fg_color'])
            if 'hover' in kwargs:
                widget.configure(hover_color=kwargs['hover'])
            if 'hover_color' in kwargs:
                widget.configure(hover_color=kwargs['hover_color'])
        else:
            if 'bg' in kwargs:
                widget.configure(bg=kwargs['bg'])
            if 'fg_color' in kwargs:
                widget.configure(bg=kwargs['fg_color'])
            if 'hover' in kwargs:
                widget.configure(activebackground=kwargs['hover'])
            if 'hover_color' in kwargs:
                widget.configure(activebackground=kwargs['hover_color'])

    def entry(self, parent, **kwargs):
        """
        Crea un entry abstrayendo CustomTkinter/Tkinter
        
        Args:
            parent: Widget padre
            **kwargs:
                - bg/fg_color: Color de fondo"""
        if self.is_custom:
            ctk_kwargs = {}
            if 'bg' in kwargs:
                ctk_kwargs['fg_color'] = kwargs['bg']
            if 'fg_color' in kwargs:
                ctk_kwargs['fg_color'] = kwargs['fg_color']
            if 'width' in kwargs:
                ctk_kwargs['width'] = kwargs['width']
            if 'font' in kwargs:
                ctk_kwargs['font'] = kwargs['font']
            if 'textvariable' in kwargs:
                ctk_kwargs['textvariable'] = kwargs['textvariable']
            
            return self.UI.CTkEntry(parent, **ctk_kwargs)
        else:
            tk_kwargs = {}
            if 'bg' in kwargs:
                tk_kwargs['bg'] = kwargs['bg']
            if 'fg_color' in kwargs:
                tk_kwargs['bg'] = kwargs['fg_color']
            if 'width' in kwargs:
                # tkinter usa caracteres, CustomTkinter usa pixeles
                # Conversión aproximada: pixels / 8
                tk_kwargs['width'] = max(1, kwargs['width'] // 8)
            if 'font' in kwargs:
                tk_kwargs['font'] = kwargs['font']
            if 'textvariable' in kwargs:
                tk_kwargs['textvariable'] = kwargs['textvariable']
            
            return tk.Entry(parent, **tk_kwargs)
