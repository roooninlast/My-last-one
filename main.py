import os, json, requests
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
    requests.post(f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendMessage", json={"chat_id": chat_id, "text": text})

@app.get("/health")
def health():
    return {"ok": True}

@app.post("/telegram")
async def telegram_webhook(update: dict):
    msg = (update.get("message") or update.get("edited_message") or {})
    chat_id = (msg.get("chat") or {}).get("id")
    text = msg.get("text")
    if not chat_id or not text:
        return {"ok": True}

    try:
        spec = plan_from_text(text)
        # فرض المنطقة الزمنية
        spec.timezone = TIMEZONE

        issues = static_checks(spec) + active_checks(spec)
        wf = spec_to_n8n(spec)
        wf_json = json.dumps(wf, ensure_ascii=False, indent=2)

        report = "✅ الفحوصات الأساسية مرت بنجاح." if not issues else "⚠️ ملاحظات:\n- " + "\n- ".join(issues)
        # أرسل التقرير أولاً
        tg_send(chat_id, report[:3900])

        # أرسل JSON كملف (إن أمكن)، وإلا كنص
        files = {"document": ("workflow.json", wf_json.encode("utf-8"), "application/json")}
        requests.post(f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendDocument",
                      data={"chat_id": chat_id, "caption": "هذا هو ملف n8n جاهز للاستيراد."},
                      files=files)

    except ValidationError as ve:
        tg_send(chat_id, f"❌ خطأ في بناء المخطط:\n{ve}")
    except Exception as e:
        tg_send(chat_id, f"❌ خطأ غير متوقع: {e}")

    return {"ok": True}
