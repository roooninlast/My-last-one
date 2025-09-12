from typing import Dict, Any, List
from .spec import WorkflowSpec, Step

def _pos(i: int) -> List[int]:
    # توزيع أفقي بسيط لعقد n8n
    return [260 + i * 260, 300]

def _http_node_from_step(step: Step, i: int) -> Dict[str, Any]:
    url = step.params.get("url", "")
    method = step.params.get("method", "GET")

    # تطبيع: لو فيها BTC/سعر واستخدمت coindesk → بدّل إلى Binance الأنسب للسحابات المجانية
    if "coindesk" in url or ("btc" in url.lower() and not url):
        url = "https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT"

    return {
        "name": step.params.get("name", "HTTP Request"),
        "type": "n8n-nodes-base.httpRequest",
        "typeVersion": 3,
        "parameters": {
            "url": url,
            "method": method
        },
        "position": _pos(i)
    }

def _set_node_from_step(step: Step, i: int) -> Dict[str, Any]:
    return {
        "name": step.params.get("name", "Set"),
        "type": "n8n-nodes-base.set",
        "typeVersion": 2,
        "parameters": {
            "keepOnlySet": True,
            "values": step.params.get("values", {})
        },
        "position": _pos(i)
    }

def _telegram_node_from_step(step: Step, i: int) -> Dict[str, Any]:
    # لا نضع credentials كي لا يمنع n8n.cloud الحفظ
    return {
        "name": step.params.get("name", "Telegram"),
        "type": "n8n-nodes-base.telegram",
        "typeVersion": 2,
        "parameters": {
            "chatId": step.params.get("chatId", "={{$env.TELEGRAM_CHAT_ID}}"),
            "text": step.params.get("message", "No message")
        },
        "position": _pos(i)
    }

def _if_node_from_step(step: Step, i: int) -> Dict[str, Any]:
    return {
        "name": step.params.get("name", "IF"),
        "type": "n8n-nodes-base.if",
        "typeVersion": 2,
        "parameters": step.params,
        "position": _pos(i)
    }

def spec_to_n8n(spec: WorkflowSpec) -> Dict[str, Any]:
    nodes: List[Dict[str, Any]] = []
    name_by_id: Dict[str, str] = {}

    # Trigger
    if spec.trigger.type == "cron":
        # نترجم الكرون إلى triggerTimes إن أمكن، وإلا نترك Cron Default
        cron_node = {
            "name": "Cron",
            "type": "n8n-nodes-base.cron",
            "typeVersion": 1,
            "parameters": {
                "triggerTimes": [{
                    "hour": spec.trigger.config.get("hour", 9),
                    "minute": spec.trigger.config.get("minute", 0)
                }]
            },
            "position": _pos(0)
        }
        nodes.append(cron_node)
        name_by_id["trigger"] = "Cron"
    else:
        webhook_node = {
            "name": "Webhook",
            "type": "n8n-nodes-base.webhook",
            "typeVersion": 1,
            "parameters": {
                "path": spec.trigger.config.get("path", "auto/webhook"),
                "httpMethod": spec.trigger.config.get("method", "POST")
            },
            "position": _pos(0)
        }
        nodes.append(webhook_node)
        name_by_id["trigger"] = "Webhook"

    # Steps → Nodes
    for i, s in enumerate(spec.steps, start=1):
        if s.type == "http":
            node = _http_node_from_step(s, i)
        elif s.type == "set":
            node = _set_node_from_step(s, i)
        elif s.type == "telegram":
            node = _telegram_node_from_step(s, i)
        elif s.type == "if":
            node = _if_node_from_step(s, i)
        else:
            # أنواع أخرى غير مدعومة حاليًا نتخطاها
            continue
        nodes.append(node)
        name_by_id[s.id] = node["name"]

    # Connections بصيغة n8n الصحيحة: main: [[ {...} ]]
    connections: Dict[str, Any] = {}

    def connect(frm: str, to: str):
        if frm not in connections:
            connections[frm] = {"main": [[{"node": to, "type": "main", "index": 0}]]}
        else:
            # نضيف وصلة جديدة داخل نفس الـ array
            connections[frm]["main"][0].append({"node": to, "type": "main", "index": 0})

    # وصل الترِغر بأول عقدة إن وُجدت
    if spec.steps:
        connect(name_by_id["trigger"], name_by_id[spec.steps[0].id])

    # وصلات spec المعرّفة
    for e in spec.edges:
        if e.from_ in name_by_id and e.to in name_by_id:
            connect(name_by_id[e.from_], name_by_id[e.to])

    return {
        "name": spec.name,
        "nodes": nodes,
        "connections": connections,
        "settings": {"timezone": spec.timezone}
            }
