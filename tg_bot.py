import telebot
from telebot import types
import sqlite3
import pandas as pd
import logging
import os
import traceback
from typing import Dict, List

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Токен бота
TOKEN = '8741110152:AAHB05JKFv3hVE4zs--Wd4LzSIWFFe3BT_g'
bot = telebot.TeleBot(TOKEN)

# ID поддержки
SUPPORT_USERNAME = "@ChebuStore_support"  
SUPPORT_CHAT_ID = "123456789"

# Константы для кнопок
BUTTONS = {
    'catalog': '📱 Каталог',
    'about': 'ℹ️ О нас',
    'support': '📞 Оформить заказ',
    'back': '🔙 Назад',
    'main_menu': '🏠 Главное меню',
    'refresh': '🔄 Обновить каталог'
}

# Глобальная переменная для хранения каталога
PRODUCTS = {}

def debug_file_location():
    """Показывает информацию о местоположении файла"""
    current_dir = os.getcwd()
    print("\n" + "="*50)
    print("🔍 ОТЛАДКА ФАЙЛОВОЙ СИСТЕМЫ")
    print("="*50)
    print(f"📁 Текущая рабочая директория: {current_dir}")
    
    excel_files = [f for f in os.listdir(current_dir) if f.endswith('.xlsx')]
    print(f"📁 Найденные Excel файлы: {excel_files}")
    
    if os.path.exists('products.xlsx'):
        print("✅ Файл products.xlsx найден")
        file_size = os.path.getsize('products.xlsx')
        print(f"📊 Размер файла: {file_size} байт")
    else:
        print("❌ Файл products.xlsx НЕ найден")
    print("="*50 + "\n")

def reorganize_smartphones_by_brand(products):
    """Разделяет только смартфоны на бренды, остальные категории оставляет как есть"""
    reorganized = {}
    
    for cat_id, category in products.items():
        category_lower = cat_id.lower()
        
        # Только для категории смартфонов делаем разделение
        if 'смартфон' in category_lower or cat_id == 'smartphones' or 'phone' in category_lower:
            apple_phones = []
            samsung_phones = []
            other_phones = []
            
            for item in category['items']:
                name_lower = item['name'].lower()
                if 'iphone' in name_lower or 'apple' in name_lower:
                    apple_phones.append(item)
                elif 'samsung' in name_lower or 'galaxy' in name_lower:
                    samsung_phones.append(item)
                else:
                    other_phones.append(item)
            
            # Создаем структуру с подкатегориями для смартфонов
            reorganized[cat_id] = {
                'name': category['name'],
                'type': 'parent',
                'subcategories': []
            }
            
            if apple_phones:
                reorganized[cat_id]['subcategories'].append({
                    'id': f"{cat_id}_apple",
                    'name': "🍎 Apple iPhone",
                    'items': apple_phones
                })
            
            if samsung_phones:
                reorganized[cat_id]['subcategories'].append({
                    'id': f"{cat_id}_samsung",
                    'name': "📱 Samsung Galaxy",
                    'items': samsung_phones
                })
            
            if other_phones:
                reorganized[cat_id]['subcategories'].append({
                    'id': f"{cat_id}_other",
                    'name': "📱 Другие смартфоны",
                    'items': other_phones
                })
        
        # Для всех остальных категорий - оставляем как есть
        else:
            reorganized[cat_id] = {
                'name': category['name'],
                'type': 'simple',
                'items': category['items']
            }
    
    return reorganized

