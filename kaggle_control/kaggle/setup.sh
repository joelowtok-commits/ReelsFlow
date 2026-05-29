#!/bin/bash
# Setup inicial del entorno en Kaggle
# Copiar este script al notebook de Kaggle y ejecutar: !bash setup.sh

echo "🔧 Configurando entorno Kaggle..."

# Instalar dependencias básicas
pip install -q google-api-python-client google-auth-httplib2 google-auth-oauthlib
pip install -q gdown
pip install -q yt-dlp

# Configurar Google Drive (si hay credentials)
if [ -f "credentials.json" ]; then
    echo "✅ credentials.json encontrado"
else
    echo "⚠️  credentials.json no encontrado - algunas funciones no estarÃ¡n disponibles"
fi

# Crear directorios de trabajo
mkdir -p /kaggle/working/input
mkdir -p /kaggle/working/output

echo "✅ Setup completado"
echo ""
echo "Directorios:"
echo "  Input:  /kaggle/working/input"
echo "  Output: /kaggle/working/output"
