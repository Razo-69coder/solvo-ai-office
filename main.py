import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from aiogram.types import Update

from config import BOT_TOKEN, WEBHOOK_URL
from database import init_db
from bot import bot, dp

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def _db_keepalive():
    from database import get_pool
    while True:
        await asyncio.sleep(240)
        try:
            pool = await get_pool()
            async with pool.acquire() as conn:
                await conn.execute("SELECT 1")
            logger.info("[KEEPALIVE] DB ping ok")
        except Exception as e:
            logger.warning(f"[KEEPALIVE] DB ping failed: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        await asyncio.wait_for(init_db(), timeout=120)
    except asyncio.TimeoutError:
        logger.warning("init_db timed out after 120s")
    except Exception as e:
        logger.warning(f"init_db failed: {e}")
    keepalive = asyncio.create_task(_db_keepalive())

    if WEBHOOK_URL:
        webhook_url = f"{WEBHOOK_URL}/webhook"
        await bot.set_webhook(url=webhook_url)
        logger.info(f"Webhook set to {webhook_url}")
    else:
        logger.warning("WEBHOOK_URL not set, bot will not receive updates")

    yield
    keepalive.cancel()
    await bot.session.close()


app = FastAPI(title="Solvo AI Office", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/webhook")
async def telegram_webhook(request: Request):
    pass
    data = await request.json()
    update = Update.model_validate(data)
    asyncio.create_task(dp.feed_update(bot, update))
    return {"ok": True}


@app.get("/health")
async def health():
    return {"status": "ok"}
