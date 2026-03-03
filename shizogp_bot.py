#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🔥 SHIZOGP - ФИНАЛЬНАЯ РАБОЧАЯ ВЕРСИЯ
✅ Тикеты в канал
✅ Реальные платежи через Crypto Pay
✅ Все кнопки работают
"""

import os
import sys
import subprocess
import importlib.util
import json
import asyncio
import logging
import random
import string
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
    "python-dotenv==1.0.0",
    "requests==2.31.0"
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
print("🚀 Загрузка бота с реальными платежами и тикетами...")

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
import aiosqlite
import requests

try:
    from dotenv import load_dotenv
    load_dotenv()
except:
    pass

# ========== НАСТРОЙКИ ==========
BOT_TOKEN = os.getenv('BOT_TOKEN', '8498694285:AAG3Ezx7BDGciUIYAAb4UHMtFUmBYvock3w')
CRYPTOPAY_TOKEN = '540261:AAzd4sQW2mo4I8UdxardSygAc3H3CSZbZBs'
ADMIN_IDS = [int(x) for x in os.getenv('ADMIN_IDS', '2091630272,1760627021').split(',') if x]
VIP_CHAT_LINK = os.getenv('VIP_CHAT_LINK', 'https://t.me/+r3rxYlBjbTYyMDY6')
SUPPORT_LINK = os.getenv('SUPPORT_LINK', 'https://t.me/SHIZOGP_support')
CHANNEL_LINK = os.getenv('CHANNEL_LINK', 'https://t.me/+borSYGXUlKFkM2Yy')  # Твой канал для тикетов

# Цены и валюты
VIP_PRICE = 550
VIP_PRICE_RUB = 1500
USD_TO_RUB = 95
VIP_DURATION = 30
REFERRAL_BONUS = 50
START_BALANCE = 100
DAILY_BONUS = 10

# Тестовые скины
TEST_SKINS = [
    {"name": "AK-47 | Redline", "quality": "Field-Tested", "price_usd": 1500},
    {"name": "AWP | Dragon Lore", "quality": "Minimal Wear", "price_usd": 150000},
    {"name": "M4A1-S | Hyper Beast", "quality": "Factory New", "price_usd": 3000},
    {"name": "Karambit | Doppler", "quality": "Factory New", "price_usd": 8500},
    {"name": "USP-S | Kill Confirmed", "quality": "Minimal Wear", "price_usd": 2500},
    {"name": "Butterfly Knife | Fade", "quality": "Factory New", "price_usd": 12000}
]

DATABASE_PATH = "shizogp.db"
BOT_VERSION = "13.0 (РЕАЛЬНЫЕ ПЛАТЕЖИ + ТИКЕТЫ)"
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

# ========== CRYPTO PAY API ==========
class CryptoPayAPI:
    def __init__(self, token: str):
        self.token = token
        self.base_url = "https://pay.crypt.bot/api"
        self.headers = {
            "Crypto-Pay-API-Token": token,
            "Content-Type": "application/json"
        }

    async def create_invoice(self, amount: float, asset: str = 'USDT', description: str = 'Пополнение баланса') -> Dict:
        """Создание реального счёта в Crypto Pay"""
        url = f"{self.base_url}/createInvoice"
        payload = {
            "asset": asset,
            "amount": str(amount),
            "description": description,
            "paid_btn_name": "openBot",
            "paid_btn_url": f"https://t.me/{(await bot.get_me()).username}",
            "allow_comments": False,
            "allow_anonymous": False,
            "expires_in": 3600  # 1 час
        }

        try:
            response = requests.post(url, headers=self.headers, json=payload)
            data = response.json()

            if data.get('ok'):
                return {
                    'success': True,
                    'invoice_id': data['result']['invoice_id'],
                    'pay_url': data['result']['pay_url'],
                    'amount': float(data['result']['amount']),
                    'asset': data['result']['asset'],
                    'status': data['result']['status']
                }
            else:
                return {'success': False, 'error': data.get('error', 'Unknown error')}
        except Exception as e:
            logger.error(f"❌ Crypto Pay API error: {e}")
            return {'success': False, 'error': str(e)}

    async def get_invoice_status(self, invoice_id: int) -> Dict:
        """Получение статуса счёта"""
        url = f"{self.base_url}/getInvoices"
        params = {"invoice_ids": str(invoice_id)}

        try:
            response = requests.get(url, headers=self.headers, params=params)
            data = response.json()

            if data.get('ok') and data.get('result') and data['result'].get('items'):
                invoice = data['result']['items'][0]
                return {
                    'success': True,
                    'invoice_id': invoice['invoice_id'],
                    'status': invoice['status'],
                    'amount': float(invoice['amount']),
                    'asset': invoice['asset'],
                    'paid_at': invoice.get('paid_at')
                }
            else:
                return {'success': False, 'status': 'not_found'}
        except Exception as e:
            logger.error(f"❌ Crypto Pay API error: {e}")
            return {'success': False, 'error': str(e)}

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
                    balance_usd INTEGER DEFAULT 100,
                    balance_rub INTEGER DEFAULT 9500,
                    frozen_usd INTEGER DEFAULT 0,
                    frozen_rub INTEGER DEFAULT 0,
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
                    amount_usd INTEGER,
                    amount_rub INTEGER,
                    type TEXT,
                    description TEXT,
                    date TEXT DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # Крипто-платежи (реальные)
            await db.execute('''
                CREATE TABLE IF NOT EXISTS crypto_payments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    invoice_id INTEGER UNIQUE,
                    amount_usd INTEGER,
                    amount_crypto REAL,
                    asset TEXT,
                    status TEXT DEFAULT 'active',
                    pay_url TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    paid_at TEXT
                )
            ''')

            # Скины
            await db.execute('''
                CREATE TABLE IF NOT EXISTS skins (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT,
                    quality TEXT,
                    price_usd INTEGER,
                    price_rub INTEGER,
                    seller_id INTEGER,
                    buyer_id INTEGER DEFAULT NULL,
                    status TEXT DEFAULT 'available',
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # Сделки
            await db.execute('''
                CREATE TABLE IF NOT EXISTS deals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    skin_id INTEGER UNIQUE,
                    buyer_id INTEGER,
                    seller_id INTEGER,
                    price_usd INTEGER,
                    price_rub INTEGER,
                    status TEXT DEFAULT 'pending',
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    confirmed_at TEXT
                )
            ''')

            await db.commit()

            # Добавляем тестовые скины если их нет
            cursor = await db.execute('SELECT COUNT(*) FROM skins')
            count = await cursor.fetchone()
            if count[0] == 0:
                for skin in TEST_SKINS:
                    price_rub = skin['price_usd'] * USD_TO_RUB
                    await db.execute('''
                        INSERT INTO skins (name, quality, price_usd, price_rub, seller_id, status)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (skin['name'], skin['quality'], skin['price_usd'], price_rub, 2091630272, 'available'))
                await db.commit()
                print(f"{Colors.GREEN}✅ Добавлено {len(TEST_SKINS)} тестовых скинов{Colors.END}")

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
            existing = await cursor.fetchone()

            if existing:
                await db.execute('''
                    UPDATE users SET 
                        last_visit = CURRENT_TIMESTAMP,
                        username = ?,
                        full_name = ?
                    WHERE user_id = ?
                ''', (username, full_name, user_id))
                await db.commit()
                return False

            await db.execute('''
                INSERT INTO users (user_id, username, full_name, balance_usd, balance_rub, referrer_id)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (user_id, username, full_name, START_BALANCE, START_BALANCE * USD_TO_RUB, referrer_id))

            if referrer_id:
                cursor = await db.execute('SELECT user_id FROM users WHERE user_id = ?', (referrer_id,))
                if await cursor.fetchone():
                    await db.execute('''
                        UPDATE users SET balance_usd = balance_usd + ?, balance_rub = balance_rub + ?, referral_count = referral_count + 1
                        WHERE user_id = ?
                    ''', (REFERRAL_BONUS, REFERRAL_BONUS * USD_TO_RUB, referrer_id))

                    await db.execute('''
                        INSERT INTO transactions (user_id, amount_usd, amount_rub, type, description)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (referrer_id, REFERRAL_BONUS, REFERRAL_BONUS * USD_TO_RUB, 'referral', f'Бонус за реферала {user_id}'))

            await db.commit()
            return True

    async def update_balance(self, user_id: int, amount_usd: int = 0, amount_rub: int = 0, description: str = '') -> bool:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('''
                UPDATE users SET 
                    balance_usd = balance_usd + ?,
                    balance_rub = balance_rub + ?
                WHERE user_id = ?
            ''', (amount_usd, amount_rub, user_id))

            if description:
                await db.execute('''
                    INSERT INTO transactions (user_id, amount_usd, amount_rub, type, description)
                    VALUES (?, ?, ?, ?, ?)
                ''', (user_id, amount_usd, amount_rub, 'balance_change', description))

            await db.commit()
            return True

    async def add_crypto_payment(self, user_id: int, invoice_id: int, amount_usd: int, amount_crypto: float, asset: str, pay_url: str) -> bool:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('''
                INSERT INTO crypto_payments (user_id, invoice_id, amount_usd, amount_crypto, asset, pay_url, status)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (user_id, invoice_id, amount_usd, amount_crypto, asset, pay_url, 'active'))
            await db.commit()
            return True

    async def confirm_crypto_payment(self, invoice_id: int) -> bool:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute('SELECT user_id, amount_usd FROM crypto_payments WHERE invoice_id = ? AND status = ?', (invoice_id, 'active'))
            payment = await cursor.fetchone()

            if not payment:
                return False

            user_id, amount_usd = payment

            await db.execute('''
                UPDATE users SET balance_usd = balance_usd + ?, balance_rub = balance_rub + ?
                WHERE user_id = ?
            ''', (amount_usd, amount_usd * USD_TO_RUB, user_id))

            await db.execute('''
                UPDATE crypto_payments SET status = ?, paid_at = CURRENT_TIMESTAMP
                WHERE invoice_id = ?
            ''', ('paid', invoice_id))

            await db.execute('''
                INSERT INTO transactions (user_id, amount_usd, amount_rub, type, description)
                VALUES (?, ?, ?, ?, ?)
            ''', (user_id, amount_usd, amount_usd * USD_TO_RUB, 'crypto_deposit', f'Пополнение через Crypto Pay'))

            await db.commit()
            return True

    async def freeze_balance(self, user_id: int, skin_id: int, price_usd: int, price_rub: int) -> bool:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute('SELECT balance_usd, balance_rub FROM users WHERE user_id = ?', (user_id,))
            user = await cursor.fetchone()

            if not user or user[0] < price_usd or user[1] < price_rub:
                return False

            await db.execute('''
                UPDATE users SET 
                    balance_usd = balance_usd - ?,
                    balance_rub = balance_rub - ?,
                    frozen_usd = frozen_usd + ?,
                    frozen_rub = frozen_rub + ?
                WHERE user_id = ?
            ''', (price_usd, price_rub, price_usd, price_rub, user_id))

            cursor = await db.execute('SELECT seller_id FROM skins WHERE id = ?', (skin_id,))
            skin = await cursor.fetchone()

            await db.execute('''
                INSERT INTO deals (skin_id, buyer_id, seller_id, price_usd, price_rub, status)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (skin_id, user_id, skin[0], price_usd, price_rub, 'pending'))

            await db.execute('''
                UPDATE skins SET status = 'sold', buyer_id = ? WHERE id = ?
            ''', (user_id, skin_id))

            await db.commit()
            return True

    async def confirm_deal(self, skin_id: int) -> bool:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute('''
                SELECT * FROM deals WHERE skin_id = ? AND status = 'pending'
            ''', (skin_id,))
            deal = await cursor.fetchone()

            if not deal:
                return False

            await db.execute('''
                UPDATE users SET 
                    frozen_usd = frozen_usd - ?,
                    frozen_rub = frozen_rub - ?,
                    balance_usd = balance_usd + ?,
                    balance_rub = balance_rub + ?
                WHERE user_id = ?
            ''', (deal[4], deal[5], deal[4], deal[5], deal[3]))

            await db.execute('''
                UPDATE deals SET status = 'confirmed', confirmed_at = CURRENT_TIMESTAMP 
                WHERE skin_id = ?
            ''', (skin_id,))

            await db.commit()
            return True

    async def cancel_deal(self, skin_id: int) -> bool:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute('''
                SELECT * FROM deals WHERE skin_id = ? AND status = 'pending'
            ''', (skin_id,))
            deal = await cursor.fetchone()

            if not deal:
                return False

            await db.execute('''
                UPDATE users SET 
                    frozen_usd = frozen_usd - ?,
                    frozen_rub = frozen_rub - ?,
                    balance_usd = balance_usd + ?,
                    balance_rub = balance_rub + ?
                WHERE user_id = ?
            ''', (deal[4], deal[5], deal[4], deal[5], deal[2]))

            await db.execute('''
                UPDATE skins SET status = 'available', buyer_id = NULL WHERE id = ?
            ''', (skin_id,))

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

            cursor = await db.execute('SELECT SUM(balance_usd) FROM users')
            total_usd = (await cursor.fetchone())[0] or 0

            cursor = await db.execute('SELECT SUM(balance_rub) FROM users')
            total_rub = (await cursor.fetchone())[0] or 0

            cursor = await db.execute('SELECT SUM(frozen_usd) FROM users')
            frozen_usd = (await cursor.fetchone())[0] or 0

            cursor = await db.execute('SELECT SUM(frozen_rub) FROM users')
            frozen_rub = (await cursor.fetchone())[0] or 0

            cursor = await db.execute('SELECT COUNT(*) FROM deals WHERE status = ?', ('pending',))
            active_deals = (await cursor.fetchone())[0]

            cursor = await db.execute('SELECT COUNT(*) FROM crypto_payments WHERE status = ?', ('active',))
            active_payments = (await cursor.fetchone())[0]

            return {
                'users': users,
                'vip': vip,
                'total_usd': total_usd,
                'total_rub': total_rub,
                'frozen_usd': frozen_usd,
                'frozen_rub': frozen_rub,
                'active_deals': active_deals,
                'active_payments': active_payments
            }

    async def get_top_users(self, limit: int = 10) -> List[Dict]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute('''
                SELECT user_id, username, balance_usd, frozen_usd, referral_count 
                FROM users 
                ORDER BY balance_usd DESC 
                LIMIT ?
            ''', (limit,))
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def add_skin(self, name: str, quality: str, price_usd: int, seller_id: int) -> int:
        price_rub = price_usd * USD_TO_RUB
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute('''
                INSERT INTO skins (name, quality, price_usd, price_rub, seller_id, status)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (name, quality, price_usd, price_rub, seller_id, 'available'))
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

# ========== ИНИЦИАЛИЗАЦИЯ ==========
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())
db = Database()
crypto = CryptoPayAPI(CRYPTOPAY_TOKEN)

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
                InlineKeyboardButton(text="💳 КРИПТО", callback_data="crypto_menu")
            ],
            [
                InlineKeyboardButton(text="📢 КАНАЛ", url=CHANNEL_LINK),
                InlineKeyboardButton(text="ℹ️ ПОМОЩЬ", callback_data="help")
            ]
        ]
        return InlineKeyboardMarkup(inline_keyboard=buttons)

    @staticmethod
    def back() -> InlineKeyboardMarkup:
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀ НАЗАД В МЕНЮ", callback_data="main_menu")]
        ])

    @staticmethod
    def crypto_menu() -> InlineKeyboardMarkup:
        buttons = [
            [InlineKeyboardButton(text="₿ Bitcoin (BTC)", callback_data="crypto_btc")],
            [InlineKeyboardButton(text="⟠ Ethereum (ETH)", callback_data="crypto_eth")],
            [InlineKeyboardButton(text="💵 Tether (USDT)", callback_data="crypto_usdt")],
            [InlineKeyboardButton(text="⬤ Toncoin (TON)", callback_data="crypto_ton")],
            [InlineKeyboardButton(text="◀ НАЗАД", callback_data="main_menu")]
        ]
        return InlineKeyboardMarkup(inline_keyboard=buttons)

    @staticmethod
    def crypto_amounts(asset: str) -> InlineKeyboardMarkup:
        amounts = [10, 25, 50, 100, 250, 500, 1000]
        buttons = []
        row = []
        for i, amount in enumerate(amounts):
            row.append(InlineKeyboardButton(text=f"{amount}$", callback_data=f"crypto_pay_{asset}_{amount}"))
            if (i + 1) % 4 == 0:
                buttons.append(row)
                row = []
        if row:
            buttons.append(row)
        buttons.append([InlineKeyboardButton(text="◀ НАЗАД", callback_data="crypto_menu")])
        return InlineKeyboardMarkup(inline_keyboard=buttons)

    @staticmethod
    def vip(is_vip: bool = False) -> InlineKeyboardMarkup:
        if is_vip:
            return InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="👑 ВОЙТИ В VIP ЧАТ", url=VIP_CHAT_LINK)],
                [InlineKeyboardButton(text="◀ НАЗАД", callback_data="main_menu")]
            ])
        else:
            return InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=f"💎 КУПИТЬ VIP ({VIP_PRICE}$ / {VIP_PRICE_RUB}₽)", callback_data="buy_vip")],
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
            [InlineKeyboardButton(text="💳 КРИПТО-ПЛАТЕЖИ", callback_data="admin_payments")],
            [InlineKeyboardButton(text="◀ НАЗАД", callback_data="main_menu")]
        ]
        return InlineKeyboardMarkup(inline_keyboard=buttons)

    @staticmethod
    def shop(skins: List[Dict]) -> InlineKeyboardMarkup:
        buttons = []
        for skin in skins:
            buttons.append([InlineKeyboardButton(
                text=f"{skin['name']} ({skin['quality']}) - {skin['price_usd']}$ / {skin['price_rub']}₽",
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
├ 💰 Доступно: **{user['balance_usd']}$** / **{user['balance_rub']}₽**
├ 🔒 Заморожено: **{user['frozen_usd']}$** / **{user['frozen_rub']}₽**
├ 👥 Рефералов: **{user['referral_count']}**
└ 👑 VIP: {"✅" if is_vip else "❌"}

💳 **КРИПТО-ПЛАТЕЖИ ЧЕРЕЗ @CryptoBot:**
├ ₿ BTC | ⟠ ETH | 💵 USDT | ⬤ TON
├ Мгновенное зачисление
└ Без комиссии

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

💳 **Крипто-платежи через @CryptoBot:**
├ BTC, ETH, USDT, TON
├ Мгновенное зачисление
└ Без комиссии

💎 **Реферальная система:**
За каждого друга ты получаешь **+{REFERRAL_BONUS}$**!

👑 **VIP статус:**
├ Стоимость: **{VIP_PRICE}$** / **{VIP_PRICE_RUB}₽**
├ Длительность: **{VIP_DURATION}** дней
├ Доступ к закрытому VIP чату
└ Удвоенный реферальный бонус

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
├ Доступно USD: **{user['balance_usd']}$**
├ Доступно RUB: **{user['balance_rub']}₽**
├ Заморожено USD: **{user['frozen_usd']}$**
├ Заморожено RUB: **{user['frozen_rub']}₽**
├ Всего USD: **{user['balance_usd'] + user['frozen_usd']}$**
├ Всего RUB: **{user['balance_rub'] + user['frozen_rub']}₽**
├ 👥 Рефералов: **{user['referral_count']}**
└ Заработано: **{user['referral_count'] * REFERRAL_BONUS}$**

👑 **VIP статус:**
├ Статус: {"✅ АКТИВЕН" if is_vip else "❌ НЕ АКТИВЕН"}
{f"├ Действует до: {user['vip_until'][:10]}" if is_vip and user['vip_until'] else ""}
└ Стоимость: {VIP_PRICE}$ / {VIP_PRICE_RUB}₽
    """

    await message.answer(text, reply_markup=Keyboards.back(), parse_mode="Markdown")

