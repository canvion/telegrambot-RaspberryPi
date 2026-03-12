import requests
import time
import json
import os
import re
import config
from datetime import datetime, timedelta

ultimo_update_id = None

# ─── RECORDATORIOS ──────────────────────────────────────

def cargar_recordatorios():
    if os.path.exists("recordatorios.json"):
        f = open("recordatorios.json", "r")
        datos = json.load(f)
        f.close()
        return datos
    return []

def guardar_recordatorios(recordatorios):
    f = open("recordatorios.json", "w")
    json.dump(recordatorios, f)
    f.close()

def añadir_recordatorio(hora, texto):
    recordatorios = cargar_recordatorios()
    recordatorios.append({"hora": hora, "texto": texto})
    guardar_recordatorios(recordatorios)

def parsear_mensaje(mensaje):
    # Formato: "a las 18h" o "a las 18:06"
    patron_hora = re.search(r"a las (\d+)(?::(\d+))?h?", mensaje)
    if patron_hora:
        hora = patron_hora.group(1).zfill(2)
        minutos = patron_hora.group(2) if patron_hora.group(2) else "00"
        hora_completa = hora + ":" + minutos
        texto = re.sub(r"a las \d+(?::\d+)?h?", "", mensaje).strip()
        texto = re.sub(r"recuérdame|recuerda|que|me", "", texto).strip()
        return hora_completa, texto

    # Formato: "en 30 minutos"
    patron_minutos = re.search(r"en (\d+) minutos", mensaje)
    if patron_minutos:
        minutos = int(patron_minutos.group(1))
        hora_dt = datetime.now() + timedelta(minutes=minutos)
        hora_completa = hora_dt.strftime("%H:%M")
        texto = re.sub(r"en \d+ minutos", "", mensaje).strip()
        texto = re.sub(r"recuérdame|recuerda|que|me", "", texto).strip()
        return hora_completa, texto

    return None, None

def comprobar_recordatorios():
    recordatorios = cargar_recordatorios()
    ahora = datetime.now()
    pendientes = []
    disparados = []

    for r in recordatorios:
        partes = r["hora"].split(":")
        hora_r = ahora.replace(hour=int(partes[0]), minute=int(partes[1]), second=0)
        diferencia = (ahora - hora_r).total_seconds()
        if 0 <= diferencia <= 90:
            disparados.append(r)
        else:
            pendientes.append(r)

    if len(disparados) > 0:
        guardar_recordatorios(pendientes)

    return disparados

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
        print("Mensaje recibido: " + texto)

        if texto == "/recordatorios":
            recordatorios = cargar_recordatorios()
            if len(recordatorios) == 0:
                mandar_mensaje("📭 No tienes recordatorios pendientes")
            else:
                respuesta = "📋 Recordatorios pendientes:\n\n"
                for i, r in enumerate(recordatorios):
                    respuesta = respuesta + str(i + 1) + ". " + r["hora"] + "h → " + r["texto"] + "\n"
                mandar_mensaje(respuesta)

        elif texto.startswith("/borrar"):
            partes = texto.split()
            if len(partes) == 2:
                numero = int(partes[1]) - 1
                recordatorios = cargar_recordatorios()
                if 0 <= numero < len(recordatorios):
                    borrado = recordatorios.pop(numero)
                    guardar_recordatorios(recordatorios)
                    mandar_mensaje("🗑️ Borrado: " + borrado["texto"])
                else:
                    mandar_mensaje("❌ Número inválido")

        elif texto == "/ayuda":
            mandar_mensaje(
                "⏰ Bot de Recordatorios:\n\n"
                "Para añadir un recordatorio escribe:\n"
                "→ a las 18h recuérdame sacar la lavadora\n"
                "→ en 30 minutos recuérdame llamar al médico\n\n"
                "/recordatorios → ver todos los pendientes\n"
                "/borrar 1 → borrar el recordatorio número 1\n"
                "/ayuda → este mensaje"
            )

        else:
            hora, texto_recordatorio = parsear_mensaje(texto)
            if hora and texto_recordatorio:
                añadir_recordatorio(hora, texto_recordatorio)
                mandar_mensaje("✅ Recordatorio guardado para las " + hora + "h:\n" + texto_recordatorio)
            else:
                mandar_mensaje("❓ No te entendí. Escribe /ayuda para ver cómo usarme")

# ─── INICIO ─────────────────────────────────────────────

inicializar_updates()
mandar_mensaje("⏰ Bot de recordatorios iniciado...")

while True:
    procesar_comandos()

    disparados = comprobar_recordatorios()
    for r in disparados:
        mandar_mensaje("⏰ Recuerda: " + r["texto"])

    time.sleep(30)
