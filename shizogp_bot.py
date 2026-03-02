#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🔥 SHIZOGP - АБСОЛЮТНО ПОЛНЫЙ ТЕЛЕГРАМ БОТ
Версия: 3.1 (АВТОУСТАНОВКА)
"""

import os
import sys
import subprocess
import importlib.util

# ========== АВТОМАТИЧЕСКАЯ УСТАНОВКА БИБЛИОТЕК ==========
def install_package(package):
    """Установка пакета через pip"""
    print(f"🔄 Устанавливаю {package}...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "--quiet", package])
        print(f"✅ {package} установлен!")
        return True
    except:
        print(f"❌ Ошибка установки {package}")
        return False

# Проверяем и устанавливаем все необходимые библиотеки
required_packages = [
    "aiogram==3.4.1",
    "aiosqlite==0.19.0",
    "python-dotenv==1.0.0"
]

for package in required_packages:
    package_name = package.split("==")[0]
    if importlib.util.find_spec(package_name) is None:
        print(f"⚠️ Библиотека {package_name} не найдена")
        install_package(package)
    else:
        print(f"✅ {package_name} уже установлен")

# ========== ТЕПЕРЬ МОЖНО ИМПОРТИРОВАТЬ ==========
print("🚀 Загрузка бота...")

import json
import asyncio
import logging
import sqlite3
import aiosqlite
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any
from contextlib import asynccontextmanager

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.exceptions import TelegramBadRequest

try:
    from dotenv import load_dotenv
except:
    pass

# Загружаем переменные окружения если есть .env
if os.path.exists('.env'):
    load_dotenv()

# ========== НАСТРОЙКИ ==========
BOT_TOKEN = os.getenv('BOT_TOKEN', '8498694285:AAG3Ezx7BDGciUIYAAb4UHMtFUmBYvock3w')
ADMIN_IDS = [int(x) for x in os.getenv('ADMIN_IDS', '2091630272').split(',') if x]
VIP_CHAT_LINK = os.getenv('VIP_CHAT_LINK', 'https://t.me/+r3rxYlBjbTYyMDY6')
SUPPORT_LINK = os.getenv('SUPPORT_LINK', 'https://t.me/SHIZOGP_support')
CHANNEL_LINK = os.getenv('CHANNEL_LINK', 'https://t.me/SHIZOGP_channel')

VIP_PRICE = 550
VIP_DURATION = 30
REFERRAL_BONUS = 50
START_BALANCE = 100
DATABASE_PATH = "shizogp.db"
BOT_VERSION = "3.1 (АВТОУСТАНОВКА)"
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

# ========== ЦВЕТА ==========
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
                    is_banned INTEGER DEFAULT 0
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
            
            cursor = await db.execute('SELECT SUM(balance) FROM users')
            total_balance = (await cursor.fetchone())[0] or 0
            
            return {
                'users': users,
                'vip': vip,
                'total_balance': total_balance
            }

# ========== СОЗДАЁМ ЭКЗЕМПЛЯР БД ==========
db = Database()

# ========== КЛАВИАТУРЫ ==========
class Keyboards:
    @staticmethod
    def main() -> InlineKeyboardMarkup:
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
            [InlineKeyboardButton(text="💰 ПОПОЛНИТЬ БАЛАНС", callback_data="admin_add_balance")],
            [InlineKeyboardButton(text="👑 ВЫДАТЬ VIP", callback_data="admin_give_vip")],
            [InlineKeyboardButton(text="◀ НАЗАД", callback_data="main_menu")]
        ]
        return InlineKeyboardMarkup(inline_keyboard=buttons)

# ========== СОСТОЯНИЯ ==========
class States(StatesGroup):
    admin_add_balance_user = State()
    admin_add_balance_amount = State()
    admin_give_vip_user = State()

# ========== ИНИЦИАЛИЗАЦИЯ БОТА ==========
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# ========== КОМАНДЫ ==========
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
    
    welcome_text = f"""
🎮 **ДОБРО ПОЖАЛОВАТЬ В SHIZOGP!** 🎮

👤 **Информация:**
├ 💰 Баланс: **{user['balance']}** монет
├ 👥 Рефералов: **{user['referral_count']}**
└ 👑 VIP: {"✅" if is_vip else "❌"}

🔥 **Выбери действие в меню ниже!**
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
        "📋 **ГЛАВНОЕ МЕНЮ**",
        reply_markup=Keyboards.main(),
        parse_mode="Markdown"
    )

@dp.message(Command("help"))
async def cmd_help(message: Message):
    """Команда помощи"""
    help_text = f"""
🆘 **ПОМОЩЬ ПО БОТУ {BOT_NAME}**

📌 **Команды:**
/start - Запустить
/menu - Меню
/help - Помощь
/profile - Профиль
/balance - Баланс

💎 **Рефералы:** +{REFERRAL_BONUS} монет за друга
👑 **VIP:** {VIP_PRICE} монет / {VIP_DURATION} дней

📢 Канал: {CHANNEL_LINK}
📞 Поддержка: {SUPPORT_LINK}
    """
    
    await message.answer(
        help_text,
        reply_markup=Keyboards.back(),
        parse_mode="Markdown"
    )

@dp.message(Command("profile"))
async def cmd_profile(message: Message):
    """Профиль"""
    user_id = message.from_user.id
    user = await db.get_user(user_id)
    is_vip = await db.check_vip(user_id)
    
    text = f"""
📊 **ТВОЙ ПРОФИЛЬ**

👤 ID: `{user_id}`
💰 Баланс: **{user['balance']}** монет
👥 Рефералов: **{user['referral_count']}**
👑 VIP: {"✅" if is_vip else "❌"}
📅 Регистрация: {user['registration_date'][:10]}
    """
    
    await message.answer(text, reply_markup=Keyboards.back(), parse_mode="Markdown")

