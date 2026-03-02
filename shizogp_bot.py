#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🔥 SHIZOGP - АБСОЛЮТНО ПОЛНЫЙ ТЕЛЕГРАМ БОТ
Версия: 3.0 (РАЗЪЕБАЛОВО-ФИНАЛ)
Разработчик: GhostiPeeK
Лицензия: Да пофиг, главное что работает!
"""

import os
import sys
import json
import asyncio
import logging
import sqlite3
import aiosqlite
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any
from contextlib import asynccontextmanager

# Настройка путей
import pathlib
path = pathlib.Path(__file__).parent.absolute()
os.chdir(path)

# ========== УСТАНОВКА ЗАВИСИМОСТЕЙ (АВТОМАТИЧЕСКАЯ) ==========
try:
    from aiogram import Bot, Dispatcher, types, F
    from aiogram.filters import Command
    from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
    from aiogram.fsm.context import FSMContext
    from aiogram.fsm.state import State, StatesGroup
    from aiogram.fsm.storage.memory import MemoryStorage
    from aiogram.exceptions import TelegramBadRequest
except ImportError:
    print("🔄 Устанавливаю aiogram...")
    os.system("pip install aiogram==3.4.1")
    from aiogram import Bot, Dispatcher, types, F
    from aiogram.filters import Command
    from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
    from aiogram.fsm.context import FSMContext
    from aiogram.fsm.state import State, StatesGroup
    from aiogram.fsm.storage.memory import MemoryStorage
    from aiogram.exceptions import TelegramBadRequest

try:
    import aiosqlite
except ImportError:
    print("🔄 Устанавливаю aiosqlite...")
    os.system("pip install aiosqlite==0.19.0")
    import aiosqlite

try:
    from dotenv import load_dotenv
except ImportError:
    print("🔄 Устанавливаю python-dotenv...")
    os.system("pip install python-dotenv==1.0.0")
    from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

# ========== НАСТРОЙКИ (МЕНЯЙ ПОД СЕБЯ) ==========
BOT_TOKEN = os.getenv('BOT_TOKEN', '8498694285:AAG3Ezx7BDGciUIYAAb4UHMtFUmBYvock3w')
ADMIN_IDS = [int(x) for x in os.getenv('ADMIN_IDS', '2091630272').split(',') if x]
VIP_CHAT_LINK = os.getenv('VIP_CHAT_LINK', 'https://t.me/+r3rxYlBjbTYyMDY6')
SUPPORT_LINK = os.getenv('SUPPORT_LINK', 'https://t.me/SHIZOGP_support')
CHANNEL_LINK = os.getenv('CHANNEL_LINK', 'https://t.me/SHIZOGP_channel')

# Настройки бота
VIP_PRICE = 550  # Цена VIP в монетах
VIP_DURATION = 30  # Дней VIP
REFERRAL_BONUS = 50  # Бонус за реферала
START_BALANCE = 100  # Стартовый баланс
DATABASE_PATH = "shizogp.db"  # Имя файла базы данных
BOT_VERSION = "3.0 (РАЗЪЕБАЛОВО-ФИНАЛ)"
BOT_NAME = "SHIZOGP"

# ========== НАСТРОЙКА ЛОГИРОВАНИЯ ==========
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("bot.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ========== ЦВЕТА ДЛЯ ТЕРМИНАЛА ==========
class Colors:
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    END = '\033[0m'

# ========== БАЗА ДАННЫХ ==========
class Database:
    def __init__(self, db_path: str = DATABASE_PATH):
        self.db_path = db_path
    
    async def init_db(self):
        """Инициализация базы данных"""
        async with aiosqlite.connect(self.db_path) as db:
            # Пользователи
            await db.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    full_name TEXT,
                    balance INTEGER DEFAULT 100,
                    vip_status INTEGER DEFAULT 0,
                    vip_until TEXT,
                    referrer_id INTEGER,
                    referral_count INTEGER DEFAULT 0,
                    registration_date TEXT DEFAULT CURRENT_TIMESTAMP,
                    last_visit TEXT DEFAULT CURRENT_TIMESTAMP,
                    is_admin INTEGER DEFAULT 0,
                    is_banned INTEGER DEFAULT 0,
                    language TEXT DEFAULT 'ru'
                )
            ''')
            
            # Транзакции
            await db.execute('''
                CREATE TABLE IF NOT EXISTS transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    amount INTEGER,
                    type TEXT,
                    description TEXT,
                    date TEXT DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Скины
            await db.execute('''
                CREATE TABLE IF NOT EXISTS skins (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT,
                    quality TEXT,
                    price INTEGER,
                    image_url TEXT,
                    seller_id INTEGER,
                    status TEXT DEFAULT 'available',
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    sold_at TEXT
                )
            ''')
            
            # Сделки
            await db.execute('''
                CREATE TABLE IF NOT EXISTS deals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    skin_id INTEGER,
                    buyer_id INTEGER,
                    seller_id INTEGER,
                    price INTEGER,
                    status TEXT DEFAULT 'pending',
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    completed_at TEXT
                )
            ''')
            
            # Рефералы
            await db.execute('''
                CREATE TABLE IF NOT EXISTS referrals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    referrer_id INTEGER,
                    date TEXT DEFAULT CURRENT_TIMESTAMP,
                    bonus_paid INTEGER DEFAULT 1
                )
            ''')
            
            await db.commit()
        
        logger.info(f"{Colors.GREEN}✅ База данных инициализирована{Colors.END}")
    
    async def get_user(self, user_id: int) -> Optional[Dict]:
        """Получить пользователя"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
            user = await cursor.fetchone()
            return dict(user) if user else None
    
    async def create_user(self, user_id: int, username: str, full_name: str, referrer_id: int = None) -> bool:
        """Создать пользователя"""
        async with aiosqlite.connect(self.db_path) as db:
            # Проверяем существование
            cursor = await db.execute('SELECT user_id FROM users WHERE user_id = ?', (user_id,))
            if await cursor.fetchone():
                return False
            
            # Создаём
            await db.execute('''
                INSERT INTO users (user_id, username, full_name, balance, referrer_id)
                VALUES (?, ?, ?, ?, ?)
            ''', (user_id, username, full_name, START_BALANCE, referrer_id))
            
            # Если есть реферер, начисляем бонус
            if referrer_id:
                await db.execute('''
                    UPDATE users SET balance = balance + ?, referral_count = referral_count + 1
                    WHERE user_id = ?
                ''', (REFERRAL_BONUS, referrer_id))
                
                await db.execute('''
                    INSERT INTO referrals (user_id, referrer_id)
                    VALUES (?, ?)
                ''', (user_id, referrer_id))
                
                await db.execute('''
                    INSERT INTO transactions (user_id, amount, type, description)
                    VALUES (?, ?, ?, ?)
                ''', (referrer_id, REFERRAL_BONUS, 'referral', f'Бонус за реферала {user_id}'))
            
            await db.commit()
            return True
    
    async def update_balance(self, user_id: int, amount: int, description: str = '') -> bool:
        """Изменить баланс"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('''
                UPDATE users SET balance = balance + ? WHERE user_id = ?
            ''', (amount, user_id))
            
            if description:
                await db.execute('''
                    INSERT INTO transactions (user_id, amount, type, description)
                    VALUES (?, ?, ?, ?)
                ''', (user_id, amount, 'balance_change', description))
            
            await db.commit()
            return True
    
    async def activate_vip(self, user_id: int, days: int = VIP_DURATION) -> bool:
        """Активировать VIP"""
        vip_until = (datetime.now() + timedelta(days=days)).strftime('%Y-%m-%d %H:%M:%S')
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('''
                UPDATE users SET vip_status = 1, vip_until = ? WHERE user_id = ?
            ''', (vip_until, user_id))
            await db.commit()
            return True
    
    async def check_vip(self, user_id: int) -> bool:
        """Проверить VIP"""
        user = await self.get_user(user_id)
        if not user or not user['vip_status']:
            return False
        
        if user['vip_until']:
            vip_date = datetime.strptime(user['vip_until'], '%Y-%m-%d %H:%M:%S')
            if vip_date < datetime.now():
                async with aiosqlite.connect(self.db_path) as db:
                    await db.execute('UPDATE users SET vip_status = 0 WHERE user_id = ?', (user_id,))
                    await db.commit()
                return False
        return True
    
    async def get_stats(self) -> Dict:
        """Получить статистику"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute('SELECT COUNT(*) FROM users')
            users = (await cursor.fetchone())[0]
            
            cursor = await db.execute('SELECT COUNT(*) FROM users WHERE vip_status = 1')
            vip = (await cursor.fetchone())[0]
            
            cursor = await db.execute('SELECT COUNT(*) FROM deals WHERE status = "completed"')
            deals = (await cursor.fetchone())[0]
            
            cursor = await db.execute('SELECT SUM(balance) FROM users')
            total_balance = (await cursor.fetchone())[0] or 0
            
            return {
                'users': users,
                'vip': vip,
                'deals': deals,
                'total_balance': total_balance
            }

