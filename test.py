"""
Test simple para OperatorBlackboard
"""
import tkinter as tk
from views.operator_blackboard import OperatorBlackboard


def test():
    """Test básico del OperatorBlackboard"""
    print("="*50)
    print("TEST OPERATOR BLACKBOARD")
    print("="*50)
    
    root = tk.Tk()
    root.withdraw()
    
    # Crear blackboard
    blackboard = OperatorBlackboard(
        username="prueba",
        role="Operador",
        session_id=None,
        station="1",
        root=root
    )
    
    print(f"✅ Blackboard creado: {blackboard.__class__.__name__}")
    print(f"✅ Tabs: {list(blackboard.tab_frames.keys())}")
    print(f"✅ Tab actual: {blackboard.current_tab}")
    
    if hasattr(blackboard, 'daily_module'):
        print(f"✅ DailyModule: OK")
        print(f"✅ Eventos: {len(blackboard.daily_module.row_ids)}")
    
    print("\n🔄 Cierra la ventana para terminar\n")
    
    root.mainloop()


if __name__ == "__main__":
    test()
