import asyncio
import logging
import os
from datetime import datetime, timedelta
from typing import Dict, Any

import aiosqlite
from aiogram import Bot, Dispatcher, Router, F, BaseMiddleware
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode, ChatMemberStatus
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, TelegramObject

# ============ КОНФИГ ============
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = 8777046904
ADMIN_USERNAME = "DietologLobar"

# НАСТРОЙКИ КАНАЛА И ЧАТА
CHANNEL_USERNAME = "DietologLobarhon"
CHANNEL_URL = f"https://t.me/{CHANNEL_USERNAME}"
# ВАЖНО: Замени на реальный ID чата @OzishChati (начинается с -100...)
CHAT_ID = -1001234567890 

DATA_DIR = os.getenv('DATA_DIR', '/app/data')
os.makedirs(DATA_DIR, exist_ok=True)
DB_PATH = os.path.join(DATA_DIR, 'bot.db')

START_TIME = datetime.now()

# ============ ТЕКСТЫ ============
TEXTS = {
    "ru": {
        "choose_lang": "🌐 Тилни танланг / Выберите язык:",
        "hello": "👋 Здравствуйте! Я помогу вам похудеть безопасно.\n\nВыберите ваш пол:",
        "gender_btn": ["👩 Женский", "👨 Мужской"],
        "enter_age": "🎂 Возраст (например: 28):",
        "enter_weight": "⚖️ Текущий вес в кг (например: 72.5):",
        "enter_height": "📏 Рост в см (например: 165):",
        "enter_target": "🎯 Желаемый вес в кг (например: 65):",
        "calculated": "✅ Норма: <b>{kcal} ккал/день</b>.\nИМТ: <b>{bmi}</b> ({bmi_text}).\n\nВаш план готов! Используйте меню ниже.",
        
        "menu_btn": "📅 План", "next_btn": "➡️ Далее", "stats_btn": "📊 Статистика", "daily_btn": "📝 Дневник", "sub_btn": "💳 Оплата",
        "ref_btn": "🔗 Пригласить друга",
        
        "day_header": "📅 <b>День {day} из 60</b> ({phase})\n\n",
        "day_food": "<b>Меню (~{kcal} ккал):</b>\n{food}\n\n",
        "day_workout": "<b>Тренировка:</b>\n{workout}\n\n",
        "day_tip": "{tip}",
        
        "enter_daily": "📝 <b>Дневник</b>\nВведите через запятую: <b>Вес, Шаги, Вода, Сон, Голод (1-10)</b>\n\n<i>Пример: 71.5, 8000, 1.5, 7, 4</i>",
        "daily_saved": "✅ Сохранено! Текущий вес: {weight} кг.",
        "daily_error": "⚠️ Ошибка. Введите 5 чисел.",
        
        "stats_header": "📊 <b>Аналитика</b>\n",
        "stats_weight": "Старт: {start} | Сейчас: {current} | Цель: {target}\n",
        "stats_diff": "📉 Отвес: <b>{diff} кг</b>\n",
        "stats_graph": "📈 График:\n{graph}\n",
        "stats_advice": "💡 {advice}",
        
        "advice_good": "Вы отлично идете по плану!",
        "advice_stall": "Вес встал. Проверьте соль и сон.",
        "advice_gain": "Вес растет. Вернитесь к плану.",
        
        "need_sub": "⛔ Для доступа нужна подписка.\nНапишите @DietologLobar",
        "payment_text": "💳 Оплата: @DietologLobar\n\nПосле перевода нажмите кнопку.",
        "paid_btn": "✅ Я оплатил",
        "claim_sent": "Заявка отправлена.",
        "sub_active": "🎉 Подписка активна до {date}!",
        "blocked": "⛔ Вы заблокированы.",
        "error_num": "⚠️ Введите число.",
        
        # Тексты для канала
        "channel_need_sub": "⛔ <b>Для использования бота обязательно подпишитесь на наш канал!</b>\n\nНажмите кнопку ниже, подпишитесь и вернитесь сюда.",
        "channel_sub_btn": "📢 Подписаться на канал",
        "channel_check_btn": "✅ Я подписался",
        "channel_checked_ok": "✅ Спасибо за подписку! Теперь вы можете пользоваться ботом.",
        "channel_checked_fail": "❌ Вы еще не подписались на канал!",

        "ref_text": (
            "🔗 <b>Пригласи друзей и получи подписку бесплатно!</b>\n\n"
            "За каждого друга, который зайдет по твоей ссылке, подпишется на канал и напишет сообщение в наш чат, ты получаешь баллы.\n\n"
            "<b>5 друзей = +3 дня подписки!</b>\n\n"
            "Твоя ссылка:\n<code>{link}</code>\n\n"
            "Приглашено друзей: <b>{count} / 5</b>"
        ),
        "ref_new_user": "🎉 Ты пришел по приглашению! Зайди в наш чат @OzishChati и напиши любое сообщение, чтобы твой друг получил балл.",
        "ref_success": "🎉 Поздравляем! Вы пригласили {count} человек и получили <b>+3 дня подписки</b>! Ваша подписка активна до {date}.",
        
        "anti_edema_title": "\n\n💧 <b>Анти-отеки:</b>\n",
        "anti_edema_rules": "1. Соль до 3-5 г.\n2. Калий (банан).\n3. 2л воды.\n4. Контрастное умывание.\n5. Сон на спине.",
        "bmi_low": "Недостаточный вес", "bmi_normal": "Норма", "bmi_over": "Избыточный вес", "bmi_obese": "Ожирение"
    }
}
TEXTS["uz"] = TEXTS["ru"] 

