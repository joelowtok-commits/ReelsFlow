#!/usr/bin/env python3
"""
Sube los resultados procesados a Google Drive.
Ejecutar despuÃ©s de procesar el video.
"""

import os
import sys
import argparse
from pathlib import Path

def upload_to_drive(file_path, folder_id=None):
    """Sube un archivo a Google Drive."""
    try:
        from google.oauth2.credentials import Credentials
        from google.oauth2 import service_account
        from google.auth.transport.requests import Request
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaFileUpload
    except ImportError:
        print("Instalando google-api-python-client...")
        os.system("pip install google-api-python-client google-auth")
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaFileUpload
    
    # Usar service account si existe
    cred_path = Path('service_account.json')
    if cred_path.exists():
        creds = service_account.Credentials.from_service_account_file(
            cred_path, 
            scopes=['https://www.googleapis.com/auth/drive.file']
        )
    else:
        # OAuth normal
        print("âš  No hay service_account.json - usando OAuth")
        print("   Para producciÃ³n, usÃ¡ service account")
        sys.exit(1)
    
    try:
        service = build('drive', 'v3', credentials=creds)
        
        file_metadata = {'name': Path(file_path).name}
        if folder_id:
            file_metadata['parents'] = [folder_id]
        
        media = MediaFileUpload(str(file_path), resumable=True)
        
        file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id, name, webViewLink'
        ).execute()
        
        print(f"âœ… Subido: {file.get('name')}")
        print(f"   URL: {file.get('webViewLink')}")
        print(f"   ID: {file.get('id')}")
        
        return file.get('id')
        
    except Exception as e:
        print(f"âŒ Error: {e}")
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description='Subir resultados a Drive')
    parser.add_argument('--folder', '-f', help='Carpeta de destino en Drive')
    parser.add_argument('--output-dir', '-o', default='/kaggle/working/output',
                        help='Directorio con los resultados')
    
    args = parser.parse_args()
    
    output_dir = Path(args.output_dir)
    
    if not output_dir.exists():
        print(f"âŒ Directorio no encontrado: {output_dir}")
        sys.exit(1)
    
    # Subir todos los archivos del directorio
    files = list(output_dir.glob('*.mp4')) + list(output_dir.glob('*.json'))
    
    if not files:
        print("â  No hay archivos para subir")
        sys.exit(0)
    
    print(f"ðŸ“¤ Subiendo {len(files)} archivos...")
    
    for file_path in files:
        upload_to_drive(str(file_path), args.folder)
    
    print("âœ… Todos los archivos subidos")

if __name__ == '__main__':
    main()
