"""
colab_setup.py — Script para ejecutar en Google Colab con Google Drive.

Instrucciones:
  1. Crea un nuevo cuaderno en Google Colab con GPU T4.
  2. Ejecuta la celda para clonar e instalar:
     !rm -rf ReelsFlow
     !git clone https://github.com/joelowtok-commits/ReelsFlow.git
     !bash ReelsFlow/colab_install.sh
     
  3. Ejecuta el servidor con Google Drive:
  
     !python ReelsFlow/colab_setup.py --authkey "tskey-auth-XXXXX"

  Los videos se leen y escriben en Google Drive:
    /content/drive/MyDrive/OpenShorts/uploads/   ← videos subidos desde Windows
    /content/drive/MyDrive/OpenShorts/output/     ← clips procesados por la GPU

  En tu PC Windows con Google Drive Desktop instalado, la carpeta
  "G:\\Mi unidad\\OpenShorts" se sincroniza automáticamente.
"""

import subprocess
import os
import sys
import time
import argparse


def run(cmd, check=True, shell=True, capture=False):
    """Run a shell command with logging."""
    print(f"  → {cmd}")
    if capture:
        result = subprocess.run(cmd, shell=shell, capture_output=True, text=True)
        return result
    else:
        subprocess.run(cmd, shell=shell, check=check)


def step_mount_drive():
    """Mount Google Drive in Colab."""
    print("\n" + "=" * 60)
    print("📂 STEP 1: Montando Google Drive")
    print("=" * 60)

    drive_base = "/content/drive"
    if os.path.ismount(drive_base) or os.path.exists(os.path.join(drive_base, "MyDrive")):
        print("  ✅ Google Drive ya está montado")
    else:
        try:
            from google.colab import drive
            drive.mount(drive_base)
            print("  ✅ Google Drive montado exitosamente")
        except Exception as e:
            print(f"  ❌ Error montando Google Drive: {e}")
            print("  💡 Asegurate de estar ejecutando esto en Google Colab")
            sys.exit(1)

    # Crear estructura de carpetas en Drive
    drive_openshorts = "/content/drive/MyDrive/OpenShorts"
    uploads_dir = os.path.join(drive_openshorts, "uploads")
    output_dir = os.path.join(drive_openshorts, "output")
    thumbnails_dir = os.path.join(output_dir, "thumbnails")

    os.makedirs(uploads_dir, exist_ok=True)
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(thumbnails_dir, exist_ok=True)

    print(f"  📂 Carpeta de uploads:    {uploads_dir}")
    print(f"  📂 Carpeta de output:     {output_dir}")
    print(f"  📂 Carpeta de thumbnails: {thumbnails_dir}")

    return uploads_dir, output_dir


def step_tailscale(authkey):
    """Install and connect Tailscale."""
    print("\n" + "=" * 60)
    print("📡 STEP 2: Instalando y Conectando Tailscale")
    print("=" * 60)

    # Install
    print("\n📥 Instalando Tailscale...")
    run("curl -fsSL https://tailscale.com/install.sh | sh")

    # Kill any existing daemon
    run("pkill tailscaled || true")
    time.sleep(1)

    # Start daemon in userspace mode
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
    print("📦 STEP 3: Instalando Dependencias y Código")
    print("=" * 60)

    # System packages
    print("\n📦 Paquetes del sistema...")
    run("apt-get update -qq && apt-get install -qq -y ffmpeg btop nvtop", check=False)

    # Clone repo
    work_dir = "/content/OpenShorts"
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
    print("\n🐍 Verificando dependencias...")
    missing = []
    for pkg in ["faster_whisper", "ultralytics", "fastapi", "uvicorn", "yt_dlp", "boto3", "bs4", "mediapipe"]:
        try:
            __import__(pkg)
        except ImportError:
            missing.append(pkg)
    
    if missing:
        print(f"  ⚠️ Faltan paquetes: {', '.join(missing)}")
        print(f"  💡 Ejecutá primero: !bash {os.path.join(work_dir, 'colab_install.sh')}")
        print(f"  Intentando instalar automáticamente...")
        install_script = os.path.join(work_dir, "colab_install.sh")
        if os.path.exists(install_script):
            os.system(f"bash {install_script}")
        else:
            for pkg in missing:
                os.system(f"pip install -q --no-cache-dir {pkg}")
    else:
        print("  ✅ Todas las dependencias están instaladas")

    # Verify GPU
    print("\n🎮 Verificando GPU...")
    result = run("nvidia-smi --query-gpu=name,memory.total --format=csv,noheader", capture=True)
    if result and result.stdout.strip():
        print(f"  ✅ GPU detectada: {result.stdout.strip()}")
    else:
        print("  ⚠️ No se detectó GPU. Asegurate de activar GPU en Colab Settings (Runtime -> Change runtime type).")

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


