"""
RequestCoverDialog - Diálogo para solicitar un cover.
Captura motivo de la solicitud y valida antes de enviar.

Responsabilidades:
- Mostrar formulario simple con campo de motivo
- Validar que el motivo no esté vacío
- Retornar datos o None si cancela
"""
import tkinter as tk
from tkinter import messagebox


class RequestCoverDialog:
    """
    Diálogo modal para solicitar cover.
    Reutilizable, sin dependencias de controlador.
    """
    
    def __init__(self, parent, ui_factory, UI=None):
        """
        Inicializa diálogo de solicitud de cover
        
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
        
        # Crear ventana modal
        self.dialog = None
        self.motivo_entry = None
    
    def show(self):
        """
        Muestra el diálogo y retorna el resultado.
        
        Returns:
            dict or None: {'motivo': str} si acepta, None si cancela
        """
        self._create_dialog()
        
        # Esperar hasta que se cierre el diálogo
        self.dialog.wait_window()
        
        return self.result
    
    def _create_dialog(self):
        """Crea la ventana del diálogo"""
        # Ventana modal
        if self.UI:
            self.dialog = self.UI.CTkToplevel(self.parent)
        else:
            self.dialog = tk.Toplevel(self.parent)
        
        self.dialog.title("Solicitar Cover")
        self.dialog.geometry("450x250")
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
        x = (self.dialog.winfo_screenwidth() // 2) - (450 // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (250 // 2)
        self.dialog.geometry(f"450x250+{x}+{y}")
        
        # Contenido
        self._create_content()
    
    def _create_content(self):
        """Crea el contenido del diálogo"""
        # Frame principal
        main_frame = self.ui_factory.frame(self.dialog, fg_color="#1e1e1e")
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Título
        self.ui_factory.label(
            main_frame,
            text="📋 Solicitar Cover",
            font=("Segoe UI", 18, "bold"),
            fg="#00bfae"
        ).pack(pady=(0, 10))
        
        # Descripción
        self.ui_factory.label(
            main_frame,
            text="Ingresa el motivo de tu solicitud de cover:",
            font=("Segoe UI", 11),
            fg="#cccccc"
        ).pack(pady=(0, 15))
        
        # Frame para campo de motivo
        input_frame = self.ui_factory.frame(main_frame, fg_color="transparent")
        input_frame.pack(fill="x", pady=(0, 20))
        
        # Label del campo
        self.ui_factory.label(
            input_frame,
            text="Motivo:",
            font=("Segoe UI", 11),
            fg="#ffffff"
        ).pack(anchor="w", pady=(0, 5))
        
        # Entry para motivo
        if self.UI:
            self.motivo_entry = self.UI.CTkEntry(
                input_frame,
                placeholder_text="Ejemplo: Break, Baño, Emergencia...",
                font=("Segoe UI", 12),
                height=40
            )
        else:
            self.motivo_entry = tk.Entry(
                input_frame,
                font=("Segoe UI", 12),
                bg="#2b2b2b",
                fg="#ffffff",
                insertbackground="#ffffff",
                relief="flat",
                bd=2
            )
        
        self.motivo_entry.pack(fill="x")
        self.motivo_entry.focus()
        
        # Bind Enter key
        self.motivo_entry.bind("<Return>", lambda e: self._on_accept())
        
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
        
        # Botón Solicitar
        self.ui_factory.button(
            buttons_frame,
            text="✅ Solicitar Cover",
            command=self._on_accept,
            width=160,
            fg_color="#2e7d32",
            hover_color="#1b5e20"
        ).pack(side="right", padx=(0, 5))
    
    def _on_accept(self):
        """Valida y acepta la solicitud"""
        motivo = self.motivo_entry.get().strip()
        
        if not motivo:
            messagebox.showwarning(
                "Campo requerido",
                "Por favor ingresa un motivo para el cover.",
                parent=self.dialog
            )
            self.motivo_entry.focus()
            return
        
        # Validación básica de longitud
        if len(motivo) < 3:
            messagebox.showwarning(
                "Motivo muy corto",
                "El motivo debe tener al menos 3 caracteres.",
                parent=self.dialog
            )
            self.motivo_entry.focus()
            return
        
        # Guardar resultado
        self.result = {
            'motivo': motivo
        }
        
        # Cerrar diálogo
        self.dialog.destroy()
    
    def _on_cancel(self):
        """Cancela la solicitud"""
        self.result = None
        self.dialog.destroy()
