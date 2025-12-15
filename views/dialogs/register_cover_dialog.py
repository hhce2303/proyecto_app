"""
RegisterCoverDialog - Diálogo para registrar un cover realizado.
Captura motivo y operador que cubre para el proceso de cambio de sesión.

Responsabilidades:
- Mostrar formulario con motivo (combobox) y operador que cubre (FilteredCombobox)
- Validar selecciones
- Retornar datos o None si cancela
"""
import tkinter as tk
from tkinter import messagebox
from under_super import FilteredCombobox


class RegisterCoverDialog:
    """
    Diálogo modal para registrar cover realizado.
    Reutilizable, sin lógica de negocio.
    """
    
    # Motivos predefinidos
    MOTIVOS = ["Break", "Cover Baño", "Cover Training", "Otro"]
    
    def __init__(self, parent, ui_factory, UI=None):
        """
        Inicializa diálogo de registro de cover
        
        Args:
            parent: Ventana padre
            ui_factory: Factory para crear widgets
            UI: Módulo CustomTkinter (opcional)
        """
        self.parent = parent
        self.ui_factory = ui_factory
        self.UI = UI
        
        # Resultado
        self.result = None
        
        # Componentes
        self.dialog = None
        self.motivo_combo = None
        self.operador_combo = None
    
    def show(self, operadores_list):
        """
        Muestra el diálogo y retorna el resultado.
        
        Args:
            operadores_list: Lista de nombres de operadores disponibles
        
        Returns:
            dict or None: {'motivo': str, 'covered_by': str} si acepta, None si cancela
        """
        self._create_dialog(operadores_list)
        
        # Esperar hasta que se cierre el diálogo
        self.dialog.wait_window()
        
        return self.result
    
    def _create_dialog(self, operadores_list):
        """Crea la ventana del diálogo"""
        # Ventana modal
        if self.UI:
            self.dialog = self.UI.CTkToplevel(self.parent)
        else:
            self.dialog = tk.Toplevel(self.parent)
        
        self.dialog.title("Registrar Cover")
        self.dialog.geometry("500x320")
        self.dialog.resizable(False, False)
        self.dialog.transient(self.parent)
        self.dialog.grab_set()
        
        # Configurar color de fondo
        if self.UI:
            self.dialog.configure(fg_color="#1e1e1e")
        else:
            self.dialog.configure(bg="#1e1e1e")
        
        # Centrar en pantalla
        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() // 2) - (500 // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (320 // 2)
        self.dialog.geometry(f"500x320+{x}+{y}")
        
        # Contenido
        self._create_content(operadores_list)
    
    def _create_content(self, operadores_list):
        """Crea el contenido del diálogo"""
        # Frame principal
        main_frame = self.ui_factory.frame(self.dialog, fg_color="#1e1e1e")
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Título
        self.ui_factory.label(
            main_frame,
            text="📋 Registrar Cover Realizado",
            font=("Segoe UI", 18, "bold"),
            fg="#00bfae"
        ).pack(pady=(0, 5))
        
        # Descripción
        self.ui_factory.label(
            main_frame,
            text="Ingresa los datos del cover para cambiar de sesión:",
            font=("Segoe UI", 10),
            fg="#cccccc"
        ).pack(pady=(0, 20))
        
        # Campo Motivo
        motivo_frame = self.ui_factory.frame(main_frame, fg_color="transparent")
        motivo_frame.pack(fill="x", pady=(0, 15))
        
        self.ui_factory.label(
            motivo_frame,
            text="Motivo del Cover:",
            font=("Segoe UI", 11),
            fg="#ffffff"
        ).pack(anchor="w", pady=(0, 5))
        
        # Combobox para motivo
        if self.UI:
            self.motivo_combo = self.UI.CTkComboBox(
                motivo_frame,
                values=self.MOTIVOS,
                font=("Segoe UI", 12),
                height=35,
                state="readonly"
            )
            self.motivo_combo.set(self.MOTIVOS[0])  # Default: Break
        else:
            from tkinter import ttk
            self.motivo_combo = ttk.Combobox(
                motivo_frame,
                values=self.MOTIVOS,
                font=("Segoe UI", 11),
                state="readonly",
                width=40
            )
            self.motivo_combo.current(0)  # Default: Break
        
        self.motivo_combo.pack(fill="x")
        
        # Campo Operador que cubre
        operador_frame = self.ui_factory.frame(main_frame, fg_color="transparent")
        operador_frame.pack(fill="x", pady=(0, 20))
        
        self.ui_factory.label(
            operador_frame,
            text="Operador que cubre:",
            font=("Segoe UI", 11),
            fg="#ffffff"
        ).pack(anchor="w", pady=(0, 5))
        
        # FilteredCombobox para operador
        self.operador_combo = FilteredCombobox(
            operador_frame,
            values=operadores_list,
            width=45
        )
        self.operador_combo.pack(fill="x")
        self.operador_combo.focus_set()
        
        # Frame para botones
        buttons_frame = self.ui_factory.frame(main_frame, fg_color="transparent")
        buttons_frame.pack(fill="x", pady=(10, 0))
        
        # Botón Cancelar
        self.ui_factory.button(
            buttons_frame,
            text="❌ Cancelar",
            command=self._on_cancel,
            width=140,
            fg_color="#d32f2f",
            hover_color="#b71c1c"
        ).pack(side="right", padx=(5, 0))
        
        # Botón Registrar
        self.ui_factory.button(
            buttons_frame,
            text="✅ Registrar Cover",
            command=self._on_accept,
            width=160,
            fg_color="#2e7d32",
            hover_color="#1b5e20"
        ).pack(side="right", padx=(0, 5))
    
    def _on_accept(self):
        """Valida y acepta el registro"""
        motivo = self.motivo_combo.get().strip()
        covered_by = self.operador_combo.get().strip()
        
        if not motivo:
            messagebox.showwarning(
                "Campo requerido",
                "Por favor selecciona un motivo para el cover.",
                parent=self.dialog
            )
            return
        
        if not covered_by:
            messagebox.showwarning(
                "Campo requerido",
                "Por favor selecciona el operador que cubre.",
                parent=self.dialog
            )
            self.operador_combo.focus_set()
            return
        
        # Guardar resultado
        self.result = {
            'motivo': motivo,
            'covered_by': covered_by
        }
        
        # Cerrar diálogo
        self.dialog.destroy()
    
    def _on_cancel(self):
        """Cancela el registro"""
        self.result = None
        self.dialog.destroy()
