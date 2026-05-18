import asyncio
import httpx

from config import HIGGSFIELD_API_KEY


async def run(scripts: str) -> str:
    if not HIGGSFIELD_API_KEY:
        return ("🎬 Video Agent: готов сгенерировать видео после настройки Higgsfield API.\n"
                "Для работы требуется Higgsfield API Key (получить на higgsfield.ai/settings после покупки Plus).")
    return await _generate_video(scripts)


async def _generate_video(scripts: str) -> str:
    headers = {"Authorization": f"Bearer {HIGGSFIELD_API_KEY}", "Content-Type": "application/json"}
    prompt = _extract_visual_prompt(scripts)
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(
            "https://api.higgsfield.ai/v1/generation/text-to-video",
            headers=headers,
            json={"prompt": prompt, "model": "veo-3-fast", "duration": 8},
        )
        if resp.status_code != 200:
            return f"❌ Higgsfield API error: {resp.status_code} {resp.text}"
        data = resp.json()
        gen_id = data.get("id")
        if not gen_id:
            return "❌ Higgsfield: не получен ID генерации"

        for _ in range(12):
            await asyncio.sleep(5)
            status_resp = await client.get(
                f"https://api.higgsfield.ai/v1/generation/{gen_id}",
                headers=headers,
            )
            if status_resp.status_code != 200:
                continue
            status_data = status_resp.json()
            if status_data.get("status") == "completed":
                video_url = status_data.get("video_url") or status_data.get("output", {}).get("video_url")
                return f"🎬 Видео готово: {video_url}"
            if status_data.get("status") in ("failed", "error"):
                return "❌ Higgsfield: ошибка генерации видео"

        return f"⏳ Видео ещё генерируется. Проверьте позже. ID: {gen_id}"


def _extract_visual_prompt(scripts: str) -> str:
    lines = scripts.split("\n")
    refs = [l for l in lines if "референс" in l.lower() or "visual" in l.lower() or l.startswith("🎬")]
    if refs:
        return " ".join(refs)[:500]
    return "Solvo Beauty app — a master using CRM on smartphone, professional nail studio, before/after transformation"
