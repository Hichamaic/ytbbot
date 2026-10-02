import os
import re
import yt_dlp
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

# التوكن تاعك
TOKEN = "8695577690:AAFV5o9nDPTIBk3J-FRgH4hjZj6VJLzWoL4"

# نخزن الروابط مؤقتا
URLS = {}

def clean_url(text):
    m = re.search(r'(https?://[^\s]+)', text)
    return m.group(1) if m else None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "أهلا بك في بوت تحميل اليوتيوب 👋\n\n"
        "أرسل لي رابط يوتيوب فقط، وسأعطيك خيارات التحميل:\n"
        "🎬 فيديو 720p / 480p / 360p\n"
        "🎵 صوت MP3"
    )

async def handle_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = clean_url(update.message.text)
    if not url or "youtu" not in url:
        await update.message.reply_text("❌ أرسل رابط يوتيوب صحيح فقط.")
        return

    URLS[update.effective_user.id] = url

    keyboard = [
        [InlineKeyboardButton("🎬 فيديو 720p", callback_data="video_720"),
         InlineKeyboardButton("🎬 فيديو 480p", callback_data="video_480")],
        [InlineKeyboardButton("🎬 فيديو 360p", callback_data="video_360"),
         InlineKeyboardButton("🎵 صوت MP3", callback_data="audio_mp3")]
    ]
    await update.message.reply_text(
        f"✅ تمام، وجدت الرابط:\n{url}\n\nاختر الصيغة:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def handle_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    choice = query.data
    user_id = query.from_user.id
    url = URLS.get(user_id)
    if not url:
        await query.edit_message_text("انتهت صلاحية الرابط، أرسله مرة أخرى.")
        return

    await query.edit_message_text(f"⏳ جاري التحميل {choice}... قد يأخذ دقيقة")

    filename_base = f"{user_id}_{choice}"
    downloaded_file = None

    try:
        if choice.startswith("video"):
            height = choice.split("_")[1]
            ydl_opts = {
                'format': f'bestvideo[height<={height}][ext=mp4]+bestaudio[ext=m4a]/best[height<={height}][ext=mp4]/best',
                'outtmpl': f'{filename_base}.%(ext)s',
                'merge_output_format': 'mp4',
                'quiet': True,
            }
        else:
            ydl_opts = {
                'format': 'bestaudio/best',
                'outtmpl': f'{filename_base}.%(ext)s',
                'postprocessors': [{'key': 'FFmpegExtractAudio','preferredcodec': 'mp3','preferredquality': '192'}],
                'quiet': True,
            }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            downloaded_file = ydl.prepare_filename(info)
            if choice == "audio_mp3":
                downloaded_file = os.path.splitext(downloaded_file)[0] + ".mp3"

        if not os.path.exists(downloaded_file):
            # احيانا الامتداد يتغير
            for f in os.listdir("."):
                if f.startswith(filename_base):
                    downloaded_file = f
                    break

        size_mb = os.path.getsize(downloaded_file) / (1024*1024)
        if size_mb > 49:
            await context.bot.send_message(user_id, f"⚠️ الملف كبير جدا ({size_mb:.1f} MB) - تيليجرام لا يسمح بأكثر من 50MB للبوتات المجانية. جرب جودة أقل 360p أو مقطع أقصر.")
            os.remove(downloaded_file)
            return

        if choice.startswith("video"):
            await context.bot.send_video(
                chat_id=user_id, 
                video=open(downloaded_file, 'rb'), 
                caption=f"تم ✅ {info.get('title', '')[:100]}",
                supports_streaming=True
            )
        else:
            await context.bot.send_audio(
                chat_id=user_id, 
                audio=open(downloaded_file, 'rb'), 
                title=info.get('title', 'audio')[:100]
            )

        os.remove(downloaded_file)
        await context.bot.send_message(user_id, "✅ تم! أرسل رابط آخر للتحميل.")

    except Exception as e:
        print(f"Error: {e}")
        await context.bot.send_message(user_id, f"❌ حدث خطأ: {str(e)[:300]}\nجرب رابط آخر أو جودة أقل.")
        if downloaded_file and os.path.exists(downloaded_file):
            os.remove(downloaded_file)

if __name__ == "__main__":
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_link))
    app.add_handler(CallbackQueryHandler(handle_choice))
    print("البوت شغال... اذهب لتيليجرام وجربه")
    app.run_polling()
