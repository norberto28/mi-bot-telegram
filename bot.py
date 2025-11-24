import logging
import os
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters
import google.generativeai as genai
from flask import Flask
from threading import Thread

# --- SECCIÓN 1: EL CORAZÓN WEB (Para que Render no nos apague) ---
app = Flask('')

@app.route('/')
def home():
    return "¡Hola! Soy el Bot y estoy vivo."

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

# --- SECCIÓN 2: TU BOT DE SIEMPRE ---
# OJO: Ahora tomaremos las claves de las "Variables de Entorno" (más seguro)
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
GOOGLE_API_KEY = os.environ.get('GOOGLE_API_KEY')

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Configuración de Gemini
try:
    if GOOGLE_API_KEY:
        genai.configure(api_key=GOOGLE_API_KEY)
        model = genai.GenerativeModel('gemini-2.0-flash')
    else:
        print("¡ADVERTENCIA! No encontré la clave de Google.")
except Exception as e:
    print(f"Error configurando Gemini: {e}")

async def chat_con_ia(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not GOOGLE_API_KEY:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Me falta mi cerebro (API Key).")
        return

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action='typing')
    mensaje_usuario = update.message.text
    
    try:
        response = model.generate_content(mensaje_usuario)
        await context.bot.send_message(chat_id=update.effective_chat.id, text=response.text)
    except Exception as e:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Error conectando con la IA.")
        print(e)

if __name__ == '__main__':
    # 1. Encendemos el servidor web falso
    keep_alive()
    
    # 2. Encendemos el bot
    if TELEGRAM_TOKEN:
        application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
        handler_ia = MessageHandler(filters.TEXT & (~filters.COMMAND), chat_con_ia)
        application.add_handler(handler_ia)
        print("El Bot está corriendo...")
        application.run_polling()
    else:
        print("¡ERROR! No encontré el Token de Telegram.")