def load_products_from_excel(file_path='products.xlsx'):
    """
    Загружает товары из Excel файла
    """
    try:
        if not os.path.exists(file_path):
            logger.error(f"Файл {file_path} не найден!")
            print(f"❌ Файл {file_path} не найден! Создаю пример...")
            create_sample_excel(file_path)
            return load_products_from_excel(file_path)
        
        print(f"📖 Чтение файла: {file_path}")
        df = pd.read_excel(file_path)
        
        print(f"📊 Найдено строк в Excel: {len(df)}")
        
        if len(df) == 0:
            print("❌ Excel файл пуст!")
            return {}
        
        # Проверяем наличие необходимых колонок
        required_columns = ['category_id', 'category_name', 'product_id', 'product_name', 'price', 'description', 'available']
        for col in required_columns:
            if col not in df.columns:
                print(f"❌ В файле отсутствует колонка: {col}")
                return {}
        
        # Преобразуем в нужную структуру
        products = {}
        
        for category_id in df['category_id'].unique():
            category_data = df[df['category_id'] == category_id]
            category_name = category_data['category_name'].iloc[0]
            
            # Добавляем эмодзи в зависимости от названия категории
            category_lower = str(category_name).lower()
            
            if 'смартфон' in category_lower or 'iphone' in category_lower:
                display_name = f"📱 {category_name}"
            elif 'ноут' in category_lower or 'macbook' in category_lower:
                display_name = f"💻 {category_name}"
            elif 'наушники' in category_lower or 'pods' in category_lower:
                display_name = f"🎧 {category_name}"
            elif 'планшет' in category_lower or 'ipad' in category_lower:
                display_name = f"📱 {category_name}"
            elif 'часы' in category_lower or 'watch' in category_lower:
                display_name = f"⌚ {category_name}"
            elif 'игровые консоли' in category_lower or 'playstation' in category_lower:
                display_name = f"🎮 {category_name}"
            elif 'дайсон' in category_lower or 'dyson' in category_lower:
                display_name = f"🌀 {category_name}"
            else:
                display_name = f"📦 {category_name}"
            
            items = []
            for _, row in category_data.iterrows():
                price = row['price']
                if pd.isna(price):
                    price = 0
                
                available = row['available']
                if pd.isna(available):
                    available = True
                
                item = {
                    'id': int(row['product_id']),
                    'name': str(row['product_name']),
                    'price': int(float(price)),
                    'description': str(row['description']) if pd.notna(row['description']) else 'Нет описания',
                    'available': bool(available)
                }
                items.append(item)
            
            products[category_id] = {
                'name': display_name,
                'items': items
            }
            
            print(f"✅ Загружена категория: {display_name} ({len(items)} товаров)")
        
        # Разделяем только смартфоны на бренды
        products = reorganize_smartphones_by_brand(products)
        
        print(f"✅ Всего загружено {len(products)} категорий")
        return products
        
    except Exception as e:
        logger.error(f"Ошибка при загрузке из Excel: {e}")
        print(f"❌ Детали ошибки: {str(e)}")
        traceback.print_exc()
        return {}

def create_sample_excel(file_path='products.xlsx'):
    """
    Создает пример Excel файла с товарами
    """
    sample_data = {
        'category_id': ['smartphones', 'smartphones', 'smartphones', 'laptops', 'laptops', 'accessories'],
        'category_name': ['Смартфоны', 'Смартфоны', 'Смартфоны', 'Ноутбуки', 'Ноутбуки', 'Аксессуары'],
        'product_id': [1, 2, 3, 4, 5, 6],
        'product_name': ['iPhone 15', 'Samsung S24', 'Xiaomi 14', 'MacBook Air M2', 'Lenovo ThinkPad', 'AirPods Pro'],
        'price': [79990, 69990, 49990, 119990, 89990, 24990],
        'description': ['128GB, черный', '256GB, зеленый', '256GB, синий', '13" 256GB', '14" 512GB', '2-го поколения'],
        'available': [True, True, False, True, True, True]
    }
    
    df = pd.DataFrame(sample_data)
    df.to_excel(file_path, index=False)
    logger.info(f"Создан пример файла {file_path}")
    print(f"📁 Создан файл {file_path} с примером товаров")
    print(f"📊 Всего добавлено {len(df)} товаров")

