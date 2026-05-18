import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import Message

from config import BOT_TOKEN, ADMIN_TG_ID
from database import create_task, update_task_status, save_result, get_recent_tasks
from agents import orchestrator, strategist, script_writer, smm_agent, video_agent

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

MAX_LENGTH = 4096


async def notify_admin(text: str):
    try:
        await bot.send_message(ADMIN_TG_ID, text[:MAX_LENGTH])
    except Exception:
        pass


@dp.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer(
        "🤖 <b>Solvo AI Office</b>\n\n"
        "Напиши задачу — и AI-агенты создадут контент для Solvo Beauty.\n\n"
        "Примеры:\n"
        "• «Сделай 5 сценариев для Reels про то как мастер теряет клиентов без приложения»\n"
        "• «Контент-план на неделю для мастера маникюра»\n"
        "• «Стратегия продвижения Solvo Beauty в TikTok»\n\n"
        "Команды:\n"
        "/status — последние задачи\n"
        "/help — подробнее о возможностях",
    )


@dp.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(
        "🧠 <b>Как работает Solvo AI Office</b>\n\n"
        "Ты пишешь задачу — запускается команда AI-агентов:\n\n"
        "🧠 <b>Оркестратор</b> — анализирует задачу и строит план\n"
        "📊 <b>Стратегист</b> — определяет когорту аудитории и платформу\n"
        "✍️ <b>Сценарист</b> — пишет сценарии для Reels/TikTok/Shorts\n"
        "📱 <b>SMM Agent</b> — создаёт контент-план и расписание\n"
        "🎬 <b>Video Agent</b> — генерирует видео (требуется Higgsfield API)\n\n"
        "Все агенты работают параллельно. Результат — одно большое сообщение.",
    )


@dp.message(Command("status"))
async def cmd_status(message: Message):
    user_id = message.from_user.id
    tasks = await get_recent_tasks(user_id)
    if not tasks:
        await message.answer("У вас пока нет задач.")
        return
    lines = ["📋 <b>Последние задачи:</b>\n"]
    for t in tasks:
        status_emoji = {"done": "✅", "processing": "⚙️", "error": "❌", "pending": "⏳"}
        emoji = status_emoji.get(t["status"], "⏳")
        created = t["created_at"].strftime("%d.%m %H:%M") if t.get("created_at") else ""
        request = t["original_request"][:80] + ("..." if len(t["original_request"]) > 80 else "")
        lines.append(f"{emoji} <b>#{t['id']}</b> {created} — {request}")
    await message.answer("\n".join(lines))


@dp.message()
async def handle_task(message: Message):
    user_id = message.from_user.id
    request = message.text.strip()
    if not request:
        return

    task_id = await create_task(user_id, request)
    await update_task_status(task_id, "processing")
    status_msg = await message.answer(
        f"⚙️ Офис принял задачу <b>#{task_id}</b>.\nЗапускаю агентов..."
    )

    await notify_admin(
        f"📥 Новая задача #{task_id} от @{message.from_user.username or 'unknown'}: {request[:200]}"
    )

    orchest_task = asyncio.create_task(orchestrator.run(request))
    strat_task = asyncio.create_task(strategist.run(request))
    script_task = asyncio.create_task(script_writer.run(request))
    results = await asyncio.gather(orchest_task, strat_task, script_task, return_exceptions=True)

    orchest_result = results[0] if not isinstance(results[0], Exception) else f"❌ Ошибка: {results[0]}"
    strategy = results[1] if not isinstance(results[1], Exception) else f"❌ Ошибка: {results[1]}"
    scripts = results[2] if not isinstance(results[2], Exception) else f"❌ Ошибка: {results[2]}"

    smm_val = await smm_agent.run(request, scripts=scripts, strategy=strategy)
    video_val = await video_agent.run(scripts)

    await save_result(task_id, "orchestrator", orchest_result)
    await save_result(task_id, "strategist", strategy)
    await save_result(task_id, "script_writer", scripts)
    await save_result(task_id, "smm_agent", smm_val)
    await save_result(task_id, "video_agent", video_val)

    await update_task_status(task_id, "done")
    await status_msg.delete()

    parts = [
        "🧠 <b>ОРКЕСТРАТОР</b>",
        orchest_result,
        "",
        "📊 <b>СТРАТЕГИСТ</b>",
        strategy,
        "",
        "✍️ <b>СЦЕНАРИИ</b>",
        scripts,
        "",
        "📱 <b>SMM АГЕНТ</b>",
        smm_val,
        "",
        "🎬 <b>VIDEO АГЕНТ</b>",
        video_val,
    ]
    full_text = "\n".join(parts)

    if len(full_text) <= MAX_LENGTH:
        await message.answer(full_text)
    else:
        for i in range(0, len(full_text), MAX_LENGTH):
            await message.answer(full_text[i:i + MAX_LENGTH])

    await notify_admin(f"✅ Задача #{task_id} выполнена")
