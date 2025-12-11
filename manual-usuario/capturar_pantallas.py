"""
Script para capturar pantallas de la plataforma SAM automáticamente
usando Selenium WebDriver
"""
import time
import os
import sys

# Fix encoding for Windows console
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options

# Configuración
BASE_URL = "https://app.sammetrologia.com"
USERNAME = "CERTIBOY"
PASSWORD = "Cer.901601314"
OUTPUT_DIR = "assets/images"

# Crear directorio de salida si no existe
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Configurar Chrome para capturas
chrome_options = Options()
chrome_options.add_argument("--window-size=1920,1080")
chrome_options.add_argument("--force-device-scale-factor=1")
chrome_options.add_argument("--disable-blink-features=AutomationControlled")

# Inicializar driver
driver = webdriver.Chrome(options=chrome_options)
wait = WebDriverWait(driver, 10)

try:
    print("🚀 Iniciando captura de pantallas...")

    # 1. CAPTURA: Pantalla de Login
    print("📸 [1/10] Capturando pantalla de login...")
    driver.get(f"{BASE_URL}/core/login/")
    time.sleep(3)

    # Debug: Guardar HTML
    with open("debug_login.html", "w", encoding="utf-8") as f:
        f.write(driver.page_source)

    driver.save_screenshot(f"{OUTPUT_DIR}/01-login.png")

    # Login con espera explícita
    print("🔐 Iniciando sesión...")
    username_input = wait.until(EC.presence_of_element_located((By.ID, "id_username")))
    password_input = driver.find_element(By.ID, "id_password")
    username_input.clear()
    password_input.clear()
    username_input.send_keys(USERNAME)
    password_input.send_keys(PASSWORD)
    login_button = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
    login_button.click()

    # Esperar a que se complete la redirección después del login
    wait.until(EC.url_changes(f"{BASE_URL}/core/login/"))
    time.sleep(2)

    # Verificar que el login fue exitoso
    current_url = driver.current_url
    print(f"✓ Redirigido a: {current_url}")

    # 2. CAPTURA: Dashboard principal
    print("📸 [2/10] Capturando dashboard...")
    wait.until(EC.url_contains("/core/"))
    driver.get(f"{BASE_URL}/core/dashboard/")
    time.sleep(2)
    driver.save_screenshot(f"{OUTPUT_DIR}/02-dashboard.png")

    # 3. CAPTURA: Lista de equipos (home)
    print("📸 [3/10] Capturando lista de equipos...")
    driver.get(f"{BASE_URL}/core/")
    time.sleep(2)
    driver.save_screenshot(f"{OUTPUT_DIR}/03-lista-equipos.png")

    # 4. CAPTURA: Formulario de nuevo equipo
    print("📸 [4/10] Capturando formulario de equipo...")
    driver.get(f"{BASE_URL}/core/equipos/añadir/")
    time.sleep(2)
    driver.save_screenshot(f"{OUTPUT_DIR}/04-formulario-equipo.png")

    # Necesitamos un equipo_id para las siguientes capturas
    # Intentar obtener el primer equipo de la lista
    print("🔍 Buscando equipo para capturas detalladas...")
    driver.get(f"{BASE_URL}/core/")
    time.sleep(2)

    try:
        # Buscar el primer enlace con icono de ojo (ver detalle)
        import re
        time.sleep(2)
        # Buscar en la tabla de equipos
        ver_buttons = driver.find_elements(By.CSS_SELECTOR, "a[href*='/equipos/'][href*='/']")
        if ver_buttons:
            for button in ver_buttons:
                href = button.get_attribute("href")
                match = re.search(r'/equipos/(\d+)/', href)
                if match:
                    equipo_id = match.group(1)
                    print(f"✓ Equipo encontrado: ID {equipo_id}")
                    break
            else:
                equipo_id = "1"
                print("⚠ No se pudo extraer ID, usando por defecto: 1")
        else:
            equipo_id = "1"
            print("⚠ No se encontraron equipos, usando ID por defecto: 1")
    except Exception as e:
        equipo_id = "1"
        print(f"⚠ Error detectando equipo: {str(e)}, usando ID por defecto: 1")

    # 5. CAPTURA: Confirmación metrológica
    print("📸 [5/10] Capturando confirmación metrológica...")
    driver.get(f"{BASE_URL}/core/equipos/{equipo_id}/confirmacion-metrologica/")
    time.sleep(2)
    driver.save_screenshot(f"{OUTPUT_DIR}/05-confirmacion.png")

    # 6. CAPTURA: Comprobación intermedia
    print("📸 [6/10] Capturando comprobación intermedia...")
    driver.get(f"{BASE_URL}/core/equipos/{equipo_id}/comprobacion-metrologica/")
    time.sleep(2)
    driver.save_screenshot(f"{OUTPUT_DIR}/06-comprobacion.png")

    # 7. CAPTURA: Intervalos ILAC
    print("📸 [7/10] Capturando intervalos ILAC...")
    driver.get(f"{BASE_URL}/core/equipos/{equipo_id}/intervalos-calibracion/")
    time.sleep(2)
    driver.save_screenshot(f"{OUTPUT_DIR}/07-intervalos-ilac.png")

    # 8. CAPTURA: Detalle de equipo (calibraciones)
    print("📸 [8/10] Capturando detalle de equipo...")
    driver.get(f"{BASE_URL}/core/equipos/{equipo_id}/")
    time.sleep(2)
    driver.save_screenshot(f"{OUTPUT_DIR}/08-detalle-equipo.png")

    # 9. CAPTURA: Mantenimiento
    print("📸 [9/10] Capturando mantenimiento...")
    driver.get(f"{BASE_URL}/core/equipos/{equipo_id}/mantenimiento-actividades/")
    time.sleep(2)
    driver.save_screenshot(f"{OUTPUT_DIR}/09-mantenimiento.png")

    # 10. CAPTURA: Programación de actividades
    print("📸 [10/10] Capturando programación...")
    driver.get(f"{BASE_URL}/core/informes/actividades_programadas/")
    time.sleep(2)
    driver.save_screenshot(f"{OUTPUT_DIR}/10-programacion.png")

    print("✅ ¡Capturas completadas exitosamente!")
    print(f"📁 Archivos guardados en: {os.path.abspath(OUTPUT_DIR)}")

except Exception as e:
    print(f"❌ Error durante la captura: {str(e)}")
    import traceback
    traceback.print_exc()

finally:
    print("🔚 Cerrando navegador...")
    driver.quit()
