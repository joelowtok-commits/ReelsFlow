"""
auto_connect_colab.py — Auto-detecta 'reelsflow' (o colab-gpu) en Tailscale y configura el proxy.

Uso:
    python auto_connect_colab.py
    
Esto busca la máquina 'reelsflow' en tu red Tailscale, obtiene su IP,
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

HOSTNAMES_TO_FIND = ["reelsflow", "colab-gpu", "colab", "kaggle-gpu"]


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
    """Busca reelsflow o colab-gpu en los peers de Tailscale."""
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


def sync_worker(gpu_ip):
    """Background worker to automatically sync completed jobs from Colab to Windows local output/."""
    import time
    import urllib.request
    import urllib.error

    local_output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")
    os.makedirs(local_output_dir, exist_ok=True)

    synced_jobs_file = os.path.join(local_output_dir, "synced_jobs.json")
    synced_jobs = set()
    if os.path.exists(synced_jobs_file):
        try:
            with open(synced_jobs_file, "r") as f:
                synced_jobs = set(json.load(f))
        except Exception:
            pass

    print(f"\n🔄 [Sync Daemon] Sistema de auto-sincronización iniciado por Tailscale.")
    print(f"🔄 [Sync Daemon] Escuchando servidor en http://{gpu_ip}:8000 ...")

    while True:
        try:
            time.sleep(5)
            # 1. Fetch active jobs from Colab
            url = f"http://{gpu_ip}:8000/api/jobs"
            req = urllib.request.Request(url, method='GET')
            with urllib.request.urlopen(req, timeout=5) as resp:
                remote_jobs = json.loads(resp.read().decode())

            for job_id, job_info in remote_jobs.items():
                status = job_info.get("status")
                if status in ("complete", "completed") and job_id not in synced_jobs:
                    print(f"\n⚡ [Sync] ¡Nuevo job completado detectado en Colab! ID: {job_id}")

                    # Create local folder for this job
                    job_folder = os.path.join(local_output_dir, job_id)
                    os.makedirs(job_folder, exist_ok=True)

                    # 2. Get the list of all files for this job from Colab
                    files_url = f"http://{gpu_ip}:8000/api/sync/{job_id}/files"
                    files_req = urllib.request.Request(files_url, method='GET')

                    try:
                        with urllib.request.urlopen(files_req, timeout=5) as files_resp:
                            files_data = json.loads(files_resp.read().decode())
                            files_to_download = files_data.get("files", [])
                    except urllib.error.HTTPError as e:
                        print(f"❌ [Sync] Error obteniendo lista de archivos para {job_id}: {e}")
                        continue

                    # 3. Download each file with progress
                    success_sync = True
                    total_files = len(files_to_download)
                    
                    for i, file_info in enumerate(files_to_download):
                        filename = file_info["name"]
                        expected_size = file_info["size"]

                        local_file_path = os.path.join(job_folder, filename)

                        # If file already exists and has the correct size, skip download
                        if os.path.exists(local_file_path) and os.path.getsize(local_file_path) == expected_size:
                            print(f"✅ [{i+1}/{total_files}] {filename} (ya existe)")
                            continue

                        download_url = f"http://{gpu_ip}:8000/videos/{job_id}/{filename}"
                        print(f"\n📥 [{i+1}/{total_files}] Descargando {filename} ({round(expected_size/(1024*1024), 2)} MB)...")

                        try:
                            # Direct stream download to file with progress
                            def reporthook(blocknum, blocksize, totalsize):
                                readsofar = blocknum * blocksize
                                if totalsize > 0:
                                    percent = min(100, readsofar * 100 / totalsize)
                                    print(f"   ↳ {percent:.1f}% ({readsofar/1024/1024:.2f} MB / {totalsize/1024/1024:.2f} MB)", end='\r')

                            urllib.request.urlretrieve(download_url, local_file_path, reporthook=reporthook)
                            print(f"\n   ✅ {filename} descargado")
                            
                        except Exception as e:
                            print(f"\n❌ Error descargando {filename}: {e}")
                            success_sync = False
                            break

                    # 4. Generate the TXT metadata info file locally on Windows!
                    if success_sync:
                        clips = job_info.get("result", {}).get("clips", [])
                        if clips:
                            txt_lines = []
                            for i, clip in enumerate(clips):
                                txt_lines.append(f"=== Clip {i + 1} ==={ ' | Hook: ' + clip.get('hook_title') if clip.get('hook_title') else '' }")
                                if clip.get("youtube_title"):
                                    txt_lines.append(f"YouTube Title : {clip['youtube_title']}")
                                if clip.get("tiktok_caption"):
                                    txt_lines.append(f"TikTok Caption : {clip['tiktok_caption']}")
                                if clip.get("instagram_caption"):
                                    txt_lines.append(f"Instagram Caption: {clip['instagram_caption']}")
                                if clip.get("description"):
                                    txt_lines.append(f"Description : {clip['description']}")
                                txt_lines.append("")

                            txt_content = "\n".join(txt_lines)
                            txt_filename = f"clips-info-{job_id}.txt"
                            with open(os.path.join(job_folder, txt_filename), "w", encoding="utf-8") as txt_f:
                                txt_f.write(txt_content)
                            print(f"\n📝 [Sync] Guardado archivo de metadata: {txt_filename}")

                        # Add to synced jobs and save list
                        synced_jobs.add(job_id)
                        try:
                            with open(synced_jobs_file, "w") as f:
                                json.dump(list(synced_jobs), f)
                            print(f"\n✅ [Sync] Job {job_id} sincronizado completamente y guardado en disco.")
                        except Exception as e:
                            print(f"⚠️ [Sync] Error guardando estado de sincronización: {e}")

        except Exception as e:
            # Silence general errors and retry
            pass

    print(f"\n🔄 [Sync Daemon] Sistema de auto-sincronización iniciado por Tailscale.")
    print(f"🔄 [Sync Daemon] Escuchando servidor en http://{gpu_ip}:8000 ...")

    while True:
        try:
            time.sleep(5)
            # 1. Fetch active jobs from Colab
            url = f"http://{gpu_ip}:8000/api/jobs"
            req = urllib.request.Request(url, method='GET')
            with urllib.request.urlopen(req, timeout=5) as resp:
                remote_jobs = json.loads(resp.read().decode())
            
            for job_id, job_info in remote_jobs.items():
                status = job_info.get("status")
                if status in ("complete", "completed") and job_id not in synced_jobs:
                    print(f"\n⚡ [Sync] ¡Nuevo job completado detectado en Colab! ID: {job_id}")
                    
                    # Create local folder for this job
                    job_folder = os.path.join(local_output_dir, job_id)
                    os.makedirs(job_folder, exist_ok=True)
                    
                    # 2. Get the list of all files for this job from Colab
                    files_url = f"http://{gpu_ip}:8000/api/sync/{job_id}/files"
                    files_req = urllib.request.Request(files_url, method='GET')
                    
                    try:
                        with urllib.request.urlopen(files_req, timeout=5) as files_resp:
                            files_data = json.loads(files_resp.read().decode())
                            files_to_download = files_data.get("files", [])
                    except urllib.error.HTTPError as e:
                        print(f"❌ [Sync] Error obteniendo lista de archivos para {job_id}: {e}")
                        continue
                    
                    # 3. Download each file
                    success_sync = True
                    for file_info in files_to_download:
                        filename = file_info["name"]
                        expected_size = file_info["size"]
                        
                        local_file_path = os.path.join(job_folder, filename)
                        
                        # If file already exists and has the correct size, skip download
                        if os.path.exists(local_file_path) and os.path.getsize(local_file_path) == expected_size:
                            continue
                            
                        download_url = f"http://{gpu_ip}:8000/videos/{job_id}/{filename}"
                        print(f"📥 [Sync] Descargando {filename} ({round(expected_size/(1024*1024), 2)} MB)...")
                        
                        try:
                            # Direct stream download to file
                            urllib.request.urlretrieve(download_url, local_file_path)
                        except Exception as e:
                            print(f"❌ [Sync] Error descargando {filename}: {e}")
                            success_sync = False
                            break
                    
                    # 4. Generate the TXT metadata info file locally on Windows!
                    if success_sync:
                        clips = job_info.get("result", {}).get("clips", [])
                        if clips:
                            txt_lines = []
                            for i, clip in enumerate(clips):
                                txt_lines.append(f"=== Clip {i + 1} ==={ ' | Hook: ' + clip.get('hook_title') if clip.get('hook_title') else '' }")
                                if clip.get("youtube_title"):
                                    txt_lines.append(f"YouTube Title   : {clip['youtube_title']}")
                                if clip.get("tiktok_caption"):
                                    txt_lines.append(f"TikTok Caption  : {clip['tiktok_caption']}")
                                if clip.get("instagram_caption"):
                                    txt_lines.append(f"Instagram Caption: {clip['instagram_caption']}")
                                if clip.get("description"):
                                    txt_lines.append(f"Description     : {clip['description']}")
                                txt_lines.append("")
                            
                            txt_content = "\n".join(txt_lines)
                            txt_filename = f"clips-info-{job_id}.txt"
                            with open(os.path.join(job_folder, txt_filename), "w", encoding="utf-8") as txt_f:
                                txt_f.write(txt_content)
                            print(f"📝 [Sync] Guardado archivo de metadata: {txt_filename}")
                            
                        # Add to synced jobs and save list
                        synced_jobs.add(job_id)
                        try:
                            with open(synced_jobs_file, "w") as f:
                                json.dump(list(synced_jobs), f)
                            print(f"✅ [Sync] Job {job_id} sincronizado completamente y guardado en disco.")
                        except Exception as e:
                            print(f"⚠️ [Sync] Error guardando estado de sincronización: {e}")
                            
        except Exception as e:
            # Silence general errors and retry
            pass


def main():
    print("=" * 60)
    print("🔍 OpenShorts — Auto Connect Colab GPU")
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
        print("   1. El notebook de Colab esté ejecutándose")
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
        
        # Start background sync daemon!
        import threading
        t = threading.Thread(target=sync_worker, args=(gpu_ip,), daemon=True)
        t.start()
    else:
        print(f"   ⚠️  Backend no responde aún. Puede estar arrancando...")
        print(f"   💡 Esperá 1-2 minutos y volvé a intentar.")

    # 4. Show how to use
    print(f"\n{'=' * 60}")
    print(f"🚀 Para usar OpenShorts con Colab GPU:")
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
            print(f"\n🚀 Lanzando dashboard apuntando a Colab GPU...")
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
