import os
import shutil
import subprocess
import sys
from pathlib import Path
import re

# Directorio del servidor donde están las versiones
SERVER_DIR = Path(r"\\LDBONILLA\Daily\App")

# Ruta local donde se guardará
LOCAL_DIR = Path.home() / "Documents" / "DailyApp"

def get_latest_exe():
    """Busca el .exe más reciente con patrón 'Daily Log SLC v*.exe'"""
    try:
        # Buscar todos los archivos que coincidan con el patrón
        pattern = re.compile(r"Daily Log SLC v(\d+\.\d+\.\d+)\.exe", re.IGNORECASE)
        versions = []
        
        for file in SERVER_DIR.glob("Daily Log SLC v*.exe"):
            match = pattern.match(file.name)
            if match:
                version_str = match.group(1)
                # Convertir "2.1.2" a tupla (2, 1, 2) para comparar
                version_tuple = tuple(map(int, version_str.split('.')))
                versions.append((version_tuple, file))
        
        if not versions:
            print(f"⚠️ No se encontraron archivos 'Daily Log SLC v*.exe' en {SERVER_DIR}")
            return None
        
        # Ordenar por versión y tomar la más reciente
        versions.sort(reverse=True)
        latest_version, latest_file = versions[0]
        print(f"✅ Versión más reciente encontrada: {latest_file.name}")
        return latest_file
        
    except Exception as e:
        print(f"❌ Error buscando versión más reciente: {e}")
        return None

def copy_with_verification(src, dst):
    """Copia un archivo con verificación de integridad"""
    try:
        # Copiar con buffer más grande para archivos en red
        with open(src, 'rb') as fsrc:
            with open(dst, 'wb') as fdst:
                shutil.copyfileobj(fsrc, fdst, length=1024*1024)  # Buffer de 1MB
        
        # Verificar que el tamaño sea correcto
        if src.stat().st_size == dst.stat().st_size:
            return True
        else:
            print(f"⚠️ Tamaños no coinciden: servidor={src.stat().st_size}, local={dst.stat().st_size}")
            return False
    except Exception as e:
        print(f"❌ Error copiando archivo: {e}")
        return False

def ensure_local_copy():
    """Copia o actualiza la versión más reciente del servidor"""
    # Crear carpeta si no existe
    LOCAL_DIR.mkdir(parents=True, exist_ok=True)

    # Obtener la versión más reciente del servidor
    server_exe = get_latest_exe()
    if not server_exe:
        # Buscar cualquier .exe local como fallback
        local_exes = list(LOCAL_DIR.glob("Daily Log SLC v*.exe"))
        if local_exes:
            print(f"⚠️ Usando versión local: {local_exes[0].name}")
            return local_exes[0]
        else:
            print("❌ No se encontró ninguna versión (ni en servidor ni local)")
            return None
    
    local_exe = LOCAL_DIR / server_exe.name

    # Si no existe localmente, copiar
    if not local_exe.exists():
        print(f"📥 Copiando {server_exe.name} por primera vez...")
        if copy_with_verification(server_exe, local_exe):
            print(f"✅ Copia completada exitosamente")
            return local_exe
        else:
            print(f"❌ Error en la copia, buscando alternativa local...")
            local_exes = list(LOCAL_DIR.glob("Daily Log SLC v*.exe"))
            return local_exes[0] if local_exes else None

    # Comparar tamaño para detectar cambios (más rápido que fecha en red)
    try:
        server_size = server_exe.stat().st_size
        local_size = local_exe.stat().st_size
        
        if server_size != local_size:
            print(f"🔄 Actualizando a {server_exe.name}...")
            # Eliminar versión antigua antes de copiar
            temp_backup = local_exe.with_suffix('.exe.bak')
            if temp_backup.exists():
                temp_backup.unlink()
            local_exe.rename(temp_backup)
            
            if copy_with_verification(server_exe, local_exe):
                print(f"✅ Actualización completada")
                temp_backup.unlink()  # Eliminar backup
            else:
                print(f"⚠️ Error actualizando, restaurando versión anterior")
                temp_backup.rename(local_exe)
    except Exception as e:
        print(f"⚠️ Error comparando versiones: {e}. Usando versión local.")
    
    return local_exe

def run_local_app(exe_path):
    """Ejecuta el .exe local"""
    if exe_path and exe_path.exists():
        print(f"🚀 Iniciando {exe_path.name}...")
        subprocess.Popen([str(exe_path)], shell=False)
    else:
        print("❌ No se pudo iniciar la aplicación")

if __name__ == "__main__":
    local_exe = ensure_local_copy()
    run_local_app(local_exe)