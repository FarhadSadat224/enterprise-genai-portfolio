from typing import Literal
from pydantic import BaseModel, Field, field_validator


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=8000)

    @field_validator("message")
    @classmethod
    def nonblank(cls, value):
        if not value.strip():
            raise ValueError("Message cannot be blank")
        return value.strip()


class Citation(BaseModel):
    source: str
    snippet: str
    chunk_id: str


class ChatResponse(BaseModel):
    answer: str
    route: str
    citations: list[Citation] = Field(default_factory=list)
    blocked: bool = False


class IngestRequest(BaseModel):
    source: str = Field(min_length=1, max_length=200, pattern=r"^[\w .-]+$")
    text: str = Field(min_length=1, max_length=100000)


class Principal(BaseModel):
    subject: str
    tenant: str
    role: Literal["reader", "admin"] = "reader"
