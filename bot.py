import asyncio
import aiosqlite
import os
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from apscheduler.schedulers.asyncio import AsyncIOScheduler

TOKEN = TOKEN = os.getenv(8703650001:AAEVkjAA8EBTR0sU4vzdHM9494LdHpySlG0)

bot = Bot(token=8703650001:AAEVkjAA8EBTR0sU4vzdHM9494LdHpySlG0)
dp = Dispatcher()

DB_NAME = "bot.db"

DAILY_NORM = 10
REWARD = 80
MIN_BALANCE = 10000
MIN_DAYS = 10


# 📋 Меню
menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📊 Статистика")],
        [KeyboardButton(text="🔗 Моє посилання")],
        [KeyboardButton(text="💸 Вивести кошти")]
    ],
    resize_keyboard=True
)


# 🗄️ База
async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            invited INTEGER DEFAULT 0,
            balance INTEGER DEFAULT 0,
            day INTEGER DEFAULT 1
        )
        """)

        await db.execute("""
        CREATE TABLE IF NOT EXISTS invites (
            user_id INTEGER,
            invited_today INTEGER DEFAULT 0
        )
        """)

        await db.execute("""
        CREATE TABLE IF NOT EXISTS referrals (
            user_id INTEGER UNIQUE,
            referrer_id INTEGER
        )
        """)

        await db.commit()


# 👤 Реєстрація
async def register(user_id):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
        await db.execute("INSERT OR IGNORE INTO invites (user_id) VALUES (?)", (user_id,))
        await db.commit()


# 🚀 START
@dp.message(CommandStart())
async def start(message: types.Message):
    user_id = message.from_user.id
    args = message.text.split()

    await register(user_id)

    # 🔗 Реферал
    if len(args) > 1:
        ref_id = int(args[1])

        if ref_id != user_id:
            async with aiosqlite.connect(DB_NAME) as db:
                cur = await db.execute("SELECT * FROM referrals WHERE user_id=?", (user_id,))
                if not await cur.fetchone():

                    await db.execute(
                        "INSERT INTO referrals (user_id, referrer_id) VALUES (?, ?)",
                        (user_id, ref_id)
                    )

                    await db.execute(
                        "UPDATE users SET invited = invited + 1, balance = balance + ? WHERE user_id=?",
                        (REWARD, ref_id)
                    )

                    await db.execute(
                        "UPDATE invites SET invited_today = invited_today + 1 WHERE user_id=?",
                        (ref_id,)
                    )

                    await db.commit()

                    cur = await db.execute("SELECT invited, balance FROM users WHERE user_id=?", (ref_id,))
                    invited, balance = await cur.fetchone()

                    cur = await db.execute("SELECT invited_today FROM invites WHERE user_id=?", (ref_id,))
                    today = (await cur.fetchone())[0]

                    await bot.send_message(
                        ref_id,
                        f"➕ +1 людина\n"
                        f"👥 Запрошено: {invited}\n"
                        f"📉 Залишилось: {max(0, DAILY_NORM - today)}\n"
                        f"💰 Баланс: {balance} грн"
                    )

    # 👋 ВІТАННЯ
    await message.answer(
        f"👋 Вітаю у SlemWorkBot!\n\n"
        f"💼 Тут ти можеш заробляти гроші, запрошуючи друзів.\n\n"
        f"💰 За кожного друга: 80 грн\n"
        f"📊 Денна норма: 10 людей\n\n"
        f"📅 Умови:\n"
        f"• Мінімум 10 робочих днів\n"
        f"• Мінімум 10 000 грн\n\n"
        f"👇 Використовуй меню нижче",
        reply_markup=menu
    )


# 📊 Статистика
@dp.message(lambda msg: msg.text == "📊 Статистика")
async def stats(message: types.Message):
    user_id = message.from_user.id

    async with aiosqlite.connect(DB_NAME) as db:
        cur = await db.execute("SELECT invited, balance, day FROM users WHERE user_id=?", (user_id,))
        invited, balance, day = await cur.fetchone()

        cur = await db.execute("SELECT invited_today FROM invites WHERE user_id=?", (user_id,))
        today = (await cur.fetchone())[0]

    await message.answer(
        f"📊 Статистика:\n\n"
        f"👥 Запрошено: {invited}\n"
        f"📅 Робочих днів: {day}\n"
        f"📉 Залишилось: {max(0, DAILY_NORM - today)}\n"
        f"💰 Баланс: {balance} грн"
    )


# 🔗 Посилання
@dp.message(lambda msg: msg.text == "🔗 Моє посилання")
async def link(message: types.Message):
    await message.answer(
        f"🔗 Твоє реферальне посилання:\n"
        f"https://t.me/SlemWorkBot?start={message.from_user.id}"
    )


# 💸 Вивід
@dp.message(lambda msg: msg.text == "💸 Вивести кошти")
async def withdraw(message: types.Message):
    user_id = message.from_user.id

    async with aiosqlite.connect(DB_NAME) as db:
        cur = await db.execute("SELECT balance, day FROM users WHERE user_id=?", (user_id,))
        balance, day = await cur.fetchone()

    if balance >= MIN_BALANCE and day >= MIN_DAYS:
        await message.answer("✅ Заявка на вивід прийнята!")
    else:
        await message.answer(
            f"❌ Недостатньо умов:\n"
            f"Баланс: {balance}/{MIN_BALANCE}\n"
            f"Днів: {day}/{MIN_DAYS}"
        )


# 🔔 Нагадування
async def reminder():
    async with aiosqlite.connect(DB_NAME) as db:
        cur = await db.execute("SELECT user_id, invited_today FROM invites")
        users = await cur.fetchall()

        for user_id, today in users:
            if today < DAILY_NORM:
                try:
                    await bot.send_message(
                        user_id,
                        f"⚠️ Не виконав норму!\n"
                        f"Залишилось: {DAILY_NORM - today}"
                    )
                except:
                    pass


# 🌙 Скидання
async def reset_day():
    async with aiosqlite.connect(DB_NAME) as db:
        cur = await db.execute("SELECT user_id, invited_today FROM invites")
        users = await cur.fetchall()

        for user_id, today in users:
            if today >= DAILY_NORM:
                await db.execute(
                    "UPDATE users SET day = day + 1 WHERE user_id=?",
                    (user_id,)
                )

            await db.execute(
                "UPDATE invites SET invited_today = 0 WHERE user_id=?",
                (user_id,)
            )

        await db.commit()


# ⏰ Таймери
scheduler = AsyncIOScheduler()
scheduler.add_job(reminder, "cron", hour=20)
scheduler.add_job(reset_day, "cron", hour=0)
scheduler.start()


# ▶️ Запуск
async def main():
    await init_db()
    print("Бот запущений...")
await dp.start_polling(bot)
print("Отримано /start")

if __name__ == "__main__":
    asyncio.run(main())
