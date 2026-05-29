#!/usr/bin/env python3
"""
Script para desplegar el kernel en Kaggle.
Ejecutar una sola vez para crear el kernel.
"""

import os
import sys
import subprocess
from pathlib import Path
import codecs

# Forzar UTF-8 para evitar errores de encoding en Windows
if sys.platform == 'win32':
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

def main():
    print("Deploy de OpenShorts Kernel a Kaggle")
    print("=" * 50)

    # Verificar kaggle CLI
    try:
        result = subprocess.run(['kaggle', '--version'], capture_output=True, text=True)
        if result.returncode == 0:
            print("[OK] Kaggle CLI disponible")
        else:
            print("[ERR] Kaggle CLI no instalada")
            print(" pip install kaggle")
            sys.exit(1)
    except FileNotFoundError:
        print("[ERR] Kaggle CLI no encontrada")
        print(" pip install kaggle")
        sys.exit(1)

    # Verificar credenciales
    kaggle_dir = Path.home() / '.kaggle'
    if not (kaggle_dir / 'kaggle.json').exists() and not (kaggle_dir / 'access_token').exists():
        print("[ERR] No se encontraron credenciales de Kaggle")
        print(" 1. Andá a https://www.kaggle.com/settings")
        print(" 2. API Tokens -> Generate New Token")
        print(" 3. Guardá el token en ~/.kaggle/access_token")
        sys.exit(1)

    print("[OK] Credenciales encontradas")

    # Directorio del kernel
    kernel_dir = Path('kaggle_kernel')
    if not kernel_dir.exists():
        print(f"[ERR] No se encontró: {kernel_dir}")
        sys.exit(1)

    # Archivos del kernel
    kernel_files = list(kernel_dir.glob('*.py')) + list(kernel_dir.glob('*.json'))
    if not kernel_files:
        print(f"[ERR] No hay archivos en {kernel_dir}")
        sys.exit(1)

    print(f"\nArchivos del kernel:")
    for f in kernel_files:
        print(f" - {f.name}")

    # Push a Kaggle
    print(f"\nEmpujando a Kaggle...")
    print(f" Kernel: joelowtok/openshorts-processor")

    try:
        result = subprocess.run(
            ['kaggle', 'kernels', 'push', '-p', str(kernel_dir)],
            capture_output=True,
            text=True,
            check=True
        )
        print(f"\n[OK] Kernel subido exitosamente!")
        print(f"\n{result.stdout}")
        print(f"\n Próximos pasos:")
        print(f" 1. Abrí el kernel en Kaggle")
        print(f" 2. Verificá que las variables de entorno estén configuradas")
        print(f" 3. Ejecutá el kernel")
    except subprocess.CalledProcessError as e:
        print(f"\n[ERR] Error: {e.stderr}")
        print(f"\n Asegurate de tener permisos para crear kernels")
        sys.exit(1)

if __name__ == '__main__':
    main()
