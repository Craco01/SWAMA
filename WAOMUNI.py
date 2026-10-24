import os
import json
import shutil
import time
import logging
import unicodedata
import ctypes
from datetime import datetime
from logging.handlers import RotatingFileHandler

from selenium import webdriver
from selenium.common.exceptions import TimeoutException
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

# Opcional: ruta a un chromedriver.exe local. Si se deja vacío, se usa
# webdriver_manager y, si éste falla (sin internet), Selenium Manager.
CHROMEDRIVER_LOCAL = ""

USER_DATA = r"C:\Users\Christian Redes\AppData\Local\Google\Chrome\User Data\Persona 1"

# ---- XPATH: NO MODIFICAR. Dependen del DOM actual de WhatsApp Web. ----
XPATH_BUSCADOR = '/html/body/div[2]/div/div/div/div/div[3]/div/div[3]/div/div[1]/div[1]/div/div/div/div/div/div[2]/input'
XPATH_RESULTADO_GRUPO = '//span[@title={grupo}]'
XPATH_MENSAJE = '/html/body/div[2]/div/div/div/div/div[3]/div/div[4]/div/footer/div[1]/div/span/div/div/div/div[3]/div[1]/p'
XPATH_MENSAJE_CONTACTO = '/html[1]/body[1]/div[2]/div[1]/div[1]/div[1]/div[1]/div[3]/div[1]/div[4]/div[1]/footer[1]/div[1]/div[1]/span[1]/div[1]/div[1]/div[1]/div[3]/div[1]'
# -----------------------------------------------------------------------

ESPERA_CONTACTO = 20

# True  = si no se encuentra el grupo en la búsqueda, NO se envía nada y el
#         archivo queda pendiente (evita enviar al chat equivocado).
# False = comportamiento anterior (envía al chat que esté abierto).
ABORTAR_SI_NO_ENCUENTRA_GRUPO = True

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

log = logging.getLogger("WAOMUNI")

# ================= GRUPOS =================

grupo_ids = {
    "Taller": "Taller Reporte Reparaciones",
    "Accesorios": "Accesorios Reporte Reparaciones",
    "Armado": "Armado Reporte Reparaciones",
    "Herreria": "Herrería Reporte Reparaciones",
    "Herrería": "Herrería Reporte Reparaciones",
    "Maquinado": "Maquinado Reporte Reparaciones",
    "Obras": "Obras Reporte Reparaciones",
    "Pintura": "Pintura Reporte Reparaciones",
    "Galvamax": "GALVAMAX Reporte Mantenimiento"
}

GRUPO_DEFECTO_1 = "Reparaciones MVSRL (Asignación y reporte de OM)"
GRUPO_DEFECTO_2 = "Reparaciones MVSRL (Asignación y reporte de OM)"

# ================= UTIL =================

def configurar_logging():
    log.setLevel(logging.INFO)
    if log.handlers:
        return
    formato = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    archivo = RotatingFileHandler(
        os.path.join(BASE_DIR, "WAOMUNI.log"),
        maxBytes=1_000_000, backupCount=3, encoding="utf-8"
    )
    archivo.setFormatter(formato)
    consola = logging.StreamHandler()
    consola.setFormatter(formato)
    log.addHandler(archivo)
    log.addHandler(consola)


def normalizar(texto):
    """Minúsculas y sin acentos, para comparar nombres de sector."""
    texto = unicodedata.normalize("NFKD", str(texto).strip().lower())
    return "".join(c for c in texto if not unicodedata.combining(c))


_GRUPOS_NORMALIZADOS = {normalizar(k): v for k, v in grupo_ids.items()}


def grupo_para_sector(sector, defecto):
    return _GRUPOS_NORMALIZADOS.get(normalizar(sector), defecto)


def campo(datos, clave):
    """Lee un campo del JSON como texto, aunque venga como número o null."""
    valor = datos.get(clave, "")
    return "" if valor is None else str(valor).strip()


