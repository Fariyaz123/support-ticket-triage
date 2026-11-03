from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field


Category = Literal["billing", "login_access", "technical_issue", "refund", "account_management", "other"]
Urgency = Literal["low", "medium", "high", "critical"]


class TicketCreate(BaseModel):
    customer_email: EmailStr
    subject: str = Field(min_length=5, max_length=200)
    description: str = Field(min_length=20, max_length=5000)
    attachment_name: str | None = Field(default=None, max_length=255)


class ClassificationResult(BaseModel):
    category: Category
    urgency: Urgency
    intent: str = Field(min_length=2, max_length=100)
    confidence: float = Field(ge=0.0, le=1.0)
    summary: str = Field(min_length=3, max_length=500)


class ValidationResult(BaseModel):
    supported: bool
    confidence: float = Field(ge=0.0, le=1.0)
    unsupported_claims: list[str] = Field(default_factory=list)


class ReviewRequest(BaseModel):
    reviewer_id: str = Field(min_length=2, max_length=100)
    action: Literal["approve", "edit", "reject"]
    edited_response: str | None = Field(default=None, max_length=10000)
    comments: str | None = Field(default=None, max_length=2000)


class SourceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    source_name: str
    section: str
    relevance_score: float


class TicketOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    customer_email: EmailStr
    attachment_name: str | None = None
    subject: str
    description: str
    status: str
    category: str | None = None
    urgency: str | None = None
    intent: str | None = None
    classification_confidence: float | None = None
    summary: str | None = None
    draft_response: str | None = None
    final_response: str | None = None
    validation_supported: bool | None = None
    validation_confidence: float | None = None
    review_reason: str | None = None
    created_at: datetime
    updated_at: datetime
    sources: list[SourceOut] = []
