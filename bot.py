import logging
import os
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters
import google.generativeai as genai
from flask import Flask
from threading import Thread
import PIL.Image # <--- IMPORTANTE: Esto usa la librería Pillow que acabamos de agregar

# --- 1. MANTENER VIVO EL BOT ---
app = Flask('')

@app.route('/')
def home():
    return "J.A.R.V.I.S. Online"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

# --- 2. CONFIGURACIÓN ---
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
GOOGLE_API_KEY = os.environ.get('GOOGLE_API_KEY')

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

try:
    if GOOGLE_API_KEY:
        genai.configure(api_key=GOOGLE_API_KEY)
        model = genai.GenerativeModel('gemini-2.0-flash')
    else:
        print("¡ADVERTENCIA! Falta la API Key.")
except Exception as e:
    print(f"Error Gemini: {e}")

chats_activos = {}

# --- 3. CEREBRO DE JARVIS (TEXTO) ---
async def chat_con_ia(update: Update, context: ContextTypes.DEFAULT_TYPE):
    usuario_id = update.effective_chat.id
    mensaje_usuario = update.message.text
    nombre_usuario = update.effective_user.first_name
    
    await context.bot.send_chat_action(chat_id=usuario_id, action='typing')

    try:
        if usuario_id not in chats_activos:
            prompt_inicial = (
                f"Eres J.A.R.V.I.S., una IA avanzada. Tu usuario es {nombre_usuario} (Señor/a). "
                "Tu tono es servicial, técnico, elegante y con humor británico sutil. "
                "Eres un experto en tecnología y análisis."
            )
            chats_activos[usuario_id] = model.start_chat(history=[
                {"role": "user", "parts": prompt_inicial},
                {"role": "model", "parts": "A sus órdenes, Señor. Sistemas listos."}
            ])
        
        chat_sesion = chats_activos[usuario_id]
        response = chat_sesion.send_message(mensaje_usuario)
        await context.bot.send_message(chat_id=usuario_id, text=response.text)

    except Exception as e:
        chats_activos[usuario_id] = model.start_chat(history=[])
        await context.bot.send_message(chat_id=usuario_id, text="Reiniciando sistemas de memoria, señor.")

# --- 4. OJOS DE JARVIS (IMÁGENES) ---
async def recibir_imagen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    usuario_id = update.effective_chat.id
    await context.bot.send_chat_action(chat_id=usuario_id, action='typing')
    
    try:
        # Descargar foto
        foto_archivo = await update.message.photo[-1].get_file()
        await foto_archivo.download_to_drive("imagen_temp.jpg")
        
        # Texto que acompaña la foto (si hay)
        texto_usuario = update.message.caption if update.message.caption else "Analice esta imagen visual y descríbala detalladamente."

        # Cargar imagen con Pillow
        img = PIL.Image.open("imagen_temp.jpg")
        
        if usuario_id not in chats_activos:
             chats_activos[usuario_id] = model.start_chat(history=[])
        
        # Enviar a Gemini (Imagen + Texto)
        chat_sesion = chats_activos[usuario_id]
        response = chat_sesion.send_message([texto_usuario, img])
        
        await context.bot.send_message(chat_id=usuario_id, text=response.text)
        
    except Exception as e:
        await context.bot.send_message(chat_id=usuario_id, text="Error en los sensores visuales.")
        print(f"Error imagen: {e}")

if __name__ == '__main__':
    keep_alive()
    if TELEGRAM_TOKEN:
        app_bot = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
        
        # Handler de Texto
        app_bot.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), chat_con_ia))
        
        # Handler de Fotos (Ahora acepta fotos solas O fotos con texto)
        app_bot.add_handler(MessageHandler(filters.PHOTO, recibir_imagen))
        
        print("JARVIS ONLINE...")
        app_bot.run_polling()