def literal_xpath(texto):
    """Escapa un texto para usarlo dentro de un XPath."""
    if '"' not in texto:
        return f'"{texto}"'
    if "'" not in texto:
        return f"'{texto}'"
    partes = texto.split('"')
    return "concat(" + ", '\"', ".join(f'"{p}"' for p in partes) + ")"


DIAS = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]


def formatear_fecha(fecha_iso):
    try:
        fecha_obj = datetime.strptime(fecha_iso, "%Y-%m-%dT%H:%M:%SZ")
        # weekday() no depende del idioma configurado en Windows
        return f"{DIAS[fecha_obj.weekday()]}, {fecha_obj.strftime('%d/%m/%Y')}"
    except (ValueError, TypeError):
        return fecha_iso


def listar_json(carpeta):
    if not os.path.isdir(carpeta):
        return []
    return sorted(f for f in os.listdir(carpeta) if f.lower().endswith(".json"))


def leer_json(ruta):
    with open(ruta, encoding="utf-8") as f:
        return json.load(f)


def mover(ruta, carpeta_destino):
    """Mueve el archivo; si ya existe uno igual, agrega marca de tiempo."""
    os.makedirs(carpeta_destino, exist_ok=True)
    nombre = os.path.basename(ruta)
    destino = os.path.join(carpeta_destino, nombre)
    if os.path.exists(destino):
        base, extension = os.path.splitext(nombre)
        marca = datetime.now().strftime("%Y%m%d%H%M%S%f")
        destino = os.path.join(carpeta_destino, f"{base}_{marca}{extension}")
    shutil.move(ruta, destino)
    return destino

# ================= WHATSAPP =================

def crear_servicio():
    if CHROMEDRIVER_LOCAL and os.path.isfile(CHROMEDRIVER_LOCAL):
        return Service(CHROMEDRIVER_LOCAL)
    try:
        from webdriver_manager.chrome import ChromeDriverManager
        return Service(ChromeDriverManager().install())
    except Exception as e:
        log.warning("webdriver_manager falló (%s); usando Selenium Manager.", e)
        return Service()


def iniciar_driver():
    options = webdriver.ChromeOptions()
    options.add_argument(f"user-data-dir={USER_DATA}")
    options.add_argument("--start-maximized")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)

    driver = webdriver.Chrome(service=crear_servicio(), options=options)

    try:
        driver.get('https://web.whatsapp.com')
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.ID, "pane-side"))
        )
        return driver
    except TimeoutException:
        log.error(
            "WhatsApp Web no cargó la lista de chats en 30 s: ¿sesión "
            "cerrada (hay que escanear el QR) o sin conexión?"
        )
        cerrar_driver(driver)
        raise
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


def liberar_bloqueo_instancia(handle):
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.ReleaseMutex.argtypes = (ctypes.c_void_p,)
    kernel32.ReleaseMutex.restype = ctypes.c_bool
    kernel32.CloseHandle.argtypes = (ctypes.c_void_p,)
    kernel32.CloseHandle.restype = ctypes.c_bool
    kernel32.ReleaseMutex(handle)
    kernel32.CloseHandle(handle)


def cerrar_driver(driver):
    """Cierra el navegador y termina ChromeDriver si Selenium no pudo hacerlo."""
    if driver is None:
        return

    try:
        driver.quit()
    except Exception as e:
        log.warning("Error al cerrar Chrome mediante Selenium: %s", e)
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
                    log.error("No se pudo terminar ChromeDriver: %s", e)


# Alternativas por si WhatsApp cambia el DOM; solo se usan si el XPATH falla.
XPATH_MENSAJE_ALT = '//footer//div[@contenteditable="true"][@role="textbox"]'
XPATH_BUSCADOR_ALT = '//div[@id="side"]//input[@role="textbox" or @type="text" or @type="search"] | //div[@id="side"]//div[@contenteditable="true"][@role="textbox"]'


