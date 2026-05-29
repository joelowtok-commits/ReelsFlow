#!/usr/bin/env python3
"""
Script principal de procesamiento de video en Kaggle.
Ejecutar desde el notebook: !python process_video.py --input <URL_O_PATH>
"""

import os
import sys
import argparse
import subprocess
from pathlib import Path

def download_from_drive(url, output_dir='.'):
    """Descarga video desde Google Drive."""
    import gdown
    print(f"ðŸ“¥ Descargando desde Drive: {url}")
    gdown.download(url, output=output_dir, quiet=False)
    return True

def download_from_youtube(url, output_dir='.'):
    """Descarga video desde YouTube."""
    print(f"ðŸ“¥ Descargando desde YouTube: {url}")
    cmd = [
        'yt-dlp',
        '-f', 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        '-o', os.path.join(output_dir, '%(title)s.%(ext)s'),
        url
    ]
    subprocess.run(cmd, check=True)
    return True

def process_video(input_path, output_dir='/kaggle/working/output'):
    """
    Procesa el video con el pipeline de OpenShorts.
    """
    print(f"ðŸŽ¬ Procesando: {input_path}")
    
    # Verificar si existe main.py en el repo
    main_py = Path('/kaggle/input/openshorts/main.py')
    if not main_py.exists():
        # Buscar en el directorio actual
        main_py = Path('main.py')
        if not main_py.exists():
            print("âŒ main.py no encontrado")
            print("   SubÃ­ el repo de OpenShorts como dataset o copia main.py")
            sys.exit(1)
    
    # Ejecutar main.py
    cmd = [
        sys.executable,
        str(main_py),
        '-i', input_path,
        '-o', output_dir,
        '--format', 'vertical'
    ]
    
    print(f"â–¶ Ejecutando: {' '.join(cmd)}")
    subprocess.run(cmd, check=True)
    
    print(f"âœ… Procesamiento completado")
    print(f"   Output: {output_dir}")

def main():
    parser = argparse.ArgumentParser(description='Procesar video en Kaggle')
    parser.add_argument('--input', '-i', required=True, help='URL de YouTube o path local')
    parser.add_argument('--source', '-s', choices=['auto', 'youtube', 'drive', 'local'], 
                        default='auto', help='Fuente del video')
    parser.add_argument('--output', '-o', default='/kaggle/working/output', 
                        help='Directorio de salida')
    
    args = parser.parse_args()
    
    input_path = args.input
    
    # Determinar fuente
    source = args.source
    if source == 'auto':
        if input_path.startswith('http'):
            if 'youtube' in input_path or 'youtu.be' in input_path:
                source = 'youtube'
            elif 'drive.google.com' in input_path:
                source = 'drive'
        else:
            source = 'local'
    
    # Descargar segÃºn fuente
    if source == 'youtube':
        download_from_youtube(input_path, '/kaggle/working/input')
        input_path = Path('/kaggle/working/input') / Path(input_path).name
    elif source == 'drive':
        download_from_drive(input_path, '/kaggle/working/input')
        # Extraer file_id de la URL
        if 'id=' in input_path:
            file_id = input_path.split('id=')[1].split('&')[0]
        else:
            file_id = input_path.split('/')[-1]
        input_path = Path('/kaggle/working/input') / file_id
    
    # Procesar
    process_video(str(input_path), args.output)

if __name__ == '__main__':
    main()
