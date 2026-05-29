#!/usr/bin/env python3
"""
Test de setup - Verifica que todo este configurado correctamente.
"""

import os
import sys
from pathlib import Path

def test_kaggle():
    """Test Kaggle API."""
    print("Testeando Kaggle API...")
    
    try:
        from kaggle import api
        print("✅ Kaggle API instalada")
        
        # Verificar credenciales
        kaggle_dir = Path.home() / Path('.kaggle')
        if (kaggle_dir / 'kaggle.json').exists() or (kaggle_dir / 'access_token').exists():
            print("✅ Credenciales encontradas")
            return True
        else:
            print("❌ No se encontraron credenciales")
            print(f"   Guarda el token en: {kaggle_dir}/access_token")
            return False
            
    except ImportError:
        print("❌ Kaggle API no instalada")
        print("   pip install kaggle")
        return False

def test_drive():
    """Test Google Drive."""
    print("\nTesteando Google Drive...")
    
    cred_path = Path('credentials.json')
    if cred_path.exists():
        print("✅ credentials.json encontrado")
        return True
    else:
        print("⚠️  credentials.json no encontrado")
        print("   Segui SETUP_KAGGLE.md para configurar")
        return False

def test_kernel():
    """Test kernel files."""
    print("\nTesteando kernel files...")
    
    kernel_dir = Path('kaggle_kernel')
    if not kernel_dir.exists():
        print("❌ kaggle_kernel/ no encontrado")
        return False
    
    main_py = kernel_dir / 'main.py'
    metadata = kernel_dir / 'kernel-metadata.json'
    
    if main_py.exists() and metadata.exists():
        print("✅ Kernel files OK")
        return True
    else:
        print("❌ Faltan archivos en kaggle_kernel/")
        return False

def test_dependencies():
    """Test dependencias."""
    print("\nTesteando dependencias...")
    
    deps = ['googleapiclient', 'gdown']
    missing = []
    
    for dep in deps:
        try:
            __import__(dep)
            print(f"✅ {dep}")
        except ImportError:
            print(f"❌ {dep}")
            missing.append(dep)
    
    if missing:
        print(f"\n   pip install {' '.join(missing)}")
        return False
    
    return True

if __name__ == '__main__':
    print("Test de Setup - Kaggle Integration\n")
    print("=" * 50)
    
    results = {
        'Kaggle API': test_kaggle(),
        'Google Drive': test_drive(),
        'Kernel Files': test_kernel(),
        'Dependencias': test_dependencies()
    }
    
    print("\n" + "=" * 50)
    print("Resumen:")
    
    all_ok = all(results.values())
    for test, result in results.items():
        status = "✅" if result else "❌"
        print(f"   {status} {test}")
    
    if all_ok:
        print("\n✅ Todo OK! Podés usar Kaggle Integration")
        print("\nProximos pasos:")
        print("   1. python deploy_kernel.py")
        print("   2. python kaggle_integration.py video.mp4")
    else:
        print("\n⚠️  Algunos tests fallaron")
        print("   Revisa SETUP_KAGGLE.md")
