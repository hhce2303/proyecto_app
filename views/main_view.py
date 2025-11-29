"""
🏠 MAIN VIEW

Vista principal para usuarios regulares.

Componentes:
- Menú de opciones
- Botones de acceso rápido
- Panel de eventos
- etc.

TODO: Migrar desde main.py
"""

import tkinter as tk


class MainView:
    """Vista principal para usuarios regulares"""
    
    def __init__(self, root, controller=None, username=None):
        """
        Inicializa la vista principal
        
        Args:
            root: Ventana raíz de Tkinter
            controller: Controlador de eventos
            username: Nombre del usuario logueado
        """
        self.root = root
        self.controller = controller
        self.username = username
        self.window = None
        
    def show(self):
        """Muestra la ventana principal"""
        # TODO: Implementar interfaz principal
        pass
    
    def close(self):
        """Cierra la ventana principal"""
        if self.window:
            self.window.destroy()
