"""Envía los recordatorios de WhatsApp según el número indicado.

Uso: python mensajes.py <1-6>
"""

import sys
import time
import traceback
from datetime import datetime
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager


PERFIL_CHROME = r"C:\Users\Christian Redes\AppData\Local\Google\Chrome\User Data\Persona 1"
GRUPO_NOMBRE = "Reparaciones MVSRL (Asignación y reporte de OM)"
XPATH_BUSCADOR = '/html/body/div[2]/div/div/div/div/div[3]/div/div[3]/div/div[1]/div[1]/div/div/div/div/div/div[2]/input'
XPATH_RESULTADO_GRUPO = '//span[@title="{grupo}"]'
XPATH_MENSAJE = '/html/body/div[2]/div/div/div/div/div[3]/div/div[4]/div/footer/div[1]/div/span/div/div/div/div[3]/div[1]/p'
XPATH_BOTON_CONTINUAR = '//a[contains(@href,"web.whatsapp.com/send")]'
ARCHIVO_LOG = Path(__file__).with_name("mensajes.log")


def registrar(texto):
    """Guarda el resultado porque los .vbs ejecutan el proceso oculto."""
    marca_tiempo = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with ARCHIVO_LOG.open("a", encoding="utf-8") as archivo:
        archivo.write(f"[{marca_tiempo}] {texto}\n")


def esperar_elemento_clickable(driver, xpath, timeout=30):
    """Espera un elemento de WhatsApp Web usando su XPath completo."""
    return WebDriverWait(driver, timeout).until(
        EC.element_to_be_clickable((By.XPATH, xpath))
    )


def crear_driver():
    """Abre Chrome con el perfil que ya tiene iniciada la sesión de WhatsApp."""
    opciones = webdriver.ChromeOptions()
    opciones.add_argument(f"user-data-dir={PERFIL_CHROME}")
    opciones.add_argument("--start-maximized")
    opciones.add_argument("--disable-blink-features=AutomationControlled")
    opciones.add_experimental_option(
        "excludeSwitches",
        ["enable-automation"]
    )
    opciones.add_experimental_option(
        "useAutomationExtension",
        False
    )

    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=opciones
    )

    driver.get("https://web.whatsapp.com")

    WebDriverWait(driver, 60).until(
        EC.presence_of_element_located((By.ID, "app"))
    )

    time.sleep(3)

    return driver


def abrir_grupo(driver):
    buscador = esperar_elemento_clickable(
        driver,
        XPATH_BUSCADOR
    )

    buscador.click()
    buscador.send_keys(Keys.CONTROL, "a")
    buscador.send_keys(Keys.BACKSPACE)
    buscador.send_keys(GRUPO_NOMBRE)

    time.sleep(2)

    resultados = driver.find_elements(
        By.XPATH,
        XPATH_RESULTADO_GRUPO.format(grupo=GRUPO_NOMBRE)
    )

    if resultados:
        resultados[0].click()
    else:
        # Es el método de los scripts originales 1, 2 y 3;
        # sirve cuando el nombre no está expuesto en el atributo
        # title por una nueva versión.
        buscador.send_keys(Keys.ARROW_DOWN)
        buscador.send_keys(Keys.ENTER)

    time.sleep(1)


def caja_mensaje(driver):
    return esperar_elemento_clickable(
        driver,
        XPATH_MENSAJE
    )


def enviar_texto(driver, texto):
    caja = caja_mensaje(driver)

    caja.click()
    caja.send_keys(texto)
    caja.send_keys(Keys.ENTER)

    # WhatsApp envía de forma asíncrona;
    # no cerrar Chrome justo tras Enter.
    time.sleep(1)


def enviar_mencion(driver, texto, nombre):
    caja = caja_mensaje(driver)

    caja.click()
    caja.send_keys(texto)
    caja.send_keys("@")

    time.sleep(1)

    caja.send_keys(nombre)

    time.sleep(0.5)

    caja.send_keys(Keys.ARROW_DOWN)

    time.sleep(0.3)

    caja.send_keys(Keys.ENTER)
    caja.send_keys(".")
    caja.send_keys(Keys.ENTER)


