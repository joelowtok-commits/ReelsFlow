#!/usr/bin/env python3
"""
Control total del kernel de Kaggle.
Prender, apagar, configurar GPU, persistencia, etc.
"""

import json
import subprocess
from pathlib import Path

KERNEL_META = Path('kaggle_kernel/kernel-metadata.json')

def load_config():
    """Carga la configuracion actual del kernel."""
    with open(KERNEL_META, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_config(config):
    """Guarda la configuracion del kernel."""
    with open(KERNEL_META, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2)
        f.write('\n')

def show_config():
    """Muestra la configuracion actual."""
    config = load_config()
    
    print("\n" + "=" * 60)
    print("CONFIGURACION DEL KERNEL")
    print("=" * 60)
    print(f"ID: {config['id']}")
    print(f"Titulo: {config['title']}")
    print(f"Tipo: {config['kernel_type']}")
    print()
    print("HARDWARE:")
    print(f"  [1] GPU: {'ACTIVADA' if config['enable_gpu'] else 'DESACTIVADA'}")
    print(f"  [2] TPU: {'ACTIVADA' if config['enable_tpu'] else 'DESACTIVADA'}")
    print()
    print("ACCESO:")
    print(f"  [3] Privado: {'SI' if config['is_private'] else 'NO (PUBLICO)'}")
    print(f"  [4] Internet: {'ACTIVADO' if config['enable_internet'] else 'DESACTIVADO'}")
    print()
    print("DATASETS:")
    if config['dataset_sources']:
        for i, ds in enumerate(config['dataset_sources'], 5):
            print(f"  [{i}] {ds}")
    else:
        print("  (ninguno)")
    print()
    print("PERSISTENCIA:")
    print("  Los archivos en /kaggle/working/ se guardan MIENTRAS")
    print("  el kernel este corriendo. Se borran al terminar.")
    print("  Para guardar permanente: subir a Drive o S3")
    print("=" * 60)

def toggle_gpu():
    """Activa/desactiva GPU."""
    config = load_config()
    config['enable_gpu'] = not config['enable_gpu']
    save_config(config)
    print(f"GPU {'ACTIVADA' if config['enable_gpu'] else 'DESACTIVADA'}")
    print("  El cambio se aplica la proxima vez que ejecutes el kernel")

def toggle_tpu():
    """Activa/desactiva TPU."""
    config = load_config()
    config['enable_tpu'] = not config['enable_tpu']
    save_config(config)
    print(f"TPU {'ACTIVADA' if config['enable_tpu'] else 'DESACTIVADA'}")
    print("  El cambio se aplica la proxima vez que ejecutes el kernel")

def toggle_private():
    """Cambia entre privado/publico."""
    config = load_config()
    config['is_private'] = not config['is_private']
    save_config(config)
    print(f"Kernel {'PRIVADO' if config['is_private'] else 'PUBLICO'}")
    print("  El cambio se aplica la proxima vez que hagas push")

def toggle_internet():
    """Activa/desactiva internet."""
    config = load_config()
    config['enable_internet'] = not config['enable_internet']
    save_config(config)
    print(f"Internet {'ACTIVADO' if config['enable_internet'] else 'DESACTIVADO'}")
    print("  El cambio se aplica la proxima vez que ejecutes el kernel")

def add_dataset():
    """Agrega un dataset."""
    print("\nIngresa el slug del dataset (ej: joelowtok/mi-dataset):")
    slug = input("> ").strip()
    if not slug:
        return
    
    config = load_config()
    if slug not in config['dataset_sources']:
        config['dataset_sources'].append(slug)
        save_config(config)
        print(f"Dataset {slug} AGREGADO")
    else:
        print(f"Dataset {slug} YA EXISTE")

def remove_dataset():
    """Elimina un dataset."""
    config = load_config()
    if not config['dataset_sources']:
        print("No hay datasets para eliminar")
        return
    
    print("\nDatasets disponibles:")
    for i, ds in enumerate(config['dataset_sources']):
        print(f"  [{i+1}] {ds}")
    print(f"  [0] Cancelar")
    
    try:
        opt = int(input("\nNumero a eliminar: "))
        if opt > 0 and opt <= len(config['dataset_sources']):
            removed = config['dataset_sources'].pop(opt - 1)
            save_config(config)
            print(f"Dataset {removed} ELIMINADO")
    except (ValueError, IndexError):
        print("Opcion invalida")

def push_kernel():
    """Hace push del kernel a Kaggle."""
    print("\nEmpujando kernel a Kaggle...")
    result = subprocess.run(
        ['kaggle', 'kernels', 'push', '-p', 'kaggle_kernel'],
        capture_output=True,
        text=True
    )
    if result.returncode == 0:
        print("[OK] Kernel pusheado")
        print(result.stdout)
    else:
        print(f"[ERR] Error: {result.stderr}")

def run_kernel():
    """Ejecuta el kernel en Kaggle."""
    print("\nEjecutando kernel en Kaggle...")
    result = subprocess.run(
        ['kaggle', 'kernels', 'run', 'joelowtok/openshorts-processor'],
        capture_output=True,
        text=True
    )
    if result.returncode == 0:
        print("[OK] Kernel iniciado")
        print("Ver en: https://www.kaggle.com/code/joelowtok/openshorts-processor")
    else:
        print(f"[ERR] Error: {result.stderr}")

def status_kernel():
    """Muestra el estado del kernel."""
    result = subprocess.run(
        ['kaggle', 'kernels', 'status', 'joelowtok/openshorts-processor'],
        capture_output=True,
        text=True
    )
    print(result.stdout)

def main_menu():
    """Menu principal."""
    while True:
        print("\n" + "=" * 60)
        print("KAGGLE KERNEL CONTROL")
        print("=" * 60)
        print("[1] Mostrar configuracion")
        print("[2] GPU (prender/apagar)")
        print("[3] TPU (prender/apagar)")
        print("[4] Privado/Publico")
        print("[5] Internet (prender/apagar)")
        print("[6] Agregar dataset")
        print("[7] Eliminar dataset")
        print("[8] Push del kernel")
        print("[9] Ejecutar kernel")
        print("[10] Estado del kernel")
        print("[0] Salir")
        print("=" * 60)
        
        try:
            opt = input("Opcion: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nSaliendo...")
            break
        
        if opt == '1':
            show_config()
        elif opt == '2':
            toggle_gpu()
        elif opt == '3':
            toggle_tpu()
        elif opt == '4':
            toggle_private()
        elif opt == '5':
            toggle_internet()
        elif opt == '6':
            add_dataset()
        elif opt == '7':
            remove_dataset()
        elif opt == '8':
            push_kernel()
        elif opt == '9':
            run_kernel()
        elif opt == '10':
            status_kernel()
        elif opt == '0':
            print("Saliendo...")
            break
        else:
            print("Opcion invalida")

if __name__ == '__main__':
    main_menu()
