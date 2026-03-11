import requests
import time
import os
import config

ultimo_update_id = None

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
    total = info.f_blocks * info.f_frsize
    libre = info.f_bfree * info.f_frsize
    usado = total - libre
    porcentaje = round(100 * usado / total, 1)
    return porcentaje

def get_uptime():
    f = open("/proc/uptime", "r")
    segundos = float(f.read().split()[0])
    f.close()
    dias = int(segundos // 86400)
    horas = int((segundos % 86400) // 3600)
    minutos = int((segundos % 3600) // 60)
    return str(dias) + "d " + str(horas) + "h " + str(minutos) + "m"

def get_ip_local():
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8", 80))
    ip = s.getsockname()[0]
    s.close()
    return ip

def get_procesos():
    f = open("/proc/stat", "r")
    f.close()
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
    return str(bloqueados) + " bloqueados de " + str(total) + " consultas (" + str(porcentaje) + "%)"

def mandar_mensaje(texto):
    url = "https://api.telegram.org/bot" + config.TOKEN + "/sendMessage"
    datos = {
        "chat_id": config.CHAT_ID,
        "text": texto
    }
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
            disco = get_disco()
            uptime = get_uptime()
            respuesta = (
                "🍓 Estado del Pi:\n"
                "CPU: " + str(cpu) + "%\n"
                "RAM: " + str(ram) + "%\n"
                "Temp: " + str(temp) + "°C\n"
                "Disco: " + str(disco) + "%\n"
                "Uptime: " + uptime + "\n"
            )
            mandar_mensaje(respuesta)
        elif texto == "/reiniciar":
            mandar_mensaje("🔄 Reiniciando el Pi...")
            os.system("sudo reboot")

        elif texto == "/ip":
            ip = get_ip_local()
            mandar_mensaje("🌐 IP local: " + ip + "\n🔒 Tailscale: 100.125.239.75")

        elif texto == "/procesos":
            procesos = get_procesos()
            mandar_mensaje("⚙️ Top procesos:\n" + procesos)

        elif texto == "/pihole":
            stats = get_pihole()
            mandar_mensaje("🛡️ Pi-hole hoy: " + stats)

        elif texto == "/ayuda":
            mandar_mensaje(
                "🍓 Comandos disponibles:\n\n"
                "/estado → CPU, RAM, temperatura, disco y uptime\n"
                "/ip → IP local y Tailscale\n"
                "/procesos → top 5 procesos por CPU\n"
                "/pihole → estadísticas de Pi-hole\n"
                "/reiniciar → reinicia el Pi\n"
                "/ayuda → muestra este mensaje"
            )

contador = 0

while True:
    procesar_comandos()

    contador = contador + 1
    if contador >= 6:
        contador = 0
        cpu = calcular_cpu_porcentaje()
        ram = get_ram()
        temp = get_temperatura()
        disco = get_disco()

        if cpu > 80:
            mandar_mensaje("⚠️ CPU alta: " + str(cpu) + "%")
        if ram > 80:
            mandar_mensaje("⚠️ RAM alta: " + str(ram) + "%")
        if temp > 70:
            mandar_mensaje("🌡️ Temperatura alta: " + str(temp) + "°C")
        if disco > 80:
            mandar_mensaje("💾 Disco casi lleno: " + str(disco) + "%")

    time.sleep(10)
