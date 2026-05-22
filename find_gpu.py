#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Find Colab GPU machine via Tailscale and launch dashboard.
"""
import os
import sys
import json
import subprocess

# Set UTF-8 encoding for Windows
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

def get_tailscale_status():
    """Get Tailscale status as JSON."""
    try:
        result = subprocess.run(['tailscale', 'status', '--json'], 
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            return json.loads(result.stdout)
    except Exception as e:
        print(f"Error getting Tailscale status: {e}")
    return None

def find_gpu_machine(status):
    """Find a GPU machine in Tailscale status."""
    HOSTNAMES_TO_FIND = ['reelsflow', 'colab-gpu', 'colab', 'kaggle-gpu', 'gpu']
    peers = status.get("Peer", {})
    
    for key, info in peers.items():
        hostname = info.get("HostName", "")
        online = info.get("Online", False)
        ips = info.get("TailscaleIPs", [])
        
        if online and any(h.lower() in hostname.lower() for h in HOSTNAMES_TO_FIND):
            return ips[0] if ips else None, hostname
    
    return None, None

def main():
    print("=" * 60)
    print("OpenShorts - Finding Colab GPU")
    print("=" * 60)
    
    # 1. Check Tailscale
    status = get_tailscale_status()
    if not status:
        print("No se pudo obtener el estado de Tailscale.")
        print("Asegurate de que Tailscale este corriendo:")
        print("  tailscale status")
        sys.exit(1)
    
    # 2. Find GPU machine
    gpu_ip, gpu_hostname = find_gpu_machine(status)
    
    if not gpu_ip:
        print("\nNo se encontro ninguna GPU remota en Tailscale")
        print("Buscando: reelsflow, colab-gpu, colab, kaggle-gpu, gpu")
        print("\nMaquinas disponibles:")
        peers = status.get("Peer", {})
        if peers:
            for key, info in peers.items():
                hostname = info.get("HostName", "N/A")
                online = "[ON]" if info.get("Online") else "[OFF]"
                ips = info.get("TailscaleIPs", [])
                print(f"  {online} {hostname} ({ips[0] if ips else 'N/A'})")
        else:
            print("  (no hay peers conectados)")
        print("\nAsegurate de que:")
        print("  1. El notebook de Colab este ejecutandose")
        print("  2. Ambas maquinas esten en la misma cuenta de Tailscale")
        sys.exit(1)
    
    print(f"GPU encontrada: {gpu_hostname} -> {gpu_ip}")
    
    # 3. Verify backend
    print(f"\nVerificando backend en http://{gpu_ip}:8000 ...")
    try:
        import urllib.request
        req = urllib.request.Request(f"http://{gpu_ip}:8000/api/system-info", method='GET')
        with urllib.request.urlopen(req, timeout=5) as resp:
            sys_info = json.loads(resp.read().decode())
            gpu = sys_info.get("gpu", "No GPU")
            print(f" Backend ONLINE - {gpu}")
    except Exception as e:
        print(f" Backend no responde: {e}")
        print("Espera 1-2 minutos y volvi a intentar.")
    
    # 4. Launch dashboard
    print(f"\nLanzando dashboard apuntando a Colab GPU...")
    print(f"  Backend: http://{gpu_ip}:8000")
    print(f"  Sync worker: iniciado")
    
    dashboard_dir = os.path.join(os.path.dirname(__file__), "dashboard")
    env = os.environ.copy()
    env["VITE_BACKEND_URL"] = f"http://{gpu_ip}:8000"
    
    # Start dashboard
    subprocess.run(
        ["npm", "run", "dev"],
        cwd=dashboard_dir,
        env=env,
        shell=True
    )

if __name__ == "__main__":
    main()
