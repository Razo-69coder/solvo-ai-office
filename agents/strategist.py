from pathlib import Path
from anthropic import AsyncAnthropic

from config import ANTHROPIC_API_KEY

PROMPT = (Path(__file__).parent.parent / "prompts" / "strategist.txt").read_text(encoding="utf-8")

client = AsyncAnthropic(api_key=ANTHROPIC_API_KEY)


async def run(request: str) -> str:
    if not ANTHROPIC_API_KEY:
        return "⚠️ Strategist: Claude API ключ не настроен"
    resp = await client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1000,
        system=PROMPT,
        messages=[{"role": "user", "content": request}],
    )
    return resp.content[0].text