# ========== СОЗДАЁМ ЭКЗЕМПЛЯР БД ==========
db = Database()

# ========== КЛАВИАТУРЫ ==========
class Keyboards:
    @staticmethod
    def main(user_id: int = None) -> InlineKeyboardMarkup:
        """Главное меню"""
        buttons = [
            [InlineKeyboardButton(text="🛒 МАГАЗИН", callback_data="shop")],
            [
                InlineKeyboardButton(text="💰 БАЛАНС", callback_data="balance"),
                InlineKeyboardButton(text="🤝 РЕФЕРАЛЫ", callback_data="referral")
            ],
            [
                InlineKeyboardButton(text="👑 VIP", callback_data="vip"),
                InlineKeyboardButton(text="📊 ПРОФИЛЬ", callback_data="profile")
            ],
            [
                InlineKeyboardButton(text="ℹ️ ПОМОЩЬ", callback_data="help"),
                InlineKeyboardButton(text="📢 КАНАЛ", url=CHANNEL_LINK)
            ]
        ]
        return InlineKeyboardMarkup(inline_keyboard=buttons)
    
    @staticmethod
    def back() -> InlineKeyboardMarkup:
        """Кнопка назад"""
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀ НАЗАД В МЕНЮ", callback_data="main_menu")]
        ])
    
    @staticmethod
    def vip(is_vip: bool = False) -> InlineKeyboardMarkup:
        """VIP меню"""
        if is_vip:
            return InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="👑 ВОЙТИ В VIP ЧАТ", url=VIP_CHAT_LINK)],
                [InlineKeyboardButton(text="◀ НАЗАД", callback_data="main_menu")]
            ])
        else:
            return InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=f"💎 КУПИТЬ VIP ({VIP_PRICE}💰)", callback_data="buy_vip")],
                [InlineKeyboardButton(text="◀ НАЗАД", callback_data="main_menu")]
            ])
    
    @staticmethod
    def admin() -> InlineKeyboardMarkup:
        """Админ меню"""
        buttons = [
            [InlineKeyboardButton(text="📊 СТАТИСТИКА", callback_data="admin_stats")],
            [InlineKeyboardButton(text="👥 ПОЛЬЗОВАТЕЛИ", callback_data="admin_users")],
            [InlineKeyboardButton(text="💰 ПОПОЛНИТЬ БАЛАНС", callback_data="admin_add_balance")],
            [InlineKeyboardButton(text="👑 ВЫДАТЬ VIP", callback_data="admin_give_vip")],
            [InlineKeyboardButton(text="🔧 УПРАВЛЕНИЕ", callback_data="admin_manage")],
            [InlineKeyboardButton(text="◀ НАЗАД", callback_data="main_menu")]
        ]
        return InlineKeyboardMarkup(inline_keyboard=buttons)

