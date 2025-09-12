import os, requests
from typing import List
from .spec import WorkflowSpec, Step

def static_checks(spec: WorkflowSpec) -> List[str]:
    issues = []
    if not spec.steps:
        issues.append("لا توجد خطوات في الـ workflow.")
    # كرون بدائي
    if spec.trigger.type == "cron":
        h = spec.trigger.config.get("hour")
        m = spec.trigger.config.get("minute")
        if h is None or m is None:
            # ليس خطأ قاتل، فقط تنبيه
            issues.append("تم استخدام Cron بوقت افتراضي 09:00 (لم تُحدد hour/minute).")
    return issues

def active_checks(spec: WorkflowSpec, timeout: float = 4.0) -> List[str]:
    # تعطيل افتراضيًا على الاستضافة المجانية
    if os.getenv("SKIP_ACTIVE_CHECKS", "true").lower() in ("1", "true", "yes"):
        return []
    issues = []
    for s in spec.steps:
        if s.type == "http":
            url = s.params.get("url")
            if url:
                try:
                    r = requests.get(url, timeout=timeout)
                    if r.status_code >= 400:
                        issues.append(f"فشل الوصول إلى {url}: status {r.status_code}")
                except Exception as e:
                    issues.append(f"فشل الوصول إلى {url}: {e}")
    return issues
