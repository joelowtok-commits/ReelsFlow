#!/usr/bin/env python3
"""Script para subir el kernel a Kaggle usando la API directamente"""
import os
from pathlib import Path
from kaggle.api.kaggle_api_extended import KaggleApi

kernel_dir = Path(__file__).parent / 'kaggle_kernel'

print(f"Subiendo kernel desde: {kernel_dir}")
print("=" * 50)

# Inicializar API
api = KaggleApi()
api.authenticate()

print("[OK] Autenticación exitosa")

# Push del kernel
try:
    api.kernels_push(str(kernel_dir))
    print("\n[OK] Kernel subido exitosamente!")
    print("Ver en: https://www.kaggle.com/joelowtok/openshorts-processor")
except Exception as e:
    print(f"\n[ERR] Error: {e}")
    import sys
    sys.exit(1)