def enviar_directo(driver, numero, texto):
    driver.get(
        f"https://web.whatsapp.com/send?phone={numero}"
    )

    time.sleep(5)

    try:
        boton_continuar = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable(
                (
                    By.XPATH,
                    XPATH_BOTON_CONTINUAR
                )
            )
        )

        boton_continuar.click()

        time.sleep(5)

    except Exception:
        # El botón no aparece cuando WhatsApp abre el chat directamente.
        pass

    enviar_texto(driver, texto)

    # Los chats abiertos por URL necesitan un margen adicional
    # para que el mensaje salga de la cola antes de que el
    # finally cierre el navegador.
    time.sleep(4)


def ejecutar_automatizacion(accion):
    driver = None

    try:
        registrar("Inicio de la automatización.")

        driver = crear_driver()

        accion(driver)

        registrar("Mensaje(s) enviado(s) correctamente.")

        print("Mensaje(s) enviado(s) correctamente.")

    except Exception as error:
        detalle = "".join(
            traceback.format_exception(
                type(error),
                error,
                error.__traceback__
            )
        )

        registrar(f"ERROR: {detalle}")

        print(
            f"Error durante la automatización: {error}"
        )

    finally:
        if driver:
            driver.quit()

        registrar("Navegador cerrado.")

        print("Navegador cerrado.")


def enviar_mensaje_1():
    """Mensaje diario general de seguridad, Pegasus, materiales y equipos."""

    def accion(driver):
        abrir_grupo(driver)

        hoy = datetime.now()

        dias = {
            "Monday": "Lunes",
            "Tuesday": "Martes",
            "Wednesday": "Miércoles",
            "Thursday": "Jueves",
            "Friday": "Viernes",
            "Saturday": "Sábado",
            "Sunday": "Domingo",
        }

        mensaje_fecha = (
            f"Mensaje Automático: hoy {dias[hoy.strftime('%A')]} "
            f"{hoy.strftime('%d/%m/%Y')}, es el día número "
            f"{hoy.timetuple().tm_yday} del año, la semana "
            f"{hoy.isocalendar()[1]} del {hoy.year}."
        )

        mensajes = [
            mensaje_fecha,

            "Recordatorio Automático: Todos los trabajos en altura requieren la elaboración de PTA y ATS.",

            "Asegúrense de:",
            "- Completarlos correctamente.",
            "- Que todas las partes los firmen.",
            "- Entregarlos a SIHO.",

            "Además, recuerden que:",
            "- Es obligatorio el uso de equipo de protección personal (EPP): arnés de seguridad, línea de vida, casco con barboquejo, calzado de seguridad, guantes y cualquier otro requerido según la tarea.",
            "- Verifiquen el estado de los equipos antes de utilizarlos.",
            "- Mantengan orden y comunicación constante durante la ejecución de la tarea.",
            "- La seguridad es responsabilidad individual y colectiva: cada uno debe cuidarse a sí mismo y a sus compañeros.",
            "¡Trabajemos seguros, la prevención salva vidas!",

            "Recordatorio Automático: Solo serán registradas en el sistema Pegasus las entradas de los equipos que ingresen físicamente al taller (ejemplos: amoladoras, mini amoladoras, equipos de soldar).",

            "- Aquellos equipos que no ingresen físicamente al taller deberán ser registrados en la página de mantenimiento vía formulario de solicitud de mantenimiento (ejemplos: sierra taladro, arco sumergido, puente grúa, reparación de luces, reparación de tomas).",

            "- Todos los miembros del área de mantenimiento están habilitados para realizar solicitudes y efectuar el cierre correspondiente.",

            "- Todos los materiales e insumos utilizados por el departamento serán retirados del depósito correspondiente a la OT 25611 (Depósito de Gastos de Mantenimiento).",

            "- Es requisito obligatorio que todos los insumos y materiales estén previamente habilitados.",

            "- La habilitación debe ser solicitada a Gustavo González, Blas Giménez o Cristhian Redes.",

            "- Para la habilitación y el retiro, se deberá indicar el número de la solicitud en el List correspondiente.",

            "- No se habilitarán materiales si el trabajo no cuenta con una solicitud abierta, salvo en casos excepcionales debidamente justificados.",

            "- Este procedimiento también aplica para herramientas, pudiendo existir criterios adicionales.",

            "- Al recibir herramientas o equipos, es obligatorio verificar su estado y registrarlo.",

            "- En caso de faltantes o anomalías no documentadas, la responsabilidad recaerá sobre quien realiza la recepción.",

            "- Verificación obligatoria en los siguientes equipos:",

            "  • Migmag - Cable y Pinza a Maza/Tierra, Manómetro de CO2.",

            "  • Soldadores MMA - Cables y Pinza a Maza/Tierra y PortaElectrodo.",

            "  • Amoladoras y Miniamoladoras - Protector de disco, Puño Lateral/Mango.",
        ]

        for mensaje in mensajes:
            enviar_texto(driver, mensaje)
            time.sleep(0.3)

    ejecutar_automatizacion(accion)


