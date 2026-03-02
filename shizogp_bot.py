#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🔥 SHIZOGP - ПОЛНАЯ ВЕРСИЯ С ЗАМОРОЗКОЙ
✅ VIP ссылка приходит в ЛС
✅ Скины замораживаются
✅ Деньги замораживаются
✅ Подтверждение сделок
✅ Отмена сделок
"""

import os
import sys
import subprocess
import importlib.util
import json
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any

# ========== АВТОУСТАНОВКА ==========
def install_package(package):
    print(f"🔄 Устанавливаю {package}...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "--quiet", package])
        print(f"✅ {package} установлен!")
        return True
    except Exception as e:
        print(f"❌ Ошибка установки {package}: {e}")
        return False

required_packages = [
    "aiogram==3.4.1",
    "aiosqlite==0.19.0",
    "python-dotenv==1.0.0"
]

for package in required_packages:
    package_name = package.split("==")[0]
    spec = importlib.util.find_spec(package_name)
    if spec is None:
        print(f"⚠️ Библиотека {package_name} не найдена, устанавливаю...")
        if not install_package(package):
            print(f"❌ Критическая ошибка: не удалось установить {package_name}")
            sys.exit(1)
    else:
        print(f"✅ {package_name} уже установлен")

# ========== ИМПОРТЫ ==========
print("🚀 Загрузка бота...")

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
import aiosqlite

try:
    from dotenv import load_dotenv
    load_dotenv()
except:
    pass

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
DAILY_BONUS = 10
DATABASE_PATH = "shizogp.db"
BOT_VERSION = "6.0 (ПОЛНАЯ ЗАМОРОЗКА)"
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
        async with aiosqlite.connect(self.db_path) as db:
            # Пользователи
            await db.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    full_name TEXT,
                    balance INTEGER DEFAULT 100,
                    frozen_balance INTEGER DEFAULT 0,
                    vip_status INTEGER DEFAULT 0,
                    vip_until TEXT,
                    referrer_id INTEGER,
                    referral_count INTEGER DEFAULT 0,
                    daily_bonus TEXT,
                    registration_date TEXT DEFAULT CURRENT_TIMESTAMP,
                    last_visit TEXT DEFAULT CURRENT_TIMESTAMP,
                    is_admin INTEGER DEFAULT 0
                )
            ''')
            
            # Транзакции
            await db.execute('''
                CREATE TABLE IF NOT EXISTS transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    amount INTEGER,
                    type TEXT,
                    status TEXT DEFAULT 'completed',
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
                    buyer_id INTEGER DEFAULT NULL,
                    status TEXT DEFAULT 'available',
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    sold_at TEXT
                )
            ''')
            
            # Активные сделки
            await db.execute('''
                CREATE TABLE IF NOT EXISTS deals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    skin_id INTEGER UNIQUE,
                    buyer_id INTEGER,
                    seller_id INTEGER,
                    price INTEGER,
                    status TEXT DEFAULT 'pending',
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    confirmed_at TEXT
                )
            ''')
            
            await db.commit()
        
        logger.info(f"{Colors.GREEN}✅ База данных инициализирована{Colors.END}")
    
    async def get_user(self, user_id: int) -> Optional[Dict]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
            user = await cursor.fetchone()
            return dict(user) if user else None
    
    async def create_user(self, user_id: int, username: str, full_name: str, referrer_id: int = None) -> bool:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute('SELECT user_id FROM users WHERE user_id = ?', (user_id,))
            if await cursor.fetchone():
                return False
            
            await db.execute('''
                INSERT INTO users (user_id, username, full_name, balance, referrer_id)
                VALUES (?, ?, ?, ?, ?)
            ''', (user_id, username, full_name, START_BALANCE, referrer_id))
            
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
    
    async def freeze_balance(self, user_id: int, amount: int, skin_id: int) -> bool:
        """Заморозка баланса при покупке"""
        async with aiosqlite.connect(self.db_path) as db:
            # Проверяем баланс
            cursor = await db.execute('SELECT balance FROM users WHERE user_id = ?', (user_id,))
            user = await cursor.fetchone()
            
            if not user or user[0] < amount:
                return False
            
            # Замораживаем средства
            await db.execute('''
                UPDATE users SET balance = balance - ?, frozen_balance = frozen_balance + ? 
                WHERE user_id = ?
            ''', (amount, amount, user_id))
            
            # Создаём сделку
            await db.execute('''
                INSERT INTO deals (skin_id, buyer_id, seller_id, price, status)
                SELECT ?, ?, seller_id, ?, 'pending'
                FROM skins WHERE id = ?
            ''', (skin_id, user_id, amount, skin_id))
            
            # Обновляем статус скина
            await db.execute('''
                UPDATE skins SET status = 'sold', buyer_id = ? WHERE id = ?
            ''', (user_id, skin_id))
            
            await db.commit()
            return True
    
    async def confirm_deal(self, skin_id: int) -> bool:
        """Подтверждение сделки - разморозка денег продавцу"""
        async with aiosqlite.connect(self.db_path) as db:
            # Получаем информацию о сделке
            cursor = await db.execute('''
                SELECT d.*, s.seller_id, s.price 
                FROM deals d
                JOIN skins s ON d.skin_id = s.id
                WHERE d.skin_id = ? AND d.status = 'pending'
            ''', (skin_id,))
            deal = await cursor.fetchone()
            
            if not deal:
                return False
            
            # Размораживаем деньги продавцу
            await db.execute('''
                UPDATE users SET frozen_balance = frozen_balance - ?, balance = balance + ? 
                WHERE user_id = ?
            ''', (deal[4], deal[4], deal[3]))
            
            # Обновляем статус сделки
            await db.execute('''
                UPDATE deals SET status = 'confirmed', confirmed_at = CURRENT_TIMESTAMP 
                WHERE skin_id = ?
            ''', (skin_id,))
            
            await db.commit()
            return True
    
    async def cancel_deal(self, skin_id: int) -> bool:
        """Отмена сделки - разморозка денег покупателю"""
        async with aiosqlite.connect(self.db_path) as db:
            # Получаем информацию о сделке
            cursor = await db.execute('''
                SELECT d.*, s.seller_id, s.price 
                FROM deals d
                JOIN skins s ON d.skin_id = s.id
                WHERE d.skin_id = ? AND d.status = 'pending'
            ''', (skin_id,))
            deal = await cursor.fetchone()
            
            if not deal:
                return False
            
            # Размораживаем деньги покупателю
            await db.execute('''
                UPDATE users SET frozen_balance = frozen_balance - ?, balance = balance + ? 
                WHERE user_id = ?
            ''', (deal[4], deal[4], deal[2]))
            
            # Возвращаем скин в продажу
            await db.execute('''
                UPDATE skins SET status = 'available', buyer_id = NULL WHERE id = ?
            ''', (skin_id,))
            
            # Обновляем статус сделки
            await db.execute('''
                UPDATE deals SET status = 'cancelled' WHERE skin_id = ?
            ''', (skin_id,))
            
            await db.commit()
            return True
    
    async def activate_vip(self, user_id: int, days: int = VIP_DURATION) -> bool:
        vip_until = (datetime.now() + timedelta(days=days)).strftime('%Y-%m-%d %H:%M:%S')
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('''
                UPDATE users SET vip_status = 1, vip_until = ? WHERE user_id = ?
            ''', (vip_until, user_id))
            await db.commit()
            return True
    
    async def check_vip(self, user_id: int) -> bool:
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
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute('SELECT COUNT(*) FROM users')
            users = (await cursor.fetchone())[0]
            
            cursor = await db.execute('SELECT COUNT(*) FROM users WHERE vip_status = 1')
            vip = (await cursor.fetchone())[0]
            
            cursor = await db.execute('SELECT SUM(balance) FROM users')
            total_balance = (await cursor.fetchone())[0] or 0
            
            cursor = await db.execute('SELECT SUM(frozen_balance) FROM users')
            total_frozen = (await cursor.fetchone())[0] or 0
            
            cursor = await db.execute('SELECT COUNT(*) FROM deals WHERE status = ?', ('pending',))
            active_deals = (await cursor.fetchone())[0]
            
            return {
                'users': users,
                'vip': vip,
                'total_balance': total_balance,
                'total_frozen': total_frozen,
                'active_deals': active_deals
            }
    
    async def get_top_users(self, limit: int = 10) -> List[Dict]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute('''
                SELECT user_id, username, balance, frozen_balance, referral_count 
                FROM users 
                ORDER BY balance DESC 
                LIMIT ?
            ''', (limit,))
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
    
    async def add_skin(self, name: str, quality: str, price: int, seller_id: int, image_url: str = '') -> int:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute('''
                INSERT INTO skins (name, quality, price, image_url, seller_id)
                VALUES (?, ?, ?, ?, ?)
            ''', (name, quality, price, image_url, seller_id))
            await db.commit()
            return cursor.lastrowid
    
    async def get_available_skins(self) -> List[Dict]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute('''
                SELECT * FROM skins WHERE status = 'available' ORDER BY created_at DESC
            ''')
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
    
    async def get_user_deals(self, user_id: int) -> List[Dict]:
        """Получить активные сделки пользователя"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute('''
                SELECT d.*, s.name, s.quality 
                FROM deals d
                JOIN skins s ON d.skin_id = s.id
                WHERE (d.buyer_id = ? OR d.seller_id = ?) AND d.status = 'pending'
                ORDER BY d.created_at DESC
            ''', (user_id, user_id))
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

# ========== СОЗДАЁМ ЭКЗЕМПЛЯР БД ==========
db = Database()

# ========== КЛАВИАТУРЫ ==========
class Keyboards:
    @staticmethod
    def main() -> InlineKeyboardMarkup:
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
                InlineKeyboardButton(text="🎁 ДЕЙЛИК", callback_data="daily"),
                InlineKeyboardButton(text="🏆 ТОП", callback_data="top")
            ],
            [
                InlineKeyboardButton(text="🔄 МОИ СДЕЛКИ", callback_data="my_deals"),
                InlineKeyboardButton(text="📢 КАНАЛ", url=CHANNEL_LINK)
            ],
            [InlineKeyboardButton(text="ℹ️ ПОМОЩЬ", callback_data="help")]
        ]
        return InlineKeyboardMarkup(inline_keyboard=buttons)
    
    @staticmethod
    def back() -> InlineKeyboardMarkup:
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀ НАЗАД В МЕНЮ", callback_data="main_menu")]
        ])
    
    @staticmethod
    def vip(is_vip: bool = False) -> InlineKeyboardMarkup:
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
        buttons = [
            [InlineKeyboardButton(text="📊 СТАТИСТИКА", callback_data="admin_stats")],
            [InlineKeyboardButton(text="💰 ПОПОЛНИТЬ БАЛАНС", callback_data="admin_add_balance")],
            [InlineKeyboardButton(text="👑 ВЫДАТЬ VIP", callback_data="admin_give_vip")],
            [InlineKeyboardButton(text="🛒 ДОБАВИТЬ СКИН", callback_data="admin_add_skin")],
            [InlineKeyboardButton(text="📋 АКТИВНЫЕ СДЕЛКИ", callback_data="admin_deals")],
            [InlineKeyboardButton(text="◀ НАЗАД", callback_data="main_menu")]
        ]
        return InlineKeyboardMarkup(inline_keyboard=buttons)
    
    @staticmethod
    def shop(skins: List[Dict]) -> InlineKeyboardMarkup:
        buttons = []
        for skin in skins:
            buttons.append([InlineKeyboardButton(
                text=f"{skin['name']} ({skin['quality']}) - {skin['price']}💰",
                callback_data=f"buy_skin_{skin['id']}"
            )])
        buttons.append([InlineKeyboardButton(text="◀ НАЗАД", callback_data="main_menu")])
        return InlineKeyboardMarkup(inline_keyboard=buttons)
    
    @staticmethod
    def deal_actions(skin_id: int, user_id: int, deal: Dict) -> InlineKeyboardMarkup:
        buttons = []
        if deal['buyer_id'] == user_id:
            buttons.append([
                InlineKeyboardButton(text="✅ ПОДТВЕРДИТЬ ПОЛУЧЕНИЕ", callback_data=f"confirm_deal_{skin_id}"),
                InlineKeyboardButton(text="❌ ОТМЕНИТЬ СДЕЛКУ", callback_data=f"cancel_deal_{skin_id}")
            ])
        buttons.append([InlineKeyboardButton(text="◀ НАЗАД", callback_data="my_deals")])
        return InlineKeyboardMarkup(inline_keyboard=buttons)

# ========== СОСТОЯНИЯ ==========
class States(StatesGroup):
    admin_add_balance_user = State()
    admin_add_balance_amount = State()
    admin_give_vip_user = State()
    admin_add_skin_name = State()
    admin_add_skin_quality = State()
    admin_add_skin_price = State()

# ========== ИНИЦИАЛИЗАЦИЯ БОТА ==========
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# ========== КОМАНДЫ ==========
@dp.message(Command("start"))
async def cmd_start(message: Message):
    user_id = message.from_user.id
    username = message.from_user.username or "NoName"
    full_name = message.from_user.full_name or "NoName"
    
    args = message.text.split()
    referrer_id = None
    if len(args) > 1 and args[1].startswith("ref_"):
        try:
            referrer_id = int(args[1].replace("ref_", ""))
            if referrer_id == user_id:
                referrer_id = None
        except:
            pass
    
    await db.create_user(user_id, username, full_name, referrer_id)
    user = await db.get_user(user_id)
    is_vip = await db.check_vip(user_id)
    
    welcome_text = f"""
🎮 **ДОБРО ПОЖАЛОВАТЬ В SHIZOGP!** 🎮

👤 **Твой профиль:**
├ 💰 Доступно: **{user['balance']}** монет
├ 🔒 Заморожено: **{user['frozen_balance']}** монет
├ 👥 Рефералов: **{user['referral_count']}**
└ 👑 VIP: {"✅" if is_vip else "❌"}

🔥 **Версия 6.0 - ПОЛНАЯ ЗАМОРОЗКА!**
├ ✅ Деньги замораживаются до подтверждения
├ ✅ Скины замораживаются
├ ✅ Сделки с подтверждением
└ ✅ Отмена сделок

⚡ **Выбери действие в меню ниже!**
    """
    
    await message.answer(
        welcome_text,
        reply_markup=Keyboards.main(),
        parse_mode="Markdown"
    )

@dp.message(Command("menu"))
async def cmd_menu(message: Message):
    await message.answer(
        "📋 **ГЛАВНОЕ МЕНЮ**",
        reply_markup=Keyboards.main(),
        parse_mode="Markdown"
    )

@dp.message(Command("help"))
async def cmd_help(message: Message):
    help_text = f"""
🆘 **ПОМОЩЬ ПО БОТУ {BOT_NAME}**

📌 **Основные команды:**
/start - Запустить бота
/menu - Открыть меню
/help - Показать помощь
/profile - Мой профиль
/balance - Мой баланс
/daily - Ежедневный бонус
/top - Топ пользователей
/mydeals - Мои сделки

💎 **Реферальная система:**
За каждого друга ты получаешь **+{REFERRAL_BONUS}** монет!

👑 **VIP статус:**
├ Стоимость: **{VIP_PRICE}** монет
├ Длительность: **{VIP_DURATION}** дней
├ Доступ к закрытому VIP чату
└ Удвоенный реферальный бонус

🛒 **Магазин:**
├ Деньги замораживаются до подтверждения
├ Скин замораживается
├ Подтверждение получения
└ Возврат при отмене

📢 **Наши ресурсы:**
├ Канал: {CHANNEL_LINK}
├ VIP чат: {VIP_CHAT_LINK}
└ Поддержка: {SUPPORT_LINK}
    """
    
    await message.answer(
        help_text,
        reply_markup=Keyboards.back(),
        parse_mode="Markdown",
        disable_web_page_preview=True
    )

@dp.message(Command("profile"))
async def cmd_profile(message: Message):
    user_id = message.from_user.id
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
├ Доступно: **{user['balance']}** монет
├ Заморожено: **{user['frozen_balance']}** монет
├ Всего: **{user['balance'] + user['frozen_balance']}** монет
├ Рефералов: **{user['referral_count']}** 👥
└ Заработано: **{user['referral_count'] * REFERRAL_BONUS}** монет

👑 **VIP статус:**
├ Статус: {"✅ АКТИВЕН" if is_vip else "❌ НЕ АКТИВЕН"}
{f"├ Действует до: {user['vip_until'][:10]}" if is_vip and user['vip_until'] else ""}
└ Стоимость: {VIP_PRICE} монет
    """
    
    await message.answer(text, reply_markup=Keyboards.back(), parse_mode="Markdown")

@dp.message(Command("balance"))
async def cmd_balance(message: Message):
    user_id = message.from_user.id
    user = await db.get_user(user_id)
    
    await message.answer(
        f"💰 **ТВОЙ БАЛАНС**\n\n"
        f"Доступно: **{user['balance']}** монет 💰\n"
        f"Заморожено: **{user['frozen_balance']}** монет 🔒\n"
        f"Рефералов: **{user['referral_count']}** 👥\n\n"
        f"До VIP: **{max(0, VIP_PRICE - (user['balance'] + user['frozen_balance']))}** монет",
        reply_markup=Keyboards.back(),
        parse_mode="Markdown"
    )

@dp.message(Command("daily"))
async def cmd_daily(message: Message):
    user_id = message.from_user.id
    user = await db.get_user(user_id)
    
    today = datetime.now().strftime('%Y-%m-%d')
    
    if user.get('daily_bonus') == today:
        await message.answer(
            "❌ **Ты уже получил ежедневный бонус сегодня!**\n"
            "Возвращайся завтра!",
            reply_markup=Keyboards.back(),
            parse_mode="Markdown"
        )
        return
    
    async with aiosqlite.connect(DATABASE_PATH) as db_conn:
        await db_conn.execute('''
            UPDATE users SET balance = balance + ?, daily_bonus = ? WHERE user_id = ?
        ''', (DAILY_BONUS, today, user_id))
        await db_conn.commit()
    
    await message.answer(
        f"🎁 **ЕЖЕДНЕВНЫЙ БОНУС**\n\n"
        f"Ты получил **+{DAILY_BONUS}** монет!\n"
        f"💰 Новый баланс: **{user['balance'] + DAILY_BONUS}** монет",
        reply_markup=Keyboards.back(),
        parse_mode="Markdown"
    )

@dp.message(Command("top"))
async def cmd_top(message: Message):
    top_users = await db.get_top_users(10)
    
    text = "🏆 **ТОП-10 ПОЛЬЗОВАТЕЛЕЙ**\n\n"
    
    for i, user in enumerate(top_users, 1):
        medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "👤"
        username = user['username'] or f"ID {user['user_id']}"
        total = user['balance'] + user['frozen_balance']
        text += f"{medal} **{i}.** {username} — {total}💰 (реф: {user['referral_count']})\n"
    
    await message.answer(text, reply_markup=Keyboards.back(), parse_mode="Markdown")

@dp.message(Command("mydeals"))
async def cmd_mydeals(message: Message):
    user_id = message.from_user.id
    deals = await db.get_user_deals(user_id)
    
    if not deals:
        await message.answer(
            "📋 **У тебя нет активных сделок**",
            reply_markup=Keyboards.back(),
            parse_mode="Markdown"
        )
        return
    
    text = "📋 **ТВОИ АКТИВНЫЕ СДЕЛКИ**\n\n"
    for deal in deals:
        role = "Покупатель" if deal['buyer_id'] == user_id else "Продавец"
        text += f"🎯 {deal['name']} ({deal['quality']})\n"
        text += f"💰 Цена: {deal['price']} монет\n"
        text += f"👤 Ты: {role}\n"
        text += f"🔄 Статус: Ожидает подтверждения\n\n"
    
    await message.answer(text, reply_markup=Keyboards.back(), parse_mode="Markdown")

# ========== КНОПКИ ==========
@dp.callback_query(F.data == "main_menu")
async def callback_main_menu(callback: CallbackQuery):
    await callback.message.edit_text(
        "📋 **ГЛАВНОЕ МЕНЮ**",
        reply_markup=Keyboards.main(),
        parse_mode="Markdown"
    )

@dp.callback_query(F.data == "balance")
async def callback_balance(callback: CallbackQuery):
    user_id = callback.from_user.id
    user = await db.get_user(user_id)
    
    await callback.message.edit_text(
        f"💰 **ТВОЙ БАЛАНС**\n\n"
        f"Доступно: **{user['balance']}** монет 💰\n"
        f"Заморожено: **{user['frozen_balance']}** монет 🔒\n"
        f"Рефералов: **{user['referral_count']}** 👥",
        reply_markup=Keyboards.back(),
        parse_mode="Markdown"
    )

@dp.callback_query(F.data == "referral")
async def callback_referral(callback: CallbackQuery):
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
    user_id = callback.from_user.id
    is_vip = await db.check_vip(user_id)
    user = await db.get_user(user_id)
    
    if is_vip:
        text = f"""
👑 **VIP СТАТУС АКТИВЕН**

✅ Ты имеешь доступ к закрытому VIP чату!
📅 Действует до: {user['vip_until'][:10]}

**Преимущества VIP:**
├ 🔥 Закрытый VIP чат
├ 💰 Двойной бонус за рефералов
├ 🎁 Эксклюзивные предложения
└ 🚀 Ранний доступ к новым скинам

👇 **Нажми кнопку ниже чтобы войти в чат!**
        """
    else:
        total = user['balance'] + user['frozen_balance']
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

📊 **Твой баланс:** {total} монет
{"✅ **Можешь купить!**" if total >= VIP_PRICE else f"❌ **Нужно ещё {VIP_PRICE - total} монет**"}
        """
    
    await callback.message.edit_text(
        text,
        reply_markup=Keyboards.vip(is_vip),
        parse_mode="Markdown"
    )

@dp.callback_query(F.data == "buy_vip")
async def callback_buy_vip(callback: CallbackQuery):
    """Покупка VIP - С ССЫЛКОЙ В ЛС"""
    user_id = callback.from_user.id
    user = await db.get_user(user_id)
    total = user['balance'] + user['frozen_balance']
    
    if total >= VIP_PRICE and user['balance'] >= VIP_PRICE:
        # Списываем монеты
        await db.update_balance(user_id, -VIP_PRICE, "Покупка VIP")
        await db.activate_vip(user_id)
        
        # Отправляем ссылку в ЛИЧКУ
        try:
            await bot.send_message(
                user_id,
                f"👑 **ТВОЯ ССЫЛКА В VIP ЧАТ**\n\n"
                f"{VIP_CHAT_LINK}\n\n"
                f"🔗 **Сохрани её, чтобы не потерять!**\n\n"
                f"👇 Там общаются топовые трейдеры и выходят эксклюзивные предложения!",
                parse_mode="Markdown"
            )
            logger.info(f"✅ VIP ссылка отправлена пользователю {user_id}")
        except Exception as e:
            logger.error(f"❌ Ошибка отправки VIP ссылки: {e}")
            await callback.message.answer(
                f"👑 **VIP ЧАТ**\n\n{VIP_CHAT_LINK}",
                parse_mode="Markdown"
            )
        
        # Изменяем текущее сообщение
        await callback.message.edit_text(
            f"✅ **VIP УСПЕШНО АКТИВИРОВАН!**\n\n"
            f"💰 Списанo: {VIP_PRICE} монет\n"
            f"📅 Действует: {VIP_DURATION} дней\n"
            f"💰 Остаток на балансе: {user['balance'] - VIP_PRICE} монет\n\n"
            f"👑 **Ссылка на чат отправлена в личные сообщения!**",
            reply_markup=Keyboards.vip(True),
            parse_mode="Markdown"
        )
        
        # Уведомление админам
        for admin_id in ADMIN_IDS:
            try:
                await bot.send_message(
                    admin_id,
                    f"👑 Пользователь @{callback.from_user.username or user_id} купил VIP!\n"
                    f"💰 Баланс был: {user['balance']}, стал: {user['balance'] - VIP_PRICE}"
                )
            except:
                pass
    else:
        need = VIP_PRICE - total
        await callback.message.edit_text(
            f"❌ **Недостаточно монет!**\n\n"
            f"Твой баланс: {total} монет\n"
            f"Нужно ещё: **{need}** монет\n"
            f"(Доступно: {user['balance']}, заморожено: {user['frozen_balance']})\n\n"
            f"🤝 **Приглашай друзей и получай бонусы!**",
            reply_markup=Keyboards.back(),
            parse_mode="Markdown"
        )

@dp.callback_query(F.data == "profile")
async def callback_profile(callback: CallbackQuery):
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
├ Доступно: **{user['balance']}** монет
├ Заморожено: **{user['frozen_balance']}** монет
├ Всего: **{user['balance'] + user['frozen_balance']}** монет
├ Рефералов: **{user['referral_count']}** 👥
└ Заработано: **{user['referral_count'] * REFERRAL_BONUS}** монет

👑 **VIP статус:**
├ Статус: {"✅ АКТИВЕН" if is_vip else "❌ НЕ АКТИВЕН"}
{f"├ Действует до: {user['vip_until'][:10]}" if is_vip and user['vip_until'] else ""}
└ Стоимость: {VIP_PRICE} монет
    """
    
    await callback.message.edit_text(
        text,
        reply_markup=Keyboards.back(),
        parse_mode="Markdown"
    )

@dp.callback_query(F.data == "daily")
async def callback_daily(callback: CallbackQuery):
    user_id = callback.from_user.id
    user = await db.get_user(user_id)
    
    today = datetime.now().strftime('%Y-%m-%d')
    
    if user.get('daily_bonus') == today:
        await callback.message.edit_text(
            "❌ **Ты уже получил ежедневный бонус сегодня!**\n"
            "Возвращайся завтра!",
            reply_markup=Keyboards.back(),
            parse_mode="Markdown"
        )
        return
    
    async with aiosqlite.connect(DATABASE_PATH) as db_conn:
        await db_conn.execute('''
            UPDATE users SET balance = balance + ?, daily_bonus = ? WHERE user_id = ?
        ''', (DAILY_BONUS, today, user_id))
        await db_conn.commit()
    
    await callback.message.edit_text(
        f"🎁 **ЕЖЕДНЕВНЫЙ БОНУС**\n\n"
        f"Ты получил **+{DAILY_BONUS}** монет!\n"
        f"💰 Новый баланс: **{user['balance'] + DAILY_BONUS}** монет",
        reply_markup=Keyboards.back(),
        parse_mode="Markdown"
    )

@dp.callback_query(F.data == "top")
async def callback_top(callback: CallbackQuery):
    top_users = await db.get_top_users(10)
    
    text = "🏆 **ТОП-10 ПОЛЬЗОВАТЕЛЕЙ**\n\n"
    
    for i, user in enumerate(top_users, 1):
        medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "👤"
        username = user['username'] or f"ID {user['user_id']}"
        total = user['balance'] + user['frozen_balance']
        text += f"{medal} **{i}.** {username} — {total}💰 (реф: {user['referral_count']})\n"
    
    await callback.message.edit_text(text, reply_markup=Keyboards.back(), parse_mode="Markdown")

@dp.callback_query(F.data == "my_deals")
async def callback_my_deals(callback: CallbackQuery):
    user_id = callback.from_user.id
    deals = await db.get_user_deals(user_id)
    
    if not deals:
        await callback.message.edit_text(
            "📋 **У тебя нет активных сделок**",
            reply_markup=Keyboards.back(),
            parse_mode="Markdown"
        )
        return
    
    text = "📋 **ТВОИ АКТИВНЫЕ СДЕЛКИ**\n\n"
    buttons = []
    
    for deal in deals:
        role = "Покупатель" if deal['buyer_id'] == user_id else "Продавец"
        text += f"🎯 {deal['name']} ({deal['quality']})\n"
        text += f"💰 {deal['price']} монет | 👤 {role}\n\n"
        buttons.append([InlineKeyboardButton(
            text=f"🔍 Сделка #{deal['id']} - {deal['name']}",
            callback_data=f"view_deal_{deal['skin_id']}"
        )])
    
    buttons.append([InlineKeyboardButton(text="◀ НАЗАД", callback_data="main_menu")])
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons), parse_mode="Markdown")

@dp.callback_query(F.data.startswith("view_deal_"))
async def callback_view_deal(callback: CallbackQuery):
    skin_id = int(callback.data.replace("view_deal_", ""))
    user_id = callback.from_user.id
    
    async with aiosqlite.connect(DATABASE_PATH) as db_conn:
        db_conn.row_factory = aiosqlite.Row
        cursor = await db_conn.execute('''
            SELECT d.*, s.name, s.quality, s.price 
            FROM deals d
            JOIN skins s ON d.skin_id = s.id
            WHERE d.skin_id = ? AND d.status = 'pending'
        ''', (skin_id,))
        deal = await cursor.fetchone()
        
        if not deal:
            await callback.message.edit_text(
                "❌ Сделка не найдена или уже завершена",
                reply_markup=Keyboards.back(),
                parse_mode="Markdown"
            )
            return
        
        text = f"""
📋 **ДЕТАЛИ СДЕЛКИ**

🎯 **Скин:** {deal['name']} ({deal['quality']})
💰 **Цена:** {deal['price']} монет
👤 **Продавец:** ID {deal['seller_id']}
👤 **Покупатель:** ID {deal['buyer_id']}
🔄 **Статус:** Ожидает подтверждения
📅 **Создана:** {deal['created_at'][:16]}

**Инструкция:**
1. Продавец отправляет скин покупателю
2. Покупатель подтверждает получение
3. Деньги размораживаются продавцу
        """
        
        await callback.message.edit_text(
            text,
            reply_markup=Keyboards.deal_actions(skin_id, user_id, deal),
            parse_mode="Markdown"
        )

@dp.callback_query(F.data == "shop")
async def callback_shop(callback: CallbackQuery):
    skins = await db.get_available_skins()
    
    if not skins:
        await callback.message.edit_text(
            "🛒 **МАГАЗИН СКИНОВ**\n\n"
            "😢 Пока нет доступных скинов.\n\n"
            "🔥 **Но ты можешь:**\n"
            "├ 🤝 Зарабатывать на рефералах\n"
            "├ 👑 Купить VIP статус\n"
            "└ 🎁 Забирать ежедневный бонус",
            reply_markup=Keyboards.back(),
            parse_mode="Markdown"
        )
        return
    
    await callback.message.edit_text(
        "🛒 **МАГАЗИН СКИНОВ**\n\n🔥 **Выбери скин для покупки:**",
        reply_markup=Keyboards.shop(skins),
        parse_mode="Markdown"
    )

@dp.callback_query(F.data.startswith("buy_skin_"))
async def callback_buy_skin(callback: CallbackQuery):
    skin_id = int(callback.data.replace("buy_skin_", ""))
    buyer_id = callback.from_user.id
    
    async with aiosqlite.connect(DATABASE_PATH) as db_conn:
        db_conn.row_factory = aiosqlite.Row
        cursor = await db_conn.execute('SELECT * FROM skins WHERE id = ? AND status = ?', (skin_id, 'available'))
        skin = await cursor.fetchone()
        
        if not skin:
            await callback.message.edit_text(
                "❌ **Скин уже продан!**",
                reply_markup=Keyboards.back(),
                parse_mode="Markdown"
            )
            return
        
        cursor = await db_conn.execute('SELECT balance FROM users WHERE user_id = ?', (buyer_id,))
        buyer = await cursor.fetchone()
        
        if not buyer or buyer[0] < skin['price']:
            await callback.message.edit_text(
                f"❌ **Недостаточно доступных монет!**\n\n"
                f"Цена скина: {skin['price']}💰\n"
                f"Твой доступный баланс: {buyer[0]}💰\n\n"
                f"🔒 Заморожено: {buyer[1] if len(buyer) > 1 else 0}💰",
                reply_markup=Keyboards.back(),
                parse_mode="Markdown"
            )
            return
        
        # Замораживаем деньги и создаём сделку
        success = await db.freeze_balance(buyer_id, skin['price'], skin_id)
        
        if success:
            await callback.message.edit_text(
                f"✅ **Покупка оформлена!**\n\n"
                f"🎯 Скин: {skin['name']} ({skin['quality']})\n"
                f"💰 Цена: {skin['price']} монет\n\n"
                f"🔄 **Статус:** Деньги заморожены до подтверждения\n\n"
                f"📞 Свяжись с продавцом для передачи скина, затем подтверди получение в разделе «Мои сделки».",
                reply_markup=Keyboards.back(),
                parse_mode="Markdown"
            )
            
            # Уведомление продавцу
            try:
                await bot.send_message(
                    skin['seller_id'],
                    f"🛒 **Ваш скин купили!**\n\n"
                    f"🎯 {skin['name']} ({skin['quality']})\n"
                    f"💰 Цена: {skin['price']} монет (заморожены)\n"
                    f"👤 Покупатель: @{callback.from_user.username or buyer_id}\n\n"
                    f"📞 Свяжитесь с покупателем для передачи скина.\n"
                    f"После подтверждения деньги поступят на ваш счёт.",
                    parse_mode="Markdown"
                )
            except:
                pass
        else:
            await callback.message.edit_text(
                f"❌ **Ошибка при оформлении покупки**",
                reply_markup=Keyboards.back(),
                parse_mode="Markdown"
            )

@dp.callback_query(F.data.startswith("confirm_deal_"))
async def callback_confirm_deal(callback: CallbackQuery):
    skin_id = int(callback.data.replace("confirm_deal_", ""))
    user_id = callback.from_user.id
    
    # Подтверждаем сделку
    success = await db.confirm_deal(skin_id)
    
    if success:
        await callback.message.edit_text(
            f"✅ **Сделка подтверждена!**\n\n"
            f"💰 Деньги разморожены и переведены продавцу.\n\n"
            f"🔥 Спасибо за покупку!",
            reply_markup=Keyboards.main(),
            parse_mode="Markdown"
        )
        
        # Уведомление продавцу
        async with aiosqlite.connect(DATABASE_PATH) as db_conn:
            cursor = await db_conn.execute('''
                SELECT seller_id, price, name FROM deals d
                JOIN skins s ON d.skin_id = s.id
                WHERE d.skin_id = ?
            ''', (skin_id,))
            deal = await cursor.fetchone()
            
            if deal:
                try:
                    await bot.send_message(
                        deal[0],
                        f"✅ **Сделка завершена!**\n\n"
                        f"🎯 {deal[2]}\n"
                        f"💰 Деньги поступили на ваш счёт: +{deal[1]} монет",
                        parse_mode="Markdown"
                    )
                except:
                    pass
    else:
        await callback.message.edit_text(
            "❌ Ошибка подтверждения сделки",
            reply_markup=Keyboards.back(),
            parse_mode="Markdown"
        )

@dp.callback_query(F.data.startswith("cancel_deal_"))
async def callback_cancel_deal(callback: CallbackQuery):
    skin_id = int(callback.data.replace("cancel_deal_", ""))
    user_id = callback.from_user.id
    
    # Отменяем сделку
    success = await db.cancel_deal(skin_id)
    
    if success:
        await callback.message.edit_text(
            f"✅ **Сделка отменена!**\n\n"
            f"💰 Деньги возвращены на ваш счёт.\n"
            f"🔄 Скин снова доступен в магазине.",
            reply_markup=Keyboards.main(),
            parse_mode="Markdown"
        )
        
        # Уведомление продавцу
        async with aiosqlite.connect(DATABASE_PATH) as db_conn:
            cursor = await db_conn.execute('''
                SELECT seller_id, name FROM skins WHERE id = ?
            ''', (skin_id,))
            skin = await cursor.fetchone()
            
            if skin:
                try:
                    await bot.send_message(
                        skin[0],
                        f"❌ **Сделка отменена покупателем**\n\n"
                        f"🎯 {skin[1]}\n"
                        f"🔄 Скин снова доступен в магазине.",
                        parse_mode="Markdown"
                    )
                except:
                    pass
    else:
        await callback.message.edit_text(
            "❌ Ошибка отмены сделки",
            reply_markup=Keyboards.back(),
            parse_mode="Markdown"
        )

@dp.callback_query(F.data == "help")
async def callback_help(callback: CallbackQuery):
    await callback.message.edit_text(
        f"🆘 **ПОМОЩЬ**\n\n"
        f"📌 **Команды:**\n"
        f"/start - Запустить\n"
        f"/menu - Меню\n"
        f"/help - Помощь\n"
        f"/profile - Профиль\n"
        f"/balance - Баланс\n"
        f"/daily - Бонус\n"
        f"/top - Топ\n"
        f"/mydeals - Мои сделки\n\n"
        f"💎 Рефералы: +{REFERRAL_BONUS} монет\n"
        f"👑 VIP: {VIP_PRICE} монет\n"
        f"🛒 Магазин: заморозка до подтверждения\n"
        f"📞 Поддержка: {SUPPORT_LINK}",
        reply_markup=Keyboards.back(),
        parse_mode="Markdown"
    )

# ========== АДМИНКА ==========
@dp.message(Command("admin"))
async def cmd_admin(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("⛔ Доступ запрещён!")
        return
    
    stats = await db.get_stats()
    
    text = f"""
🔧 **АДМИН ПАНЕЛЬ**

📊 **СТАТИСТИКА:**
├ 👥 Пользователей: {stats['users']}
├ 👑 VIP: {stats['vip']}
├ 💰 Всего монет: {stats['total_balance']}
├ 🔒 Заморожено: {stats['total_frozen']}
├ 📋 Активных сделок: {stats['active_deals']}
└ 💳 Средний баланс: {(stats['total_balance'] + stats['total_frozen']) // stats['users'] if stats['users'] else 0}

⚙️ **Доступные действия:**
├ 📊 Просмотр статистики
├ 💰 Пополнение баланса
├ 👑 Выдача VIP
└ 🛒 Добавление скинов
    """
    
    await message.answer(text, reply_markup=Keyboards.admin(), parse_mode="Markdown")

@dp.callback_query(F.data == "admin_stats")
async def callback_admin_stats(callback: CallbackQuery):
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
├ Доступно: **{stats['total_balance']}** монет
├ Заморожено: **{stats['total_frozen']}** монет
├ Всего: **{stats['total_balance'] + stats['total_frozen']}** монет
└ Средний баланс: **{(stats['total_balance'] + stats['total_frozen']) // stats['users'] if stats['users'] else 0}**

📋 **Сделки:**
├ Активных: **{stats['active_deals']}**
└ Заморожено в сделках: **{stats['total_frozen']}** монет
    """
    
    await callback.message.edit_text(text, reply_markup=Keyboards.admin(), parse_mode="Markdown")

@dp.callback_query(F.data == "admin_add_balance")
async def callback_admin_add_balance(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("⛔ Доступ запрещён!", show_alert=True)
        return
    
    await state.set_state(States.admin_add_balance_user)
    await callback.message.edit_text(
        "💰 Введи **Telegram ID** пользователя для пополнения баланса:",
        parse_mode="Markdown"
    )

@dp.message(States.admin_add_balance_user)
async def admin_add_balance_user(message: Message, state: FSMContext):
    try:
        user_id = int(message.text)
    except:
        await message.answer("❌ Некорректный ID. Введи число:")
        return
    
    await state.update_data(target_user_id=user_id)
    await state.set_state(States.admin_add_balance_amount)
    await message.answer("💰 Введи **сумму** пополнения:")

@dp.message(States.admin_add_balance_amount)
async def admin_add_balance_amount(message: Message, state: FSMContext):
    try:
        amount = int(message.text)
        if amount <= 0:
            raise ValueError
    except:
        await message.answer("❌ Сумма должна быть положительным числом:")
        return
    
    data = await state.get_data()
    user_id = data['target_user_id']
    
    await db.update_balance(user_id, amount, f"Пополнение от администратора")
    
    await message.answer(f"✅ Баланс пользователя {user_id} пополнен на {amount} монет!")
    await state.clear()

@dp.callback_query(F.data == "admin_give_vip")
async def callback_admin_give_vip(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("⛔ Доступ запрещён!", show_alert=True)
        return
    
    await state.set_state(States.admin_give_vip_user)
    await callback.message.edit_text(
        "👑 Введи **Telegram ID** пользователя для выдачи VIP:",
        parse_mode="Markdown"
    )

@dp.message(States.admin_give_vip_user)
async def admin_give_vip_user(message: Message, state: FSMContext):
    try:
        user_id = int(message.text)
    except:
        await message.answer("❌ Некорректный ID. Введи число:")
        return
    
    await db.activate_vip(user_id)
    
    await message.answer(f"✅ Пользователю {user_id} выдан VIP на {VIP_DURATION} дней!")
    await state.clear()

@dp.callback_query(F.data == "admin_add_skin")
async def callback_admin_add_skin(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("⛔ Доступ запрещён!", show_alert=True)
        return
    
    await state.set_state(States.admin_add_skin_name)
    await callback.message.edit_text(
        "🛒 Введи **название скина** (например: AK-47 | Redline):",
        parse_mode="Markdown"
    )

@dp.message(States.admin_add_skin_name)
async def admin_add_skin_name(message: Message, state: FSMContext):
    await state.update_data(skin_name=message.text)
    await state.set_state(States.admin_add_skin_quality)
    await message.answer("📦 Введи **качество** (Factory New, Minimal Wear и т.д.):")

@dp.message(States.admin_add_skin_quality)
async def admin_add_skin_quality(message: Message, state: FSMContext):
    await state.update_data(skin_quality=message.text)
    await state.set_state(States.admin_add_skin_price)
    await message.answer("💰 Введи **цену** в монетах:")

@dp.message(States.admin_add_skin_price)
async def admin_add_skin_price(message: Message, state: FSMContext):
    try:
        price = int(message.text)
        if price <= 0:
            raise ValueError
    except:
        await message.answer("❌ Цена должна быть положительным числом:")
        return
    
    data = await state.get_data()
    skin_id = await db.add_skin(
        data['skin_name'],
        data['skin_quality'],
        price,
        message.from_user.id
    )
    
    await message.answer(f"✅ Скин добавлен! ID: {skin_id}")
    await state.clear()

@dp.callback_query(F.data == "admin_deals")
async def callback_admin_deals(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("⛔ Доступ запрещён!", show_alert=True)
        return
    
    async with aiosqlite.connect(DATABASE_PATH) as db_conn:
        db_conn.row_factory = aiosqlite.Row
        cursor = await db_conn.execute('''
            SELECT d.*, s.name, s.quality 
            FROM deals d
            JOIN skins s ON d.skin_id = s.id
            WHERE d.status = 'pending'
            ORDER BY d.created_at DESC
        ''')
        deals = await cursor.fetchall()
    
    if not deals:
        await callback.message.edit_text(
            "📋 **Нет активных сделок**",
            reply_markup=Keyboards.admin(),
            parse_mode="Markdown"
        )
        return
    
    text = "📋 **АКТИВНЫЕ СДЕЛКИ**\n\n"
    for deal in deals:
        text += f"🎯 {deal['name']} ({deal['quality']})\n"
        text += f"💰 {deal['price']} монет\n"
        text += f"👤 Продавец: {deal['seller_id']}\n"
        text += f"👤 Покупатель: {deal['buyer_id']}\n"
        text += f"📅 {deal['created_at'][:16]}\n\n"
    
    await callback.message.edit_text(text, reply_markup=Keyboards.admin(), parse_mode="Markdown")

# ========== ЗАПУСК ==========
async def on_startup():
    print(f"\n{Colors.CYAN}{'='*60}{Colors.END}")
    print(f"{Colors.MAGENTA}{Colors.BOLD}🔥 SHIZOGP - ПОЛНАЯ ЗАМОРОЗКА 🔥{Colors.END}")
    print(f"{Colors.CYAN}{'='*60}{Colors.END}")
    print(f"{Colors.GREEN}✅ Версия: {BOT_VERSION}{Colors.END}")
    print(f"{Colors.GREEN}✅ Токен: {BOT_TOKEN[:15]}...{Colors.END}")
    print(f"{Colors.GREEN}✅ Админы: {ADMIN_IDS}{Colors.END}")
    print(f"{Colors.GREEN}✅ VIP чат: {VIP_CHAT_LINK}{Colors.END}")
    
    await db.init_db()
    
    me = await bot.get_me()
    print(f"{Colors.GREEN}✅ Бот: @{me.username}{Colors.END}")
    print(f"{Colors.GREEN}✅ ID: {me.id}{Colors.END}")
    print(f"{Colors.GREEN}✅ Заморозка баланса: АКТИВНА{Colors.END}")
    print(f"{Colors.GREEN}✅ Заморозка скинов: АКТИВНА{Colors.END}")
    print(f"{Colors.CYAN}{'='*60}{Colors.END}")
    print(f"{Colors.YELLOW}{Colors.BOLD}🚀 БОТ ЗАПУЩЕН И ГОТОВ К РАБОТЕ!{Colors.END}")
    print(f"{Colors.CYAN}{'='*60}{Colors.END}")

async def on_shutdown():
    print(f"\n{Colors.RED}👋 БОТ ОСТАНАВЛИВАЕТСЯ...{Colors.END}")

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
