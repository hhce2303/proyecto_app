"""
🔐 LOGIN VIEW

Vista de inicio de sesión de la aplicación.

Componentes:
- Campo Usuario (FilteredCombobox con lista de usuarios)
- Campo Contraseña (Entry con show="*")
- Campo Estación (Entry numérico)
- Botón Iniciar Sesión

TODO: Migrar desde login.py
"""

import tkinter as tk
from tkinter import messagebox


class LoginView:
    """Vista de inicio de sesión"""
    
    def __init__(self, root, controller=None):
        """
        Inicializa la vista de login
        
        Args:
            root: Ventana raíz de Tkinter
            controller: Controlador de autenticación (AuthController)
        """
        self.root = root
        self.controller = controller
        self.window = None
        
    def show(self):
        """Muestra la ventana de login"""
        # TODO: Implementar interfaz de login
        pass
    
    def get_credentials(self):
        """
        Obtiene las credenciales ingresadas
        
        Returns:
            Tuple (username, password, station)
        """
        # TODO: Implementar
        pass
    
    def show_error(self, message: str):
        """Muestra un mensaje de error"""
        messagebox.showerror("Error", message, parent=self.window)
    
    def show_success(self, message: str):
        """Muestra un mensaje de éxito"""
        messagebox.showinfo("Éxito", message, parent=self.window)
    
    def close(self):
        """Cierra la ventana de login"""
        if self.window:
            self.window.destroy()
