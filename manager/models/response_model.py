from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from src.database.triplets import TripletSet
from dataclasses import dataclass, field

@dataclass
class CommandResponse:
    command: str
    timestamp: float = field(default_factory=lambda: datetime.now().timestamp())
    message: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S") + ' -> ')
    success: bool = False
    output: TripletSet|list|None = None


class APIResponse(BaseModel):
    command: str
    timestamp: float = Field(default_factory=lambda: datetime.now().timestamp())
    message: str = ""
    success: bool = False
    output: dict|list|None = None