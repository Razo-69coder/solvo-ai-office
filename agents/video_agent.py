import asyncio
import re

import httpx

from config import HIGGSFIELD_API_ID, HIGGSFIELD_API_SECRET

AUTH_URL = "https://cloud.higgsfield.ai/api/auth/token"
DRAFT_URL = "https://cloud.higgsfield.ai/api/v1/video/generate"
STATUS_URL = "https://cloud.higgsfield.ai/api/v1/video"
VIRALITY_URL = "https://cloud.higgsfield.ai/api/v1/virality-predictor"
KREDITS_LIMIT = 1000
KREDITS_DRAFT = 7
KREDITS_FINAL = 22


async def _get_token(client: httpx.AsyncClient) -> str:
    resp = await client.post(
        AUTH_URL,
        json={"client_id": HIGGSFIELD_API_ID, "client_secret": HIGGSFIELD_API_SECRET},
    )
    resp.raise_for_status()
    return resp.json()["access_token"]


async def _generate_video(client: httpx.AsyncClient, token: str, prompt: str, model: str, duration: int = 8) -> dict:
    resp = await client.post(
        DRAFT_URL,
        headers={"Authorization": f"Bearer {token}"},
        json={"model": model, "prompt": prompt, "aspect_ratio": "9:16", "duration": duration},
    )
    resp.raise_for_status()
    return resp.json()


async def _poll_video(client: httpx.AsyncClient, token: str, video_id: str, timeout: int = 120) -> dict:
    for _ in range(timeout // 5):
        await asyncio.sleep(5)
        resp = await client.get(
            f"{STATUS_URL}/{video_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        if resp.status_code != 200:
            continue
        data = resp.json()
        if data.get("status") == "completed":
            return data
        if data.get("status") in ("failed", "error"):
            raise RuntimeError(f"Video generation failed: {data}")
    raise TimeoutError(f"Video {video_id} not ready after {timeout}s")


async def _virality_check(client: httpx.AsyncClient, token: str, video_url: str) -> dict:
    resp = await client.post(
        VIRALITY_URL,
        headers={"Authorization": f"Bearer {token}"},
        json={"video_url": video_url},
    )
    resp.raise_for_status()
    return resp.json()


async def _rewrite_hook(client: httpx.AsyncClient, token: str, script_text: str) -> str:
    import anthropic
    from config import ANTHROPIC_API_KEY

    claude = anthropic.AsyncAnthropic(api_key=ANTHROPIC_API_KEY)
    msg = await claude.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=300,
        messages=[{"role": "user", "content": f"Перепиши хук (первые 3 секунды) для этого сценария, чтобы он был вирусным. Только хук, 1 предложение.\n\nСценарий: {script_text[:1000]}"}],
    )
    return msg.content[0].text if msg.content else script_text[:200]


def _extract_visual_prompt(script_text: str) -> str:
    lines = script_text.split("\n")
    refs = [l for l in lines if "вижуал" in l.lower() or "референс" in l.lower() or "visual" in l.lower() or "prompt" in l.lower() or l.startswith("🎬")]
    if refs:
        return " ".join(refs)[:500]
    return "Solvo Beauty app — a master using CRM on smartphone, professional nail studio, before/after transformation"


def _extract_title(script_text: str) -> str:
    for line in script_text.split("\n"):
        line = line.strip()
        if line.lower().startswith("название") or line.lower().startswith("сценарий") or line.lower().startswith("видео"):
            clean = re.sub(r"^[^:]*:", "", line).strip().strip('"').strip('«»')
            if clean:
                return clean[:60]
    return "Сценарий"


def _format_video_block(idx: int, title: str, viral: dict, draft_url: str, final_url: str) -> str:
    score = viral.get("viral_score", 0)
    hook = viral.get("hook_score", 0)
    hold = viral.get("hold_rate", 0)
    hold_pct = int(hold * 100) if hold else 0
    passed = score >= 65

    lines = [
        f"ВИДЕО {idx} — \"{title}\"",
        f"📊 Viral Score: {score} | Hook: {hook} | Hold: {hold_pct}%",
    ]
    if passed:
        lines.append("✅ Прошло проверку")
    else:
        lines.append("⚠️ Низкий score — переписан хук")
    if draft_url:
        lines.append(f"🎥 Черновик: {draft_url}")
    if final_url:
        lines.append(f"🏆 Финал Veo 3: {final_url}")
    return "\n".join(lines)


async def run(scripts: str) -> str:
    if not HIGGSFIELD_API_ID or not HIGGSFIELD_API_SECRET:
        return ("🎬 <b>VIDEO AGENT</b>\n\n"
                "Готов сгенерировать видео после настройки Higgsfield API.\n"
                "Добавьте HIGGSFIELD_API_ID и HIGGSFIELD_API_SECRET в .env")

    script_blocks = [s.strip() for s in scripts.split("---") if s.strip()]
    if not script_blocks:
        script_blocks = [scripts]

    total_kredits = 0
    video_blocks = []

    async with httpx.AsyncClient(timeout=60) as client:
        try:
            token = await _get_token(client)
        except Exception as e:
            return f"❌ Higgsfield auth failed: {e}"

        for i, block in enumerate(script_blocks, start=1):
            title = _extract_title(block)
            visual_prompt = _extract_visual_prompt(block)

            draft_url = ""
            final_url = ""
            viral_data = {}

            for attempt in range(2):
                try:
                    prompt_to_use = visual_prompt
                    if attempt == 1:
                        new_hook = await _rewrite_hook(client, token, block)
                        prompt_to_use = f"{new_hook}. {visual_prompt[:400]}"

                    # Stage 1: Kling draft
                    draft_resp = await _generate_video(client, token, prompt_to_use, "kling-3.0", 8)
                    draft_id = draft_resp.get("id")
                    if not draft_id:
                        video_blocks.append(f"❌ {title}: не получен ID черновика")
                        total_kredits += KREDITS_DRAFT
                        continue

                    draft_data = await _poll_video(client, token, draft_id)
                    total_kredits += KREDITS_DRAFT
                    draft_url = draft_data.get("video_url") or draft_data.get("output", {}).get("video_url", "")

                    if not draft_url:
                        video_blocks.append(f"❌ {title}: черновик не получен")
                        continue

                    # Stage 2: Virality Predictor
                    viral_data = await _virality_check(client, token, draft_url)
                    viral_score = viral_data.get("viral_score", 0)

                    if viral_score >= 65 or attempt == 1:
                        break

                except Exception as e:
                    video_blocks.append(f"❌ {title}: {e}")
                    break

            # Stage 3: Veo 3 Fast (if viral score passed)
            if viral_data.get("viral_score", 0) >= 65:
                try:
                    final_resp = await _generate_video(client, token, visual_prompt, "veo-3-fast", 8)
                    final_id = final_resp.get("id")
                    if final_id:
                        final_data = await _poll_video(client, token, final_id)
                        total_kredits += KREDITS_FINAL
                        final_url = final_data.get("video_url") or final_data.get("output", {}).get("video_url", "")
                except Exception as e:
                    pass

            if viral_data:
                video_blocks.append(_format_video_block(i, title, viral_data, draft_url, final_url))
            else:
                video_blocks.append(f"ВИДЕО {i} — \"{title}\"\n❌ Не удалось сгенерировать")

    remaining = max(0, KREDITS_LIMIT - total_kredits)
    header = "🎬 <b>VIDEO AGENT — результаты</b>\n\n"
    footer = f"\n\n💳 Потрачено кредитов: ~{total_kredits} из {KREDITS_LIMIT}"

    return header + "\n\n".join(video_blocks) + footer
