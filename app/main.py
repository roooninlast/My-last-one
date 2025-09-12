import os, json, re, requests
from fastapi import FastAPI, Request
from pydantic import ValidationError
from .spec import WorkflowSpec
from .llm import plan_from_text
from .generator import spec_to_n8n
from .validators import static_checks, active_checks

TG_BOT_TOKEN = os.getenv("TG_BOT_TOKEN")
TIMEZONE = os.getenv("TIMEZONE","Africa/Algiers")

app = FastAPI(title="Telegram → n8n JSON Bot")

def tg_send(chat_id, text):
    if not TG_BOT_TOKEN:
        return
    requests.post(f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendMessage",
                  json={"chat_id": chat_id, "text": text})

def tg_send_doc(chat_id, filename, content_bytes, caption=None):
    if not TG_BOT_TOKEN:
        return
    files = {"document": (filename, content_bytes, "application/json")}
    data = {"chat_id": chat_id}
    if caption:
        data["caption"] = caption
    requests.post(f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendDocument",
                  data=data, files=files)

@app.get("/health")
def health():
    return {"ok": True}

# ---------------------------
# نكشف النية (تحية/عادي/أتمتة)
# ---------------------------
GREETINGS = {
    "مرحبا", "السلام", "سلام", "اهلا", "أهلا", "هاي", "هلا", "صباح الخير",
    "مساء الخير", "hi", "hello", "hey", "yo"
}
TASK_HINTS = [
    # كلمات تدل على مهمة/أتمتة بالعربية
    r"\bكل يوم\b", r"\bكل اسبوع\b", r"\bكل أسبوع\b", r"\bكل ساعة\b",
    r"\bالساعة\s*\d", r"\bجدول\b", r"\bجدولة\b", r"\bأرسل\b", r"\bارسل\b",
    r"\bابعت\b", r"\bنبهني\b", r"\bانبهني\b", r"\bجِب\b|\bجيب\b", r"\bسجّل\b|\bسجل\b",
    r"\bwebhook\b", r"\bcron\b",
    # بالإنجليزية
    r"\bevery day\b", r"\bevery\s+\w+\b", r"\bat\s*\d", r"\bsend\b", r"\bfetch\b",
    r"\bnotify\b", r"\balert\b", r"\bcron\b", r"\bwebhook\b"
]

def is_greeting(text: str) -> bool:
    t = text.strip().lower()
    return t in {g.lower() for g in GREETINGS}

def looks_like_task(text: str) -> bool:
    t = text.strip().lower()
    return any(re.search(p, t) for p in TASK_HINTS)

HELP_MSG = (
    "أهلًا! ✨\n"
    "أنا أصنع لك ملف n8n جاهز للاستيراد.\n\n"
    "اكتب وصف الأتمتة بصيغة واضحة، أمثلة:\n"
    "• كل يوم 09:00 جيب سعر EUR→DZD وإذا تغيّر >1% ابعثه لي على تيليغرام.\n"
    "• أنشئ Webhook يستقبل email و pdf_url، نزّل الـ PDF وارفعه إلى Google Drive ثم أرسل الرابط.\n"
    "• راقب موقع example.com/status كل ساعة وإذا status != ok نبهني.\n\n"
    "للشرح السريع اكتب: /help"
)

@app.post("/telegram")
async def telegram_webhook(update: dict):
    msg = (update.get("message") or update.get("edited_message") or {})
    chat_id = (msg.get("chat") or {}).get("id")
    text = msg.get("text") or ""
    if not chat_id:
        return {"ok": True}

    t = text.strip()

    # أوامر مباشرة
    if t.startswith("/start") or t.startswith("/help"):
        tg_send(chat_id, HELP_MSG)
        return {"ok": True}

    # تحية؟
    if is_greeting(t):
        tg_send(chat_id, "أهلًا! 🙌 أرسل وصف الأتمتة التي تريدها وسأرجع لك ملف n8n جاهز.\n\n" + HELP_MSG)
        return {"ok": True}

    # ليس وصف أتمتة واضح؟
    if not looks_like_task(t):
        tg_send(chat_id, "يبدو أنها رسالة عامة 🙂\nأرسل وصف الأتمتة مثل الأمثلة التالية:\n"
                         "• كل يوم 08:00 ابعثلي سعر البيتكوين\n"
                         "• Webhook يستقبل email و pdf_url ويحمّل الملف ثم يرسل الرابط\n"
                         "أو اكتب /help للمزيد.")
        return {"ok": True}

    # هنا نولّد الأتمتة
    try:
        spec = plan_from_text(t)
        spec.timezone = TIMEZONE

        issues = static_checks(spec) + active_checks(spec)
        wf = spec_to_n8n(spec)
        wf_json = json.dumps(wf, ensure_ascii=False, indent=2)

        report = "✅ الفحوصات الأساسية مرت بنجاح." if not issues else "⚠️ ملاحظات:\n- " + "\n- ".join(issues)
        tg_send(chat_id, report[:3900])

        tg_send_doc(chat_id, "workflow.json", wf_json.encode("utf-8"),
                    caption="هذا هو ملف n8n جاهز للاستيراد.")
    except ValidationError as ve:
        tg_send(chat_id, f"❌ خطأ في بناء المخطط:\n{ve}")
    except Exception as e:
        tg_send(chat_id, f"❌ خطأ غير متوقع: {e}")

    return {"ok": True}
