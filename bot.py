import logging
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ChatPermissions
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, CommandHandler, CallbackQueryHandler, filters
import google.generativeai as genai
from flask import Flask
from threading import Thread
import PIL.Image
from gtts import gTTS
import wikipedia

# ==========================================
# CONFIGURACIÓN 👑
# ==========================================
ADMIN_ID = 1393624932  # <--- TU ID
GRUPOS_DESTINO = [-4947151665] # <--- TUS GRUPOS
PALABRAS_PROHIBIDAS = ["estafa", "bitcoin gratis", "tonto", "idiota"]

wikipedia.set_lang("es")

# ==========================================
# SERVER
# ==========================================
app = Flask('')
@app.route('/')
def home(): return "J.A.R.V.I.S. Interface Online"
def run(): app.run(host='0.0.0.0', port=8080)
def keep_alive(): t = Thread(target=run); t.start()

# ==========================================
# API
# ==========================================
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
GOOGLE_API_KEY = os.environ.get('GOOGLE_API_KEY')

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

try:
    if GOOGLE_API_KEY:
        genai.configure(api_key=GOOGLE_API_KEY)
        model = genai.GenerativeModel('gemini-2.0-flash')
except: pass

chats_activos = {}

# ==========================================
# 1. PANEL DE CONTROL (MENÚ) 🎛️
# ==========================================
async def mostrar_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [
            InlineKeyboardButton("🔄 Reiniciar IA", callback_data="menu_reset"),
            InlineKeyboardButton("🎲 Dado", callback_data="menu_dado")
        ],
        [
            InlineKeyboardButton("🆔 Mi ID", callback_data="menu_id"),
            InlineKeyboardButton("🆘 Ayuda", callback_data="menu_help")
        ],
        [
            InlineKeyboardButton("🗣️ Instrucciones de Voz", callback_data="menu_voz")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    msg = "🖥️ **PANEL DE CONTROL J.A.R.V.I.S.**\n\nSeleccione una función, Señor:"
    
    # Si viene de un comando /menu
    if update.message:
        await context.bot.send_message(update.effective_chat.id, msg, reply_markup=reply_markup, parse_mode='Markdown')
    # Si viene de un botón (para actualizar el menú existente)
    elif update.callback_query:
        await update.callback_query.message.reply_text(msg, reply_markup=reply_markup, parse_mode='Markdown')

# ==========================================
# 2. MANEJADOR DE BOTONES (ROUTER) 🚦
# ==========================================
async def manejar_botones(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer() # Avisar a Telegram que recibimos el click
    data = query.data
    uid = update.effective_chat.id

    # --- LOGICA DEL MENÚ ---
    if data == "menu_reset":
        chats_activos[uid] = model.start_chat(history=[])
        await context.bot.send_message(uid, "🧠 **Memoria reiniciada.** J.A.R.V.I.S. listo para nueva sesión.", parse_mode='Markdown')
    
    elif data == "menu_dado":
        await context.bot.send_dice(uid)
    
    elif data == "menu_id":
        await context.bot.send_message(uid, f"🆔 ID del Chat: `{uid}`", parse_mode='Markdown')
    
    elif data == "menu_help":
        help_text = (
            "📄 **LISTA DE COMANDOS:**\n\n"
            "• `/menu` - Abrir este panel\n"
            "• `/wiki [texto]` - Buscar info\n"
            "• `/habla [texto]` - J.A.R.V.I.S. habla\n"
            "• `/traducir` - (Responder a mensaje)\n"
            "• `/resumen` - (Responder a mensaje)\n"
            "• `Jarvis ...` - Para hablar en grupos"
        )
        await context.bot.send_message(uid, help_text, parse_mode='Markdown')
        
    elif data == "menu_voz":
        await context.bot.send_message(uid, "🎤 Para usar mi voz, escribe:\n`/habla Hola mundo`\n\nO responde a un mensaje con `/habla`.", parse_mode='Markdown')

    # --- LOGICA DEL CAPTCHA ---
    elif data.startswith("verify_"):
        usuario_id_boton = int(data.split("_")[1])
        usuario_que_cliqueo = query.from_user.id
        
        if usuario_que_cliqueo != usuario_id_boton:
            await context.bot.send_message(uid, "⛔ Este botón no es para ti.")
            return

        try:
            await context.bot.restrict_chat_member(uid, usuario_que_cliqueo, ChatPermissions(True, True, True, True))
            await query.message.delete()
            await context.bot.send_message(uid, f"✅ Acceso concedido, {query.from_user.first_name}.")
        except: pass

# ==========================================
# 3. FUNCIONES RESTANTES (IA, FOTOS, ETC)
# ==========================================
async def procesar_todo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_chat.id
    tipo = update.effective_chat.type
    msg_texto = update.message.text or update.message.caption or ""
    
    # Filtros
    if tipo != 'private' and any(p in msg_texto.lower() for p in PALABRAS_PROHIBIDAS):
        try: await update.message.delete(); return
        except: pass

    responder = True
    if tipo != 'private':
        bot_name = context.bot.username.lower()
        es_reply = update.message.reply_to_message and update.message.reply_to_message.from_user.id == context.bot.id
        if not ("jarvis" in msg_texto.lower() or f"@{bot_name}" in msg_texto.lower() or es_reply): 
            if not (update.message.voice or update.message.audio): responder = False
            else: responder = False 

    if not responder: return

    await context.bot.send_chat_action(uid, 'typing')
    try:
        contenido = []
        if msg_texto: contenido.append(msg_texto)
        
        archivo_temp = None
        if update.message.photo:
            f = await update.message.photo[-1].get_file()
            archivo_temp = "temp.jpg"
            await f.download_to_drive(archivo_temp)
            contenido.append(PIL.Image.open(archivo_temp))
        elif update.message.voice or update.message.audio:
            f = await (update.message.voice or update.message.audio).get_file()
            ext = ".ogg" if update.message.voice else ".mp3"
            archivo_temp = f"temp{ext}"
            await f.download_to_drive(archivo_temp)
            contenido.append(genai.upload_file(path=archivo_temp))
            contenido.append("Escucha y responde.")
        elif update.message.document:
             if 'pdf' in update.message.document.mime_type or 'text' in update.message.document.mime_type:
                 f = await update.message.document.get_file()
                 archivo_temp = update.message.document.file_name
                 await f.download_to_drive(archivo_temp)
                 contenido.append(genai.upload_file(path=archivo_temp))
                 contenido.append("Analiza este documento.")

        if uid not in chats_activos: chats_activos[uid] = model.start_chat(history=[])
        if not chats_activos[uid].history: chats_activos[uid].send_message("Eres J.A.R.V.I.S. Sé útil y breve.")

        resp = chats_activos[uid].send_message(contenido)
        await context.bot.send_message(uid, resp.text)
        if archivo_temp and os.path.exists(archivo_temp): os.remove(archivo_temp)
    except Exception as e:
        await context.bot.send_message(uid, "⚠️ Error procesando solicitud.")
        print(e)

# COMANDOS EXTRA
async def bienvenida_captcha(update: Update, context: ContextTypes.DEFAULT_TYPE):
    for nuevo in update.message.new_chat_members:
        if nuevo.id == context.bot.id: continue
        try:
            await context.bot.restrict_chat_member(update.effective_chat.id, nuevo.id, ChatPermissions(False))
            kb = [[InlineKeyboardButton("🤖 Verificar Humano", callback_data=f"verify_{nuevo.id}")]]
            await context.bot.send_message(update.effective_chat.id, f"Hola {nuevo.first_name}. Verifica identidad.", reply_markup=InlineKeyboardMarkup(kb))
        except: pass

async def hablar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = " ".join(context.args)
    if not texto and update.message.reply_to_message: texto = update.message.reply_to_message.text
    if not texto: return
    await context.bot.send_chat_action(update.effective_chat.id, 'record_voice')
    try:
        gTTS(text=texto, lang='es').save("voz.mp3")
        await context.bot.send_voice(update.effective_chat.id, voice=open("voz.mp3", "rb"))
        os.remove("voz.mp3")
    except: pass

async def wiki_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = " ".join(context.args)
    if not q: return
    try: await context.bot.send_message(update.effective_chat.id, f"📚 {wikipedia.summary(q, sentences=2)}")
    except: await context.bot.send_message(update.effective_chat.id, "❌ Sin resultados.")

async def banear(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID or not update.message.reply_to_message: return
    try: await context.bot.ban_chat_member(update.effective_chat.id, update.message.reply_to_message.from_user.id)
    except: pass

async def limpiar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    n = int(context.args[0]) if context.args else 5
    mid = update.message.message_id
    for i in range(n+1): 
        try: await context.bot.delete_message(update.effective_chat.id, mid-i)
        except: pass

async def traducir(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.reply_to_message: return
    try:
        r = model.start_chat(history=[]).send_message(f"Traduce: {update.message.reply_to_message.text}")
        await context.bot.send_message(update.effective_chat.id, f"🌍 {r.text}")
    except: pass

async def anuncio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    msg = " ".join(context.args)
    for g in GRUPOS_DESTINO: 
        try: await context.bot.send_message(g, msg)
        except: pass
    await context.bot.send_message(update.effective_chat.id, "✅ Enviado.")

async def resumir(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.reply_to_message: return
    try:
        r = model.start_chat(history=[]).send_message(f"Resume: {update.message.reply_to_message.text}")
        await context.bot.send_message(update.effective_chat.id, f"📝 {r.text}")
    except: pass

async def get_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
     await context.bot.send_message(update.effective_chat.id, f"`{update.effective_chat.id}`", parse_mode='Markdown')

# ==========================================
# ARRANQUE
# ==========================================
if __name__ == '__main__':
    keep_alive()
    if TELEGRAM_TOKEN:
        app_bot = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
        
        # COMANDO DEL MENÚ
        app_bot.add_handler(CommandHandler("menu", mostrar_menu))
        app_bot.add_handler(CommandHandler("start", mostrar_menu)) # /start también abre el menú
        
        # Comandos
        app_bot.add_handler(CommandHandler("habla", hablar))
        app_bot.add_handler(CommandHandler("wiki", wiki_search))
        app_bot.add_handler(CommandHandler("id", get_id))
        app_bot.add_handler(CommandHandler("anuncio", anuncio))
        app_bot.add_handler(CommandHandler("ban", banear))
        app_bot.add_handler(CommandHandler("resumen", resumir))
        app_bot.add_handler(CommandHandler("traducir", traducir))
        app_bot.add_handler(CommandHandler("limpiar", limpiar))
        
        # Manejador UNIFICADO de Botones (Menú + Captcha)
        app_bot.add_handler(CallbackQueryHandler(manejar_botones))
        
        # Eventos
        app_bot.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, bienvenida_captcha))
        app_bot.add_handler(MessageHandler(filters.ALL & (~filters.COMMAND) & (~filters.StatusUpdate.ALL), procesar_todo))
        
        app_bot.run_polling()
