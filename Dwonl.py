import os
import sqlite3
import logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler, ContextTypes
import yt_dlp
from keep_alive import keep_alive

# --- الإعدادات (استبدل البيانات هنا) ---
TOKEN = '8521737523:AAGv-XRGN9x-IqhDZZqTfS10U5rQveVZYlI'
ADMIN_ID = 5524416062  # ضع الآيدي الخاص بك هنا (للدخول للوحة التحكم)

# تشغيل سيرفر الويب للبقاء حياً 24 ساعة
keep_alive()

# --- إعداد قاعدة البيانات ---
def setup_db():
    conn = sqlite3.connect('data.db')
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS users (id TEXT PRIMARY KEY)')
    c.execute('CREATE TABLE IF NOT EXISTS groups (id TEXT PRIMARY KEY)')
    conn.commit()
    conn.close()

def add_data(table, chat_id):
    conn = sqlite3.connect('data.db')
    c = conn.cursor()
    c.execute(f'INSERT OR IGNORE INTO {table} VALUES (?)', (str(chat_id),))
    conn.commit()
    conn.close()

# --- وظيفة التحميل الشاملة ---
def download_media(url, mode):
    ydl_opts = {
        # 'best' للفيديو و 'bestaudio' للصوت
        'format': 'bestvideo+bestaudio/best' if mode == 'video' else 'bestaudio/best',
        'cookiefile': 'cookies.txt', # ضروري جداً ليوتيوب
        'outtmpl': 'downloads/%(title)s.%(ext)s',
        'nocheckcertificate': True,
        'quiet': True,
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
    }
    
    if not os.path.exists('downloads'):
        os.makedirs('downloads')

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        return ydl.prepare_filename(info)

# --- معالجة الأوامر ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    
    # ترحيب وحفظ البيانات
    if update.effective_chat.type == 'private':
        add_data('users', user_id)
        msg = f"أهلاً بك {update.effective_user.first_name}!\n\nأرسل لي أي رابط من (يوتيوب، فيسبوك، تيك توك، انستا، سناب) وسأقوم بتحميله فوراً."
    else:
        add_data('groups', chat_id)
        msg = "البوت مفعل الآن في المجموعة!"

    # أزرار المسؤول
    markup = None
    if user_id == ADMIN_ID:
        keyboard = [[InlineKeyboardButton("📊 إحصائيات المستخدمين", callback_data='stats')]]
        markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(msg, reply_markup=markup)

async def handle_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text
    if "http" in url:
        context.user_data['url'] = url
        keyboard = [[
            InlineKeyboardButton("فيديو 🎬", callback_data='v'),
            InlineKeyboardButton("صوت 🎵", callback_data='a')
        ]]
        await update.message.reply_text("اختر طريقة التحميل:", reply_markup=InlineKeyboardMarkup(keyboard))

async def actions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    # لوحة الإحصائيات
    if query.data == 'stats':
        conn = sqlite3.connect('data.db')
        c = conn.cursor()
        users = c.execute('SELECT COUNT(*) FROM users').fetchone()[0]
        groups = c.execute('SELECT COUNT(*) FROM groups').fetchone()[0]
        conn.close()
        await query.message.reply_text(f"📊 إحصائياتك:\n👤 المستخدمين: {users}\n👥 المجموعات: {groups}")
        return

    # التحميل
    url = context.user_data.get('url')
    mode = 'video' if query.data == 'v' else 'audio'
    wait_msg = await query.message.reply_text("🚀 جاري التحميل... انتظر قليلاً")

    try:
        path = download_media(url, mode)
        with open(path, 'rb') as f:
            if mode == 'video':
                await query.message.reply_video(video=f, caption="تم التحميل بواسطة بوتك ✅")
                else:
                await query.message.reply_audio(audio=f, caption="تم التحميل بواسطة بوتك ✅")
        os.remove(path)
        await wait_msg.delete()
    except Exception as e:
        await wait_msg.edit_text(f"❌ حدث خطأ، تأكد من ملف cookies.txt أو الرابط.\nالسبب: {str(e)[:50]}")

# --- التشغيل ---
if __name__ == '__main__':
    setup_db()
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_url))
    app.add_handler(CallbackQueryHandler(actions))
    print("البوت يعمل...")
    app.run_polling()