def save_products_to_excel(products: Dict, file_path='products.xlsx'):
    """
    Сохраняет каталог обратно в Excel
    """
    try:
        rows = []
        for cat_id, category in products.items():
            # Для категорий с подкатегориями
            if 'subcategories' in category:
                for subcat in category['subcategories']:
                    for item in subcat['items']:
                        clean_name = category['name'].split(' ', 1)[-1] if ' ' in category['name'] else category['name']
                        rows.append({
                            'category_id': cat_id,
                            'category_name': clean_name,
                            'product_id': item['id'],
                            'product_name': item['name'],
                            'price': item['price'],
                            'description': item['description'],
                            'available': item['available']
                        })
            # Для простых категорий
            else:
                for item in category['items']:
                    clean_name = category['name'].split(' ', 1)[-1] if ' ' in category['name'] else category['name']
                    rows.append({
                        'category_id': cat_id,
                        'category_name': clean_name,
                        'product_id': item['id'],
                        'product_name': item['name'],
                        'price': item['price'],
                        'description': item['description'],
                        'available': item['available']
                    })
        
        df = pd.DataFrame(rows)
        df.to_excel(file_path, index=False)
        logger.info(f"Каталог сохранен в {file_path}")
        print(f"💾 Каталог сохранен в {file_path}")
        
    except Exception as e:
        logger.error(f"Ошибка сохранения в Excel: {e}")
        print(f"❌ Ошибка сохранения: {e}")

# Функция для создания базы данных
def init_database():
    """Инициализация базы данных"""
    try:
        conn = sqlite3.connect('chebustore.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                registration_date DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS orders (
                order_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                product_id INTEGER,
                order_date DATETIME DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'new',
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        ''')
        
        conn.commit()
        conn.close()
        logger.info("Database initialized successfully")
        print("✅ База данных инициализирована")
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        print(f"❌ Ошибка инициализации БД: {e}")

def save_user(message):
    """Сохраняем информацию о пользователе"""
    try:
        conn = sqlite3.connect('chebustore.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR IGNORE INTO users (user_id, username, first_name, last_name)
            VALUES (?, ?, ?, ?)
        ''', (
            message.from_user.id,
            message.from_user.username,
            message.from_user.first_name,
            message.from_user.last_name
        ))
        
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"Error saving user: {e}")

def main_menu_keyboard():
    """Создает клавиатуру главного меню"""
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    buttons = [
        types.KeyboardButton(BUTTONS['catalog']),
        types.KeyboardButton(BUTTONS['about']),
        types.KeyboardButton(BUTTONS['support'])
    ]
    keyboard.add(*buttons)
    return keyboard

def catalog_keyboard():
    """Создает клавиатуру категорий товаров"""
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    
    for category_id, category in PRODUCTS.items():
        # Если есть подкатегории (только для смартфонов)
        if 'subcategories' in category:
            keyboard.add(
                types.InlineKeyboardButton(
                    category['name'], 
                    callback_data=f"parent_{category_id}"
                )
            )
        else:
            keyboard.add(
                types.InlineKeyboardButton(
                    category['name'], 
                    callback_data=f"category_{category_id}"
                )
            )
    
    keyboard.add(
        types.InlineKeyboardButton(
            BUTTONS['main_menu'], 
            callback_data="main_menu"
        )
    )
    
    return keyboard

@bot.message_handler(commands=['start'])
def start_command(message):
    save_user(message)
    
    welcome_text = (
        f"👋 Привет, {message.from_user.first_name}!\n\n"
        "Добро пожаловать в ChebuStore - ваш магазин техники!\n\n"
        "🛍️ Здесь вы можете:\n"
        "• Посмотреть наш каталог товаров\n"
        "• Узнать информацию о магазине\n"
        "• Связаться с поддержкой\n\n"
        "Выберите интересующий вас раздел:"
    )
    
    bot.send_message(
        message.chat.id, 
        welcome_text, 
        reply_markup=main_menu_keyboard()
    )

@bot.message_handler(func=lambda message: True)
def handle_text(message):
    if message.text == BUTTONS['catalog']:
        show_catalog(message.chat.id)
        
    elif message.text == BUTTONS['about']:
        show_about(message.chat.id)
        
    elif message.text == BUTTONS['support']:
        show_support(message.chat.id)
        
    elif message.text == BUTTONS['back']:
        bot.send_message(
            message.chat.id,
            "Главное меню:",
            reply_markup=main_menu_keyboard()
        )
        
    else:
        bot.send_message(
            message.chat.id,
            "Я не понимаю эту команду. Пожалуйста, воспользуйтесь меню.",
            reply_markup=main_menu_keyboard()
        )