# ========== СОСТОЯНИЯ FSM ==========
class States(StatesGroup):
    # Админские состояния
    admin_add_balance_user = State()
    admin_add_balance_amount = State()
    admin_give_vip_user = State()
    
    # Пользовательские состояния
    sell_skin_name = State()
    sell_skin_quality = State()
    sell_skin_price = State()
    sell_skin_image = State()
    
    # Поддержка
    support_message = State()

# ========== ИНИЦИАЛИЗАЦИЯ БОТА ==========
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# ========== ХЕНДЛЕРЫ КОМАНД ==========
@dp.message(Command("start"))
async def cmd_start(message: Message):
    """Обработчик команды /start"""
    user_id = message.from_user.id
    username = message.from_user.username or "NoName"
    full_name = message.from_user.full_name or "NoName"
    
    # Парсим реферальный код
    args = message.text.split()
    referrer_id = None
    if len(args) > 1 and args[1].startswith("ref_"):
        try:
            referrer_id = int(args[1].replace("ref_", ""))
            if referrer_id == user_id:
                referrer_id = None
        except:
            pass
    
    # Создаём пользователя
    await db.create_user(user_id, username, full_name, referrer_id)
    
    # Получаем инфо
    user = await db.get_user(user_id)
    is_vip = await db.check_vip(user_id)
    
    # Красивое приветствие
    welcome_text = f"""
🎮 **ДОБРО ПОЖАЛОВАТЬ В SHIZOGP!** 🎮

👤 **Информация о тебе:**
├ 🆔 ID: `{user_id}`
├ 💰 Баланс: **{user['balance']}** монет
├ 👥 Рефералов: **{user['referral_count']}**
└ 👑 VIP статус: {"✅" if is_vip else "❌"}

🔥 **Что умеет бот:**
├ 🛒 Покупать и продавать скины CS2
├ 💎 Зарабатывать на рефералах
├ 👑 Получать VIP статус
└ 📊 Следить за статистикой

⚡ **Выбери действие в меню ниже!**
    """
    
    await message.answer(
        welcome_text,
        reply_markup=Keyboards.main(),
        parse_mode="Markdown"
    )