def step_server(work_dir=None, uploads_dir=None, output_dir=None, gemini_key=None,
                aws_id=None, aws_secret=None, aws_region=None, aws_bucket=None,
                aws_public_bucket=None, aws_endpoint=None):
    """Launch the OpenShorts backend server with Google Drive directories."""
    print("\n" + "=" * 60)
    print("🚀 STEP 4: Lanzando Servidor OpenShorts (con Google Drive)")
    print("=" * 60)

    if not work_dir:
        work_dir = "/content/OpenShorts"

    if not os.path.exists(os.path.join(work_dir, "app.py")):
        print(f"  ❌ No se encontró app.py en {work_dir}")
        print("  💡 Asegurate de clonar el repo primero (--step install --repo ...)")
        return

    # Set environment variables
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env["KMP_DUPLICATE_LIB_OK"] = "TRUE"

    # ★ Google Drive directories — this is the key change!
    if uploads_dir:
        env["UPLOAD_DIR"] = uploads_dir
        print(f"  📂 UPLOAD_DIR = {uploads_dir}")
    if output_dir:
        env["OUTPUT_DIR"] = output_dir
        print(f"  📂 OUTPUT_DIR = {output_dir}")
    
    if gemini_key:
        env["GEMINI_API_KEY"] = gemini_key
        print(f"  ✅ GEMINI_API_KEY configurada")

    if aws_id:
        env["AWS_ACCESS_KEY_ID"] = aws_id
        print("  ✅ AWS_ACCESS_KEY_ID configurada")
    if aws_secret:
        env["AWS_SECRET_ACCESS_KEY"] = aws_secret
        print("  ✅ AWS_SECRET_ACCESS_KEY configurada")
    if aws_region:
        env["AWS_REGION"] = aws_region
    if aws_bucket:
        env["AWS_S3_BUCKET"] = aws_bucket
    if aws_public_bucket:
        env["AWS_S3_PUBLIC_BUCKET"] = aws_public_bucket
    if aws_endpoint:
        env["AWS_ENDPOINT_URL"] = aws_endpoint
        print("  ✅ AWS_ENDPOINT_URL configurada")

    # Expose port via Tailscale (solo para la API HTTP, no para transferir archivos pesados)
    print("\n🌐 Exponiendo puerto 8000 via Tailscale (solo API, archivos van por Drive)...")
    run("tailscale serve --bg --tcp=8000 tcp://localhost:8000", check=False)
    time.sleep(2)

    # Get Tailscale IP
    result = run("tailscale ip -4", capture=True)
    ts_ip = result.stdout.strip() if result and result.stdout.strip() else "100.x.x.x"

    print(f"\n{'=' * 60}")
    print(f"✅ TODO LISTO! — MODO GOOGLE DRIVE ACTIVO")
    print(f"{'=' * 60}")
    print(f"\n📂 Archivos van por Google Drive (NO por red):")
    print(f"   Uploads: {uploads_dir}")
    print(f"   Output:  {output_dir}")
    print(f"\n🌐 API Tailscale: http://{ts_ip}:8000 (solo comandos JSON)")
    print(f"\n📋 En tu PC Windows:")
    print(f"   1. Asegurate de tener Google Drive Desktop instalado")
    print(f"   2. Edita tu .env y pone:")
    print(f"      GOOGLE_DRIVE_PATH=G:\\Mi unidad\\OpenShorts")
    print(f"      VITE_BACKEND_URL=http://{ts_ip}:8000")
    print(f"   3. Ejecuta:")
    print(f"      cd E:\\PROYECTOS_PY\\OpenShorts\\1.1")
    print(f"      python auto_connect_colab.py")
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