def enviar_mensaje_2():
    """Inicio del horario de descanso."""

    ejecutar_automatizacion(
        lambda driver: (
            abrir_grupo(driver),
            enviar_texto(
                driver,
                "Recordatorio Automático: Inicio del horario de descanso, no olviden marcar."
            )
        )
    )


def enviar_mensaje_3():
    """Fin del horario de descanso."""

    ejecutar_automatizacion(
        lambda driver: (
            abrir_grupo(driver),
            enviar_texto(
                driver,
                "Recordatorio Automático: Fin de horario de descanso, no olviden marcar."
            )
        )
    )


def enviar_mensaje_4():
    """Hora de limpiar y ordenar el taller."""

    ejecutar_automatizacion(
        lambda driver: (
            abrir_grupo(driver),
            enviar_texto(
                driver,
                "Recordatorio Automático: Hora de limpiar y ordenar el taller, por favor todos los presentes."
            )
        )
    )


def enviar_mensaje_5():
    """Mantenimiento de grupos generadores: grupo con mención y mensaje directo."""

    def accion(driver):
        abrir_grupo(driver)

        enviar_mencion(
            driver,
            "Recordatorio Automático: Realizar mantenimiento preventivo a los *Grupos Generadores*, asignado a ",
            "Angel"
        )

        time.sleep(1)

        enviar_directo(
            driver,
            "595994246602",
            "Recordatorio Automático: Realizar mantenimiento preventivo a los *Grupos Generadores*, asignado a Angel Lezcano."
        )

    ejecutar_automatizacion(accion)


def enviar_mensaje_6():
    """Registro de horómetros: grupo con mención y mensaje directo."""

    def accion(driver):
        abrir_grupo(driver)

        enviar_mencion(
            driver,
            "Recordatorio Automático: Realizar registro de los *horómetros de equipos de Maquinado*, asignado a ",
            "Ronald"
        )

        time.sleep(1)

        enviar_directo(
            driver,
            "595982090279",
            "Recordatorio Automático: Realizar registro de los *horómetros de equipos de Maquinado*, asignado a Ronald Caceres."
        )

    ejecutar_automatizacion(accion)


MENSAJES = {
    "1": enviar_mensaje_1,
    "2": enviar_mensaje_2,
    "3": enviar_mensaje_3,
    "4": enviar_mensaje_4,
    "5": enviar_mensaje_5,
    "6": enviar_mensaje_6,
}


def main():
    if len(sys.argv) != 2 or sys.argv[1] not in MENSAJES:
        print("Uso: python mensajes.py <1|2|3|4|5|6>")
        sys.exit(1)

    MENSAJES[sys.argv[1]]()


if __name__ == "__main__":
    main()
