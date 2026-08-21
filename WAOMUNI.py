import os
import json
import shutil
import time
from datetime import datetime

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from docxtpl import DocxTemplate
from docx2pdf import convert

# ================= CONFIG =================

RUTAS = {
    "WAOM": r'C:\Users\Christian Redes\OneDrive - Grupo MV\Escritorio\WAOM',
    "WAOM3": r'C:\Users\Christian Redes\OneDrive - Grupo MV\Escritorio\WAOM3',
    "WAOM2": r'C:\Users\Christian Redes\OneDrive - Grupo MV\Escritorio\WAOM2',
    "REPORTES": r'C:\Users\Christian Redes\OneDrive - Grupo MV\Escritorio\Reportes automaticos con PY',
    "PLANTILLA": r'C:\Users\Christian Redes\OneDrive - Grupo MV\Escritorio\Reportes automaticos con PY\Plantilla de Reporte.docx'
}

#CHROMEDRIVER = r'C:\Users\Christian Redes\OneDrive - Grupo MV\Escritorio\Reportes WA con Selenium\MSJ AUTO\chromedriver\win64-133.0.6943.53\chromedriver-win64\chromedriver.exe'
USER_DATA = r"C:\Users\Christian Redes\AppData\Local\Google\Chrome\User Data\Persona 1"

# ================= GRUPOS =================

grupo_ids = {
    "Taller": "Taller Reporte Reparaciones",
    "Accesorios": "Accesorios Reporte Reparaciones",
    "Armado": "Armado Reporte Reparaciones",
    "Armado 1": "Armado Reporte Reparaciones",
    "Armado 2": "Armado Reporte Reparaciones",
    "Corte": "Maquinado Reporte Reparaciones",
    "Herreria": "Herrería Reporte Reparaciones",
    "Herrería": "Herrería Reporte Reparaciones",
    "Maquinado": "Maquinado Reporte Reparaciones",
    "Obras": "Obras Reporte Reparaciones",
    "Pantografo 1 y 2": "Maquinado Reporte Reparaciones",
    "Pintura": "Pintura Reporte Reparaciones",
    "Plegado": "Maquinado Reporte Reparaciones",
    "Punteadora": "Maquinado Reporte Reparaciones",
    "Punzonadora": "Maquinado Reporte Reparaciones",
    "Arco Sumergido": "Maquinado Reporte Reparaciones",
    "Sierra Taladro": "Maquinado Reporte Reparaciones",
    "Galvamax": "GALVAMAX Reporte Mantenimiento"
}

GRUPO_DEFECTO_1 = "Reparaciones MVSRL (Asignación y reporte de OM)"
GRUPO_DEFECTO_2 = "Reparaciones MVSRL (Asignación y reporte de OM)"

# ================= UTIL =================

def formatear_fecha(fecha_iso):
    try:
        fecha_obj = datetime.strptime(fecha_iso, "%Y-%m-%dT%H:%M:%SZ")
        dias = {
            'Monday': 'Lunes','Tuesday': 'Martes','Wednesday': 'Miércoles',
            'Thursday': 'Jueves','Friday': 'Viernes','Saturday': 'Sábado','Sunday': 'Domingo'
        }
        return f"{dias[fecha_obj.strftime('%A')]}, {fecha_obj.strftime('%d/%m/%Y')}"
    except:
        return fecha_iso

# ================= PDF =================

def generar_pdf(datos):
    try:
        id_ = datos.get("ID", "").strip()
        equipo = datos.get("equipo", "").strip()
        nombre = f"{id_}_{equipo}".replace(" ", "_")

        word = os.path.join(RUTAS["REPORTES"], nombre + ".docx")
        pdf = os.path.join(RUTAS["REPORTES"], nombre + ".pdf")

        doc = DocxTemplate(RUTAS["PLANTILLA"])
        doc.render(datos)
        doc.save(word)

        convert(word, pdf)

        for i in range(5):
            try:
                if os.path.exists(word):
                    os.remove(word)
                break
            except:
                time.sleep(1)

        return pdf
    except Exception as e:
        print("Error generando PDF:", e)
        return None

# ================= WHATSAPP =================

