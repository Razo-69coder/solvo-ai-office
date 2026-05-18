from pathlib import Path
from anthropic import AsyncAnthropic

from config import ANTHROPIC_API_KEY

PROMPT = (Path(__file__).parent.parent / "prompts" / "smm_agent.txt").read_text(encoding="utf-8")

client = AsyncAnthropic(api_key=ANTHROPIC_API_KEY)


async def run(request: str, scripts: str = "", strategy: str = "") -> str:
    if not ANTHROPIC_API_KEY:
        return "⚠️ SMM Agent: Claude API ключ не настроен"
    context = f"Задача: {request}\n\nСтратегия:\n{strategy}\n\nСценарии:\n{scripts}" if scripts or strategy else request
    resp = await client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=2000,
        system=PROMPT,
        messages=[{"role": "user", "content": context}],
    )
    return resp.content[0].text
