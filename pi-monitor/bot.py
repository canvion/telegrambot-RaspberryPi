import requests
import time
import os
import socket
import config
from datetime import datetime

ultimo_update_id = None
ultima_alerta_cpu = 0
ultima_alerta_ram = 0
ultima_alerta_temp = 0
ultima_alerta_disco = 0
ultima_alerta_conexion = 0
conexion_perdida = False
dispositivos_conocidos = set()
informe_enviado_hoy = False
ultimo_dia_informe = -1

# ─── MÉTRICAS ───────────────────────────────────────────

def get_cpu():
    f = open("/proc/stat", "r")
    line = f.readline()
    f.close()
    valores = line.split()
    total = sum(int(x) for x in valores[1:])
    idle = int(valores[4])
    return total, idle

def calcular_cpu_porcentaje():
    total1, idle1 = get_cpu()
    time.sleep(1)
    total2, idle2 = get_cpu()
    diferencia_total = total2 - total1
    diferencia_idle = idle2 - idle1
    cpu = 100 * (diferencia_total - diferencia_idle) / diferencia_total
    return round(cpu, 1)

def get_ram():
    f = open("/proc/meminfo", "r")
    lineas = f.readlines()
    f.close()
    total = int(lineas[0].split()[1])
    disponible = int(lineas[2].split()[1])
    usada = total - disponible
    porcentaje = round(100 * usada / total, 1)
    return porcentaje

def get_temperatura():
    f = open("/sys/class/thermal/thermal_zone0/temp", "r")
    temp = f.read()
    f.close()
    return round(int(temp) / 1000, 1)

def get_disco():
    info = os.statvfs("/")
    total_gb = round((info.f_blocks * info.f_frsize) / 1073741824, 1)
    libre_gb = round((info.f_bfree * info.f_frsize) / 1073741824, 1)
    usado_gb = round(total_gb - libre_gb, 1)
    porcentaje = round(100 * usado_gb / total_gb, 1)
    return usado_gb, libre_gb, total_gb, porcentaje

