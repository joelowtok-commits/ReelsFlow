@echo off
echo ========================================================
echo 🌐 Iniciando Chrome en modo Depuracion Remota (Puerto 9222)
echo ========================================================
echo Asegurate de que NO haya otras ventanas de Chrome abiertas antes de ejecutar esto.
echo Una vez abierto Chrome, inicia sesion en tu cuenta de Google/Colab.
echo.

:: Buscar Chrome en ubicaciones estandares
set "CHROME_PATH=C:\Program Files\Google\Chrome\Application\chrome.exe"
if not exist "%CHROME_PATH%" (
    set "CHROME_PATH=C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
)
if not exist "%CHROME_PATH%" (
    set "CHROME_PATH=%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"
)

if not exist "%CHROME_PATH%" (
    echo [ERROR] No se pudo encontrar google chrome. Por favor abre Chrome con:
    echo chrome.exe --remote-debugging-port=9222 --user-data-dir="%LOCALAPPDATA%\ChromeRemoteDebug"
    pause
    exit /b 1
)

start "" "%CHROME_PATH%" --remote-debugging-port=9222 --user-data-dir="%LOCALAPPDATA%\ChromeRemoteDebug"
echo Chrome iniciado con exito en el puerto 9222.
pause
