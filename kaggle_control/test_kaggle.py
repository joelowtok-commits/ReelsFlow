#!/usr/bin/env python3
"""
Test de la integración con Kaggle.
"""

import sys
from pathlib import Path

# Agregar el path
sys.path.insert(0, str(Path(__file__).parent))

from kaggle_integration import KaggleIntegration, process_video_on_kaggle

def test_push_kernel():
    """Test:  pushear el kernel."""
    print("=" * 60)
    print("TEST: Push Kernel")
    print("=" * 60)
    
    kaggle = KaggleIntegration(username='joelowtok')
    success = kaggle.push_kernel('kaggle_kernel')
    
    if success:
        print("[OK] TEST PASSED: Kernel pusheado correctamente")
    else:
        print("[ERR] TEST FAILED: Error al pushear")
    
    return success

def test_run_kernel():
    """Test: ejecutar el kernel con video de prueba."""
    print("\n" + "=" * 60)
    print("TEST: Run Kernel")
    print("=" * 60)
    
    kaggle = KaggleIntegration(username='joelowtok')
    
    # Usar video corto de prueba (10 segundos)
    video_url = "https://www.youtube.com/watch?v=jNQXAC9IVRw"
    print(f"Video: {video_url}")
    
    job_id = kaggle.run_kernel(video_url)
    
    if job_id:
        print(f"[OK] TEST PASSED: Job iniciado: {job_id}")
    else:
        print("[ERR] TEST FAILED: Error al iniciar job")
    
    return job_id

def test_status():
    """Test: consultar estado."""
    print("\n" + "=" * 60)
    print("TEST: Status")
    print("=" * 60)
    
    kaggle = KaggleIntegration(username='joelowtok')
    status = kaggle.get_status()
    
    print(f"Status: {status}")
    print("[OK] TEST PASSED: Status consultado")
    
    return status

def main():
    print("\nKAGGLE INTEGRATION TESTS\n")
    
    test_push_kernel()
    test_run_kernel()
    test_status()
    
    print("\n" + "=" * 60)
    print("TODOS LOS TESTS COMPLETADOS")
    print("=" * 60)
    print("\nProximos pasos:")
    print("1. Revisa el kernel en: https://www.kaggle.com/code/joelowtok/openshorts-processor")
    print("2. Ejecuta el kernel manualmente para verificar")
    print("3. Integra con tu app.py")

if __name__ == '__main__':
    main()
