import os
import logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler, ContextTypes
import yt_dlp
from keep_alive import keep_alive

# إعدادات البوت
TOKEN = '8521737523:AAGv-XRGN9x-IqhDZZqTfS10U5rQveVZYlI'
ADMIN_ID = 5524416062  # الآيدي الخاص بك

# تشغيل سيرفر الإبقاء حياً
keep_alive()

# دالة التحميل
def download_media(url, mode):
    ydl_opts = {
        'format': 'best' if mode == 'video' else 'bestaudio/best',
        'outtmpl': 'downloaded_file.%(ext)s',
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        return ydl.prepare_filename(info)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # حفظ المستخدم (بشكل بسيط في ملف نصي)
    user_id = str(update.effective_user.id)
    with open("users.txt", "a+") as f:
        f.seek(0)
        if user_id not in f.read():
            f.write(user_id + "\n")
    
    await update.message.reply_text(f"أهلاً بك {update.effective_user.first_name}! أرسل رابط الفيديو الآن.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text
    if "http" in url:
        context.user_data['url'] = url
        keyboard = [[InlineKeyboardButton("فيديو 🎬", callback_data='video'),
                     InlineKeyboardButton("صوت 🎵", callback_data='audio')]]
        await update.message.reply_text("اختر الصيغة:", reply_markup=InlineKeyboardMarkup(keyboard))

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("جاري التحميل... انتظر قليلاً")
    url = context.user_data.get('url')
    mode = query.data
    
    try:
        file_path = download_media(url, mode)
        with open(file_path, 'rb') as f:
            if mode == 'video':
                await query.message.reply_video(f)
            else:
                await query.message.reply_audio(f)
        os.remove(file_path) # حذف الملف بعد الإرسال لتوفير المساحة
    except Exception as e:
        await query.message.reply_text(f"حدث خطأ: {str(e)}")

if __name__ == '__main__':
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(button_callback))
    app.run_polling()