@dp.message(Command("menu"))
async def cmd_menu(message: Message):
    """Команда для открытия меню"""
    await message.answer(
        "📋 **ГЛАВНОЕ МЕНЮ**\nВыбери действие:",
        reply_markup=Keyboards.main(),
        parse_mode="Markdown"
    )

@dp.message(Command("help"))
async def cmd_help(message: Message):
    """Команда помощи"""
    help_text = """
🆘 **ПОМОЩЬ ПО БОТУ SHIZOGP**

📌 **Основные команды:**
├ /start - Запустить бота
├ /menu - Открыть меню
├ /help - Показать помощь
├ /profile - Мой профиль
└ /balance - Мой баланс

🎮 **Разделы меню:**
├ 🛒 **Магазин** - покупка скинов
├ 💰 **Баланс** - проверка средств
├ 🤝 **Рефералы** - приглашай друзей
├ 👑 **VIP** - закрытый чат
├ 📊 **Профиль** - твои данные
└ ℹ️ **Помощь** - эта справка

💎 **Реферальная система:**
За каждого приглашённого друга ты получаешь **50 монет**!

👑 **VIP статус:**
├ Стоимость: **550 монет**
├ Длительность: **30 дней**
└ Доступ к закрытому VIP чату

❓ **Вопросы и поддержка:**
├ 📢 Канал: [Наш канал]({CHANNEL_LINK})
└ 📞 Поддержка: [Написать]({SUPPORT_LINK})

⚡ **Желаем удачных сделок!** ⚡
    """
    await message.answer(
        help_text,
        reply_markup=Keyboards.back(),
        parse_mode="Markdown",
        disable_web_page_preview=True
    )