def t(lang, key, **kwargs):
    text = TEXTS.get(lang, TEXTS["ru"]).get(key, "")
    return text.format(**kwargs) if kwargs else text

# ============ ЛОГИКА ПЛАНА ============
def get_bmi_text(bmi, lang):
    if bmi < 18.5: return "Недостаточный вес"
    elif bmi < 25: return "Норма"
    elif bmi < 30: return "Избыточный вес"
    else: return "Ожирение"

def get_personal_plan(user: dict, day: int, lang: str):
    bmi = user["current_weight"] / ((user["height"]/100) ** 2)
    age = user["age"]
    
    if bmi >= 25:
        food_advice = "🚫 Без сахара/мучного.\n🍳 Завтрак: 2 яйца.\n🍗 Обед: 120г курицы + гречка.\n🐟 Ужин: Рыба + овощи."
    else:
        food_advice = "🍳 Завтрак: Овсянка + яйцо.\n🍗 Обед: 100г мяса + гречка + салат.\n🐟 Ужин: Рыба + овощи."

    if age > 45:
        workout_advice = "🔥 Ходьба 45 мин.\n💪 20 приседаний, планка 30 сек."
    else:
        workout_advice = "🔥 Ходьба 50 мин (интервальная).\n💪 Круг (3 раза): 20 приседаний, 15 выпадов, 15 подъемов таза, планка 40 сек."

    if day <= 20: phase = "Фаза 1: Адаптация"
    elif day <= 40: phase = "Фаза 2: Жиросжигание"
    else: phase = "Фаза 3: Закрепление"

    tip = "💧 Пейте 2 литра воды!"
    if day % 2 == 0:
        tip += t(lang, "anti_edema_title") + t(lang, "anti_edema_rules")

    return {"phase": phase, "food": food_advice, "workout": workout_advice, "tip": tip, "bmi": round(bmi, 1), "bmi_text": get_bmi_text(bmi, lang)}

