import logging
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils import executor
from aiogram.dispatcher import FSMContext
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher.filters.state import State, StatesGroup

# ========== CONFIG ==========
API_TOKEN = '8077961165:AAGOcmrcXYXswfosdH8LMbwf5TLUqmHrIpM'
GROUP_ID = -1002801579739
CATEGORIES = [
    "Работа служб",
    "Руководство",
    "Условия труда",
    "Безопасность и охрана",
    "Другое"
]
ADMIN_IDS = [-1002801579739]  # Добавь сюда свой Telegram ID для команды /ответ

# ========== БАЗА (простая на память) ==========
feedback_counter = 100
feedback_map = {}  # {отзыв_id: user_id}

# ========== BOT INIT ==========
logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

# ========== FSM ==========
class FeedbackForm(StatesGroup):
    choosing_category = State()
    typing_feedback = State()
    waiting_reply_option = State()

# ========== КЛАВИАТУРЫ ==========
category_markup = ReplyKeyboardMarkup(resize_keyboard=True)
for cat in CATEGORIES:
    category_markup.add(KeyboardButton(cat))

back_markup = ReplyKeyboardMarkup(resize_keyboard=True)
back_markup.add(KeyboardButton("Назад"))

reply_option_markup = ReplyKeyboardMarkup(resize_keyboard=True)
reply_option_markup.add(KeyboardButton("✅ Хочу получить ответ"))
reply_option_markup.add(KeyboardButton("❌ Без ответа"))

# ========== ХЕНДЛЕРЫ ==========
@dp.message_handler(commands=['start'])
async def start_handler(message: types.Message):
    await message.answer(
        "👋 Добро пожаловать в анонимный Telegram-бот для сотрудников аэропорта!\n\n"
        "Здесь Вы можете оставить отзывы, предложения и прикрепить фото.\n"
        "Пожалуйста, выберите категорию:",
        reply_markup=category_markup
    )
    await FeedbackForm.choosing_category.set()

@dp.message_handler(lambda message: message.text == "Назад")
async def go_back_to_category(message: types.Message):
    await message.answer(
        "Пожалуйста, выберите категорию для нового отзыва:",
        reply_markup=category_markup
    )
    await FeedbackForm.choosing_category.set()

@dp.message_handler(state=FeedbackForm.choosing_category)
async def category_chosen(message: types.Message, state: FSMContext):
    category = message.text
    if category not in CATEGORIES:
        await message.answer("Пожалуйста, выберите категорию из списка.")
        return

    await state.update_data(category=category)
    await message.answer("✏️ Пожалуйста, напишите Ваш анонимный отзыв или прикрепите фото:")
    await FeedbackForm.typing_feedback.set()

@dp.message_handler(content_types=['text', 'photo'], state=FeedbackForm.typing_feedback)
async def feedback_received(message: types.Message, state: FSMContext):
    global feedback_counter
    data = await state.get_data()
    category = data['category']

    feedback_id = feedback_counter
    feedback_counter += 1

    caption = f"📨 Новый анонимный отзыв #{feedback_id}:\nКатегория: {category}"

    if message.content_type == 'photo':
        if message.caption:
            caption += f"\nКомментарий: {message.caption}"
        await bot.send_photo(GROUP_ID, message.photo[-1].file_id, caption=caption)
    else:
        caption += f"\nОтзыв: {message.text}"
        await bot.send_message(GROUP_ID, caption)

    await state.update_data(feedback_id=feedback_id)
    await message.answer("Хотите получить ответ от администрации?", reply_markup=reply_option_markup)
    await FeedbackForm.waiting_reply_option.set()

@dp.message_handler(state=FeedbackForm.waiting_reply_option)
async def reply_option(message: types.Message, state: FSMContext):
    data = await state.get_data()
    feedback_id = data['feedback_id']

    if message.text.startswith("✅"):
        feedback_map[feedback_id] = message.from_user.id
        await bot.send_message(GROUP_ID, f"📌 Отзыв #{feedback_id}: сотрудник хочет получить ответ. Напишите: /ответ {feedback_id} <текст>")
        await message.answer("✅ Спасибо! Мы отправим Вам ответ, как только он будет готов.", reply_markup=back_markup)
    else:
        await message.answer("✅ Спасибо! Ваш отзыв передан руководству.", reply_markup=back_markup)

    await state.finish()

@dp.message_handler(commands=['ответ'])
async def send_admin_reply(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        await message.reply("⛔ У Вас нет прав для отправки ответов.")
        return

    args = message.text.split(maxsplit=2)
    if len(args) < 3:
        await message.reply("❗ Формат: /ответ <номер> <текст ответа>")
        return

    feedback_id = int(args[1])
    reply_text = args[2]

    user_id = feedback_map.get(feedback_id)
    if user_id:
        try:
            await bot.send_message(user_id, f"📩 Ответ на Ваш отзыв #{feedback_id}:\n{reply_text}")
            await message.reply("✅ Ответ отправлен.")
        except:
            await message.reply("⚠ Не удалось отправить ответ. Возможно, пользователь заблокировал бота.")
    else:
        await message.reply("❌ Отзыв с таким номером не найден или сотрудник не запросил ответ.")

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