@dp.message(Command("profile"))
async def cmd_profile(message: Message):
    """Команда профиля"""
    user_id = message.from_user.id
    user = await db.get_user(user_id)
    is_vip = await db.check_vip(user_id)
    
    if not user:
        await message.answer("❌ Пользователь не найден! Напиши /start")
        return
    
    profile_text = f"""
📊 **ТВОЙ ПРОФИЛЬ**

👤 **Личные данные:**
├ 🆔 ID: `{user_id}`
├ 👤 Имя: {user['full_name']}
├ 🏷 Username: @{user['username']}
└ 📅 Регистрация: {user['registration_date'][:10]}

💰 **Финансы:**
├ Баланс: **{user['balance']}** монет
├ Рефералов: **{user['referral_count']}** 👥
└ Заработано с рефералов: **{user['referral_count'] * REFERRAL_BONUS}** монет

👑 **VIP статус:**
├ Статус: {"✅ АКТИВЕН" if is_vip else "❌ НЕ АКТИВЕН"}
{"├ Действует до: " + user['vip_until'][:10] if is_vip and user['vip_until'] else ""}
└ Стоимость: {VIP_PRICE} монет

⚡ **Активность:**
├ Последний визит: {user['last_visit'][:16] if user['last_visit'] else "Неизвестно"}
└ Всего операций: {user['referral_count'] + 1}
    """
    
    await message.answer(
        profile_text,
        reply_markup=Keyboards.back(),
        parse_mode="Markdown"
    )

@dp.message(Command("balance"))
async def cmd_balance(message: Message):
    """Команда баланса"""
    user_id = message.from_user.id
    user = await db.get_user(user_id)
    
    if not user:
        await message.answer("❌ Пользователь не найден! Напиши /start")
        return
    
    balance_text = f"""
💰 **ТВОЙ БАЛАНС**

├ Текущий баланс: **{user['balance']}** монет
├ Рефералов: **{user['referral_count']}** 👥
└ До VIP: **{max(0, VIP_PRICE - user['balance'])}** монет

📊 **Способы пополнения:**
├ 🤝 Приглашай друзей (+{REFERRAL_BONUS} монет)
├ 🛒 Продавай скины
└ 💎 Покупай VIP

⚡ **Баланс можно потратить на:**
├ 👑 VIP статус ({VIP_PRICE} монет)
├ 🛒 Покупку скинов в магазине
└ 🎁 Специальные предложения
    """
    
    await message.answer(
        balance_text,
        reply_markup=Keyboards.back(),
        parse_mode="Markdown"
    )

# ========== ОБРАБОТЧИКИ КНОПОК ==========
@dp.callback_query(F.data == "main_menu")
async def callback_main_menu(callback: CallbackQuery):
    """Возврат в главное меню"""
    await callback.message.edit_text(
        "📋 **ГЛАВНОЕ МЕНЮ**\nВыбери действие:",
        reply_markup=Keyboards.main(),
        parse_mode="Markdown"
    )

@dp.callback_query(F.data == "balance")
async def callback_balance(callback: CallbackQuery):
    """Показать баланс"""
    user_id = callback.from_user.id
    user = await db.get_user(user_id)
    
    await callback.message.edit_text(
        f"💰 **ТВОЙ БАЛАНС**\n\n"
        f"Монет: **{user['balance']}** 💰\n"
        f"Рефералов: **{user['referral_count']}** 👥\n\n"
        f"До VIP: **{max(0, VIP_PRICE - user['balance'])}** монет",
        reply_markup=Keyboards.back(),
        parse_mode="Markdown"
    )

@dp.callback_query(F.data == "referral")
async def callback_referral(callback: CallbackQuery):
    """Реферальная система"""
    user_id = callback.from_user.id
    bot_info = await bot.get_me()
    ref_link = f"https://t.me/{bot_info.username}?start=ref_{user_id}"
    
    user = await db.get_user(user_id)
    
    text = f"""
🤝 **РЕФЕРАЛЬНАЯ ПРОГРАММА**

👥 **Твоя статистика:**
├ Рефералов: **{user['referral_count']}** 👥
├ Заработано: **{user['referral_count'] * REFERRAL_BONUS}** монет
└ Бонус за друга: **+{REFERRAL_BONUS}** монет

🔗 **Твоя ссылка:**
`{ref_link}`

📤 **Как зарабатывать:**
1. Отправь ссылку друзьям
2. Друг переходит по ссылке
3. Ты получаешь **+{REFERRAL_BONUS}** монет
4. Профит! 🚀

👑 **VIP бонус:**  
VIP пользователи получают **+{REFERRAL_BONUS * 2}** монет за реферала!
    """
    
    await callback.message.edit_text(
        text,
        reply_markup=Keyboards.back(),
        parse_mode="Markdown"
    )

