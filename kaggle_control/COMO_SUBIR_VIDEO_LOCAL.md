# Cómo subir videos locales a Kaggle

## Flujo completo

```
Tu PC (local)                          Kaggle (nube)
│                                      │
│ 1. python kaggle_integration.py video.mp4
 │────────────────────────────────────>│
│    Sube video como Dataset           │
│                                      │
│    Push kernel + config              │
│─────────────────────────────────────>│
│                                      │
│    Kernel lee desde /kaggle/input/  │
│    ┌────────────────────────────┐   │
│    │ /kaggle/input/             │   │
│    │  └─ openshorts-input-xxx/  │   │
│    │      └─ video.mp4          │   │
│    └────────────────────────────┘   │
│                                      │
│ 2. Procesa video                     │
│    (con GPU de Kaggle)              │
│                                      │
│ 3. Sube resultados a Drive           │
│    o los deja en /kaggle/working/   │
│                                      │
│<────────────────────────────────────│
│    Resultados listos                │
```

## Uso

### Opción A: Desde consola (más simple)

```bash
# Video local
python kaggle_integration.py mi_video.mp4

# URL de YouTube o Drive
python kaggle_integration.py https://youtube.com/watch?v=XYZ
```

### Opción B: Desde Python

```python
from kaggle_integration import process_video_on_kaggle

# Video local
job_id = process_video_on_kaggle('mi_video.mp4')

# URL
job_id = process_video_on_kaggle('https://youtube.com/watch?v=XYZ')
```

### Opción C: Con carpeta de Drive para resultados

```python
from kaggle_integration import process_video_on_kaggle

job_id = process_video_on_kaggle(
    'mi_video.mp4',
    drive_folder_id='1234567890abcdef'  # ID de carpeta de Drive
)
```

## ¿Cómo funciona?

### 1. Subida del video
- El script crea un **dataset temporal** en Kaggle con tu video
- Nombre: `openshorts-input-{timestamp}`
- El dataset es privado (solo vos lo ves)

### 2. Ejecución del kernel
- El kernel se pushea a Kaggle con la config actualizada
- El kernel lee el video desde `/kaggle/input/openshorts-input-*/`
- Procesa el video con el pipeline de OpenShorts

### 3. Resultados
- Los resultados se guardan en `/kaggle/working/output/`
- Opcionalmente se suben a Google Drive
- Podés bajarlos con: `python kaggle_integration.py download <job_id>`

## Ventajas de este método

✅ **Sin Drive OAuth** - No requiere configuración de Google Cloud
✅ **Sin YouTube bloqueado** - Kaggle puede leer sus propios datasets
✅ **Todo vía API** - Automatizable 100%
✅ **_privado** - Los datasets son privados por defecto

## Desventajas

⚠️ **Límite de Kaggle** - 10GB por dataset, 100GB por mes
⚠️ **Tiempo de subida** - Depende de tu conexión a internet
⚠️ **Dataset basura** - Acumula datasets viejos (hay que limpiar)

## Limpiar datasets viejos

```bash
# Listar datasets
kaggle datasets list

# Borrar dataset
kaggle datasets delete joelowtok/openshorts-input-1234567890
```

## Ejemplo completo

```bash
# 1. Subir y procesar video
python kaggle_integration.py mi_video.mp4

# Salida:
# [PUSH] Subiendo video a Kaggle Dataset: openshorts-input-1779571035
# [OK] Video subido como dataset: joelowtok/openshorts-input-1779571035
# [PUSH] Empujando kernel: joelowtok/openshorts-processor
# [OK] Kernel empujado
# [OK] Job iniciado: joelowtok-openshorts-processor-1779571035

# 2. Monitorear
# Ver en: https://www.kaggle.com/code/joelowtok/openshorts-processor

# 3. (Opcional) Bajar resultados
python kaggle_integration.py download joelowtok-openshorts-processor-1779571035
```

## Problemas comunes

### "No module named 'google_auth_oauthlib'"
Ya no se necesita. El método nuevo usa datasets de Kaggle.

### "Dataset already exists"
El nombre del dataset incluye timestamp, no debería pasar. Si pasa, usá otro nombre:
```python
kaggle.upload_video_dataset('video.mp4', 'mi-unico-nombre')
```

### "Kernel no encuentra el video"
Verificá que el kernel tenga `enable_internet: true` y el dataset source correcto en `kernel-metadata.json`.
