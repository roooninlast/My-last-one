import os, re
from typing import Optional
from .spec import WorkflowSpec
from .skills import capabilities, tpl_cron_http_to_telegram, tpl_monitor_status_every_5min, tpl_ai_video_outline_to_telegram

USE_LLM = os.getenv("USE_LLM_PLANNER", "false").lower() in ("1","true","yes")

def _looks(s: str, pat: str) -> bool:
    return re.search(pat, s, flags=re.IGNORECASE) is not None

def _parse_time_hhmm(text: str) -> Optional[tuple]:
    m = re.search(r'(\d{1,2})[:٫\.](\d{2})', text)
    if m:
        h, mm = int(m.group(1)), int(m.group(2))
        if 0 <= h < 24 and 0 <= mm < 60:
            return h, mm
    if _looks(text, r'\bكل\s*5\s*د(ق|قائق|قائق|قائق)\b') or "every 5" in text.lower():
        return (0, "*/5")
    return None

def plan_from_text(user_text: str) -> WorkflowSpec:
    caps = capabilities()
    t = user_text.strip()

    # 1) حالات “مراقبة خدمة” / “لو تعطّل نبّهني”
    if _looks(t, r'راقب|monitor|status|تعط'):
        url = "https://httpbin.org/status/200"
        m = re.search(r'(https?://\S+)', t)
        if m: url = m.group(1)
        return tpl_monitor_status_every_5min(url)

    # 2) “أرسل لي سعر/بيانات كل يوم/ساعة…”
    if _looks(t, r'سعر|price|btc|بتكوين|بيتكوين'):
        hhmm = _parse_time_hhmm(t) or (9, 0)
        hour, minute = hhmm
        return tpl_cron_http_to_telegram(
            name="Daily BTC to Telegram",
            url="https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT",
            method="GET",
            set_expr="={{`BTC/USDT: ${Number($json[\"price\"] || 0).toFixed(2)}`}}",
            message="={{$json.msg}}",
            hour=hour if isinstance(hour, int) else 9,
            minute=minute if isinstance(minute, int) else 0
        )

    # 3) “اصنع فيديو AI وانشره” → نولّد مخطط نصي يومي كنسخة أولى
    if _looks(t, r'فيديو|video') and _looks(t, r'ذكاء|اصطناعي|ai'):
        prompt = re.sub(r'[\r\n]+', ' ', t)
        return tpl_ai_video_outline_to_telegram(prompt)

    # 4) طلب عام “أرسل لي ملخص/خبر/..” → قالب HTTP→Set→Telegram
    if _looks(t, r'ارسِل|ابعت|ذكّر|remind|send|notify'):
        url = "https://httpbin.org/json"
        m = re.search(r'(https?://\S+)', t)
        if m: url = m.group(1)
        hhmm = _parse_time_hhmm(t) or (9, 0)
        hour, minute = hhmm
        return tpl_cron_http_to_telegram(
            name="Scheduled Fetch & Notify",
            url=url,
            method="GET",
            set_expr="={{`النتيجة: ${JSON.stringify($json).slice(0,180)}...`}}",
            message="={{$json.msg}}",
            hour=hour if isinstance(hour, int) else 9,
            minute=minute if isinstance(minute, int) else 0
        )

    # 5) افتراضي: ردّ بخطّة معقولة بدل رفض
    return tpl_cron_http_to_telegram(
        name="Daily Digest to Telegram",
        url="https://httpbin.org/json",
        method="GET",
        set_expr="={{`ملخص يومي: ${($json.slideshow && $json.slideshow.title) || 'OK'}`}}",
        message="={{$json.msg}}",
        hour=9, minute=0
    )