def iniciar_driver():
    from webdriver_manager.chrome import ChromeDriverManager  # 🔴 NUEVO

    options = webdriver.ChromeOptions()
    options.add_argument(f"user-data-dir={USER_DATA}")
    options.add_argument("--start-maximized")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)

    # 🔴 CAMBIO ÚNICO AQUÍ
    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options
    )

    driver.get('https://web.whatsapp.com')

    WebDriverWait(driver, 30).until(
        EC.presence_of_element_located((By.ID, "pane-side"))
    )

    return driver

def enviar_texto(driver, grupo, mensaje):
    try:
        # Buscar grupo
        search_box = WebDriverWait(driver, 30).until(
            EC.element_to_be_clickable((By.XPATH, '//*[@id="_r_a_"]'))
        )
        search_box.click()
        search_box.clear()
        search_box.send_keys(grupo)
        time.sleep(2)

        resultados = driver.find_elements(By.XPATH, f'//span[@title="{grupo}"]')
        if resultados:
            resultados[0].click()
            time.sleep(1)

        # Caja de mensaje
        message_box = WebDriverWait(driver, 30).until(
            EC.element_to_be_clickable((By.XPATH, '/html/body/div[2]/div/div/div/div/div[3]/div/div[4]/div/footer/div[1]/div/span/div/div/div/div[3]/div[1]/p'))
        )
        message_box.click()
        message_box.send_keys(mensaje)

        # Botón enviar
        message_box.send_keys(Keys.ENTER)
        time.sleep(0.5)
        return True
    except Exception as e:
        print("Error enviando mensaje:", e)
        return False

def obtener_contacto_valido(datos):
    """Devuelve el contacto local si tiene un formato paraguayo válido."""
    contacto = next(
        (valor for clave, valor in datos.items() if clave.lower() == "contacto"),
        ""
    )
    contacto = str(contacto).strip()
    numero = "".join(caracter for caracter in contacto if caracter.isdigit())

    if len(numero) == 9 and numero.startswith(("96", "97", "98", "99")):
        return numero
    return None

def enviar_texto_contacto(driver, numero, mensaje):
    try:
        # Abre el chat directamente en WhatsApp Web, sin pasar por wa.me ni la app.
        driver.get(f"https://web.whatsapp.com/send?phone=595{numero}")

        message_box = WebDriverWait(driver, 30).until(
            EC.element_to_be_clickable((By.XPATH, '/html/body/div[2]/div/div/div/div/div[3]/div/div[4]/div/footer/div[1]/div/span/div/div/div/div[3]/div[1]/p'))
        )
        message_box.click()
        message_box.send_keys(mensaje)
        message_box.send_keys(Keys.ENTER)
        time.sleep(0.5)
        return True
    except Exception as e:
        print(f"Error enviando mensaje a 595{numero}:", e)
        return False

def mencionar(message_box, nombre):
    corto = nombre.split()[0]
    message_box.send_keys("@")
    time.sleep(1)
    message_box.send_keys(corto)
    time.sleep(1)
    message_box.send_keys(Keys.ARROW_DOWN)
    time.sleep(0.4)
    message_box.send_keys(Keys.ENTER)
    time.sleep(0.4)

def enviar_con_menciones(driver, grupo, datos):
    try:
        # Buscar grupo
        search_box = WebDriverWait(driver, 30).until(
            EC.element_to_be_clickable((By.XPATH, '//*[@id="_r_a_"]'))
        )
        search_box.click()
        search_box.clear()
        search_box.send_keys(grupo)
        time.sleep(2)

        resultados = driver.find_elements(By.XPATH, f'//span[@title="{grupo}"]')
        if resultados:
            resultados[0].click()
            time.sleep(1)

        # Caja de mensaje
        message_box = WebDriverWait(driver, 30).until(
            EC.element_to_be_clickable((By.XPATH, '/html/body/div[2]/div/div/div/div/div[3]/div/div[4]/div/footer/div[1]/div/span/div/div/div/div[3]/div[1]/p'))
        )
        message_box.click()

        message_box.send_keys(
            f" Para asistir la *Solicitud de Mantenimiento* N° *{datos['ID']}*, "
            f"con prioridad *{datos['Prioridad']}*, para *{datos['Maquina']}* "
            f"que reporta *{datos['Averia']}*, los técnicos asignados son "
        )
        mencionar(message_box, datos['Responsable'])
        message_box.send_keys(" con apoyo de ")
        if datos.get("Apoyo"):
            mencionar(message_box, datos['Apoyo'])
        message_box.send_keys(".")
        
        message_box.send_keys(Keys.ENTER)
        time.sleep(0.5)
        return True
    except Exception as e:
        print("Error menciones:", e)
        return False

