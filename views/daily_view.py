import customtkinter as ctk
import tkinter as tk
import tksheet
from controllers.daily_controller import DailyController
from models.daily_model import obtain_site_name

def render_daily_view(data, username, session_id, cur, top):
# load_daily():
    """Carga datos diarios desde el último START SHIFT (MODO DAILY)"""

    try:
        controller = DailyController(username)
        eventos = controller.load_daily(session_id)
        sheet = top.daily_sheet  # Asumiendo que 'top' es la ventana principal y tiene el sheet diario
        columns = ["FechaHora", "Nombre_Sitio", "Nombre_Actividad", "Cantidad", "Camera", "Descripcion"]
        sheet.headers(columns)
        display_rows = []
        row_ids = set()

        for evento in eventos:
            (id_evento, fecha_hora, id_sitio, nombre_actividad, cantidad, camera, descripcion) = evento
            row_ids.add(id_evento)
            sit_row = controller.obtain_site_name(cur, id_sitio)
        # Resolver Nombre_Sitio desde ID_Sitio
        try:

            # ⭐ Formato consistente: "Nombre (ID)" igual que en load_specials
            nombre_sitio = f"{sit_row[0]} ({id_sitio})" if sit_row else f"ID: {id_sitio}"
        except Exception:
            nombre_sitio = f"ID: {id_sitio}"

        # Formatear fecha/hora
        fecha_str = fecha_hora.strftime("%Y-%m-%d %H:%M:%S") if fecha_hora else ""


        # Fila para mostrar
        display_rows.append([
            fecha_str,
            nombre_sitio,
            nombre_actividad or "",
            str(cantidad) if cantidad is not None else "0",
            camera or "",
            descripcion or ""
        ])

    if not display_rows:
        display_rows = [["No hay eventos en este turno"] + [""] * (len(columns)-1)]

        row_ids.clear()

    sheet.set_sheet_data(display_rows)
    
    # ⭐ LIMPIAR COLORES (solo Specials tiene colores)
    sheet.dehighlight_all()
    
    apply_sheet_widths()

    print(f"[DEBUG] Loaded {len(row_ids)} events for {username}")

except Exception as e:
    messagebox.showerror("Error", f"No se pudo cargar eventos:\n{e}", parent=top)
            traceback.print_exc()