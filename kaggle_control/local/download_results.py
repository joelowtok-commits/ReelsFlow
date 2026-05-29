#!/usr/bin/env python3
"""
Descarga resultados desde Google Drive.
"""

import os
import sys
import argparse
from pathlib import Path

def download_from_drive(file_id, output_path='.'):
    """
    Descarga un archivo desde Google Drive.
    """
    print(f"ðŸ“¥ Descargando: {file_id}")
    
    try:
        import gdown
    except ImportError:
        print("Instalando gdown...")
        os.system("pip install gdown")
        import gdown
    
    # gdown descarga por file_id
    url = f"https://drive.google.com/uc?id={file_id}"
    
    output = Path(output_path) / Path(file_id)
    
    gdown.download(url, str(output), quiet=False)
    
    print(f"âœ… Descargado: {output}")
    return str(output)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Descargar archivo de Google Drive')
    parser.add_argument('file_id', help='ID del archivo en Drive')
    parser.add_argument('--output', '-o', default='.', help='Directorio de salida')
    
    args = parser.parse_args()
    download_from_drive(args.file_id, args.output)
