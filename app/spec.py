from __future__ import annotations
from pydantic import BaseModel, Field, field_validator
from typing import List, Literal, Optional, Dict, Any

# ---------- خطة مجردة (يُنتجها الـ LLM) ----------

StepType = Literal["cron", "webhook", "http", "set", "if", "wait", "telegram"]

class Step(BaseModel):
    id: str = Field(..., description="unique id (slug)")
    type: StepType
    name: Optional[str] = None
    params: Dict[str, Any] = Field(default_factory=dict)

class Edge(BaseModel):
    from_: str = Field(..., alias="from")
    to: str

class Plan(BaseModel):
    name: str
    steps: List[Step]
    edges: List[Edge]
    timezone: Optional[str] = "UTC"

    @field_validator("steps")
    @classmethod
    def unique_ids(cls, v: List[Step]):
        ids = [s.id for s in v]
        if len(ids) != len(set(ids)):
            raise ValueError("Step ids must be unique")
        return v

# ---------- n8n workflow (المنتج النهائي) ----------

class N8nNode(BaseModel):
    id: str
    name: str
    type: str
    typeVersion: int
    position: List[int]
    parameters: Dict[str, Any] = Field(default_factory=dict)
    credentials: Optional[Dict[str, Dict[str, str]]] = None

class N8nWorkflow(BaseModel):
    name: str
    nodes: List[N8nNode]
    connections: Dict[str, Dict[str, List[Dict[str, Any]]]]
    settings: Dict[str, Any] = Field(default_factory=dict)
