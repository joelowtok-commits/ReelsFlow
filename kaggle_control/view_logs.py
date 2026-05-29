#!/usr/bin/env python3
"""
Ver logs del kernel sin errores de encoding.
"""

import sys
import json
from pathlib import Path

try:
    import httpx
except ImportError:
    print("Instalando httpx...")
    import subprocess
    subprocess.run([sys.executable, '-m', 'pip', 'install', 'httpx', '-q'])
    import httpx

def get_logs(kernel_slug='joelowtok/openshorts-processor'):
    """Obtiene los logs del kernel usando la API de Kaggle."""
    
    # Leer access_token
    token_path = Path.home() / '.kaggle' / 'access_token'
    if not token_path.exists():
        print("Error: No se encontró access_token en ~/.kaggle/access_token")
        return None
    
    with open(token_path, 'r') as f:
        token = f.read().strip()
    
    if not token:
        print("Error: access_token vacío")
        return None
    
    # URL de la API
    url = f'https://www.kaggle.com/api/v1/kernels/{kernel_slug}/logs'
    
    headers = {
        'User-Agent': 'OpenShorts/1.0',
    }
    
    try:
        # Request con el token
        response = httpx.get(url, headers=headers, timeout=30)
        
        # Verificar si requiere autenticación
        if response.status_code == 401:
            # Intentar con API key
            kaggle_json = Path.home() / '.kaggle' / 'kaggle.json'
            if kaggle_json.exists():
                with open(kaggle_json, 'r') as f:
                    creds = json.load(f)
                username = creds.get('username', '')
                key = creds.get('key', '')
                import base64
                auth = base64.b64encode(f'{username}:{key}'.encode()).decode()
                headers['Authorization'] = f'Basic {auth}'
                response = httpx.get(url, headers=headers, timeout=30)
        
        if response.status_code == 200:
            # Guardar logs
            logs_file = Path('kernel_logs.txt')
            with open(logs_file, 'w', encoding='utf-8') as f:
                f.write(response.text)
            
            print(f"Logs guardados en: {logs_file}")
            print(f"Tamaño: {len(response.text)} bytes")
            print()
            
            # Mostrar últimas 50 líneas
            lines = response.text.split('\n')
            print(f"Mostrando {min(50, len(lines))} de {len(lines)} líneas:")
            print("=" * 60)
            for line in lines[-50:]:
                print(line)
            print("=" * 60)
            
            return response.text
        else:
            print(f"Error {response.status_code}: {response.text[:200]}")
            return None
            
    except Exception as e:
        print(f"Error: {e}")
        print(f"\nAlternativa: https://www.kaggle.com/code/{kernel_slug}")
        return None

if __name__ == '__main__':
    kernel = sys.argv[1] if len(sys.argv) > 1 else 'joelowtok/openshorts-processor'
    get_logs(kernel)
