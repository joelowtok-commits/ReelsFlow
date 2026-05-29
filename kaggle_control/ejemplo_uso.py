#!/usr/bin/env python3
"""
Ejemplo completo de uso:
1. Sube video a Drive
2. Inicia job en Kaggle
3. Monitorea progreso
4. Baja resultados
"""

import os
import sys
import time
import argparse
from pathlib import Path

def main():
    parser = argparse.ArgumentParser(description='Ejemplo completo Kaggle + Drive')
    parser.add_argument('video', help='Video a procesar')
    parser.add_argument('--kernel', help='URL del kernel en Kaggle (usuario/nombre)')
    parser.add_argument('--drive-folder', help='Carpeta de Drive para resultados')
    
    args = parser.parse_args()
    
    print("🎬 OpenShorts - Kaggle Control")
    print("=" * 50)
    
    # Paso 1: Subir a Drive
    print("\n1️⃣  Subiendo video a Google Drive...")
    print(f"   Archivo: {args.video}")
    
    if os.path.exists(args.video):
        from local.upload_to_drive import upload_to_drive
        file_id = upload_to_drive(args.video)
        drive_url = f"https://drive.google.com/file/d/{file_id}"
        print(f"   ✅ Subido: {drive_url}")
    else:
        print(f"   ⚠️  Archivo no encontrado: {args.video}")
        sys.exit(1)
    
    # Paso 2: Iniciar en Kaggle
    print("\n2️⃣  Iniciando procesamiento en Kaggle...")
    if args.kernel:
        print(f"   Kernel: {args.kernel}")
        print(f"   ⚠️  Deberías ejecutar manualmente en Kaggle:")
        print(f"   !python kaggle/process_video.py --input {drive_url}")
    else:
        print("   ⚠️  No se proporcionó kernel - ejecutá manualmente")
    
    print("\n   Para monitorear:")
    print(f"   python local/monitor_job.py {args.kernel} --live")
    
    # Paso 3: Esperar resultados
    print("\n3️⃣  Esperando resultados...")
    print("   (Monitoreá el progreso con el comando de arriba)")
    
    # Paso 4: Bajar resultados
    print("\n4️⃣  Para bajar resultados:")
    print(f"   python local/download_results.py <FILE_ID> --output ./resultados")
    
    print("\n✅ ¡Listo!")

if __name__ == '__main__':
    main()