def run_all(authkey, repo=None, gemini_key=None, aws_id=None, aws_secret=None,
            aws_region=None, aws_bucket=None, aws_public_bucket=None, aws_endpoint=None):
    """Run all steps sequentially."""
    print("\n" + "=" * 60)
    print("🚀 OpenShorts — Colab GPU Backend Setup (Google Drive Mode)")
    print("=" * 60)

    # Step 1: Mount Google Drive
    uploads_dir, output_dir = step_mount_drive()

    # Step 2: Tailscale (solo para API HTTP)
    ts_ip = step_tailscale(authkey)

    # Step 3: Install
    work_dir = step_install(repo)

    # Step 4: Server (blocking) — usando directorios de Google Drive
    step_server(work_dir, uploads_dir, output_dir, gemini_key,
                aws_id, aws_secret, aws_region, aws_bucket, aws_public_bucket, aws_endpoint)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="OpenShorts Colab Setup (Google Drive Mode)")
    parser.add_argument("--step", choices=["drive", "tailscale", "install", "server", "all"],
                        default="all", help="Which step to run")
    parser.add_argument("--authkey", default="tskey-auth-kY5UFMnc4n11CNTRL-FP8hox4LH2jUNR4Ma28s1jY7WWVuwVDBU", help="Tailscale Auth Key")
    parser.add_argument("--repo", type=str, default="joelowtok-commits/ReelsFlow", help="GitHub repo (user/repo)")
    parser.add_argument("--gemini-key", type=str, help="Gemini API Key")
    parser.add_argument("--workdir", type=str, default="/content/OpenShorts",
                        help="Working directory")
    parser.add_argument("--aws-id", type=str, help="AWS Access Key ID")
    parser.add_argument("--aws-secret", type=str, help="AWS Secret Access Key")
    parser.add_argument("--aws-region", type=str, default="eu-west-3", help="AWS Region")
    parser.add_argument("--aws-bucket", type=str, default="my-clips-bucket", help="AWS Private S3 Bucket")
    parser.add_argument("--aws-public-bucket", type=str, default="my-public-bucket", help="AWS Public S3 Bucket")
    parser.add_argument("--aws-endpoint", type=str, help="AWS S3-compatible Endpoint URL (e.g. for Cloudflare R2)")
    args, _ = parser.parse_known_args()

    if args.step == "all":
        if not args.authkey:
            print("❌ --authkey es obligatorio para el setup completo")
            print("   Uso: python colab_setup.py --authkey 'tskey-auth-XXXXX'")
            sys.exit(1)
        run_all(args.authkey, args.repo, args.gemini_key, args.aws_id, args.aws_secret,
                args.aws_region, args.aws_bucket, args.aws_public_bucket, args.aws_endpoint)

    elif args.step == "drive":
        step_mount_drive()

    elif args.step == "tailscale":
        if not args.authkey:
            print("❌ --authkey es obligatorio")
            sys.exit(1)
        step_tailscale(args.authkey)

    elif args.step == "install":
        step_install(args.repo)

    elif args.step == "server":
        # For standalone server step, mount drive first for directories
        uploads_dir, output_dir = step_mount_drive()
        step_server(args.workdir, uploads_dir, output_dir, args.gemini_key,
                    args.aws_id, args.aws_secret, args.aws_region, args.aws_bucket,
                    args.aws_public_bucket, args.aws_endpoint)
