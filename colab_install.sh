#!/bin/bash
# colab_install.sh — Instala las dependencias de OpenShorts en Google Colab
# Uso: !bash colab_install.sh
set -e

echo "============================================"
echo "📦 Instalando dependencias para Colab GPU"
echo "============================================"

# Sistema
echo "📦 FFmpeg, btop y nvtop..."
apt-get update -qq && apt-get install -qq -y ffmpeg btop nvtop 2>/dev/null

# Python deps — uno por uno para no reventar la RAM
echo ""
echo "🐍 faster-whisper..."
pip install -q --no-cache-dir faster-whisper 2>&1 | tail -1

echo "🐍 ultralytics..."
pip install -q --no-cache-dir ultralytics 2>&1 | tail -1

echo "🐍 scenedetect..."
pip install -q --no-cache-dir scenedetect 2>&1 | tail -1

echo "🐍 mediapipe..."
pip install -q --no-cache-dir mediapipe 2>&1 | tail -1

echo "🐍 google-genai..."
pip install -q --no-cache-dir google-genai 2>&1 | tail -1

echo "🐍 yt-dlp..."
pip install -q --no-cache-dir yt-dlp 2>&1 | tail -1

echo "🐍 fastapi + uvicorn..."
pip install -q --no-cache-dir fastapi uvicorn python-multipart httpx 2>&1 | tail -1

echo "🐍 python-dotenv + psutil + boto3 + beautifulsoup4..."
pip install -q --no-cache-dir python-dotenv psutil boto3 beautifulsoup4 2>&1 | tail -1

echo ""
echo "✅ Dependencias instaladas!"
echo ""

# Verificar GPU
echo "🎮 Verificando GPU..."
nvidia-smi --query-gpu=name,memory.total --format=csv,noheader 2>/dev/null || echo "⚠️ No GPU detected"
python3 -c "import torch; print(f'✅ PyTorch CUDA: {torch.cuda.get_device_name(0)}') if torch.cuda.is_available() else print('⚠️ No CUDA')" 2>/dev/null || true

echo ""
echo "============================================"
echo "✅ LISTO — Ahora ejecutá colab_setup.py"
echo "============================================"
