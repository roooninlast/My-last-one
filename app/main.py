from __future__ import annotations
import os, json
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, PlainTextResponse
from pydantic import ValidationError

from .llm import call_openrouter
from .validators import LLMEnvelope, coerce_json
from .spec import Plan
from .generator import plan_to_n8n
from .telegram import send_text, send_document

app = FastAPI()

@app.get("/health")
def health():
    return {"ok": True}

@app.get("/")
def root():
    return PlainTextResponse("n8n planner bot is running")

# ---------- Telegram Webhook ----------
TG = os.getenv("TG_BOT_TOKEN","")

@app.post("/telegram")
async def telegram_webhook(req: Request):
    data = await req.json()
    try:
        msg = (data.get("message") or data.get("edited_message") or {}).get("text","").strip()
        chat_id = (data.get("message") or data.get("edited_message") or {}).get("chat",{}).get("id")

        if not msg:
            return JSONResponse({"ok": True})

        if msg.lower() in ["help","/help","/start","start","مساعدة"]:
            help_text = (
                "أرسل وصف الأتمتة بالعربية (أو الإنجليزية) وسأحوّله لملف n8n.\n"
                "مثال: كل يوم 08:00 اجلب سعر BTC ثم أرسل إشعار تيليغرام.\n"
                "سأعيد لك ملف workflow.json جاهز للاستيراد."
            )
            send_text(help_text, chat_id)
            return {"ok": True}

        # 1) أطلب من الـ LLM إنشاء خطة مُقيّدة
        prompt = f"حوّل هذا الوصف إلى خطة أتمتة عامة: {msg}"
        llm_raw = call_openrouter(prompt)

        # 2) تحقّق/استخراج JSON
        payload = coerce_json(llm_raw)

        # 3) تحقّق بالـ Pydantic
        env = LLMEnvelope(**payload)
        plan = Plan(**env.plan)

        # 4) حولها إلى n8n workflow
        wf = plan_to_n8n(plan)
        wf_bytes = json.dumps(wf.model_dump(), ensure_ascii=False, separators=(",",":")).encode("utf-8")

        # 5) أرسل الملف
        send_document(wf_bytes, "workflow.json", "هذا هو ملف n8n جاهز للاستيراد.", chat_id)

        # ملاحظات قصيرة (افتراضات)
        assumptions = []
        # مثال صغير: إن لم يجد plan.timezone نضع UTC
        if not plan.timezone:
            assumptions.append("- تم افتراض المنطقة الزمنية: UTC.")
        if assumptions:
            send_text("افتراضات:\n"+"\n".join(assumptions), chat_id)

        return {"ok": True}

    except ValidationError as ve:
        send_text(f"validation error: {ve}", chat_id)
        return {"ok": True}
    except Exception as e:
        # فشل عام → أعطِ ملف بديل بسيط كي لا ترجع صفر
        fallback = {
            "name":"Simple Echo",
            "nodes":[
                {
                    "id":"webhook1","name":"Webhook","type":"n8n-nodes-base.webhook","typeVersion":1,
                    "position":[300,400],
                    "parameters":{"path":"hook","httpMethod":"POST","responseMode":"onReceived","responseData":"ok"}
                }
            ],
            "connections":{},
            "settings":{"timezone": os.getenv("TIMEZONE","UTC")}
        }
        wf_bytes = json.dumps(fallback, ensure_ascii=False).encode("utf-8")
        if TG:
            send_document(wf_bytes, "workflow.json", "تعذر إنشاء الخطة الذكية؛ هذا ملف بديل (Webhook).")
            send_text(f"الخطأ: {e!s}")
        return {"ok": True}
