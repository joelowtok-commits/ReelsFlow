@echo off
setlocal enabledelayedexpansion
title OpenShorts 1.1 - Launcher
color 0A

echo.
echo  =====================================================
echo       OpenShorts 1.1 - AI Viral Shorts Generator
echo  =====================================================
echo.

:: ─── 1. Verificar Python ───
echo  [1/5] Verificando Python...
python --version >nul 2>nul
if %errorlevel% neq 0 (
    color 0C
    echo  [ERROR] Python no encontrado en el PATH!
    echo         Descargalo de: https://python.org
    pause
    exit /b 1
)
for /f "tokens=*" %%v in ('python --version') do echo         %%v
echo.

:: ─── 2. Verificar Node.js ───
echo  [2/5] Verificando Node.js...
node --version >nul 2>nul
if %errorlevel% neq 0 (
    color 0C
    echo  [ERROR] Node.js no encontrado en el PATH!
    echo         Descargalo de: https://nodejs.org
    pause
    exit /b 1
)
for /f "tokens=*" %%v in ('node --version') do echo         Node %%v
echo.

:: ─── 3. Dependencias Python ───
echo  [3/5] Verificando dependencias Python...
python -c "import fastapi, uvicorn" >nul 2>nul
if %errorlevel% neq 0 (
    echo         Instalando dependencias... (esto puede tardar un momento)
    pip install -r requirements.txt -q
    if %errorlevel% neq 0 (
        color 0C
        echo  [ERROR] Fallo al instalar dependencias Python.
        pause
        exit /b 1
    )
) else (
    echo         OK - Todas las dependencias encontradas.
)
echo.

:: ─── 4. Verificar .env ───
echo  [4/5] Verificando configuracion...
if not exist .env (
    echo         Creando .env desde plantilla...
    copy .env.example .env >nul
    echo  [AVISO] Configura tus API keys en el archivo .env antes de procesar videos!
) else (
    echo         OK - Archivo .env encontrado.
)
echo.

:: ─── 5. Dependencias Frontend ───
echo  [5/5] Verificando dependencias frontend...
if not exist dashboard\node_modules (
    echo         Instalando node_modules... (primera vez, puede tardar)
    cd dashboard
    call npm install --silent
    cd ..
    echo         OK - node_modules instalados.
) else (
    echo         OK - node_modules encontrados.
)
echo.

:: ─── Lanzar Backend ───
echo  =====================================================
echo   Iniciando servicios...
echo  =====================================================
echo.
echo  [Backend]  Levantando FastAPI en http://localhost:8000
start "OpenShorts - Backend" cmd /k "cd /d "%~dp0" && python -u -m uvicorn app:app --host 0.0.0.0 --port 8000 --reload"

:: Esperar a que el backend arranque
echo  [Backend]  Esperando que el servidor este listo...
timeout /t 3 /nobreak >nul

:: ─── Lanzar Frontend ───
echo  [Frontend] Levantando Vite Dashboard en http://localhost:5173
start "OpenShorts - Frontend" cmd /k "cd /d "%~dp0dashboard" && npm run dev"

:: Esperar a que el frontend arranque
timeout /t 3 /nobreak >nul

:: ─── Abrir Navegador ───
echo  [Browser]  Abriendo http://localhost:5173 ...
start http://localhost:5173

echo.
echo  =====================================================
echo   OpenShorts 1.1 listo!
echo.
echo   Backend:   http://localhost:8000
echo   Frontend:  http://localhost:5173
echo   API Docs:  http://localhost:8000/docs
echo  =====================================================
echo.
echo   Para detener: Cierra las ventanas de terminal
echo   que se abrieron para Backend y Frontend.
echo  =====================================================
echo.
pause
