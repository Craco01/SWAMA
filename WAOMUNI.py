import os
import json
import shutil
import time
import unicodedata
import ctypes
from datetime import datetime

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# ================= CONFIG =================

RUTAS = {
    "WAOM": r'C:\Users\Christian Redes\OneDrive - Grupo MV\Escritorio\WAOM',
    "WAOM3": r'C:\Users\Christian Redes\OneDrive - Grupo MV\Escritorio\WAOM3',
    "WAOM2": r'C:\Users\Christian Redes\OneDrive - Grupo MV\Escritorio\WAOM2'
}

#CHROMEDRIVER = r'C:\Users\Christian Redes\OneDrive - Grupo MV\Escritorio\Reportes WA con Selenium\MSJ AUTO\chromedriver\win64-133.0.6943.53\chromedriver-win64\chromedriver.exe'
USER_DATA = r"C:\Users\Christian Redes\AppData\Local\Google\Chrome\User Data\Persona 1"
XPATH_BUSCADOR = '/html/body/div[2]/div/div/div/div/div[3]/div/div[3]/div/div[1]/div[1]/div/div/div/div/div/div[2]/input'
XPATH_RESULTADO_GRUPO = '//span[@title="{grupo}"]'
XPATH_MENSAJE = '/html/body/div[2]/div/div/div/div/div[3]/div/div[4]/div/footer/div[1]/div/span/div/div/div/div[3]/div[1]/p'
XPATH_MENSAJE_CONTACTO = '/html[1]/body[1]/div[2]/div[1]/div[1]/div[1]/div[1]/div[3]/div[1]/div[4]/div[1]/footer[1]/div[1]/div[1]/span[1]/div[1]/div[1]/div[1]/div[3]/div[1]'
ESPERA_CONTACTO = 20

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

    try:
        driver.get('https://web.whatsapp.com')
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.ID, "pane-side"))
        )
        return driver
    except Exception:
        cerrar_driver(driver)
        raise

def adquirir_bloqueo_instancia():
    """Impide que dos procesos WAOMUNI trabajen al mismo tiempo en Windows."""
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.CreateMutexW.argtypes = (ctypes.c_void_p, ctypes.c_bool, ctypes.c_wchar_p)
    kernel32.CreateMutexW.restype = ctypes.c_void_p
    kernel32.CloseHandle.argtypes = (ctypes.c_void_p,)
    kernel32.CloseHandle.restype = ctypes.c_bool

    handle = kernel32.CreateMutexW(None, True, "Local\\WAOMUNI_Selenium_SingleInstance_v1")
    if not handle:
        raise ctypes.WinError(ctypes.get_last_error())

    # ERROR_ALREADY_EXISTS: el mutex ya pertenece a otra instancia.
    if ctypes.get_last_error() == 183:
        kernel32.CloseHandle(handle)
        return None
    return handle

def cerrar_driver(driver):
    """Cierra el navegador y termina ChromeDriver si Selenium no pudo hacerlo."""
    if driver is None:
        return

    try:
        driver.quit()
    except Exception as e:
        print("Error al cerrar Chrome mediante Selenium:", e)
    finally:
        servicio = getattr(driver, "service", None)
        proceso = getattr(servicio, "process", None)
        if proceso is not None and proceso.poll() is None:
            try:
                proceso.terminate()
                proceso.wait(timeout=5)
            except Exception:
                try:
                    proceso.kill()
                    proceso.wait(timeout=5)
                except Exception as e:
                    print("No se pudo terminar ChromeDriver:", e)

def obtener_caja_mensaje(driver):
    return WebDriverWait(driver, 30).until(
        EC.element_to_be_clickable((By.XPATH, XPATH_MENSAJE))
    )

def numero_no_disponible(driver):
    texto = driver.find_element(By.TAG_NAME, "body").text.lower()
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(caracter for caracter in texto if not unicodedata.combining(caracter))

    aviso_es = "numero de telefono" in texto and any(
        frase in texto
        for frase in ("no es valido", "no esta disponible", "no esta registrado")
    )
    aviso_en = "phone number" in texto and any(
        frase in texto
        for frase in ("is invalid", "is not available", "isn't on whatsapp")
    )
    return aviso_es or aviso_en

