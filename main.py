# main.py - ARENA DRAFT v4.7 (ФИНАЛЬНАЯ ВЕРСИЯ - БЕЗ ДЕФОЛТОВ)
import random
import json
import os
import logging
import sqlite3
import asyncio
import time
import re
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from aiogram.client.default import DefaultBotProperties

DB_NAME = "arena.db"

# ==================== СОСТОЯНИЯ ====================
class States(StatesGroup):
    reg_name = State()
    pack_open = State()
    deck_edit = State()
    card_info = State()
    base_menu = State()
    base_upgrade = State()
    base_skill_tree = State()
    clan_input = State()
    clan_emoji = State()
    clan_upgrade = State()
    clan_join_code = State()
    live_wait = State()
    live_join = State()
    battle_live = State()
    battle_raid = State()
    battle_select_unit = State()
    battle_select_skill = State()
    battle_select_target = State()
    qte_memory = State()
    qte_find = State()
    rating_mode = State()

# ==================== ИНИЦИАЛИЗАЦИЯ БД ====================
def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS players (
        user_id INTEGER PRIMARY KEY,
        name TEXT,
        gold INTEGER DEFAULT 500,
        rating INTEGER DEFAULT 1000,
        energy INTEGER DEFAULT 5,
        energy_time INTEGER DEFAULT 0,
        clan_id INTEGER,
        cards TEXT DEFAULT '{"1":5,"2":3}',
        packs TEXT DEFAULT '{"basic":2,"rare":0,"epic":0}',
        deck TEXT DEFAULT '["1","2","3","4","5","6"]',
        base_level INTEGER DEFAULT 1,
        base_xp INTEGER DEFAULT 0,
        base_skills TEXT DEFAULT '{"max_rarity":1,"relic_slots":0,"trap_level":0,"equipment_slots":0,"mana_regen":0,"crit_chance":0}',
        equipment TEXT DEFAULT '{}',
        relics TEXT DEFAULT '{}',
        wins INTEGER DEFAULT 0,
        losses INTEGER DEFAULT 0
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS clans (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE,
        emoji TEXT,
        leader_id INTEGER,
        level INTEGER DEFAULT 1,
        members INTEGER DEFAULT 1,
        clan_damage_bonus REAL DEFAULT 0,
        clan_defense_bonus REAL DEFAULT 0,
        clan_hp_bonus REAL DEFAULT 0,
        join_code TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS rooms (
    room_id TEXT PRIMARY KEY,
    host_id INTEGER,
    guest_id INTEGER,
    host_deck TEXT,
    guest_deck TEXT,
    host_hp TEXT,
    guest_hp TEXT,
    host_max_hp TEXT,
    guest_max_hp TEXT,
    host_atk TEXT,
    host_chat_id INTEGER,
    guest_chat_id INTEGER,
    guest_atk TEXT,
    turn INTEGER DEFAULT 1,
    status TEXT DEFAULT 'waiting',
    current_turn TEXT DEFAULT 'host',
    host_ultimate INTEGER DEFAULT 0,
    guest_ultimate INTEGER DEFAULT 0,
    host_mana INTEGER DEFAULT 3,
    guest_mana INTEGER DEFAULT 3,
    host_action TEXT DEFAULT '{}',
    guest_action TEXT DEFAULT '{}',
    round_start_time INTEGER DEFAULT 0
)''')
    c.execute('''CREATE TABLE IF NOT EXISTS unit_levels (
        user_id INTEGER,
        unit_id TEXT,
        level INTEGER DEFAULT 1,
        copies INTEGER DEFAULT 1,
        PRIMARY KEY (user_id, unit_id)
    )''')
    conn.commit()
    conn.close()

# ==================== ДАННЫЕ ====================
CARDS = {
    "1": {"name": "⚔️ Воин", "hp": 90, "atk": 12, "def": 8, "rarity": 1, "ability": "Мощный удар", "skills": [
        {"name": "⚔️ Мощный удар", "desc": "Наносит 22 урона врагу. Комбо: следующий удар лучника +25%", "dmg": 22, "mana": 2, "type": "attack"},
        {"name": "🛡️ Защитная стойка", "desc": "Снижает следующий получаемый урон на 18", "def": 18, "mana": 1, "type": "defend"},
        {"name": "🔥 Ярость", "desc": "Следующая атака нанесет на 50% больше урона", "buff": "atk_50", "mana": 3, "type": "buff"}
    ]},
    "2": {"name": "🛡️ Танк", "hp": 125, "atk": 7, "def": 12, "rarity": 1, "ability": "Живая стена", "skills": [
        {"name": "🛡️ Блок", "desc": "Снижает следующий получаемый урон на 26", "def": 26, "mana": 2, "type": "defend"},
        {"name": "💪 Контратака", "desc": "Наносит 16 урона и снижает следующий получаемый урон на 13. Комбо: следующий удар воина +20%", "dmg": 16, "def": 13, "mana": 2, "type": "counter"},
        {"name": "🏰 Непоколебимый", "desc": "Невозможно оглушить, повышает защиту", "buff": "unstunnable", "mana": 3, "type": "buff"}
    ]},
    "3": {"name": "👹 Берсерк", "hp": 80, "atk": 18, "def": 5, "rarity": 2, "ability": "Неистовство", "skills": [
        {"name": "⚔️ Неистовство", "desc": "Наносит 28 урона врагу", "dmg": 28, "mana": 2, "type": "attack"},
        {"name": "🩸 Жажда крови", "desc": "Наносит 24 урона и восстанавливает 70% от нанесенного в виде HP", "dmg": 24, "lifesteal": 0.7, "mana": 3, "type": "lifesteal"},
        {"name": "💀 Безумие", "desc": "Наносит 35 урона врагу и 12 урона себе. Комбо: следующий удар вора x2", "dmg": 35, "self_dmg": 12, "mana": 3, "type": "berserk"}
    ]},
    "4": {"name": "⚡ Паладин", "hp": 100, "atk": 9, "def": 10, "rarity": 2, "ability": "Светлая защита", "skills": [
        {"name": "✨ Лечение", "desc": "Восстанавливает 24 HP. Комбо: следующее лечение барда +25%", "heal": 24, "mana": 2, "type": "heal"},
        {"name": "⚔️ Святой удар", "desc": "Наносит 20 урона врагу", "dmg": 20, "mana": 2, "type": "attack"},
        {"name": "🛡️ Аура защиты", "desc": "Повышает защиту всех союзников", "buff": "ally_def", "mana": 4, "type": "aura"}
    ]},
    "5": {"name": "🏹 Лучник", "hp": 60, "atk": 15, "def": 4, "rarity": 1, "ability": "Точный выстрел", "skills": [
        {"name": "🎯 Точный выстрел", "desc": "Наносит 24 урона врагу. Комбо с воином: +25% к урону (всего 30)", "dmg": 24, "mana": 2, "type": "attack"},
        {"name": "💨 Уклонение", "desc": "50% шанс полностью избежать следующей атаки", "dodge": 0.5, "mana": 2, "type": "dodge"},
        {"name": "🏹 Двойной выстрел", "desc": "Наносит два удара по 18 урона (всего 36)", "dmg": 18, "hits": 2, "mana": 4, "type": "multi"}
    ]},
    "6": {"name": "🔮 Маг", "hp": 50, "atk": 20, "def": 3, "rarity": 2, "ability": "Огненный шар", "skills": [
        {"name": "🔥 Огненный шар", "desc": "Наносит 32 магического урона врагу. Комбо: следующий удар некроманта +30%", "dmg": 32, "mana": 3, "type": "magic"},
        {"name": "❄️ Ледяная стрела", "desc": "Наносит 20 урона. 20% шанс оглушить врага на 1 ход", "dmg": 20, "stun_chance": 20, "mana": 2, "type": "magic"},
        {"name": "🛡️ Щит маны", "desc": "Создает щит, поглощающий 26 урона", "shield": 26, "mana": 2, "type": "shield"}
    ]},
    "7": {"name": "💀 Некромант", "hp": 65, "atk": 14, "def": 6, "rarity": 2, "ability": "Тёмная магия", "skills": [
        {"name": "🌑 Тёмная стрела", "desc": "Наносит 24 магического урона врагу", "dmg": 24, "mana": 2, "type": "magic"},
        {"name": "🩸 Вампиризм", "desc": "Наносит 22 урона и восстанавливает 70% от нанесенного в виде HP", "dmg": 22, "lifesteal": 0.7, "mana": 3, "type": "lifesteal"},
        {"name": "☠️ Проклятие", "desc": "Снижает атаку врага на 20%", "debuff": "atk_down", "mana": 2, "type": "debuff"}
    ]},
    "8": {"name": "🧪 Алхимик", "hp": 55, "atk": 11, "def": 5, "rarity": 2, "ability": "Ядовитый коктейль", "skills": [
        {"name": "🧪 Яд", "desc": "Наносит 14 урона и 8 урона каждый ход в течение 3 ходов", "dmg": 14, "dot": 8, "mana": 2, "type": "poison"},
        {"name": "⚗️ Зелье силы", "desc": "Повышает атаку союзников на 25%", "buff": "ally_atk", "mana": 3, "type": "buff"},
        {"name": "💣 Бомба", "desc": "Наносит 24 урона всем врагам", "dmg": 24, "aoe": True, "mana": 4, "type": "aoe"}
    ]},
    "9": {"name": "🗡️ Вор", "hp": 70, "atk": 16, "def": 6, "rarity": 2, "ability": "Удар в спину", "skills": [
        {"name": "🗡️ Удар в спину", "desc": "Наносит 28 урона (игнорирует 50% защиты)", "dmg": 28, "backstab": True, "mana": 2, "type": "attack"},
        {"name": "💨 Исчезновение", "desc": "70% шанс полностью избежать следующей атаки", "dodge": 0.7, "mana": 3, "type": "dodge"},
        {"name": "🎲 Критический удар", "desc": "Следующая атака нанесет двойной урон (x2)", "crit": 2.0, "mana": 3, "type": "crit"}
    ]},
    "10": {"name": "🎻 Бард", "hp": 60, "atk": 8, "def": 7, "rarity": 2, "ability": "Боевая песня", "skills": [
        {"name": "🎵 Боевая песня", "desc": "Повышает атаку всех союзников на 20%", "buff": "ally_atk", "mana": 3, "type": "buff"},
        {"name": "🎶 Лечение", "desc": "Восстанавливает 20 HP. Комбо с паладином: +25% к лечению (всего 25)", "heal": 20, "mana": 2, "type": "heal"},
        {"name": "🎼 Героизм", "desc": "Повышает все характеристики союзников на 15%", "buff": "all_stats", "mana": 5, "type": "ultimate_buff"}
    ]}
}

COMBOS = {
    "warrior_archer": {
        "skills": [("1", "⚔️ Мощный удар"), ("5", "🎯 Точный выстрел")],
        "bonus": "atk", "value": 25, "name": "🔥 Обстрел", "desc": "Воин атакует, затем Лучник добивает"
    },
    "mage_necro": {
        "skills": [("6", "🔥 Огненный шар"), ("7", "🌑 Тёмная стрела")],
        "bonus": "magic", "value": 30, "name": "🔥 Тёмная магия", "desc": "Двойной магический удар"
    },
    "paladin_bard": {
        "skills": [("4", "✨ Лечение"), ("10", "🎶 Лечение")],
        "bonus": "heal", "value": 25, "name": "✨ Божественная защита", "desc": "Двойное лечение"
    },
    "tank_counter": {
        "skills": [("2", "💪 Контратака"), ("1", "⚔️ Мощный удар")],
        "bonus": "counter", "value": 20, "name": "💪 Контратака", "desc": "Танк держит удар, Воин контратакует"
    },
    "berserk_rage": {
        "skills": [("3", "💀 Безумие"), ("9", "🎲 Критический удар")],
        "bonus": "crit", "value": 40, "name": "💀 Смертельный удар", "desc": "Берсерк и Вор наносят критический урон"
    }
}

PACKS = {
    "basic": {"name": "📦 Обычный", "price": 50, "pool": ["1", "2", "5"]},
    "rare": {"name": "💎 Редкий", "price": 150, "pool": ["1", "2", "3", "4", "5", "6", "7"]},
    "epic": {"name": "👑 Эпический", "price": 300, "pool": ["3", "4", "6", "7", "8", "9", "10"]}
}

# ✅ Правильное чтение токена из переменных Render
BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    print("❌ ОШИБКА: Токен не найден в переменных окружения!")
    exit()

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher()

def main_kb(uid=None):
    """Основное меню (показывает только зарегистрированным)"""
    if uid and not is_registered(uid):
        return ReplyKeyboardMarkup(keyboard=[], resize_keyboard=True)
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="⚔️ LIVE"), KeyboardButton(text="🌑 Рейд")],
        [KeyboardButton(text="🛒 Магазин"), KeyboardButton(text="🎒 Инвентарь")],
        [KeyboardButton(text="🏗️ База"), KeyboardButton(text="🏛️ Клан")],
        [KeyboardButton(text="🏆 Рейтинг"), KeyboardButton(text="👤 Профиль")]
    ], resize_keyboard=True, persistent=True)

# ==================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ====================
def get_user(uid):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT * FROM players WHERE user_id=?", (uid,))
    row = c.fetchone()
    if not row:
        c.execute("""INSERT INTO players VALUES 
            (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (uid, "Игрок", 500, 1000, 5, int(time.time()), None, 
             '{"1":5,"2":3}', '{"basic":2,"rare":0,"epic":0}', 
             '["1","2","3","4","5","6"]', 1, 0, 
             '{"max_rarity":1,"relic_slots":0,"trap_level":0,"equipment_slots":0,"mana_regen":0,"crit_chance":0}', 
             '{}', '{}', 0, 0))
        conn.commit()
        row = c.execute("SELECT * FROM players WHERE user_id=?", (uid,)).fetchone()
    conn.close()
    return row

def is_registered(uid):
    """Проверяет, зарегистрирован ли пользователь"""
    u = get_user(uid)
    return u[1] != "Игрок"

def get_empty_kb():
    """Пустая клавиатура для незарегистрированных"""
    return ReplyKeyboardMarkup(keyboard=[], resize_keyboard=True)

def update_user(uid, **kwargs):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    for k, v in kwargs.items():
        if isinstance(v, (dict, list)):
            v = json.dumps(v)
        c.execute(f"UPDATE players SET {k}=? WHERE user_id=?", (v, uid))
    conn.commit()
    conn.close()

def get_clan(cid):
    if not cid: return None
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT * FROM clans WHERE id=?", (cid,))
    row = c.fetchone()
    conn.close()
    return row

def update_clan(cid, **kwargs):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    for k, v in kwargs.items():
        c.execute(f"UPDATE clans SET {k}=? WHERE id=?", (v, cid))
    conn.commit()
    conn.close()

def check_energy(uid):
    u = get_user(uid)
    current_time = int(time.time())
    energy = u[4]
    last_restore = u[5]
    if current_time - last_restore >= 14400 and energy < 5:
        hours_passed = (current_time - last_restore) // 14400
        new_energy = min(5, energy + hours_passed)
        if new_energy > energy:
            update_user(uid, energy=new_energy, energy_time=current_time)
            return new_energy
    return energy

def has_emoji(text):
    emoji_pattern = re.compile("[" u"\U0001F600-\U0001F64F" u"\U0001F300-\U0001F5FF" 
        u"\U0001F680-\U0001F6FF" u"\U0001F1E0-\U0001F1FF" u"\U00002702-\U000027B0" "]+", flags=re.UNICODE)
    return bool(emoji_pattern.search(text))

def get_unit_level(uid, unit_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT level, copies FROM unit_levels WHERE user_id=? AND unit_id=?", (uid, unit_id))
    row = c.fetchone()
    conn.close()
    return (row[0], row[1]) if row else (1, 1)

def upgrade_unit(uid, unit_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT cards FROM players WHERE user_id=?", (uid,))
    cards = json.loads(c.fetchone()[0])
    c.execute("SELECT level FROM unit_levels WHERE user_id=? AND unit_id=?", (uid, unit_id))
    row = c.fetchone()
    current_level = row[0] if row else 1
    conn.close()
    owned = cards.get(unit_id, 0)
    required = 2 ** current_level
    if owned >= required:
        new_level = current_level + 1
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("INSERT OR REPLACE INTO unit_levels VALUES (?,?,?,?)", (uid, unit_id, new_level, owned))
        conn.commit()
        conn.close()
        return True, new_level
    return False, required - owned

def render_hp(current, maximum, length=10):
    current = max(0, int(current))
    maximum = max(1, int(maximum))
    filled = int(length * current / maximum)
    return f"[{'█' * filled}{'░' * (length - filled)}] {current}/{maximum}"

# ==================== ОСНОВНЫЕ КОМАНДЫ ====================
@dp.message(Command("start"))
async def cmd_start(msg: types.Message, state: FSMContext):
    u = get_user(msg.from_user.id)
    if u[1] == "Игрок":
        await msg.answer("<b>🎮 ARENA DRAFT v4.7</b>\n\nВведи имя (2-15 символов, без смайликов):")
        await state.set_state(States.reg_name)
        return
    energy = check_energy(msg.from_user.id)
    clan_txt = ""
    if u[6]:
        clan = get_clan(u[6])
        if clan: clan_txt = f"\n🏛️ {clan[1]} {clan[2] or ''}"
    await msg.answer(f"<b>🎮 ARENA DRAFT</b>{clan_txt}\n\n👤 {u[1]} | 🏗️ База: Ур.{u[10]}\n"
        f"🪙 {u[2]} | ⭐ {u[3]} | ⚡ {energy}/5\n🏆 {u[14] or 0} побед", reply_markup=main_kb())


@dp.message(States.reg_name)
async def set_name(msg: types.Message, state: FSMContext):
    name = msg.text.strip()
    if has_emoji(name):
        await msg.answer("❌ В имени нельзя использовать смайлики!")
        return
    if 2 <= len(name) <= 15:
        update_user(msg.from_user.id, name=name)
        await state.clear()  # ✅ Очищаем состояние
        await msg.answer(f"✅ Регистрация завершена!\n\n👤 Ваше имя: <b>{name}</b>\n\nТеперь вам доступны все функции бота!", 
                        reply_markup=main_kb(msg.from_user.id))
    else:
        await msg.answer("❌ Имя должно быть 2-15 символов:")

@dp.message(F.text == "🎒 Инвентарь")
async def inventory(msg: types.Message, state: FSMContext):
    u = get_user(msg.from_user.id)
    if u[1] == "Игрок":
        await msg.answer("❌ Сначала зарегистрируйтесь! Нажмите /start")
        return
    cards = json.loads(u[7] if u[7] else '{"1":5,"2":3}')
    packs = json.loads(u[8] if u[8] else '{"basic":2,"rare":0,"epic":0}')
    deck = json.loads(u[9] if u[9] else '["1","2","3","4","5","6"]')
    text = "<b>🎒 ИНВЕНТАРЬ</b>\n\n<b>📦 Паки:</b>\n"
    pack_kb = []
    for pid, cnt in packs.items():
        if cnt > 0:
            text += f"{PACKS[pid]['name']} x{cnt}\n"
            pack_kb.append([InlineKeyboardButton(text=f"Открыть {PACKS[pid]['name']}", callback_data=f"open_pack_btn:{pid}")])
    if not pack_kb: text += "Пусто\n"
    text += "\n<b>🎴 Колода (6 слотов):</b>\n"
    for i, cid in enumerate(deck, 1):
        if cid and cid in CARDS:
            c = CARDS[cid]
            lvl, _ = get_unit_level(msg.from_user.id, cid)
            text += f"{i}. {c['name']} (Ур.{lvl})\n"
        else:
            text += f"{i}. [Пусто]\n"
    text += "\n<b>📚 Карты для улучшения:</b>\n"
    upgrade_kb = []
    for cid, cnt in cards.items():
        if cnt > 0 and cid in CARDS:
            c = CARDS[cid]
            lvl, _ = get_unit_level(msg.from_user.id, cid)
            required = 2 ** lvl
            text += f"{c['name']} x{cnt} (Ур.{lvl}, нужно:{required})\n"
            if cnt >= required:
                upgrade_kb.append([InlineKeyboardButton(text=f"⬆️ {c['name']}", callback_data=f"upgrade_unit:{cid}")])
    kb = pack_kb + upgrade_kb + [
        [InlineKeyboardButton(text="🎴 Редактировать колоду", callback_data="deck_edit")],
        [InlineKeyboardButton(text="📖 Info о картах", callback_data="card_info")],
        [InlineKeyboardButton(text="📜 Мануал", callback_data="manual_main")]
    ]
    await msg.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

@dp.callback_query(F.data == "card_info")
async def card_info(cb: types.CallbackQuery):
    text = "<b>📖 ИНФОРМАЦИЯ О КАРТАХ</b>\n\n"
    for cid, c in CARDS.items():
        text += f"<b>{c['name']}</b> (Редкость:{c['rarity']})\n"
        text += f"❤️ HP: {c['hp']} | ⚔️ ATK: {c['atk']} | 🛡 DEF: {c['def']}\n"
        text += f"Способность: {c['ability']}\n"
        for skill in c['skills']:
            text += f"  • {skill['name']}: {skill['desc']} ({skill['mana']}💧)\n"
        text += "\n"
    kb = [[InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main")]]
    await cb.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
    await cb.answer()

@dp.callback_query(F.data.startswith("open_pack_btn:"))
async def open_pack_btn(cb: types.CallbackQuery, state: FSMContext):
    pid = cb.data.split(":")[1]
    u = get_user(cb.from_user.id)
    packs = json.loads(u[8])
    if packs.get(pid, 0) <= 0:
        await cb.answer("❌ Нет пака!", show_alert=True)
        return
    await state.update_data(open_pack=pid)
    await state.set_state(States.pack_open)
    await cb.message.answer(f"📦 <b>{PACKS[pid]['name']}</b>\n\nОткрыть?",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🎉 Открыть", callback_data=f"open_pack:{pid}")],
            [InlineKeyboardButton(text="В меню", callback_data="menu")]
        ]))
    await cb.answer()

@dp.callback_query(F.data.startswith("open_pack:"))
async def open_pack(cb: types.CallbackQuery, state: FSMContext):
    pid = cb.data.split(":")[1]
    pack = PACKS[pid]
    u = get_user(cb.from_user.id)
    packs = json.loads(u[8])
    if packs.get(pid, 0) <= 0:
        await cb.answer("❌ Нет пака!", show_alert=True)
        return
    packs[pid] -= 1
    cards = json.loads(u[7])
    received = []
    for _ in range(2):
        card = random.choice(pack["pool"])
        cards[card] = cards.get(card, 0) + 1
        received.append(CARDS[card])
    update_user(cb.from_user.id, packs=packs, cards=cards)
    text = "🎉 <b>Открыто!</b>\n\n"
    for c in received:
        text += f"✅ {c['name']}\n   ❤️ {c['hp']} | ⚔️ {c['atk']}\n"
    await cb.message.answer(text, reply_markup=main_kb())
    await cb.answer()

@dp.callback_query(F.data.startswith("upgrade_unit:"))
async def upgrade_unit_handler(cb: types.CallbackQuery, state: FSMContext):
    unit_id = cb.data.split(":")[1]
    success, result = upgrade_unit(cb.from_user.id, unit_id)
    if success:
        await cb.message.answer(f"✅ {CARDS[unit_id]['name']} улучшен до уровня {result}!")
    else:
        await cb.message.answer(f"❌ Нужно ещё {result} копий!")
    await cb.answer()

@dp.callback_query(F.data == "deck_edit")
async def deck_edit(cb: types.CallbackQuery, state: FSMContext):
    u = get_user(cb.from_user.id)
    deck = json.loads(u[9] if u[9] else '["1","2","3","4","5","6"]')
    while len(deck) < 6:
        deck.append(None)
    text = "<b>🎴 РЕДАКТИРОВАНИЕ КОЛОДЫ</b>\n\n"
    kb = []
    for i in range(6):
        cid = deck[i]
        if cid and cid in CARDS:
            c = CARDS[cid]
            text += f"<b>Слот {i+1}:</b> {c['name']}\n"
        else:
            text += f"<b>Слот {i+1}:</b> [Пусто]\n"
        kb.append([InlineKeyboardButton(text=f"✏️ Слот {i+1}", callback_data=f"deck_set:{i}")])
    await cb.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
    await cb.answer()

@dp.callback_query(F.data.startswith("deck_set:"))
async def deck_set(cb: types.CallbackQuery, state: FSMContext):
    slot = int(cb.data.split(":")[1])
    u = get_user(cb.from_user.id)
    cards = json.loads(u[7])
    text = "<b>Выбери карту для слота:</b>\n\n"
    kb = []
    for cid, cnt in cards.items():
        if cnt > 0 and cid in CARDS:
            c = CARDS[cid]
            text += f"{c['name']} x{cnt}\n"
            kb.append([InlineKeyboardButton(text=f"Выбрать {c['name']}", callback_data=f"deck_choose:{slot}:{cid}")])
    kb.append([InlineKeyboardButton(text="🔙 К колоде", callback_data="deck_edit")])
    await cb.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
    await cb.answer()

@dp.callback_query(F.data.startswith("deck_choose:"))
async def deck_choose(cb: types.CallbackQuery, state: FSMContext):
    _, slot_idx, cid = cb.data.split(":")
    slot_idx = int(slot_idx)
    u = get_user(cb.from_user.id)
    deck = json.loads(u[9])
    cards = json.loads(u[7])
    
    while len(deck) < 6:
        deck.append(None)
    
    # ✅ ВОЗВРАЩАЕМ СТАРУЮ КАРТУ В ИНВЕНТАРЬ
    old_card = deck[slot_idx]
    if old_card and old_card != cid:  # Если есть старая карта и она не та же самая
        cards[old_card] = cards.get(old_card, 0) + 1
        await cb.answer(f"📦 {CARDS[old_card]['name']} возвращена в инвентарь")
    
    # Ставим новую карту в слот
    deck[slot_idx] = cid
    
    # Убираем новую карту из инвентаря
    if cid in cards:
        cards[cid] = cards.get(cid, 0) - 1
        if cards[cid] <= 0:
            del cards[cid]
    
    update_user(cb.from_user.id, deck=deck, cards=cards)
    await cb.message.answer(f"✅ Слот {slot_idx+1}: {CARDS[cid]['name']}")
    await deck_edit(cb, state)
    await cb.answer()

@dp.callback_query(F.data == "manual_main")
async def manual_main(cb: types.CallbackQuery):
    text = "<b>📜 МАНУАЛ</b>\n\nВыберите раздел:\n\n"
    kb = [
        [InlineKeyboardButton(text="🎴 Юниты", callback_data="manual_units")],
        [InlineKeyboardButton(text="⚔️ Комбо", callback_data="manual_combos")],
        [InlineKeyboardButton(text="🏗️ База", callback_data="manual_base")],
        [InlineKeyboardButton(text="В меню", callback_data="menu")]
    ]
    await cb.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
    await cb.answer()

@dp.callback_query(F.data == "manual_units")
async def manual_units(cb: types.CallbackQuery):
    text = "<b>🎴 ЮНИТЫ</b>\n\n"
    text += "Вся информация о юнитах доступна в разделе\n"
    text += "📖 <b>Info о картах</b>\n\n"
    text += "Там указаны:\n"
    text += "• Характеристики (HP, ATK, DEF)\n"
    text += "• Способности и навыки\n"
    text += "• Стоимость маны\n"
    kb = [[InlineKeyboardButton(text="🔙 К мануалу", callback_data="manual_main")]]
    await cb.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
    await cb.answer()

@dp.callback_query(F.data == "manual_combos")
async def manual_combos(cb: types.CallbackQuery):
    text = "<b>⚔️ КОМБИНАЦИИ</b>\n\n"
    for combo_id, combo in COMBOS.items():
        units_names = " + ".join([f"{CARDS[uid]['name']} ({sn})" for uid, sn in combo['skills']])
        text += f"<b>{combo['name']}</b>\n{combo['desc']}\n"
        text += f"Навыки: {units_names}\n"
        text += f"Бонус: +{combo['value']}% к {combo['bonus']}\n\n"
    kb = [[InlineKeyboardButton(text="🔙 К мануалу", callback_data="manual_main")]]
    await cb.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
    await cb.answer()

@dp.callback_query(F.data == "manual_base")
async def manual_base(cb: types.CallbackQuery):
    text = "<b>🏗️ БАЗА - ДЕРЕВО РАЗВИТИЯ</b>\n\n"
    text += "<b>Уровень базы:</b> Главный прогресс аккаунта\n"
    text += "• Открывает доступ к навыкам\n"
    text += "• Повышает максимальную редкость карт\n\n"
    text += "<b>Навыки:</b>\n"
    text += "📦 <b>Редкие карты</b> - Открывает карты более высокой редкости в магазине\n"
    text += "💎 <b>Слоты реликвий</b> - Дополнительные слоты для экипировки реликвий\n"
    text += "🪤 <b>Ловушки</b> - Защита базы в рейдах (дебаффы атакующим)\n"
    text += "⚔️ <b>Слоты экипировки</b> - Дополнительные слоты для оружия/брони\n"
    text += "💧 <b>Реген маны</b> - +1 мана каждый ход в бою\n"
    text += "🎯 <b>Шанс крита</b> - +5% к шансу критического удара\n"
    kb = [[InlineKeyboardButton(text="🔙 К мануалу", callback_data="manual_main")]]
    await cb.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
    await cb.answer()

@dp.message(F.text == "🏗️ База")
async def base_menu(msg: types.Message, state: FSMContext):
    u = get_user(msg.from_user.id)
    if u[1] == "Игрок":
        await msg.answer("❌ Сначала зарегистрируйтесь! Нажмите /start")
        return
    base_skills = json.loads(u[12])
    text = f"<b>🏗️ БАЗА - УРОВЕНЬ {u[10]}</b>\n"
    text += f"Опыт: {u[11]}/1000\n\n"
    text += f"<b>Открыто:</b>\n"
    text += f"📦 Макс. редкость: {base_skills.get('max_rarity', 1)}/3\n"
    text += f"💎 Слоты реликвий: {base_skills.get('relic_slots', 0)}/3\n"
    text += f"🪤 Ловушки: Ур.{base_skills.get('trap_level', 0)}/3\n"
    text += f"⚔️ Слоты экип.: {base_skills.get('equipment_slots', 0)}/3\n"
    text += f"💧 Реген маны: {base_skills.get('mana_regen', 0)}/3\n"
    text += f"🎯 Шанс крита: {base_skills.get('crit_chance', 0)*5}%\n\n"
    kb = [
        [InlineKeyboardButton(text="⬆️ Улучшить базу", callback_data="base_upgrade_main")],
        [InlineKeyboardButton(text="🌳 Дерево навыков", callback_data="base_skill_tree")],
        [InlineKeyboardButton(text="В меню", callback_data="menu")]
    ]
    await msg.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

@dp.callback_query(F.data == "base_upgrade_main")
async def base_upgrade_main(cb: types.CallbackQuery, state: FSMContext):
    u = get_user(cb.from_user.id)
    cost = u[10] * 500
    if u[2] >= cost:
        update_user(cb.from_user.id, gold=u[2]-cost, base_level=u[10]+1, base_xp=0)
        await cb.message.answer(f"✅ База улучшена до уровня {u[10]+1}!")
    else:
        await cb.answer(f"❌ Нужно {cost}🪙", show_alert=True)
    await cb.answer()

@dp.callback_query(F.data == "base_skill_tree")
async def base_skill_tree(cb: types.CallbackQuery, state: FSMContext):
    u = get_user(cb.from_user.id)
    base_skills = json.loads(u[12])
    text = "<b>🌳 ДЕРЕВО НАВЫКОВ</b>\n\n"
    text += "<i>Нажми на навык для улучшения</i>\n\n"
    kb = []
    skills_info = {
        "max_rarity": {"name": "📦 Редкие карты", "level": base_skills.get("max_rarity", 1), "max": 3, "desc": "Открывает карты высокой редкости"},
        "relic_slots": {"name": "💎 Слоты реликвий", "level": base_skills.get("relic_slots", 0), "max": 3, "desc": "+1 слот для реликвий"},
        "trap_level": {"name": "🪤 Ловушки", "level": base_skills.get("trap_level", 0), "max": 3, "desc": "Защита в рейдах"},
        "equipment_slots": {"name": "⚔️ Слоты экип.", "level": base_skills.get("equipment_slots", 0), "max": 3, "desc": "+1 слот экипировки"},
        "mana_regen": {"name": "💧 Реген маны", "level": base_skills.get("mana_regen", 0), "max": 3, "desc": "+1 мана/ход"},
        "crit_chance": {"name": "🎯 Шанс крита", "level": base_skills.get("crit_chance", 0), "max": 3, "desc": "+5% крита"}
    }
    for skill_id, info in skills_info.items():
        cost = (info["level"] + 1) * 300
        text += f"<b>{info['name']}</b> (Ур.{info['level']}/{info['max']})\n<i>{info['desc']}</i>\n"
        if info["level"] < info["max"]:
            kb.append([InlineKeyboardButton(text=f"⬆️ {info['name']} ({cost}🪙)", callback_data=f"base_skill_up:{skill_id}")])
        text += "\n"
    await cb.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
    await cb.answer()

@dp.callback_query(F.data.startswith("base_skill_up:"))
async def base_skill_up(cb: types.CallbackQuery, state: FSMContext):
    skill_id = cb.data.split(":")[1]
    u = get_user(cb.from_user.id)
    base_skills = json.loads(u[12])
    current_level = base_skills.get(skill_id, 0 if skill_id != "max_rarity" else 1)
    cost = (current_level + 1) * 300
    if u[2] >= cost:
        base_skills[skill_id] = current_level + 1
        update_user(cb.from_user.id, gold=u[2]-cost, base_skills=base_skills)
        await cb.message.answer(f"✅ Навык улучшен!")
    else:
        await cb.answer(f"❌ Нужно {cost}🪙", show_alert=True)
    await cb.answer()

@dp.message(F.text == "🏛️ Клан")
async def clan_menu(msg: types.Message, state: FSMContext):
    u = get_user(msg.from_user.id)
    if u[1] == "Игрок":
        await msg.answer("❌ Сначала зарегистрируйтесь! Нажмите /start")
        return
    if not u[6]:
        await msg.answer("<b>🏛️ КЛАН</b>\n\nУ тебя нет клана",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="➕ Создать клан", callback_data="clan_create")],
                [InlineKeyboardButton(text="🔍 Вступить в клан", callback_data="clan_join_menu")],
                [InlineKeyboardButton(text="В меню", callback_data="menu")]
            ]))
        return
    clan = get_clan(u[6])
    if not clan:
        await msg.answer("❌ Ошибка клана")
        return
    is_leader = clan[3] == msg.from_user.id
    join_code = clan[9] if len(clan) > 9 and clan[9] else str(clan[0])
    text = f"<b>🏛️ {clan[1]}</b> {clan[2] or ''}\n"
    text += f"ID: <code>{join_code}</code>\n"
    text += f"Уровень: {clan[4]}\nУчастников: {clan[5]}\n"
    text += f"{'👑 Лидер' if is_leader else '👤 Участник'}\n\n"
    text += f"<b>Бонусы:</b>\n"
    text += f"❤️ HP: +{clan[8]}%\n⚔️ ATK: +{clan[6]}%\n🛡 DEF: +{clan[7]}%\n"
    kb = [[InlineKeyboardButton(text="🚪 Выйти", callback_data="clan_leave")]]
    if is_leader:
        kb.append([InlineKeyboardButton(text="✏️ Сменить смайлик", callback_data="clan_emoji")])
        kb.append([InlineKeyboardButton(text="⬆️ Прокачать", callback_data="clan_upgrades")])
    await msg.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

@dp.callback_query(F.data == "clan_create")
async def clan_create(cb: types.CallbackQuery, state: FSMContext):
    await cb.message.answer("<b>Название клана (3-15 символов):</b>")
    await state.set_state(States.clan_input)
    await cb.answer()

@dp.message(States.clan_input)
async def clan_name(msg: types.Message, state: FSMContext):
    if 3 <= len(msg.text) <= 15:
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        try:
            c.execute("INSERT INTO clans (name, leader_id) VALUES (?,?)", (msg.text.strip(), msg.from_user.id))
            cid = c.lastrowid
            conn.commit()
            update_user(msg.from_user.id, clan_id=cid)
            await msg.answer(f"✅ Клан '{msg.text}' создан! ID: {cid}", reply_markup=main_kb())
        except:
            await msg.answer("❌ Имя занято:")
        finally:
            conn.close()
    else:
        await msg.answer("❌ 3-15 символов:")
    await state.clear()

@dp.callback_query(F.data == "clan_join_menu")
async def clan_join_menu(cb: types.CallbackQuery, state: FSMContext):
    await cb.message.answer("<b>🔍 ВСТУПЛЕНИЕ В КЛАН</b>\n\n"
        "Введи ID клана (число), который дал тебе лидер:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="В меню", callback_data="menu")]]))
    await state.set_state(States.clan_join_code)
    await cb.answer()

@dp.message(States.clan_join_code)
async def clan_join_code(msg: types.Message, state: FSMContext):
    code = msg.text.strip()
    try:
        clan_id = int(code)
    except:
        await msg.answer("❌ ID должен быть числом!")
        return
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT id, members FROM clans WHERE id=?", (clan_id,))
    row = c.fetchone()
    if row:
        update_user(msg.from_user.id, clan_id=clan_id)
        c.execute("UPDATE clans SET members=members+1 WHERE id=?", (clan_id,))
        conn.commit()
        conn.close()
        await msg.answer("✅ Ты вступил в клан!", reply_markup=main_kb())
    else:
        await msg.answer("❌ Клан не найден!")
    await state.clear()

@dp.callback_query(F.data == "clan_emoji")
async def clan_emoji_set(cb: types.CallbackQuery, state: FSMContext):
    await cb.message.answer("<b>Введи 1 смайлик для клана:</b>")
    await state.set_state(States.clan_emoji)
    await cb.answer()

@dp.message(States.clan_emoji)
async def clan_emoji_process(msg: types.Message, state: FSMContext):
    emoji = msg.text.strip()
    emoji_count = len([c for c in emoji if ord(c) > 127])
    if emoji_count != 1:
        await msg.answer(f"❌ Можно только 1 смайлик! Ты ввёл {emoji_count}")
        return
    u = get_user(msg.from_user.id)
    clan = get_clan(u[6])
    if clan and clan[3] == msg.from_user.id:
        update_clan(clan[0], emoji=emoji)
        await msg.answer(f"✅ Смайлик: {emoji}", reply_markup=main_kb())
    else:
        await msg.answer("❌ Ошибка!")
    await state.clear()

@dp.callback_query(F.data == "clan_upgrades")
async def clan_upgrades(cb: types.CallbackQuery, state: FSMContext):
    u = get_user(cb.from_user.id)
    clan = get_clan(u[6])
    if not clan or clan[3] != cb.from_user.id:
        await cb.answer("❌ Только лидер!", show_alert=True)
        return
    cost = clan[4] * 300
    text = f"<b>🏛️ УЛУЧШЕНИЯ</b>\n\nТекущий уровень: {clan[4]}\nСтоимость: {cost}🪙\n\n"
    kb = [
        [InlineKeyboardButton(text=f"⚔️ Урон +1% ({cost}🪙)", callback_data=f"clan_upg:damage:{cost}")],
        [InlineKeyboardButton(text=f"🛡 Защита +1% ({cost}🪙)", callback_data=f"clan_upg:defense:{cost}")],
        [InlineKeyboardButton(text=f"❤️ HP +2% ({cost}🪙)", callback_data=f"clan_upg:hp:{cost}")],
        [InlineKeyboardButton(text="В меню", callback_data="menu")]
    ]
    await cb.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
    await cb.answer()

@dp.callback_query(F.data.startswith("clan_upg:"))
async def clan_upg(cb: types.CallbackQuery, state: FSMContext):
    _, stat, cost = cb.data.split(":")
    cost = int(cost)
    u = get_user(cb.from_user.id)
    clan = get_clan(u[6])
    if u[2] < cost:
        await cb.answer("❌ Мало золота!", show_alert=True)
        return
    if stat == "damage":
        update_clan(clan[0], clan_damage_bonus=clan[6]+1, level=clan[4]+1)
    elif stat == "defense":
        update_clan(clan[0], clan_defense_bonus=clan[7]+1, level=clan[4]+1)
    else:
        update_clan(clan[0], clan_hp_bonus=clan[8]+2, level=clan[4]+1)
    update_user(cb.from_user.id, gold=u[2]-cost)
    await cb.message.answer(f"✅ Улучшено!")
    await cb.answer()

@dp.callback_query(F.data == "clan_leave")
async def clan_leave(cb: types.CallbackQuery):
    u = get_user(cb.from_user.id)
    clan = get_clan(u[6])
    if clan and clan[3] == cb.from_user.id:
        await cb.answer("❌ Лидер не может выйти!", show_alert=True)
        return
    update_user(cb.from_user.id, clan_id=None)
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("UPDATE clans SET members=members-1 WHERE id=?", (u[6],))
    conn.commit()
    conn.close()
    await cb.message.answer("✅ Ты вышел из клана", reply_markup=main_kb())
    await cb.answer()

@dp.message(F.text == "🛒 Магазин")
async def shop(msg: types.Message, state: FSMContext):
    u = get_user(msg.from_user.id)
    if u[1] == "Игрок":
        await msg.answer("❌ Сначала зарегистрируйтесь! Нажмите /start")
        return
    
    base_skills = json.loads(u[12])
    max_rarity = base_skills.get('max_rarity', 1)
    
    text = f"<b>🛒 МАГАЗИН</b>\n🪙 {u[2]}\n"
    text += f"<i>Доступна редкость: до {max_rarity}/3</i>\n\n"
    
    kb = []
    for pid, pack in PACKS.items():
        # Проверяем редкость пака
        pack_rarity = 1 if pid == "basic" else (2 if pid == "rare" else 3)
        if pack_rarity <= max_rarity:  # Показываем только доступные паки
            text += f"{pack['name']} - {pack['price']}🪙\n"
            kb.append([InlineKeyboardButton(text=f"Купить {pack['name']}", callback_data=f"buy:{pid}")])
    await msg.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

@dp.callback_query(F.data.startswith("buy:"))
async def buy_pack_menu(cb: types.CallbackQuery, state: FSMContext):
    pid = cb.data.split(":")[1]
    pack = PACKS[pid]
    u = get_user(cb.from_user.id)
    if u[2] < pack["price"]:
        await cb.answer("❌ Мало золота!", show_alert=True)
        return
    packs = json.loads(u[8])
    packs[pid] = packs.get(pid, 0) + 1
    update_user(cb.from_user.id, gold=u[2]-pack["price"], packs=packs)
    await cb.message.answer(f"✅ Куплен {pack['name']}! Открой в инвентаре.", reply_markup=main_kb())
    await cb.answer()

@dp.message(F.text == "🏆 Рейтинг")
async def rating(msg: types.Message):
    u = get_user(msg.from_user.id)
    if u[1] == "Игрок":
        await msg.answer("❌ Сначала зарегистрируйтесь! Нажмите /start")
        return
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👤 Топ игроков", callback_data="rating_players")],
        [InlineKeyboardButton(text="🏛️ Топ кланов", callback_data="rating_clans")]
    ])
    await msg.answer("<b>🏆 РЕЙТИНГ</b>\n\nВыбери категорию:", reply_markup=kb)

@dp.callback_query(F.data == "rating_players")
async def rating_players(cb: types.CallbackQuery):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT name, rating FROM players ORDER BY rating DESC LIMIT 5")
    rows = c.fetchall()
    conn.close()
    text = "<b>👤 ТОП ИГРОКОВ</b>\n\n"
    for i, r in enumerate(rows, 1):
        text += f"{i}. {r[0] or 'Игрок'} | ⭐ {r[1]}\n"
    await cb.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 К рейтингу", callback_data="rating_menu_back")]
    ]))
    await cb.answer()

@dp.callback_query(F.data == "rating_clans")
async def rating_clans(cb: types.CallbackQuery):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT name, level, members FROM clans ORDER BY level DESC LIMIT 5")
    rows = c.fetchall()
    conn.close()
    text = "<b>🏛️ ТОП КЛАНОВ</b>\n\n"
    for i, r in enumerate(rows, 1):
        text += f"{i}. {r[0]} | Ур.{r[1]} | 👥 {r[2]}\n"
    await cb.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 К рейтингу", callback_data="rating_menu_back")]
    ]))
    await cb.answer()

@dp.callback_query(F.data == "rating_menu_back")
async def rating_menu_back(cb: types.CallbackQuery):
    await rating(cb.message)
    await cb.answer()

@dp.message(F.text == "👤 Профиль")
async def profile(msg: types.Message):
    u = get_user(msg.from_user.id)
    if u[1] == "Игрок":
        await msg.answer("❌ Сначала зарегистрируйтесь! Нажмите /start")
        return
    energy = check_energy(msg.from_user.id)
    clan_txt = ""
    if u[6]:
        clan = get_clan(u[6])
        if clan: clan_txt = f"\n🏛️ {clan[1]}"
    wins = u[14] if u[14] else 0
    losses = u[15] if u[15] else 0
    await msg.answer(
        f"<b>👤 {u[1]}</b>{clan_txt}\n\n"
        f"🪙 {u[2]} | ⭐ {u[3]} | ⚡ {energy}/5\n"
        f"🏆 {wins} побед | {losses} поражений\n"
        f"🏗️ База: Ур.{u[10]}"
    )

# ==================== БОЕВАЯ СИСТЕМА (LIVE) ====================
@dp.message(F.text == "⚔️ LIVE")
async def live_menu(msg: types.Message, state: FSMContext):
    u = get_user(msg.from_user.id)
    if u[1] == "Игрок":
        await msg.answer("❌ Сначала зарегистрируйтесь! Нажмите /start")
        return
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔴 Создать комнату", callback_data="live_create")],
        [InlineKeyboardButton(text="🔵 Присоединиться", callback_data="live_join_menu")],
        [InlineKeyboardButton(text="В меню", callback_data="menu")]
    ])
    await msg.answer("<b>⚔️ LIVE ДУЭЛЬ</b>\n\nВыбери действие:", reply_markup=kb)

@dp.callback_query(F.data == "live_create")
async def live_create(cb: types.CallbackQuery, state: FSMContext):
    room_id = f"{cb.from_user.id}{random.randint(1000,9999)}"
    u = get_user(cb.from_user.id)
    deck = json.loads(u[9])
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("""INSERT OR REPLACE INTO rooms 
        (room_id, host_id, guest_id, host_chat_id, host_deck, guest_deck, status, current_turn, host_mana, guest_mana) 
        VALUES (?,?,?,?,?,?,?,?,?,?)""",
        (room_id, cb.from_user.id, None, cb.from_user.id, json.dumps(deck), "", "waiting", "host", 3, 3))
    conn.commit()
    conn.close()
    await state.update_data(room_id=room_id, player_role="host")
    await state.set_state(States.live_wait)
    await cb.message.answer(
        f"🔴 <b>Комната создана!</b>\n\n"
        f"<b>ID:</b> <code>{room_id}</code>\n"
        f"Твоя колода: {len(deck)} юнитов\n\n"
        f"Жди противника...",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔄 Проверить", callback_data="check_room")]])
    )
    await cb.answer()

@dp.callback_query(F.data == "live_join_menu")
async def live_join_menu(cb: types.CallbackQuery, state: FSMContext):
    await cb.message.answer("<b>🔵 Введи ID комнаты:</b>", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="В меню", callback_data="menu")]]))
    await state.set_state(States.live_join)
    await cb.answer()

@dp.message(States.live_join)
async def live_join_process(msg: types.Message, state: FSMContext):
    u = get_user(msg.from_user.id)
    if u[1] == "Игрок":
        await msg.answer("❌ Сначала зарегистрируйтесь! Нажмите /start")
        return
    
    room_id = msg.text.strip()
    deck = json.loads(u[9])
    
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT host_id, status FROM rooms WHERE room_id=?", (room_id,))
    row = c.fetchone()
    
    if not row:
        await msg.answer("❌ Комната не найдена!")
        return
    if row[1] != 'waiting':
        await msg.answer("❌ Игра уже идет!")
        return
    if row[0] == msg.from_user.id:
        await msg.answer("❌ Нельзя с самим собой!")
        return
    
    c.execute("""UPDATE rooms SET guest_id=?, guest_chat_id=?, guest_deck=?, status='ready' 
                 WHERE room_id=?""", (msg.from_user.id, msg.from_user.id, json.dumps(deck), room_id))
    conn.commit()
    conn.close()
    
    # ✅ ОТПРАВЛЯЕМ НОВОЕ СООБЩЕНИЕ, а не редактируем
    await init_live_battle(msg, state, room_id, "guest")


@dp.callback_query(F.data == "check_room")
async def check_room(cb: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    room_id = data.get("room_id")
    
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT status FROM rooms WHERE room_id=?", (room_id,))
    row = c.fetchone()
    conn.close()
    
    if row and row[0] == 'ready':
        # ✅ Инициализируем бой для 1-го игрока
        await init_live_battle(cb.message, state, room_id, "host")
    else:
        await cb.answer("⏳ Противник ещё не присоединился. Жми 'Проверить' снова.", show_alert=True)

# Вспомогательная функция для инициализации боя
async def init_live_battle(msg_or_cb, state, room_id, role):
    """Инициализация LIVE боя для обоих игроков"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT host_deck, guest_deck FROM rooms WHERE room_id=?", (room_id,))
    row = c.fetchone()
    conn.close()
    
    if not row: 
        return
    
    h_deck = json.loads(row[0])
    g_deck = json.loads(row[1])
    h_hp = sum(CARDS[c]['hp'] for c in h_deck if c in CARDS)
    g_hp = sum(CARDS[c]['hp'] for c in g_deck if c in CARDS)
    
    my_deck = h_deck if role == "host" else g_deck
    enemy_deck = g_deck if role == "host" else h_deck
    
    await state.update_data(
        battle_arena="live", room_id=room_id, player_role=role,
        my_deck=my_deck, enemy_deck=enemy_deck,
        my_hp=h_hp if role=="host" else g_hp, enemy_hp=g_hp if role=="host" else h_hp,
        my_max_hp=h_hp if role=="host" else g_hp, enemy_max_hp=g_hp if role=="host" else h_hp,
        my_mana=3, enemy_mana=3, my_ultimate=0, turn=1,
        current_turn="host"
    )
    await state.set_state(States.battle_live)
    
    # ✅ ОТПРАВЛЯЕМ НАЧАЛО БОЯ
    await send_battle_start(msg_or_cb, state)

async def send_battle_start(msg_or_cb, state: FSMContext):
    """Отправляет начало боя (корректно для Message и CallbackQuery)"""
    data = await state.get_data()
    text = f"⚔️ <b>ХОД {data['turn']}</b>\n\n"
    text += f"👹 <b>ВРАГ</b> {render_hp(data['enemy_hp'], data['enemy_max_hp'])}\n"
    text += f"⚔️ <b>ТЫ</b> {render_hp(data['my_hp'], data['my_max_hp'])}\n\n"
    text += f"💧 Мана: {data['my_mana']}/6 | 💥 Ульта: {data['my_ultimate']}%\n"
    
    kb = []
    for i, cid in enumerate(data['my_deck']):
        if cid and cid in CARDS:
            c = CARDS[cid]
            kb.append([InlineKeyboardButton(text=f"{c['name']} (HP:{c['hp']})", callback_data=f"sel_unit:{cid}")])
    kb.append([InlineKeyboardButton(text="🔥 УЛЬТА", callback_data="use_ultimate")])
    kb.append([InlineKeyboardButton(text="📖 Помощь", callback_data="help_battle")])
    
    reply_markup = InlineKeyboardMarkup(inline_keyboard=kb)
    
    # ✅ ПРОВЕРКА: это Message или CallbackQuery?
    if isinstance(msg_or_cb, types.CallbackQuery):
        # CallbackQuery: используем .message
        try:
            await msg_or_cb.message.edit_text(text, reply_markup=reply_markup)
        except:
            await msg_or_cb.message.answer(text, reply_markup=reply_markup)
    else:
        # Message: используем напрямую
        await msg_or_cb.answer(text, reply_markup=reply_markup)

async def start_battle(cb, state, host_deck_str, guest_deck_str):
    h_deck = json.loads(host_deck_str)
    g_deck = json.loads(guest_deck_str)
    h_hp = sum(CARDS[c]['hp'] for c in h_deck if c in CARDS)
    g_hp = sum(CARDS[c]['hp'] for c in g_deck if c in CARDS)
    role = await state.get_data().get("player_role", "host")
    my_deck = h_deck if role == "host" else g_deck
    enemy_deck = g_deck if role == "host" else h_deck
    await state.update_data(
        battle_arena="live", my_deck=my_deck, enemy_deck=enemy_deck,
        my_hp=h_hp if role=="host" else g_hp, enemy_hp=g_hp if role=="host" else h_hp,
        my_max_hp=h_hp if role=="host" else g_hp, enemy_max_hp=g_hp if role=="host" else h_hp,
        my_mana=3, enemy_mana=3, my_ultimate=0, turn=1
    )
    await battle_turn(cb, state)

async def battle_turn(msg_or_cb, state: FSMContext):
    """Обновление поля боя"""
    data = await state.get_data()
    text = f"⚔️ <b>ХОД {data['turn']}</b>\n\n"
    text += f"👹 <b>ВРАГ</b> {render_hp(data['enemy_hp'], data['enemy_max_hp'])}\n"
    text += f"⚔️ <b>ТЫ</b> {render_hp(data['my_hp'], data['my_max_hp'])}\n\n"
    text += f"💧 Мана: {data['my_mana']}/6 | 💥 Ульта: {data['my_ultimate']}%\n"
    if data['my_ultimate'] >= 100: text += "🔥 <b>УЛЬТА ГОТОВА!</b>\n"
    
    kb = []
    for i, cid in enumerate(data['my_deck']):
        if cid and cid in CARDS:
            c = CARDS[cid]
            kb.append([InlineKeyboardButton(text=f"{c['name']} (HP:{c['hp']})", callback_data=f"sel_unit:{cid}")])
    kb.append([InlineKeyboardButton(text="🔥 УЛЬТА", callback_data="use_ultimate")])
    kb.append([InlineKeyboardButton(text="🏳️ СДАТЬСЯ", callback_data="surrender_confirm")])
    kb.append([InlineKeyboardButton(text="📖 Помощь", callback_data="help_battle")])
    
    reply_markup = InlineKeyboardMarkup(inline_keyboard=kb)
    
    # ✅ ПРОВЕРКА ТИПА
    if isinstance(msg_or_cb, types.CallbackQuery):
        try:
            await msg_or_cb.message.edit_text(text, reply_markup=reply_markup)
        except:
            await msg_or_cb.message.answer(text, reply_markup=reply_markup)
    else:
        await msg_or_cb.answer(text, reply_markup=reply_markup)

@dp.callback_query(F.data == "surrender_confirm")
async def surrender_confirm(cb: types.CallbackQuery, state: FSMContext):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Да, сдаться", callback_data="surrender_yes")],
        [InlineKeyboardButton(text="❌ Нет, сражаться", callback_data="surrender_no")]
    ])
    await cb.message.answer("<b>⚠️ ТЫ УВЕРЕН?</b>\n\nЭто действие нельзя отменить!", reply_markup=kb)
    await cb.answer()

@dp.callback_query(F.data == "surrender_yes")
async def surrender_yes(cb: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    room_id = data.get("room_id")
    
    await cb.message.answer("❌ <b>ТЫ СДАЛСЯ!</b>\n\nПротивник победил!")
    await end_live_battle(state, room_id, "lose")
    await cb.answer()

@dp.callback_query(F.data == "surrender_no")
async def surrender_no(cb: types.CallbackQuery, state: FSMContext):
    await cb.message.delete()
    await battle_turn(cb, state)
    await cb.answer()

@dp.callback_query(F.data.startswith("sel_unit:"))
async def select_unit(cb: types.CallbackQuery, state: FSMContext):
    unit_id = cb.data.split(":")[1]
    c = CARDS[unit_id]
    text = f"<b>Выбран: {c['name']}</b>\n\nВыбери действие:\n"
    kb = []
    for skill in c['skills']:
        kb.append([InlineKeyboardButton(text=f"{skill['name']} ({skill['mana']}💧)", callback_data=f"sel_skill:{unit_id}:{skill['name']}:{skill['mana']}:{skill['type']}")])
    kb.append([InlineKeyboardButton(text="🔙 К бою", callback_data="back_to_battle")])
    await cb.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
    await cb.answer()

@dp.callback_query(F.data.startswith("sel_skill:"))
async def select_skill(cb: types.CallbackQuery, state: FSMContext):
    parts = cb.data.split(":")
    unit_id, skill_name, cost, skill_type = parts[1], parts[2], int(parts[3]), parts[4]
    data = await state.get_data()
    if data['my_mana'] < cost:
        await cb.answer("❌ Недостаточно маны!", show_alert=True)
        return
    c = CARDS[unit_id]
    skill = next((s for s in c['skills'] if s['name'] == skill_name), None)
    
    available_combos = []
    for combo_id, combo_data in COMBOS.items():
        combo_skills = combo_data['skills']
        current_idx = next((i for i, (uid, sn) in enumerate(combo_skills) if uid == unit_id and sn == skill_name), -1)
        if current_idx > 0:
            prev_uid, prev_sn = combo_skills[current_idx - 1]
            last_unit = data.get("last_unit_used")
            last_skill = data.get("last_skill_name")
            if last_unit == prev_uid and last_skill == prev_sn:
                available_combos.append(combo_data)
    
    text = f"<b>{skill['name']}</b>\n<i>{skill['desc']}</i>\n\n"
    text += f"💧 Мана: {cost}\nТип: {skill['type']}\n\n"
    if available_combos:
        text += "<b>🔥 Доступно комбо:</b>\n"
        for combo in available_combos:
            text += f"• {combo['name']}: {combo['desc']}\n"
            text += f"  Бонус: +{combo['value']}% к {combo['bonus']}\n"
    else:
        text += "<i>Используй после правильного навыка для комбо</i>\n"
    
    await state.update_data(selected_skill={"unit": unit_id, "name": skill_name, "cost": cost, "type": skill_type, "desc": skill['desc']})
    await cb.message.answer(text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="💥 ПРИМЕНИТЬ", callback_data="exec_attack")]]))
    await cb.answer()

# ==================== ИСПРАВЛЕННАЯ ФУНКЦИЯ execute_attack (LIVE) - БЕЗ ДЕФОЛТОВ ====================
@dp.callback_query(States.battle_live, F.data == "exec_attack")
async def execute_attack_live(cb: types.CallbackQuery, state: FSMContext):
    """LIVE PvP - ОДНОВРЕМЕННЫЕ ходы с полной механикой"""
    data = await state.get_data()
    skill = data.get("selected_skill")
    if not skill: return
    
    room_id = data.get("room_id")
    role = data.get("player_role")
    
    # Сохраняем ВСЮ информацию о действии
    action_data = {
        "unit": skill['unit'],
        "skill_name": skill['name'],
        "skill_type": skill['type'],
        "cost": skill['cost'],
        "timestamp": int(time.time()),
        # Для комбо
        "last_unit": data.get("last_unit_used"),
        "last_skill": data.get("last_skill_name")
    }
    
    # ✅ СОХРАНЯЕМ ДЕЙСТВИЕ В БД
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    if role == "host":
        c.execute("UPDATE rooms SET host_action=? WHERE room_id=?", 
                  (json.dumps(action_data), room_id))
    else:
        c.execute("UPDATE rooms SET guest_action=? WHERE room_id=?", 
                  (json.dumps(action_data), room_id))
    conn.commit()
    
    # Проверяем действия обоих
    c.execute("SELECT host_action, guest_action, round_start_time FROM rooms WHERE room_id=?", (room_id,))
    row = c.fetchone()
    host_action = json.loads(row[0]) if row[0] and row[0] != '{}' else {}
    guest_action = json.loads(row[1]) if row[1] and row[1] != '{}' else {}
    round_start = row[2] if row[2] else int(time.time())
    
    current_time = int(time.time())
    time_elapsed = current_time - round_start
    
    host_ready = bool(host_action)
    guest_ready = bool(guest_action)
    
    # ✅ ТАЙМЕР 30 СЕКУНД
    if time_elapsed >= 30:
        if not host_ready:
            await cb.message.answer("⏰ Хост не успел сделать ход!")
        if not guest_ready:
            await cb.message.answer("⏰ Гость не успел сделать ход!")
    
    # Если оба сделали ход ИЛИ таймер истёк
    if (host_ready and guest_ready) or time_elapsed >= 30:
        conn.close()
        await process_live_round_full(cb, state, room_id, host_action, guest_action)
    else:
        conn.close()
        await cb.message.answer("✅ Ход записан! Ждём противника...")

async def process_live_round_full(cb, state, room_id, host_action, guest_action):
    """Обработка раунда LIVE с ПОЛНОЙ механикой"""
    data = await state.get_data()
    
    result_text = "<b>⚔️ РЕЗУЛЬТАТЫ РАУНДА</b>\n\n"
    
    my_hp = data['my_hp']
    enemy_hp = data['enemy_hp']
    role = data.get("player_role")
    
    # Определяем кто есть кто
    if role == "host":
        my_action = host_action
        enemy_action = guest_action
        my_role_name = "Хост"
        enemy_role_name = "Гость"
    else:
        my_action = guest_action
        enemy_action = host_action
        my_role_name = "Гость"
        enemy_role_name = "Хост"
    
    # ✅ ОБРАБОТКА ДЕЙСТВИЯ ИГРОКА
    if my_action:
        unit_id = my_action['unit']
        skill_name = my_action['skill_name']
        skill_type = my_action['skill_type']
        
        skill = None
        for s in CARDS[unit_id]['skills']:
            if s['name'] == skill_name:
                skill = s
                break
        
        if skill:
            combo_bonus = 0
            combo_msg = ""
            last_unit = my_action.get("last_unit")
            last_skill = my_action.get("last_skill")
            
            for combo_id, combo_data in COMBOS.items():
                combo_skills = combo_data['skills']
                current_idx = next((i for i, (uid, sn) in enumerate(combo_skills) 
                                   if uid == unit_id and sn == skill_name), -1)
                if current_idx > 0 and last_unit and last_skill:
                    prev_uid, prev_sn = combo_skills[current_idx - 1]
                    if last_unit == prev_uid and last_skill == prev_sn:
                        combo_bonus = combo_data['value']
                        combo_msg = combo_data['name']
                        break
            
            if skill_type == 'heal':
                heal_amount = skill.get('heal', 15)
                if combo_bonus > 0:
                    heal_amount = int(heal_amount * (1 + combo_bonus/100))
                my_hp = min(data['my_max_hp'], my_hp + heal_amount)
                result_text += f"✨ {my_role_name} восстановил {heal_amount} HP\n"
                
            elif skill_type == 'defend':
                def_amount = skill.get('def', 10)
                if combo_bonus > 0:
                    def_amount += int(def_amount * combo_bonus/100)
                await state.update_data(defense_buff=def_amount)
                result_text += f"🛡️ {my_role_name} повысил защиту на {def_amount}\n"
                
            elif skill_type in ['attack', 'magic']:
                base_dmg = skill.get('dmg', 15)
                if combo_bonus > 0:
                    base_dmg += int(base_dmg * combo_bonus/100)
                enemy_hp -= base_dmg
                result_text += f"⚔️ {my_role_name} нанёс {base_dmg} урона"
                if combo_msg:
                    result_text += f" ({combo_msg})"
                result_text += "\n"
                
            elif skill_type == 'lifesteal':
                base_dmg = skill.get('dmg', 12)
                lifesteal_pct = skill.get('lifesteal', 0.5)
                if combo_bonus > 0:
                    base_dmg += int(base_dmg * combo_bonus/100)
                heal_amount = int(base_dmg * lifesteal_pct)
                enemy_hp -= base_dmg
                my_hp = min(data['my_max_hp'], my_hp + heal_amount)
                result_text += f"🩸 {my_role_name}: {base_dmg} урона, +{heal_amount} HP\n"
                
            elif skill_type == 'berserk':
                base_dmg = skill.get('dmg', 25)
                self_dmg = skill.get('self_dmg', 10)
                if combo_bonus > 0:
                    base_dmg += int(base_dmg * combo_bonus/100)
                enemy_hp -= base_dmg
                my_hp -= self_dmg
                result_text += f"💀 {my_role_name}: {base_dmg} врагу, {self_dmg} себе\n"
    
    # ✅ ОБРАБОТКА ДЕЙСТВИЯ ПРОТИВНИКА
    if enemy_action:
        unit_id = enemy_action['unit']
        skill_name = enemy_action['skill_name']
        skill_type = enemy_action['skill_type']
        
        skill = None
        for s in CARDS[unit_id]['skills']:
            if s['name'] == skill_name:
                skill = s
                break
        
        if skill:
            if skill_type in ['attack', 'magic']:
                base_dmg = skill.get('dmg', 15)
                defense = data.get('defense_buff', 0)
                if defense > 0:
                    base_dmg = max(1, base_dmg - defense)
                    await state.update_data(defense_buff=0)
                
                my_hp -= base_dmg
                result_text += f"⚔️ {enemy_role_name} нанёс {base_dmg} урона\n"
            
            elif skill_type == 'heal':
                heal_amount = skill.get('heal', 15)
                result_text += f"✨ {enemy_role_name} восстановил {heal_amount} HP\n"
    
    # ✅ ПРОВЕРКА ПОБЕДЫ
    if my_hp <= 0 and enemy_hp <= 0:
        result_text += "\n🤝 <b>НИЧЬЯ!</b>"
        await cb.message.answer(result_text)
        await end_live_battle(state, room_id, "draw")
        return
    elif enemy_hp <= 0:
        result_text += f"\n🏆 <b>ПОБЕДА!</b>"
        await cb.message.answer(result_text)
        await end_live_battle(state, room_id, "win")
        return
    elif my_hp <= 0:
        result_text += f"\n❌ <b>ПОРАЖЕНИЕ...</b>"
        await cb.message.answer(result_text)
        await end_live_battle(state, room_id, "lose")
        return
    
    # Обновляем состояние
    await state.update_data(my_hp=max(0, my_hp), enemy_hp=max(0, enemy_hp))
    
    # Сбрасываем действия и УСТАНАВЛИВАЕМ время начала следующего раунда
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    current_time = int(time.time())
    c.execute("""UPDATE rooms SET 
                 host_action='{}', guest_action='{}', 
                 round_start_time=?
                 WHERE room_id=?""", 
              (current_time, room_id))
    conn.commit()
    conn.close()
    
    result_text += f"\n❤️ Ваш HP: {my_hp}\n💀 HP врага: {enemy_hp}"
    
    # ✅ ОТПРАВЛЯЕМ ОБОИМ ИГРОКАМ
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT host_chat_id, guest_chat_id FROM rooms WHERE room_id=?", (room_id,))
    chats = c.fetchone()
    conn.close()
    
    if chats:
        host_chat, guest_chat = chats
        
        # Отправляем хосту
        try:
            await bot.send_message(host_chat, result_text)
        except:
            pass
        
        # Отправляем гостю
        try:
            await bot.send_message(guest_chat, result_text)
        except:
            pass
    
    # Показываем меню боя обоим
    if random.random() < 0.3:
        await asyncio.sleep(1)
        await trigger_qte_live(room_id, state)
    else:
        await send_battle_to_both(room_id, state)
    
    # ✅ СОХРАНЯЕМ ПОСЛЕДНИЕ НАВЫКИ ДЛЯ КОМБО
    if my_action:
        await state.update_data(
            last_unit_used=my_action.get("unit"),
            last_skill_name=my_action.get("skill_name")
        )

async def send_battle_to_both(room_id, state):
    """Отправляет меню боя обоим игрокам"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT host_chat_id, guest_chat_id FROM rooms WHERE room_id=?", (room_id,))
    chats = c.fetchone()
    conn.close()
    
    if not chats:
        return
    
    data = await state.get_data()
    text = f"⚔️ <b>ХОД {data['turn']}</b>\n\n"
    text += f"👹 <b>ВРАГ</b> {render_hp(data['enemy_hp'], data['enemy_max_hp'])}\n"
    text += f"⚔️ <b>ТЫ</b> {render_hp(data['my_hp'], data['my_max_hp'])}\n\n"
    text += f"💧 Мана: {data['my_mana']}/6 | 💥 Ульта: {data['my_ultimate']}%\n"
    
    kb = []
    for i, cid in enumerate(data['my_deck']):
        if cid and cid in CARDS:
            c = CARDS[cid]
            kb.append([InlineKeyboardButton(text=f"{c['name']} (HP:{c['hp']})", callback_data=f"sel_unit:{cid}")])
    kb.append([InlineKeyboardButton(text="🔥 УЛЬТА", callback_data="use_ultimate")])
    kb.append([InlineKeyboardButton(text="📖 Помощь", callback_data="help_battle")])
    
    reply_markup = InlineKeyboardMarkup(inline_keyboard=kb)
    
    host_chat, guest_chat = chats
    
    # Отправляем обоим
    try:
        await bot.send_message(host_chat, text, reply_markup=reply_markup)
    except:
        pass
    
    try:
        await bot.send_message(guest_chat, text, reply_markup=reply_markup)
    except:
        pass

async def trigger_qte_live(room_id, state):
    """QTE для LIVE боёв - отправляется обоим игрокам"""
    target = "💎"
    options = ["💎", "💠", "⚡", "🔥"]
    random.shuffle(options)
    
    # Сохраняем правильный ответ
    await state.update_data(qte_answer=target, qte_room_id=room_id, qte_completed_host=False, qte_completed_guest=False)
    
    btns = [[InlineKeyboardButton(text=o, callback_data=f"qte_ans_live:{o}:{room_id}")] for o in options]
    kb = InlineKeyboardMarkup(inline_keyboard=btns)
    
    # Отправляем обоим игрокам
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT host_chat_id, guest_chat_id FROM rooms WHERE room_id=?", (room_id,))
    chats = c.fetchone()
    conn.close()
    
    if chats:
        host_chat, guest_chat = chats
        try:
            await bot.send_message(host_chat, f"⚡ <b>QTE: ПОИСК</b>\n\nНайди: {target}\n<i>Кто первый нажмёт - получит +33% к ульте!</i>", reply_markup=kb)
        except:
            pass
        try:
            await bot.send_message(guest_chat, f"⚡ <b>QTE: ПОИСК</b>\n\nНайди: {target}\n<i>Кто первый нажмёт - получит +33% к ульте!</i>", reply_markup=kb)
        except:
            pass

@dp.callback_query(F.data.startswith("qte_ans_live:"))
async def process_qte_live(cb: types.CallbackQuery, state: FSMContext):
    parts = cb.data.split(":")
    answer = parts[1]
    room_id = parts[2]
    
    data = await state.get_data()
    correct_answer = data.get("qte_answer")
    qte_room_id = data.get("qte_room_id")
    
    # Проверяем что это та комната
    if qte_room_id != room_id:
        await cb.answer("❌ Это QTE для другого боя!", show_alert=True)
        return
    
    # Проверяем кто уже прошёл
    host_done = data.get("qte_completed_host", False)
    guest_done = data.get("qte_completed_guest", False)
    
    role = data.get("player_role")
    
    if answer == correct_answer:
        # Проверяем кто первый
        if role == "host" and not host_done:
            await state.update_data(qte_completed_host=True, my_ultimate=min(100, data.get("my_ultimate", 0) + 33))
            await cb.message.answer("✅ <b>ПЕРВЫЙ!</b> Ульта заряжена на +33%!\n\nЖди противника...")
            # Проверяем закончил ли гость
            if guest_done:
                await asyncio.sleep(1)
                await send_battle_to_both(room_id, state)
        elif role == "guest" and not guest_done:
            await state.update_data(qte_completed_guest=True, my_ultimate=min(100, data.get("my_ultimate", 0) + 33))
            await cb.message.answer("✅ <b>ПЕРВЫЙ!</b> Ульта заряжена на +33%!\n\nЖди противника...")
            # Проверяем закончил ли хост
            if host_done:
                await asyncio.sleep(1)
                await send_battle_to_both(room_id, state)
        else:
            await cb.message.answer("⏳ Ты уже прошёл QTE! Жди противника...")
    else:
        await cb.message.answer("❌ Ошибка! Попробуй в следующий раз...")
        # Даже при ошибке ждём второго игрока
        if role == "host":
            await state.update_data(qte_completed_host=True)
            if guest_done:
                await asyncio.sleep(1)
                await send_battle_to_both(room_id, state)
        else:
            await state.update_data(qte_completed_guest=True)
            if host_done:
                await asyncio.sleep(1)
                await send_battle_to_both(room_id, state)
    
    await cb.answer()

async def process_live_round(cb, state, room_id, host_action, guest_action):
    """Обработка раунда LIVE PvP"""
    data = await state.get_data()
    role = data.get("player_role")
    
    result_text = "<b>⚔️ РЕЗУЛЬТАТЫ РАУНДА</b>\n\n"
    
    my_hp = data['my_hp']
    enemy_hp = data['enemy_hp']
    
    # Определяем кто есть кто
    if role == "host":
        my_action = host_action
        enemy_action = guest_action
    else:
        my_action = guest_action
        enemy_action = host_action
    
    # ✅ ОБРАБОТКА ДЕЙСТВИЙ (упрощённо для MVP)
    # Хост атакует гостя
    if host_action and host_action.get('skill_type') in ['attack', 'magic']:
        unit_id = host_action['unit']
        skill_name = host_action['skill_name']
        # Ищем урон в CARDS
        for skill in CARDS[unit_id]['skills']:
            if skill['name'] == skill_name:
                dmg = skill.get('dmg', 10)
                enemy_hp -= dmg
                result_text += f"🗡️ Хост ({CARDS[unit_id]['name']}) нанёс {dmg} урона\n"
                break
    
    # Гость атакует хоста
    if guest_action and guest_action.get('skill_type') in ['attack', 'magic']:
        unit_id = guest_action['unit']
        skill_name = guest_action['skill_name']
        for skill in CARDS[unit_id]['skills']:
            if skill['name'] == skill_name:
                dmg = skill.get('dmg', 10)
                my_hp -= dmg
                result_text += f"🗡️ Гость ({CARDS[unit_id]['name']}) нанёс {dmg} урона\n"
                break
    
    # ✅ ПРОВЕРКА ПОБЕДЫ
    if my_hp <= 0 and enemy_hp <= 0:
        result_text += "\n🤝 <b>НИЧЬЯ!</b> (оба погибли)"
        await cb.message.answer(result_text)
        await end_live_battle(state, room_id, "draw")
        return
    elif enemy_hp <= 0:
        result_text += f"\n🏆 <b>ПОБЕДА!</b>"
        await cb.message.answer(result_text)
        await end_live_battle(state, room_id, "win")
        return
    elif my_hp <= 0:
        result_text += f"\n❌ <b>ПОРАЖЕНИЕ...</b>"
        await cb.message.answer(result_text)
        await end_live_battle(state, room_id, "lose")
        return
    
    # Обновляем состояние
    await state.update_data(my_hp=max(0, my_hp), enemy_hp=max(0, enemy_hp))
    
    # Сбрасываем действия для следующего раунда
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("""UPDATE rooms SET 
                 host_action='{}', guest_action='{}', 
                 round_start_time=?
                 WHERE room_id=?""", 
              (int(time.time()), room_id))
    conn.commit()
    conn.close()
    
    result_text += f"\n\n❤️ Ваш HP: {my_hp}\n💀 HP врага: {enemy_hp}\n\n⏳ Новый раунд начался!"
    await cb.message.answer(result_text)
    await battle_turn(cb, state)

async def end_live_battle(state, room_id, result):
    """Завершение LIVE боя"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("DELETE FROM rooms WHERE room_id=?", (room_id,))
    conn.commit()
    conn.close()
    
    u = get_user(state.get_data().get('user_id', list(state.get_data().values())[0] if state.get_data() else 0))
    if not u: return
    
    wins = u[14] if u[14] else 0
    losses = u[15] if u[15] else 0
    
    if result == "win":
        update_user(state.get_data().get('user_id', 0), wins=wins+1, rating=u[3]+15)
    elif result == "lose":
        update_user(state.get_data().get('user_id', 0), losses=losses+1, rating=max(0, u[3]-10))
    
    await state.clear()

@dp.callback_query(F.data == "back_to_battle")
async def back_battle(cb: types.CallbackQuery, state: FSMContext):
    await state.set_state(States.battle_live)
    await battle_turn(cb, state)
    await cb.answer()

async def trigger_qte(cb, state: FSMContext):
    target = "💎"
    options = ["💎", "💠", "", ""]
    random.shuffle(options)
    await state.update_data(qte_answer=target)
    btns = [[InlineKeyboardButton(text=o, callback_data=f"qte_ans:{o}")] for o in options]
    await cb.message.answer(f"⚡ <b>QTE: ПОИСК</b>\n\nНайди: {target}", reply_markup=InlineKeyboardMarkup(inline_keyboard=btns))

@dp.callback_query(F.data.startswith("qte_ans:"))
async def process_qte(cb: types.CallbackQuery, state: FSMContext):
    answer = cb.data.split(":")[1]
    data = await state.get_data()
    if answer == data.get("qte_answer"):
        ult_charge = min(100, data.get("my_ultimate", 0) + 33)
        await state.update_data(my_ultimate=ult_charge)
        await cb.message.answer("✅ QTE пройден! Ульта заряжена!")
    else:
        await cb.message.answer("❌ Ошибка!")
    await state.set_state(States.battle_live)
    await battle_turn(cb, state)
    await cb.answer()

@dp.callback_query(F.data == "help_battle")
async def help_battle(cb: types.CallbackQuery):
    text = "<b>📖 ПОМОЩЬ В БОЮ</b>\n\n1. Выбери юнита → 2. Выбери навык → 3. Атакуй/Лечи/Защищай\n\n💧 Мана: +2 за ход | 💥 Ульта: от QTE | ⚔️ Комбо: используй навыки в правильной последовательности"
    await cb.answer(text, show_alert=True)

@dp.callback_query(F.data == "use_ultimate")
async def use_ultimate(cb: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    ult_charge = data.get("my_ultimate", 0)
    
    if ult_charge < 100:
        await cb.answer(f"❌ Ульта заряжена только на {ult_charge}%! Нужно 100%", show_alert=True)
        return
    
    # Ульта - массовая атака всеми юнитами
    result_text = "<b>🔥 УЛЬТА АКТИВИРОВАНА!</b>\n\n"
    
    my_deck = data.get("my_deck", [])
    total_dmg = 0
    
    for cid in my_deck:
        if cid and cid in CARDS:
            c = CARDS[cid]
            dmg = c["atk"]  # Урон равен атаке юнита
            total_dmg += dmg
            result_text += f"⚔️ {c['name']}: {dmg} урона\n"
    
    # Применяем урон
    new_enemy_hp = data["enemy_hp"] - total_dmg
    await state.update_data(enemy_hp=max(0, new_enemy_hp), my_ultimate=0)
    
    result_text += f"\n💥 <b>ОБЩИЙ УРОН: {total_dmg}</b>"
    
    # Проверяем победу
    if new_enemy_hp <= 0:
        result_text += "\n\n🏆 <b>ПОБЕДА!</b>"
        await cb.message.answer(result_text)
        room_id = data.get("room_id")
        await end_live_battle(state, room_id, "win")
        return
    
    result_text += f"\n\n❤️ Ваш HP: {data['my_hp']}\n💀 HP врага: {new_enemy_hp}"
    await cb.message.answer(result_text)
    
    # Обновляем поле
    await battle_turn(cb, state)
    await cb.answer()

# ==================== РЕЙДЫ ====================
@dp.message(F.text == "🌑 Рейд")
async def raid_menu(msg: types.Message):
    u = get_user(msg.from_user.id)
    if u[1] == "Игрок":
        await msg.answer("❌ Сначала зарегистрируйтесь! Нажмите /start")
        return
    energy = check_energy(msg.from_user.id)
    if energy <= 0:
        await msg.answer("⚡ Нет энергии! Подожди восстановления.")
        return
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT user_id, name, rating FROM players WHERE user_id!=? LIMIT 3", (msg.from_user.id,))
    targets = c.fetchall()
    conn.close()
    if not targets:
        await msg.answer("❌ Нет целей. Напиши /addtest чтобы добавить тестового бота.")
        return
    kb = [[InlineKeyboardButton(text=f"⚔️ {t[1] or 'Игрок'} ({t[2]}⭐)", callback_data=f"raid:{t[0]}")] for t in targets]
    await msg.answer(f"⚡ {energy}/5 | Выбери цель для атаки:", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

@dp.callback_query(F.data.startswith("raid:"))
async def raid_start(cb: types.CallbackQuery, state: FSMContext):
    target_id = int(cb.data.split(":")[1])
    attacker = get_user(cb.from_user.id)
    defender = get_user(target_id)
    def_deck = json.loads(defender[9])
    def_hp = sum(CARDS[c]['hp'] for c in def_deck if c in CARDS)
    def_atk = sum(CARDS[c]['atk'] for c in def_deck if c in CARDS)
    att_deck = json.loads(attacker[9])
    att_hp = sum(CARDS[c]['hp'] for c in att_deck if c in CARDS)
    def_skills = json.loads(defender[12])
    trap_level = def_skills.get("trap_level", 0)
    await state.update_data(
        raid_mode=True, raid_enemy_id=target_id, raid_enemy_name=defender[1] or "Игрок",
        raid_enemy_deck=def_deck, raid_enemy_hp=def_hp, raid_enemy_max_hp=def_hp, raid_enemy_atk=def_atk,
        raid_player_hp=att_hp, raid_player_max_hp=att_hp, raid_player_mana=3, raid_turn=1,
        raid_trap_level=trap_level, raid_last_unit=None, raid_last_skill=None, raid_selected_skill=None
    )
    await state.set_state(States.battle_raid)
    await raid_render(cb, state)
    await cb.answer()

async def raid_render(cb: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    text = f"🌑 <b>РЕЙД: {data['raid_enemy_name']}</b> (Ход {data['raid_turn']})\n\n"
    text += f"🛡 <b>Защитник</b> {render_hp(max(0, data['raid_enemy_hp']), data['raid_enemy_max_hp'])}\n"
    text += f"⚔️ <b>Ты</b> {render_hp(max(0, data['raid_player_hp']), data['raid_player_max_hp'])}\n\n"
    text += f"💧 Мана: {data['raid_player_mana']}/6"
    if data['raid_trap_level'] > 0: text += f"\n🪤 Ловушки врага: Ур.{data['raid_trap_level']}"
    
    u = get_user(cb.from_user.id)
    my_deck = json.loads(u[9])
    kb = []
    
    can_act = False
    for cid in my_deck:
        if cid in CARDS:
            c = CARDS[cid]
            # Считаем минимальную ману для ВСЕХ навыков юнита
            min_mana = min([s['mana'] for s in c['skills']])
            
            if data['raid_player_mana'] >= min_mana:
                can_act = True
            
            # В кнопке тоже показываем минимальную ману
            kb.append([InlineKeyboardButton(text=f"{c['name']} (💧{min_mana})", callback_data=f"raid_sel_unit:{cid}")])
    
    if not can_act:
        kb.append([InlineKeyboardButton(text="⏳ Пропустить ход (+2 маны)", callback_data="raid_skip_turn")])
    
    await cb.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

@dp.callback_query(States.battle_raid, F.data.startswith("raid_sel_unit:"))
async def raid_sel_unit(cb: types.CallbackQuery, state: FSMContext):
    unit_id = cb.data.split(":")[1]
    c = CARDS[unit_id]
    data = await state.get_data()
    
    # Считаем минимальную ману для этого юнита
    min_mana = min([s['mana'] for s in c['skills']])
    
    if data['raid_player_mana'] < min_mana:
        await cb.answer(f"❌ Недостаточно маны! Нужно минимум {min_mana}", show_alert=True)
        return
        
    text = f"<b>{c['name']}</b>\nВыбери действие:"
    kb = []
    for skill in c['skills']:
        kb.append([InlineKeyboardButton(text=f"{skill['name']} ({skill['mana']}💧)", callback_data=f"raid_skill:{unit_id}:{skill['name']}:{skill['mana']}:{skill['type']}")])
    kb.append([InlineKeyboardButton(text="🔙 К рейду", callback_data="raid_back_render")])
    await cb.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
    await cb.answer()

@dp.callback_query(States.battle_raid, F.data == "raid_skip_turn")
async def raid_skip_turn(cb: types.CallbackQuery, state: FSMContext):
    await cb.message.answer("⏳ Вы пропустили ход...")
    await asyncio.sleep(1)
    await raid_bot_turn(cb, state)
    await cb.answer()

@dp.callback_query(States.battle_raid, F.data.startswith("raid_sel_unit:"))
async def raid_sel_unit(cb: types.CallbackQuery, state: FSMContext):
    unit_id = cb.data.split(":")[1]
    c = CARDS[unit_id]
    data = await state.get_data()
    if data['raid_player_mana'] < 2:
        await cb.answer("❌ Недостаточно маны для действий!", show_alert=True)
        return
    text = f"<b>Атака через {c['name']}</b>\nВыбери действие:"
    kb = []
    for skill in c['skills']:
        kb.append([InlineKeyboardButton(text=f"{skill['name']} ({skill['mana']}💧)", callback_data=f"raid_skill:{unit_id}:{skill['name']}:{skill['mana']}:{skill['type']}")])
    kb.append([InlineKeyboardButton(text="🔙 К рейду", callback_data="raid_back_render")])
    await cb.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
    await cb.answer()

@dp.callback_query(States.battle_raid, F.data.startswith("raid_skill:"))
async def raid_sel_skill(cb: types.CallbackQuery, state: FSMContext):
    parts = cb.data.split(":")
    unit_id, skill_name, cost, skill_type = parts[1], parts[2], int(parts[3]), parts[4]
    data = await state.get_data()
    if data['raid_player_mana'] < cost:
        await cb.answer("❌ Мало маны!", show_alert=True)
        return
    c = CARDS[unit_id]
    skill = next((s for s in c['skills'] if s['name'] == skill_name), None)
    
    available_combos = []
    for combo_id, combo_data in COMBOS.items():
        combo_skills = combo_data['skills']
        current_idx = next((i for i, (uid, sn) in enumerate(combo_skills) if uid == unit_id and sn == skill_name), -1)
        if current_idx > 0:
            prev_uid, prev_sn = combo_skills[current_idx - 1]
            last_unit = data.get("raid_last_unit")
            last_skill = data.get("raid_last_skill")
            if last_unit == prev_uid and last_skill == prev_sn:
                available_combos.append(combo_data)
    
    text = f"<b>{skill['name']}</b>\n<i>{skill['desc']}</i>\n\n"
    text += f"💧 Мана: {cost}\nТип: {skill['type']}\n\n"
    if available_combos:
        text += "<b>🔥 Доступно комбо:</b>\n"
        for combo in available_combos:
            text += f"• {combo['name']}: {combo['desc']}\n"
            text += f"  Бонус: +{combo['value']}% к {combo['bonus']}\n"
    else:
        text += "<i>Используй после правильного навыка для комбо</i>\n"
    
    await state.update_data(raid_selected_skill={"unit": unit_id, "name": skill_name, "cost": cost, "type": skill_type, "desc": skill['desc']})
    await cb.message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="💥 АТАКОВАТЬ", callback_data="raid_exec")]]))
    await cb.answer()

# ==================== ИСПРАВЛЕННАЯ ФУНКЦИЯ raid_exec - БЕЗ ДЕФОЛТОВ ====================
@dp.callback_query(States.battle_raid, F.data == "raid_exec")
async def raid_exec(cb: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    skill = data.get("raid_selected_skill")
    if not skill: 
        await cb.answer("❌ Ошибка: навык не выбран!", show_alert=True)
        return
    
    combo_bonus = 0
    combo_msg = ""
    last = data.get("raid_last_unit")
    curr = skill['unit']
    last_skill_name = data.get("raid_last_skill")
    curr_skill_name = skill['name']
    
    for combo_id, combo_data in COMBOS.items():
        combo_skills = combo_data['skills']
        current_idx = next((i for i, (uid, sn) in enumerate(combo_skills) if uid == curr and sn == curr_skill_name), -1)
        if current_idx > 0 and last and last_skill_name:
            prev_uid, prev_sn = combo_skills[current_idx - 1]
            if last == prev_uid and last_skill_name == prev_sn:
                combo_bonus = combo_data['value']
                combo_msg = f"{combo_data['name']} (+{combo_bonus}% к {combo_data['bonus']})"
                break
    
    action_text = ""
    
    if skill['type'] == 'heal':
        heal_amount = skill.get('heal', 15)
        if combo_bonus > 0: heal_amount = int(heal_amount * (1 + combo_bonus/100))
        new_hp = min(data['raid_player_max_hp'], data['raid_player_hp'] + heal_amount)
        await state.update_data(raid_player_hp=new_hp)
        action_text = f"✨ {skill['name']}: восстановлено <b>{heal_amount} HP</b>"
        
    elif skill['type'] == 'defend':
        def_amount = skill.get('def', 10)
        if combo_bonus > 0: def_amount += int(def_amount * combo_bonus/100)
        await state.update_data(raid_defense_buff=def_amount)
        action_text = f"🛡️ {skill['name']}: защита повышена на <b>{def_amount}</b>"
        
    elif skill['type'] in ['attack', 'magic']:
        base_dmg = skill.get('dmg', 15)
        if combo_bonus > 0: base_dmg += int(base_dmg * combo_bonus/100)
        trap_mult = 1 - (data['raid_trap_level'] * 0.1)
        final_dmg = max(1, int(base_dmg * trap_mult))
        new_enemy_hp = data['raid_enemy_hp'] - final_dmg
        action_text = f"⚔️ {skill['name']}: нанесено <b>{final_dmg} урона</b>"
        if skill.get('stun_chance') and random.randint(1, 100) <= skill['stun_chance']:
            await state.update_data(enemy_stunned=True, stun_turns=1)
            action_text += f"\n✨ Враг оглушен!"
        if new_enemy_hp <= 0:
            await state.update_data(raid_enemy_hp=0)
            if combo_msg: action_text += f"\n{combo_msg}"
            await cb.message.answer(action_text)
            await raid_finish(cb, state, win=True)
            return
        await state.update_data(raid_enemy_hp=new_enemy_hp)
        
    elif skill['type'] == 'lifesteal':
        base_dmg = skill.get('dmg', 12)
        lifesteal_pct = skill.get('lifesteal', 0.5)
        if combo_bonus > 0: base_dmg += int(base_dmg * combo_bonus/100)
        trap_mult = 1 - (data['raid_trap_level'] * 0.1)
        final_dmg = max(1, int(base_dmg * trap_mult))
        heal_amount = int(final_dmg * lifesteal_pct)
        new_enemy_hp = data['raid_enemy_hp'] - final_dmg
        new_hp = min(data['raid_player_max_hp'], data['raid_player_hp'] + heal_amount)
        action_text = f"🩸 {skill['name']}: {final_dmg} урона, +{heal_amount} HP"
        if new_enemy_hp <= 0:
            await state.update_data(raid_enemy_hp=0, raid_player_hp=new_hp)
            if combo_msg: action_text += f"\n{combo_msg}"
            await cb.message.answer(action_text)
            await raid_finish(cb, state, win=True)
            return
        await state.update_data(raid_enemy_hp=new_enemy_hp, raid_player_hp=new_hp)
        
    elif skill['type'] == 'berserk':
        base_dmg = skill.get('dmg', 25)
        self_dmg = skill.get('self_dmg', 10)
        if combo_bonus > 0: base_dmg += int(base_dmg * combo_bonus/100)
        trap_mult = 1 - (data['raid_trap_level'] * 0.1)
        final_dmg = max(1, int(base_dmg * trap_mult))
        new_enemy_hp = data['raid_enemy_hp'] - final_dmg
        new_player_hp = data['raid_player_hp'] - self_dmg
        action_text = f"💀 {skill['name']}: {final_dmg} урона врагу, {self_dmg} себе"
        if new_enemy_hp <= 0:
            await state.update_data(raid_enemy_hp=0, raid_player_hp=max(0, new_player_hp))
            if combo_msg: action_text += f"\n{combo_msg}"
            await cb.message.answer(action_text)
            await raid_finish(cb, state, win=True)
            return
        await state.update_data(raid_enemy_hp=new_enemy_hp, raid_player_hp=max(0, new_player_hp))
        
    elif skill['type'] == 'dodge':
        dodge_chance = skill.get('dodge', 0.5) * 100
        await state.update_data(raid_dodge_active=True, raid_dodge_chance=dodge_chance)
        action_text = f"💨 {skill['name']}: <b>{int(dodge_chance)}% шанс</b> избежать следующей атаки"
        
    elif skill['type'] == 'buff':
        await state.update_data(raid_buff_active=True)
        action_text = f"✨ {skill['name']}: бафф активирован"
        
    elif skill['type'] == 'shield':
        shield_amount = skill.get('shield', 30)
        await state.update_data(raid_shield=shield_amount)
        action_text = f"🛡️ {skill['name']}: щит на <b>{shield_amount}</b>"
        
    elif skill['type'] == 'crit':
        await state.update_data(raid_crit_ready=True)
        action_text = f"🎲 {skill['name']}: следующая атака x2"
        
    elif skill['type'] == 'poison':
        base_dmg = skill.get('dmg', 8)
        dot_dmg = skill.get('dot', 5)
        if combo_bonus > 0: base_dmg += int(base_dmg * combo_bonus/100)
        new_enemy_hp = data['raid_enemy_hp'] - base_dmg
        await state.update_data(raid_enemy_hp=max(0, new_enemy_hp), raid_enemy_poisoned=True, raid_poison_dmg=dot_dmg, raid_poison_turns=3)
        action_text = f"🧪 {skill['name']}: {base_dmg} урона + {dot_dmg}/ход"
        if new_enemy_hp <= 0:
            await state.update_data(raid_enemy_hp=0)
            if combo_msg: action_text += f"\n{combo_msg}"
            await cb.message.answer(action_text)
            await raid_finish(cb, state, win=True)
            return
            
    elif skill['type'] == 'multi':
        base_dmg = skill.get('dmg', 12)
        hits = skill.get('hits', 2)
        total_dmg = base_dmg * hits
        if combo_bonus > 0: total_dmg = int(total_dmg * (1 + combo_bonus/100))
        new_enemy_hp = data['raid_enemy_hp'] - total_dmg
        await state.update_data(raid_enemy_hp=max(0, new_enemy_hp))
        action_text = f"🏹 {skill['name']}: {hits} удара = <b>{total_dmg} урона</b>"
        if new_enemy_hp <= 0:
            await state.update_data(raid_enemy_hp=0)
            if combo_msg: action_text += f"\n{combo_msg}"
            await cb.message.answer(action_text)
            await raid_finish(cb, state, win=True)
            return
            
    elif skill['type'] == 'debuff':
        await state.update_data(raid_enemy_debuff=True)
        action_text = f"☠️ {skill['name']}: дебафф на врага"
        
    elif skill['type'] == 'aoe':
        base_dmg = skill.get('dmg', 15)
        if combo_bonus > 0: base_dmg += int(base_dmg * combo_bonus/100)
        new_enemy_hp = data['raid_enemy_hp'] - base_dmg
        await state.update_data(raid_enemy_hp=max(0, new_enemy_hp))
        action_text = f"💣 {skill['name']}: {base_dmg} урона"
        if new_enemy_hp <= 0:
            await state.update_data(raid_enemy_hp=0)
            if combo_msg: action_text += f"\n{combo_msg}"
            await cb.message.answer(action_text)
            await raid_finish(cb, state, win=True)
            return
            
    elif skill['type'] == 'ultimate_buff':
        await state.update_data(raid_all_stats_buff=True)
        action_text = f"🎼 {skill['name']}: все статы +15%"
        
    elif skill['type'] == 'counter':
        base_dmg = skill.get('dmg', 10)
        def_amount = skill.get('def', 5)
        if combo_bonus > 0: base_dmg += int(base_dmg * combo_bonus/100)
        new_enemy_hp = data['raid_enemy_hp'] - base_dmg
        await state.update_data(raid_enemy_hp=max(0, new_enemy_hp), raid_defense_buff=def_amount)
        action_text = f"💪 {skill['name']}: {base_dmg} урона, защита +{def_amount}"
        if new_enemy_hp <= 0:
            await state.update_data(raid_enemy_hp=0)
            if combo_msg: action_text += f"\n{combo_msg}"
            await cb.message.answer(action_text)
            await raid_finish(cb, state, win=True)
            return
    else:
        action_text = f"⚠️ {skill['name']}: эффект активирован"
    
    if combo_msg: action_text += f"\n{combo_msg}"
    
    new_mana = max(0, data['raid_player_mana'] - skill['cost'])
    await state.update_data(raid_player_mana=new_mana, raid_last_unit=curr, raid_last_skill=curr_skill_name, raid_selected_skill=None)
    
    await cb.message.answer(action_text)
    await asyncio.sleep(1)
    await raid_bot_turn(cb, state)

async def raid_bot_turn(cb: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    
    if data.get('enemy_stunned', False):
        stun_turns = data.get('stun_turns', 1) - 1
        if stun_turns <= 0:
            await state.update_data(enemy_stunned=False)
            await cb.message.answer("✨ Враг пришел в себя!")
        else:
            await state.update_data(stun_turns=stun_turns)
            await cb.message.answer("😵 Враг оглушен!")
            await raid_render(cb, state)
            return
    
    bot_dmg = random.randint(5, 12)
    
    if data.get('raid_dodge_active', False):
        dodge_chance = data.get('raid_dodge_chance', 50)
        if random.randint(1, 100) <= dodge_chance:
            await cb.message.answer(f"💨 <b>УКЛОНЕНИЕ!</b> Вы избежали урона!")
            await state.update_data(raid_dodge_active=False)
            await raid_render(cb, state)
            return
        await state.update_data(raid_dodge_active=False)
    
    shield = data.get('raid_shield', 0)
    if shield > 0:
        if shield >= bot_dmg:
            await cb.message.answer(f"🛡️ Щит поглотил урон!")
            await state.update_data(raid_shield=0)
            await raid_render(cb, state)
            return
        bot_dmg -= shield
        await state.update_data(raid_shield=0)
    
    defense = data.get('raid_defense_buff', 0)
    if defense > 0:
        bot_dmg = max(1, bot_dmg - defense)
        await state.update_data(raid_defense_buff=0)
    
    if data['raid_trap_level'] > 0: bot_dmg += data['raid_trap_level'] * 2
    
    new_player_hp = data['raid_player_hp'] - bot_dmg
    new_mana = min(6, data['raid_player_mana'] + 2)
    
    await state.update_data(raid_player_hp=new_player_hp, raid_player_mana=new_mana, raid_turn=data['raid_turn'] + 1)
    await cb.message.answer(f"🛡️ Защитник контратакует! Получено <b>{bot_dmg}</b> урона.")
    
    if new_player_hp <= 0:
        await raid_finish(cb, state, win=False)
        return
    await raid_render(cb, state)

async def raid_finish(cb: types.CallbackQuery, state: FSMContext, win: bool):
    try:
        data = await state.get_data()
        u = get_user(cb.from_user.id)
        
        # Безопасное получение значений из базы
        try:
            current_gold = int(u[2]) if u[2] and str(u[2]).strip() and str(u[2]) != '{}' else 0
        except:
            current_gold = 0
            
        try:
            current_rating = int(u[3]) if u[3] and str(u[3]).strip() and str(u[3]) != '{}' else 0
        except:
            current_rating = 0
            
        try:
            current_energy = int(u[4]) if u[4] and str(u[4]).strip() and str(u[4]) != '{}' else 5
        except:
            current_energy = 5
            
        try:
            current_wins = int(u[14]) if u[14] and str(u[14]).strip() and str(u[14]) != '{}' else 0
        except:
            current_wins = 0
            
        try:
            current_losses = int(u[15]) if u[15] and str(u[15]).strip() and str(u[15]) != '{}' else 0
        except:
            current_losses = 0
        
        if win:
            gold = 50 + random.randint(0, 20)
            rating = 15 + random.randint(0, 10)
            if data.get('raid_trap_level', 0) > 0:
                gold = max(10, int(gold * (1 - data['raid_trap_level'] * 0.15)))
                rating = max(5, int(rating * (1 - data['raid_trap_level'] * 0.1)))
            update_user(cb.from_user.id, gold=current_gold + gold, rating=current_rating + rating, energy=max(0, current_energy - 1), wins=current_wins + 1)
            text = f"✅ <b>РЕЙД УСПЕШЕН!</b>\n\n🪙 +{gold}\n⭐ +{rating}\n⚡ -1 энергия"
        else:
            rating_loss = 10 + (data.get('raid_trap_level', 0) * 3)
            update_user(cb.from_user.id, energy=max(0, current_energy - 1), rating=max(0, current_rating - rating_loss), losses=current_losses + 1)
            text = f"❌ <b>РЕЙД ПРОВАЛЕН!</b>\n\n⭐ -{rating_loss}\n⚡ -1 энергия"
        await cb.message.answer(text, reply_markup=main_kb())
        await state.clear()
    except Exception as e:
        print(f"Error in raid_finish: {e}")
        await cb.message.answer("⚠️ Произошла ошибка при завершении рейда", reply_markup=main_kb())
        await state.clear()
    await cb.answer()

@dp.callback_query(States.battle_raid, F.data == "raid_back_render")
async def raid_back_render(cb: types.CallbackQuery, state: FSMContext):
    await raid_render(cb, state)
    await cb.answer()

@dp.callback_query(F.data == "menu")
async def go_menu(cb: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await cmd_start(cb.message, state)
    await cb.answer()

@dp.message(Command("addtest"))
async def add_test(msg: types.Message):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("""INSERT OR REPLACE INTO players VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (999999, "TestBot", 500, 900, 5, int(time.time()), None, '{"1":5}', '{"basic":0,"rare":0,"epic":0}', '["1","1","1"]', 2, 0, '{"max_rarity":1,"relic_slots":0,"trap_level":0,"equipment_slots":0,"mana_regen":0,"crit_chance":0}', '{}', '{}', 5, 0))
    conn.commit()
    conn.close()
    await msg.answer("✅ Тестовый игрок добавлен! ID: 999999")


logging.basicConfig(level=logging.INFO)

async def main():
    init_db()
    BOT_TOKEN = os.getenv("BOT_TOKEN")
    if not BOT_TOKEN:
        logging.error("❌ BOT_TOKEN не найден в переменных окружения!")
        return

    # ✅ ПЕРЕВОД НА WEBHOOK (обязательно для бесплатного хостинга)
    WEBHOOK_URL = os.getenv("WEBHOOK_URL")
    if WEBHOOK_URL:
        await bot.delete_webhook(drop_pending_updates=True)
        await bot.set_webhook(url=WEBHOOK_URL)
        logging.info(f"✅ Webhook установлен: {WEBHOOK_URL}")
        # Запускаем бота без polling
        await dp.start_webhook(path="/webhook")
    else:
        # Fallback на polling (будет спать на Render)
        logging.warning("⚠️ WEBHOOK_URL не задан. Использую polling (может засыпать).")
        await dp.start_polling(bot)

if __name__ == "__main__":
    from aiohttp import web
    from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
    import os
    
    # Настройки сервера
    WEBAPP_HOST = '0.0.0.0'
    WEBAPP_PORT = int(os.environ.get('PORT', 8080))
    
    async def on_startup(app):
        if WEBHOOK_URL:
            await bot.set_webhook(WEBHOOK_URL, allowed_updates=dp.resolve_used_update_types())
        else:
            logging.warning("WEBHOOK_URL не задан!")
    
    async def on_shutdown(app):
        logging.info("Бот останавливается...")
        await bot.delete_webhook()
        await bot.session.close()
    
    # Создаем веб-приложение
    app = web.Application()
    app.on_startup.append(on_startup)
    app.on_shutdown.append(on_shutdown)
    
    # Настраиваем обработчик вебхука
    SimpleRequestHandler(dispatcher=dp, bot=bot).register(app, path="/webhook")
    setup_application(app, dp, bot=bot)
    
    print(f"🚀 Бот запущен на порту {WEBAPP_PORT}")
    web.run_app(app, host=WEBAPP_HOST, port=WEBAPP_PORT)
