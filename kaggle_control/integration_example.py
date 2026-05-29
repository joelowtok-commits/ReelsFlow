#!/usr/bin/env python3
"""
Ejemplo de integracion con app.py

Agrega esto a tu app.py actual para soportar procesamiento en Kaggle.
"""

# ============================================
# En app.py, agregar estos endpoints:
# ============================================

from fastapi import UploadFile, File
import os
import tempfile

# Endpoint para procesar con Kaggle
@app.post("/api/kaggle/process")
async def process_with_kaggle(
    file: Optional[UploadFile] = File(None),
    url: Optional[str] = None
):
    """
    Procesa video usando Kaggle.
    
    Args:
        file: Archivo de video (upload)
        url: URL de YouTube o Drive
    
    Returns:
        job_id para trackear el progreso
    """
    from kaggle_control.kaggle_integration import process_video_on_kaggle, KaggleIntegration
    
    # 1. Obtener video (archivo o URL)
    video_path = None
    
    if file:
        # Guardar temporalmente
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as tmp:
            content = await file.read()
            tmp.write(content)
            video_path = tmp.name
    
    elif url:
        if 'drive.google.com' in url:
            video_path = url  # URL directa de Drive
        elif 'youtube.com' in url or 'youtu.be' in url:
            video_path = url  # URL de YouTube
        else:
            return {"error": "URL no soportada"}
    
    if not video_path:
        return {"error": "Debes proporcionar un archivo o URL"}
    
    # 2. Enviar a Kaggle
    try:
        kaggle = KaggleIntegration(username='joelowtok')
        
        # Si es URL de YouTube, el kernel lo descarga
        # Si es archivo local, primero se sube a Drive
        if os.path.exists(video_path):
            # Subir a Drive primero
            from drive_upload import upload_to_drive
            drive_result = upload_to_drive(video_path)
            video_url = drive_result['web_view_link']
        else:
            video_url = video_path
        
        # Ejecutar en Kaggle
        job_id = kaggle.run_kernel(video_url)
        
        # Limpiar temporal
        if os.path.exists(video_path):
            os.remove(video_path)
        
        return {
            "job_id": job_id,
            "status": "running",
            "kernel_url": f"https://www.kaggle.com/joelowtok/openshorts-processor"
        }
        
    except Exception as e:
        return {"error": str(e)}


@app.get("/api/kaggle/status/{job_id}")
async def kaggle_status(job_id: str):
    """Obtiene el estado del job en Kaggle."""
    from kaggle_control.kaggle_integration import KaggleIntegration
    
    kaggle = KaggleIntegration(username='joelowtok')
    status = kaggle.get_status(job_id)
    
    return status


@app.get("/api/kaggle/download/{job_id}")
async def kaggle_download(job_id: str):
    """Descarga los resultados del job."""
    from kaggle_control.kaggle_integration import KaggleIntegration
    
    kaggle = KaggleIntegration(username='joelowtok')
    output_dir = kaggle.get_output(job_id, output_dir='./kaggle_output')
    
    if output_dir:
        return {"output_dir": str(output_dir)}
    else:
        return {"error": "No se pudo descargar"}


# ============================================
# En tu frontend (App.jsx), agregar:
# ============================================

"""
// En App.jsx

const handleKaggleProcess = async (data) => {
  try {
    // 1. Enviar a Kaggle
    const res = await fetch('/api/kaggle/process', {
      method: 'POST',
      headers: { 'X-Gemini-Key': apiKey },
      body: formData // o JSON con URL
    });
    
    const { job_id } = await res.json();
    
    // 2. Monitorear progreso
    const pollStatus = async () => {
      const status = await fetch(`/api/kaggle/status/${job_id}`);
      const data = await status.json();
      
      if (data.status === 'complete') {
        // 3. Bajar resultados
        const download = await fetch(`/api/kaggle/download/${job_id}`);
        // Mostrar resultados
      } else {
        setTimeout(pollStatus, 5000); // Poll cada 5s
      }
    };
    
    pollStatus();
    
  } catch (e) {
    console.error('Error:', e);
  }
};
"""

if __name__ == '__main__':
    print("Ejemplo de integracion - ver codigo arriba")
    print("\nPara integrar con tu app:")
    print("1. Copia los endpoints en app.py")
    print("2. Agrega el boton en tu frontend")
    print("3. Test: python test_setup.py")
