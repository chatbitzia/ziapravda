import logging
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.state import State, StatesGroup
from aiogram.filters import CommandStart, Command
from flask import Flask
from threading import Thread

API_TOKEN = '8077961165:AAGOcmrcXYXswfosdH8LMbwf5TLUqmHrIpM'
GROUP_ID = -1002801579739

CATEGORIES = [
    "Работа служб", "Руководство", "Условия труда", "Безопасность и охрана",
    "Другое"
]

logging.basicConfig(level=logging.INFO)

bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)


class FeedbackForm(StatesGroup):
    choosing_category = State()
    typing_feedback = State()


@dp.message(CommandStart())
async def start_handler(message: types.Message, state: FSMContext):
    keyboard_buttons = [[KeyboardButton(text=cat)] for cat in CATEGORIES]
    markup = ReplyKeyboardMarkup(keyboard=keyboard_buttons,
                                 resize_keyboard=True)
    await message.answer(
        "👋 Добро пожаловать в анонимный Telegram-бот для сотрудников аэропорта.\n\n"
        "Пожалуйста, выберите категорию, по которой хотите оставить отзыв:",
        reply_markup=markup)
    await state.set_state(FeedbackForm.choosing_category)


@dp.message(FeedbackForm.choosing_category)
async def category_chosen(message: types.Message, state: FSMContext):
    category = message.text
    if category not in CATEGORIES:
        await message.answer("Пожалуйста, выберите категорию из списка.")
        return
    await state.update_data(category=category)
    await message.answer("✏️ Пожалуйста, напишите Ваш анонимный отзыв при желании добавьте фото:",
                         reply_markup=types.ReplyKeyboardRemove())
    await state.set_state(FeedbackForm.typing_feedback)


@dp.message(FeedbackForm.typing_feedback,
            lambda message: message.text and not message.photo)
async def feedback_text_received(message: types.Message, state: FSMContext):
    feedback = message.text
    data = await state.get_data()
    category = data['category']
    full_message = f"📨 Новый анонимный отзыв:\nКатегория: {category}\nОтзыв: {feedback}"
    await bot.send_message(GROUP_ID, full_message)
    back_markup = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="Назад")]],
                                      resize_keyboard=True)
    await message.answer("✅ Спасибо! Ваш отзыв передан руководству.",
                         reply_markup=back_markup)
    await state.clear()


@dp.message(FeedbackForm.typing_feedback, lambda message: message.photo)
async def feedback_photo_received(message: types.Message, state: FSMContext):
    data = await state.get_data()
    category = data['category']
    caption = f"📨 Новый анонимный отзыв:\nКатегория: {category}"
    if message.caption:
        caption += f"\nКомментарий: {message.caption}"
    await bot.send_photo(GROUP_ID, message.photo[-1].file_id, caption=caption)
    back_markup = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="Назад")]],
                                      resize_keyboard=True)
    await message.answer("✅ Спасибо! Ваш отзыв с фото передан руководству.",
                         reply_markup=back_markup)
    await state.clear()


@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    help_text = ("Доступные команды:\n"
                 "/start - Начать работу с ботом\n"
                 "/help - Показать эту справку")
    await message.reply(help_text)


@dp.message(lambda message: message.text == "Назад")
async def go_back_to_category(message: types.Message, state: FSMContext):
    keyboard_buttons = [[KeyboardButton(text=cat)] for cat in CATEGORIES]
    markup = ReplyKeyboardMarkup(keyboard=keyboard_buttons,
                                 resize_keyboard=True)
    await message.answer("Пожалуйста, выберите категорию для отзыва:",
                         reply_markup=markup)
    await state.set_state(FeedbackForm.choosing_category)


@dp.message()
async def echo(message: types.Message):
    await message.reply(
        "Я не понимаю эту команду. Используйте /help для получения списка доступных команд."
    )


async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot, skip_updates=True, handle_signals=False)


# --- 🌐 Flask-сервер ---
app = Flask(__name__)

@app.route('/')
def home():
    return "✅ Бот запущен."

@app.route('/ping')
def ping():
    return "🏓 Pong!"


def run_flask():
    app.run(host='0.0.0.0', port=8080)


def start_aiogram():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.create_task(main())
    loop.run_forever()


if __name__ == '__main__':
    Thread(target=start_aiogram).start()
    run_flask()