def show_catalog(chat_id):
    if not PRODUCTS:
        text = "📱 Каталог временно пуст. Пожалуйста, попробуйте позже."
        bot.send_message(chat_id, text, reply_markup=main_menu_keyboard())
        return
    
    text = "📱 Наш каталог:\n\nВыберите категорию:"
    bot.send_message(chat_id, text, reply_markup=catalog_keyboard())

def show_about(chat_id):
    about_text = (
        "ℹ️ О магазине ChebuStore\n\n"
        "🏪 Мы - современный магазин техники, в приоритете у которого - доступность продуктов\n\n"
        "🚀 Почему выбирают нас:\n"
        "✔️ Устройства новые и запечатанные\n"
        "✔️ Цена ниже розничной\n"
        "✔️ на всех этапах сделки\n"
        "✔️ Отправка по РФ / возможна личная встреча\n"
        "✔️ Проверенные поставщики\n\n"
        "Цена может меняться - обращайтесь в поддержку\n"
        "По вопросам цвета техники, а также техники, которой нет в каталоге - обращайтесь в поддержку\n"
    )
    
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(types.KeyboardButton(BUTTONS['back']))
    
    bot.send_message(chat_id, about_text, reply_markup=keyboard)

def show_support(chat_id):
    support_text = (
        "📞 Оформление заказа в ChebuStore\n\n"
        "Если у вас возникли вопросы:\n\n"
        f"👤 Напишите нам: {SUPPORT_USERNAME}\n"
        "⏱️ Время работы:\n"
        "Ежедневно с: 10:00 - 20:00\n\n"
        "👉 Нажмите на username выше, чтобы написать сообщение!"
    )
    
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(types.KeyboardButton(BUTTONS['back']))
    
    bot.send_message(chat_id, support_text, reply_markup=keyboard)

@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    if call.data == "main_menu":
        bot.delete_message(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id
        )
        bot.send_message(
            call.message.chat.id,
            "Главное меню:",
            reply_markup=main_menu_keyboard()
        )
        
    elif call.data.startswith("parent_"):
        category_id = call.data.replace("parent_", "")
        show_subcategories(call.message.chat.id, category_id, call.message.message_id)
        
    elif call.data.startswith("subcategory_"):
        parts = call.data.replace("subcategory_", "").split('_', 1)
        category_id = parts[0]
        subcat_id = parts[1]
        show_subcategory_products(call.message.chat.id, category_id, subcat_id, call.message.message_id)
        
    elif call.data.startswith("category_"):
        category_id = call.data.replace("category_", "")
        show_category_products(call.message.chat.id, category_id, call.message.message_id)
        
    elif call.data == "back_to_catalog":
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text="📱 Наш каталог:\n\nВыберите категорию:",
            reply_markup=catalog_keyboard()
        )

def show_subcategories(chat_id, category_id, message_id):
    """Показывает подкатегории (бренды смартфонов)"""
    
    if category_id not in PRODUCTS:
        bot.send_message(chat_id, "Категория не найдена")
        return
    
    category = PRODUCTS[category_id]
    
    text = f"{category['name']}\n"
    text += "━" * 20 + "\n\n"
    text += "Выберите бренд:\n\n"
    
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    
    for subcat in category['subcategories']:
        count = len(subcat['items'])
        keyboard.add(
            types.InlineKeyboardButton(
                f"{subcat['name']} ({count} шт.)", 
                callback_data=f"subcategory_{category_id}_{subcat['id']}"
            )
        )
    
    keyboard.add(
        types.InlineKeyboardButton("🔙 К категориям", callback_data="back_to_catalog"),
        types.InlineKeyboardButton(BUTTONS['main_menu'], callback_data="main_menu")
    )
    
    bot.edit_message_text(
        chat_id=chat_id,
        message_id=message_id,
        text=text,
        reply_markup=keyboard
    )

