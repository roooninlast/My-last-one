from __future__ import annotations
from pydantic import BaseModel, field_validator
from typing import Dict, Any
import json

class LLMEnvelope(BaseModel):
    """نطلب من الـ LLM يعيد JSON داخل هذا الظرف للحماية من الخروج النصّي."""
    plan: Dict[str, Any]

    @field_validator("plan")
    @classmethod
    def must_have(cls, v):
        if "steps" not in v or "edges" not in v or "name" not in v:
            raise ValueError("Invalid plan format")
        return v

def coerce_json(text: str) -> Dict[str, Any]:
    """يحاول استخراج JSON من نص الـ LLM بأمان."""
    # أبسط محاولة قوية: ابحث عن أول { وآخر } وجرّب
    try:
        start = text.index("{")
        end = text.rindex("}")
        payload = text[start:end+1]
        return json.loads(payload)
    except Exception:
        raise ValueError("LLM did not return valid JSON")
