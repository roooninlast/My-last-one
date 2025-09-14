# app/main.py
import os
import re
import json
import time
import tempfile
from typing import Any, Dict, Optional

import httpx
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse

# مكوّناتنا الداخلية
from .llm import plan_from_text
from .generator import spec_to_n8n
from .validators import static_checks, active_checks

# ========= إعدادات عامة =========
BOT_TOKEN = (
    os.getenv("TG_BOT_TOKEN")
    or os.getenv("TELEGRAM_BOT_TOKEN")
    or os.getenv("TELEGRAM_TOKEN")
)
API_BASE = f"https://api.telegram.org/bot{BOT_TOKEN}" if BOT_TOKEN else None

APP_TZ = os.getenv("TIMEZONE", "Africa/Algiers")

# تعطيل فحوص الشبكة افتراضيًا على الاستضافة المجانية
SKIP_ACTIVE = os.getenv("SKIP_ACTIVE_CHECKS", "true").lower() in ("1", "true", "yes")

# ========= FastAPI =========
app = FastAPI()

# ========= أدوات مساعدة للتيليغرام =========
async def tg_send(chat_id: int | str, text: str, parse_mode: Optional[str] = None) -> None:
    if not API_BASE:
        return
    payload = {"chat_id": chat_id, "text": text}
    if parse_mode:
        payload["parse_mode"] = parse_mode
    async with httpx.AsyncClient(timeout=15) as client:
        try:
            await client.post(f"{API_BASE}/sendMessage", json=payload)
        except Exception:
            pass  # لا نكسر التنفيذ لو فشل الإرسال

async def tg_send_document(chat_id: int | str, filename: str, bytes_data: bytes, caption: Optional[str] = None) -> None:
    if not API_BASE:
        return
    data = {"chat_id": str(chat_id)}
    if caption:
        data["caption"] = caption
    files = {"document": (filename, bytes_data, "application/json")}
    async with httpx.AsyncClient(timeout=30) as client:
        try:
            await client.post(f"{API_BASE}/sendDocument", data=data, files=files)
        except Exception:
            pass

# ========= منطق كشف "هل النص يبدو كطلب أتمتة؟" لكن بدون منع التنفيذ =========
TASK_HINTS = [
    # تكرار/جدولة
    r"كل\s*يوم", r"كليوم", r"يومي(?:ً|ا)?", r"every\s*day", r"\bdaily\b",
    r"كل\s*ساع(?:ة|ه)", r"ساع(?:يًا|يا)?", r"every\s*hour",
    r"\bcron\b", r"\bwebhook\b",
    # أفعال تنفيذ/تنبيه
    r"اصنع|أنشئ|انشئ|اعمل|سو(?:ي)?|generate|create|send|notify|alert|fetch|monitor|راقب|نبهني|ابعث|ارسل",
    # توقيتات شائعة
    r"\bالساعة\s*\d", r"\b(?:0?\d|1\d|2[0-3])[:٫\.]\d{2}\b"
]

def looks_like_task(text: str) -> bool:
    t = text.strip().lower()
    return any(re.search(p, t) for p in TASK_HINTS) or len(t) > 8

# ========= نقاط النهاية =========
@app.get("/health")
async def health() -> Dict[str, Any]:
    return {"ok": True, "ts": int(time.time())}

@app.post("/telegram")
async def telegram_webhook(req: Request) -> Response:
    """
    Webhook تيليغرام: يستقبل أي رسالة نصية من المستخدم،
    يحوّل الوصف إلى خطة، يولّد JSON متوافق مع n8n، ويُرسله كمستند.
    """
    if not BOT_TOKEN:
        return JSONResponse({"ok": False, "error": "Missing BOT_TOKEN"}, status_code=500)

    payload = await req.json()
    message = payload.get("message") or payload.get("edited_message")
    if not message:
        return JSONResponse({"ok": True})

    chat_id = message["chat"]["id"]
    text = (message.get("text") or "").strip()

    # أوامر بسيطة
    if text in ("/start", "start"):
        await tg_send(chat_id,
            "أهلًا بك! أكتب وصف الأتمتة بالعربية وسأبني لك ملف n8n جاهز للاستيراد.\n"
            "مثال:\n"
            "• كل يوم 08:00 ابعثلي سعر البيتكوين\n"
            "• راقب https://httpbin.org/status/200 ونبهني لو تعطّل\n"
            "• كل 5 دقائق افحص API وأرسل تنبيه إلى تيليغرام")
        return JSONResponse({"ok": True})

    if text in ("/help", "help"):
        await tg_send(chat_id,
            "أرسل وصفًا بسيطًا لما تريد أتمتته، وأنا أختار الأدوات تلقائيًا (Cron/HTTP/Telegram).")
        return JSONResponse({"ok": True})

    # تلميح خفيف لو ما ظهر أنه مهمة، لكن **لا نوقف التنفيذ**
    if not looks_like_task(text):
        await tg_send(chat_id, "حاضر! سأحاول بناء أتمتة من وصفك حتى لو كان عام ✨")

    # 1) تخطيط → WorkflowSpec
    try:
        spec = plan_from_text(text)
    except Exception as e:
        await tg_send(chat_id, f"تعذّر إنشاء الخطة: {e}")
        return JSONResponse({"ok": False})

    # 2) فحوصات
    issues = []
    try:
        issues.extend(static_checks(spec))
        if not SKIP_ACTIVE:
            issues.extend(active_checks(spec))
    except Exception as e:
        issues.append(f"تعذّر إجراء الفحوص: {e}")

    if issues:
        pretty = "⚠️ ملاحظات:\n- " + "\n- ".join(issues[:10])
        await tg_send(chat_id, pretty)

    # 3) تحويل إلى n8n JSON
    try:
        n8n_obj = spec_to_n8n(spec)
    except Exception as e:
        await tg_send(chat_id, f"تعذّر توليد n8n JSON: {e}")
        return JSONResponse({"ok": False})

    # 4) إرسال الملف كمستند
    try:
        data = json.dumps(n8n_obj, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        await tg_send_document(chat_id, "workflow.json", data, caption="هذا هو ملف n8n جاهز للاستيراد.")
    except Exception as e:
        await tg_send(chat_id, f"توليد الملف نجح لكن فشل الإرسال: {e}")

    # 5) ملخّص افتراضات مفيدة للمستخدم
    try:
        assumptions = []
        try_urls = [str(s.params.get("url", "")) for s in getattr(spec, "steps", []) if getattr(s, "type", "") == "http"]
        if any("binance.com" in u for u in try_urls):
            assumptions.append("استخدمت Binance لأسعار BTC لتجنّب مشاكل DNS.")
        if getattr(spec, "trigger", None) and spec.trigger.type == "cron":
            h = spec.trigger.config.get("hour")
            m = spec.trigger.config.get("minute")
            assumptions.append(f"موعد التنفيذ: {h}:{m} (افتراضي/مستخلص).")
        if assumptions:
            await tg_send(chat_id, "ℹ️ افتراضات:\n- " + "\n- ".join(assumptions)[:3500])
    except Exception:
        pass

    return JSONResponse({"ok": True})


# ========= تشغيل محلي (اختياري) =========
# uvicorn app.main:app --host 0.0.0.0 --port 8080