@dp.callback_query(F.data == "vip")
async def callback_vip(callback: CallbackQuery):
    """VIP информация"""
    user_id = callback.from_user.id
    is_vip = await db.check_vip(user_id)
    user = await db.get_user(user_id)
    
    if is_vip:
        text = f"""
👑 **VIP СТАТУС АКТИВЕН**

✅ Ты имеешь доступ к закрытому VIP чату!
📅 Действует до: {user['vip_until'][:10]}

**Преимущества VIP:**
├ 🔥 Закрытый чат с трейдерами
├ 💰 Двойной бонус за рефералов
├ 🎁 Эксклюзивные предложения
├ ⚡ Приоритетная поддержка
└ 🚀 Ранний доступ к новым скинам

👇 **Нажми кнопку ниже чтобы войти в чат!**
        """
    else:
        text = f"""
👑 **VIP СТАТУС**

💰 **Стоимость:** {VIP_PRICE} монет
📅 **Длительность:** {VIP_DURATION} дней

🎁 **Что даёт VIP:**
├ 🔥 Доступ в закрытый VIP чат
├ 💰 Двойной бонус за рефералов
├ 🎁 Эксклюзивные предложения
├ ⚡ Приоритетная поддержка
├ 🚀 Ранний доступ к новым скинам
└ 👑 Статус и уважение

📊 **Твой баланс:** {user['balance']} монет
{"✅ **Можешь купить!**" if user['balance'] >= VIP_PRICE else f"❌ **Нужно ещё {VIP_PRICE - user['balance']} монет**"}
        """
    
    await callback.message.edit_text(
        text,
        reply_markup=Keyboards.vip(is_vip),
        parse_mode="Markdown"
    )

@dp.callback_query(F.data == "buy_vip")
async def callback_buy_vip(callback: CallbackQuery):
    """Покупка VIP"""
    user_id = callback.from_user.id
    user = await db.get_user(user_id)
    
    if user['balance'] >= VIP_PRICE:
        # Списываем монеты
        await db.update_balance(user_id, -VIP_PRICE, "Покупка VIP")
        await db.activate_vip(user_id)
        
        await callback.message.edit_text(
            f"✅ **VIP УСПЕШНО АКТИВИРОВАН!**\n\n"
            f"💰 Списанo: {VIP_PRICE} монет\n"
            f"📅 Действует: {VIP_DURATION} дней\n"
            f"👑 Остаток на балансе: {user['balance'] - VIP_PRICE} монет\n\n"
            f"👇 **Нажми кнопку чтобы войти в VIP чат!**",
            reply_markup=Keyboards.vip(True),
            parse_mode="Markdown"
        )
        
        # Уведомление админам
        for admin_id in ADMIN_IDS:
            try:
                await bot.send_message(
                    admin_id,
                    f"👑 Пользователь @{callback.from_user.username or user_id} купил VIP!"
                )
            except:
                pass
    else:
        need = VIP_PRICE - user['balance']
        await callback.message.edit_text(
            f"❌ **Недостаточно монет!**\n\n"
            f"Твой баланс: {user['balance']} монет\n"
            f"Нужно ещё: **{need}** монет\n\n"
            f"🤝 **Приглашай друзей и получай бонусы!**",
            reply_markup=Keyboards.back(),
            parse_mode="Markdown"
        )

@dp.callback_query(F.data == "profile")
async def callback_profile(callback: CallbackQuery):
    """Профиль пользователя"""
    user_id = callback.from_user.id
    user = await db.get_user(user_id)
    is_vip = await db.check_vip(user_id)
    
    text = f"""
📊 **ТВОЙ ПРОФИЛЬ**

👤 **Личные данные:**
├ 🆔 ID: `{user_id}`
├ 👤 Имя: {user['full_name']}
├ 🏷 Username: @{user['username']}
└ 📅 Регистрация: {user['registration_date'][:10]}

💰 **Финансы:**
├ Баланс: **{user['balance']}** монет
├ Рефералов: **{user['referral_count']}** 👥
└ Заработано: **{user['referral_count'] * REFERRAL_BONUS}** монет

👑 **VIP статус:**
├ Статус: {"✅ АКТИВЕН" if is_vip else "❌ НЕ АКТИВЕН"}
{"├ Действует до: " + user['vip_until'][:10] if is_vip and user['vip_until'] else ""}
└ Стоимость: {VIP_PRICE} монет
    """
    
    await callback.message.edit_text(
        text,
        reply_markup=Keyboards.back(),
        parse_mode="Markdown"
    )

