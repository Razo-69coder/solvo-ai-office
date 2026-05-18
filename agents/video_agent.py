import anthropic
from config import ANTHROPIC_API_KEY

client = anthropic.AsyncAnthropic(api_key=ANTHROPIC_API_KEY)

PROMPT_TEMPLATE = (
    "You are a video production expert at an ad agency. "
    "Based on the brief below, create a single ready-to-use prompt "
    "for Higgsfield Supercomputer video generation.\n\n"
    "Brief: {brief}\n\n"
    "Your prompt MUST include ALL of the following sections:\n\n"
    "STYLE:\n"
    "- App Cinematic Showcase\n"
    "- Banco Plata style (rich colors, dramatic lighting, smooth motion)\n\n"
    "COLOR PALETTE:\n"
    "- Primary: pink #FF2D78\n"
    "- Secondary: purple #9B30FF\n"
    "- Background: dark (#0A0A0A)\n\n"
    "VIDEOS (5 total, 9:16 vertical, 14-17 seconds each):\n"
    "Video 1: Device mockup animation — 3D phone rotating slowly, app screen visible\n"
    "Video 2: Chromatic burst — background color explosion from phone screen\n"
    "Video 3: Macro screen drift — camera pushes into phone screen and pans across UI\n"
    "Video 4: Typography reveal with Russian voiceover — text appears with dynamic animation\n"
    "Video 5: UI explosion — cards and interface elements fly out of phone\n\n"
    "For Video 4 (voiceover), insert these exact texts from the brief:\n"
    "{voiceover_texts}\n\n"
    "TECHNICAL:\n"
    "- Format: 9:16 vertical, 14-17 seconds per video\n"
    "- Models: Kling 3.0 for drafts, Veo 3 Fast for finals\n"
    "- Motion intensity: medium-high\n\n"
    "At the very end add:\n"
    "\"Upload all 9 mockup images from C:\\Users\\Arso\\Downloads\\mockups_png\\\"\n\n"
    "Return ONLY the final English prompt text, no explanations, no markdown."
)


def _extract_voiceover_texts(brief: str) -> str:
    lines = [l for l in brief.split("\n") if l.strip()]
    text_lines = [l for l in lines if any(k in l.lower() for k in ("текст", "voice", "голос", "озвучк", "слоган", "caption", "copy", "text"))]
    if text_lines:
        return "\n".join(text_lines)
    return "—"


async def run(scripts: str) -> str:
    prompt = PROMPT_TEMPLATE.format(
        brief=scripts[:3000],
        voiceover_texts=_extract_voiceover_texts(scripts),
    )
    try:
        msg = await client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}],
        )
        result = msg.content[0].text if msg.content else ""
        return result if result else "⚠️ Не удалось сгенерировать промпт."
    except Exception as e:
        return f"❌ Ошибка генерации промпта: {e}"
