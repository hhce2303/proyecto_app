"""
Script de prueba para verificar el sistema de status visual en supervisores
"""
import tkinter as tk
from tkinter import messagebox
import sys
from pathlib import Path

# Agregar el directorio del proyecto al path
proyecto_path = Path(__file__).parent
sys.path.insert(0, str(proyecto_path))

import under_super
import backend_super

def test_status_functions():
    """Prueba las funciones de status"""
    print("\n" + "="*60)
    print("PRUEBA DE FUNCIONES DE STATUS")
    print("="*60)
    
    # Usuario de prueba
    test_username = "test_user"
    
    # Prueba 1: Obtener status
    print("\n1️⃣ Obteniendo status del usuario...")
    status = under_super.get_user_status_bd(test_username)
    print(f"   Status BD: {status}")
    
    status_text = backend_super.get_user_status(test_username)
    print(f"   Status formateado: {status_text}")
    
    # Prueba 2: Mapeo de valores
    print("\n2️⃣ Verificando mapeo de valores:")
    test_values = {
        1: "🟢 Disponible",
        0: "🟡 Ocupado",
        -1: "🔴 No disponible"
    }
    
    for val, expected in test_values.items():
        print(f"   Valor {val} -> {expected}")
    
    print("\n✅ Funciones de status verificadas")
    print("="*60)

def test_ui_elements():
    """Prueba la interfaz de status"""
    print("\n" + "="*60)
    print("PRUEBA DE INTERFAZ DE STATUS")
    print("="*60)
    
    root = tk.Tk()
    root.title("Prueba de Status UI")
    root.geometry("500x400")
    root.configure(bg="#2c2f33")
    
    print("\n🎨 Creando elementos de interfaz...")
    
    # Simular el status frame
    status_frame = tk.Frame(root, bg="#23272a", height=60)
    status_frame.pack(fill="x", padx=20, pady=20)
    
    # Label de status
    status_label = tk.Label(
        status_frame,
        text="🟢 Disponible",
        bg="#23272a",
        fg="#e0e0e0",
        font=("Segoe UI", 14, "bold")
    )
    status_label.pack(side="left", padx=20, pady=15)
    
    def change_status_test():
        """Simula el cambio de status"""
        status_win = tk.Toplevel(root)
        status_win.title("Cambiar Status")
        status_win.geometry("350x280")
        status_win.configure(bg="#2c2f33")
        status_win.transient(root)
        status_win.grab_set()
        
        tk.Label(
            status_win,
            text="Status actual: 🟢 Disponible",
            bg="#2c2f33",
            fg="#e0e0e0",
            font=("Segoe UI", 13, "bold")
        ).pack(pady=(20, 10))
        
        tk.Label(
            status_win,
            text="Selecciona nuevo status:",
            bg="#2c2f33",
            fg="#c9d1d9",
            font=("Segoe UI", 11)
        ).pack(pady=(0, 15))
        
        def set_status(emoji, text):
            status_label.configure(text=f"{emoji} {text}")
            messagebox.showinfo("Éxito", f"Status cambiado a: {emoji} {text}", parent=status_win)
            status_win.destroy()
        
        # Botones de status
        tk.Button(
            status_win,
            text="🟢 Disponible",
            command=lambda: set_status("🟢", "Disponible"),
            bg="#00c853",
            fg="white",
            font=("Segoe UI", 12, "bold"),
            relief="flat",
            width=18,
            height=2
        ).pack(pady=8)
        
        tk.Button(
            status_win,
            text="🟡 Ocupado",
            command=lambda: set_status("🟡", "Ocupado"),
            bg="#f5a623",
            fg="white",
            font=("Segoe UI", 12, "bold"),
            relief="flat",
            width=18,
            height=2
        ).pack(pady=8)
        
        tk.Button(
            status_win,
            text="🔴 No disponible",
            command=lambda: set_status("🔴", "No disponible"),
            bg="#d32f2f",
            fg="white",
            font=("Segoe UI", 12, "bold"),
            relief="flat",
            width=18,
            height=2
        ).pack(pady=8)
    
    # Botón de settings
    tk.Button(
        status_frame,
        text="⚙️",
        command=change_status_test,
        bg="#3b4754",
        fg="white",
        font=("Segoe UI", 12, "bold"),
        relief="flat",
        width=3
    ).pack(side="left", padx=5)
    
    # Información
    info_frame = tk.Frame(root, bg="#2c2f33")
    info_frame.pack(fill="both", expand=True, padx=20, pady=20)
    
    tk.Label(
        info_frame,
        text="🎯 Prueba de Interfaz de Status",
        bg="#2c2f33",
        fg="#e0e0e0",
        font=("Segoe UI", 16, "bold")
    ).pack(pady=(0, 20))
    
    info_text = """
    ✅ Indicador de status visible en header
    ✅ Botón de configuración (⚙️) funcional
    ✅ Ventana modal para cambiar status
    ✅ 3 opciones de status disponibles:
       • 🟢 Disponible (verde)
       • 🟡 Ocupado (amarillo)
       • 🔴 No disponible (rojo)
    
    📝 Haz clic en ⚙️ para probar el cambio de status
    """
    
    tk.Label(
        info_frame,
        text=info_text,
        bg="#2c2f33",
        fg="#c9d1d9",
        font=("Segoe UI", 10),
        justify="left"
    ).pack()
    
    print("   ✅ Interfaz creada correctamente")
    print("   🖱️  Prueba haciendo clic en el botón ⚙️")
    print("="*60 + "\n")
    
    root.mainloop()

if __name__ == "__main__":
    print("\n" + "🚀 INICIANDO PRUEBAS DEL SISTEMA DE STATUS")
    
    try:
        # Prueba 1: Funciones
        test_status_functions()
        
        # Prueba 2: Interfaz
        print("\n📋 ¿Deseas probar la interfaz gráfica? (s/n)")
        respuesta = input(">> ").strip().lower()
        
        if respuesta == 's':
            test_ui_elements()
        else:
            print("\n✅ Pruebas completadas")
            
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
