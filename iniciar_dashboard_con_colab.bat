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

REM First, find Colab GPU IP
echo Detectando Colab...
python find_gpu.py

pause