@dp.message(Command("balance"))
async def cmd_balance(message: Message):
    """Баланс"""
    user_id = message.from_user.id
    user = await db.get_user(user_id)
    
    await message.answer(
        f"💰 **ТВОЙ БАЛАНС**\n\n"
        f"Монет: **{user['balance']}** 💰\n"
        f"Рефералов: **{user['referral_count']}** 👥\n\n"
        f"До VIP: **{max(0, VIP_PRICE - user['balance'])}** монет",
        reply_markup=Keyboards.back(),
        parse_mode="Markdown"
    )

# ========== КНОПКИ ==========
@dp.callback_query(F.data == "main_menu")
async def callback_main_menu(callback: CallbackQuery):
    """Возврат в главное меню"""
    await callback.message.edit_text(
        "📋 **ГЛАВНОЕ МЕНЮ**",
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
        f"Рефералов: **{user['referral_count']}** 👥",
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

👥 Рефералов: **{user['referral_count']}**
💰 Заработано: **{user['referral_count'] * REFERRAL_BONUS}** монет
🎁 Бонус за друга: **+{REFERRAL_BONUS}** монет

🔗 **Твоя ссылка:**
`{ref_link}`
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

📅 Действует до: {user['vip_until'][:10]}
        """
    else:
        text = f"""
👑 **VIP СТАТУС**

💰 Цена: {VIP_PRICE} монет
📅 Длительность: {VIP_DURATION} дней
📊 Твой баланс: {user['balance']} монет
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
        await db.update_balance(user_id, -VIP_PRICE, "Покупка VIP")
        await db.activate_vip(user_id)
        
        await callback.message.edit_text(
            f"✅ **VIP АКТИВИРОВАН!**\n\n"
            f"💰 Остаток: {user['balance'] - VIP_PRICE} монет",
            reply_markup=Keyboards.vip(True),
            parse_mode="Markdown"
        )
    else:
        need = VIP_PRICE - user['balance']
        await callback.message.edit_text(
            f"❌ **Недостаточно монет!**\n\nНужно ещё: **{need}** монет",
            reply_markup=Keyboards.back(),
            parse_mode="Markdown"
        )

@dp.callback_query(F.data == "profile")
async def callback_profile(callback: CallbackQuery):
    """Профиль"""
    user_id = callback.from_user.id
    user = await db.get_user(user_id)
    is_vip = await db.check_vip(user_id)
    
    text = f"""
📊 **ТВОЙ ПРОФИЛЬ**

👤 ID: `{user_id}`
💰 Баланс: **{user['balance']}** монет
👥 Рефералов: **{user['referral_count']}**
👑 VIP: {"✅" if is_vip else "❌"}
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
        f"🆘 **ПОМОЩЬ**\n\n"
        f"📌 Команды: /start, /menu, /help, /profile, /balance\n"
        f"💎 Рефералы: +{REFERRAL_BONUS} монет\n"
        f"👑 VIP: {VIP_PRICE} монет\n"
        f"📞 Поддержка: {SUPPORT_LINK}",
        reply_markup=Keyboards.back(),
        parse_mode="Markdown"
    )

@dp.callback_query(F.data == "shop")
async def callback_shop(callback: CallbackQuery):
    """Магазин"""
    await callback.message.edit_text(
        "🛒 **МАГАЗИН**\n\n⚡ В разработке...",
        reply_markup=Keyboards.back(),
        parse_mode="Markdown"
    )

# ========== АДМИНКА ==========
@dp.message(Command("admin"))
async def cmd_admin(message: Message):
    """Админ панель"""
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("⛔ Доступ запрещён!")
        return
    
    stats = await db.get_stats()
    
    text = f"""
🔧 **АДМИН ПАНЕЛЬ**

📊 **СТАТИСТИКА:**
👥 Пользователей: {stats['users']}
👑 VIP: {stats['vip']}
💰 Всего монет: {stats['total_balance']}
    """
    
    await message.answer(text, reply_markup=Keyboards.admin(), parse_mode="Markdown")

@dp.callback_query(F.data == "admin_stats")
async def callback_admin_stats(callback: CallbackQuery):
    """Статистика"""
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("⛔ Доступ запрещён!", show_alert=True)
        return
    
    stats = await db.get_stats()
    
    text = f"""
📊 **СТАТИСТИКА**

👥 Всего пользователей: {stats['users']}
👑 VIP пользователей: {stats['vip']}
💰 Монет в системе: {stats['total_balance']}
    """
    
    await callback.message.edit_text(text, reply_markup=Keyboards.admin(), parse_mode="Markdown")

# ========== ЗАПУСК ==========
async def on_startup():
    """Запуск"""
    print(f"\n{Colors.CYAN}{'='*50}{Colors.END}")
    print(f"{Colors.MAGENTA}🔥 SHIZOGP БОТ ЗАПУЩЕН 🔥{Colors.END}")
    print(f"{Colors.CYAN}{'='*50}{Colors.END}")
    print(f"{Colors.GREEN}✅ Версия: {BOT_VERSION}{Colors.END}")
    
    await db.init_db()
    
    me = await bot.get_me()
    print(f"{Colors.GREEN}✅ Бот: @{me.username}{Colors.END}")
    print(f"{Colors.GREEN}✅ ID: {me.id}{Colors.END}")
    print(f"{Colors.CYAN}{'='*50}{Colors.END}")

async def on_shutdown():
    """Остановка"""
    print(f"\n{Colors.RED}👋 БОТ ОСТАНОВЛЕН{Colors.END}")

async def main():
    await on_startup()
    try:
        await dp.start_polling(bot)
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}⚠️ Остановка...{Colors.END}")
    finally:
        await on_shutdown()
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())