def show_subcategory_products(chat_id, category_id, subcat_id, message_id):
    """Показывает товары выбранного бренда"""
    
    if category_id not in PRODUCTS:
        bot.send_message(chat_id, "Категория не найдена")
        return
    
    category = PRODUCTS[category_id]
    
    subcategory = None
    for subcat in category.get('subcategories', []):
        if subcat['id'] == subcat_id:
            subcategory = subcat
            break
    
    if not subcategory:
        bot.send_message(chat_id, "Подкатегория не найдена")
        return
    
    items = sorted(subcategory['items'], key=lambda x: x['price'])
    
    text = f"{category['name']} → {subcategory['name']}\n"
    text += "━" * 30 + "\n\n"
    
    for product in items:
        status = "✅ В АССОРТИМЕНТЕ" if product['available'] else "❌ БУДЕТ ПОЗЖЕ"
        price_str = f"{product['price']:,}".replace(',', ' ')
        
        text += f"✨ *{product['name']}*\n"
        text += f"   💰 *{price_str} ₽*\n"
        text += f"   📝 {product['description']}\n"
        text += f"   {status}\n\n"
    
    available_count = sum(1 for p in items if p['available'])
    text += f"📊 В наличии: {available_count} из {len(items)} товаров\n"
    
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(
        types.InlineKeyboardButton("🔙 К брендам", callback_data=f"parent_{category_id}"),
        types.InlineKeyboardButton("🔙 К категориям", callback_data="back_to_catalog"),
        types.InlineKeyboardButton(BUTTONS['main_menu'], callback_data="main_menu")
    )
    
    bot.edit_message_text(
        chat_id=chat_id,
        message_id=message_id,
        text=text,
        reply_markup=keyboard,
        parse_mode='Markdown'
    )

def show_category_products(chat_id, category_id, message_id):
    """Показывает товары обычной категории (без подкатегорий)"""
    
    if category_id not in PRODUCTS:
        bot.send_message(chat_id, "Категория не найдена")
        return
    
    category = PRODUCTS[category_id]
    
    items = sorted(category['items'], key=lambda x: x['price'])
    
    text = f"{category['name']}\n"
    text += "━" * 20 + "\n\n"
    
    for product in items:
        status = "✅ В АССОРТИМЕНТЕ" if product['available'] else "❌ БУДЕТ ПОЗЖЕ"
        price_str = f"{product['price']:,}".replace(',', ' ')
        
        text += f"✨ *{product['name']}*\n"
        text += f"   💰 *{price_str} ₽*\n"
        text += f"   📝 {product['description']}\n"
        text += f"   {status}\n\n"
    
    available_count = sum(1 for p in items if p['available'])
    text += f"📊 В наличии: {available_count} из {len(items)} товаров\n"
    
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(
        types.InlineKeyboardButton("🔙 К категориям", callback_data="back_to_catalog"),
        types.InlineKeyboardButton(BUTTONS['main_menu'], callback_data="main_menu")
    )
    
    bot.edit_message_text(
        chat_id=chat_id,
        message_id=message_id,
        text=text,
        reply_markup=keyboard,
        parse_mode='Markdown'
    )

@bot.message_handler(commands=['help'])
def help_command(message):
    help_text = (
        "🆘 Помощь по боту ChebuStore\n\n"
        "Доступные команды:\n"
        "/start - Начать работу с ботом\n"
        "/help - Показать это сообщение\n"
        "/catalog - Перейти в каталог\n"
        "/about - Информация о магазине\n"
        "/support - Связаться с поддержкой\n"
        "/refresh - Обновить каталог из Excel (только для админа)\n"
        "/download - Скачать текущий каталог в Excel\n\n"
        "Если у вас возникли проблемы, напишите в поддержку."
    )
    bot.reply_to(message, help_text)

@bot.message_handler(commands=['catalog'])
def catalog_command(message):
    show_catalog(message.chat.id)

