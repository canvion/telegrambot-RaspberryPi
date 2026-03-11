# 🍓 Telegram Bot - Raspberry Pi Monitor

Bot de Telegram para monitorizar el estado de una Raspberry Pi en tiempo real. Manda alertas automáticas cuando algo va mal y responde a comandos manuales.

## ¿Qué hace?

- Manda una alerta si la **CPU** supera el 80%
- Manda una alerta si la **RAM** supera el 80%
- Manda una alerta si la **temperatura** supera los 70°C
- Manda una alerta si el **disco** supera el 80%
- Responde al comando `/estado` con un resumen completo del Pi
- Responde al comando `/reiniciar` para reiniciar el Pi remotamente

## Comandos disponibles

| Comando | Descripción |
|---|---|
| `/estado` | Muestra CPU, RAM, temperatura, disco y uptime |
| `/reiniciar` | Reinicia el Pi |

## Instalación

**1. Clona el repositorio:**
```bash
git clone https://github.com/tu-usuario/telegram-bot.git
cd telegram-bot
```

**2. Crea tu archivo de configuración:**
```bash
cp config.example.py config.py
nano config.py
```

Rellena tu Token de Telegram y tu Chat ID:
```python
TOKEN = "tu-token-de-botfather"
CHAT_ID = "tu-chat-id"
```

**3. Ejecuta el bot:**
```bash
python3 bot.py
```

## Ejecutar como servicio (arranque automático)

Para que el bot arranque solo cada vez que el Pi se reinicie:

```bash
sudo nano /etc/systemd/system/telegrambot.service
```

```
[Unit]
Description=Telegram Bot Monitor
After=network.target

[Service]
User=tu-usuario
WorkingDirectory=/home/tu-usuario/telegram-bot
ExecStart=/usr/bin/python3 /home/tu-usuario/telegram-bot/bot.py
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable telegrambot
sudo systemctl start telegrambot
```

## ¿Cómo obtener el Token y el Chat ID?

1. Abre Telegram y busca `@BotFather`
2. Escríbele `/newbot` y sigue los pasos
3. Copia el Token que te da
4. Busca tu bot, escríbele cualquier mensaje y entra en:
   `https://api.telegram.org/botTU_TOKEN/getUpdates`
5. Copia el valor del campo `"id"` dentro de `"chat"`

## Requisitos

- Raspberry Pi con Raspberry Pi OS
- Python 3
- Librería `requests` (`pip3 install requests --break-system-packages`)
- Conexión a internet
