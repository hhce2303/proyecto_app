import time
import pythoncom
import win32com.client as win32
from datetime import datetime, timedelta
import os
import traceback
import shutil

# -------------------------------
# Configuración
# -------------------------------
USERPANEL_PATH = r"C:\Users\hcruz.SIG\OneDrive - SIG Systems, Inc\UserPanel.xlsx"
SERVICE_PATH   = r"S:\Central Station SLC-COLOMBIA\3. DST Monitoring Split Colombia\forbidden acces\Health Check 4.1.xlsm"
SERVICE_REFRESH = 180  # refresco completo cada 3 min
COLOR_ROJO = 0x0000FF
START_ROW = 10
TICKET_URL_PREFIX = "https://sigdomain01:8080/WorkOrder.do?woMode=viewWO&woID="
TICKET_URL_SUFFIX = "#resolution"
LOG_FILE = r"C:\Users\hcruz.SIG\OneDrive - SIG Systems, Inc\excel_sync_log.txt"

# -------------------------------
# Limpiar gen_py si está corrupto
# -------------------------------
gen_py = os.path.join(os.environ.get("LOCALAPPDATA", ""), "Temp", "gen_py")
if os.path.exists(gen_py):
    try:
        shutil.rmtree(gen_py)
        print("🗑️ gen_py cache cleared")
    except Exception as e:
        print(f"⚠️ Could not clear gen_py: {e}")

# -------------------------------
# Logging
# -------------------------------
def log(msg):
    timestamp = datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
    line = f"{timestamp} {msg}"
    print(line)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")

# -------------------------------
# Normalizar ticket IDs
# -------------------------------
def normalize_ticket_id(ticket):
    if ticket is None:
        return []
    s = str(ticket).strip()
    if s.endswith(".0"):
        s = s[:-2]
    s = s.replace("\n", ";").replace(",", ";")
    return [p.strip() for p in s.split(";") if p.strip()]


from datetime import datetime, timedelta

from datetime import datetime, timedelta

def excel_date_to_datetime(value):
    if value is None:
        return ""
    
    # Formato de salida fijo
    out_fmt = "%Y-%m-%d %H:%M:%S"
    
    # Si es número (como lo guarda Excel)
    if isinstance(value, (int, float)):
        dt = datetime(1899, 12, 30) + timedelta(days=float(value))
        return dt.strftime(out_fmt)
    
    # Si es string → intentar varios formatos de entrada
    if isinstance(value, str):
        for fmt in (
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d %H:%M",
        ):
            try:
                dt = datetime.strptime(value.strip(), fmt)
                return dt.strftime(out_fmt)
            except Exception:
                continue
    
    # Si ya es datetime (último caso)
    if isinstance(value, datetime):
        return value.strftime(out_fmt)
    
    # Si no se pudo convertir → devolver texto limpio
    return str(value).strip()


def format_date_value(value):
    if not value:
        return ""
    
    out_fmt = "%Y-%m-%d %H:%M:%S"
    
    def try_parse_date(val):
        for fmt in (
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d %H:%M",
            "%m/%d/%Y %H:%M:%S",
            "%m/%d/%Y %H:%M",
            
        ):
            try:
                d = datetime.strptime(val.strip(), fmt)
                return d.strftime(out_fmt)
            except Exception:
                continue
        return val.strip()
    
    # Manejar saltos de línea
    if isinstance(value, str) and "\n" in value:
        parts = value.splitlines()
        return "\n".join(try_parse_date(p) for p in parts)
    else:
        return try_parse_date(str(value))

# -------------------------------
# Banner en I1
# -------------------------------
def update_banner(ws_panel, text, color=0x00FF00, size=20):
    """Actualiza el banner en la celda I1 con estilo"""
    cell = ws_panel.Cells(1, 5)  # E1
    cell.Value = text
    cell.Font.Size = size
    cell.Font.Bold = True
    cell.Font.Color = color
    cell.HorizontalAlignment = -4108  # xlCenter
    cell.VerticalAlignment = -4108    # xlCenter

# -------------------------------
# Cargar ServiceDesk
# -------------------------------
def load_service(ws_base):
    base_dict = {}
    try:
        last_row_base = ws_base.Cells(ws_base.Rows.Count, 1).End(win32.constants.xlUp).Row
        if last_row_base < 2:
            return base_dict

        values = ws_base.Range(f"A2:F{last_row_base}").Value
        for row in values:
            ticket_id, _, _, status, _, raw_fecha = row
            fecha = excel_date_to_datetime(raw_fecha)
            if ticket_id:
                tid = str(ticket_id).strip()
                if tid.endswith(".0"):
                    tid = tid[:-2]
                base_dict[tid] = (status if status else "Not Found", fecha)
    except Exception:
        log("⚠️ Error en load_service:")
        log(traceback.format_exc())
    return base_dict

# -------------------------------
# Hipervínculos en K
# -------------------------------
def update_links(ws_panel, start_row=START_ROW):
    last_row_panel = ws_panel.Cells(ws_panel.Rows.Count, 9).End(win32.constants.xlUp).Row
    values_i = ws_panel.Range(f"I{start_row}:I{last_row_panel}").Value
    ws_panel.Range(f"K{start_row}:K{last_row_panel}").ClearContents()

    for idx, cell_value in enumerate(values_i, start=start_row):
        val = cell_value[0] if isinstance(cell_value, tuple) else cell_value
        if val:
            ids = normalize_ticket_id(val)
            if ids:
                tid = ids[0]
                url = f"{TICKET_URL_PREFIX}{tid}{TICKET_URL_SUFFIX}"
                ws_panel.Hyperlinks.Add(
                    Anchor=ws_panel.Cells(idx, 11),
                    Address=url,
                    TextToDisplay=f"Open {tid}"
                )
                ws_panel.Cells(idx, 11).Borders.Weight = 2
        else:
            ws_panel.Cells(idx, 11).Value = ""

