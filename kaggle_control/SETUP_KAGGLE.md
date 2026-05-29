# Setup Kaggle Integration - OpenShorts

## Configuración Inicial (1 sola vez)

### 1. Instalar dependencias

```bash
pip install -r requirements-kaggle.txt
```

### 2. Configurar credenciales de Kaggle

De la imagen que copiaste, guarda el token:

**Windows:**
```bash
mkdir C:\Users\joel9\.kaggle
echo KGAT_85fbbdc42d20933b5972be2afae8de3a > C:\Users\joel9\.kaggle\access_token
```

### 3. Configurar Google Drive API

1. Andá a https://console.cloud.google.com/
2. Creá un proyecto nuevo
3. Buscá 'Google Drive API' y habilitala
4. Creá credentials (OAuth desktop app)
5. Descargá credentials.json y guardalo en kaggle_control/

### 4. Crear kernel en Kaggle

```bash
cd E:\PROYECTOS_PY\OpenShorts\1.1\kaggle_control
python deploy_kernel.py
```

## Flujo de Uso

```python
from kaggle_integration import process_video_on_kaggle

# Procesar video
job_id = process_video_on_kaggle('mi_video.mp4')
print(f'Job: {job_id}')
```

## Comandos Rápidos

```bash
# Deploy inicial
python deploy_kernel.py

# Procesar video
python kaggle_integration.py video.mp4

# Ver logs en vivo
kaggle kernels output joelowtok/openshorts-processor -w
```

