import logging
import os
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, CommandHandler, filters
import google.generativeai as genai
from flask import Flask
from threading import Thread
import PIL.Image

# ==========================================
# CONFIGURACIÓN DE TU IMPERIO 👑
# ==========================================

# 1. Pega aquí TU ID PERSONAL (el que te dio @userinfobot)
# Si no lo pones, nadie podrá mandar anuncios.
ADMIN_ID = 1393624932 

# 2. Lista de grupos donde se enviarán los anuncios.
# Ejemplo: GRUPOS_DESTINO = [-10012345678, -10098765432]
# Déjalo vacío [] hasta que uses el comando /id en tus grupos para saber sus números.
GRUPOS_DESTINO = [-4947151665] 

# ==========================================
# 1. MANTENER VIVO EL BOT (Keep Alive) 💓
# ==========================================
app = Flask('')

@app.route('/')
def home():
    return "J.A.R.V.I.S. Sistema de Difusión Online"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

# ==========================================
# 2. CONFIGURACIÓN DE CREDENCIALES 🔑
# ==========================================
TELEGRAM_TOKEN = os.environ.get('8356125312:AAEqgCxe53DBnopnjtQXoiAC4IjUxUikrCA')
GOOGLE_API_KEY = os.environ.get('AIzaSyDKaMXJJwRn7hnj2DGlBGHp9rqKSYjTxKI')

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
        print("¡ADVERTENCIA! Falta la API Key.")
except Exception as e:
    print(f"Error Gemini: {e}")

# Memoria del bot
chats_activos = {}

# ==========================================
# 3. FUNCIONES DE ADMINISTRADOR (NUEVO) 📢
# ==========================================

# Comando /id -> Te dice el ID del chat actual
async def obtener_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    titulo = update.effective_chat.title or "Chat Privado"
    
    msg = f"🆔 **ID de {titulo}:**\n`{chat_id}`\n\n(Copia este número y agrégalo a GRUPOS_DESTINO en tu código)"
    await context.bot.send_message(chat_id=chat_id, text=msg, parse_mode='Markdown')

# Comando /anuncio -> Envía mensaje a todos los grupos
async def enviar_anuncio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    usuario_id = update.effective_user.id
    
    # Seguridad: Solo TÚ puedes usar este comando
    if usuario_id != ADMIN_ID:
        await context.bot.send_message(update.effective_chat.id, "⛔ Acceso denegado. Protocolo reservado para el Administrador.")
        return

    # Obtenemos el texto que escribiste después de /anuncio
    mensaje_a_enviar = " ".join(context.args)
    
    if not mensaje_a_enviar:
        await context.bot.send_message(update.effective_chat.id, "⚠️ Error de sintaxis. Uso correcto: `/anuncio Hola a todos`", parse_mode='Markdown')
        return

    # Enviamos a la lista
    enviados = 0
    errores = 0
    
    if not GRUPOS_DESTINO:
        await context.bot.send_message(update.effective_chat.id, "⚠️ La lista de grupos está vacía. Usa /id en los grupos primero y actualiza el código.")
        return

    await context.bot.send_message(update.effective_chat.id, "🚀 Iniciando protocolo de difusión...")

    for grupo_id in GRUPOS_DESTINO:
        try:
            await context.bot.send_message(chat_id=grupo_id, text=mensaje_a_enviar)
            enviados += 1
        except Exception as e:
            errores += 1
            print(f"Error enviando a {grupo_id}: {e}")

    await context.bot.send_message(update.effective_chat.id, f"✅ Informe Final: Enviado a {enviados} grupos. ({errores} fallos).")


# ==========================================
# 4. CEREBRO DE JARVIS (TEXTO Y MEMORIA) 🧠
# ==========================================
async def chat_con_ia(update: Update, context: ContextTypes.DEFAULT_TYPE):
    usuario_id = update.effective_chat.id
    mensaje_usuario = update.message.text
    nombre_usuario = update.effective_user.first_name
    
    await context.bot.send_chat_action(chat_id=usuario_id, action='typing')

    try:
        # Si no hay memoria, creamos la personalidad de Jarvis
        if usuario_id not in chats_activos:
            prompt_inicial = (
                f"Eres J.A.R.V.I.S., una IA avanzada. Tu usuario actual es {nombre_usuario} (Señor/a). "
                "Tu tono es servicial, técnico, elegante y con un toque de humor británico sutil. "
                "Eres experto en tecnología, análisis y asistencia personal."
            )
            chats_activos[usuario_id] = model.start_chat(history=[
                {"role": "user", "parts": prompt_inicial},
                {"role": "model", "parts": "A sus órdenes, Señor. Sistemas en línea y listos."}
            ])
        
        chat_sesion = chats_activos[usuario_id]
        response = chat_sesion.send_message(mensaje_usuario)
        await context.bot.send_message(chat_id=usuario_id, text=response.text)

    except Exception as e:
        chats_activos[usuario_id] = model.start_chat(history=[])
        await context.bot.send_message(chat_id=usuario_id, text="⚠️ Error en procesadores de memoria. Reiniciando sesión, señor.")
        print(e)

# ==========================================
# 5. OJOS DE JARVIS (VISIÓN) 👁️
# ==========================================
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
        
        # Asegurar que existe sesión de memoria
        if usuario_id not in chats_activos:
             chats_activos[usuario_id] = model.start_chat(history=[])
        
        # Enviar a Gemini (Imagen + Texto)
        chat_sesion = chats_activos[usuario_id]
        response = chat_sesion.send_message([texto_usuario, img])
        
        await context.bot.send_message(chat_id=usuario_id, text=response.text)
        
    except Exception as e:
        await context.bot.send_message(chat_id=usuario_id, text="⚠️ Fallo en los sensores visuales, señor.")
        print(f"Error imagen: {e}")

# ==========================================
# 6. ARRANQUE DEL SISTEMA 🚀
# ==========================================
if __name__ == '__main__':
    keep_alive() # Inicia el servidor web falso
    
    if TELEGRAM_TOKEN:
        app_bot = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
        
        # --- ZONA DE COMANDOS ---
        app_bot.add_handler(CommandHandler("id", obtener_id))
        app_bot.add_handler(CommandHandler("anuncio", enviar_anuncio))
        
        # --- ZONA DE INTERACCIÓN (TEXTO Y FOTOS) ---
        app_bot.add_handler(MessageHandler(filters.PHOTO, recibir_imagen))
        app_bot.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), chat_con_ia))
        
        print("SISTEMA J.A.R.V.I.S. EN LÍNEA...")
        app_bot.run_polling()
    else:
        print("¡ERROR CRÍTICO! No se detectó el Token de Telegram.")
