# Kaggle Control - OpenShorts

Controlá tu instancia de Kaggle desde tu máquina local para procesar videos pesados.

## Estructura

```
kaggle_control/
├── local/                    # Scripts que corren en tu máquina
│   ├── upload_to_drive.py    # Sube videos a Drive
│   ├── download_results.py   # Baja resultados de Drive  
│   └── monitor_job.py        # Monitorea jobs en Kaggle
├── kaggle/                   # Scripts que van a Kaggle
│   ├── setup.sh              # Setup del entorno
│   ├── process_video.py      # Procesa video
│   └── upload_results.py     # Sube resultados a Drive
└── utils/
    └── ssh_tunnel.py         # SSH tunnel con ngrok
```

## Flujo completo

### 1. Preparación (primera vez)

```bash
# Instalar dependencias locales
pip install kaggle google-api-python-client google-auth gdown

# Configurar Kaggle CLI
kaggle config set

# Configurar Google Drive (opcional, para automatizar)
# Ver: https://console.cloud.google.com/
```

### 2. Subir video a Drive (desde tu máquina)

```bash
# Opción A: Usando el script
python local/upload_to_drive.py video_original.mp4

# Opción B: Manual desde drive.google.com
# - Subí el video
# - Copiá el URL (compartir → cualquiera con el link)
```

### 3. En Kaggle Notebook

```python
# Celdas del notebook

# Celda 1: Clone y setup
!git clone https://github.com/tu-usuario/openshorts.git
%cd openshorts/kaggle_control
!bash kaggle/setup.sh

# Celda 2: Procesar video
!python kaggle/process_video.py \
  --input "https://drive.google.com/file/d/FILE_ID" \
  --output /kaggle/working/output

# Celda 3: Subir resultados
!python kaggle/upload_results.py --folder DRIVE_FOLDER_ID
```

### 4. Monitorear (desde tu máquina)

```bash
# Ver progreso en tiempo real
python local/monitor_job.py tu-usuario/tu-kernel --live

# O ver logs una vez
python local/monitor_job.py tu-usuario/tu-kernel
```

### 5. Bajar resultados

```bash
# Si subiste los resultados a Drive, ya están disponibles
# Si no, bajalos de Kaggle:
kaggle kernels output tu-usuario/tu-kernel -p ./resultados
```

## SSH Tunnel (opcional)

Si querés control total via SSH:

```bash
# En tu máquina local
python utils/ssh_tunnel.py --port 22

# Te da una URL tipo: 0.tcp.ngrok.io:12345
# Desde Kaggle:
# !ssh usuario@0.tcp.ngrok.io -p 12345
```

## Comandos útiles

### Kaggle CLI
```bash
kaggle kernels push -p kaggle/        # Subir kernel
kaggle kernels pull -p kaggle/        # Bajar kernel
kaggle kernels output tu-user/kernel  # Bajar output
kaggle kernels list                   # Listar kernels
```

### Drive
```bash
# Subir archivo
python local/upload_to_drive.py video.mp4

# Bajar archivo
python local/download_results.py FILE_ID
```

## Variables de entorno

Crear `.env` (no trackear en git):
```
KAGGLE_USERNAME=tu_usuario
KAGGLE_KEY=tu_api_key

# Google Drive (opcional)
GDRIVE_CLIENT_ID=xxx
GDRIVE_CLIENT_SECRET=xxx
```

## Troubleshooting

### "No space left on device"
Kaggle tiene ~20GB de disk. Usá:
```python
!df -h  # Ver espacio
!rm -rf /kaggle/working/input/*  # Limpiar
```

### "Killed" por memoria
Reducí el tamaño del video o usá:
```python
!free -h  # Ver memoria
```

### Drive API quota
El límite es ~750GB/día por cuenta.
