#!/usr/bin/env python3
"""
Script unificado para:
1. Ejecutar kernel en Kaggle
2. Esperar a que termine
3. Descargar automáticamente los resultados
"""

import os
import sys
import time
import subprocess
from pathlib import Path
from datetime import datetime

def run_kernel_and_download(username='joelowtok', kernel_name='openshorts-processor', local_output_dir='kaggle_output'):
    """
    Ejecuta el kernel y descarga los resultados automáticamente.
    
    Args:
        username: Usuario de Kaggle
        kernel_name: Nombre del kernel
        local_output_dir: Directorio local para guardar resultados
    """
    kernel_slug = f'{username}/{kernel_name}'
    
    print("="*60)
    print("Kaggle Run & Download")
    print("="*60)
    print(f"Kernel: {kernel_slug}")
    print(f"Output local: {local_output_dir}/")
    print("="*60)
    
    # 1. Ejecutar kernel
    print(f"\n[1/3] Ejecutando kernel...")
    result = subprocess.run(
        ['kaggle', 'kernels', 'execute', kernel_slug],
        capture_output=True,
        text=True,
        encoding='utf-8',
        errors='replace'
    )
    
    if result.returncode != 0:
        print(f"❌ Error al ejecutar: {result.stderr}")
        return False
    
    print(f"✅ Kernel iniciado")
    
    # 2. Esperar a que termine
    print(f"\n[2/3] Esperando finalización...")
    print(f"   (puede tardar varios minutos)")
    
    start_time = time.time()
    timeout = 3600  # 1 hora
    poll_interval = 15
    
    while time.time() - start_time < timeout:
        status_result = subprocess.run(
            ['kaggle', 'kernels', 'status', '-k', kernel_slug],
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace'
        )
        
        status = status_result.stdout.lower()
        print(f"   Estado: {status_result.stdout.strip()}")
        
        if 'complete' in status or 'success' in status:
            print(f"   ✅ Completado")
            break
        elif 'error' in status or 'failed' in status:
            print(f"   ❌ Falló")
            return False
        
        time.sleep(poll_interval)
    
    # 3. Descargar resultados
    print(f"\n[3/3] Descargando resultados...")
    
    local_path = Path(local_output_dir)
    local_path.mkdir(parents=True, exist_ok=True)
    
    pull_result = subprocess.run(
        ['kaggle', 'kernels', 'pull', kernel_slug, '-p', str(local_path)],
        capture_output=True,
        text=True,
        encoding='utf-8',
        errors='replace'
    )
    
    if pull_result.returncode == 0:
        print(f"✅ Resultados descargados en: {local_path}/")
        
        # Listar archivos
        files = list(local_path.iterdir())
        if files:
            print(f"\n📁 Archivos descargados:")
            for f in files:
                size = f.stat().st_size if f.is_file() else 0
                size_str = f"{size / 1024 / 1024:.2f} MB" if size > 0 else ""
                print(f"   - {f.name} {size_str}")
        else:
            print(f"   (vacío)")
        
        return True
    else:
        print(f"❌ Error al descargar: {pull_result.stderr}")
        return False


if __name__ == '__main__':
    success = run_kernel_and_download()
    sys.exit(0 if success else 1)