# ================= PROCESOS (WAOM, WAOM2, WAOM3) =================

def procesar_waom(driver):
    carpeta = RUTAS["WAOM"]
    prereportado = os.path.join(carpeta, "Prereportado")
    reportado = os.path.join(carpeta, "Reportado")
    os.makedirs(prereportado, exist_ok=True)
    os.makedirs(reportado, exist_ok=True)

    archivos = [f for f in os.listdir(carpeta) if f.endswith(".json")]

    for archivo in archivos:
        ruta = os.path.join(carpeta, archivo)
        try:
            with open(ruta, encoding='utf-8') as f:
                datos = json.load(f)
            id_ = datos.get("ID", "").strip()
            equipo = datos.get("equipo", "").strip()
            fecha_formateada = formatear_fecha(datos.get("Fecha", "").strip())
            sector = datos.get("sector", "").strip()
            solicitante = datos.get("Solicitante", "").strip()
            averia = datos.get("Averia", "").strip()
            prioridad = datos.get("Prioridad", "").strip()
            mensaje = f" ❌ Solicitud de mantenimiento ID: *{id_}* registrada para *{equipo}* con prioridad *{prioridad}*, (Motivo de la solicitud << *{averia}* >>),Solicitado por *{solicitante}* del sector *{sector}* el *{fecha_formateada}*."
            grupo = grupo_ids.get(sector, GRUPO_DEFECTO_1)
            if enviar_texto(driver, grupo, mensaje):
                shutil.move(ruta, os.path.join(prereportado, archivo))
            time.sleep(3)
        except Exception as e:
            print("Error WAOM fase 1:", e)

    for archivo in os.listdir(prereportado):
        if not archivo.endswith(".json"):
            continue
        ruta = os.path.join(prereportado, archivo)
        try:
            with open(ruta, encoding='utf-8') as f:
                datos = json.load(f)
            id_ = datos.get("ID", "").strip()
            equipo = datos.get("equipo", "").strip()
            fecha_formateada = formatear_fecha(datos.get("Fecha", "").strip())
            sector = datos.get("sector", "").strip()
            solicitante = datos.get("Solicitante", "").strip()
            averia = datos.get("Averia", "").strip()
            prioridad = datos.get("Prioridad", "").strip()
            mensaje = f" ❌ Solicitud de mantenimiento ID: *{id_}* registrada para *{equipo}* con prioridad *{prioridad}*, (Motivo de la solicitud << *{averia}* >>),Solicitado por *{solicitante}* del sector *{sector}* el *{fecha_formateada}*."
            if enviar_texto(driver, GRUPO_DEFECTO_1, mensaje):
                contacto = obtener_contacto_valido(datos)
                if not contacto or enviar_texto_contacto(driver, contacto, mensaje):
                    shutil.move(ruta, os.path.join(reportado, archivo))
            time.sleep(3)
        except Exception as e:
            print("Error WAOM fase 2:", e)

def procesar_waom3(driver):
    carpeta = RUTAS["WAOM3"]
    reportado = os.path.join(carpeta, "Reportado")
    os.makedirs(reportado, exist_ok=True)
    archivos = [f for f in os.listdir(carpeta) if f.endswith(".json")]
    for archivo in archivos:
        ruta = os.path.join(carpeta, archivo)
        try:
            with open(ruta, encoding='utf-8') as f:
                datos = json.load(f)
            if enviar_con_menciones(driver, GRUPO_DEFECTO_1, datos):
                shutil.move(ruta, os.path.join(reportado, archivo))
            time.sleep(3)
        except Exception as e:
            print("Error WAOM3:", e)

