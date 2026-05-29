#!/usr/bin/env python3
"""
Crea un SSH tunnel hacia tu mÃ¡quina local usando ngrok.
Permite conectar desde Kaggle a tu mÃ¡quina via SSH.
"""

import os
import sys
import subprocess
import argparse

def setup_ngrok_tunnel(port=22, token=None):
    """
    Crea un tunnel SSH usando ngrok.
    """
    print(f"ðŸ”„ Creando tunnel SSH en puerto {port}...")
    
    # Verificar si ngrok estÃ¡ instalado
    ngrok_path = None
    try:
        result = subprocess.run(['where', 'ngrok'], capture_output=True, text=True)
        if result.returncode == 0:
            ngrok_path = result.stdout.strip().split('\n')[0]
    except:
        pass
    
    if not ngrok_path:
        # Buscar en PATH comun
        possible_paths = [
            os.path.expanduser("~/.ngrok/ngrok.exe"),
            os.path.expanduser("~/ngrok/ngrok.exe"),
            "C:/ngrok/ngrok.exe",
            "ngrok.exe"
        ]
        for path in possible_paths:
            if os.path.exists(path):
                ngrok_path = path
                break
    
    if not ngrok_path:
        print("âŒ ngrok no encontrado")
        print("   Instalalo de: https://ngrok.com/download")
        print("   O: winget install ngrok")
        sys.exit(1)
    
    # Configurar token si se proporciona
    if token:
        subprocess.run([ngrok_path, 'config', 'add-token', token])
    
    # Iniciar tunnel
    print(f"ðŸš€ Iniciando tunnel con: {ngrok_path} tcp {port}")
    
    # ngrok con output parseable
    cmd = [ngrok_path, 'tcp', str(port), '--log', 'stdout']
    
    try:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        print("âœ… ngrok iniciado. Esperando URL...")
        print("   Presiona Ctrl+C para detener")
        
        # Leer output hasta encontrar la URL
        for line in process.stdout:
            if 'tcp://' in line:
                print(f"\nðŸŽ¯ Tunnel activo!")
                print(f"   URL: {line.strip()}")
                print(f"\n   Para conectar desde Kaggle:")
                print(f"   ssh usuario@{line.split(':')[0]} -p {line.split(':')[-1]}")
                break
                
    except KeyboardInterrupt:
        print("\nðŸ›‘ Tunnel detenido")
        process.terminate()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Crear SSH tunnel con ngrok')
    parser.add_argument('--port', '-p', type=int, default=22, help='Puerto SSH local')
    parser.add_argument('--token', help='Token de ngrok (opcional)')
    
    args = parser.parse_args()
    setup_ngrok_tunnel(args.port, args.token)
