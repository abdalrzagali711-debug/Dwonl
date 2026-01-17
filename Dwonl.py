import os
import sqlite3
import logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler, ContextTypes
import yt_dlp
from keep_alive import keep_alive

# --- الإعدادات ---
TOKEN = '8521737523:AAGv-XRGN9x-IqhDZZqTfS10U5rQveVZYlI'
ADMIN_ID = 5524416062  # ضع الآيدي الخاص بك هنا (رقم فقط)

# إعداد السجلات (Logs) لسهولة اكتشاف الأخطاء
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# تشغيل سيرفر الإبقاء حياً للعمل 24 ساعة على Render
keep_alive()

# --- قاعدة البيانات ---
def setup_db():
    conn = sqlite3.connect('bot_database.db')
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS users (id TEXT PRIMARY KEY)')
    c.execute('CREATE TABLE IF NOT EXISTS groups (id TEXT PRIMARY KEY)')
    conn.commit()
    conn.close()

def save_user(user_id):
    conn = sqlite3.connect('bot_database.db')
    c = conn.cursor()
    c.execute('INSERT OR IGNORE INTO users VALUES (?)', (str(user_id),))
    conn.commit()
    conn.close()

def save_group(group_id):
    conn = sqlite3.connect('bot_database.db')
    c = conn.cursor()
    c.execute('INSERT OR IGNORE INTO groups VALUES (?)', (str(group_id),))
    conn.commit()
    conn.close()

def get_stats():
    conn = sqlite3.connect('bot_database.db')
    c = conn.cursor()
    c.execute('SELECT COUNT(*) FROM users')
    u_count = c.fetchone()[0]
    c.execute('SELECT COUNT(*) FROM groups')
    g_count = c.fetchone()[0]
    conn.close()
    return u_count, g_count

# --- منطق التحميل ---
def download_media(url, mode):
    # إعدادات yt-dlp لتجاوز الحظر والتحميل
    ydl_opts = {
        'format': 'best' if mode == 'video' else 'bestaudio/best',
        'cookiefile': 'cookies.txt', # تأكد من وجود الملف في المشروع
        'outtmpl': 'downloads/%(title)s.%(ext)s',
        'nocheckcertificate': True,
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
    }
    
    if not os.path.exists('downloads'):
        os.makedirs('downloads')

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        return ydl.prepare_filename(info)

# --- معالجة الأوامر ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat = update.effective_chat
    
    # حفظ المستخدم أو المجموعة
    if chat.type == 'private':
        save_user(user.id)
        welcome_text = f"أهلاً بك يا {user.first_name} في بوت التحميل الشامل! 🚀\n\nأرسل رابطاً من يوتيوب، تيك توك، أو إنستغرام وسأقوم بتحميله لك فوراً."
    else:
        save_group(chat.id)
        welcome_text = "تم تفعيل البوت في المجموعة! أرسلوا الروابط وسأقوم بالتحميل."

    # أزرار لوحة التحكم للمسؤول فقط
    reply_markup = None
    if user.id == ADMIN_ID:
        keyboard = [[InlineKeyboardButton("📊 إحصائيات البوت", callback_data='show_stats')]]
        reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(welcome_text, reply_markup=reply_markup)

async def handle_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text
    if url.startswith("http"):
        context.user_data['pending_url'] = url
        keyboard = [
            [
                InlineKeyboardButton("تحميل فيديو 🎬", callback_data='dl_video'),
                InlineKeyboardButton("تحميل صوت 🎵", callback_data='dl_audio')
            ]
        ]
        await update.message.reply_text("كيف تريد تحميل الرابط؟", reply_markup=InlineKeyboardMarkup(keyboard))

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    # لوحة التحكم
    if query.data == 'show_stats':
        u, g = get_stats()
        await query.message.reply_text(f"📊 إحصائيات البوت الحالية:\n\n👤 عدد المستخدمين: {u}\n👥 عدد المجموعات: {g}")
        return
    # عملية التحميل
    url = context.user_data.get('pending_url')
    mode = 'video' if query.data == 'dl_video' else 'audio'
    
    status_msg = await query.message.reply_text("⏳ جاري المعالجة والتحميل... يرجى الانتظار.")
    
    try:
        file_path = download_media(url, mode)
        with open(file_path, 'rb') as f:
            if mode == 'video':
                await query.message.reply_video(video=f, caption="✅ تم التحميل بنجاح!")
            else:
                await query.message.reply_audio(audio=f, caption="✅ تم تحويل الملف الصوتي!")
        
        # تنظيف: حذف الملف بعد الإرسال لتوفير مساحة السيرفر
        os.remove(file_path)
        await status_msg.delete()
        
    except Exception as e:
        await status_msg.edit_text(f"❌ حدث خطأ أثناء التحميل.\nتأكد من الرابط أو ملف الكوكيز.\n\nالسبب: {str(e)[:100]}")

# --- التشغيل الأساسي ---
if __name__ == '__main__':
    setup_db()
    application = Application.builder().token(TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_url))
    application.add_handler(CallbackQueryHandler(callback_handler))
    
    print("البوت يعمل الآن بنجاح...")
    application.run_polling()