def enviar_texto(driver, grupo, mensaje):
    try:
        # Buscar grupo
        search_box = WebDriverWait(driver, 30).until(
            EC.element_to_be_clickable((By.XPATH, XPATH_BUSCADOR))
        )
        search_box.click()
        search_box.clear()
        search_box.send_keys(grupo)
        time.sleep(2)

        resultados = driver.find_elements(
            By.XPATH,
            XPATH_RESULTADO_GRUPO.format(grupo=grupo)
        )
        if resultados:
            resultados[0].click()
            time.sleep(1)

        # Caja de mensaje
        message_box = obtener_caja_mensaje(driver)
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

        time.sleep(5)

        def chat_disponible_o_invalido(pagina):
            return numero_no_disponible(pagina) or pagina.find_elements(
                By.XPATH,
                XPATH_MENSAJE_CONTACTO
            )

        try:
            WebDriverWait(driver, ESPERA_CONTACTO).until(chat_disponible_o_invalido)
        except Exception:
            print(f"Sin respuesta para 595{numero}; refrescando WhatsApp Web.")
            driver.refresh()
            try:
                WebDriverWait(driver, ESPERA_CONTACTO).until(chat_disponible_o_invalido)
            except Exception:
                print(f"Contacto 595{numero} omitido: WhatsApp no respondió.")
                return False

        if numero_no_disponible(driver):
            print(f"Contacto 595{numero} omitido: no tiene WhatsApp.")
            return True

        message_box = WebDriverWait(driver, ESPERA_CONTACTO).until(
            EC.element_to_be_clickable((By.XPATH, XPATH_MENSAJE_CONTACTO))
        )
        driver.execute_script(
            "arguments[0].scrollIntoView({block: 'center'}); arguments[0].focus();",
            message_box
        )
        message_box.click()
        message_box.send_keys(mensaje)

        WebDriverWait(driver, 10).until(
            lambda _: mensaje in message_box.get_attribute("textContent")
        )

        message_box.send_keys(Keys.ENTER)
        WebDriverWait(driver, 10).until(
            lambda _: not message_box.get_attribute("textContent").strip()
        )
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
            EC.element_to_be_clickable((By.XPATH, XPATH_BUSCADOR))
        )
        search_box.click()
        search_box.clear()
        search_box.send_keys(grupo)
        time.sleep(2)

        resultados = driver.find_elements(
            By.XPATH,
            XPATH_RESULTADO_GRUPO.format(grupo=grupo)
        )
        if resultados:
            resultados[0].click()
            time.sleep(1)

        # Caja de mensaje
        message_box = obtener_caja_mensaje(driver)
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
    en_proceso = os.path.join(carpeta, "EnProceso")
    duplicados = os.path.join(carpeta, "Duplicados")
    os.makedirs(reportado, exist_ok=True)
    os.makedirs(en_proceso, exist_ok=True)
    archivos = [f for f in os.listdir(carpeta) if f.endswith(".json")]

    for archivo in archivos:
        ruta = os.path.join(carpeta, archivo)
        ruta_proceso = os.path.join(en_proceso, archivo)
        ruta_reportado = os.path.join(reportado, archivo)
        try:
            if os.path.exists(ruta_reportado):
                os.makedirs(duplicados, exist_ok=True)
                destino_duplicado = os.path.join(duplicados, archivo)
                if os.path.exists(destino_duplicado):
                    nombre, extension = os.path.splitext(archivo)
                    marca_tiempo = datetime.now().strftime("%Y%m%d%H%M%S%f")
                    destino_duplicado = os.path.join(
                        duplicados, f"{nombre}_{marca_tiempo}{extension}"
                    )
                shutil.move(ruta, destino_duplicado)
                print(f"WAOM3 omitido: {archivo} ya figura en Reportado.")
                continue

            os.rename(ruta, ruta_proceso)
        except FileNotFoundError:
            continue
        except FileExistsError:
            print(f"WAOM3 omitido: {archivo} ya está en proceso.")
            continue

        try:
            with open(ruta_proceso, encoding='utf-8') as f:
                datos = json.load(f)
            if enviar_con_menciones(driver, GRUPO_DEFECTO_1, datos):
                shutil.move(ruta_proceso, ruta_reportado)
            else:
                print(
                    f"WAOM3 requiere revisión: {archivo} permanece en "
                    f"{en_proceso}; no se reintentará automáticamente."
                )
            time.sleep(3)
        except Exception as e:
            print("Error WAOM3:", e)
            print(
                f"El archivo {archivo} permanece en {en_proceso} "
                "para evitar un reenvío automático."
            )

