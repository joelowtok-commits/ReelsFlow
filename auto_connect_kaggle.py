"""
auto_connect_kaggle.py — Auto-detecta 'kaggle-gpu' en Tailscale y configura el proxy.

Uso:
    python auto_connect_kaggle.py
    
Esto busca la máquina 'kaggle-gpu' en tu red Tailscale, obtiene su IP,
y lanza el dashboard apuntando al backend remoto automáticamente.
"""
import subprocess
import json
import sys
import os
import codecs

# Configurar encoding UTF-8 para Windows
if sys.platform == 'win32':
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

HOSTNAMES_TO_FIND = ["reelsflow", "kaggle-gpu", "colab-gpu", "colab"]


def get_tailscale_status():
    """Obtiene el estado de Tailscale en JSON."""
    try:
        result = subprocess.run(
            ["tailscale", "status", "--json"],
            capture_output=True, text=True, timeout=10, encoding='utf-8'
        )
        return json.loads(result.stdout)
    except FileNotFoundError:
        print("❌ Tailscale no está instalado o no está en el PATH")
        print("   Descargalo desde: https://tailscale.com/download")
        return None
    except Exception as e:
        print(f"❌ Error al obtener estado de Tailscale: {e}")
        return None


def find_gpu_machine(status_data):
    """Busca kaggle-gpu o colab-gpu en los peers de Tailscale."""
    if not status_data:
        return None, None

    peers = status_data.get("Peer", {})
    for nodekey, peer_info in peers.items():
        hostname = peer_info.get("HostName", "").lower()
        for target in HOSTNAMES_TO_FIND:
            if target in hostname:
                if peer_info.get("Online", False):
                    tailscale_ips = peer_info.get("TailscaleIPs", [])
                    if tailscale_ips:
                        return tailscale_ips[0], peer_info.get("HostName", "unknown")
    return None, None


def verify_backend(ip):
    """Verifica que el backend de OpenShorts esté corriendo en la IP remota."""
    import urllib.request
    try:
        url = f"http://{ip}:8000/api/system-info"
        req = urllib.request.Request(url, method='GET')
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode())
            return data
    except Exception:
        return None


def main():
    print("=" * 60)
    print("🔍 OpenShorts — Auto Connect Kaggle GPU")
    print("=" * 60)

    # 1. Check Tailscale
    status = get_tailscale_status()
    if not status:
        sys.exit(1)

    self_info = status.get("Self", {})
    if not self_info:
        print("❌ No estás conectado a Tailscale. Ejecutá: tailscale up")
        sys.exit(1)

    my_hostname = self_info.get("HostName", "unknown")
    my_ips = self_info.get("TailscaleIPs", [])
    print(f"✅ Tu máquina: {my_hostname} ({my_ips[0] if my_ips else 'N/A'})")

    # 2. Find GPU machine
    gpu_ip, gpu_hostname = find_gpu_machine(status)

    if not gpu_ip:
        print(f"\n❌ No se encontró ninguna GPU remota en Tailscale")
        print(f"   Buscando: {', '.join(HOSTNAMES_TO_FIND)}")
        print("\n📋 Máquinas disponibles:")
        peers = status.get("Peer", {})
        if peers:
            for key, info in peers.items():
                hostname = info.get("HostName", "N/A")
                online = "🟢" if info.get("Online") else "🔴"
                ips = info.get("TailscaleIPs", [])
                print(f"   {online} {hostname} ({ips[0] if ips else 'N/A'})")
        else:
            print("   (no hay peers conectados)")

        print("\n💡 Asegurate de que:")
        print("   1. El notebook de Kaggle esté ejecutándose")
        print("   2. Ambas máquinas estén en la misma cuenta de Tailscale")
        sys.exit(1)

    print(f"✅ GPU encontrada: {gpu_hostname} → {gpu_ip}")

    # 3. Verify backend is running
    print(f"\n🔗 Verificando backend en http://{gpu_ip}:8000 ...")
    sys_info = verify_backend(gpu_ip)

    if sys_info:
        gpu = sys_info.get("gpu", "No GPU detected")
        ram = sys_info.get("total_ram_gb", "?")
        cores = sys_info.get("cpu_cores", "?")
        platform = sys_info.get("platform", "?")
        print(f"   ✅ Backend ONLINE")
        print(f"   🖥️  Plataforma: {platform}")
        print(f"   🧠 CPU Cores: {cores}")
        print(f"   💾 RAM: {ram} GB")
        print(f"   🎮 GPU: {gpu}")
    else:
        print(f"   ⚠️  Backend no responde aún. Puede estar arrancando...")
        print(f"   💡 Esperá 1-2 minutos y volvé a intentar.")

    # 4. Show how to use
    print(f"\n{'=' * 60}")
    print(f"🚀 Para usar OpenShorts con Kaggle GPU:")
    print(f"{'=' * 60}")
    print(f"\n   cd dashboard")
    print(f"   set VITE_BACKEND_URL=http://{gpu_ip}:8000")
    print(f"   npm run dev")
    print(f"\n   O en una sola línea (PowerShell):")
    print(f"   $env:VITE_BACKEND_URL='http://{gpu_ip}:8000'; npm run dev")
    print(f"\n{'=' * 60}")

    # 5. Ask if user wants to launch automatically
    try:
        answer = input("\n¿Lanzar el dashboard ahora? (s/n): ").strip().lower()
        if answer in ('s', 'si', 'y', 'yes', ''):
            print(f"\n🚀 Lanzando dashboard apuntando a Kaggle GPU...")
            dashboard_dir = os.path.join(os.path.dirname(__file__), "dashboard")
            env = os.environ.copy()
            env["VITE_BACKEND_URL"] = f"http://{gpu_ip}:8000"
            subprocess.run(
                ["npm", "run", "dev"],
                cwd=dashboard_dir,
                env=env,
                shell=True
            )
    except KeyboardInterrupt:
        print("\n\n👋 Cancelado. Usá los comandos de arriba para lanzar manualmente.")


if __name__ == "__main__":
    main()
