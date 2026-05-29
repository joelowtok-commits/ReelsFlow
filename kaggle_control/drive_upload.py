#!/usr/bin/env python3
"""
Sube archivos a Google Drive.
Requiere: credentials.json en el mismo directorio
"""

import os
import sys
from pathlib import Path

def upload_to_drive(file_path, folder_id=None):
    """
    Sube un archivo a Google Drive.
    
    Args:
        file_path: Path al archivo local
        folder_id: ID de carpeta de Drive (opcional)
    
    Returns:
        dict con file_id, file_name, web_view_link
    """
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
    
    if not cred_path.exists():
        print("❌ No se encontró credentials.json")
        print("   Descargalo de: https://console.cloud.google.com/")
        sys.exit(1)
    
    if token_path.exists():
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(cred_path, SCOPES)
            creds = flow.run_local_server(port=0)
        
        # Guardar token
        with open(token_path, 'w') as token:
            token.write(creds.to_json())
    
    # Subir archivo
    service = build('drive', 'v3', credentials=creds)
    
    file_metadata = {'name': Path(file_path).name}
    if folder_id:
        file_metadata['parents'] = [folder_id]
    
    media = MediaFileUpload(file_path, resumable=True)
    
    file = service.files().create(
        body=file_metadata,
        media_body=media,
        fields='id, name, webViewLink, webContentLink'
    ).execute()
    
    return {
        'file_id': file.get('id'),
        'file_name': file.get('name'),
        'web_view_link': file.get('webViewLink'),
        'web_content_link': file.get('webContentLink')
    }

def download_from_drive(file_id, output_path='.'):
    """
    Descarga un archivo desde Google Drive.
    """
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
    
    SCOPES = ['https://www.googleapis.com/auth/drive.file']
    
    token_path = Path('token.json')
    cred_path = Path('credentials.json')
    
    if token_path.exists():
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)
    else:
        flow = InstalledAppFlow.from_client_secrets_file(cred_path, SCOPES)
        creds = flow.run_local_server(port=0)
        with open(token_path, 'w') as token:
            token.write(creds.to_json())
    
    service = build('drive', 'v3', credentials=creds)
    
    request = service.files().get_media(fileId=file_id)
    
    output = Path(output_path) / f'downloaded_{file_id}'
    
    with open(output, 'wb') as f:
        request.download(file_handle=f)
    
    return str(output)

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Subir archivo a Google Drive')
    parser.add_argument('file', help='Archivo a subir')
    parser.add_argument('--folder', help='ID de carpeta de Drive (opcional)')
    
    args = parser.parse_args()
    
    if not os.path.exists(args.file):
        print(f"❌ Archivo no encontrado: {args.file}")
        sys.exit(1)
    
    result = upload_to_drive(args.file, args.folder)
    print(f"✅ Subido: {result['file_name']}")
    print(f"   URL: {result['web_view_link']}")
    print(f"   ID: {result['file_id']}")
