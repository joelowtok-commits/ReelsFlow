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

REM First, find Colab GPU IP and launch dashboard with local sync
echo Detectando Colab y levantando sincronizador...
python auto_connect_colab.py

exit