@dp.callback_query(F.data == "help")
async def callback_help(callback: CallbackQuery):
    """Помощь"""
    await callback.message.edit_text(
        f"🆘 **ПОМОЩЬ ПО БОТУ {BOT_NAME}**\n\n"
        f"📌 **Основные команды:**\n"
        f"├ /start - Запустить бота\n"
        f"├ /menu - Открыть меню\n"
        f"├ /help - Показать помощь\n"
        f"├ /profile - Мой профиль\n"
        f"└ /balance - Мой баланс\n\n"
        f"🎮 **Разделы меню:**\n"
        f"├ 🛒 **Магазин** - покупка скинов\n"
        f"├ 💰 **Баланс** - проверка средств\n"
        f"├ 🤝 **Рефералы** - приглашай друзей\n"
        f"├ 👑 **VIP** - закрытый чат\n"
        f"├ 📊 **Профиль** - твои данные\n"
        f"└ ℹ️ **Помощь** - эта справка\n\n"
        f"💎 **Реферальная система:**\n"
        f"За каждого друга **+{REFERRAL_BONUS}** монет!\n\n"
        f"👑 **VIP статус:** {VIP_PRICE} монет / {VIP_DURATION} дней\n\n"
        f"📢 **Наш канал:** {CHANNEL_LINK}\n"
        f"📞 **Поддержка:** {SUPPORT_LINK}",
        reply_markup=Keyboards.back(),
        parse_mode="Markdown",
        disable_web_page_preview=True
    )

@dp.callback_query(F.data == "shop")
async def callback_shop(callback: CallbackQuery):
    """Магазин"""
    await callback.message.edit_text(
        "🛒 **МАГАЗИН СКИНОВ**\n\n"
        "⚡ В разработке...\n\n"
        "Скоро здесь появятся самые топовые скины CS2!\n\n"
        "🔥 **А пока:**\n"
        "├ 🤝 Зарабатывай на рефералах\n"
        "├ 👑 Копи на VIP статус\n"
        "└ ⏳ Жди обновлений",
        reply_markup=Keyboards.back(),
        parse_mode="Markdown"
    )

# ========== АДМИНСКИЕ КОМАНДЫ ==========
@dp.message(Command("admin"))
async def cmd_admin(message: Message):
    """Админ панель"""
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("⛔ У тебя нет прав администратора!")
        return
    
    stats = await db.get_stats()
    
    text = f"""
🔧 **АДМИН ПАНЕЛЬ** 🔧

📊 **СТАТИСТИКА:**
├ 👥 Пользователей: **{stats['users']}**
├ 👑 VIP: **{stats['vip']}**
├ 💳 Сделок: **{stats['deals']}**
└ 💰 Монет в системе: **{stats['total_balance']}**

⚙️ **Доступные действия:**
├ 📊 Просмотр статистики
├ 👥 Управление пользователями
├ 💰 Пополнение баланса
└ 👑 Выдача VIP

👇 **Выбери действие в меню:**
    """
    
    await message.answer(
        text,
        reply_markup=Keyboards.admin(),
        parse_mode="Markdown"
    )

