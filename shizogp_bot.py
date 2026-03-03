#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🔥 SHIZOGP - P2P ЭСКРОУ БОТ С ТИКЕТАМИ
✅ Выставление скинов
✅ Тикеты в канал
✅ Оплата через @CryptoBot
✅ Чат покупателя и продавца
✅ Эскроу + Арбитраж
"""

import os
import sys
import asyncio
import logging
import random
import string
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any

# ========== УСТАНОВКА ЗАВИСИМОСТЕЙ ==========
try:
    from aiogram import Bot, Dispatcher, types, F
    from aiogram.filters import Command
    from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
    from aiogram.fsm.context import FSMContext
    from aiogram.fsm.state import State, StatesGroup
    from aiogram.fsm.storage.memory import MemoryStorage
    import aiosqlite
    import requests
except ImportError:
    print("🔄 Устанавливаю зависимости...")
    os.system("pip install aiogram==3.4.1 aiosqlite==0.19.0 requests")
    from aiogram import Bot, Dispatcher, types, F
    from aiogram.filters import Command
    from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
    from aiogram.fsm.context import FSMContext
    from aiogram.fsm.state import State, StatesGroup
    from aiogram.fsm.storage.memory import MemoryStorage
    import aiosqlite
    import requests

# ========== НАСТРОЙКИ ==========
BOT_TOKEN = os.getenv('BOT_TOKEN', '8498694285:AAG3Ezx7BDGciUIYAAb4UHMtFUmBYvock3w')
CRYPTOPAY_TOKEN = '540261:AAzd4sQW2mo4I8UdxardSygAc3H3CSZbZBs'
ADMIN_IDS = [int(x) for x in os.getenv('ADMIN_IDS', '2091630272,1760627021').split(',') if x]
CHANNEL_LINK = os.getenv('CHANNEL_LINK', 'https://t.me/+borSYGXUlKFkM2Yy')
SUPPORT_LINK = os.getenv('SUPPORT_LINK', 'https://t.me/SHIZOGP_support')

# Настройки платформы
PLATFORM_FEE = 0.5  # 0.5% комиссия
MIN_PRICE = 10  # Минимальная цена в USDT
MAX_PRICE = 10000  # Максимальная цена

DATABASE_PATH = "shizogp.db"
BOT_VERSION = "15.0 (P2P ЭСКРОУ + ТИКЕТЫ)"
BOT_NAME = "SHIZOGP"

# ========== ЛОГИРОВАНИЕ ==========
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ========== ЦВЕТА ==========
class Colors:
    RED = '\033[91m'; GREEN = '\033[92m'; YELLOW = '\033[93m'
    BLUE = '\033[94m'; MAGENTA = '\033[95m'; CYAN = '\033[96m'
    BOLD = '\033[1m'; END = '\033[0m'

# ========== CRYPTO PAY API ==========
class CryptoPayAPI:
    def __init__(self, token: str):
        self.token = token
        self.base_url = "https://pay.crypt.bot/api"
        self.headers = {"Crypto-Pay-API-Token": token, "Content-Type": "application/json"}

    async def create_invoice(self, amount: float, asset: str = 'USDT', description: str = '') -> Dict:
        url = f"{self.base_url}/createInvoice"
        payload = {
            "asset": asset,
            "amount": str(amount),
            "description": description,
            "paid_btn_name": "openBot",
            "paid_btn_url": f"https://t.me/{(await bot.get_me()).username}",
            "expires_in": 3600
        }
        try:
            response = requests.post(url, headers=self.headers, json=payload)
            data = response.json()
            if data.get('ok'):
                return {'success': True, 'invoice_id': data['result']['invoice_id'], 'pay_url': data['result']['pay_url'], 'amount': float(data['result']['amount']), 'asset': data['result']['asset']}
            return {'success': False, 'error': data.get('error')}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    async def get_invoice_status(self, invoice_id: int) -> Dict:
        url = f"{self.base_url}/getInvoices"
        params = {"invoice_ids": str(invoice_id)}
        try:
            response = requests.get(url, headers=self.headers, params=params)
            data = response.json()
            if data.get('ok') and data['result']['items']:
                inv = data['result']['items'][0]
                return {'success': True, 'status': inv['status'], 'paid_at': inv.get('paid_at')}
            return {'success': False}
        except Exception as e:
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
                    balance_usdt REAL DEFAULT 0,
                    frozen_usdt REAL DEFAULT 0,
                    total_trades INTEGER DEFAULT 0,
                    successful_trades INTEGER DEFAULT 0,
                    registration_date TEXT DEFAULT CURRENT_TIMESTAMP,
                    is_admin INTEGER DEFAULT 0
                )
            ''')
            
            # Объявления (лоты)
            await db.execute('''
                CREATE TABLE IF NOT EXISTS listings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    seller_id INTEGER,
                    skin_name TEXT,
                    skin_quality TEXT,
                    price_usdt REAL,
                    description TEXT,
                    photo_id TEXT,
                    status TEXT DEFAULT 'active',  -- active, sold, cancelled
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    channel_message_id INTEGER,
                    FOREIGN KEY (seller_id) REFERENCES users (user_id)
                )
            ''')
            
            # Сделки
            await db.execute('''
                CREATE TABLE IF NOT EXISTS deals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    listing_id INTEGER UNIQUE,
                    seller_id INTEGER,
                    buyer_id INTEGER,
                    price_usdt REAL,
                    fee REAL,
                    seller_gets REAL,
                    status TEXT DEFAULT 'pending',  -- pending, paid, shipped, completed, dispute
                    crypto_invoice_id INTEGER,
                    escrow_hold_id INTEGER,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    paid_at TEXT,
                    completed_at TEXT,
                    dispute_reason TEXT,
                    dispute_opened_by INTEGER,
                    FOREIGN KEY (listing_id) REFERENCES listings (id),
                    FOREIGN KEY (seller_id) REFERENCES users (user_id),
                    FOREIGN KEY (buyer_id) REFERENCES users (user_id)
                )
            ''')
            
            # Сообщения чата (для сделок)
            await db.execute('''
                CREATE TABLE IF NOT EXISTS deal_messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    deal_id INTEGER,
                    user_id INTEGER,
                    message TEXT,
                    date TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (deal_id) REFERENCES deals (id)
                )
            ''')
            
            # Крипто-платежи
            await db.execute('''
                CREATE TABLE IF NOT EXISTS crypto_payments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    invoice_id INTEGER UNIQUE,
                    amount_usdt REAL,
                    asset TEXT,
                    purpose TEXT,  -- 'deposit', 'payment'
                    deal_id INTEGER,
                    status TEXT DEFAULT 'pending',
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    confirmed_at TEXT,
                    FOREIGN KEY (user_id) REFERENCES users (user_id),
                    FOREIGN KEY (deal_id) REFERENCES deals (id)
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

    async def create_user(self, user_id: int, username: str, full_name: str) -> bool:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute('SELECT user_id FROM users WHERE user_id = ?', (user_id,))
            if await cursor.fetchone():
                return False
            await db.execute('INSERT INTO users (user_id, username, full_name) VALUES (?, ?, ?)',
                           (user_id, username, full_name))
            await db.commit()
            return True

    async def add_listing(self, seller_id: int, skin_name: str, skin_quality: str, price_usdt: float, description: str, photo_id: str = '') -> int:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute('''
                INSERT INTO listings (seller_id, skin_name, skin_quality, price_usdt, description, photo_id)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (seller_id, skin_name, skin_quality, price_usdt, description, photo_id))
            await db.commit()
            return cursor.lastrowid

    async def get_active_listings(self) -> List[Dict]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute('''
                SELECT l.*, u.username as seller_name 
                FROM listings l
                JOIN users u ON l.seller_id = u.user_id
                WHERE l.status = 'active'
                ORDER BY l.created_at DESC
            ''')
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def get_listing(self, listing_id: int) -> Optional[Dict]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute('''
                SELECT l.*, u.username as seller_name 
                FROM listings l
                JOIN users u ON l.seller_id = u.user_id
                WHERE l.id = ?
            ''', (listing_id,))
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def update_listing_channel_msg(self, listing_id: int, message_id: int):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('UPDATE listings SET channel_message_id = ? WHERE id = ?', (message_id, listing_id))
            await db.commit()

    async def create_deal(self, listing_id: int, buyer_id: int, invoice_id: int) -> int:
        async with aiosqlite.connect(self.db_path) as db:
            listing = await self.get_listing(listing_id)
            if not listing:
                return 0
            
            fee = listing['price_usdt'] * PLATFORM_FEE / 100
            seller_gets = listing['price_usdt'] - fee
            
            cursor = await db.execute('''
                INSERT INTO deals (listing_id, seller_id, buyer_id, price_usdt, fee, seller_gets, crypto_invoice_id, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (listing_id, listing['seller_id'], buyer_id, listing['price_usdt'], fee, seller_gets, invoice_id, 'pending'))
            await db.commit()
            
            # Обновляем статус лота
            await db.execute('UPDATE listings SET status = ? WHERE id = ?', ('sold', listing_id))
            await db.commit()
            
            return cursor.lastrowid

    async def get_deal(self, deal_id: int) -> Optional[Dict]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute('''
                SELECT d.*, l.skin_name, l.skin_quality, l.description,
                       seller.username as seller_name, buyer.username as buyer_name
                FROM deals d
                JOIN listings l ON d.listing_id = l.id
                JOIN users seller ON d.seller_id = seller.user_id
                JOIN users buyer ON d.buyer_id = buyer.user_id
                WHERE d.id = ?
            ''', (deal_id,))
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def get_user_deals(self, user_id: int) -> List[Dict]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute('''
                SELECT d.*, l.skin_name, l.skin_quality
                FROM deals d
                JOIN listings l ON d.listing_id = l.id
                WHERE d.seller_id = ? OR d.buyer_id = ?
                ORDER BY d.created_at DESC
            ''', (user_id, user_id))
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def add_crypto_payment(self, user_id: int, invoice_id: int, amount_usdt: float, asset: str, purpose: str, deal_id: int = None) -> bool:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('''
                INSERT INTO crypto_payments (user_id, invoice_id, amount_usdt, asset, purpose, deal_id)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (user_id, invoice_id, amount_usdt, asset, purpose, deal_id))
            await db.commit()
            return True

    async def confirm_crypto_payment(self, invoice_id: int) -> bool:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute('SELECT user_id, amount_usdt, purpose, deal_id FROM crypto_payments WHERE invoice_id = ? AND status = ?', (invoice_id, 'pending'))
            payment = await cursor.fetchone()
            
            if not payment:
                return False
            
            user_id, amount, purpose, deal_id = payment
            
            if purpose == 'deposit':
                # Просто пополнение баланса
                await db.execute('UPDATE users SET balance_usdt = balance_usdt + ? WHERE user_id = ?', (amount, user_id))
            elif purpose == 'payment' and deal_id:
                # Оплата сделки - замораживаем на эскроу
                await db.execute('UPDATE users SET frozen_usdt = frozen_usdt + ? WHERE user_id = ?', (amount, user_id))
                await db.execute('UPDATE deals SET status = ? WHERE id = ?', ('paid', deal_id))
            
            await db.execute('UPDATE crypto_payments SET status = ?, confirmed_at = CURRENT_TIMESTAMP WHERE invoice_id = ?', ('confirmed', invoice_id))
            await db.commit()
            return True

    async def add_deal_message(self, deal_id: int, user_id: int, message: str):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('INSERT INTO deal_messages (deal_id, user_id, message) VALUES (?, ?, ?)', (deal_id, user_id, message))
            await db.commit()

    async def get_deal_messages(self, deal_id: int) -> List[Dict]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute('''
                SELECT m.*, u.username 
                FROM deal_messages m
                JOIN users u ON m.user_id = u.user_id
                WHERE m.deal_id = ?
                ORDER BY m.date ASC
            ''', (deal_id,))
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def complete_deal(self, deal_id: int) -> bool:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute('SELECT seller_id, seller_gets, price_usdt FROM deals WHERE id = ? AND status = ?', (deal_id, 'paid'))
            deal = await cursor.fetchone()
            
            if not deal:
                return False
            
            seller_id, seller_gets, price = deal
            
            # Переводим деньги продавцу (за вычетом комиссии)
            await db.execute('UPDATE users SET frozen_usdt = frozen_usdt - ?, balance_usdt = balance_usdt + ? WHERE user_id = ?', (price, seller_gets, seller_id))
            
            # Обновляем статус сделки
            await db.execute('UPDATE deals SET status = ?, completed_at = CURRENT_TIMESTAMP WHERE id = ?', ('completed', deal_id))
            
            # Обновляем статистику пользователей
            await db.execute('UPDATE users SET total_trades = total_trades + 1, successful_trades = successful_trades + 1 WHERE user_id = ?', (seller_id,))
            await db.execute('UPDATE users SET total_trades = total_trades + 1, successful_trades = successful_trades + 1 WHERE user_id = ?', (deal[4] if len(deal) > 4 else 0,))
            
            await db.commit()
            return True

    async def dispute_deal(self, deal_id: int, user_id: int, reason: str) -> bool:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('''
                UPDATE deals SET status = ?, dispute_reason = ?, dispute_opened_by = ?
                WHERE id = ?
            ''', ('dispute', reason, user_id, deal_id))
            await db.commit()
            return True

    async def resolve_dispute(self, deal_id: int, winner_id: int) -> bool:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute('SELECT price_usdt, seller_id FROM deals WHERE id = ?', (deal_id,))
            deal = await cursor.fetchone()
            
            if not deal:
                return False
            
            price, seller_id = deal
            
            if winner_id == seller_id:
                # Победил продавец
                await db.execute('UPDATE users SET frozen_usdt = frozen_usdt - ?, balance_usdt = balance_usdt + ? WHERE user_id = ?', (price, price, seller_id))
            else:
                # Победил покупатель
                await db.execute('UPDATE users SET frozen_usdt = frozen_usdt - ?, balance_usdt = balance_usdt + ? WHERE user_id = ?', (price, price, winner_id))
            
            await db.execute('UPDATE deals SET status = ? WHERE id = ?', ('completed', deal_id))
            await db.commit()
            return True

    async def get_stats(self) -> Dict:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute('SELECT COUNT(*) FROM users')
            users = (await cursor.fetchone())[0]
            
            cursor = await db.execute('SELECT COUNT(*) FROM listings WHERE status = ?', ('active',))
            active_listings = (await cursor.fetchone())[0]
            
            cursor = await db.execute('SELECT COUNT(*) FROM deals')
            total_deals = (await cursor.fetchone())[0]
            
            cursor = await db.execute('SELECT SUM(price_usdt) FROM deals WHERE status = ?', ('completed',))
            volume = (await cursor.fetchone())[0] or 0
            
            cursor = await db.execute('SELECT SUM(fee) FROM deals WHERE status = ?', ('completed',))
            fees = (await cursor.fetchone())[0] or 0
            
            return {
                'users': users,
                'active_listings': active_listings,
                'total_deals': total_deals,
                'volume': volume,
                'fees': fees
            }

# ========== ИНИЦИАЛИЗАЦИЯ ==========
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())
db = Database()
crypto = CryptoPayAPI(CRYPTOPAY_TOKEN)

# ========== СОСТОЯНИЯ ==========
class SellStates(StatesGroup):
    waiting_for_skin_name = State()
    waiting_for_skin_quality = State()
    waiting_for_price = State()
    waiting_for_description = State()
    waiting_for_photo = State()

class DealMessageStates(StatesGroup):
    waiting_for_message = State()

class DisputeStates(StatesGroup):
    waiting_for_reason = State()

# ========== КЛАВИАТУРЫ ==========
class Keyboards:
    @staticmethod
    def main() -> InlineKeyboardMarkup:
        buttons = [
            [InlineKeyboardButton(text="🛒 КУПИТЬ", callback_data="buy_menu")],
            [InlineKeyboardButton(text="💸 ПРОДАТЬ", callback_data="sell_start")],
            [InlineKeyboardButton(text="📦 МОИ СДЕЛКИ", callback_data="my_deals")],
            [InlineKeyboardButton(text="💰 БАЛАНС", callback_data="balance")],
            [InlineKeyboardButton(text="📢 КАНАЛ", url=CHANNEL_LINK)],
            [InlineKeyboardButton(text="ℹ️ ПОМОЩЬ", callback_data="help")]
        ]
        return InlineKeyboardMarkup(inline_keyboard=buttons)

    @staticmethod
    def back() -> InlineKeyboardMarkup:
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀ НАЗАД", callback_data="main_menu")]
        ])

    @staticmethod
    def deal_actions(deal_id: int, user_id: int, deal: Dict) -> InlineKeyboardMarkup:
        buttons = []
        
        if deal['status'] == 'paid':
            if deal['seller_id'] == user_id:
                buttons.append([InlineKeyboardButton(text="✅ ПОДТВЕРДИТЬ ПОЛУЧЕНИЕ ОПЛАТЫ", callback_data=f"deal_confirm_{deal_id}")])
            if deal['buyer_id'] == user_id or deal['seller_id'] == user_id:
                buttons.append([InlineKeyboardButton(text="💬 НАПИСАТЬ", callback_data=f"deal_message_{deal_id}")])
        
        if deal['status'] != 'completed' and deal['status'] != 'dispute':
            buttons.append([InlineKeyboardButton(text="⚠️ ОТКРЫТЬ СПОР", callback_data=f"deal_dispute_{deal_id}")])
        
        buttons.append([InlineKeyboardButton(text="◀ НАЗАД", callback_data="my_deals")])
        return InlineKeyboardMarkup(inline_keyboard=buttons)

    @staticmethod
    def listing_keyboard(listing_id: int) -> InlineKeyboardMarkup:
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💰 КУПИТЬ", callback_data=f"buy_listing_{listing_id}")],
            [InlineKeyboardButton(text="◀ НАЗАД", callback_data="buy_menu")]
        ])

    @staticmethod
    def admin() -> InlineKeyboardMarkup:
        buttons = [
            [InlineKeyboardButton(text="📊 СТАТИСТИКА", callback_data="admin_stats")],
            [InlineKeyboardButton(text="⚠️ АКТИВНЫЕ СПОРЫ", callback_data="admin_disputes")],
            [InlineKeyboardButton(text="◀ НАЗАД", callback_data="main_menu")]
        ]
        return InlineKeyboardMarkup(inline_keyboard=buttons)

# ========== КОМАНДЫ ==========
@dp.message(Command("start"))
async def cmd_start(message: Message):
    user_id = message.from_user.id
    username = message.from_user.username or "NoName"
    full_name = message.from_user.full_name or "NoName"
    
    await db.create_user(user_id, username, full_name)
    user = await db.get_user(user_id)
    
    await message.answer(
        f"🎮 **ДОБРО ПОЖАЛОВАТЬ В SHIZOGP P2P!**\n\n"
        f"👤 Твой ID: `{user_id}`\n"
        f"💰 Баланс: **{user['balance_usdt']:.2f}** USDT\n"
        f"🔒 Заморожено: **{user['frozen_usdt']:.2f}** USDT\n"
        f"📊 Сделок: **{user['total_trades']}** (✅ {user['successful_trades']})\n\n"
        f"⚡ P2P-платформа с гарантом\n"
        f"💸 Покупай и продавай безопасно!",
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

@dp.message(Command("balance"))
async def cmd_balance(message: Message):
    user_id = message.from_user.id
    user = await db.get_user(user_id)
    
    await message.answer(
        f"💰 **ТВОЙ БАЛАНС**\n\n"
        f"Доступно: **{user['balance_usdt']:.2f}** USDT\n"
        f"Заморожено: **{user['frozen_usdt']:.2f}** USDT\n\n"
        f"💳 Пополнить можно через раздел КРИПТО",
        reply_markup=Keyboards.back(),
        parse_mode="Markdown"
    )

# ========== ПРОДАЖА ==========
@dp.callback_query(F.data == "sell_start")
async def callback_sell_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(SellStates.waiting_for_skin_name)
    await callback.message.edit_text(
        "💸 **ПРОДАЖА СКИНА**\n\n"
        "Шаг 1/5: Введи **название скина**\n"
        "Пример: `AK-47 | Redline`",
        parse_mode="Markdown"
    )

@dp.message(SellStates.waiting_for_skin_name)
async def sell_skin_name(message: Message, state: FSMContext):
    await state.update_data(skin_name=message.text)
    await state.set_state(SellStates.waiting_for_skin_quality)
    await message.answer(
        "📦 Шаг 2/5: Введи **качество**\n"
        "Пример: `Factory New`, `Minimal Wear`"
    )

@dp.message(SellStates.waiting_for_skin_quality)
async def sell_skin_quality(message: Message, state: FSMContext):
    await state.update_data(skin_quality=message.text)
    await state.set_state(SellStates.waiting_for_price)
    await message.answer(
        f"💰 Шаг 3/5: Введи **цену в USDT**\n"
        f"Мин: {MIN_PRICE}$, Макс: {MAX_PRICE}$"
    )

@dp.message(SellStates.waiting_for_price)
async def sell_price(message: Message, state: FSMContext):
    try:
        price = float(message.text)
        if price < MIN_PRICE or price > MAX_PRICE:
            raise ValueError
    except:
        await message.answer(f"❌ Цена должна быть числом от {MIN_PRICE} до {MAX_PRICE} USDT")
        return
    
    await state.update_data(price=price)
    await state.set_state(SellStates.waiting_for_description)
    await message.answer(
        "📝 Шаг 4/5: Введи **описание**\n"
        "Состояние скина, float, паттерн и т.д."
    )

@dp.message(SellStates.waiting_for_description)
async def sell_description(message: Message, state: FSMContext):
    await state.update_data(description=message.text)
    await state.set_state(SellStates.waiting_for_photo)
    await message.answer(
        "🖼 Шаг 5/5: Отправь **фото скина** (можно пропустить, отправив любой текст)"
    )

@dp.message(SellStates.waiting_for_photo)
async def sell_photo(message: Message, state: FSMContext):
    data = await state.get_data()
    photo_id = message.photo[-1].file_id if message.photo else ''
    
    listing_id = await db.add_listing(
        message.from_user.id,
        data['skin_name'],
        data['skin_quality'],
        data['price'],
        data['description'],
        photo_id
    )
    
    # Отправляем в канал
    try:
        text = f"🆕 **НОВЫЙ ЛОТ!**\n\n"
        text += f"🎯 **{data['skin_name']}**\n"
        text += f"📦 **Качество:** {data['skin_quality']}\n"
        text += f"💰 **Цена:** {data['price']} USDT\n"
        text += f"📝 **Описание:** {data['description']}\n"
        text += f"👤 **Продавец:** @{message.from_user.username or 'NoName'}\n\n"
        text += f"👇 Нажми кнопку чтобы купить!"
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💰 КУПИТЬ", url=f"https://t.me/{(await bot.get_me()).username}?start=buy_{listing_id}")]
        ])
        
        if photo_id:
            msg = await bot.send_photo(CHANNEL_LINK, photo_id, caption=text, reply_markup=keyboard, parse_mode="Markdown")
        else:
            msg = await bot.send_message(CHANNEL_LINK, text, reply_markup=keyboard, parse_mode="Markdown")
        
        await db.update_listing_channel_msg(listing_id, msg.message_id)
    except Exception as e:
        logger.error(f"Ошибка отправки в канал: {e}")
    
    await message.answer(
        f"✅ **Лот #{listing_id} создан!**\n\n"
        f"Опубликован в канале. Как только кто-то купит, ты получишь уведомление.",
        reply_markup=Keyboards.main()
    )
    await state.clear()

# ========== ПОКУПКА ==========
@dp.callback_query(F.data == "buy_menu")
async def callback_buy_menu(callback: CallbackQuery):
    listings = await db.get_active_listings()
    
    if not listings:
        await callback.message.edit_text(
            "🛒 **Нет активных лотов**\n\n"
            "Нажми «ПРОДАТЬ» чтобы создать первый лот!",
            reply_markup=Keyboards.back()
        )
        return
    
    text = "🛒 **ДОСТУПНЫЕ ЛОТЫ**\n\n"
    for l in listings:
        text += f"🎯 **{l['skin_name']}** ({l['skin_quality']})\n"
        text += f"💰 {l['price_usdt']} USDT | 👤 @{l['seller_name']}\n"
        text += f"🆔 Лот #{l['id']}\n\n"
    
    buttons = []
    for l in listings[:5]:
        buttons.append([InlineKeyboardButton(text=f"Лот #{l['id']} - {l['skin_name'][:20]}", callback_data=f"view_listing_{l['id']}")])
    buttons.append([InlineKeyboardButton(text="◀ НАЗАД", callback_data="main_menu")])
    
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons), parse_mode="Markdown")

@dp.callback_query(F.data.startswith("view_listing_"))
async def callback_view_listing(callback: CallbackQuery):
    listing_id = int(callback.data.replace("view_listing_", ""))
    listing = await db.get_listing(listing_id)
    
    if not listing or listing['status'] != 'active':
        await callback.message.edit_text("❌ Лот уже не доступен", reply_markup=Keyboards.back())
        return
    
    text = f"🎯 **{listing['skin_name']}**\n"
    text += f"📦 **Качество:** {listing['skin_quality']}\n"
    text += f"💰 **Цена:** {listing['price_usdt']} USDT\n"
    text += f"📝 **Описание:** {listing['description']}\n"
    text += f"👤 **Продавец:** @{listing['seller_name']}\n"
    text += f"🆔 **Лот #{listing['id']}**\n\n"
    text += f"⚠️ **Комиссия платформы:** {PLATFORM_FEE}%\n"
    text += f"💸 Продавец получит: {listing['price_usdt'] * (1 - PLATFORM_FEE/100):.2f} USDT"
    
    if listing['photo_id']:
        await callback.message.delete()
        await callback.message.answer_photo(
            listing['photo_id'],
            caption=text,
            reply_markup=Keyboards.listing_keyboard(listing_id),
            parse_mode="Markdown"
        )
    else:
        await callback.message.edit_text(text, reply_markup=Keyboards.listing_keyboard(listing_id), parse_mode="Markdown")

@dp.callback_query(F.data.startswith("buy_listing_"))
async def callback_buy_listing(callback: CallbackQuery):
    listing_id = int(callback.data.replace("buy_listing_", ""))
    buyer_id = callback.from_user.id
    listing = await db.get_listing(listing_id)
    
    if not listing or listing['status'] != 'active':
        await callback.answer("❌ Лот уже куплен!", show_alert=True)
        return
    
    if listing['seller_id'] == buyer_id:
        await callback.answer("❌ Нельзя купить свой лот!", show_alert=True)
        return
    
    # Проверяем баланс
    user = await db.get_user(buyer_id)
    if user['balance_usdt'] < listing['price_usdt']:
        await callback.answer(f"❌ Недостаточно USDT! Нужно {listing['price_usdt']} USDT", show_alert=True)
        return
    
    # Создаём счёт в Crypto Pay для оплаты
    inv = await crypto.create_invoice(listing['price_usdt'], 'USDT', f"Оплата лота #{listing_id}")
    
    if not inv['success']:
        await callback.answer("❌ Ошибка создания платежа", show_alert=True)
        return
    
    # Сохраняем платёж
    await db.add_crypto_payment(buyer_id, inv['invoice_id'], listing['price_usdt'], 'USDT', 'payment')
    
    # Создаём сделку
    deal_id = await db.create_deal(listing_id, buyer_id, inv['invoice_id'])
    
    text = f"💳 **ОПЛАТА ЛОТА #{listing_id}**\n\n"
    text += f"🎯 **Скин:** {listing['skin_name']} ({listing['skin_quality']})\n"
    text += f"💰 **Сумма:** {listing['price_usdt']} USDT\n\n"
    text += f"🔗 **Ссылка для оплаты:**\n{inv['pay_url']}\n\n"
    text += f"⏱ Действительна 1 час\n\n"
    text += f"✅ **После оплаты нажми «ПРОВЕРИТЬ»**"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 ОПЛАТИТЬ", url=inv['pay_url'])],
        [InlineKeyboardButton(text="🔄 ПРОВЕРИТЬ", callback_data=f"check_deal_payment_{deal_id}")],
        [InlineKeyboardButton(text="◀ ОТМЕНА", callback_data="buy_menu")]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")

@dp.callback_query(F.data.startswith("check_deal_payment_"))
async def callback_check_deal_payment(callback: CallbackQuery):
    deal_id = int(callback.data.replace("check_deal_payment_", ""))
    deal = await db.get_deal(deal_id)
    
    if not deal:
        await callback.answer("❌ Сделка не найдена", show_alert=True)
        return
    
    if deal['status'] != 'pending':
        await callback.answer(f"⏳ Статус: {deal['status']}", show_alert=True)
        return
    
    # Проверяем статус инвойса
    status = await crypto.get_invoice_status(deal['crypto_invoice_id'])
    
    if status['success'] and status['status'] == 'paid':
        # Подтверждаем оплату
        await db.confirm_crypto_payment(deal['crypto_invoice_id'])
        
        # Обновляем статус сделки
        async with aiosqlite.connect(DATABASE_PATH) as conn:
            await conn.execute('UPDATE deals SET status = ? WHERE id = ?', ('paid', deal_id))
            await conn.commit()
        
        # Уведомляем продавца
        try:
            await bot.send_message(
                deal['seller_id'],
                f"✅ **Ваш лот #{deal['listing_id']} купили!**\n\n"
                f"🎯 Скин: {deal['skin_name']}\n"
                f"💰 Сумма заморожена: {deal['price_usdt']} USDT\n\n"
                f"📞 Свяжитесь с покупателем для передачи скина.\n"
                f"После передачи нажмите «ПОДТВЕРДИТЬ».",
                reply_markup=Keyboards.main()
            )
        except:
            pass
        
        await callback.message.edit_text(
            f"✅ **ОПЛАЧЕНО!**\n\n"
            f"Средства заморожены.\n"
            f"Свяжитесь с продавцом: @{deal['seller_name']}\n\n"
            f"После получения скина подтвердите сделку.",
            reply_markup=Keyboards.main()
        )
    else:
        await callback.answer("⏳ Оплата ещё не поступила", show_alert=True)

# ========== СДЕЛКИ ==========
@dp.callback_query(F.data == "my_deals")
async def callback_my_deals(callback: CallbackQuery):
    user_id = callback.from_user.id
    deals = await db.get_user_deals(user_id)
    
    if not deals:
        await callback.message.edit_text(
            "📦 **У тебя нет сделок**\n\n"
            "Купи или продай что-нибудь!",
            reply_markup=Keyboards.back()
        )
        return
    
    text = "📦 **ТВОИ СДЕЛКИ**\n\n"
    buttons = []
    
    for d in deals:
        role = "Продавец" if d['seller_id'] == user_id else "Покупатель"
        status_emoji = {
            'pending': '⏳', 'paid': '💰', 'shipped': '📦',
            'completed': '✅', 'dispute': '⚠️'
        }.get(d['status'], '⏳')
        
        text += f"{status_emoji} **Сделка #{d['id']}**\n"
        text += f"🎯 {d['skin_name']}\n"
        text += f"💰 {d['price_usdt']} USDT | 👤 {role}\n\n"
        
        buttons.append([InlineKeyboardButton(
            text=f"🔍 Сделка #{d['id']}",
            callback_data=f"view_deal_{d['id']}"
        )])
    
    buttons.append([InlineKeyboardButton(text="◀ НАЗАД", callback_data="main_menu")])
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons), parse_mode="Markdown")

@dp.callback_query(F.data.startswith("view_deal_"))
async def callback_view_deal(callback: CallbackQuery):
    deal_id = int(callback.data.replace("view_deal_", ""))
    user_id = callback.from_user.id
    deal = await db.get_deal(deal_id)
    
    if not deal:
        await callback.message.edit_text("❌ Сделка не найдена", reply_markup=Keyboards.back())
        return
    
    role = "Продавец" if deal['seller_id'] == user_id else "Покупатель"
    other_id = deal['seller_id'] if role == "Покупатель" else deal['buyer_id']
    
    status_text = {
        'pending': '⏳ Ожидает оплаты',
        'paid': '💰 Оплачено (ожидает передачи)',
        'shipped': '📦 Отправлено',
        'completed': '✅ Завершено',
        'dispute': '⚠️ Спор'
    }.get(deal['status'], deal['status'])
    
    text = f"📋 **СДЕЛКА #{deal_id}**\n\n"
    text += f"🎯 **Скин:** {deal['skin_name']} ({deal['skin_quality']})\n"
    text += f"💰 **Цена:** {deal['price_usdt']} USDT\n"
    text += f"👤 **Твоя роль:** {role}\n"
    text += f"👥 **Оппонент:** @{deal['seller_name'] if role == 'Покупатель' else deal['buyer_name']}\n"
    text += f"🔄 **Статус:** {status_text}\n\n"
    
    if deal['status'] == 'completed':
        text += f"💸 **Продавец получил:** {deal['seller_gets']:.2f} USDT\n"
        text += f"📊 **Комиссия:** {deal['fee']:.2f} USDT\n"
        text += f"✅ Завершена: {deal['completed_at'][:16]}\n\n"
    
    if deal['status'] == 'dispute':
        text += f"⚠️ **Причина спора:** {deal['dispute_reason']}\n"
        text += f"👤 Открыл: {'Продавец' if deal['dispute_opened_by'] == deal['seller_id'] else 'Покупатель'}\n\n"
    
    text += f"💬 **Чат сделки:**"
    
    # Получаем сообщения
    messages = await db.get_deal_messages(deal_id)
    if messages:
        for m in messages[-5:]:  # последние 5
            text += f"\n👤 @{m['username']}: {m['message']}"
    else:
        text += "\nНет сообщений"
    
    await callback.message.edit_text(
        text,
        reply_markup=Keyboards.deal_actions(deal_id, user_id, deal),
        parse_mode="Markdown"
    )

@dp.callback_query(F.data.startswith("deal_message_"))
async def callback_deal_message(callback: CallbackQuery, state: FSMContext):
    deal_id = int(callback.data.replace("deal_message_", ""))
    await state.update_data(deal_id=deal_id)
    await state.set_state(DealMessageStates.waiting_for_message)
    await callback.message.edit_text(
        "💬 Напиши сообщение для оппонента:",
        reply_markup=Keyboards.back()
    )

@dp.message(DealMessageStates.waiting_for_message)
async def deal_message_send(message: Message, state: FSMContext):
    data = await state.get_data()
    deal_id = data['deal_id']
    
    await db.add_deal_message(deal_id, message.from_user.id, message.text)
    
    # Уведомляем оппонента
    deal = await db.get_deal(deal_id)
    opponent_id = deal['seller_id'] if deal['buyer_id'] == message.from_user.id else deal['buyer_id']
    
    try:
        await bot.send_message(
            opponent_id,
            f"💬 **Новое сообщение по сделке #{deal_id}**\n\n"
            f"👤 @{message.from_user.username or 'NoName'}: {message.text}"
        )
    except:
        pass
    
    await message.answer("✅ Сообщение отправлено!")
    await state.clear()

@dp.callback_query(F.data.startswith("deal_confirm_"))
async def callback_deal_confirm(callback: CallbackQuery):
    deal_id = int(callback.data.replace("deal_confirm_", ""))
    user_id = callback.from_user.id
    deal = await db.get_deal(deal_id)
    
    if not deal or deal['status'] != 'paid' or deal['seller_id'] != user_id:
        await callback.answer("❌ Нельзя подтвердить", show_alert=True)
        return
    
    # Завершаем сделку
    await db.complete_deal(deal_id)
    
    # Уведомляем покупателя
    try:
        await bot.send_message(
            deal['buyer_id'],
            f"✅ **Сделка #{deal_id} завершена!**\n\n"
            f"Продавец подтвердил получение оплаты.\n"
            f"Спасибо за покупку!",
            reply_markup=Keyboards.main()
        )
    except:
        pass
    
    await callback.message.edit_text(
        f"✅ **Сделка #{deal_id} завершена!**\n\n"
        f"Деньги ({deal['seller_gets']:.2f} USDT) зачислены на твой баланс.",
        reply_markup=Keyboards.main()
    )

@dp.callback_query(F.data.startswith("deal_dispute_"))
async def callback_deal_dispute(callback: CallbackQuery, state: FSMContext):
    deal_id = int(callback.data.replace("deal_dispute_", ""))
    await state.update_data(deal_id=deal_id)
    await state.set_state(DisputeStates.waiting_for_reason)
    await callback.message.edit_text(
        "⚠️ Напиши причину спора.\n\n"
        "Администратор рассмотрит и примет решение.",
        reply_markup=Keyboards.back()
    )

@dp.message(DisputeStates.waiting_for_reason)
async def dispute_reason(message: Message, state: FSMContext):
    data = await state.get_data()
    deal_id = data['deal_id']
    user_id = message.from_user.id
    
    await db.dispute_deal(deal_id, user_id, message.text)
    
    # Уведомляем админов
    deal = await db.get_deal(deal_id)
    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(
                admin_id,
                f"⚠️ **НОВЫЙ СПОР** по сделке #{deal_id}\n\n"
                f"🎯 Скин: {deal['skin_name']}\n"
                f"💰 Сумма: {deal['price_usdt']} USDT\n"
                f"👤 Открыл: @{message.from_user.username or user_id}\n"
                f"📝 Причина: {message.text}\n\n"
                f"Используй /admin для решения.",
                reply_markup=Keyboards.admin()
            )
        except:
            pass
    
    await message.answer("✅ Спор открыт! Администратор скоро свяжется.")
    await state.clear()

# ========== ПОПОЛНЕНИЕ БАЛАНСА ==========
@dp.callback_query(F.data == "balance")
async def callback_balance(callback: CallbackQuery):
    user_id = callback.from_user.id
    user = await db.get_user(user_id)
    
    text = f"💰 **ТВОЙ БАЛАНС**\n\n"
    text += f"Доступно: **{user['balance_usdt']:.2f}** USDT\n"
    text += f"Заморожено: **{user['frozen_usdt']:.2f}** USDT\n\n"
    text += f"💳 **Пополнить баланс:**\n"
    text += f"1. Выбери сумму\n"
    text += f"2. Оплати через @CryptoBot\n"
    text += f"3. Средства зачислятся автоматически"
    
    amounts = [10, 25, 50, 100, 250, 500]
    buttons = []
    row = []
    for i, a in enumerate(amounts):
        row.append(InlineKeyboardButton(text=f"{a}$", callback_data=f"deposit_{a}"))
        if (i + 1) % 3 == 0:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    buttons.append([InlineKeyboardButton(text="◀ НАЗАД", callback_data="main_menu")])
    
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons), parse_mode="Markdown")

@dp.callback_query(F.data.startswith("deposit_"))
async def callback_deposit(callback: CallbackQuery):
    amount = float(callback.data.replace("deposit_", ""))
    user_id = callback.from_user.id
    
    inv = await crypto.create_invoice(amount, 'USDT', f"Пополнение баланса SHIZOGP")
    
    if not inv['success']:
        await callback.answer("❌ Ошибка создания платежа", show_alert=True)
        return
    
    await db.add_crypto_payment(user_id, inv['invoice_id'], amount, 'USDT', 'deposit')
    
    text = f"💳 **ПОПОЛНЕНИЕ БАЛАНСА**\n\n"
    text += f"💰 Сумма: **{amount} USDT**\n"
    text += f"🔗 **Ссылка для оплаты:**\n{inv['pay_url']}\n\n"
    text += f"⏱ Действительна 1 час\n\n"
    text += f"✅ После оплаты нажми «ПРОВЕРИТЬ»"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 ОПЛАТИТЬ", url=inv['pay_url'])],
        [InlineKeyboardButton(text="🔄 ПРОВЕРИТЬ", callback_data=f"check_deposit_{inv['invoice_id']}")],
        [InlineKeyboardButton(text="◀ НАЗАД", callback_data="balance")]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")

@dp.callback_query(F.data.startswith("check_deposit_"))
async def callback_check_deposit(callback: CallbackQuery):
    invoice_id = int(callback.data.replace("check_deposit_", ""))
    
    status = await crypto.get_invoice_status(invoice_id)
    
    if status['success'] and status['status'] == 'paid':
        if await db.confirm_crypto_payment(invoice_id):
            await callback.message.edit_text(
                f"✅ **БАЛАНС ПОПОЛНЕН!**\n\n"
                f"Средства зачислены.\n"
                f"Можешь проверить в разделе «БАЛАНС».",
                reply_markup=Keyboards.main()
            )
        else:
            await callback.answer("❌ Ошибка зачисления", show_alert=True)
    else:
        await callback.answer("⏳ Платёж ещё не поступил", show_alert=True)

# ========== АДМИНКА ==========
@dp.message(Command("admin"))
async def cmd_admin(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("⛔ Доступ запрещён!")
        return
    
    stats = await db.get_stats()
    
    text = f"🔧 **АДМИН ПАНЕЛЬ**\n\n"
    text += f"📊 **СТАТИСТИКА:**\n"
    text += f"├ 👥 Пользователей: {stats['users']}\n"
    text += f"├ 🛒 Активных лотов: {stats['active_listings']}\n"
    text += f"├ 💳 Всего сделок: {stats['total_deals']}\n"
    text += f"├ 💰 Объём: {stats['volume']:.2f} USDT\n"
    text += f"└ 💸 Комиссий собрано: {stats['fees']:.2f} USDT"
    
    await message.answer(text, reply_markup=Keyboards.admin(), parse_mode="Markdown")

@dp.callback_query(F.data == "admin_stats")
async def callback_admin_stats(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("⛔ Доступ запрещён!", show_alert=True)
        return
    
    stats = await db.get_stats()
    
    text = f"📊 **ПОЛНАЯ СТАТИСТИКА**\n\n"
    text += f"👥 **Пользователи:** {stats['users']}\n"
    text += f"🛒 **Активные лоты:** {stats['active_listings']}\n"
    text += f"💳 **Всего сделок:** {stats['total_deals']}\n"
    text += f"💰 **Объём:** {stats['volume']:.2f} USDT\n"
    text += f"💸 **Комиссии:** {stats['fees']:.2f} USDT\n"
    text += f"📈 **Средняя комиссия:** {stats['fees']/max(stats['total_deals'],1):.2f} USDT"
    
    await callback.message.edit_text(text, reply_markup=Keyboards.admin(), parse_mode="Markdown")

@dp.callback_query(F.data == "admin_disputes")
async def callback_admin_disputes(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("⛔ Доступ запрещён!", show_alert=True)
        return
    
    async with aiosqlite.connect(DATABASE_PATH) as conn:
        conn.row_factory = aiosqlite.Row
        cursor = await conn.execute('''
            SELECT d.*, l.skin_name 
            FROM deals d
            JOIN listings l ON d.listing_id = l.id
            WHERE d.status = 'dispute'
            ORDER BY d.created_at DESC
        ''')
        disputes = await cursor.fetchall()
    
    if not disputes:
        await callback.message.edit_text("📭 Нет активных споров", reply_markup=Keyboards.admin())
        return
    
    text = "⚠️ **АКТИВНЫЕ СПОРЫ**\n\n"
    buttons = []
    
    for d in disputes:
        text += f"🔴 Спор #{d['id']}\n"
        text += f"🎯 {d['skin_name']}\n"
        text += f"💰 {d['price_usdt']} USDT\n"
        text += f"📝 {d['dispute_reason'][:50]}...\n\n"
        
        buttons.append([InlineKeyboardButton(
            text=f"⚖️ Решить спор #{d['id']}",
            callback_data=f"resolve_dispute_{d['id']}"
        )])
    
    buttons.append([InlineKeyboardButton(text="◀ НАЗАД", callback_data="admin_stats")])
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons), parse_mode="Markdown")

@dp.callback_query(F.data.startswith("resolve_dispute_"))
async def callback_resolve_dispute(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("⛔ Доступ запрещён!", show_alert=True)
        return
    
    deal_id = int(callback.data.replace("resolve_dispute_", ""))
    deal = await db.get_deal(deal_id)
    
    if not deal or deal['status'] != 'dispute':
        await callback.answer("❌ Спор уже решён", show_alert=True)
        return
    
    text = f"⚖️ **РЕШЕНИЕ СПОРА #{deal_id}**\n\n"
    text += f"🎯 {deal['skin_name']}\n"
    text += f"💰 Сумма: {deal['price_usdt']} USDT\n"
    text += f"👤 Продавец: @{deal['seller_name']}\n"
    text += f"👤 Покупатель: @{deal['buyer_name']}\n"
    text += f"📝 Причина: {deal['dispute_reason']}\n\n"
    text += f"**Кому присудить средства?**"
    
    buttons = [
        [InlineKeyboardButton(text="👤 ПРОДАВЦУ", callback_data=f"dispute_winner_{deal_id}_{deal['seller_id']}")],
        [InlineKeyboardButton(text="👤 ПОКУПАТЕЛЮ", callback_data=f"dispute_winner_{deal_id}_{deal['buyer_id']}")],
        [InlineKeyboardButton(text="◀ НАЗАД", callback_data="admin_disputes")]
    ]
    
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons), parse_mode="Markdown")

@dp.callback_query(F.data.startswith("dispute_winner_"))
async def callback_dispute_winner(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("⛔ Доступ запрещён!", show_alert=True)
        return
    
    _, _, deal_id, winner_id = callback.data.split("_")
    deal_id = int(deal_id)
    winner_id = int(winner_id)
    
    await db.resolve_dispute(deal_id, winner_id)
    
    # Уведомляем участников
    deal = await db.get_deal(deal_id)
    for uid in [deal['seller_id'], deal['buyer_id']]:
        try:
            role = "Продавец" if uid == deal['seller_id'] else "Покупатель"
            await bot.send_message(
                uid,
                f"⚖️ **Спор по сделке #{deal_id} решён!**\n\n"
                f"Администратор принял решение в пользу **{'ПРОДАВЦА' if winner_id == deal['seller_id'] else 'ПОКУПАТЕЛЯ'}**.\n"
                f"Средства переведены победителю.",
                reply_markup=Keyboards.main()
            )
        except:
            pass
    
    await callback.message.edit_text(
        f"✅ Спор #{deal_id} решён! Средства переведены.",
        reply_markup=Keyboards.admin()
    )

# ========== ПОМОЩЬ ==========
@dp.callback_query(F.data == "help")
async def callback_help(callback: CallbackQuery):
    text = f"""
