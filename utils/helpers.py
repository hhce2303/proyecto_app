"""
🔧 HELPERS

Funciones auxiliares generales.

TODO: Migrar funciones auxiliares dispersas en el código
"""


class Helpers:
    """Funciones auxiliares"""
    
    @staticmethod
    def singleton_check(window_name: str):
        """
        Verifica si ya existe una ventana con ese nombre (singleton)
        
        TODO: Migrar _focus_singleton desde backend_super.py
        """
        pass
    
    @staticmethod
    def center_window(window, width: int, height: int):
        """Centra una ventana en la pantalla"""
        screen_width = window.winfo_screenwidth()
        screen_height = window.winfo_screenheight()
        x = (screen_width - width) // 2
        y = (screen_height - height) // 2
        window.geometry(f"{width}x{height}+{x}+{y}")
    
    @staticmethod
    def truncate_string(text: str, max_length: int) -> str:
        """Trunca un string si excede la longitud máxima"""
        return text[:max_length] + "..." if len(text) > max_length else text
