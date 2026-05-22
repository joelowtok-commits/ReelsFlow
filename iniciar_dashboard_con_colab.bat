@echo off
cls
title ReelsFlow - Conectar Dashboard a Google Colab
echo ==========================================================
echo REELSFLOW - INICIAR DASHBOARD CON GOOGLE COLAB
echo ==========================================================
echo.
echo Este script va a detectar tu Google Colab de forma automatica,
echo configurara tu dashboard para procesar alli, y lo iniciara.
echo.
echo.
cd /d "%~dp0"
python auto_connect_colab.py --auto
if %ERRORLEVEL% NEQ 0 (
echo.
echo [ERROR] Hubo un problema al conectar. Asegurate de que:
echo 1. Tu Google Colab este encendido y ejecutando el script.
echo 2. Tengas Tailscale abierto y conectado en tu Windows.
echo.
)
pause
