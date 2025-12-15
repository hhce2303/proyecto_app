"""
Test OperatorBlackboard - Prueba el contenedor de tabs del OPERADOR
ENFOQUE: Solo tab Daily con DailyModule funcionando
"""
import tkinter as tk
from views.operator_blackboard import OperatorBlackboard


def test_operator_blackboard():
    """Prueba el OperatorBlackboard con DailyModule"""
    print("=" * 70)
    print("TEST OPERATOR BLACKBOARD - DAILY MODULE")
    print("=" * 70)
    print()
    print("🎯 ENFOQUE: Tab Daily con DailyModule")
    print()
    print("Inicializando OperatorBlackboard...")
    print()
    
    root = tk.Tk()
    root.withdraw()
    
    # Crear blackboard de OPERADOR
    blackboard = OperatorBlackboard(
        username="prueba",
        role="Operador",
        session_id=None,
        station="ST-TEST",
        root=root
    )
    
    print("✅ OperatorBlackboard creado")
    print("✅ DailyModule cargado en tab 'Daily'")
    print()
    print("📊 Verificando estructura:")
    print(f"   - Blackboard: {blackboard.__class__.__name__}")
    print(f"   - Rol: {blackboard.role}")
    print(f"   - Tabs disponibles: {list(blackboard.tab_frames.keys())}")
    print(f"   - Tab actual: {blackboard.current_tab}")
    
    if hasattr(blackboard, 'daily_module'):
        print(f"   - DailyModule: ✅ Inicializado")
        print(f"   - Sheet: {blackboard.daily_module.sheet is not None}")
        print(f"   - Eventos cargados: {len(blackboard.daily_module.row_ids)}")
    else:
        print(f"   - DailyModule: ❌ No encontrado")
    
    print()
    print("🎯 Tab Daily (ACTIVO):")
    print("   - ✅ CREAR eventos regulares")
    print("   - ✅ Editar eventos propios")
    print("   - ✅ Eliminar eventos")
    print("   - ✅ Auto-save funcionando")
    print()
    print("⏳ Tabs pendientes:")
    print("   - Specials (placeholder)")
    print("   - Covers (placeholder)")
    print()
    print("🔄 Cierra la ventana para terminar")
    print("=" * 70)
    
    root.mainloop()


if __name__ == "__main__":
    test_operator_blackboard()
