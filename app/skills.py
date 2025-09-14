import os
from typing import Dict, Any, List
from .spec import WorkflowSpec, Step, Edge, Trigger

def has(var: str) -> bool:
    v = os.getenv(var, "")
    return bool(v and v.strip())

def capabilities() -> Dict[str, bool]:
    return {
        "telegram": has("TG_BOT_TOKEN") or has("TELEGRAM_BOT_TOKEN") or has("TELEGRAM_CHAT_ID"),
        "openrouter": has("OPENROUTER_API_KEY") or has("OPENROUTER_TOKEN"),
        # أضف مزودين آخرين هنا حسب الحاجة (replicate, stability…)
    }

# ===== TEMPLATES شائعة =====

def tpl_cron_http_to_telegram(name: str,
                              url: str,
                              method: str = "GET",
                              set_expr: str = "={{`Result: ${$json[\"price\"] ?? $json[\"result\"] ?? \"OK\"}`}}",
                              message: str = "={{$json.msg}}",
                              hour: int = 9,
                              minute: int = 0,
                              chat_id_expr: str = "={{$env.TELEGRAM_CHAT_ID}}") -> WorkflowSpec:
    spec = WorkflowSpec(
        name=name,
        timezone=os.getenv("TIMEZONE", "Africa/Algiers"),
        trigger=Trigger(type="cron", config={"hour": hour, "minute": minute}),
        steps=[],
        edges=[]
    )
    spec.steps.append(Step(id="http", type="http", params={"url": url, "method": method}))
    spec.steps.append(Step(id="set", type="set", params={
        "values": {"string": [{"name": "msg", "value": set_expr}]},
        "keepOnlySet": True
    }))
    spec.steps.append(Step(id="tg", type="telegram", params={
        "chatId": chat_id_expr,
        "message": message
    }))
    spec.edges += [
        Edge(from_="http", to="set"),
        Edge(from_="set", to="tg"),
    ]
    return spec

def tpl_monitor_status_every_5min(url: str) -> WorkflowSpec:
    # Cron كل 5 دقائق → HTTP → IF (status != 200) → HTTP(POST Telegram API)
    spec = WorkflowSpec(
        name="Monitor URL and alert to Telegram",
        timezone=os.getenv("TIMEZONE", "Africa/Algiers"),
        trigger=Trigger(type="cron", config={"hour": 0, "minute": "*/5"}),
        steps=[],
        edges=[]
    )
    spec.steps.append(Step(id="http", type="http", params={"url": url, "method": "GET"}))
    spec.steps.append(Step(id="if", type="if", params={
        "conditions": {"number": [{"operation": "notEqual", "value1": "={{$json[\"statusCode\"]}}", "value2": 200}]}
    }))
    # بدل عقدة Telegram بالـ HTTP API لتجنب Credentials في n8n.cloud
    spec.steps.append(Step(id="tghttp", type="http", params={
        "url": "https://api.telegram.org/bot{{$env.TELEGRAM_BOT_TOKEN}}/sendMessage",
        "method": "POST",
        "json": True,
        "body": {
            "chat_id": "{{$env.TELEGRAM_CHAT_ID}}",
            "text": "={{`⚠️ المشكلة في ${\"" + url + "\"}: ${$json[\"statusCode\"]}`}}"
        }
    }))
    spec.edges += [
        Edge(from_="http", to="if"),
        Edge(from_="if", to="tghttp"),
    ]
    return spec

def tpl_ai_video_outline_to_telegram(prompt: str) -> WorkflowSpec:
    """
    تبسيط لمهمة "اصنع فيديو بالذكاء الاصطناعي": نولّد سكريبت نصي من LLM (لو متاح)،
    ثم نرسله كرسالة/رابط — لأن إنشاء فيديو كامل ورفع تيك توك يحتاج مزودي مدفوعين و OAuth.
    """
    url = "https://httpbin.org/anything/ai-video-outline"
    # لو عندك OPENROUTER متاح، نستبدل HTTP بعقدة HTTP تُنادي خادمك لاحقًا؛ حالياً مجرد placeholder يعمل.
    set_expr = "={{`🎬 مخطط فيديو بالذكاء الاصطناعي لموضوع: " + prompt + "`}}"
    return tpl_cron_http_to_telegram(
        name="Daily AI Video Outline to Telegram",
        url=url,
        method="GET",
        set_expr=set_expr,
        message="={{$json.msg}}",
        hour=9, minute=0
    )
