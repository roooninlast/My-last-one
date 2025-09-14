from __future__ import annotations
import os, httpx, json

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")

SYSTEM = (
"أنت مخطط أتمتة عام. حوّل وصف المستخدم إلى خطة JSON مُقيّدة."
" لا تعُد أي شرح. أعد JSON فقط بالمخطط وفق هذا الـ schema:\n"
"{"
'  "plan": {'
'    "name": "string",'
'    "timezone": "string (IANA, optional)",'
'    "steps": ['
'      {"id":"slug","type":"cron|webhook|http|set|if|wait|telegram","name":"opt","params":{...}}'
'    ],'
'    "edges": [ {"from":"step_id","to":"step_id"} ]'
"  }"
"}\n"
"قواعد مهمة:\n"
"- ids فريدة قصيرة (english slug).\n"
"- لو الوصف لا يحتوي جدولة، لا تنشئ cron.\n"
"- لو الوصف ذكر تيليغرام للإشعار أضف step type=telegram مع params {chatId:'{{$env.TELEGRAM_CHAT_ID}}', text:'...'}.\n"
"- http params مثال: {method:'GET|POST', url:'https://...', headers:{}, query:{}, body:{}, json:{}}.\n"
"- set params: {keepOnlySet:true, values:{string:[{name:'key', value:'={{expr}}'}]}}.\n"
"- if params: {expression:'={{ $json.ok == true }}', then:'id', else:'id'} (سنتحوّلها لاحقاً إلى عقد n8n).\n"
"- wait params: {seconds: 10}.\n"
"- لا تستخدم مفاتيح حقيقية؛ استخدم متغيرات بيئة مثل {{$env.MY_KEY}} إذا لزم.\n"
)

def call_openrouter(prompt: str) -> str:
    if not OPENROUTER_API_KEY:
        raise RuntimeError("OPENROUTER_API_KEY is missing")
    model = "openrouter/auto"  # يختار موديل مناسب
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.2,
    }
    with httpx.Client(timeout=60) as client:
        r = client.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, data=json.dumps(payload))
        r.raise_for_status()
        data = r.json()
        return data["choices"][0]["message"]["content"]