def esperar_clickable(driver, xpath, xpath_alt, espera=30):
    """Usa primero la alternativa (vigente); el XPATH original queda de respaldo."""
    try:
        return WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, xpath_alt))
        )
    except TimeoutException:
        log.warning("Alternativa sin resultado, usando XPATH original: %s", xpath)
        return WebDriverWait(driver, espera).until(
            EC.element_to_be_clickable((By.XPATH, xpath))
        )


def obtener_caja_mensaje(driver):
    return esperar_clickable(driver, XPATH_MENSAJE, XPATH_MENSAJE_ALT)


def limpiar_caja(message_box):
    """Vacía la caja de mensaje para no arrastrar texto a otro envío."""
    try:
        message_box.send_keys(Keys.CONTROL, "a")
        message_box.send_keys(Keys.DELETE)
    except Exception as e:
        log.warning("No se pudo limpiar la caja de mensaje: %s", e)


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


def abrir_chat_grupo(driver, grupo):
    """Busca el grupo y abre su chat. Devuelve False si no lo encuentra."""
    search_box = esperar_clickable(driver, XPATH_BUSCADOR, XPATH_BUSCADOR_ALT)
    search_box.click()
    search_box.send_keys(Keys.CONTROL, "a")
    search_box.send_keys(Keys.DELETE)
    search_box.send_keys(grupo)
    time.sleep(1)

    xpath = XPATH_RESULTADO_GRUPO.format(grupo=literal_xpath(grupo))
    try:
        resultado = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, xpath))
        )
    except TimeoutException:
        log.warning("Grupo no encontrado en la búsqueda: %s", grupo)
        return not ABORTAR_SI_NO_ENCUENTRA_GRUPO

    resultado.click()
    time.sleep(1)
    return True


def enviar_texto(driver, grupo, mensaje, abrir=True):
    try:
        if abrir and not abrir_chat_grupo(driver, grupo):
            return False

        message_box = obtener_caja_mensaje(driver)
        message_box.click()
        message_box.send_keys(mensaje)

        message_box.send_keys(Keys.ENTER)
        time.sleep(0.5)
        return True
    except Exception as e:
        log.error("Error enviando mensaje al grupo '%s': %s", grupo, e)
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
                XPATH_MENSAJE_ALT
            ) or pagina.find_elements(By.XPATH, XPATH_MENSAJE_CONTACTO)

        try:
            WebDriverWait(driver, ESPERA_CONTACTO).until(chat_disponible_o_invalido)
        except Exception:
            log.warning("Sin respuesta para 595%s; refrescando WhatsApp Web.", numero)
            driver.refresh()
            try:
                WebDriverWait(driver, ESPERA_CONTACTO).until(chat_disponible_o_invalido)
            except Exception:
                log.warning("Contacto 595%s omitido: WhatsApp no respondió.", numero)
                return False

        if numero_no_disponible(driver):
            log.info("Contacto 595%s omitido: no tiene WhatsApp.", numero)
            return True

        message_box = esperar_clickable(driver, XPATH_MENSAJE_CONTACTO, XPATH_MENSAJE_ALT)
        driver.execute_script(
            "arguments[0].scrollIntoView({block: 'center'}); arguments[0].focus();",
            message_box
        )
        message_box.click()
        message_box.send_keys(mensaje)

        # Basta con que el texto haya entrado (los emojis pueden alterar la comparación exacta)
        WebDriverWait(driver, 10).until(
            lambda _: message_box.get_attribute("textContent").strip()
        )
        time.sleep(1)

        message_box.send_keys(Keys.ENTER)
        try:
            WebDriverWait(driver, 10).until(
                lambda _: not message_box.get_attribute("textContent").strip()
            )
        except Exception:
            # Reintento: a veces el primer ENTER no se registra
            message_box.send_keys(Keys.ENTER)
            WebDriverWait(driver, 10).until(
                lambda _: not message_box.get_attribute("textContent").strip()
            )
        time.sleep(1)
        return True
    except Exception as e:
        log.error("Error enviando mensaje a 595%s: %s", numero, e)
        return False