# -------------------------------
# Actualizar panel
# -------------------------------
def update_panel(ws_panel, base_dict, start_row=START_ROW, fecha_cache={}):
    last_row_panel = ws_panel.Cells(ws_panel.Rows.Count, 9).End(win32.constants.xlUp).Row
    values_i = ws_panel.Range(f"I{start_row}:I{last_row_panel}").Value
    new_values_j, new_values_l = [], []

       # Limpiar y forzar la columna L a Texto
    
    ws_panel.Columns(12).NumberFormat = "@"   # Forzar formato Texto

    for val in values_i:
        v = val[0] if isinstance(val, tuple) else val
        if not v:
            new_values_j.append(("",))
            new_values_l.append(("",))
        else:
            ids = normalize_ticket_id(v)
            statuses, fechas = [], []
            for tid in ids:
                if tid in base_dict:
                    status, fecha = base_dict[tid]
                    statuses.append(status)
                    
                    # Guardar SIEMPRE la fecha ya formateada
                    if tid not in fecha_cache:
                        fecha_cache[tid] = format_date_value(fecha)
                    
                    fechas.append(fecha_cache[tid])
                else:
                    statuses.append("Not Found")
                    fechas.append("")
            new_values_j.append(("\n".join(statuses),))
            new_values_l.append(("\n".join(fechas),))
    
    ws_panel.Columns(12).NumberFormat = "@"

    ws_panel.Range(f"J{start_row}:J{last_row_panel}").Value = new_values_j
    ws_panel.Range(f"L{start_row}:L{last_row_panel}").Value = new_values_l
    ws_panel.Range(f"J{start_row}:L{last_row_panel}").WrapText = True
    ws_panel.Columns(10).AutoFit()
    ws_panel.Columns(12).AutoFit()
    




    for idx, cell_value in enumerate(new_values_j, start=start_row):
        cell_j = ws_panel.Cells(idx, 10)
        cell_j.Interior.Color = COLOR_ROJO if "Not Found" in cell_value[0] else 0

    update_links(ws_panel, start_row)

# -------------------------------
# Inicializar Excel con reintentos
# -------------------------------
def open_excel():
    pythoncom.CoInitialize()
    excel = win32.gencache.EnsureDispatch("Excel.Application")
    excel.Visible = False
    wb_panel = excel.Workbooks.Open(USERPANEL_PATH)
    ws_panel = wb_panel.Worksheets("UserPanel")
    wb_service = excel.Workbooks.Open(SERVICE_PATH, ReadOnly=True)
    ws_base = wb_service.Worksheets("ServiceDesk")
    return excel, wb_panel, ws_panel, wb_service, ws_base

# -------------------------------
# Script principal con autocorrección
# -------------------------------
def main():
    fecha_cache, prev_snapshot = {}, {}
    while True:
        try:
            excel, wb_panel, ws_panel, wb_service, ws_base = open_excel()
            update_banner(ws_panel, "Script Running ✅", color=0x00CC00)  # verde
            base_dict = load_service(ws_base)
            update_panel(ws_panel, base_dict, fecha_cache=fecha_cache)
            wb_panel.Save()
            log("✅ Script iniciado correctamente.")
            last_full_refresh = datetime.now()

            while True:
                now = datetime.now()

                # refresco programado
                if (now - last_full_refresh).total_seconds() >= SERVICE_REFRESH:
                    base_dict = load_service(ws_base)
                    update_panel(ws_panel, base_dict, fecha_cache=fecha_cache)
                    wb_panel.Save()
                    last_full_refresh = now
                    update_banner(ws_panel, "Refreshing..🔄", color=0xFF8000)  # azul neutro
                    log(f"🔄 Refresco completo {now.strftime('%H:%M:%S')}")

                # detectar cambios
                last_row_panel = ws_panel.Cells(ws_panel.Rows.Count, 9).End(win32.constants.xlUp).Row
                values_i = ws_panel.Range(f"I{START_ROW}:I{last_row_panel}").Value
                changed = False
                for idx, val in enumerate(values_i, start=START_ROW):
                    actual = val[0] if isinstance(val, tuple) else val
                    if prev_snapshot.get(idx) != actual:
                        changed = True
                        prev_snapshot[idx] = actual

                if changed:
                    update_panel(ws_panel, base_dict, fecha_cache=fecha_cache)
                    wb_panel.Save()
                    log(f"✅ Cambio detectado {now.strftime('%H:%M:%S')}")
                    update_banner(ws_panel, "Script Running ✅", color=0xFF8000)  # azul neutro

                time.sleep(5)

        except Exception as e:
            log(f"❌ Error crítico: {e}")
            update_banner(ws_panel, "Restarting...", color=0xFF8000)  # azul neutro
            log(traceback.format_exc())
        finally:
            try:
                
                wb_panel.Save()
            except:
                pass
            try: wb_panel.Close(SaveChanges=True)
            except: pass
            try: wb_service.Close(SaveChanges=False)
            except: pass
            try: excel.Quit()
            except: pass
            pythoncom.CoUninitialize()
            log("⚠️ Excel cerrado, reintentando en 10s...")
            update_banner(ws_panel, "Restarting...", color=0xFF8000)  # azul neutro
            time.sleep(9)

if __name__ == "__main__":
    main()
