import asyncio
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)
import json
import os
import logging
from pyrogram import idle

import aiohttp
from pyrogram.client import Client
from pyrogram import filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
import redis.asyncio as aioredis
from sqlalchemy import select
from os import getenv
from common.db_init import AsyncSessionLocal
from common.db_models import Item

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


BOT_TOKEN = getenv("TG_BOT_TOKEN", "")
API_ID = int(getenv("TG_API_ID", 0))
API_HASH = getenv("TG_API_HASH", "")
REDIS_URL = getenv("REDIS_URL", "")
TG_GROUP_ID = int(getenv("TG_GROUP_ID", ""))
AUTH_STATIC_TOKEN = getenv("AUTH_STATIC_TOKEN", "")
API_BASE_URL = getenv("API_BASE_URL", "")

app = Client("bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

async def handle_request(payload):
    correlation = payload["correlation_id"]
    disk = payload["disk"]
    user = payload["user_login"]
    booking_id = payload["booking_id"]

    kb = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("Подтвердить возврат ✅", callback_data=f"unblock:ok:{correlation}")],
            [InlineKeyboardButton("Отклонить ❌", callback_data=f"unblock:no:{correlation}")]
        ]
    )
    text = f"Запрос на подтверждение возврата диска *{disk}* (бронь #{booking_id}) от `{user}`.\nПодтвердить?"
    await app.send_message(TG_GROUP_ID, text, reply_markup=kb, parse_mode="markdown")

async def redis_listener():
    redis = aioredis.from_url(REDIS_URL, encoding="utf-8", decode_responses=True)
    psub = redis.pubsub()
    await psub.subscribe("bot:requests")
    async for msg in psub.listen():
        if msg is None or msg.get("type") != "message":
            continue
        payload = json.loads(msg["data"])
        asyncio.create_task(handle_request(payload))

@app.on_callback_query()
async def on_cb(c, cb):
    data = cb.data
    if not data:
        return
    try:
        action, action_data = data.split(":", 1)
    except ValueError:
        return
    match action:
        case "unblock":
            try:
                verdict, correlation = action_data.split(":", 1)
            except ValueError:
                return
            result = {
                "correlation_id": correlation,
                "verdict": "accepted" if verdict == "ok" else "rejected",
                "by": cb.from_user.username or str(cb.from_user.id),
                "at": __import__("datetime").datetime.utcnow().isoformat() + "Z"
            }

            redis = aioredis.from_url(REDIS_URL, encoding="utf-8", decode_responses=True)
            await redis.publish("bot:responses", json.dumps(result))
            await redis.close()
            await cb.answer("✅ Принято")
        case "donat":
            try:
                verdict, item_id = action_data.split(":", 1)
            except ValueError:
                return
            async with AsyncSessionLocal() as session:
                async with session.begin():
                    qb = select(Item).where(Item.id == item_id, Item.available == False).with_for_update()
                    resb = await session.execute(qb)
                    db_item = resb.scalars().first()
                    if verdict == "ok":
                        db_item.available = True
                        headers = {
                            "Authorization": f"Bearer {AUTH_STATIC_TOKEN}",
                        }
                        async with aiohttp.ClientSession() as api_session:
                            try:
                                async with api_session.post(API_BASE_URL + f"/api/availability/items/{item_id}", headers=headers) as response:
                                    if response.status == 200:
                                        session.add(db_item)
                                        await cb.answer(f"✅ Принято")
                                    elif response.status == 404:
                                        await cb.answer(f"❌ Диск с id={item_id} не найден в базе")
                                    else:
                                        text = await response.text()
                                        await cb.answer(f"⚠️ Ошибка {response.status}: {text}")
                            except aiohttp.ClientError as e:
                                await cb.answer(f"Ошибка соединения: {e}")
                    else:
                        await session.delete(db_item)
                        await cb.answer(f"✅ Принято")

# Команда /start открывает главное меню с кнопкой Mini App
@app.on_message(filters.command("start") & filters.private)
def start_command(client, message):
    donat_url = ""
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("🎮 Открыть витрину", web_app=WebAppInfo(url=API_BASE_URL)),
        InlineKeyboardButton("Пожертвовать диском", url=donat_url)
    ]])
    message.reply_text("Привет! Нажмите кнопку, чтобы открыть витрину дисков:", reply_markup=keyboard)

async def main():
    await app.start()
    asyncio.create_task(redis_listener())
    await idle()
    await app.stop()

if __name__ == "__main__":
    try:
        loop.run_until_complete(main())
    finally:
        # корректно закрываем loop
        loop.close()
