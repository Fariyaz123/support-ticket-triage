from datetime import datetime, timezone
import uuid

from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import ResponseSource, StatusHistory, Ticket
from app.services.ai import AIService
from app.services.escalation import decide_review
from app.services.knowledge import FAQRetriever


def ticket_id() -> str:
    return f"TCK-{datetime.now(timezone.utc):%Y%m%d}-{uuid.uuid4().hex[:6].upper()}"


def set_status(db: Session, ticket: Ticket, status: str, note: str | None = None) -> None:
    ticket.status = status
    db.add(StatusHistory(ticket_id=ticket.id, status=status, note=note))


def process_ticket(db: Session, ticket: Ticket) -> Ticket:
    settings = get_settings()
    set_status(db, ticket, "processing")
    db.flush()
    ai = AIService(settings)
    retriever = FAQRetriever(settings)
    classification = ai.classify(ticket.subject, ticket.description)
    documents = retriever.retrieve(f"{ticket.subject}\n{ticket.description}\n{classification.intent}")
    draft = ai.generate_answer(ticket.subject, ticket.description, documents)
    validation = ai.validate_answer(draft, documents)
    max_score = max((doc.relevance_score for doc in documents), default=0.0)
    needs_review, reason = decide_review(classification, validation, max_score, settings)

    ticket.category = classification.category
    ticket.urgency = classification.urgency
    ticket.intent = classification.intent
    ticket.classification_confidence = classification.confidence
    ticket.summary = classification.summary
    ticket.draft_response = draft
    ticket.validation_supported = validation.supported
    ticket.validation_confidence = validation.confidence
    ticket.review_reason = reason
    ticket.final_response = None if needs_review else draft
    db.query(ResponseSource).filter(ResponseSource.ticket_id == ticket.id).delete()
    for doc in documents:
        db.add(ResponseSource(ticket_id=ticket.id, source_name=doc.source_name, section=doc.section, content=doc.content, relevance_score=doc.relevance_score))
    set_status(db, ticket, "waiting_for_review" if needs_review else "answered", reason)
    db.commit()
    db.refresh(ticket)
    return ticket

