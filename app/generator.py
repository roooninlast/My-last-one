from __future__ import annotations
from typing import List, Dict, Any, Tuple
from .spec import Plan, Step, Edge, N8nNode, N8nWorkflow

# ---------- تحويل الخطة المجردة إلى n8n ----------

def _grid_positions(steps: List[Step]) -> Dict[str, Tuple[int,int]]:
    # وزّع العقد أفقياً بشكل بسيط
    x0, y0, dx = 200, 400, 300
    pos = {}
    for i, s in enumerate(steps):
        pos[s.id] = (x0 + i*dx, y0)
    return pos

def to_n8n_node(step: Step, pos: Tuple[int,int]) -> N8nNode:
    t = step.type
    name = step.name or t.capitalize()

    if t == "cron":
        node_type = "n8n-nodes-base.cron"; ver=1
        parameters = step.params or {}
        # مثال سهل: params قد تحتوي crontab أو كل يوم/ساعة
        if "crontab" in parameters:
            rule = {"interval": "custom", "customInterval": parameters["crontab"]}
            parameters = {"rule": rule}
    elif t == "webhook":
        node_type = "n8n-nodes-base.webhook"; ver=1
        parameters = {
            "path": step.params.get("path", "hook"),
            "httpMethod": step.params.get("method","POST"),
            "responseMode": "onReceived",
            "responseData": step.params.get("responseData","received"),
        }
    elif t == "http":
        node_type = "n8n-nodes-base.httpRequest"; ver=3
        p = step.params or {}
        parameters = {
            "url": p.get("url",""),
            "method": p.get("method","GET"),
            "authentication": "none",
        }
        if p.get("headers"):
            parameters["options"] = {"headers": [{"name":k,"value":v} for k,v in p["headers"].items()]}
        if p.get("json"):
            parameters["sendBody"] = True
            parameters["jsonParameters"] = True
            parameters["options"] = parameters.get("options",{})
            parameters["options"]["bodyContentType"] = "json"
            parameters["bodyParametersJson"] = p["json"]
        if p.get("body"):
            parameters["sendBody"] = True
            parameters["options"] = parameters.get("options",{})
            parameters["options"]["bodyContentType"] = "raw"
            parameters["body"] = p["body"]
        if p.get("query"):
            parameters["options"] = parameters.get("options",{})
            parameters["options"]["queryParametersUi"] = {"parameter": [{"name":k,"value":v} for k,v in p["query"].items()]}
    elif t == "set":
        node_type = "n8n-nodes-base.set"; ver=2
        parameters = step.params or {"keepOnlySet": True}
    elif t == "if":
        # سنحوّلها إلى n8n IF node
        node_type = "n8n-nodes-base.if"; ver=2
        expr = step.params.get("expression", "={{true}}")
        # n8n IF لا يأخذ تعبير واحد، لكن نستخدم "string" و "operation": "contains" بحيلة بسيطة
        parameters = {
            "conditions": {
                "string": [
                    {"value1": expr, "operation": "contains", "value2": "true"}
                ]
            }
        }
    elif t == "wait":
        node_type = "n8n-nodes-base.wait"; ver=1
        parameters = {"time": {"unit": "seconds", "value": int(step.params.get("seconds", 5))}}
    elif t == "telegram":
        node_type = "n8n-nodes-base.telegram"; ver=2
        p = step.params or {}
        parameters = {"chatId": p.get("chatId","={{$env.TELEGRAM_CHAT_ID}}"), "text": p.get("text","")}
        credentials = {"telegramApi": {"id":"TELEGRAM_CRED","name":"Telegram Account"}}
        return N8nNode(id=step.id, name=name, type=node_type, typeVersion=ver, position=list(pos), parameters=parameters, credentials=credentials)
    else:
        node_type = "n8n-nodes-base.noOp"; ver=1; parameters = {}

    return N8nNode(
        id=step.id,
        name=name,
        type=node_type,
        typeVersion=ver,
        position=list(pos),
        parameters=parameters
    )

def plan_to_n8n(plan: Plan) -> N8nWorkflow:
    positions = _grid_positions(plan.steps)
    nodes: List[N8nNode] = [to_n8n_node(s, positions[s.id]) for s in plan.steps]

    # connections
    connections: Dict[str, Dict[str, List[Dict[str,Any]]]] = {}
    for e in plan.edges:
        src = next((n for n in nodes if n.id == e.from_), None)
        dst = next((n for n in nodes if n.id == e.to), None)
        if not src or not dst: 
            # نتجاهل الربط غير الصحيح بدلاً من إسقاط الاستيراد كله
            continue
        con_key = src.name
        connections.setdefault(con_key, {"main": []})
        connections[con_key]["main"].append({"node": dst.name, "type": "main", "index": 0})

    return N8nWorkflow(
        name=plan.name,
        nodes=nodes,
        connections=connections,
        settings={"timezone": plan.timezone or "UTC"}
    )
