from typing import Dict, Any
from .spec import WorkflowSpec

def spec_to_n8n(spec: WorkflowSpec) -> Dict[str, Any]:
    nodes = []
    name_by_id = {}

    # helper للمواضع
    def pos(i): return [260 + i*260, 300]

    # Trigger
    if spec.trigger.type == "cron":
        nodes.append({
            "name": "Cron",
            "type": "n8n-nodes-base.cron",
            "typeVersion": 1,
            "parameters": {
                "triggerTimes": [{"hour": 9, "minute": 0}]
            },
            "position": pos(0)
        })
        name_by_id["trigger"] = "Cron"
    else:
        nodes.append({
            "name": "Webhook",
            "type": "n8n-nodes-base.webhook",
            "typeVersion": 1,
            "parameters": {
                "path": spec.trigger.config.get("path","auto/webhook"),
                "httpMethod": spec.trigger.config.get("method","POST")
            },
            "position": pos(0)
        })
        name_by_id["trigger"] = "Webhook"

    # Steps
    for i, s in enumerate(spec.steps, start=1):
        if s.type == "http":
            node = {
                "name": "HTTP Request",
                "type": "n8n-nodes-base.httpRequest",
                "typeVersion": 3,
                "parameters": {
                    "url": s.params.get("url"),
                    "method": s.params.get("method","GET")
                },
                "position": pos(i)
            }
        elif s.type == "set":
            node = {
                "name": "Set",
                "type": "n8n-nodes-base.set",
                "typeVersion": 2,
                "parameters": {"keepOnlySet": True, "values": s.params.get("values",{})},
                "position": pos(i)
            }
        elif s.type == "telegram":
            node = {
                "name": "Telegram",
                "type": "n8n-nodes-base.telegram",
                "typeVersion": 2,
                "parameters": {
                    "chatId": s.params.get("chatId","={{$env.TELEGRAM_CHAT_ID}}"),
                    "text": s.params.get("message","No message")
                },
                "credentials": {"telegramApi": "Telegram Account"},
                "position": pos(i)
            }
        elif s.type == "if":
            node = {
                "name": "IF",
                "type": "n8n-nodes-base.if",
                "typeVersion": 2,
                "parameters": s.params,
                "position": pos(i)
            }
        else:
            continue
        nodes.append(node)
        name_by_id[s.id] = node["name"]

    # Connections: n8n expects double array: "main": [[ {...} ]]
    def edge(frm_name, to_name):
        return {frm_name: {"main": [[{"node": to_name, "type": "main", "index": 0}]]}}

    connections: Dict[str, Any] = {}

    # وصل الترِغر بأول عقدة إن وُجدت
    if spec.steps:
        connections.update(edge(name_by_id["trigger"], name_by_id[spec.steps[0].id]))

    # وصلات مذكورة في spec
    for e in spec.edges:
        if e.from_ in name_by_id and e.to in name_by_id:
            connections.update(edge(name_by_id[e.from_], name_by_id[e.to]))

    return {"name": spec.name, "nodes": nodes, "connections": connections, "settings": {"timezone": spec.timezone}}