def get_uptime():
    f = open("/proc/uptime", "r")
    segundos = float(f.read().split()[0])
    f.close()
    dias = int(segundos // 86400)
    horas = int((segundos % 86400) // 3600)
    minutos = int((segundos % 3600) // 60)
    return str(dias) + "d " + str(horas) + "h " + str(minutos) + "m"

def get_ip_local():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8", 80))
    ip = s.getsockname()[0]
    s.close()
    return ip

def get_procesos():
    resultado = os.popen("ps aux --sort=-%cpu | head -6").read()
    lineas = resultado.strip().split("\n")
    texto = ""
    for linea in lineas[1:]:
        partes = linea.split()
        cpu = partes[2]
        mem = partes[3]
        nombre = partes[10]
        texto = texto + nombre + " CPU:" + cpu + "% RAM:" + mem + "%\n"
    return texto

def get_pihole():
    auth = requests.post("http://localhost/api/auth", json={"password": config.PIHOLE_PASSWORD})
    sid = auth.json()["session"]["sid"]
    headers = {"sid": sid}
    respuesta = requests.get("http://localhost/api/stats/summary", headers=headers)
    datos = respuesta.json()
    bloqueados = datos["queries"]["blocked"]
    total = datos["queries"]["total"]
    porcentaje = round(100 * bloqueados / total, 1)
    return str(bloqueados) + " bloqueados de " + str(total) + " (" + str(porcentaje) + "%)"

def get_docker():
    resultado = os.popen("docker ps --format '{{.Names}}|{{.Status}}|{{.Image}}'").read()
    if resultado.strip() == "":
        return "No hay contenedores corriendo"
    texto = ""
    for linea in resultado.strip().split("\n"):
        partes = linea.split("|")
        nombre = partes[0]
        estado = partes[1]
        imagen = partes[2]
        if "Up" in estado:
            emoji = "🟢"
        else:
            emoji = "🔴"
        texto = texto + emoji + " " + nombre + "\n"
        texto = texto + "   📦 " + imagen + "\n"
        texto = texto + "   ⏱️ " + estado + "\n\n"
    return texto.strip()

def hay_conexion():
    try:
        requests.get("https://8.8.8.8", timeout=3)
        return True
    except:
        return False

# ─── TIEMPO ─────────────────────────────────────────────

def codigo_a_emoji(codigo):
    if codigo == 0:
        return "☀️ Despejado"
    elif codigo <= 3:
        return "⛅ Nublado"
    elif codigo <= 48:
        return "🌫️ Niebla"
    elif codigo <= 55:
        return "🌦️ Llovizna"
    elif codigo <= 65:
        return "🌧️ Lluvia"
    elif codigo <= 75:
        return "❄️ Nieve"
    elif codigo <= 82:
        return "🌧️ Chubascos"
    elif codigo <= 99:
        return "⛈️ Tormenta"
    return "❓"

def get_tiempo():
    url = (
        "https://api.open-meteo.com/v1/forecast"
        "?latitude=39.5696&longitude=2.6502"
        "&hourly=temperature_2m,precipitation_probability,windspeed_10m,weathercode"
        "&timezone=Europe%2FMadrid&forecast_days=2"
    )
    respuesta = requests.get(url)
    datos = respuesta.json()
    horas = datos["hourly"]["time"]
    temperaturas = datos["hourly"]["temperature_2m"]
    precipitacion = datos["hourly"]["precipitation_probability"]
    viento = datos["hourly"]["windspeed_10m"]
    codigos = datos["hourly"]["weathercode"]

    manana = (datetime.now().date().__str__()[:-2])
    dia_manana = str(datetime.now().day + 1).zfill(2)
    manana = datetime.now().strftime("%Y-%m-") + dia_manana

    dias_semana = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
    meses = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
    dia_nombre = dias_semana[(datetime.now().weekday() + 1) % 7]
    dia_num = datetime.now().day + 1
    mes_nombre = meses[datetime.now().month - 1]
    texto = "🌤️ Tiempo mañana, " + dia_nombre + " " + str(dia_num) + " de " + mes_nombre + " en Palma (10h-18h):\n\n"
    for i in range(len(horas)):
        if horas[i].startswith(manana):
            hora = horas[i][11:16]
            h = int(hora[:2])
            if 10 <= h <= 18:
                estado = codigo_a_emoji(codigos[i])
                texto = texto + hora + "h " + estado + "\n"
                texto = texto + "🌡️ " + str(temperaturas[i]) + "°C  "
                texto = texto + "💧 " + str(precipitacion[i]) + "%  "
                texto = texto + "💨 " + str(viento[i]) + " km/h\n\n"
    return texto

# ─── RED ────────────────────────────────────────────────

def get_dispositivos():
    resultado = os.popen("arp -a").read()
    dispositivos = set()
    for linea in resultado.strip().split("\n"):
        partes = linea.split()
        if len(partes) >= 4 and partes[3] != "<incomplete>":
            ip = partes[1].replace("(", "").replace(")", "")
            mac = partes[3]
            dispositivos.add(ip + " " + mac)
    return dispositivos

def cargar_dispositivos():
    if os.path.exists("dispositivos.json"):
        f = open("dispositivos.json", "r")
        import json
        datos = json.load(f)
        f.close()
        return set(datos)
    return set()

def guardar_dispositivos(dispositivos):
    import json
    f = open("dispositivos.json", "w")
    json.dump(list(dispositivos), f)
    f.close()

# ─── TELEGRAM ───────────────────────────────────────────

def mandar_mensaje(texto):
    url = "https://api.telegram.org/bot" + config.TOKEN + "/sendMessage"
    datos = {"chat_id": config.CHAT_ID, "text": texto}
    requests.post(url, data=datos)

def inicializar_updates():
    global ultimo_update_id
    url = "https://api.telegram.org/bot" + config.TOKEN + "/getUpdates"
    respuesta = requests.get(url)
    datos = respuesta.json()
    if len(datos["result"]) > 0:
        ultimo_update_id = datos["result"][-1]["update_id"]

def get_mensajes():
    global ultimo_update_id
    url = "https://api.telegram.org/bot" + config.TOKEN + "/getUpdates"
    if ultimo_update_id is not None:
        url = url + "?offset=" + str(ultimo_update_id + 1)
    respuesta = requests.get(url)
    datos = respuesta.json()
    return datos["result"]

def procesar_comandos():
    global ultimo_update_id
    mensajes = get_mensajes()
    for mensaje in mensajes:
        ultimo_update_id = mensaje["update_id"]
        if "message" not in mensaje:
            continue
        texto = mensaje["message"].get("text", "")
        print("Comando recibido: " + texto)

        if texto == "/estado":
            cpu = calcular_cpu_porcentaje()
            ram = get_ram()
            temp = get_temperatura()
            usado_gb, libre_gb, total_gb, porcentaje_disco = get_disco()
            uptime = get_uptime()
            mandar_mensaje(
                "🍓 Estado del Pi:\n"
                "CPU: " + str(cpu) + "%\n"
                "RAM: " + str(ram) + "%\n"
                "Temp: " + str(temp) + "°C\n"
                "Disco: " + str(usado_gb) + "GB / " + str(total_gb) + "GB (" + str(porcentaje_disco) + "%)\n"
                "Libre: " + str(libre_gb) + "GB\n"
                "Uptime: " + uptime
            )

        elif texto == "/disco":
            usado_gb, libre_gb, total_gb, porcentaje_disco = get_disco()
            mandar_mensaje(
                "💾 Disco:\n"
                "Usado: " + str(usado_gb) + " GB\n"
                "Libre: " + str(libre_gb) + " GB\n"
                "Total: " + str(total_gb) + " GB\n"
                "Ocupación: " + str(porcentaje_disco) + "%"
            )

        elif texto == "/ip":
            ip = get_ip_local()
            mandar_mensaje("🌐 IP local: " + ip + "\n🔒 Tailscale: 100.125.239.75")

        elif texto == "/procesos":
            mandar_mensaje("⚙️ Top procesos:\n" + get_procesos())

        elif texto == "/pihole":
            mandar_mensaje("🛡️ Pi-hole hoy: " + get_pihole())

        elif texto == "/docker":
            mandar_mensaje("🐳 Contenedores Docker:\n" + get_docker())

        elif texto == "/tiempo":
            mandar_mensaje(get_tiempo())

        elif texto == "/reiniciar":
            mandar_mensaje("🔄 Reiniciando el Pi...")
            os.system("sudo reboot")

        elif texto == "/ayuda":
            mandar_mensaje(
                "🍓 Comandos disponibles:\n\n"
                "/estado → resumen completo\n"
                "/disco → espacio en GB\n"
                "/ip → IP local y Tailscale\n"
                "/procesos → top 5 por CPU\n"
                "/pihole → estadísticas Pi-hole\n"
                "/docker → contenedores activos\n"
                "/tiempo → previsión mañana 10h-18h\n"
                "/reiniciar → reinicia el Pi\n"
                "/ayuda → este mensaje"
            )

# ─── INICIO ─────────────────────────────────────────────

inicializar_updates()
dispositivos_conocidos = cargar_dispositivos()
if len(dispositivos_conocidos) == 0:
    dispositivos_conocidos = get_dispositivos()
    guardar_dispositivos(dispositivos_conocidos)
mandar_mensaje("🍓 Bot iniciado y escuchando...")

contador = 0

while True:
    procesar_comandos()
    ahora = time.time()
    hora_actual = datetime.now().hour
    dia_actual = datetime.now().day

    # Informe diario a las 8h
    if hora_actual == 8 and dia_actual != ultimo_dia_informe:
        ultimo_dia_informe = dia_actual
        cpu = calcular_cpu_porcentaje()
        ram = get_ram()
        temp = get_temperatura()
        usado_gb, libre_gb, total_gb, porcentaje_disco = get_disco()
        uptime = get_uptime()
        mandar_mensaje(
            "📊 Informe diario:\n"
            "CPU: " + str(cpu) + "%\n"
            "RAM: " + str(ram) + "%\n"
            "Temp: " + str(temp) + "°C\n"
            "Disco: " + str(usado_gb) + "GB / " + str(total_gb) + "GB\n"
            "Uptime: " + uptime
        )

    contador = contador + 1
    if contador >= 6:
        contador = 0

        # Conexión
        if not hay_conexion():
            if not conexion_perdida:
                conexion_perdida = True
                mandar_mensaje("🔴 El Pi ha perdido la conexión a internet")
        else:
            if conexion_perdida:
                conexion_perdida = False
                mandar_mensaje("🟢 El Pi ha recuperado la conexión a internet")

        cpu = calcular_cpu_porcentaje()
        ram = get_ram()
        temp = get_temperatura()
        usado_gb, libre_gb, total_gb, porcentaje_disco = get_disco()

        # Anti-spam: solo alerta si han pasado 10 minutos desde la última
        if cpu > 80 and (ahora - ultima_alerta_cpu) > 600:
            ultima_alerta_cpu = ahora
            mandar_mensaje("⚠️ CPU alta: " + str(cpu) + "%")

        if ram > 80 and (ahora - ultima_alerta_ram) > 600:
            ultima_alerta_ram = ahora
            mandar_mensaje("⚠️ RAM alta: " + str(ram) + "%")

        if temp > 70 and (ahora - ultima_alerta_temp) > 600:
            ultima_alerta_temp = ahora
            mandar_mensaje("🌡️ Temperatura alta: " + str(temp) + "°C")

        if porcentaje_disco > 80 and (ahora - ultima_alerta_disco) > 600:
            ultima_alerta_disco = ahora
            mandar_mensaje("💾 Disco casi lleno: " + str(porcentaje_disco) + "%")

        # Monitor de red
# Monitor de red
        dispositivos_actuales = get_dispositivos()
        nuevos = dispositivos_actuales - dispositivos_conocidos
        for dispositivo in nuevos:
            mandar_mensaje("📡 Nuevo dispositivo en la red: " + dispositivo)
            dispositivos_conocidos.add(dispositivo)
        if len(nuevos) > 0:
            guardar_dispositivos(dispositivos_conocidos)

    time.sleep(10)
