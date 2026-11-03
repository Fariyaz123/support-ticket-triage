from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy.orm import Session

from app.database import Base, engine, get_db
from app.models import Review, Ticket
from app.schemas import ReviewRequest, TicketCreate, TicketOut
from app.services.pipeline import process_ticket, set_status, ticket_id


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="AI Support Ticket Triage Assistant", lifespan=lifespan)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/tickets", response_model=TicketOut, status_code=201)
def create_ticket(payload: TicketCreate, db: Session = Depends(get_db)) -> Ticket:
    ticket = Ticket(id=ticket_id(), customer_email=str(payload.customer_email), attachment_name=payload.attachment_name, subject=payload.subject, description=payload.description)
    db.add(ticket)
    db.flush()
    set_status(db, ticket, "new", "Ticket created")
    db.commit()
    db.refresh(ticket)
    return process_ticket(db, ticket)


@app.get("/tickets/{ticket_id}", response_model=TicketOut)
def get_ticket(ticket_id: str, db: Session = Depends(get_db)) -> Ticket:
    ticket = db.get(Ticket, ticket_id)
    if ticket is None:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return ticket


@app.post("/tickets/{ticket_id}/process", response_model=TicketOut)
def reprocess_ticket(ticket_id: str, db: Session = Depends(get_db)) -> Ticket:
    ticket = db.get(Ticket, ticket_id)
    if ticket is None:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return process_ticket(db, ticket)


@app.get("/reviews/pending", response_model=list[TicketOut])
def pending_reviews(db: Session = Depends(get_db)) -> list[Ticket]:
    return db.query(Ticket).filter(Ticket.status == "waiting_for_review").order_by(Ticket.created_at.asc()).all()


@app.post("/reviews/{ticket_id}", response_model=TicketOut)
def review_ticket(ticket_id: str, payload: ReviewRequest, db: Session = Depends(get_db)) -> Ticket:
    ticket = db.get(Ticket, ticket_id)
    if ticket is None:
        raise HTTPException(status_code=404, detail="Ticket not found")
    if ticket.status != "waiting_for_review":
        raise HTTPException(status_code=409, detail="Ticket is not waiting for review")
    if payload.action == "edit" and not payload.edited_response:
        raise HTTPException(status_code=422, detail="edited_response is required for edit")
    db.add(Review(ticket_id=ticket.id, reviewer_id=payload.reviewer_id, action=payload.action, edited_response=payload.edited_response, comments=payload.comments))
    if payload.action in {"approve", "edit"}:
        ticket.final_response = payload.edited_response if payload.action == "edit" else ticket.draft_response
        ticket.review_reason = None
        set_status(db, ticket, "answered", f"Reviewed by {payload.reviewer_id}")
    else:
        ticket.final_response = None
        ticket.review_reason = "agent_rejected_draft"
        set_status(db, ticket, "waiting_for_review", f"Draft rejected by {payload.reviewer_id}")
    db.commit()
    db.refresh(ticket)
    return ticket
