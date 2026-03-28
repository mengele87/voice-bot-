import os
import asyncio
import logging
import subprocess
import whisper
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram import F  # магический фильтр

# Токен берётся из переменных окружения (задаётся на Render)
API_TOKEN = os.getenv("API_TOKEN")
if not API_TOKEN:
    raise ValueError("API_TOKEN environment variable not set")

MODEL_SIZE = "tiny"
TEMP_DIR = "temp"

os.makedirs(TEMP_DIR, exist_ok=True)
logging.basicConfig(level=logging.INFO)

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

print("🔄 Загрузка модели Whisper (1-2 минуты при первом запуске)...")
model = whisper.load_model(MODEL_SIZE)
print("✅ Модель загружена! Бот готов.")

def convert_ogg_to_wav(ogg_path: str, wav_path: str) -> bool:
    try:
        cmd = ["ffmpeg", "-i", ogg_path, "-acodec", "pcm_s16le", "-ar", "16000", wav_path, "-y"]
        subprocess.run(cmd, check=True, capture_output=True)
        return True
    except Exception as e:
        print(f"Ошибка конвертации: {e}")
        return False

def transcribe_audio(wav_path: str, language: str = "ru") -> str:
    try:
        result = model.transcribe(wav_path, language=language)
        return result["text"].strip()
    except Exception as e:
        print(f"Ошибка распознавания: {e}")
        return ""

@dp.message(Command("start"))
async def send_welcome(message: types.Message):
    await message.reply(
        "👋 Привет! Я бот для расшифровки голосовых сообщений.\n"
        "Просто отправь голосовое сообщение, и я превращу его в текст!\n"
        "Поддерживается русский язык 🇷🇺"
    )

@dp.message(F.voice)
async def handle_voice(message: types.Message):
    processing_msg = await message.reply("🎤 Распознаю голосовое сообщение...")
    try:
        voice = message.voice
        file_info = await bot.get_file(voice.file_id)
        file_path = file_info.file_path

        ogg_path = os.path.join(TEMP_DIR, f"{message.message_id}.ogg")
        await bot.download_file(file_path, destination=ogg_path)

        wav_path = os.path.join(TEMP_DIR, f"{message.message_id}.wav")
        if not convert_ogg_to_wav(ogg_path, wav_path):
            await processing_msg.edit_text("❌ Ошибка конвертации. Убедитесь, что установлен ffmpeg.")
            return

        text = transcribe_audio(wav_path, language="ru")

        if os.path.exists(ogg_path):
            os.remove(ogg_path)
        if os.path.exists(wav_path):
            os.remove(wav_path)

        if text:
            await processing_msg.edit_text(f"📝 **Расшифровка:**\n\n{text}")
        else:
            await processing_msg.edit_text("❌ Не удалось распознать речь.")

    except Exception as e:
        print(f"Ошибка: {e}")
        await processing_msg.edit_text("❌ Произошла ошибка. Попробуйте ещё раз.")

async def main():
    await dp.start_polling(bot, skip_updates=True)

if __name__ == "__main__":
    print("🚀 Бот запускается...")
    asyncio.run(main())