@dp.message(Command("balance"))
async def cmd_balance(message: Message):
    user_id = message.from_user.id
    user = await db.get_user(user_id)

    await message.answer(
        f"💰 **ТВОЙ БАЛАНС**\n\n"
        f"💵 Доллары: **{user['balance_usd']}$**\n"
        f"💰 Рубли: **{user['balance_rub']}₽**\n"
        f"🔒 Заморожено USD: **{user['frozen_usd']}$**\n"
        f"🔒 Заморожено RUB: **{user['frozen_rub']}₽**\n"
        f"👥 Рефералов: **{user['referral_count']}**\n\n"
        f"До VIP: **{max(0, VIP_PRICE - user['balance_usd'] - user['frozen_usd'])}$**",
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
            UPDATE users SET 
                balance_usd = balance_usd + ?,
                balance_rub = balance_rub + ?,
                daily_bonus = ? 
            WHERE user_id = ?
        ''', (DAILY_BONUS, DAILY_BONUS * USD_TO_RUB, today, user_id))
        await db_conn.commit()

    await message.answer(
        f"🎁 **ЕЖЕДНЕВНЫЙ БОНУС**\n\n"
        f"Ты получил **+{DAILY_BONUS}$** / **+{DAILY_BONUS * USD_TO_RUB}₽**!\n"
        f"💰 Новый баланс: **{user['balance_usd'] + DAILY_BONUS}$** / **{user['balance_rub'] + DAILY_BONUS * USD_TO_RUB}₽**",
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
        total = user['balance_usd'] + user['frozen_usd']
        text += f"{medal} **{i}.** {username} — {total}$ (реф: {user['referral_count']})\n"

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
        text += f"💰 Цена: {deal['price_usd']}$ / {deal['price_rub']}₽\n"
        text += f"👤 Ты: {role}\n\n"

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
        f"💵 Доллары: **{user['balance_usd']}$**\n"
        f"💰 Рубли: **{user['balance_rub']}₽**\n"
        f"🔒 Заморожено: **{user['frozen_usd']}$** / **{user['frozen_rub']}₽**\n"
        f"👥 Рефералов: **{user['referral_count']}**",
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
├ Заработано: **{user['referral_count'] * REFERRAL_BONUS}$**
└ Бонус за друга: **+{REFERRAL_BONUS}$** / **+{REFERRAL_BONUS * USD_TO_RUB}₽**

🔗 **Твоя ссылка:**
`{ref_link}`

📤 **Как зарабатывать:**
1. Отправь ссылку друзьям
2. Друг переходит по ссылке
3. Ты получаешь **+{REFERRAL_BONUS}$**
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
        total_usd = user['balance_usd'] + user['frozen_usd']
        total_rub = user['balance_rub'] + user['frozen_rub']
        text = f"""
👑 **VIP СТАТУС**

💰 **Стоимость:**
├ {VIP_PRICE}$ (доллары)
└ {VIP_PRICE_RUB}₽ (рубли)

📅 **Длительность:** {VIP_DURATION} дней

🎁 **Что даёт VIP:**
├ 🔥 Доступ в закрытый VIP чат
├ 💰 Двойной бонус за рефералов
├ 🎁 Эксклюзивные предложения
├ ⚡ Приоритетная поддержка
├ 🚀 Ранний доступ к новым скинам
└ 👑 Статус и уважение

📊 **Твой баланс:**
├ {total_usd}$ (всего)
└ {total_rub}₽ (всего)

{"✅ **Можешь купить!**" if total_usd >= VIP_PRICE or total_rub >= VIP_PRICE_RUB else f"❌ **Нужно ещё {max(0, VIP_PRICE - total_usd)}$ или {max(0, VIP_PRICE_RUB - total_rub)}₽**"}
        """

    await callback.message.edit_text(
        text,
        reply_markup=Keyboards.vip(is_vip),
        parse_mode="Markdown"
    )

@dp.callback_query(F.data == "buy_vip")
async def callback_buy_vip(callback: CallbackQuery):
    user_id = callback.from_user.id
    user = await db.get_user(user_id)

    total_usd = user['balance_usd'] + user['frozen_usd']
    total_rub = user['balance_rub'] + user['frozen_rub']

    if total_usd >= VIP_PRICE or total_rub >= VIP_PRICE_RUB:
        if user['balance_usd'] >= VIP_PRICE:
            await db.update_balance(user_id, -VIP_PRICE, -VIP_PRICE * USD_TO_RUB, "Покупка VIP (USD)")
        elif user['balance_rub'] >= VIP_PRICE_RUB:
            await db.update_balance(user_id, 0, -VIP_PRICE_RUB, "Покупка VIP (RUB)")
        else:
            await callback.message.edit_text(
                f"❌ **У тебя недостаточно доступных средств!**\n\n"
                f"Доступно: {user['balance_usd']}$ / {user['balance_rub']}₽\n"
                f"Заморожено: {user['frozen_usd']}$ / {user['frozen_rub']}₽\n\n"
                f"Дождись завершения текущих сделок.",
                reply_markup=Keyboards.back(),
                parse_mode="Markdown"
            )
            return

        await db.activate_vip(user_id)

        try:
            await bot.send_message(
                user_id,
                f"👑 **ТВОЯ ССЫЛКА В VIP ЧАТ**\n\n"
                f"{VIP_CHAT_LINK}\n\n"
                f"🔗 **Сохрани её, чтобы не потерять!**",
                parse_mode="Markdown"
            )
            logger.info(f"✅ VIP ссылка отправлена пользователю {user_id}")
        except Exception as e:
            logger.error(f"❌ Ошибка отправки VIP ссылки: {e}")

        await callback.message.edit_text(
            f"✅ **VIP УСПЕШНО АКТИВИРОВАН!**\n\n"
            f"📅 Действует: {VIP_DURATION} дней\n\n"
            f"👑 **Ссылка на чат отправлена в личные сообщения!**",
            reply_markup=Keyboards.vip(True),
            parse_mode="Markdown"
        )

        for admin_id in ADMIN_IDS:
            try:
                await bot.send_message(
                    admin_id,
                    f"👑 Пользователь @{callback.from_user.username or user_id} купил VIP!\n"
                    f"💰 Баланс был: {total_usd}$ / {total_rub}₽"
                )
            except:
                pass
    else:
        need_usd = VIP_PRICE - total_usd
        need_rub = VIP_PRICE_RUB - total_rub
        await callback.message.edit_text(
            f"❌ **Недостаточно средств!**\n\n"
            f"Твой баланс: {total_usd}$ / {total_rub}₽\n"
            f"Нужно ещё: {need_usd}$ или {need_rub}₽\n\n"
            f"🤝 **Приглашай друзей или пополни через крипту!**",
            reply_markup=Keyboards.back(),
            parse_mode="Markdown"
        )

# ========== КРИПТО-ПЛАТЕЖИ (РЕАЛЬНЫЕ) ==========
@dp.callback_query(F.data == "crypto_menu")
async def callback_crypto_menu(callback: CallbackQuery):
    """Меню выбора криптовалюты"""
    await callback.message.edit_text(
        "💳 **КРИПТО-ПЛАТЕЖИ ЧЕРЕЗ @CryptoBot**\n\n"
        "Выбери валюту для пополнения:\n\n"
        "₿ **BTC** - Bitcoin\n"
        "⟠ **ETH** - Ethereum\n"
        "💵 **USDT** - Tether (стабильная монета)\n"
        "⬤ **TON** - Toncoin\n\n"
        "✅ Мгновенное зачисление\n"
        "✅ Без комиссии\n"
        "✅ Через официального бота @CryptoBot",
        reply_markup=Keyboards.crypto_menu(),
        parse_mode="Markdown"
    )

@dp.callback_query(F.data.startswith("crypto_"))
async def callback_crypto_select(callback: CallbackQuery):
    """Выбор валюты"""
    asset = callback.data.split("_")[1].upper()
    asset_names = {
        'BTC': 'Bitcoin',
        'ETH': 'Ethereum',
        'USDT': 'Tether',
        'TON': 'Toncoin'
    }
    name = asset_names.get(asset, asset)

    await callback.message.edit_text(
        f"💳 **ПОПОЛНЕНИЕ В {name} ({asset})**\n\n"
        f"Выбери сумму в долларах США:",
        reply_markup=Keyboards.crypto_amounts(asset),
        parse_mode="Markdown"
    )

@dp.callback_query(F.data.startswith("crypto_pay_"))
async def callback_crypto_pay(callback: CallbackQuery):
    """Создание реального платежа в Crypto Pay"""
    _, _, asset, amount_str = callback.data.split("_")
    amount = int(amount_str)
    user_id = callback.from_user.id

    await callback.message.edit_text(
        f"⏳ **Создаю платёж...**\n\n"
        f"Пожалуйста, подожди.",
        parse_mode="Markdown"
    )

    # Создаём реальный счёт в Crypto Pay
    description = f"Пополнение баланса SHIZOGP на {amount}$"
    result = await crypto.create_invoice(amount, asset, description)

    if not result['success']:
        await callback.message.edit_text(
            f"❌ **Ошибка создания платежа**\n\n"
            f"{result.get('error', 'Неизвестная ошибка')}\n\n"
            f"Попробуй позже или выбери другую валюту.",
            reply_markup=Keyboards.crypto_menu(),
            parse_mode="Markdown"
        )
        return

    # Сохраняем платёж в БД
    await db.add_crypto_payment(
        user_id,
        result['invoice_id'],
        amount,
        result['amount'],
        result['asset'],
        result['pay_url']
    )

    text = f"""
💎 **КРИПТО-ПЛАТЁЖ СОЗДАН**

💰 **Сумма:** {amount}$
🪙 **Валюта:** {asset}
📤 **К оплате:** {result['amount']} {asset}

🔗 **Ссылка для оплаты:**
{result['pay_url']}

⏱ **Счёт действителен 1 час**

📋 **Инструкция:**
1. Нажми на кнопку «ОПЛАТИТЬ»
2. Оплати через @CryptoBot
3. После оплаты нажми «ПРОВЕРИТЬ»
4. Средства зачислятся автоматически

⚠️ **Не закрывай это окно до оплаты!**
    """

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 ОПЛАТИТЬ", url=result['pay_url'])],
        [InlineKeyboardButton(text="🔄 ПРОВЕРИТЬ ОПЛАТУ", callback_data=f"crypto_check_{result['invoice_id']}")],
        [InlineKeyboardButton(text="◀ НАЗАД", callback_data="crypto_menu")]
    ])

    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")

@dp.callback_query(F.data.startswith("crypto_check_"))
async def callback_crypto_check(callback: CallbackQuery):
    """Проверка статуса реального платежа"""
    invoice_id = int(callback.data.replace("crypto_check_", ""))

    result = await crypto.get_invoice_status(invoice_id)

    if not result['success']:
        await callback.answer("❌ Не удалось проверить статус", show_alert=True)
        return

    if result['status'] == 'paid':
        # Подтверждаем платёж в БД
        if await db.confirm_crypto_payment(invoice_id):
            await callback.message.edit_text(
                f"✅ **ПЛАТЁЖ ПОДТВЕРЖДЁН!**\n\n"
                f"Средства зачислены на твой баланс.\n"
                f"💰 Сумма: {result['amount']} {result['asset']}\n\n"
                f"Можешь проверить в разделе «Баланс».",
                reply_markup=Keyboards.main(),
                parse_mode="Markdown"
            )

            # Уведомление админам
            for admin_id in ADMIN_IDS:
                try:
                    await bot.send_message(
                        admin_id,
                        f"💳 Пользователь @{callback.from_user.username or callback.from_user.id} пополнил баланс через Crypto Pay!\n"
                        f"💰 Сумма: {result['amount']} {result['asset']}"
                    )
                except:
                    pass
        else:
            await callback.message.edit_text(
                f"❌ **Ошибка при зачислении средств**\n\n"
                f"Обратись в поддержку: {SUPPORT_LINK}",
                reply_markup=Keyboards.main(),
                parse_mode="Markdown"
            )
    elif result['status'] == 'active':
        await callback.answer("⏳ Платёж ещё не оплачен", show_alert=True)
    else:
        await callback.answer(f"❌ Статус: {result['status']}", show_alert=True)

# ========== ПРОФИЛЬ ==========
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
├ Доступно USD: **{user['balance_usd']}$**
├ Доступно RUB: **{user['balance_rub']}₽**
├ Заморожено USD: **{user['frozen_usd']}$**
├ Заморожено RUB: **{user['frozen_rub']}₽**
├ Всего USD: **{user['balance_usd'] + user['frozen_usd']}$**
├ Всего RUB: **{user['balance_rub'] + user['frozen_rub']}₽**
├ 👥 Рефералов: **{user['referral_count']}**
└ Заработано: **{user['referral_count'] * REFERRAL_BONUS}$**

👑 **VIP статус:**
├ Статус: {"✅ АКТИВЕН" if is_vip else "❌ НЕ АКТИВЕН"}
{f"├ Действует до: {user['vip_until'][:10]}" if is_vip and user['vip_until'] else ""}
└ Стоимость: {VIP_PRICE}$ / {VIP_PRICE_RUB}₽
    """

    await callback.message.edit_text(
        text,
        reply_markup=Keyboards.back(),
        parse_mode="Markdown"
    )

# ========== ДЕЙЛИК ==========
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
            UPDATE users SET 
                balance_usd = balance_usd + ?,
                balance_rub = balance_rub + ?,
                daily_bonus = ? 
            WHERE user_id = ?
        ''', (DAILY_BONUS, DAILY_BONUS * USD_TO_RUB, today, user_id))
        await db_conn.commit()

    await callback.message.edit_text(
        f"🎁 **ЕЖЕДНЕВНЫЙ БОНУС**\n\n"
        f"Ты получил **+{DAILY_BONUS}$** / **+{DAILY_BONUS * USD_TO_RUB}₽**!\n"
        f"💰 Новый баланс: **{user['balance_usd'] + DAILY_BONUS}$** / **{user['balance_rub'] + DAILY_BONUS * USD_TO_RUB}₽**",
        reply_markup=Keyboards.back(),
        parse_mode="Markdown"
    )