def mencionar(message_box, nombre):
    partes = nombre.split()
    if not partes:
        raise ValueError("nombre vacío para mención")
    corto = partes[0]
    message_box.send_keys("@")
    time.sleep(1)
    message_box.send_keys(corto)
    time.sleep(1)
    message_box.send_keys(Keys.ARROW_DOWN)
    time.sleep(0.4)
    message_box.send_keys(Keys.ENTER)
    time.sleep(0.4)


def enviar_con_menciones(driver, grupo, datos, abrir=True):
    message_box = None
    try:
        # Validar ANTES de escribir nada en el chat
        faltantes = [k for k in ("ID", "Prioridad", "Maquina", "Averia", "Responsable")
                     if k not in datos]
        if faltantes:
            log.error("Faltan campos en el JSON: %s", ", ".join(faltantes))
            return False
        responsable = campo(datos, "Responsable")
        if not responsable:
            log.error("Solicitud %s sin Responsable; no se envía.", campo(datos, "ID"))
            return False

        if abrir and not abrir_chat_grupo(driver, grupo):
            return False

        message_box = obtener_caja_mensaje(driver)
        message_box.click()

        message_box.send_keys(
            f" Para asistir la *Solicitud de Mantenimiento* N° *{campo(datos, 'ID')}*, "
            f"con prioridad *{campo(datos, 'Prioridad')}*, para *{campo(datos, 'Maquina')}* "
            f"que reporta *{campo(datos, 'Averia')}*, los técnicos asignados son "
        )
        mencionar(message_box, responsable)

        apoyo = campo(datos, "Apoyo")
        if apoyo:
            message_box.send_keys(" con apoyo de ")
            mencionar(message_box, apoyo)
        message_box.send_keys(".")

        message_box.send_keys(Keys.ENTER)
        time.sleep(0.5)
        return True
    except Exception as e:
        log.error("Error menciones: %s", e)
        if message_box is not None:
            limpiar_caja(message_box)
        return False

# ================= MENSAJES =================

def construir_mensaje_waom(datos):
    id_ = campo(datos, "ID")
    equipo = campo(datos, "equipo")
    fecha = formatear_fecha(campo(datos, "Fecha"))
    sector = campo(datos, "sector")
    solicitante = campo(datos, "Solicitante")
    averia = campo(datos, "Averia")
    prioridad = campo(datos, "Prioridad")
    msg = (
        f" ❌ Solicitud de mantenimiento ID: *{id_}* registrada para *{equipo}* "
        f"con prioridad *{prioridad}*, (Motivo de la solicitud << *{averia}* >>),"
        f"Solicitado por *{solicitante}* del sector *{sector}* el *{fecha}*."
    )
    return msg, False


def construir_mensaje_waom2(datos):
    """Devuelve (mensaje, es_registro). es_registro=True si es el aviso inicial."""
    id_ = campo(datos, "ID")
    equipo = campo(datos, "equipo")
    fecha = formatear_fecha(campo(datos, "Fecha"))
    sector = campo(datos, "sector")
    solicitante = campo(datos, "Solicitante")
    progreso = campo(datos, "Progreso")
    averia = campo(datos, "Averia")

    detalle = (
        f"solicitada por *{solicitante}* del sector *{sector}* el *{fecha}*, "
        f"Motivo de la solicitud *{averia}*."
    )
    if progreso == "Completado":
        return f"✅ *{equipo}*: Reparación *{id_}* completada, {detalle}", False
    if progreso == "Extemporaneo":
        return f"✅ *{equipo}*: Reparación *{id_}* completada con retraso, {detalle}", False
    if progreso == "Reprogramado":
        return f"⚠️ *{equipo}*: Reparación *{id_}* reprogramada, {detalle}", False
    return f"❌ *{equipo}*: Reparación *{id_}* registrada, {detalle}", True

