# Cómo usar Kaggle Control

## Resumen rápido

Este sistema te permite controlar una instancia de Kaggle desde tu máquina local para procesar videos pesados con OpenShorts.

## Arco general

```
Tu Máquina Local              Kaggle                 Google Drive
     │                          │                         │
     │  1. Subís video         │                         │
     ├────────────────────────>│                         │
     │                         │                         │
     │  2.ásdeas               │                         │
     │  (o usás el de Kaggle)  │                         │
     │                         │                         │
     │  3. Copiás scripts      │                         │
     │<────────────────────────┤                         │
     │                         │                         │
     │  4. Ejecutás en Kaggle  │                         │
     │                         │                         │
     │  5. Procesás video      │                         │
     │                         │                         │
     │  6. Subís resultados    │                         │
     │                         ├────────────────────────>│
     │                         │                         │
     │  7. Monitoreás          │                         │
     │<────────────────────────┤                         │
     │                         │                         │
     │  8. Bajás resultados    │                         │
     │<───────────────────────────────────────────────────┘
```

## Paso a paso

### 1. Preparación (primera vez)

```bash
# Instalá las dependencias
cd kaggle_control
pip install -r requirements.txt

# Verificá tu instalación
python iniciar.py
```

### 2. Subir video a Google Drive

**Opción A: Script (automático)**
```bash
python local/upload_to_drive.py video_original.mp4
```

**Opción B: Manual (recomendado al principio)**
1. Abrí https://drive.google.com/
2. Subí tu video
3. Click derecho → Compartir → "Cualquier persona con el link"
4. Copiá el URL

### 3. En Kaggle

```python
# Celda 1: Setup
!git clone https://github.com/tu-usuario/OpenShorts.git
%cd OpenShorts/kaggle_control
!bash kaggle/setup.sh

# Celda 2: Procesar
!python kaggle/process_video.py \
  --input "https://drive.google.com/file/d/TU_FILE_ID" \
  --output /kaggle/working/output

# Celda 3: Subir resultados
!python kaggle/upload_results.py --folder DRIVE_FOLDER_ID
```

### 4. Monitorear desde tu máquina

```bash
# Ver en tiempo real
python local/monitor_job.py tu-usuario/tu-kernel --live

# O ver una vez
python local/monitor_job.py tu-usuario/tu-kernel
```

### 5. Bajar resultados

```bash
# Si usaste upload_results.py, ya están en Drive
# Si no, bajalos de Kaggle
kaggle kernels output tu-usuario/tu-kernel -p ./resultados
```

## Comandos útiles

### Subir video
```bash
python local/upload_to_drive.py mi_video.mp4
```

### Ver progreso
```bash
python local/monitor_job.py username/kernel-name --live
```

### Bajar resultado
```bash
python local/download_results.py FILE_ID --output ./descargas
```

## SSH Tunnel (opcional)

Si querés control total via SSH:

```bash
# 1. En tu máquina local
python utils/ssh_tunnel.py --port 22

# 2. Te da una URL tipo: 0.tcp.ngrok.io:12345

# 3. En Kaggle
# !ssh usuario@0.tcp.ngrok.io -p 12345
```

## Troubleshooting

### "No space left on device"
```python
# En Kaggle
!df -h  # Ver espacio
!rm -rf /kaggle/working/input/*  # Limpiar
```

### "Killed" por memoria
```python
# Ver memoria
!free -h

# Reducir tamaño de video o usar proxy
```

### Drive no sube
- Verificá `credentials.json`
- Verificá quota (750GB/día)
- Usá service account para producción

## Flujo recomendado

1. **Primera vez**: Subí video manualmente a Drive
2. **Configurá**: `credentials.json` de Google Cloud
3. **Probá**: `python local/upload_to_drive.py test.mp4`
4. **En Kaggle**: Ejecutá `process_video.py`
5. **Monitoreá**: `python local/monitor_job.py --live`
6. **Automatizá**: Una vez que funcione, usá los scripts

## Archivos generados

```
kaggle_control/
├── local/                    # Usás desde tu máquina
│   ├── upload_to_drive.py    # Sube videos
│   ├── download_results.py   # Baja resultados
│   └── monitor_job.py        # Monitorea jobs
├── kaggle/                   # Copiás a Kaggle
│   ├── setup.sh              # Setup
│   ├── process_video.py      # Procesa
│   └── upload_results.py     # Sube a Drive
└── utils/
    └── ssh_tunnel.py         # SSH remoto
```

## Siguientes pasos

1. `python iniciar.py` - Verificá tu setup
2. Subí un video de prueba a Drive
3. Probá el flujo en Kaggle con un video corto
4. Monitoreá el progreso
5. Bajá los resultados

¡Listo! 🎬
