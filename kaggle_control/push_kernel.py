#!/usr/bin/env python3
"""Script para subir el kernel a Kaggle con encoding UTF-8"""
import subprocess
import sys
from pathlib import Path

kernel_dir = Path(__file__).parent / 'kaggle_kernel'

print(f"Subiendo kernel desde: {kernel_dir}")
print("=" * 50)

# Usar subprocess con encoding
result = subprocess.run(
    ['kaggle', 'kernels', 'push', '-p', str(kernel_dir)],
    capture_output=False,
    text=True,
    encoding='utf-8',
    errors='replace'
)

if result.returncode == 0:
    print("\n[OK] Kernel subido exitosamente!")
else:
    print(f"\n[ERR] Error al subir el kernel")
    sys.exit(1)