# ================= PROCESOS (WAOM, WAOM2, WAOM3) =================

def procesar_flujo(driver, nombre, carpeta, construir_mensaje, grupo_defecto, ids_omitir=None):
    """
    Flujo de carpetas para WAOM y WAOM2:

      raíz ──(grupo del sector)──► Prereportado
      Prereportado ──(grupo por defecto)──► ContactoPendiente  (si hay contacto válido)
                                         └► Reportado          (si no hay contacto)
      ContactoPendiente ──(mensaje al contacto)──► Reportado

    ContactoPendiente evita reenviar al grupo cuando solo falla el contacto.
    """
    prereportado = os.path.join(carpeta, "Prereportado")
    contacto_pendiente = os.path.join(carpeta, "ContactoPendiente")
    reportado = os.path.join(carpeta, "Reportado")
    for sub in (prereportado, contacto_pendiente, reportado):
        os.makedirs(sub, exist_ok=True)

    ids_omitir = ids_omitir or set()

    def mensaje_o_omitir(datos):
        msg, es_registro = construir_mensaje(datos)
        if es_registro and campo(datos, "ID") in ids_omitir:
            return None
        return msg

    # FASE 1: grupo del sector
    for archivo in listar_json(carpeta):
        ruta = os.path.join(carpeta, archivo)
        try:
            datos = leer_json(ruta)
            msg = mensaje_o_omitir(datos)
            if msg is None:
                mover(ruta, reportado)
                log.info("%s omitido: la solicitud %s ya fue enviada por WAOM.",
                         nombre, campo(datos, "ID"))
                continue

            grupo = grupo_para_sector(campo(datos, "sector"), grupo_defecto)
            if enviar_texto(driver, grupo, msg):
                mover(ruta, prereportado)
            time.sleep(3)
        except Exception as e:
            log.exception("Error %s fase 1 (%s): %s", nombre, archivo, e)

    # FASE 2: grupo por defecto (se abre una sola vez)
    pendientes = listar_json(prereportado)
    grupo_abierto = False
    if pendientes:
        try:
            grupo_abierto = abrir_chat_grupo(driver, grupo_defecto)
        except Exception as e:
            log.exception("Error %s abriendo grupo por defecto: %s", nombre, e)
        if not grupo_abierto:
            log.error("%s: no se pudo abrir el grupo por defecto; fase 2 omitida.", nombre)

    for archivo in pendientes if grupo_abierto else []:
        ruta = os.path.join(prereportado, archivo)
        try:
            datos = leer_json(ruta)
            msg = mensaje_o_omitir(datos)
            if msg is None:
                mover(ruta, reportado)
                log.info("%s omitido: la solicitud %s ya fue enviada por WAOM.",
                         nombre, campo(datos, "ID"))
                continue

            if enviar_texto(driver, grupo_defecto, msg, abrir=False):
                if obtener_contacto_valido(datos):
                    mover(ruta, contacto_pendiente)
                else:
                    mover(ruta, reportado)
            time.sleep(3)
        except Exception as e:
            log.exception("Error %s fase 2 (%s): %s", nombre, archivo, e)

    # FASE 3: contacto directo
    for archivo in listar_json(contacto_pendiente):
        ruta = os.path.join(contacto_pendiente, archivo)
        try:
            datos = leer_json(ruta)
            msg, _ = construir_mensaje(datos)
            contacto = obtener_contacto_valido(datos)
            if contacto and not enviar_texto_contacto(driver, contacto, msg):
                log.warning("%s: no se envió al contacto de %s; pasa a Reportado.",
                            nombre, archivo)
            mover(ruta, reportado)
            time.sleep(3)
        except Exception as e:
            log.exception("Error %s fase 3 (%s): %s", nombre, archivo, e)
            try:
                mover(ruta, reportado)
            except Exception:
                pass


