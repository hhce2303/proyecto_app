import os
import openpyxl
from datetime import datetime

# Ruta base de los operadores
BASE_PATH = r"\\192.168.7.12\Data SIG\Central Station SLC-COLOMBIA\1. Daily Logs - Operators"

# Ruta final del Excel de usuarios
USERS_FILE = r"\\192.168.7.12\Data SIG\Central Station SLC-COLOMBIA\1. Daily Logs - Operators\DataBase\Usuarios.xlsx"

def get_latest_year_month_path(base_path):
    """Encuentra la ruta del año y mes más recientes."""
    años = [d for d in os.listdir(base_path) if d.isdigit()]
    if not años:
        raise FileNotFoundError("No se encontraron carpetas de años en la ruta.")
    latest_year = max(años)
    year_path = os.path.join(base_path, latest_year)

    meses = [d for d in os.listdir(year_path) if os.path.isdir(os.path.join(year_path, d))]
    if not meses:
        raise FileNotFoundError(f"No se encontraron carpetas de meses en el año {latest_year}.")
    
    # Ordenamos por número inicial (ej: "09. September")
    meses_sorted = sorted(meses, key=lambda x: int(x.split(".")[0]))
    latest_month = meses_sorted[-1]
    month_path = os.path.join(year_path, latest_month)

    return month_path

def get_users_from_path(path):
    """Lista las carpetas de usuarios (operadores)."""
    users = [d for d in os.listdir(path) if os.path.isdir(os.path.join(path, d))]
    return sorted(users)

def create_users_excel(users, file_path):
    """Crea el Excel con la lista de usuarios."""
    # Crear carpeta si no existe
    os.makedirs(os.path.dirname(file_path), exist_ok=True)

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Usuarios"
    ws.append(["Usuario", "FechaCreacion"])  # encabezado

    for user in users:
        ws.append([user, datetime.now().strftime("%Y-%m-%d %H:%M:%S")])

    wb.save(file_path)
    return f"Archivo '{file_path}' creado con {len(users)} usuarios."

if __name__ == "__main__":
    try:
        latest_path = get_latest_year_month_path(BASE_PATH)
        print("Carpeta de operadores más reciente:", latest_path)

        usuarios = get_users_from_path(latest_path)
        print("Usuarios encontrados:", usuarios)

        mensaje = create_users_excel(usuarios, USERS_FILE)
        print(mensaje)
    except Exception as e:
        print("Error:", e)
