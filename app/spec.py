from pydantic import BaseModel, Field, constr
from typing import List, Literal, Dict, Any

class Edge(BaseModel):
    from_: constr(min_length=1) = Field(alias="from")
    to: constr(min_length=1)

class Trigger(BaseModel):
    type: Literal["cron","webhook"]
    config: Dict[str, Any] = {}

class Step(BaseModel):
    id: constr(min_length=1)
    type: Literal["http","if","set","telegram"]
    params: Dict[str, Any] = {}

class WorkflowSpec(BaseModel):
    name: constr(min_length=1)
    timezone: str = "Africa/Algiers"
    trigger: Trigger
    steps: List[Step]
    edges: List[Edge]
    placeholders: List[constr(min_length=1)] = []
