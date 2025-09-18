from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor

BOT_TOKEN = "8275504974:AAEJblNngby0n-XEEUNn0nVe4y_BxAVEEsw"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

@dp.message_handler(commands=['start'])
async def start_command(message: types.Message):
    await message.reply("Привет!")

if __name__ == "__main__":
    executor.start_polling(dp)