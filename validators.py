import re, requests
from typing import List, Tuple
from croniter import croniter
from datetime import datetime
from .spec import WorkflowSpec, Step

def validate_cron(expr: str) -> Tuple[bool, str]:
    try:
        croniter(expr, datetime.now())
        return True, ""
    except Exception as e:
        return False, str(e)

def static_checks(spec: WorkflowSpec) -> List[str]:
    issues = []
    # Trigger
    if spec.trigger.type == "cron":
        ok, msg = validate_cron(spec.trigger.config.get("cronExpression",""))
        if not ok:
            issues.append(f"صيغة كرون غير صالحة: {msg}")
    elif spec.trigger.type == "webhook":
        path = spec.trigger.config.get("path","")
        if not path:
            issues.append("Webhook يحتاج path محدد.")
    # Steps unique ids
    ids = [s.id for s in spec.steps]
    if len(ids) != len(set(ids)):
        issues.append("هناك تكرار في معرفات العُقد (id).")
    # Edges refer to real nodes
    node_ids = set(["trigger"] + ids)
    for e in spec.edges:
        if e.from_ not in node_ids:
            issues.append(f"Edge from يوجه إلى عقدة غير موجودة: {e.from_}")
        if e.to not in node_ids:
            issues.append(f"Edge to يوجه إلى عقدة غير موجودة: {e.to}")
    return issues

def active_checks(spec: WorkflowSpec, timeout: float = 4.0) -> List[str]:
    issues = []
    # test HTTP endpoints (best-effort)
    for s in spec.steps:
        if s.type == "http":
            url = s.params.get("url")
            if not url:
                issues.append(f"HTTP node {s.id} بدون URL.")
                continue
            try:
                r = requests.head(url, timeout=timeout)
                if r.status_code >= 400:
                    # try GET
                    r = requests.get(url, timeout=timeout)
                if r.status_code >= 400:
                    issues.append(f"URL {url} يرجع حالة {r.status_code}.")
            except Exception as e:
                issues.append(f"فشل الوصول إلى {url}: {e}")
    return issues
