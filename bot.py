import logging
import os
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters
import google.generativeai as genai
from flask import Flask
from threading import Thread

# --- 1. MANTENER VIVO EL BOT (Keep Alive) ---
app = Flask('')

@app.route('/')
def home():
    return "¡Hola! Soy el Bot con Memoria y estoy vivo."

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

# --- 2. CONFIGURACIÓN ---
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

# --- 3. DICCIONARIO PARA GUARDAR MEMORIA DE CADA USUARIO ---
# Aquí guardaremos el historial de cada persona por separado
chats_activos = {}

async def chat_con_ia(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not GOOGLE_API_KEY:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Me falta mi cerebro (API Key).")
        return

    # Avisamos que el bot está "escribiendo..."
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action='typing')
    
    # Datos del usuario
    usuario_id = update.effective_chat.id
    mensaje_usuario = update.message.text
    nombre_usuario = update.effective_user.first_name

    try:
        # Verificamos si ya conocemos a este usuario
        if usuario_id not in chats_activos:
            # Si es nuevo, iniciamos una nueva sesión de chat con historial vacío
            # Verificamos si ya conocemos a este usuario
        if usuario_id not in chats_activos:
            # INICIO DEL PROTOCOLO JARVIS 🤖
            # Le damos la instrucción precisa de cómo comportarse
            prompt_inicial = (
                f"Eres J.A.R.V.I.S., una inteligencia artificial avanzada. "
                f"Tu usuario actual es {nombre_usuario}, pero debes dirigirte a él siempre como 'Señor' (o 'Señora' si te lo pide). "
                "Tu tono es extremadamente educado, formal, breve, eficiente y con un toque sutil de humor británico. "
                "No uses emojis excesivamente, prefiere un lenguaje técnico y elegante. "
                "Estás aquí para asistir en programación, gestión de datos y cualquier tarea que requiera el Señor."
            )
            
            chats_activos[usuario_id] = model.start_chat(history=[
                {"role": "user", "parts": prompt_inicial},
                {"role": "model", "parts": f"A sus órdenes, Señor. Sistemas en línea y listos para asistirle. ¿Cuál es la primera tarea?"}
            ])
        # Recuperamos la sesión de este usuario específico
        chat_sesion = chats_activos[usuario_id]
        
        # Enviamos el mensaje al chat con memoria
        response = chat_sesion.send_message(mensaje_usuario)
        
        # Respondemos en Telegram
        await context.bot.send_message(chat_id=usuario_id, text=response.text)

    except Exception as e:
        # Si la memoria falla o hay error, reseteamos el chat
        chats_activos[usuario_id] = model.start_chat(history=[])
        await context.bot.send_message(chat_id=usuario_id, text="Ups, tuve un error. He reiniciado nuestra conversación.")
        print(e)

if __name__ == '__main__':
    keep_alive() # Encender servidor web
    
    if TELEGRAM_TOKEN:
        application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
        
        # El bot responderá a cualquier texto (excepto comandos)
        handler_ia = MessageHandler(filters.TEXT & (~filters.COMMAND), chat_con_ia)
        application.add_handler(handler_ia)
        
        # Comando para limpiar memoria manualmente
        async def borrar_memoria(update: Update, context: ContextTypes.DEFAULT_TYPE):
            chats_activos[update.effective_chat.id] = model.start_chat(history=[])
            await context.bot.send_message(chat_id=update.effective_chat.id, text="🧹 ¡Memoria borrada! Empecemos de nuevo.")

        application.add_handler(handler_ia)
        print("Bot con Memoria iniciado...")
        application.run_polling()
    else:
        print("¡ERROR! No encontré el Token de Telegram.")