@dp.callback_query(F.data == "admin_stats")
async def callback_admin_stats(callback: CallbackQuery):
    """Статистика для админа"""
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("⛔ Доступ запрещён!", show_alert=True)
        return
    
    stats = await db.get_stats()
    
    text = f"""
📊 **ПОЛНАЯ СТАТИСТИКА**

👥 **Пользователи:**
├ Всего: **{stats['users']}**
├ VIP: **{stats['vip']}**
├ Обычных: **{stats['users'] - stats['vip']}**
└ Процент VIP: **{round(stats['vip']/stats['users']*100 if stats['users'] else 0, 1)}%**

💰 **Финансы:**
├ Всего монет: **{stats['total_balance']}**
├ Средний баланс: **{round(stats['total_balance']/stats['users'] if stats['users'] else 0, 1)}**
└ Монет у VIP: **{stats['vip'] * VIP_PRICE}** (оценка)

💳 **Активность:**
├ Завершённых сделок: **{stats['deals']}**
├ Активных пользователей: **{stats['users']}**
└ Конверсия в VIP: **{round(stats['vip']/stats['users']*100 if stats['users'] else 0, 1)}%**
    """
    
    await callback.message.edit_text(
        text,
        reply_markup=Keyboards.admin(),
        parse_mode="Markdown"
    )

# ========== ОБРАБОТКА ТЕКСТОВЫХ СООБЩЕНИЙ ==========
@dp.message()
async def handle_all_messages(message: Message):
    """Обработка всех сообщений"""
    if message.text and message.text.startswith('/'):
        # Если команда не обработана
        await message.answer(
            f"❌ Неизвестная команда: {message.text}\n\n"
            f"Используй /help для списка команд или /menu для открытия меню.",
            reply_markup=Keyboards.main()
        )
    else:
        # Любое другое сообщение
        await message.answer(
            f"👋 Привет, {message.from_user.first_name}!\n\n"
            f"Я бот {BOT_NAME}. Используй кнопки меню или команду /help.",
            reply_markup=Keyboards.main()
        )

# ========== ЗАПУСК БОТА ==========
async def on_startup():
    """Действия при запуске"""
    print(f"\n{Colors.CYAN}{'='*60}{Colors.END}")
    print(f"{Colors.MAGENTA}{Colors.BOLD}🔥 SHIZOGP БОТ - РАЗЪЕБАЛОВО-ВЕРСИЯ 🔥{Colors.END}")
    print(f"{Colors.CYAN}{'='*60}{Colors.END}")
    print(f"{Colors.GREEN}✅ Версия: {BOT_VERSION}{Colors.END}")
    print(f"{Colors.GREEN}✅ Токен: {BOT_TOKEN[:15]}...{Colors.END}")
    print(f"{Colors.GREEN}✅ Админы: {ADMIN_IDS}{Colors.END}")
    print(f"{Colors.GREEN}✅ База данных: {DATABASE_PATH}{Colors.END}")
    
    # Инициализация БД
    await db.init_db()
    
    # Информация о боте
    me = await bot.get_me()
    print(f"{Colors.GREEN}✅ Бот: @{me.username}{Colors.END}")
    print(f"{Colors.GREEN}✅ ID: {me.id}{Colors.END}")
    print(f"{Colors.GREEN}✅ Имя: {me.full_name}{Colors.END}")
    
    print(f"{Colors.CYAN}{'='*60}{Colors.END}")
    print(f"{Colors.YELLOW}{Colors.BOLD}🚀 БОТ ЗАПУЩЕН И ГОТОВ К РАБОТЕ!{Colors.END}")
    print(f"{Colors.CYAN}{'='*60}{Colors.END}")

async def on_shutdown():
    """Действия при остановке"""
    print(f"\n{Colors.RED}👋 БОТ ОСТАНАВЛИВАЕТСЯ...{Colors.END}")

async def main():
    """Главная функция"""
    await on_startup()
    
    try:
        await dp.start_polling(bot)
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}⚠️ Получен сигнал остановки{Colors.END}")
    except Exception as e:
        print(f"\n{Colors.RED}❌ Ошибка: {e}{Colors.END}")
    finally:
        await on_shutdown()
        await bot.session.close()
        print(f"{Colors.GREEN}✅ Бот успешно остановлен{Colors.END}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}⚠️ Бот остановлен пользователем{Colors.END}")
    except Exception as e:
        print(f"\n{Colors.RED}❌ Критическая ошибка: {e}{Colors.END}")