def procesar_waom2(driver):
    carpeta = RUTAS["WAOM2"]
    prereportado = os.path.join(carpeta, "Prereportado")
    reportado = os.path.join(carpeta, "Reportado")
    os.makedirs(prereportado, exist_ok=True)
    os.makedirs(reportado, exist_ok=True)

    ids_waom_enviados = set()
    for estado in ("Prereportado", "Reportado"):
        waom_estado = os.path.join(RUTAS["WAOM"], estado)
        if not os.path.isdir(waom_estado):
            continue
        for archivo in os.listdir(waom_estado):
            if not archivo.endswith(".json"):
                continue
            ruta_waom = os.path.join(waom_estado, archivo)
            try:
                with open(ruta_waom, encoding='utf-8') as f:
                    datos_waom = json.load(f)
                id_waom = str(datos_waom.get("ID", "")).strip()
                if id_waom:
                    ids_waom_enviados.add(id_waom)
            except (OSError, json.JSONDecodeError) as e:
                print(
                    f"Error leyendo {ruta_waom} para evitar duplicados WAOM2:",
                    e
                )

    archivos = [f for f in os.listdir(carpeta) if f.endswith(".json")]

    # FASE 1
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
            progreso = datos.get("Progreso", "").strip()
            averia = datos.get("Averia", "").strip()

            if progreso == "Completado":
                msg = f"✅ *{equipo}*: Reparación *{id_}* completada, solicitada por *{solicitante}* del sector *{sector}* el *{fecha_formateada}*, Motivo de la solicitud *{averia}*."
            elif progreso == "Extemporaneo":
                msg = f"✅ *{equipo}*: Reparación *{id_}* completada con retraso, solicitada por *{solicitante}* del sector *{sector}* el *{fecha_formateada}*, Motivo de la solicitud *{averia}*."
            elif progreso == "Reprogramado":
                msg = f"⚠️ *{equipo}*: Reparación *{id_}* reprogramada, solicitada por *{solicitante}* del sector *{sector}* el *{fecha_formateada}*, Motivo de la solicitud *{averia}*."
            else:
                if id_ in ids_waom_enviados:
                    shutil.move(ruta, os.path.join(reportado, archivo))
                    print(
                        f"WAOM2 omitido: el registro de la solicitud {id_} "
                        "ya fue enviado por WAOM."
                    )
                    continue
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
                if id_ in ids_waom_enviados:
                    shutil.move(ruta, os.path.join(reportado, archivo))
                    print(
                        f"WAOM2 omitido: el registro de la solicitud {id_} "
                        "ya fue enviado por WAOM."
                    )
                    continue
                msg = f"❌ *{equipo}*: Reparación *{id_}* registrada, solicitada por *{solicitante}* del sector *{sector}* el *{fecha_formateada}*, Motivo de la solicitud *{averia}*."

            if enviar_texto(driver, GRUPO_DEFECTO_2, msg):
                contacto = obtener_contacto_valido(datos)
                if not contacto or enviar_texto_contacto(driver, contacto, msg):
                    shutil.move(ruta, os.path.join(reportado, archivo))
            time.sleep(3)
        except Exception as e:
            print("Error WAOM2 fase 2:", e)

# ================= MAIN =================

mutex = adquirir_bloqueo_instancia()
if mutex is None:
    print("WAOMUNI ya está ejecutándose; esta instancia termina sin enviar mensajes.")
else:
    driver = None
    try:
        driver = iniciar_driver()
        procesar_waom(driver)
        procesar_waom3(driver)
        procesar_waom2(driver)
    finally:
        try:
            cerrar_driver(driver)
        finally:
            kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
            kernel32.ReleaseMutex.argtypes = (ctypes.c_void_p,)
            kernel32.ReleaseMutex.restype = ctypes.c_bool
            kernel32.CloseHandle.argtypes = (ctypes.c_void_p,)
            kernel32.CloseHandle.restype = ctypes.c_bool
            kernel32.ReleaseMutex(mutex)
            kernel32.CloseHandle(mutex)
