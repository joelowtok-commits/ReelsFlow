"""
kaggle_setup.py — Script para ejecutar en Kaggle Notebook.

Instrucciones:
  1. Crea un nuevo Notebook en Kaggle con GPU T4 x2
  2. Sube este archivo al notebook o copia el contenido en una celda
  3. Ejecuta: !python kaggle_setup.py --authkey "tskey-auth-XXXXX" --repo "joelowtok-commits/ReelsFlow"
  
  O en celdas separadas:
    Celda 1: !python kaggle_setup.py --step tailscale --authkey "tskey-auth-XXXXX"
    Celda 2: !python kaggle_setup.py --step install --repo "tu-usuario/OpenShorts"
    Celda 3: !python kaggle_setup.py --step server
"""

import subprocess
import os
import sys
import time
import argparse
import json


def run(cmd, check=True, shell=True, capture=False):
    """Run a shell command with logging."""
    print(f"  → {cmd}")
    if capture:
        result = subprocess.run(cmd, shell=shell, capture_output=True, text=True)
        return result
    else:
        subprocess.run(cmd, shell=shell, check=check)


def step_tailscale(authkey):
    """Install and connect Tailscale."""
    print("\n" + "=" * 60)
    print("📡 STEP 1: Instalando y Conectando Tailscale")
    print("=" * 60)

    # Install
    print("\n📥 Instalando Tailscale...")
    run("curl -fsSL https://tailscale.com/install.sh | sh")

    # Kill any existing daemon
    run("pkill tailscaled || true")
    time.sleep(1)

    # Start daemon in userspace mode (Kaggle doesn't allow tun devices)
    print("\n🚀 Iniciando Tailscale daemon...")
    subprocess.Popen(
        "nohup tailscaled --tun=userspace-networking "
        "--socks5-server=localhost:1055 "
        "> /tmp/tailscaled.log 2>&1 &",
        shell=True
    )
    time.sleep(3)

    # Connect
    print("\n🔗 Conectando a Tailscale...")
    run(f'tailscale up --authkey="{authkey}" --hostname=reelsflow --ssh --reset')

    print("\n✅ Tailscale conectado!")
    run("tailscale status")

    # Get our IP
    result = run("tailscale ip -4", capture=True)
    if result and result.stdout.strip():
        print(f"\n🌐 Tu IP de Tailscale: {result.stdout.strip()}")
        return result.stdout.strip()
    return None


def step_install(repo=None):
    """Install dependencies and clone repo."""
    print("\n" + "=" * 60)
    print("📦 STEP 2: Instalando Dependencias y Código")
    print("=" * 60)

    # System packages
    print("\n📦 Paquetes del sistema...")
    run("apt-get update -qq && apt-get install -qq -y ffmpeg", check=False)

    # Clone repo
    work_dir = "/kaggle/working/OpenShorts"
    if repo:
        print(f"\n📂 Clonando repo: {repo}")
        if os.path.exists(work_dir):
            run(f"rm -rf {work_dir}")
        run(f'git clone https://github.com/{repo}.git {work_dir}')
    else:
        print(f"\n📂 Usando directorio existente: {work_dir}")
        if not os.path.exists(work_dir):
            os.makedirs(work_dir, exist_ok=True)
            print("  ⚠️ Directorio vacío. Sube los archivos manualmente o usa --repo")
            return work_dir

    # Install Python dependencies
    print("\n🐍 Instalando dependencias Python (GPU)...")
    req_file = os.path.join(work_dir, "requirements-kaggle.txt")
    if os.path.exists(req_file):
        run(f"pip install -q -r {req_file}")
    else:
        # Fallback to regular requirements
        req_file = os.path.join(work_dir, "requirements.txt")
        if os.path.exists(req_file):
            run(f"pip install -q -r {req_file}")

    # Verify GPU
    print("\n🎮 Verificando GPU...")
    result = run("nvidia-smi --query-gpu=name,memory.total --format=csv,noheader", capture=True)
    if result and result.stdout.strip():
        print(f"  ✅ GPU detectada: {result.stdout.strip()}")
    else:
        print("  ⚠️ No se detectó GPU. Asegurate de activar GPU en Kaggle Settings.")

    # Verify torch CUDA
    try:
        import torch
        if torch.cuda.is_available():
            print(f"  ✅ PyTorch CUDA: {torch.cuda.get_device_name(0)}")
        else:
            print("  ⚠️ PyTorch no detecta CUDA")
    except ImportError:
        print("  ⚠️ PyTorch no instalado")

    return work_dir


