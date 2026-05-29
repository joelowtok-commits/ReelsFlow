#!/usr/bin/env python3
"""
Kaggle Integration para OpenShorts.
Conecta tu app local con Kaggle para procesamiento remoto.
"""

import os
import sys
import json
import time
import subprocess
import shutil
from pathlib import Path
from datetime import datetime

try:
    from kaggle import api as kaggle_api
    KAGGLE_API_AVAILABLE = True
except ImportError:
    KAGGLE_API_AVAILABLE = False
    print("kaggle no disponible: pip install kaggle")


class KaggleIntegration:
    """Integracion con Kaggle API."""

    def __init__(self, username='joelowtok'):
        self.username = username
        self.kernel_name = 'openshorts-processor'
        self.kernel_slug = f'{username}/{self.kernel_name}'
        self.job_status = {}

    def cleanup_old_datasets(self, pattern='openshorts-input'):
        """
        Elimina todos los datasets viejos que coincidan con el patron.
        Usa kaggle datasets delete con confirmacion automatica.
        
        Args:
            pattern: Patron a buscar en los nombres de datasets
            
        Returns:
            Lista de datasets eliminados
        """
        print(f"[CLEAN] Buscando datasets viejos con patron: {pattern}")
        
        try:
            result = subprocess.run(
                ['kaggle', 'datasets', 'list', '-m'],
                capture_output=True,
                text=True,
                timeout=60,
                encoding='utf-8',
                errors='replace'
            )
            
            if result.returncode != 0:
                print(f"[WARN] No se pudo listar datasets (puede ser la primera vez)")
                return []
            
            deleted = []
            lines = result.stdout.strip().split('\n')
            
            for line in lines[1:]:
                if not line.strip():
                    continue
                
                parts = line.split()
                if len(parts) > 0:
                    ref = parts[0].strip()
                    if pattern in ref and 'openshorts-processor' not in ref:
                        print(f"  Eliminando: {ref}")
                        
                        delete_cmd = f'echo yes | kaggle datasets delete "{ref}"'
                        del_result = subprocess.run(
                            delete_cmd,
                            shell=True,
                            capture_output=True,
                            text=True,
                            timeout=60
                        )
                        
                        if del_result.returncode == 0 or 'deleted' in del_result.stdout.lower():
                            print(f"    [OK] Eliminado")
                            deleted.append(ref)
                        else:
                            print(f"    [WARN] No se pudo eliminar")
            
            if deleted:
                print(f"[CLEAN] {len(deleted)} datasets eliminados")
            else:
                print(f"[CLEAN] No se encontraron datasets viejos para eliminar")
            
            return deleted
            
        except subprocess.TimeoutExpired:
            print(f"[WARN] Timeout al listar datasets - salteando limpieza")
            return []
        except Exception as e:
            print(f"[WARN] Error limpiando datasets: {e} - continuando sin limpieza")
            return []

    def upload_video_dataset(self, video_path, dataset_name='openshorts-input'):
        """
        Sube un video como Kaggle Dataset con barra de progreso.
        
        Args:
            video_path: Path al archivo de video
            dataset_name: Nombre del dataset en Kaggle
            
        Returns:
            dataset_slug o None
        """
        video_file = Path(video_path)
        if not video_file.exists():
            print(f"[ERR] Archivo no encontrado: {video_path}")
            return None
        
        file_size = video_file.stat().st_size
        file_size_mb = file_size / (1024 * 1024)
        print(f"[PUSH] Subiendo video a Kaggle Dataset: {dataset_name}")
        print(f"       Tamaño: {file_size_mb:.2f} MB")
        
        temp_dir = Path(f'temp_dataset_{int(time.time())}')
        temp_dir.mkdir(exist_ok=True)
        
        try:
            print(f"[PROGRESS] Copiando archivo temporal...", end=' ')
            shutil.copy(video_file, temp_dir / video_file.name)
            print("[OK]")
            
            metadata = {
                'title': dataset_name,
                'id': f'{self.username}/{dataset_name}',
                'licenses': [{'name': 'CC0'}],
                'resources': [{
                    'path': video_file.name,
                    'name': video_file.stem.replace('.', '_')
                }]
            }
            
            metadata_path = temp_dir / 'dataset-metadata.json'
            with open(metadata_path, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2)
            
            print(f"[PROGRESS] Subiendo a Kaggle...")
            
            import threading
            import time as time_module
            
            progress_chars = ['|', '/', '-', '\\']
            progress_idx = [0]
            stop_event = threading.Event()
            
            def animate():
                while not stop_event.is_set():
                    char = progress_chars[progress_idx[0] % len(progress_chars)]
                    sys.stdout.write(f'\r[PROGRESS] [{char}] Subiendo...   ')
                    sys.stdout.flush()
                    progress_idx[0] += 1
                    time_module.sleep(0.1)
                sys.stdout.write('\r')
                sys.stdout.flush()
            
            thread = threading.Thread(target=animate)
            thread.daemon = True
            thread.start()
            
            result = subprocess.run(
                ['kaggle', 'datasets', 'create', '-p', str(temp_dir), '-r', 'skip'],
                capture_output=True,
                text=True,
                timeout=600
            )
            
            stop_event.set()
            thread.join(timeout=1)
            
            if result.returncode == 0 or 'already exists' in result.stderr.lower():
                print(f"[OK] Dataset subido: {metadata['id']}")
                return metadata['id']
            else:
                print(f"[ERR] Error subiendo dataset: {result.stderr}")
                return None
                
        except subprocess.TimeoutExpired:
            print(f"\n[ERR] Timeout - La subida tardo demasiado")
            return None
        except Exception as e:
            print(f"\n[ERR] Error: {e}")
            return None
        finally:
            if temp_dir.exists():
                shutil.rmtree(temp_dir)

    def push_kernel(self, kernel_dir='kaggle_kernel'):
        """Empuja el kernel a Kaggle usando CLI."""
        print(f"[PUSH] Empujando kernel: {self.kernel_slug}")
        
        kernel_path = Path(kernel_dir)
        if not kernel_path.exists():
            print(f"[ERR] No se encontro: {kernel_path}")
            return False
        
        try:
            result = subprocess.run(
                ['kaggle', 'kernels', 'push', '-p', str(kernel_path)],
                capture_output=True,
                text=True,
                check=True
            )
            print(f"[OK] Kernel empujado")
            print(result.stdout)
            return True
        except subprocess.CalledProcessError as e:
            print(f"[ERR] Error: {e.stderr}")
            return False

    def run_kernel(self, video_url=None, dataset_slug=None, drive_folder_id=None):
        """
        Ejecuta el kernel con parametros.
        
        Args:
            video_url: URL del video (YouTube, Drive, etc.)
            dataset_slug: Slug del dataset con el video (ej: username/dataset)
            drive_folder_id: ID de carpeta de Drive para resultados
        """
        print(f"[RUN] Ejecutando kernel: {self.kernel_slug}")
        if video_url:
            print(f" Video URL: {video_url}")
        if dataset_slug:
            print(f" Dataset: {dataset_slug}")
        
        try:
            kernel_dir = Path('kaggle_kernel')
            config = {
                'video_url': video_url or '',
                'dataset_slug': dataset_slug or '',
                'drive_folder_id': drive_folder_id or ''
            }
            
            config_path = kernel_dir / 'config.json'
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2)
            
            # Leer kernel-metadata.json actual
            kernel_metadata_path = kernel_dir / 'kernel-metadata.json'
            with open(kernel_metadata_path, 'r', encoding='utf-8') as f:
                kernel_meta = json.load(f)
            
            # Reconstruir dataset_sources desde cero para evitar acumular datasets viejos
            dataset_sources = ['joelowtok/openshorts-code']
            
            if dataset_slug and dataset_slug not in dataset_sources:
                dataset_sources.append(dataset_slug)
                print(f"  + Dataset: {dataset_slug}")
            
            kernel_meta['dataset_sources'] = dataset_sources
            
            # Guardar metadata actualizado
            with open(kernel_metadata_path, 'w', encoding='utf-8') as f:
                json.dump(kernel_meta, f, indent=2)
                f.write('\n')
            
            self.push_kernel(str(kernel_dir))
            
            job_id = f"{self.username}-{self.kernel_name}-{int(time.time())}"
            self.job_status[job_id] = {
                'status': 'running',
                'video_url': video_url,
                'dataset_slug': dataset_slug,
                'started_at': datetime.now().isoformat()
            }
            
            print(f"[OK] Kernel iniciado")
            return job_id
            
        except Exception as e:
            print(f"[ERR] Error: {e}")
            return None

    def get_status(self, job_id=None):
        """Obtiene el estado del kernel."""
        try:
            result = subprocess.run(
                ['kaggle', 'kernels', 'status', self.kernel_slug],
                capture_output=True,
                text=True
            )
            return {
                'status': 'running',
                'kernel_slug': self.kernel_slug,
                'raw': result.stdout
            }
        except Exception as e:
            return {'status': 'error', 'error': str(e)}

    def get_output(self, job_id=None, output_dir='./kaggle_results'):
        """Baja el output del kernel."""
        print(f"[DOWN] Bajando output del kernel...")
        
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)
        
        try:
            result = subprocess.run(
                ['kaggle', 'kernels', 'output', self.kernel_slug, '-p', str(output_dir)],
                capture_output=True,
                text=True,
                timeout=120
            )
            
            if output_path.exists():
                files = list(output_path.glob('*'))
                if files:
                    print(f"[OK] Output descargado en: {output_dir}")
                    print(f"    Archivos encontrados: {len(files)}")
                    for f in files:
                        size = f.stat().st_size
                        size_str = f'{size/1024/1024:.1f} MB' if size > 1024*1024 else f'{size/1024:.1f} KB'
                        print(f'      - {f.name}: {size_str}')
                    return output_dir
                else:
                    print(f"[WARN] No se encontraron archivos en {output_dir}")
                    print(f"       El kernel no generó output o no terminó correctamente")
                    return None
            else:
                print(f"[ERR] No se pudo descargar el output")
                return None
                
        except subprocess.TimeoutExpired:
            print(f"[ERR] Timeout al descargar output")
            return None
        except Exception as e:
            print(f"[ERR] Error: {e}")
            print(f"       Revisá en: https://www.kaggle.com/code/{self.kernel_slug}")
            return None

    def wait_for_completion(self, job_id=None, timeout=3600, poll_interval=30):
        """Espera a que el kernel termine."""
        print(f"[WAIT] Esperando completitud...")
        
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            status = self.get_status(job_id)
            print(f" Estado: {status.get('status', 'unknown')}")
            
            if status.get('status') == 'complete':
                print(f"[OK] Completado")
                return True
            elif status.get('status') == 'error':
                print(f"[ERR] Error en kernel")
                return False
            
            time.sleep(poll_interval)
        
        print(f"[TIMEOUT] Timeout")
        return False


