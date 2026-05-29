#!/usr/bin/env python3
"""
Sube videos a Google Drive desde tu mÃ¡quina local.
Requiere: credentials.json de Google Drive API
"""

import os
import sys
import argparse
from pathlib import Path

def upload_to_drive(file_path, folder_id=None):
    """
    Sube un archivo a Google Drive.
    """
    print(f"ðŸ“¤ Subiendo: {file_path}")
    
    try:
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from google.auth.transport.requests import Request
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaFileUpload
    except ImportError:
        print("Installando dependencias: google-api-python-client google-auth-httplib2 google-auth-oauthlib")
        os.system("pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib")
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from google.auth.transport.requests import Request
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaFileUpload
    
    SCOPES = ['https://www.googleapis.com/auth/drive.file']
    
    # Buscar credentials
    creds = None
    token_path = Path('token.json')
    cred_path = Path('credentials.json')
    
    if token_path.exists():
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not cred_path.exists():
                print("âŒ No se encontrÃ³ credentials.json")
                print("   Descargalo de: https://console.cloud.google.com/")
                sys.exit(1)
            flow = InstalledAppFlow.from_client_secrets_file(cred_path, SCOPES)
            creds = flow.run_local_server(port=0)
        
        # Guardar token
        with open(token_path, 'w') as token:
            token.write(creds.to_json())
    
    # Subir archivo
    try:
        service = build('drive', 'v3', credentials=creds)
        
        file_metadata = {'name': Path(file_path).name}
        if folder_id:
            file_metadata['parents'] = [folder_id]
        
        media = MediaFileUpload(file_path, resumable=True)
        
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

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Subir archivo a Google Drive')
    parser.add_argument('file', help='Archivo a subir')
    parser.add_argument('--folder', help='ID de carpeta de Drive (opcional)')
    
    args = parser.parse_args()
    
    if not os.path.exists(args.file):
        print(f"âŒ Archivo no encontrado: {args.file}")
        sys.exit(1)
    
    upload_to_drive(args.file, args.folder)