def step_server(work_dir=None, gemini_key=None):
    """Launch the OpenShorts backend server."""
    print("\n" + "=" * 60)
    print("🚀 STEP 3: Lanzando Servidor OpenShorts")
    print("=" * 60)

    if not work_dir:
        work_dir = "/kaggle/working/OpenShorts"

    if not os.path.exists(os.path.join(work_dir, "app.py")):
        print(f"  ❌ No se encontró app.py en {work_dir}")
        print("  💡 Asegurate de clonar el repo primero (--step install --repo ...)")
        return

    # Set environment variables
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env["KMP_DUPLICATE_LIB_OK"] = "TRUE"
    
    if gemini_key:
        env["GEMINI_API_KEY"] = gemini_key
        print(f"  ✅ GEMINI_API_KEY configurada")

    # Expose port via Tailscale
    print("\n🌐 Exponiendo puerto 8000 via Tailscale...")
    run("tailscale serve --bg --tcp=8000 tcp://localhost:8000", check=False)
    time.sleep(2)

    # Get Tailscale IP
    result = run("tailscale ip -4", capture=True)
    ts_ip = result.stdout.strip() if result and result.stdout.strip() else "100.x.x.x"

    print(f"\n{'=' * 60}")
    print(f"✅ TODO LISTO!")
    print(f"{'=' * 60}")
    print(f"\n🌐 Backend URL: http://{ts_ip}:8000")
    print(f"\n📋 En tu PC Windows, ejecutá:")
    print(f"   cd E:\\PROYECTOS_PY\\OpenShorts\\1.1")
    print(f"   python auto_connect_kaggle.py")
    print(f"\n   O manualmente:")
    print(f"   cd dashboard")
    print(f"   set VITE_BACKEND_URL=http://{ts_ip}:8000")
    print(f"   npm run dev")
    print(f"\n{'=' * 60}")
    print(f"🖥️  Iniciando servidor... (Ctrl+C para detener)")
    print(f"{'=' * 60}\n")

    # Launch uvicorn (blocking — keeps the notebook cell alive)
    os.chdir(work_dir)
    subprocess.run(
        [sys.executable, "-m", "uvicorn", "app:app",
         "--host", "0.0.0.0", "--port", "8000",
         "--log-level", "info"],
        env=env,
        cwd=work_dir
    )


def run_all(authkey, repo=None, gemini_key=None):
    """Run all steps sequentially."""
    print("\n" + "=" * 60)
    print("🚀 OpenShorts — Kaggle GPU Backend Setup")
    print("=" * 60)

    # Step 1
    ts_ip = step_tailscale(authkey)

    # Step 2
    work_dir = step_install(repo)

    # Step 3 (blocking)
    step_server(work_dir, gemini_key)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="OpenShorts Kaggle Setup")
    parser.add_argument("--step", choices=["tailscale", "install", "server", "all"],
                        default="all", help="Which step to run")
    parser.add_argument("--authkey", type=str, help="Tailscale Auth Key")
    parser.add_argument("--repo", type=str, help="GitHub repo (user/repo)")
    parser.add_argument("--gemini-key", type=str, help="Gemini API Key")
    parser.add_argument("--workdir", type=str, default="/kaggle/working/OpenShorts",
                        help="Working directory")
    args = parser.parse_args()

    if args.step == "all":
        if not args.authkey:
            print("❌ --authkey es obligatorio para el setup completo")
            print("   Uso: python kaggle_setup.py --authkey 'tskey-auth-XXXXX' --repo 'user/OpenShorts'")
            sys.exit(1)
        run_all(args.authkey, args.repo, args.gemini_key)

    elif args.step == "tailscale":
        if not args.authkey:
            print("❌ --authkey es obligatorio")
            sys.exit(1)
        step_tailscale(args.authkey)

    elif args.step == "install":
        step_install(args.repo)

    elif args.step == "server":
        step_server(args.workdir, args.gemini_key)
