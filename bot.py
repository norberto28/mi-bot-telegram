import logging
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ChatPermissions
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, CommandHandler, CallbackQueryHandler, filters
import google.generativeai as genai
from flask import Flask
from threading import Thread

# ==========================================
# CONFIGURACIÓN 👑
# ==========================================
ADMIN_ID = 1393624932  # <--- TU ID
GRUPOS_DESTINO = [-4947151665] # <--- TUS GRUPOS

# LISTA NEGRA DE PALABRAS (Edítala a tu gusto)
PALABRAS_PROHIBIDAS = ["estafa", "bitcoin gratis", "tonto", "idiota", "groseria"]

# ==========================================
# MANTENER VIVO
# ==========================================
app = Flask('')
@app.route('/')
def home(): return "J.A.R.V.I.S. Security & Admin Online"
def run(): app.run(host='0.0.0.0', port=8080)
def keep_alive(): t = Thread(target=run); t.start()

# ==========================================
# API Y CONFIGURACIÓN
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
# 1. CAPTCHA (BIENVENIDA)
# ==========================================
async def bienvenida_captcha(update: Update, context: ContextTypes.DEFAULT_TYPE):
    for nuevo in update.message.new_chat_members:
        if nuevo.id == context.bot.id: continue
        try:
            # Silenciar
            await context.bot.restrict_chat_member(
                update.effective_chat.id, nuevo.id,
                ChatPermissions(can_send_messages=False)
            )
            # Botón
            kb = [[InlineKeyboardButton("🤖 Verificar Humano", callback_data=f"verify_{nuevo.id}")]]
            await context.bot.send_message(
                update.effective_chat.id,
                f"Hola {nuevo.first_name}. Pulsa el botón para hablar.",
                reply_markup=InlineKeyboardMarkup(kb)
            )
        except: pass

async def verificar_usuario(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid = int(q.data.split("_")[1])
    if q.from_user.id != uid: return
    
    # Liberar
    try:
        await context.bot.restrict_chat_member(
            update.effective_chat.id, uid,
            ChatPermissions(True, True, True, True)
        )
        await q.message.delete()
        await context.bot.send_message(update.effective_chat.id, f"✅ Acceso concedido, {q.from_user.first_name}.")
    except: pass

# ==========================================
# 2. IA Y FILTRO DE GROSERÍAS (MODIFICADO)
# ==========================================
async def procesar_texto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message.text
    uid = update.effective_chat.id
    tipo = update.effective_chat.type
    user = update.effective_user

    # A. FILTRO DE GROSERÍAS (Solo en grupos)
    if tipo != 'private':
        # Revisamos si hay palabras malas
        if any(palabra in msg.lower() for palabra in PALABRAS_PROHIBIDAS):
            try:
                # 1. Borrar mensaje
                await update.message.delete()
                # 2. Advertencia
                alerta = await context.bot.send_message(uid, f"⚠️ {user.first_name}, modera tu lenguaje. Mensaje eliminado.")
                # (Opcional: borrar la alerta a los 10 seg para no ensuciar)
                return 
            except Exception as e:
                print(f"No pude borrar mensaje (¿Soy admin?): {e}")

    # B. INTELIGENCIA ARTIFICIAL
    # En grupos solo responde si lo llaman
    responder = True
    if tipo != 'private':
        bot_name = context.bot.username.lower()
        es_reply = update.message.reply_to_message and update.message.reply_to_message.from_user.id == context.bot.id
        if not ("jarvis" in msg.lower() or f"@{bot_name}" in msg.lower() or es_reply):
            responder = False

    if responder:
        await context.bot.send_chat_action(uid, 'typing')
        try:
            if uid not in chats_activos:
                chats_activos[uid] = model.start_chat(history=[{"role":"user","parts":"Eres J.A.R.V.I.S."},{"role":"model","parts":"Si señor."}])
            resp = chats_activos[uid].send_message(msg)
            await context.bot.send_message(uid, resp.text)
        except:
             chats_activos[uid] = model.start_chat(history=[])

# ==========================================
# 3. COMANDOS NUEVOS (ADMIN)
# ==========================================

# /ban (Respondiendo a un mensaje)
async def banear_usuario(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Solo el ADMIN puede usar esto
    if update.effective_user.id != ADMIN_ID: return
    
    # Debe ser respuesta a alguien
    if not update.message.reply_to_message:
        await context.bot.send_message(update.effective_chat.id, "⚠️ Responde al mensaje del usuario que quieres banear.")
        return

    usuario_a_banear = update.message.reply_to_message.from_user.id
    nombre = update.message.reply_to_message.from_user.first_name

    try:
        await context.bot.ban_chat_member(update.effective_chat.id, usuario_a_banear)
        await context.bot.send_message(update.effective_chat.id, f"🚫 {nombre} ha sido eliminado del grupo por orden del Administrador.")
    except Exception as e:
        await context.bot.send_message(update.effective_chat.id, f"⚠️ No pude banearlo. ¿Soy admin? Error: {e}")

# /resumen (Respondiendo a un texto largo)
async def resumir(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.reply_to_message: return
    
    texto_largo = update.message.reply_to_message.text
    if not texto_largo: return

    await context.bot.send_chat_action(update.effective_chat.id, 'typing')
    try:
        prompt = f"Resume el siguiente texto en 2 frases clave: {texto_largo}"
        chat = model.start_chat(history=[])
        resp = chat.send_message(prompt)
        await context.bot.send_message(update.effective_chat.id, f"📝 **Resumen:**\n{resp.text}", parse_mode='Markdown')
    except: pass

# Comandos de utilidad anteriores
async def obtener_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id, text=f"🆔 ID: `{update.effective_chat.id}`", parse_mode='Markdown')

async def enviar_anuncio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    msg = " ".join(context.args)
    for g in GRUPOS_DESTINO:
        try: await context.bot.send_message(g, msg)
        except: pass
    await context.bot.send_message(update.effective_chat.id, "✅ Anuncio enviado.")

# ==========================================
# ARRANQUE
# ==========================================
if __name__ == '__main__':
    keep_alive()
    if TELEGRAM_TOKEN:
        app_bot = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
        
        # Comandos
        app_bot.add_handler(CommandHandler("id", obtener_id))
        app_bot.add_handler(CommandHandler("anuncio", enviar_anuncio))
        app_bot.add_handler(CommandHandler("ban", banear_usuario)) # Nuevo
        app_bot.add_handler(CommandHandler("resumen", resumir))     # Nuevo
        
        # Eventos
        app_bot.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, bienvenida_captcha))
        app_bot.add_handler(CallbackQueryHandler(verificar_usuario))
        
        # Texto e IA (Aquí va el filtro de groserías)
        app_bot.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), procesar_texto))
        
        app_bot.run_polling()
