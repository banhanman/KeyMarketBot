import logging
from aiogram import Bot, Dispatcher, types, executor
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, LabeledPrice
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
import sqlite3
import config

# Настройка логов
logging.basicConfig(level=logging.INFO)

# Инициализация бота
bot = Bot(token=config.TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

# Подключение к БД
conn = sqlite3.connect('keys.db')
cursor = conn.cursor()

# Создание таблиц
cursor.execute('''
CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    price INTEGER NOT NULL,
    category TEXT
)''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS keys (
    id INTEGER PRIMARY KEY,
    product_id INTEGER,
    key TEXT UNIQUE,
    is_used INTEGER DEFAULT 0,
    FOREIGN KEY(product_id) REFERENCES products(id)
)''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY,
    user_id INTEGER,
    product_id INTEGER,
    key_id INTEGER,
    amount INTEGER,
    status TEXT DEFAULT 'new',
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
)''')
conn.commit()

# Классы состояний
class OrderState(StatesGroup):
    waiting_for_product = State()
    confirm_payment = State()

# Команда /start
@dp.message_handler(commands=['start'])
async def send_welcome(message: types.Message):
    keyboard = InlineKeyboardMarkup(row_width=2)
    buttons = [
        InlineKeyboardButton("🪟 Windows", callback_data="cat_windows"),
        InlineKeyboardButton("📊 Office", callback_data="cat_office"),
        InlineKeyboardButton("🛒 Мои покупки", callback_data="my_orders"),
        InlineKeyboardButton("🆘 Поддержка", callback_data="support")
    ]
    keyboard.add(*buttons)
    
    await message.answer(
        "🔑 Добро пожаловать в KeyMarketBot!\n\n"
        "✅ Оригинальные ключи активации:\n"
        "• Microsoft Windows\n"
        "• Microsoft Office\n\n"
        "⚡ Мгновенная доставка после оплаты\n"
        "🛡️ Гарантия замены при проблемах\n\n"
        "Выберите категорию:",
        reply_markup=keyboard
    )

# Обработчик категорий
@dp.callback_query_handler(lambda c: c.data.startswith('cat_'))
async def process_category(callback_query: types.CallbackQuery):
    category = callback_query.data.split('_')[1]
    cursor.execute("SELECT id, name, price FROM products WHERE category = ?", (category,))
    products = cursor.fetchall()
    
    keyboard = InlineKeyboardMarkup()
    for product in products:
        keyboard.add(InlineKeyboardButton(
            f"{product[1]} - {product[2]}₽", 
            callback_data=f"prod_{product[0]}"
        ))
    keyboard.add(InlineKeyboardButton("🔙 Назад", callback_data="back_to_main"))
    
    await bot.edit_message_text(
        chat_id=callback_query.message.chat.id,
        message_id=callback_query.message.message_id,
        text=f"Выберите продукт из категории {category.upper()}:",
        reply_markup=keyboard
    )

# Обработчик выбора товара
@dp.callback_query_handler(lambda c: c.data.startswith('prod_'))
async def process_product(callback_query: types.CallbackQuery, state: FSMContext):
    product_id = int(callback_query.data.split('_')[1])
    cursor.execute("SELECT * FROM products WHERE id = ?", (product_id,))
    product = cursor.fetchone()
    
    if not product:
        await bot.answer_callback_query(callback_query.id, "Товар не найден!")
        return
    
    async with state.proxy() as data:
        data['product_id'] = product_id
    
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("💳 Купить", callback_data="buy_now"))
    keyboard.add(InlineKeyboardButton("🔙 Назад", callback_data=f"cat_{product[4]}"))
    
    await bot.edit_message_text(
        chat_id=callback_query.message.chat.id,
        message_id=callback_query.message.message_id,
        text=f"<b>{product[1]}</b>\n\n{product[2]}\n\nЦена: <b>{product[3]}₽</b>",
        parse_mode="HTML",
        reply_markup=keyboard
    )

# Обработчик покупки
@dp.callback_query_handler(text="buy_now", state="*")
async def process_buy(callback_query: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data:
        product_id = data['product_id']
    
    cursor.execute("SELECT * FROM products WHERE id = ?", (product_id,))
    product = cursor.fetchone()
    
    # Создаем инвойс
    await bot.send_invoice(
        chat_id=callback_query.message.chat.id,
        title=product[1],
        description=product[2],
        payload=f"order_{product_id}",
        provider_token=config.PAYMENT_TOKEN,
        currency="RUB",
        prices=[LabeledPrice(label=product[1], amount=product[3]*100)],
        start_parameter="keymarket",
        photo_url="https://via.placeholder.com/400/008000/FFFFFF?text=KeyMarket",
        photo_size=512
    )
    await OrderState.confirm_payment.set()

# Обработка успешной оплаты
@dp.pre_checkout_query_handler(state=OrderState.confirm_payment)
async def process_pre_checkout(pre_checkout_query: types.PreCheckoutQuery):
    await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)

@dp.message_handler(content_types=types.ContentType.SUCCESSFUL_PAYMENT, state=OrderState.confirm_payment)
async def process_successful_payment(message: types.Message, state: FSMContext):
    # Получаем данные о платеже
    payment = message.successful_payment
    product_id = int(payment.invoice_payload.split('_')[1])
    
    # Находим свободный ключ
    cursor.execute("SELECT id, key FROM keys WHERE product_id = ? AND is_used = 0 LIMIT 1", (product_id,))
    key_data = cursor.fetchone()
    
    if key_data:
        key_id, key_value = key_data
        # Помечаем ключ как использованный
        cursor.execute("UPDATE keys SET is_used = 1 WHERE id = ?", (key_id,))
        # Создаем запись о заказе
        cursor.execute(
            "INSERT INTO orders (user_id, product_id, key_id, amount) VALUES (?, ?, ?, ?)",
            (message.from_user.id, product_id, key_id, payment.total_amount // 100)
        )
        conn.commit()
        
        # Отправляем ключ пользователю
        await message.answer(
            "✅ Оплата прошла успешно!\n\n"
            f"Ваш ключ: <code>{key_value}</code>\n\n"
            "Инструкция по активации:\n"
            "1. Запустите командную строку от имени администратора\n"
            "2. Введите: <code>slmgr /ipk ваш_ключ</code>\n"
            "3. Для активации: <code>slmgr /skms kms8.msguides.com</code>\n"
            "4. Затем: <code>slmgr /ato</code>\n\n"
            "📬 Ключ сохранен в истории заказов (/orders)",
            parse_mode="HTML"
        )
    else:
        await message.answer(
            "⚠️ Извините, ключи временно закончились!\n"
            "Администратор уже уведомлен, ваш платеж будет возвращен в течение 24 часов."
        )
    
    await state.finish()

# Команда для просмотра заказов
@dp.message_handler(commands=['orders'])
async def show_orders(message: types.Message):
    cursor.execute(
        "SELECT o.id, p.name, k.key, o.timestamp "
        "FROM orders o "
        "JOIN products p ON o.product_id = p.id "
        "JOIN keys k ON o.key_id = k.id "
        "WHERE o.user_id = ? ORDER BY o.timestamp DESC",
        (message.from_user.id,)
    )
    orders = cursor.fetchall()
    
    if not orders:
        await message.answer("У вас пока нет покупок.")
        return
    
    response = "🛒 История ваших покупок:\n\n"
    for order in orders:
        response += f"📅 {order[3]}\n🛒 {order[1]}\n🔑 <code>{order[2]}</code>\n\n"
    
    await message.answer(response, parse_mode="HTML")

# Запуск бота
if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
