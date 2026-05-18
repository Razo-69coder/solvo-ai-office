import anthropic

from config import ANTHROPIC_API_KEY


async def run(request: str, feedback: str | None = None) -> str:
    client = anthropic.AsyncAnthropic(api_key=ANTHROPIC_API_KEY)
    with open("prompts/visual_strategist.txt", encoding="utf-8") as f:
        system_prompt = f.read()

    user_msg = f"Задача: {request}\n\nСоставь дизайн-бриф на 10 видео."
    if feedback:
        user_msg = (
            f"Исходная задача: {request}\n\n"
            f"Пользователь внёс правки: {feedback}\n\n"
            "Обнови дизайн-бриф с учётом правок. Составь 10 видео."
        )

    msg = await client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=2000,
        system=system_prompt,
        messages=[{"role": "user", "content": user_msg}],
    )
    text = msg.content[0].text if msg.content else ""

    return (
        "🎨 <b>VISUAL STRATEGIST — дизайн на утверждение</b>\n\n"
        f"{text}\n\n"
        "✅ <b>Утвердить</b> → напиши <b>«Го»</b>\n"
        "✏️ <b>Изменить</b> → напиши что поменять"
    )