# ========== ТОП ==========
@dp.callback_query(F.data == "top")
async def callback_top(callback: CallbackQuery):
    top_users = await db.get_top_users(10)

    text = "🏆 **ТОП-10 ПОЛЬЗОВАТЕЛЕЙ**\n\n"

    for i, user in enumerate(top_users, 1):
        medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "👤"
        username = user['username'] or f"ID {user['user_id']}"
        total = user['balance_usd'] + user['frozen_usd']
        text += f"{medal} **{i}.** {username} — {total}$ (реф: {user['referral_count']})\n"

    await callback.message.edit_text(text, reply_markup=Keyboards.back(), parse_mode="Markdown")

# ========== МОИ СДЕЛКИ ==========
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
        text += f"💰 {deal['price_usd']}$ / {deal['price_rub']}₽ | 👤 {role}\n\n"
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
            SELECT d.*, s.name, s.quality, s.price_usd, s.price_rub
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
💰 **Цена:** {deal['price_usd']}$ / {deal['price_rub']}₽
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

# ========== МАГАЗИН ==========
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
            "├ 💎 Пополнить через крипту\n"
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

        cursor = await db_conn.execute('SELECT balance_usd, balance_rub FROM users WHERE user_id = ?', (buyer_id,))
        buyer = await cursor.fetchone()

        if not buyer or buyer[0] < skin['price_usd'] or buyer[1] < skin['price_rub']:
            await callback.message.edit_text(
                f"❌ **Недостаточно доступных средств!**\n\n"
                f"Цена скина: {skin['price_usd']}$ / {skin['price_rub']}₽\n"
                f"Твой доступный баланс: {buyer[0]}$ / {buyer[1]}₽\n\n"
                f"💎 Пополни через крипту или дождись завершения сделок.",
                reply_markup=Keyboards.back(),
                parse_mode="Markdown"
            )
            return

        success = await db.freeze_balance(buyer_id, skin_id, skin['price_usd'], skin['price_rub'])

        if success:
            await callback.message.edit_text(
                f"✅ **Покупка оформлена!**\n\n"
                f"🎯 Скин: {skin['name']} ({skin['quality']})\n"
                f"💰 Цена: {skin['price_usd']}$ / {skin['price_rub']}₽\n\n"
                f"🔄 **Статус:** Деньги заморожены до подтверждения\n\n"
                f"📞 Свяжись с продавцом для передачи скина, затем подтверди получение в разделе «Мои сделки».",
                reply_markup=Keyboards.back(),
                parse_mode="Markdown"
            )

            try:
                await bot.send_message(
                    skin['seller_id'],
                    f"🛒 **Ваш скин купили!**\n\n"
                    f"🎯 {skin['name']} ({skin['quality']})\n"
                    f"💰 Цена: {skin['price_usd']}$ / {skin['price_rub']}₽ (заморожены)\n"
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

    success = await db.confirm_deal(skin_id)

    if success:
        await callback.message.edit_text(
            f"✅ **Сделка подтверждена!**\n\n"
            f"💰 Деньги разморожены и переведены продавцу.\n\n"
            f"🔥 Спасибо за покупку!",
            reply_markup=Keyboards.main(),
            parse_mode="Markdown"
        )

        async with aiosqlite.connect(DATABASE_PATH) as db_conn:
            cursor = await db_conn.execute('''
                SELECT seller_id, price_usd, price_rub, name FROM deals d
                JOIN skins s ON d.skin_id = s.id
                WHERE d.skin_id = ?
            ''', (skin_id,))
            deal = await cursor.fetchone()

            if deal:
                try:
                    await bot.send_message(
                        deal[0],
                        f"✅ **Сделка завершена!**\n\n"
                        f"🎯 {deal[3]}\n"
                        f"💰 Деньги поступили на ваш счёт: +{deal[1]}$ / +{deal[2]}₽",
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

    success = await db.cancel_deal(skin_id)

    if success:
        await callback.message.edit_text(
            f"✅ **Сделка отменена!**\n\n"
            f"💰 Деньги возвращены на ваш счёт.\n"
            f"🔄 Скин снова доступен в магазине.",
            reply_markup=Keyboards.main(),
            parse_mode="Markdown"
        )

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

# ========== ПОМОЩЬ ==========
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
        f"💎 Рефералы: +{REFERRAL_BONUS}$\n"
        f"👑 VIP: {VIP_PRICE}$ / {VIP_PRICE_RUB}₽\n"
        f"🛒 Магазин: {len(TEST_SKINS)} скинов\n"
        f"💳 Крипта: BTC, ETH, USDT, TON через @CryptoBot\n"
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
├ 💰 Всего USD: {stats['total_usd']}$
├ 💰 Всего RUB: {stats['total_rub']}₽
├ 🔒 Заморожено USD: {stats['frozen_usd']}$
├ 🔒 Заморожено RUB: {stats['frozen_rub']}₽
├ 📋 Активных сделок: {stats['active_deals']}
├ 💳 Активных платежей: {stats['active_payments']}
└ 💳 Средний баланс: {(stats['total_usd'] + stats['frozen_usd']) // stats['users'] if stats['users'] else 0}$

⚙️ **Доступные действия:**
├ 📊 Просмотр статистики
├ 💰 Пополнение баланса
├ 👑 Выдача VIP
├ 🛒 Добавление скинов
├ 📋 Активные сделки
└ 💳 Крипто-платежи
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

💰 **Финансы (USD):**
├ Доступно: **{stats['total_usd']}$**
├ Заморожено: **{stats['frozen_usd']}$**
├ Всего: **{stats['total_usd'] + stats['frozen_usd']}$**
└ Средний: **{(stats['total_usd'] + stats['frozen_usd']) // stats['users'] if stats['users'] else 0}$**

💰 **Финансы (RUB):**
├ Доступно: **{stats['total_rub']}₽**
├ Заморожено: **{stats['frozen_rub']}₽**
├ Всего: **{stats['total_rub'] + stats['frozen_rub']}₽**
└ Средний: **{(stats['total_rub'] + stats['frozen_rub']) // stats['users'] if stats['users'] else 0}₽**

📋 **Сделки:**
├ Активных: **{stats['active_deals']}**
└ Заморожено в сделках: **{stats['frozen_usd']}$** / **{stats['frozen_rub']}₽**

💳 **Крипто-платежи:**
├ Активных: **{stats['active_payments']}**
└ Ожидают оплаты
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
    await message.answer("💰 Введи **сумму в USD** для пополнения:")

@dp.message(States.admin_add_balance_amount)
async def admin_add_balance_amount(message: Message, state: FSMContext):
    try:
        amount_usd = int(message.text)
        if amount_usd <= 0:
            raise ValueError
    except:
        await message.answer("❌ Сумма должна быть положительным числом:")
        return

    data = await state.get_data()
    user_id = data['target_user_id']

    amount_rub = amount_usd * USD_TO_RUB
    await db.update_balance(user_id, amount_usd, amount_rub, f'Пополнение от администратора')

    await message.answer(f"✅ Баланс пользователя {user_id} пополнен на {amount_usd}$ / {amount_rub}₽!")
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

# ========== АДМИНСКАЯ ФУНКЦИЯ ДОБАВЛЕНИЯ СКИНА С ТИКЕТОМ В КАНАЛ ==========
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
    await message.answer("💰 Введи **цену в USD**:")

@dp.message(States.admin_add_skin_price)
async def admin_add_skin_price(message: Message, state: FSMContext):
    try:
        price_usd = int(message.text)
        if price_usd <= 0:
            raise ValueError
    except:
        await message.answer("❌ Цена должна быть положительным числом:")
        return

    data = await state.get_data()
    skin_id = await db.add_skin(
        data['skin_name'],
        data['skin_quality'],
        price_usd,
        message.from_user.id
    )

    # Отправляем уведомление в канал (тикет)
    try:
        await bot.send_message(
            chat_id=CHANNEL_LINK,  # ID канала или ссылка-приглашение
            text=f"🆕 **НОВЫЙ СКИН В МАГАЗИНЕ!**\n\n"
                 f"🎯 **Название:** {data['skin_name']}\n"
                 f"📦 **Качество:** {data['skin_quality']}\n"
                 f"💰 **Цена:** {price_usd}$ / {price_usd * USD_TO_RUB}₽\n"
                 f"👤 **Добавил:** @{message.from_user.username or message.from_user.first_name}\n\n"
                 f"👉 Переходи в бота @{BOT_NAME}_bot и покупай!",
            parse_mode="Markdown"
        )
        logger.info(f"✅ Тикет о новом скине отправлен в канал {CHANNEL_LINK}")
    except Exception as e:
        logger.error(f"❌ Не удалось отправить тикет в канал: {e}")

    await message.answer(f"✅ Скин добавлен! ID: {skin_id}\n📢 Уведомление отправлено в канал.")
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
        text += f"💰 {deal['price_usd']}$ / {deal['price_rub']}₽\n"
        text += f"👤 Продавец: {deal['seller_id']}\n"
        text += f"👤 Покупатель: {deal['buyer_id']}\n"
        text += f"📅 {deal['created_at'][:16]}\n\n"

    await callback.message.edit_text(text, reply_markup=Keyboards.admin(), parse_mode="Markdown")

@dp.callback_query(F.data == "admin_payments")
async def callback_admin_payments(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("⛔ Доступ запрещён!", show_alert=True)
        return

    async with aiosqlite.connect(DATABASE_PATH) as db_conn:
        db_conn.row_factory = aiosqlite.Row
        cursor = await db_conn.execute('''
            SELECT * FROM crypto_payments WHERE status = 'active' ORDER BY created_at DESC LIMIT 20
        ''')
        payments = await cursor.fetchall()

    if not payments:
        await callback.message.edit_text(
            "📭 **Нет активных крипто-платежей**",
            reply_markup=Keyboards.admin(),
            parse_mode="Markdown"
        )
        return

    text = "💳 **АКТИВНЫЕ КРИПТО-ПЛАТЕЖИ**\n\n"
    for p in payments:
        text += f"🆔 Invoice: `{p['invoice_id']}`\n"
        text += f"👤 Пользователь: {p['user_id']}\n"
        text += f"💰 Сумма: {p['amount_usd']}$ / {p['amount_crypto']} {p['asset']}\n"
        text += f"📅 {p['created_at'][:16]}\n\n"

    await callback.message.edit_text(text, reply_markup=Keyboards.admin(), parse_mode="Markdown")

# ========== ЗАПУСК ==========
async def on_startup():
    print(f"\n{Colors.CYAN}{'='*60}{Colors.END}")
    print(f"{Colors.MAGENTA}{Colors.BOLD}🔥 SHIZOGP - РЕАЛЬНЫЕ ПЛАТЕЖИ + ТИКЕТЫ 🔥{Colors.END}")
    print(f"{Colors.CYAN}{'='*60}{Colors.END}")
    print(f"{Colors.GREEN}✅ Версия: {BOT_VERSION}{Colors.END}")
    print(f"{Colors.GREEN}✅ Токен: {BOT_TOKEN[:15]}...{Colors.END}")
    print(f"{Colors.GREEN}✅ Crypto Pay Token: {CRYPTOPAY_TOKEN[:10]}...{Colors.END}")
    print(f"{Colors.GREEN}✅ Админы: {ADMIN_IDS}{Colors.END}")
    print(f"{Colors.GREEN}✅ VIP чат: {VIP_CHAT_LINK}{Colors.END}")
    print(f"{Colors.GREEN}✅ Канал для тикетов: {CHANNEL_LINK}{Colors.END}")
    print(f"{Colors.GREEN}✅ Тестовые скины: {len(TEST_SKINS)}{Colors.END}")

    await db.init_db()

    me = await bot.get_me()
    print(f"{Colors.GREEN}✅ Бот: @{me.username}{Colors.END}")
    print(f"{Colors.GREEN}✅ ID: {me.id}{Colors.END}")
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
