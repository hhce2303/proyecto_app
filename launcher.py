import os
import shutil
import subprocess
import sys
from pathlib import Path
import re
import hashlib
import json

# Directorio del servidor donde están las versiones
SERVER_DIR = Path(r"\\192.168.7.12\Data SIG\Central Station SLC-COLOMBIA\1. Daily Logs - Operators")

# Ruta local donde se guardará
LOCAL_DIR = Path.home() / "Documents" / "DailyApp"
CACHE_FILE = LOCAL_DIR / ".version_cache.json"

def get_file_hash_quick(file_path, chunk_size=8192):
    """Calcula hash rápido solo del inicio y final del archivo"""
    try:
        size = file_path.stat().st_size
        hasher = hashlib.md5()
        
        with open(file_path, 'rb') as f:
            # Leer primeros 1MB
            hasher.update(f.read(min(1024*1024, size)))
            
            # Si el archivo es grande, leer también el final
            if size > 2*1024*1024:
                f.seek(-1024*1024, 2)  # Último 1MB
                hasher.update(f.read())
        
        return hasher.hexdigest()
    except:
        return None

def load_cache():
    """Carga cache de versiones conocidas"""
    try:
        if CACHE_FILE.exists():
            with open(CACHE_FILE, 'r') as f:
                return json.load(f)
    except:
        pass
    return {}

def save_cache(cache_data):
    """Guarda cache de versiones"""
    try:
        LOCAL_DIR.mkdir(parents=True, exist_ok=True)
        with open(CACHE_FILE, 'w') as f:
            json.dump(cache_data, f)
    except:
        pass

def get_latest_exe_fast():
    """Busca el .exe más reciente SIN acceder al contenido del archivo"""
    try:
        print("🔍 Buscando versión más reciente...")
        pattern = re.compile(r"Daily Log SLC v(\d+\.\d+\.\d+)\.exe", re.IGNORECASE)
        versions = []
        
        # Solo obtener nombres de archivo (rápido)
        for file in SERVER_DIR.glob("Daily Log SLC v*.exe"):
            match = pattern.match(file.name)
            if match:
                version_str = match.group(1)
                version_tuple = tuple(map(int, version_str.split('.')))
                versions.append((version_tuple, file))
        
        if not versions:
            print(f"⚠️ No se encontraron archivos 'Daily Log SLC v*.exe' en servidor")
            return None
        
        # Tomar la versión más alta
        versions.sort(reverse=True)
        latest_version, latest_file = versions[0]
        print(f"✅ Versión encontrada: {latest_file.name}")
        return latest_file
        
    except Exception as e:
        print(f"❌ Error buscando versión: {e}")
        return None

def needs_update(server_exe, local_exe):
    """Determina si necesita actualizar comparando SOLO tamaño y nombre"""
    try:
        # Si no existe local, necesita copia
        if not local_exe.exists():
            print("📥 Primera instalación necesaria")
            return True
        
        # Si los nombres son diferentes, necesita actualización
        if server_exe.name != local_exe.name:
            print(f"🔄 Nueva versión disponible: {server_exe.name}")
            return True
        
        # Comparar solo tamaño (MUY rápido, sin leer contenido)
        server_size = server_exe.stat().st_size
        local_size = local_exe.stat().st_size
        
        if server_size != local_size:
            print(f"🔄 Tamaño diferente, actualizando...")
            return True
        
        print(f"✅ Versión local actualizada: {local_exe.name}")
        return False
        
    except Exception as e:
        print(f"⚠️ Error verificando: {e}")
        return True  # Por seguridad, actualizar si hay error

