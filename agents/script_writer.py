from pathlib import Path
from anthropic import AsyncAnthropic

from config import ANTHROPIC_API_KEY

PROMPT = (Path(__file__).parent.parent / "prompts" / "script_writer.txt").read_text(encoding="utf-8")

client = AsyncAnthropic(api_key=ANTHROPIC_API_KEY)


async def run(request: str) -> str:
    if not ANTHROPIC_API_KEY:
        return "⚠️ Script Writer: Claude API ключ не настроен"
    resp = await client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=2000,
        system=PROMPT,
        messages=[{"role": "user", "content": request}],
    )
    return resp.content[0].text
