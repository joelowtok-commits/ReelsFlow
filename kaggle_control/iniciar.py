#!/usr/bin/env python3
"""
Script de inicio rápido para Kaggle Control.
Muestra el estado actual y los pasos a seguir.
"""

import os
import sys
from pathlib import Path

def check_dependencies():
    """Verifica dependencias instaladas."""
    print("📦 Verificando dependencias...")
    
    deps = {
        'google-api-python-client': 'googleapiclient',
        'google-auth': 'google.auth',
        'gdown': 'gdown',
        'kaggle': 'kaggle',
    }
    
    installed = []
    missing = []
    
    for pkg, import_name in deps.items():
        try:
            __import__(import_name.replace('-', '.'))
            installed.append(pkg)
        except ImportError:
            missing.append(pkg)
    
    if installed:
        print(f"   ✅ Instaladas: {', '.join(installed)}")
    
    if missing:
        print(f"   ❌ Faltan: {', '.join(missing)}")
        print(f"\n   Instalar: pip install {' '.join(missing)}")
    
    return len(missing) == 0

def check_credentials():
    """Verifica archivos de credenciales."""
    print("\n🔑 Verificando credenciales...")
    
    files = {
        'credentials.json': 'Google Drive API',
        'kaggle.json': 'Kaggle API',
    }
    
    found = []
    missing = []
    
    for file, name in files.items():
        if Path(file).exists():
            found.append(file)
        else:
            # Buscar en directorios comunes
            if Path('~/.config/gdown').expandvp().exists() and file == 'credentials.json':
                found.append(file)
            elif Path('~/.kaggle').exists() and file == 'kaggle.json':
                found.append(file)
            else:
                missing.append((file, name))
    
    if found:
        print(f"   ✅ Encontrados: {', '.join(found)}")
    
    if missing:
        print(f"   ⚠️  Faltan:")
        for file, name in missing:
            print(f"      - {file} ({name})")
    
    return len(missing) == 0

def show_next_steps():
    """Muestra los próximos pasos."""
    print("\n📋 Próximos pasos:")
    print("""
1. Instalar dependencias:
   pip install -r requirements.txt

2. Configurar Google Drive (opcional pero recomendado):
   - Ir a https://console.cloud.google.com/
   - Crear proyecto
   - Habilitar Drive API
   - Descargar credentials.json

3. Configurar Kaggle:
   - Ir a https://www.kaggle.com/<username>/account
   - Crear API Token
   - Ejecutar: kaggle config set

4. Probar con un video:
   python local/upload_to_drive.py tu_video.mp4
   """)

def main():
    print("🎬 OpenShorts - Kaggle Control")
    print("=" * 50)
    
    deps_ok = check_dependencies()
    creds_ok = check_credentials()
    
    print("\n" + "=" * 50)
    
    if deps_ok:
        print("✅ Dependencias OK")
    else:
        print("⚠️  Faltan dependencias")
    
    if creds_ok:
        print("✅ Credenciales OK")
    else:
        print("⚠️  Faltan credenciales (algunas funciones no estarán disponibles)")
    
    show_next_steps()

if __name__ == '__main__':
    main()