🆘 **ПОМОЩЬ ПО P2P-ПЛАТФОРМЕ**

📌 **Как купить:**
1. Нажми «КУПИТЬ» → выбери лот
2. Оплати через @CryptoBot
3. Деньги заморозятся (эскроу)
4. Свяжись с продавцом
5. Получи скин → подтверди

📌 **Как продать:**
1. Нажми «ПРОДАТЬ» → заполни данные
2. Лот появится в канале
3. Покупатель оплатит
4. Отправь скин → подтверди
5. Получишь деньги (минус {PLATFORM_FEE}%)

📌 **Безопасность:**
✅ Деньги на эскроу
✅ Чат внутри сделки
✅ Арбитраж при спорах

📞 Поддержка: {SUPPORT_LINK}
    """
    
    await callback.message.edit_text(text, reply_markup=Keyboards.back(), parse_mode="Markdown")

# ========== MAIN MENU ==========
@dp.callback_query(F.data == "main_menu")
async def callback_main_menu(callback: CallbackQuery):
    user_id = callback.from_user.id
    user = await db.get_user(user_id)
    
    await callback.message.edit_text(
        f"📋 **ГЛАВНОЕ МЕНЮ**\n\n"
        f"💰 Баланс: {user['balance_usdt']:.2f} USDT\n"
        f"🔒 Заморожено: {user['frozen_usdt']:.2f} USDT",
        reply_markup=Keyboards.main(),
        parse_mode="Markdown"
    )

# ========== ЗАПУСК ==========
async def on_startup():
    print(f"\n{Colors.CYAN}{'='*60}{Colors.END}")
    print(f"{Colors.MAGENTA}{Colors.BOLD}🔥 SHIZOGP P2P ЭСКРОУ БОТ 🔥{Colors.END}")
    print(f"{Colors.CYAN}{'='*60}{Colors.END}")
    print(f"{Colors.GREEN}✅ Версия: {BOT_VERSION}{Colors.END}")
    print(f"{Colors.GREEN}✅ Токен: {BOT_TOKEN[:15]}...{Colors.END}")
    print(f"{Colors.GREEN}✅ Админы: {ADMIN_IDS}{Colors.END}")
    print(f"{Colors.GREEN}✅ Канал: {CHANNEL_LINK}{Colors.END}")
    print(f"{Colors.GREEN}✅ Комиссия: {PLATFORM_FEE}%{Colors.END}")
    
    await db.init_db()
    
    me = await bot.get_me()
    print(f"{Colors.GREEN}✅ Бот: @{me.username}{Colors.END}")
    print(f"{Colors.CYAN}{'='*60}{Colors.END}")
    print(f"{Colors.YELLOW}{Colors.BOLD}🚀 БОТ ЗАПУЩЕН!{Colors.END}")
    print(f"{Colors.CYAN}{'='*60}{Colors.END}")

async def main():
    await on_startup()
    try:
        await dp.start_polling(bot)
    except KeyboardInterrupt:
        print(f"\n{Colors.RED}👋 Остановка...{Colors.END}")
    finally:
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())