def procesar_waom(driver):
    procesar_flujo(
        driver, "WAOM", RUTAS["WAOM"],
        construir_mensaje_waom, GRUPO_DEFECTO_1
    )


def ids_enviados_por_waom():
    """IDs que WAOM ya notificó (para que WAOM2 no repita el aviso de registro)."""
    ids = set()
    for estado in ("Prereportado", "ContactoPendiente", "Reportado"):
        carpeta = os.path.join(RUTAS["WAOM"], estado)
        for archivo in listar_json(carpeta):
            ruta = os.path.join(carpeta, archivo)
            try:
                id_waom = campo(leer_json(ruta), "ID")
                if id_waom:
                    ids.add(id_waom)
            except (OSError, json.JSONDecodeError) as e:
                log.warning("Error leyendo %s para evitar duplicados WAOM2: %s", ruta, e)
    return ids


def procesar_waom2(driver):
    procesar_flujo(
        driver, "WAOM2", RUTAS["WAOM2"],
        construir_mensaje_waom2, GRUPO_DEFECTO_2,
        ids_omitir=ids_enviados_por_waom()
    )


def procesar_waom3(driver):
    carpeta = RUTAS["WAOM3"]
    reportado = os.path.join(carpeta, "Reportado")
    en_proceso = os.path.join(carpeta, "EnProceso")
    duplicados = os.path.join(carpeta, "Duplicados")
    os.makedirs(reportado, exist_ok=True)
    os.makedirs(en_proceso, exist_ok=True)

    grupo_abierto = False
    for archivo in listar_json(carpeta):
        ruta = os.path.join(carpeta, archivo)
        ruta_proceso = os.path.join(en_proceso, archivo)
        ruta_reportado = os.path.join(reportado, archivo)
        try:
            if os.path.exists(ruta_reportado):
                mover(ruta, duplicados)
                log.info("WAOM3 omitido: %s ya figura en Reportado.", archivo)
                continue

            # Reclamar el archivo: rename falla si ya está en proceso
            os.rename(ruta, ruta_proceso)
        except FileNotFoundError:
            continue
        except FileExistsError:
            log.info("WAOM3 omitido: %s ya está en proceso.", archivo)
            continue

        try:
            datos = leer_json(ruta_proceso)
            if enviar_con_menciones(driver, GRUPO_DEFECTO_1, datos, abrir=not grupo_abierto):
                grupo_abierto = True
                mover(ruta_proceso, reportado)
            else:
                log.warning(
                    "WAOM3 requiere revisión: %s permanece en %s; "
                    "no se reintentará automáticamente.", archivo, en_proceso
                )
            time.sleep(3)
        except Exception as e:
            log.exception("Error WAOM3: %s", e)
            log.warning(
                "El archivo %s permanece en %s para evitar un reenvío automático.",
                archivo, en_proceso
            )

# ================= MAIN =================

def ejecutar(nombre, funcion, driver):
    """Aísla cada proceso: si uno falla de forma inesperada, los demás siguen."""
    try:
        funcion(driver)
    except Exception as e:
        log.exception("Fallo inesperado en %s: %s", nombre, e)


def main():
    configurar_logging()
    mutex = adquirir_bloqueo_instancia()
    if mutex is None:
        log.warning("WAOMUNI ya está ejecutándose; esta instancia termina sin enviar mensajes.")
        return

    driver = None
    try:
        driver = iniciar_driver()
        ejecutar("WAOM", procesar_waom, driver)
        ejecutar("WAOM2", procesar_waom2, driver)
        ejecutar("WAOM3", procesar_waom3, driver)
    except Exception:
        log.exception("Error fatal al iniciar WAOMUNI")
        raise
    finally:
        try:
            cerrar_driver(driver)
        finally:
            liberar_bloqueo_instancia(mutex)


if __name__ == "__main__":
    main()
