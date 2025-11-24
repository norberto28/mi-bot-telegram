import logging
import os
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, CommandHandler, filters
import google.generativeai as genai
from flask import Flask
from threading import Thread
import PIL.Image

# --- CONFIGURACIÓN DE TU IMPERIO ---
# 1. Pega aquí TU ID (1393624932)
ADMIN_ID = 1393624932  # <--- ¡CAMBIA ESTO POR TU NÚMERO!

# 2. Aquí pondremos los grupos más tarde. Déjalo vacío por ahora.
GRUPOS_DESTINO = [] 
# Ejemplo futuro: GRUPOS_DESTINO = [-4947151665]

# --- KEEP ALIVE (Para Render) ---
app = Flask('')
@app.route('/')
def home(): return "J.A.R.V.I.S. Sistema de Difusión Online"
def run(): app.run(host='0.0.0.0', port=8080)
def keep_alive(): t = Thread(target=run); t.start()

# --- CONFIGURACIÓN API ---
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
GOOGLE_API_KEY = os.environ.get('GOOGLE_API_KEY')
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

try:
    if GOOGLE_API_KEY:
        genai.configure(api_key=GOOGLE_API_KEY)
        model = genai.GenerativeModel('gemini-2.0-flash')
except: pass

chats_activos = {}

# --- FUNCIÓN 1: DESCUBRIR ID DEL GRUPO 🕵️‍♂️ ---
async def obtener_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    titulo = update.effective_chat.title or "Chat Privado"
    
    msg = f"🆔 **ID de {titulo}:**\n`{chat_id}`\n\n(Copia este número para ponerlo en tu código)"
    await context.bot.send_message(chat_id=chat_id, text=msg, parse_mode='Markdown')

# --- FUNCIÓN 2: ENVIAR ANUNCIO 📢 ---
async def enviar_anuncio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    usuario_id = update.effective_user.id
    
    # Seguridad: Solo TÚ puedes usar este comando
    if usuario_id != ADMIN_ID:
        await context.bot.send_message(update.effective_chat.id, "⛔ Acceso denegado. Protocolo solo para el Administrador.")
        return

    # Obtenemos el texto que escribiste después de /anuncio
    mensaje_a_enviar = " ".join(context.args)
    
    if not mensaje_a_enviar:
        await context.bot.send_message(update.effective_chat.id, "⚠️ Error: Escribe el mensaje. Ej: `/anuncio Hola a todos`")
        return

    # Enviamos a la lista
    enviados = 0
    errores = 0
    
    if not GRUPOS_DESTINO:
        await context.bot.send_message(update.effective_chat.id, "⚠️ La lista de grupos está vacía. Usa /id en los grupos para obtener sus números primero.")
        return

    for grupo_id in GRUPOS_DESTINO:
        try:
            await context.bot.send_message(chat_id=grupo_id, text=mensaje_a_enviar)
            enviados += 1
        except Exception as e:
            errores += 1
            print(f"Error enviando a {grupo_id}: {e}")

    await context.bot.send_message(update.effective_chat.id, f"✅ Informe: Enviado a {enviados} grupos. ({errores} fallos).")

# --- IA Y RESTO DEL BOT ---
async def chat_con_ia(update: Update, context: ContextTypes.DEFAULT_TYPE):
    usuario_id = update.effective_chat.id
    mensaje = update.message.text
    # ... (Lógica resumida de Jarvis para no alargar el código) ...
    try:
        if usuario_id not in chats_activos:
             chats_activos[usuario_id] = model.start_chat(history=[])
        chat = chats_activos[usuario_id]
        resp = chat.send_message(mensaje)
        await context.bot.send_message(chat_id=usuario_id, text=resp.text)
    except: pass

async def recibir_imagen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # ... (Tu lógica de imagen existente) ...
    pass

if __name__ == '__main__':
    keep_alive()
    if TELEGRAM_TOKEN:
        app_bot = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
        
        # COMANDOS NUEVOS
        app_bot.add_handler(CommandHandler("id", obtener_id))
        app_bot.add_handler(CommandHandler("anuncio", enviar_anuncio))
        
        # Comandos viejos (IA)
        app_bot.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), chat_con_ia))
        app_bot.add_handler(MessageHandler(filters.PHOTO, recibir_imagen))
        
        app_bot.run_polling()

