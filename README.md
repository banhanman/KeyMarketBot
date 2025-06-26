🤖 KeyMarketBot - Telegram-бот для продажи ключей Windows/Office

Автоматизированная система продажи цифровых лицензий с мгновенной доставкой ключей после оплаты.

## 🌟 Особенности
- Каталог продуктов с категориями (Windows/Office)
- Платежная система через Telegram Payments
- Автоматическая выдача ключей
- История покупок для пользователей
- Система управления ключами для администратора
- Резервное копирование базы данных

## 🛠 Установка
1. Клонируйте репозиторий:
```bash
git clone https://github.com/banhanman/KeyMarketBot.git
cd KeyMarketBot
```

2. Установите зависимости:
```bash
pip install aiogram python-dotenv sqlite3
```

3. Настройте конфигурацию:
```bash
cp config.example.py config.py
nano config.py
```

4. Создайте бота через [@BotFather](https://t.me/BotFather):
- Получите основной токен
- Включите платежи командой `/mybots` → Выбрать бота → Bot Settings → Payments

5. Инициализируйте базу данных:
```bash
python init_db.py
```

6. Добавьте товары и ключи (пример):
```sql
INSERT INTO products (name, description, price, category) 
VALUES ('Windows 10 Pro', 'Лицензионный ключ для Windows 10 Professional', 799, 'windows');

INSERT INTO keys (product_id, key) 
VALUES (1, 'XXXXX-XXXXX-XXXXX-XXXXX-XXXXX');
```

7. Запустите бота:
```bash
python main.py
```

## 📋 Команды пользователя
- `/start` - Главное меню
- `/orders` - История покупок
- Поддержка через кнопку "🆘 Поддержка"

## ⚙️ Администрирование
1. Добавляйте ключи в БД:
```sql
INSERT INTO keys (product_id, key) VALUES (product_id, 'ключ');
```
2. Просмотр статистики:
```sql
SELECT * FROM orders;
SELECT p.name, COUNT(o.id) FROM products p LEFT JOIN orders o ON p.id = o.product_id GROUP BY p.name;
```

## 📚 Технологии
- Python 3.10+
- Aiogram 3.x
- SQLite3
- Telegram Payments API
```

---

### Дополнительные скрипты

**init_db.py** - Инициализация БД с тестовыми данными:
```python
import sqlite3

conn = sqlite3.connect('keys.db')
cursor = conn.cursor()

# Создание таблиц (аналогично основному файлу)

# Добавление тестовых продуктов
products = [
    (1, 'Windows 10 Home', 'Лицензионный ключ для Windows 10 Home', 699, 'windows'),
    (2, 'Windows 11 Pro', 'Лицензионный ключ для Windows 11 Professional', 1299, 'windows'),
    (3, 'Office 2021 Home', 'Ключ для Microsoft Office 2021 Home & Student', 2999, 'office'),
    (4, 'Office 365 Personal', 'Подписка на 1 год для 1 пользователя', 1999, 'office')
]

cursor.executemany(
    "INSERT INTO products (id, name, description, price, category) VALUES (?, ?, ?, ?, ?)",
    products
)

# Добавление тестовых ключей
keys = [
    (1, 'W10H-XXXXX-XXXXX-XXXXX-XXXXX'),
    (1, 'W10H-YYYYY-YYYYY-YYYYY-YYYYY'),
    (2, 'W11P-ABCDE-ABCDE-ABCDE-ABCDE'),
    (3, 'OFF21-HS-XXXXX-XXXXX-XXXXX'),
    (4, 'O365-PERS-1YEAR-XXXXX')
]

cursor.executemany(
    "INSERT INTO keys (product_id, key) VALUES (?, ?)",
    keys
)

conn.commit()
conn.close()
print("База данных успешно инициализирована!")
```

---

### Важные замечания
  Для работы платежей:
   - Бот должен иметь username
   - Ваш аккаунт должен быть привязан к платежной системе в Telegram
   - Страна продажи должна поддерживать Telegram Payments
