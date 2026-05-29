#!/usr/bin/env python3
"""
Verificar hardware del kernel en Kaggle.
Agrega esto al inicio de tu kernel para ver qué hardware tenés.
"""

import subprocess
import sys

print("=" * 60)
print("HARDWARE REPORT - Kaggle Kernel")
print("=" * 60)

# GPU Info
print("\n1. GPU Detection:")
print("-" * 40)
try:
    result = subprocess.run(['nvidia-smi', '--query-gpu=name,memory.total,memory.free,memory.used', 
                           '--format=csv,noheader'], 
                          capture_output=True, text=True, timeout=10)
    if result.returncode == 0:
        print(f"GPU Detectada: {result.stdout.strip()}")
    else:
        print("No GPU detected or nvidia-smi not available")
except Exception as e:
    print(f"Error checking GPU: {e}")

# CPU Info
print("\n2. CPU Detection:")
print("-" * 40)
try:
    result = subprocess.run(['cat', '/proc/cpuinfo'], capture_output=True, text=True, timeout=10)
    if result.returncode == 0:
        lines = result.stdout.split('\n')
        model_line = [l for l in lines if 'model name' in l]
        if model_line:
            print(f"CPU: {model_line[0].split(':')[1].strip()}")
        
        cores = len([l for l in lines if 'processor' in l])
        print(f"Cores: {cores}")
    else:
        print("CPU info not available")
except Exception as e:
    print(f"Error checking CPU: {e}")

# RAM Info
print("\n3. RAM Detection:")
print("-" * 40)
try:
    result = subprocess.run(['free', '-h'], capture_output=True, text=True, timeout=10)
    if result.returncode == 0:
        print(result.stdout.strip())
    else:
        print("RAM info not available")
except Exception as e:
    print(f"Error checking RAM: {e}")

# Disk Info
print("\n4. Disk Space:")
print("-" * 40)
try:
    result = subprocess.run(['df', '-h', '/kaggle'], capture_output=True, text=True, timeout=10)
    if result.returncode == 0:
        print(result.stdout.strip())
    else:
        print("Disk info not available")
except Exception as e:
    print(f"Error checking disk: {e}")

print("\n" + "=" * 60)
print("End Hardware Report")
print("=" * 60)
