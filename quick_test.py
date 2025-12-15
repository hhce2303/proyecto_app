"""
Quick test - Verifica que los dashboards funcionan correctamente
"""
import tkinter as tk
from views.supervisor_dashboard import SupervisorDashboard

print("=" * 60)
print("QUICK TEST - Supervisor Dashboard")
print("=" * 60)
print()
print("✅ Importación exitosa")
print("✅ Creando dashboard...")

root = tk.Tk()
root.withdraw()

dashboard = SupervisorDashboard(
    username="test_user",
    role="Supervisor",
    station="ST-01",
    root=root
)

print("✅ Dashboard creado exitosamente")
print(f"   - Clase: {dashboard.__class__.__name__}")
print(f"   - Usuario: {dashboard.username}")
print(f"   - Rol: {dashboard.role}")
print(f"   - Window: {dashboard.window is not None}")
print(f"   - Header: {dashboard.header_frame is not None}")
print(f"   - Tabs: {dashboard.tabs_frame is not None}")
print(f"   - Content: {dashboard.content_area is not None}")
print()
print("📊 Estructura Dashboard verificada:")
print(f"   - Tabs disponibles: {list(dashboard.tab_frames.keys())}")
print(f"   - Tab actual: {dashboard.current_tab}")
print()
print("🎯 Presiona Ctrl+C o cierra la ventana para terminar")
print("=" * 60)

root.mainloop()