def copy_fast(src, dst, chunk_size=8*1024*1024):
    """Copia con chunks grandes (8MB) para redes lentas"""
    try:
        print(f"📦 Copiando archivo (esto puede tardar)...")
        
        # Crear backup si existe versión anterior
        if dst.exists():
            backup = dst.with_suffix('.exe.old')
            if backup.exists():
                backup.unlink()
            dst.rename(backup)
        
        # Copiar con chunks grandes
        total_size = src.stat().st_size
        copied = 0
        
        with open(src, 'rb') as fsrc:
            with open(dst, 'wb') as fdst:
                while True:
                    chunk = fsrc.read(chunk_size)
                    if not chunk:
                        break
                    fdst.write(chunk)
                    copied += len(chunk)
                    
                    # Mostrar progreso cada 10MB
                    if copied % (10*1024*1024) < chunk_size:
                        progress = (copied / total_size) * 100
                        print(f"   {progress:.0f}% completado ({copied/(1024*1024):.1f}MB / {total_size/(1024*1024):.1f}MB)")
        
        # Verificar tamaño
        if dst.stat().st_size == total_size:
            print(f"✅ Copia exitosa")
            # Eliminar backup
            backup = dst.with_suffix('.exe.old')
            if backup.exists():
                backup.unlink()
            return True
        else:
            print(f"❌ Copia incompleta, restaurando...")
            dst.unlink()
            backup = dst.with_suffix('.exe.old')
            if backup.exists():
                backup.rename(dst)
            return False
            
    except Exception as e:
        print(f"❌ Error copiando: {e}")
        # Restaurar backup si existe
        if dst.with_suffix('.exe.old').exists():
            dst.unlink() if dst.exists() else None
            dst.with_suffix('.exe.old').rename(dst)
        return False

def get_local_fallback():
    """Busca cualquier versión local existente"""
    try:
        local_exes = sorted(LOCAL_DIR.glob("Daily Log SLC v*.exe"), reverse=True)
        if local_exes:
            print(f"⚡ Usando versión local: {local_exes[0].name}")
            return local_exes[0]
    except:
        pass
    return None

def ensure_local_copy():
    """Copia o actualiza la versión más reciente (OPTIMIZADO)"""
    LOCAL_DIR.mkdir(parents=True, exist_ok=True)

    # Intentar obtener versión del servidor (puede fallar en redes lentas)
    try:
        server_exe = get_latest_exe_fast()
    except:
        server_exe = None
    
    # Si no hay conexión al servidor, usar versión local
    if not server_exe:
        print("⚠️ No se puede acceder al servidor, buscando versión local...")
        return get_local_fallback()
    
    local_exe = LOCAL_DIR / server_exe.name
    
    # Verificar si necesita actualización (RÁPIDO: solo tamaño y nombre)
    if not needs_update(server_exe, local_exe):
        return local_exe
    
    # Necesita actualizar: copiar archivo
    print(f"📡 Descargando desde servidor...")
    if copy_fast(server_exe, local_exe):
        return local_exe
    else:
        print(f"⚠️ Error descargando, usando versión local...")
        return get_local_fallback()

def run_local_app(exe_path):
    """Ejecuta el .exe local en proceso independiente"""
    if exe_path and exe_path.exists():
        print(f"🚀 Iniciando {exe_path.name}...")
        
        DETACHED_PROCESS = 0x00000008
        subprocess.Popen(
            [str(exe_path)], 
            creationflags=DETACHED_PROCESS,
            close_fds=True,
            shell=False
        )
        
        print(f"✅ Daily Log iniciado")
        print(f"🔌 Launcher cerrándose (conexión liberada)...")
    else:
        print("❌ No se encontró ninguna versión de la aplicación")
        print("   Verifica tu conexión de red e intenta nuevamente")
        input("\nPresiona Enter para cerrar...")

if __name__ == "__main__":
    print("=" * 50)
    print("🚀 Daily Log SLC - Launcher Rápido")
    print("=" * 50)
    
    try:
        local_exe = ensure_local_copy()
        run_local_app(local_exe)
    except Exception as e:
        print(f"\n❌ Error fatal: {e}")
        print("   Contacta al administrador del sistema")
        input("\nPresiona Enter para cerrar...")
    finally:
        sys.exit(0)