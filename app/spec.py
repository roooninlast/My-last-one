# app/spec.py
from pydantic import BaseModel, Field, ConfigDict
from typing import Any, Dict, List, Optional

class Trigger(BaseModel):
    type: str  # "cron" أو "webhook" ...
    config: Dict[str, Any] = {}

class Step(BaseModel):
    id: str
    type: str  # "http" | "set" | "if" | ...
    params: Dict[str, Any] = {}

class Edge(BaseModel):
    # 👇 هذا هو المهم
    model_config = ConfigDict(populate_by_name=True)  # يقبل from_ كبديل لـ from
    from_: str = Field(..., alias="from")
    to: str
    # حقول اختيارية مفيدة لـ n8n:
    type: str = "main"
    index: int = 0

class WorkflowSpec(BaseModel):
    name: str = "Generated Workflow"
    timezone: str = "Africa/Algiers"
    trigger: Trigger
    steps: List[Step] = []
    edges: List[Edge] = []

    # للتصدير مع aliases (from)
    def as_dict(self) -> Dict[str, Any]:
        return self.model_dump(by_alias=True)