def procesar_waom2(driver):
    carpeta = RUTAS["WAOM2"]
    prereportado = os.path.join(carpeta, "Prereportado")
    reportado = os.path.join(carpeta, "Reportado")
    os.makedirs(prereportado, exist_ok=True)
    os.makedirs(reportado, exist_ok=True)

    archivos = [f for f in os.listdir(carpeta) if f.endswith(".json")]

    # FASE 1
    for archivo in archivos:
        ruta = os.path.join(carpeta, archivo)
        try:
            with open(ruta, encoding='utf-8') as f:
                datos = json.load(f)
            generar_pdf(datos)

            id_ = datos.get("ID", "").strip()
            equipo = datos.get("equipo", "").strip()
            fecha_formateada = formatear_fecha(datos.get("Fecha", "").strip())
            sector = datos.get("sector", "").strip()
            solicitante = datos.get("Solicitante", "").strip()
            progreso = datos.get("Progreso", "").strip()
            averia = datos.get("Averia", "").strip()

            if progreso == "Completado":
                msg = f"✅ *{equipo}*: Reparación *{id_}* completada, solicitada por *{solicitante}* del sector *{sector}* el *{fecha_formateada}*, Motivo de la solicitud *{averia}*."
            elif progreso == "Extemporaneo":
                msg = f"✅ *{equipo}*: Reparación *{id_}* completada con retraso, solicitada por *{solicitante}* del sector *{sector}* el *{fecha_formateada}*, Motivo de la solicitud *{averia}*."
            elif progreso == "Reprogramado":
                msg = f"⚠️ *{equipo}*: Reparación *{id_}* reprogramada, solicitada por *{solicitante}* del sector *{sector}* el *{fecha_formateada}*, Motivo de la solicitud *{averia}*."
            else:
                msg = f"❌ *{equipo}*: Reparación *{id_}* registrada, solicitada por *{solicitante}* del sector *{sector}* el *{fecha_formateada}*, Motivo de la solicitud *{averia}*."

            grupo = grupo_ids.get(sector, GRUPO_DEFECTO_2)
            if enviar_texto(driver, grupo, msg):
                shutil.move(ruta, os.path.join(prereportado, archivo))
            time.sleep(3)
        except Exception as e:
            print("Error WAOM2 fase 1:", e)

    # FASE 2
    for archivo in os.listdir(prereportado):
        if not archivo.endswith(".json"):
            continue
        ruta = os.path.join(prereportado, archivo)
        try:
            with open(ruta, encoding='utf-8') as f:
                datos = json.load(f)

            id_ = datos.get("ID", "").strip()
            equipo = datos.get("equipo", "").strip()
            fecha_formateada = formatear_fecha(datos.get("Fecha", "").strip())
            sector = datos.get("sector", "").strip()
            solicitante = datos.get("Solicitante", "").strip()
            progreso = datos.get("Progreso", "").strip()
            averia = datos.get("Averia", "").strip()

            if progreso == "Completado":
                msg = f"✅ *{equipo}*: Reparación *{id_}* completada, solicitada por *{solicitante}* del sector *{sector}* el *{fecha_formateada}*, Motivo de la solicitud *{averia}*."
            elif progreso == "Extemporaneo":
                msg = f"✅ *{equipo}*: Reparación *{id_}* completada con retraso, solicitada por *{solicitante}* del sector *{sector}* el *{fecha_formateada}*, Motivo de la solicitud *{averia}*."
            elif progreso == "Reprogramado":
                msg = f"⚠️ *{equipo}*: Reparación *{id_}* reprogramada, solicitada por *{solicitante}* del sector *{sector}* el *{fecha_formateada}*, Motivo de la solicitud *{averia}*."
            else:
                msg = f"❌ *{equipo}*: Reparación *{id_}* registrada, solicitada por *{solicitante}* del sector *{sector}* el *{fecha_formateada}*, Motivo de la solicitud *{averia}*."

            if enviar_texto(driver, GRUPO_DEFECTO_2, msg):
                contacto = obtener_contacto_valido(datos)
                if not contacto or enviar_texto_contacto(driver, contacto, msg):
                    shutil.move(ruta, os.path.join(reportado, archivo))
            time.sleep(3)
        except Exception as e:
            print("Error WAOM2 fase 2:", e)

# ================= MAIN =================

driver = iniciar_driver()

try:
    procesar_waom(driver)
    procesar_waom3(driver)
    procesar_waom2(driver)
finally:
    time.sleep(5)
    driver.quit()
