#!/usr/bin/env python3
"""
Descarga automáticamente los resultados del kernel de Kaggle.
Versión mejorada que descarga archivos específicos del output.
"""

import os
import sys
import time
import subprocess
import requests
from pathlib import Path
from datetime import datetime

class KaggleOutputDownloader:
    """Descarga resultados de kernels de Kaggle de forma automática."""
    
    def __init__(self, username='joelowtok', kernel_name='openshorts-processor'):
        self.username = username
        self.kernel_name = kernel_name
        self.kernel_slug = f'{username}/{kernel_name}'
        self.output_dir = Path('kaggle_output')
        self.output_dir.mkdir(exist_ok=True)
        
    def get_kernel_run_status(self):
        """Obtiene el estado de la última corrida del kernel."""
        try:
            result = subprocess.run(
                ['kaggle', 'kernels', 'status', '-k', self.kernel_slug],
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace'
            )
            return result.stdout
        except Exception as e:
            return f"Error: {e}"
    
    def wait_for_completion(self, timeout=3600, poll_interval=15):
        """
        Espera a que el kernel termine de ejecutarse.
        
        Args:
            timeout: Tiempo máximo de espera en segundos (default: 1 hora)
            poll_interval: Intervalo entre consultas en segundos
        """
        print(f"⏳ Esperando a que el kernel {self.kernel_slug} termine...")
        print(f"   Timeout: {timeout}s | Poll interval: {poll_interval}s")
        print(f"   Iniciando: {datetime.now().strftime('%H:%M:%S')}")
        
        start_time = time.time()
        last_status = ""
        
        while time.time() - start_time < timeout:
            status = self.get_kernel_run_status()
            
            # Mostrar solo si cambió el estado
            if status != last_status:
                print(f"   [{datetime.now().strftime('%H:%M:%S')}] {status.strip()}")
                last_status = status
            
            status_lower = status.lower()
            if 'complete' in status_lower or 'success' in status_lower:
                print(f"   ✅ Completado en {datetime.now().strftime('%H:%M:%S')}")
                return True
            elif 'error' in status_lower or 'failed' in status_lower:
                print(f"   ❌ Falló en {datetime.now().strftime('%H:%M:%S')}")
                return False
            
            time.sleep(poll_interval)
        
        print(f"⏰ Timeout alcanzado ({timeout}s)")
        return False
    
    def pull_kernel_output(self):
        """
        Descarga el output del kernel (notebook con resultados).
        """
        print(f"\n📥 Descargando output del kernel...")
        
        try:
            result = subprocess.run(
                ['kaggle', 'kernels', 'pull', self.kernel_slug, '-p', str(self.output_dir)],
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace'
            )
            
            if result.returncode == 0:
                print(f"✅ Output descargado en: {self.output_dir}/")
                self.list_downloaded_files()
                return True
            else:
                print(f"❌ Error: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"❌ Error: {e}")
            return False
    
    def list_downloaded_files(self):
        """Lista los archivos descargados."""
        if not self.output_dir.exists():
            return
            
        files = list(self.output_dir.iterdir())
        if files:
            print(f"\n📁 Archivos en {self.output_dir}/:")
            for f in files:
                size = f.stat().st_size if f.is_file() else 0
                size_str = f"{size / 1024 / 1024:.2f} MB" if size > 0 else ""
                print(f"   - {f.name} {size_str}")
        else:
            print(f"   (vacío)")
    
    def get_output_files(self):
        """
        Obtiene la lista de archivos de video del output.
        """
        video_files = []
        if self.output_dir.exists():
            for f in self.output_dir.iterdir():
                if f.is_file() and f.suffix.lower() in ['.mp4', '.avi', '.mov', '.mkv', '.webm']:
                    video_files.append(f)
        return video_files
    
    def download_complete(self):
        """Verifica si la descarga se completó correctamente."""
        video_files = self.get_output_files()
        if video_files:
            print(f"\n✅ ¡Descarga completada! {len(video_files)} video(s) encontrado(s)")
            return True
        print("\n⚠️  No se encontraron archivos de video")
        return False


def main():
    """Función principal."""
    print("="*60)
    print("Kaggle Output Downloader")
    print("="*60)
    
    # Crear downloader
    downloader = KaggleOutputDownloader(
        username='joelowtok',
        kernel_name='openshorts-processor'
    )
    
    # Esperar a que termine
    if not downloader.wait_for_completion(timeout=3600, poll_interval=15):
        print("\n❌ El kernel no se completó correctamente")
        sys.exit(1)
    
    # Descargar resultados
    if downloader.pull_kernel_output():
        if downloader.download_complete():
            print("\n✅ ¡Proceso completado exitosamente!")
        else:
            print("\n⚠️  Proceso completado pero sin archivos de video")
    else:
        print("\n❌ Error al descargar los resultados")
        sys.exit(1)


if __name__ == '__main__':
    main()
