#!/usr/bin/env python3
"""
Monitorea el progreso de un job en Kaggle.
Muestra logs en tiempo real si se especifica --live.
"""

import os
import sys
import argparse
import time
import subprocess

def get_kaggle_output(kernel_url, interval=5):
    """
    Obtiene el output de un kernel de Kaggle.
    Usa kaggle CLI.
    """
    try:
        # kaggle kernels output <kernel-url> -w
        cmd = ['kaggle', 'kernels', 'output', kernel_url]
        
        if interval > 0:
            cmd.append('-w')  # Watch mode
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        return result.stdout
        
    except FileNotFoundError:
        print("âŒ kaggle CLI no encontrado")
        print("   pip install kaggle")
        print("   kaggle config set")
        sys.exit(1)

def monitor_with_api(kernel_url, live=False):
    """
    Monitorea el progreso usando polling.
    """
    print(f"ðŸ“Š Monitoreando: {kernel_url}")
    
    if live:
        print("ðŸ”´ Modo en vivo (Ctrl+C para detener)")
        print(get_kaggle_output(kernel_url, interval=5))
    else:
        # Solo mostrar Ãºltimo output
        print(get_kaggle_output(kernel_url, interval=0))

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Monitorear job en Kaggle')
    parser.add_argument('kernel_url', help='URL del kernel (ej: username/kernel-name)')
    parser.add_argument('--live', '-l', action='store_true', help='Modo en vivo')
    parser.add_argument('--interval', '-t', type=int, default=5, 
                        help='Intervalo de polling (segundos)')
    
    args = parser.parse_args()
    monitor_with_api(args.kernel_url, args.live)