def process_video_on_kaggle(video_path, video_url=None, drive_folder_id=None):
    """
    Procesa un video en Kaggle.
    
    Args:
        video_path: Path al video local o URL
        video_url: URL directa (Drive, YouTube)
        drive_folder_id: ID de carpeta de Drive para resultados
        
    Returns:
        job_id o None
    """
    kaggle = KaggleIntegration(username='joelowtok')
    
    if video_url is None:
        if not os.path.exists(video_path):
            print(f"[ERR] Archivo no encontrado: {video_path}")
            return None
        
        kaggle.cleanup_old_datasets('openshorts-input')
        
        dataset_name = f"openshorts-input-{int(time.time())}"
        dataset_slug = kaggle.upload_video_dataset(video_path, dataset_name)
        
        if dataset_slug:
            print(f"[OK] Video subido como dataset: {dataset_slug}")
            job_id = kaggle.run_kernel(dataset_slug=dataset_slug, drive_folder_id=drive_folder_id)
            return job_id
        else:
            print(f"[ERR] Error subiendo video a Kaggle")
            return None
    else:
        job_id = kaggle.run_kernel(video_url=video_url, drive_folder_id=drive_folder_id)
        return job_id


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Procesar video en Kaggle')
    parser.add_argument('video', nargs='?', help='Video a procesar (path o URL)')
    parser.add_argument('--drive-folder', help='Carpeta de Drive para resultados')
    parser.add_argument('--download', action='store_true', help='Bajar resultados del kernel')
    parser.add_argument('--status', action='store_true', help='Ver estado del kernel')
    
    args = parser.parse_args()
    
    kaggle = KaggleIntegration(username='joelowtok')
    
    if args.download:
        kaggle.get_output()
    elif args.status:
        status = kaggle.get_status()
        print(f"Estado: {status.get('status', 'desconocido')}")
    elif args.video:
        job_id = process_video_on_kaggle(args.video, drive_folder_id=getattr(args, 'drive_folder', None))
        
        if job_id:
            print(f"\n[OK] Job iniciado: {job_id}")
            print(f" Monitorear: python kaggle_integration.py status {job_id}")
        else:
            print(f"\n[ERR] Error al iniciar job")
    else:
        print("Usá:")
        print("  python kaggle_integration.py video.mp4       - Procesar video")
        print("  python kaggle_integration.py --download      - Bajar resultados")
        print("  python kaggle_integration.py --status        - Ver estado")
