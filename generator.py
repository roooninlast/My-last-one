from typing import Dict, Any
from .spec import WorkflowSpec

def spec_to_n8n(spec: WorkflowSpec) -> Dict[str, Any]:
    nodes = []
    connections: Dict[str, Dict[str, list]] = {}

    # Trigger node
    if spec.trigger.type == "cron":
        nodes.append({
            "id": "trigger",
            "name": "Cron",
            "type": "n8n-nodes-base.cron",
            "typeVersion": 1,
            "parameters": {
                "rule": {
                    "interval": "custom",
                    "customInterval": spec.trigger.config.get("cronExpression","0 9 * * *")
                }
            }
        })
    else:
        nodes.append({
            "id": "trigger",
            "name": "Webhook",
            "type": "n8n-nodes-base.webhook",
            "typeVersion": 1,
            "parameters": {
                "path": spec.trigger.config.get("path","auto/webhook"),
                "httpMethod": spec.trigger.config.get("method","POST")
            }
        })

    # Step nodes
    for s in spec.steps:
        if s.type == "http":
            nodes.append({
                "id": s.id, "name": "HTTP Request",
                "type": "n8n-nodes-base.httpRequest","typeVersion": 3,
                "parameters": {"url": s.params.get("url"), "method": s.params.get("method","GET")}
            })
        elif s.type == "set":
            nodes.append({
                "id": s.id, "name": "Set",
                "type": "n8n-nodes-base.set","typeVersion": 2,
                "parameters": {"keepOnlySet": True, "values": s.params.get("values",{})}
            })
        elif s.type == "telegram":
            nodes.append({
                "id": s.id, "name": "Telegram",
                "type": "n8n-nodes-base.telegram","typeVersion": 2,
                "parameters": {
                    "chatId": s.params.get("chatId","={{$env.TELEGRAM_CHAT_ID}}"),
                    "text": s.params.get("message","No message")
                },
                "credentials": {"telegramApi": {"id": "TELEGRAM_CRED", "name": "Telegram Account"}}
            })
        elif s.type == "if":
            nodes.append({
                "id": s.id, "name": "IF",
                "type": "n8n-nodes-base.if","typeVersion": 2,
                "parameters": s.params
            })

    # Build connections helper
    def add_conn(frm, to):
        source_name = [n["name"] for n in nodes if n["id"] == frm]
        if source_name:
            source = source_name[0]
        else:
            source = frm
        connections.setdefault(source, {}).setdefault("main", []).append({"node": [n["name"] for n in nodes if n["id"]==to][0], "type": "main", "index": 0})

    # Connect trigger to first step if exists
    if spec.steps:
        add_conn("trigger", spec.steps[0].id)

    # Explicit edges
    for e in spec.edges:
        add_conn(e.from_, e.to)

    return {"name": spec.name, "nodes": nodes, "connections": connections, "settings": {"timezone": spec.timezone}}
