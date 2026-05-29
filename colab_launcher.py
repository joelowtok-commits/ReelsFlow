# -*- coding: utf-8 -*-
import os
import sys
import time
import codecs
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

# Configurar encoding UTF-8 para consola en Windows
if sys.platform == 'win32':
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

load_dotenv()

def launch_colab():
    notebook_url = os.environ.get("COLAB_NOTEBOOK_URL")
    if not notebook_url:
        print("❌ Error: COLAB_NOTEBOOK_URL no está configurado en el archivo .env")
        print("   Por favor, edita tu archivo .env y agrega la URL de tu Notebook de Google Colab.")
        print("   Ejemplo: COLAB_NOTEBOOK_URL=https://colab.research.google.com/drive/1xxxxxxxxx")
        sys.exit(1)

    print("\n========================================================")
    print("🤖 Google Colab Launcher & Keep-Alive Daemon")
    print("========================================================")
    print(f"🌐 Conectando al navegador Chrome local (puerto 9222)...")
    
    try:
        with sync_playwright() as p:
            # Conectar usando Chrome DevTools Protocol (CDP)
            browser = p.chromium.connect_over_cdp("http://localhost:9222")
            print("✅ Conectado a Chrome con éxito!")
            
            # Obtener el contexto y crear una nueva pestaña
            context = browser.contexts[0] if browser.contexts else browser.new_context()
            page = context.new_page()
            
            print(f"🔄 Navegando a la URL del Notebook de Colab...")
            print(f"   URL: {notebook_url}")
            page.goto(notebook_url)
            
            # Esperar a que cargue la interfaz de Colab
            print("⏳ Esperando que cargue la interfaz del Notebook (5 segundos)...")
            page.wait_for_timeout(5000)
            
            # Intentar hacer clic en el botón de conectar
            connect_selectors = [
                "colab-connect-button",
                "#connect-button",
                "#colab-connect-button",
                "paper-button#connect",
                "text=Conectar",
                "text=Connect",
                "text=Reconectar",
                "text=Reconnect"
            ]
            
            clicked = False
            for selector in connect_selectors:
                try:
                    btn = page.locator(selector).first
                    if btn.is_visible():
                        print(f"🖱️ Botón de conexión detectado con selector '{selector}'. Haciendo clic...")
                        btn.click()
                        clicked = True
                        break
                except Exception:
                    pass
            
            if not clicked:
                print("ℹ️ No se detectó botón de conectar visible, puede que ya esté conectado o cargando.")
                
            page.wait_for_timeout(3000)
            
            # Enviar el shortcut de teclado Ctrl + F9 para Ejecutar Todo (Run All)
            print("⌨️ Enviando atajo Ctrl+F9 para ejecutar todas las celdas (Run All)...")
            page.keyboard.press("Control+F9")
            print("🚀 Celdas puestas en ejecución!")
            
            print("\n========================================================")
            print("🛡️ Keep-Alive Activo. Presiona Ctrl+C para detener.")
            print("========================================================")
            
            # Bucle keep-alive
            while True:
                time.sleep(60)
                timestamp = time.strftime('%H:%M:%S')
                
                try:
                    # Hacer un click inofensivo en el botón o widget de estado de conexión para simular actividad
                    status_btn = page.locator("colab-connect-button").first
                    if status_btn.is_visible():
                        status_btn.click()
                        print(f"⏰ [{timestamp}] Keep-Alive: Clic simulado en estado de conexión.")
                    else:
                        page.mouse.click(100, 100)
                        print(f"⏰ [{timestamp}] Keep-Alive: Clic de ratón simulado en posición neutral (100, 100).")
                except Exception as e:
                    print(f"⚠️ [{timestamp}] Keep-Alive: No se pudo simular actividad ({e})")
                    
    except Exception as e:
        print(f"\n❌ Error de automatización: {e}")
        print("   Por favor verifica que:")
        print("   1. Hayas ejecutado 'iniciar_chrome_debug.bat' primero.")
        print("   2. No tengas otras ventanas normales de Chrome abiertas que interfieran con el puerto 9222.")
        print("   3. Playwright esté correctamente configurado.")
        sys.exit(1)

if __name__ == "__main__":
    try:
        launch_colab()
    except KeyboardInterrupt:
        print("\n👋 Keep-Alive detenido por el usuario. Saliendo...")
        sys.exit(0)