# ============ БД ============
async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY, username TEXT, first_name TEXT, language TEXT,
            subscription_end TEXT, is_blocked INTEGER DEFAULT 0, registered_at TEXT, last_active TEXT,
            gender TEXT, age INTEGER, height REAL, current_day INTEGER DEFAULT 1,
            start_weight REAL, target_weight REAL, current_weight REAL, daily_kcal INTEGER,
            referrer_id INTEGER DEFAULT NULL, ref_count INTEGER DEFAULT 0, ref_credited INTEGER DEFAULT 0)""")
        await db.execute("""CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, date TEXT,
            weight REAL, steps INTEGER, water REAL, sleep REAL, hunger INTEGER)""")
        await db.commit()

async def get_user(user_id: int) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
    return dict(row) if row else None

async def update_user(user_id: int, **kwargs):
    fields = ", ".join(f"{k} = ?" for k in kwargs)
    values = list(kwargs.values()) + [user_id]
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(f"UPDATE users SET {fields} WHERE user_id = ?", values)
        await db.commit()

async def create_user_if_not_exists(user_id: int, username: str, first_name: str):
    now = datetime.now().isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT OR IGNORE INTO users (user_id, username, first_name, registered_at, last_active) VALUES (?, ?, ?, ?, ?)", 
                         (user_id, username, first_name, now, now))
        await db.execute("UPDATE users SET last_active = ?, username = ?, first_name = ? WHERE user_id = ?", (now, username, first_name, user_id))
        await db.commit()

async def add_history(user_id: int, weight: float, steps: int, water: float, sleep: float, hunger: int):
    date_str = datetime.now().strftime("%Y-%m-%d")
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM history WHERE user_id = ? AND date = ?", (user_id, date_str))
        await db.execute("INSERT INTO history (user_id, date, weight, steps, water, sleep, hunger) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (user_id, date_str, weight, steps, water, sleep, hunger))
        await db.commit()

async def get_history(user_id: int) -> list:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM history WHERE user_id = ? ORDER BY date ASC", (user_id,)) as cursor:
            rows = await cursor.fetchall()
    return [dict(r) for r in rows]

async def is_subscribed(user_id: int) -> bool:
    user = await get_user(user_id)
    if not user or not user.get("subscription_end"): return False
    return datetime.fromisoformat(user["subscription_end"]) > datetime.now()

async def is_blocked(user_id: int) -> bool:
    user = await get_user(user_id)
    return bool(user and user.get("is_blocked"))

async def get_lang(user_id: int) -> str:
    user = await get_user(user_id)
    return user["language"] if user and user.get("language") else "ru"

# ============ ПРОВЕРКА КАНАЛА ============
async def check_channel_sub(user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(chat_id=f"@{CHANNEL_USERNAME}", user_id=user_id)
        if member.status in [ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.CREATOR]:
            return True
    except Exception as e:
        logging.error(f"Ошибка проверки подписки: {e}")
    return False

# ============ MIDDLEWARE (БЛОКИРОВКА И ПРОВЕРКА КАНАЛА) ============
class CheckMiddleware(BaseMiddleware):
    async def __call__(self, handler, event: TelegramObject, data: Dict[str, Any]):
        user = data.get("event_from_user")
        if not user: return await handler(event, data)
        
        await create_user_if_not_exists(user.id, user.username or "", user.first_name)
        
        # Админ всегда пропускается
        if user.id == ADMIN_ID: return await handler(event, data)

        # 1. Проверка на бан
        if await is_blocked(user.id):
            msg = "⛔ Вы заблокированы."
            if isinstance(event, Message): await event.answer(msg)
            elif isinstance(event, CallbackQuery): await event.answer(msg, show_alert=True)
            return

        # 2. Пропускаем кнопку "Я подписался" для проверки
        if isinstance(event, CallbackQuery) and event.data == "check_sub":
            return await handler(event, data)

        # 3. Проверка подписки на канал
        is_channel_sub = await check_channel_sub(user.id)
        if not is_channel_sub:
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=t(await get_lang(user.id), "channel_sub_btn"), url=CHANNEL_URL)],
                [InlineKeyboardButton(text=t(await get_lang(user.id), "channel_check_btn"), callback_data="check_sub")]
            ])
            msg = t(await get_lang(user.id), "channel_need_sub")
            if isinstance(event, Message):
                await event.answer(msg, reply_markup=kb, disable_web_page_preview=True)
            elif isinstance(event, CallbackQuery):
                await event.message.answer(msg, reply_markup=kb, disable_web_page_preview=True)
                await event.answer()
            return

        # 4. Обработка Deep Link (Реферал)
        if isinstance(event, Message) and event.text and event.text.startswith("/start "):
            try:
                referrer_id = int(event.text.split()[1])
                if referrer_id != user.id and await get_user(referrer_id):
                    curr_user = await get_user(user.id)
                    if not curr_user.get("referrer_id"):
                        await update_user(user.id, referrer_id=referrer_id)
            except: pass

        return await handler(event, data)

# ============ КЛАВИАТУРЫ ============
def get_lang_kb():
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang_ru")], [InlineKeyboardButton(text="🇺🇿 Ўзбекча", callback_data="lang_uz")]])

def get_gender_kb(lang):
    btns = TEXTS[lang]["gender_btn"]
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=btns[0], callback_data="gender_female"), InlineKeyboardButton(text=btns[1], callback_data="gender_male")]])

def get_main_kb(lang):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t(lang, "menu_btn"), callback_data="menu"), InlineKeyboardButton(text=t(lang, "next_btn"), callback_data="next")],
        [InlineKeyboardButton(text=t(lang, "daily_btn"), callback_data="daily"), InlineKeyboardButton(text=t(lang, "stats_btn"), callback_data="stats")],
        [InlineKeyboardButton(text=t(lang, "ref_btn"), callback_data="ref_link")],
        [InlineKeyboardButton(text=t(lang, "sub_btn"), callback_data="subscribe")]
    ])

def get_payment_kb(lang):
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="@DietologLobar", url=f"https://t.me/{ADMIN_USERNAME}")],[InlineKeyboardButton(text=t(lang, "paid_btn"), callback_data="paid_claim")]])

# ============ БОТ ============
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()
router = Router()
temp_steps = {} 

# ОБРАБОТЧИК КНОПКИ "Я ПОДПИСАЛСЯ"
@router.callback_query(F.data == "check_sub")
async def handle_check_sub(callback: CallbackQuery):
    lang = await get_lang(callback.from_user.id)
    if await check_channel_sub(callback.from_user.id):
        await callback.message.delete()
        await callback.message.answer(t(lang, "channel_checked_ok"))
        await callback.message.answer(t(lang, "choose_lang"), reply_markup=get_lang_kb())
    else:
        await callback.answer(t(lang, "channel_checked_fail"), show_alert=True)

# ОБРАБОТЧИК ЧАТА (@OzishChati)
@router.message(F.chat.id == CHAT_ID)
async def handle_chat_message(message: Message):
    if message.from_user.is_bot: return
    
    user = await get_user(message.from_user.id)
    if not user or not user.get("referrer_id") or user.get("ref_credited"): return
    
    referrer_id = user["referrer_id"]
    referrer = await get_user(referrer_id)
    if not referrer: return

    await update_user(user.id, ref_credited=1)
    new_count = referrer.get("ref_count", 0) + 1
    
    if new_count >= 5:
        now = datetime.now()
        current_end = datetime.fromisoformat(referrer["subscription_end"]) if referrer.get("subscription_end") else now
        base = current_end if current_end > now else now
        new_end = base + timedelta(days=3)
        
        await update_user(referrer_id, ref_count=0, subscription_end=new_end.isoformat())
        try: await message.bot.send_message(referrer_id, t(await get_lang(referrer_id), "ref_success", count=new_count, date=new_end.date()))
        except: pass
    else:
        await update_user(referrer_id, ref_count=new_count)

# ЛИЧНЫЕ СООБЩЕНИЯ
@router.message(CommandStart(), F.chat.type == "private")
async def cmd_start(message: Message):
    user = await get_user(message.from_user.id)
    if user and user.get("referrer_id") and not user.get("ref_credited"):
        await message.answer(t(await get_lang(message.from_user.id), "ref_new_user"))
    await message.answer(t("ru", "choose_lang"), reply_markup=get_lang_kb())

@router.callback_query(F.data == "ref_link")
async def show_ref_link(callback: CallbackQuery):
    user_id = callback.from_user.id
    lang = await get_lang(user_id)
    user = await get_user(user_id)
    bot_info = await callback.bot.get_me()
    link = f"https://t.me/{bot_info.username}?start={user_id}"
    await callback.message.answer(t(lang, "ref_text", link=link, count=user.get("ref_count", 0)), reply_markup=get_main_kb(lang))
    await callback.answer()

@router.callback_query(F.data.startswith("lang_"))
async def set_lang(callback: CallbackQuery):
    lang = callback.data.split("_")[1]
    await update_user(callback.from_user.id, language=lang)
    await callback.message.edit_text(t(lang, "hello"), reply_markup=get_gender_kb(lang))

@router.callback_query(F.data.startswith("gender_"))
async def set_gender(callback: CallbackQuery):
    gender = callback.data.split("_")[1]
    lang = await get_lang(callback.from_user.id)
    await update_user(callback.from_user.id, gender=gender)
    temp_steps[callback.from_user.id] = {"step": "age"}
    await callback.message.edit_text(t(lang, "enter_age"))

@router.message(F.text & ~F.text.startswith("/") & (F.chat.type == "private"))
async def handle_text(message: Message):
    user_id = message.from_user.id
    lang = await get_lang(user_id)
    user = await get_user(user_id)
    
    if user_id in temp_steps and temp_steps[user_id].get("step") == "daily_input":
        try:
            parts = message.text.replace(",", " ").split()
            if len(parts) < 5: raise ValueError
            w, st, wa, sl, hu = float(parts[0]), int(parts[1]), float(parts[2]), float(parts[3]), int(parts[4])
            await add_history(user_id, w, st, wa, sl, hu)
            await update_user(user_id, current_weight=w)
            del temp_steps[user_id]
            await message.answer(t(lang, "daily_saved", weight=w), reply_markup=get_main_kb(lang))
        except:
            await message.answer(t(lang, "daily_error"))
        return

    if not user.get("current_weight"):
        if user_id not in temp_steps: temp_steps[user_id] = {"step": "age"}
        try: val = float(message.text.replace(",", "."))
        except ValueError: return await message.answer(t(lang, "error_num"))

        step = temp_steps[user_id]["step"]
        if step == "age":
            temp_steps[user_id]["age"] = int(val); temp_steps[user_id]["step"] = "weight"; await message.answer(t(lang, "enter_weight"))
        elif step == "weight":
            temp_steps[user_id]["start_weight"] = val; temp_steps[user_id]["step"] = "height"; await message.answer(t(lang, "enter_height"))
        elif step == "height":
            temp_steps[user_id]["height"] = val; temp_steps[user_id]["step"] = "target"; await message.answer(t(lang, "enter_target"))
        elif step == "target":
            d = temp_steps[user_id]
            if user["gender"] == "female": bmr = 10 * d["start_weight"] + 6.25 * d["height"] - 5 * d["age"] - 161
            else: bmr = 10 * d["start_weight"] + 6.25 * d["height"] - 5 * d["age"] + 5
            tdee = bmr * 1.375 
            bmi = d["start_weight"] / ((d["height"]/100) ** 2)
            target_kcal = int(tdee - (500 if bmi >= 30 else 400))
            await update_user(user_id, age=d["age"], height=d["height"], start_weight=d["start_weight"], current_weight=d["start_weight"], target_weight=val, daily_kcal=target_kcal)
            del temp_steps[user_id]
            bmi_val = round(bmi, 1)
            await message.answer(t(lang, "calculated", kcal=target_kcal, bmi=bmi_val, bmi_text=get_bmi_text(bmi_val, lang)), reply_markup=get_main_kb(lang))
        return

    await message.answer("Используйте кнопки 👇", reply_markup=get_main_kb(lang))

@router.callback_query(F.data == "daily")
async def open_daily(callback: CallbackQuery):
    lang = await get_lang(callback.from_user.id)
    if not await is_subscribed(callback.from_user.id):
        return await callback.message.answer(t(lang, "need_sub"), reply_markup=get_payment_kb(lang))
    temp_steps[callback.from_user.id] = {"step": "daily_input"}
    await callback.message.answer(t(lang, "enter_daily"))
    await callback.answer()

@router.callback_query(F.data == "stats")
async def show_stats(callback: CallbackQuery):
    user_id = callback.from_user.id
    lang = await get_lang(user_id)
    if not await is_subscribed(user_id):
        return await callback.message.answer(t(lang, "need_sub"), reply_markup=get_payment_kb(lang))
    
    user = await get_user(user_id)
    history = await get_history(user_id)
    if not history: return await callback.message.answer("Нет записей. Сначала заполните Дневник.")
    
    last_7 = history[-7:]
    min_w = min([h["weight"] for h in last_7])
    graph = "\n".join([f"{h['date'][5:]}: {'█' * max(1, int((h['weight']-min_w+1)*3))} {h['weight']}" for h in last_7])
    diff = round(user["start_weight"] - history[-1]["weight"], 1)
    
    advice = t(lang, "advice_good")
    if len(history) >= 3:
        last_3 = [h["weight"] for h in history[-3:]]
        if last_3[0] == last_3[1] == last_3[2]: advice = t(lang, "advice_stall")
        elif last_3[2] > last_3[0]: advice = t(lang, "advice_gain")

    text = t(lang, "stats_header")
    text += t(lang, "stats_weight", start=user["start_weight"], current=history[-1]["weight"], target=user["target_weight"])
    text += t(lang, "stats_diff", diff=diff)
    text += t(lang, "stats_graph", graph=graph)
    text += t(lang, "stats_advice", advice=advice)

    await callback.message.answer(text, reply_markup=get_main_kb(lang))
    await callback.answer()

@router.callback_query(F.data.in_({"menu", "next"}))
async def show_plan(callback: CallbackQuery):
    user_id = callback.from_user.id
    lang = await get_lang(user_id)
    
    user = await get_user(user_id)
    day = user.get("current_day", 1)
    subscribed = await is_subscribed(user_id)

    if callback.data == "next":
        if not subscribed and day >= 2:
            await callback.message.answer(t(lang, "need_sub"), reply_markup=get_payment_kb(lang))
            await callback.answer()
            return
        day += 1
        if day > 60: return await callback.message.answer("🏆 Вы прошли 60 дней!")
        await update_user(user_id, current_day=day)

    if callback.data == "menu" and not subscribed and day > 2:
         await callback.message.answer(t(lang, "need_sub"), reply_markup=get_payment_kb(lang))
         await callback.answer()
         return

    plan = get_personal_plan(user, day, lang)
    text = t(lang, "day_header", day=day, phase=plan['phase'])
    text += t(lang, "day_food", kcal=user["daily_kcal"], food=plan['food'])
    text += t(lang, "day_workout", workout=plan['workout'])
    text += t(lang, "day_tip", tip=plan['tip'])
    
    if not subscribed and day == 2:
        text += "\n\n⚠️ <b>Это последний бесплатный день.</b>\nДля продолжения напишите: @" + ADMIN_USERNAME

    await callback.message.answer(text, reply_markup=get_main_kb(lang))
    await callback.answer()

@router.callback_query(F.data == "subscribe")
async def subscribe(callback: CallbackQuery):
    lang = await get_lang(callback.from_user.id)
    await callback.message.answer(t(lang, "payment_text"), reply_markup=get_payment_kb(lang))
    await callback.answer()

@router.callback_query(F.data == "paid_claim")
async def paid_claim(callback: CallbackQuery):
    user = callback.from_user
    lang = await get_lang(user.id)
    await callback.bot.send_message(ADMIN_ID, f"💰 Заявка: {user.full_name} (@{user.username})\nID: <code>{user.id}</code>\n\n/activate {user.id} 30")
    await callback.message.answer(t(lang, "claim_sent"))
    await callback.answer()

# ============ АДМИН-ПАНЕЛЬ ============
def admin_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Статистика бота", callback_data="adm_stats")],
        [InlineKeyboardButton(text="👥 Пользователи", callback_data="adm_users")],
        [InlineKeyboardButton(text="🔍 Поиск", callback_data="adm_search")],
        [InlineKeyboardButton(text="🗄 Состояние БД", callback_data="adm_db")],
        [InlineKeyboardButton(text="📢 Рассылка", callback_data="adm_broadcast")]
    ])

@router.message(Command("admin"), F.chat.type == "private")
async def cmd_admin(message: Message):
    if message.from_user.id != ADMIN_ID: return
    await message.answer("👑 <b>Админ-панель</b>\nВыберите действие:", reply_markup=admin_kb())

@router.callback_query(F.data.startswith("adm_"))
async def admin_handlers(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID: return
    
    if callback.data == "adm_stats":
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute("SELECT COUNT(*) FROM users") as c: total = (await c.fetchone())[0]
            async with db.execute("SELECT COUNT(*) FROM users WHERE subscription_end > ?", (datetime.now().isoformat(),)) as c: active = (await c.fetchone())[0]
            async with db.execute("SELECT COUNT(*) FROM users WHERE is_blocked=1") as c: blocked = (await c.fetchone())[0]
        uptime = str(datetime.now() - START_TIME).split('.')[0]
        text = f"📊 <b>Статистика</b>\n\n👥 Всего: {total}\n✅ С подпиской: {active}\n🚫 Заблокировано: {blocked}\n\n⏱ Аптайм: {uptime}"
        await callback.message.answer(text, reply_markup=admin_kb())

    elif callback.data == "adm_db":
        try:
            size = os.path.getsize(DB_PATH) / 1024
            async with aiosqlite.connect(DB_PATH) as db:
                async with db.execute("SELECT COUNT(*) FROM history") as c: history_count = (await c.fetchone())[0]
            text = f"🗄 <b>Состояние БД</b>\n\n✅ Подключение: OK\n💾 Размер: {size:.2f} KB\n📝 Записей в дневнике: {history_count}\n🟢 Статус: Работает стабильно"
            await callback.message.answer(text, reply_markup=admin_kb())
        except Exception as e:
            await callback.message.answer(f"❌ Ошибка БД: {e}")

    elif callback.data == "adm_users":
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM users ORDER BY registered_at DESC LIMIT 10") as cursor:
                users = await cursor.fetchall()
        text = "👥 <b>Последние 10 пользователей:</b>\n\n"
        for u in users:
            sub = "✅" if u["subscription_end"] and datetime.fromisoformat(u["subscription_end"]) > datetime.now() else "⛔"
            blk = "🚫" if u["is_blocked"] else ""
            text += f"{sub} {blk} <code>{u['user_id']}</code> | @{u['username']} | {u['first_name']} | Реф: {u['ref_count']}\n"
        await callback.message.answer(text, reply_markup=admin_kb())

    elif callback.data == "adm_search":
        await callback.message.answer("🔍 Введите ID или @username для поиска:")
        temp_steps[ADMIN_ID] = {"step": "adm_search_input"}

    elif callback.data == "adm_broadcast":
        await callback.message.answer("📢 Отправьте текст для рассылки:")
        temp_steps[ADMIN_ID] = {"step": "adm_broadcast_input"}
    
    await callback.answer()

@router.message(F.text & ~F.text.startswith("/") & (F.chat.type == "private"))
async def handle_admin_input(message: Message):
    if message.from_user.id != ADMIN_ID: return
    state = temp_steps.get(ADMIN_ID)
    if not state: return
    
    if state.get("step") == "adm_search_input":
        query = message.text.strip()
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            if query.startswith("@"):
                async with db.execute("SELECT * FROM users WHERE username = ?", (query[1:],)) as c: user = await c.fetchone()
            else:
                async with db.execute("SELECT * FROM users WHERE user_id = ?", (int(query) if query.isdigit() else 0,)) as c: user = await c.fetchone()
        
        if not user:
            await message.answer("❌ Пользователь не найден.", reply_markup=admin_kb())
        else:
            sub = "✅ Активна" if user["subscription_end"] and datetime.fromisoformat(user["subscription_end"]) > datetime.now() else "⛔ Нет"
            blk = "🚫 Заблокирован" if user["is_blocked"] else "🟢 Активен"
            text = (f"👤 <b>Профиль</b>\nID: <code>{user['user_id']}</code>\nИмя: {user['first_name']} (@{user['username']})\n"
                    f"Реф. счетчик: {user['ref_count']}\nПригласил (ID): {user['referrer_id']}\n\n"
                    f"Подписка: {sub}\nБлокировка: {blk}\n\n"
                    f"Управление:\n/activate {user['user_id']} 30\n/block {user['user_id']}\n/unblock {user['user_id']}\n/delete {user['user_id']}")
            await message.answer(text, reply_markup=admin_kb())
        del temp_steps[ADMIN_ID]

    elif state.get("step") == "adm_broadcast_input":
        text_to_send = message.text
        del temp_steps[ADMIN_ID]
        await message.answer("⏳ Начинаю рассылку...")
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute("SELECT user_id FROM users WHERE is_blocked = 0") as cursor:
                users = await cursor.fetchall()
        success, fail = 0, 0
        for (uid,) in users:
            try:
                await message.bot.send_message(uid, text_to_send)
                success += 1
                await asyncio.sleep(0.05) 
            except: fail += 1
        await message.answer(f"✅ Рассылка завершена.\nДоставлено: {success}\nОшибок: {fail}", reply_markup=admin_kb())

# ============ КОМАНДЫ МОДЕРАЦИИ ============
@router.message(Command("activate"))
async def cmd_activate(message: Message):
    if message.from_user.id != ADMIN_ID: return
    args = message.text.split()
    if len(args) != 3: return await message.answer("Использование: /activate <id> <days>")
    try: target_id, days = int(args[1]), int(args[2])
    except ValueError: return await message.answer("Ошибка в числах.")
    end_date = datetime.now() + timedelta(days=days)
    await update_user(target_id, subscription_end=end_date.isoformat())
    await message.answer(f"✅ {target_id} активирован до {end_date.date()}")

@router.message(Command("block"))
async def cmd_block(message: Message):
    if message.from_user.id != ADMIN_ID: return
    args = message.text.split()
    if len(args) != 2: return await message.answer("Использование: /block <id>")
    await update_user(int(args[1]), is_blocked=1)
    await message.answer(f"🚫 Пользователь {args[1]} заблокирован.")

@router.message(Command("unblock"))
async def cmd_unblock(message: Message):
    if message.from_user.id != ADMIN_ID: return
    args = message.text.split()
    if len(args) != 2: return await message.answer("Использование: /unblock <id>")
    await update_user(int(args[1]), is_blocked=0)
    await message.answer(f"✅ Пользователь {args[1]} разблокирован.")

@router.message(Command("delete"))
async def cmd_delete(message: Message):
    if message.from_user.id != ADMIN_ID: return
    args = message.text.split()
    if len(args) != 2: return await message.answer("Использование: /delete <id>")
    uid = int(args[1])
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM users WHERE user_id = ?", (uid,))
        await db.execute("DELETE FROM history WHERE user_id = ?", (uid,))
        await db.commit()
    await message.answer(f"🗑 Пользователь {uid} и его данные полностью удалены.")

# ============ MAIN ============
async def main():
    logging.basicConfig(level=logging.INFO)
    await init_db()
    dp.message.middleware(CheckMiddleware())
    dp.callback_query.middleware(CheckMiddleware())
    dp.include_router(router)
    await bot.delete_webhook(drop_pending_updates=True)
    print("Бот успешно запущен. Проверка канала и подписки активна.")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