@bot.message_handler(commands=['about'])
def about_command(message):
    show_about(message.chat.id)

@bot.message_handler(commands=['support'])
def support_command(message):
    show_support(message.chat.id)

@bot.message_handler(commands=['refresh'])
def refresh_catalog(message):
    global PRODUCTS
    
    ADMIN_ID = 123456789  # 👈 ВСТАВЬ СВОЙ TELEGRAM ID!
    
    if message.from_user.id != ADMIN_ID:
        bot.reply_to(message, "❌ У вас нет прав для этой команды")
        return
    
    msg = bot.reply_to(message, "🔄 Обновляю каталог...")
    
    new_products = load_products_from_excel()
    if new_products:
        PRODUCTS = new_products
        bot.edit_message_text(
            "✅ Каталог успешно обновлен!",
            chat_id=message.chat.id,
            message_id=msg.message_id
        )
        categories_count = len(PRODUCTS)
        products_count = 0
        for cat in PRODUCTS.values():
            if 'items' in cat:
                products_count += len(cat['items'])
            else:
                for subcat in cat.get('subcategories', []):
                    products_count += len(subcat['items'])
        
        bot.send_message(
            message.chat.id,
            f"📊 Загружено: {categories_count} категорий, {products_count} товаров"
        )
    else:
        bot.edit_message_text(
            "❌ Ошибка при обновлении каталога. Проверьте файл products.xlsx",
            chat_id=message.chat.id,
            message_id=msg.message_id
        )

@bot.message_handler(commands=['download'])
def download_catalog(message):
    try:
        if os.path.exists('products.xlsx'):
            with open('products.xlsx', 'rb') as f:
                bot.send_document(
                    message.chat.id, 
                    f,
                    caption="📊 Текущий каталог товаров ChebuStore"
                )
        else:
            bot.reply_to(message, "❌ Файл каталога не найден. Создаю новый...")
            create_sample_excel()
            with open('products.xlsx', 'rb') as f:
                bot.send_document(
                    message.chat.id, 
                    f,
                    caption="📊 Пример каталога товаров"
                )
    except Exception as e:
        bot.reply_to(message, f"❌ Ошибка: {e}")

# Запуск бота
if __name__ == '__main__':
    print("\n" + "🚀" * 10 + " ЗАПУСК БОТА ChebuStore " + "🚀" * 10)
    
    debug_file_location()
    init_database()
    
    print("\n📦 Загрузка каталога...")
    PRODUCTS = load_products_from_excel()
    
    if PRODUCTS:
        categories_count = len(PRODUCTS)
        products_count = 0
        for cat in PRODUCTS.values():
            if 'items' in cat:
                products_count += len(cat['items'])
            else:
                for subcat in cat.get('subcategories', []):
                    products_count += len(subcat['items'])
        
        print(f"\n✅ УСПЕШНО ЗАГРУЖЕНО:")
        print(f"   📁 Категорий: {categories_count}")
        print(f"   📦 Товаров: {products_count}")
    else:
        print("\n⚠️ КАТАЛОГ ПУСТ!")
    
    logger.info("Bot is starting...")
    print("\n" + "="*50)
    print("🤖 БОТ ChebuStore ЗАПУЩЕН И ГОТОВ К РАБОТЕ!")
    print("="*50)
    print(f"👤 Оформить сюда: {SUPPORT_USERNAME}")
    print(f"📊 Статус каталога: {'✅ Загружен' if PRODUCTS else '❌ Пуст'}")
    print("\n❌ Нажми Ctrl+C для остановки")
    print("="*50 + "\n")
    
    try:
        bot.infinity_polling()
    except KeyboardInterrupt:
        print("\n👋 Бот остановлен пользователем")
        if PRODUCTS:
            save_products_to_excel(PRODUCTS)
            print("💾 Каталог сохранен")
    except Exception as e:
        logger.error(f"Bot error: {e}")
        print(f"\n❌ Критическая ошибка: {e}")
        traceback.print_exc()