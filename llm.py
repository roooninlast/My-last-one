import os, json, requests
from .spec import WorkflowSpec, Trigger, Step, Edge

DEMO_MODE = os.getenv("DEMO_MODE","true").lower() == "true"
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL","anthropic/claude-3.5-sonnet")

SCHEMA_HINT = """
أنت مولّد مخططات لأتمتة n8n. أعد ONLY JSON يطابق هذا المخطط بدون أي نص إضافي:
{
  "name": "string",
  "timezone": "Africa/Algiers",
  "trigger": {"type":"cron|webhook","config":{}},
  "steps": [
    {"id":"string","type":"http|if|set|telegram","params":{}}
  ],
  "edges": [{"from":"string","to":"string"}],
  "placeholders": ["TELEGRAM_BOT_TOKEN","TELEGRAM_CHAT_ID"]
}
القيود:
- لا تُدرج أسرارًا حقيقية؛ فقط أسماء مكانات في placeholders.
- استخدم الأنواع: cron/webhook, httpRequest(set type=http), set, if, telegram.
- يجب أن تكون كل المعرفات فريدة، وكل edges صحيحة.
- ضع timezone = Africa/Algiers.
"""

def _demo_plan(user_text: str) -> WorkflowSpec:
    text = user_text.strip().lower()
    if "btc" in text or "بيتكوين" in text:
        trigger = Trigger(type="cron", config={"cronExpression": "0 9 * * *"})
        steps = [
            Step(id="get_btc", type="http", params={"url": "https://api.coindesk.com/v1/bpi/currentprice/BTC.json"}),
            Step(id="fmt", type="set", params={"values":{"string":[{"name":"msg","value":"={{`سعر BTC الآن بالدولار`}}"}]}}),
            Step(id="send", type="telegram", params={"message":"={{$json.msg}}"})
        ]
        edges = [Edge.model_validate({"from":"get_btc","to":"fmt"}), Edge.model_validate({"from":"fmt","to":"send"})]
        return WorkflowSpec(name="Daily BTC to Telegram", trigger=trigger, steps=steps, edges=edges, placeholders=["TELEGRAM_BOT_TOKEN","TELEGRAM_CHAT_ID"])
    # افتراضي
    trigger = Trigger(type="webhook", config={"path":"auto/demo","method":"POST"})
    steps = [
        Step(id="fmt", type="set", params={"values":{"string":[{"name":"msg","value":"={{$json.text || 'Hi from bot'}}"}]}}),
        Step(id="send", type="telegram", params={"message":"={{$json.msg}}"})
    ]
    edges = [Edge.model_validate({"from":"fmt","to":"send"})]
    return WorkflowSpec(name="Webhook Echo to Telegram", trigger=trigger, steps=steps, edges=edges, placeholders=["TELEGRAM_BOT_TOKEN","TELEGRAM_CHAT_ID"])

def _call_openrouter(user_text: str) -> dict:
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    messages = [
        {"role":"system","content": SCHEMA_HINT},
        {"role":"user","content": f"وصف المهمة:\n{user_text}\n\nتذكر: أعد JSON فقط."}
    ]
    body = {
        "model": OPENROUTER_MODEL,
        "messages": messages,
        "temperature": 0.2
    }
    r = requests.post(url, headers=headers, data=json.dumps(body), timeout=30)
    r.raise_for_status()
    out = r.json()
    content = out["choices"][0]["message"]["content"]
    # حاول استخراج JSON فقط
    start = content.find("{")
    end = content.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("لم يتم العثور على JSON صالح في استجابة النموذج.")
    return json.loads(content[start:end+1])

def plan_from_text(user_text: str) -> WorkflowSpec:
    if DEMO_MODE or not OPENROUTER_API_KEY:
        return _demo_plan(user_text)
    raw = _call_openrouter(user_text)
    # تطبيع وتحويل إلى WorkflowSpec
    # تأكد من وجود الحقول الأساسية
    raw.setdefault("timezone","Africa/Algiers")
    if "trigger" not in raw or "steps" not in raw or "edges" not in raw:
        raise ValueError("استجابة LLM تفتقد حقولًا أساسية.")
    return WorkflowSpec.model_validate(raw)
