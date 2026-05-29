#!/usr/bin/env python3
"""
Test de subida de video local a Kaggle.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from kaggle_integration import KaggleIntegration, process_video_on_kaggle

def test_upload_video():
    """Test: subir video como dataset."""
    print("=" * 60)
    print("TEST: Upload Video Dataset")
    print("=" * 60)
    
    test_video = Path('test_video.mp4')
    if not test_video.exists():
        print(f"[SKIP] No hay video de test: {test_video}")
        print("  Crear un archivo test_video.mp4 para probar")
        return None
    
    kaggle = KaggleIntegration(username='joelowtok')
    dataset_slug = kaggle.upload_video_dataset(str(test_video), 'openshorts-input-test')
    
    if dataset_slug:
        print(f"[OK] Dataset subido: {dataset_slug}")
    else:
        print("[ERR] Error subiendo dataset")
    
    return dataset_slug

def test_process_local_video():
    """Test: procesar video local completo."""
    print("\n" + "=" * 60)
    print("TEST: Process Local Video (Full Flow)")
    print("=" * 60)
    
    test_video = Path('test_video.mp4')
    if not test_video.exists():
        print(f"[SKIP] No hay video de test: {test_video}")
        return None
    
    print(f"Video: {test_video}")
    
    job_id = process_video_on_kaggle(str(test_video))
    
    if job_id:
        print(f"[OK] Job iniciado: {job_id}")
        print(f"  Ver en: https://www.kaggle.com/code/joelowtok/openshorts-processor")
    else:
        print("[ERR] Error iniciando job")
    
    return job_id

def main():
    print("\nKAGGLE LOCAL VIDEO TEST\n")
    
    test_upload_video()
    test_process_local_video()
    
    print("\n" + "=" * 60)
    print("TEST COMPLETADO")
    print("=" * 60)

if __name__ == '__main__':
    main()
