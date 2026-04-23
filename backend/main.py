from typing import List

from fastapi import Depends, FastAPI, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from .auth import create_access_token, get_password_hash, verify_password
from .database import Base, engine, get_db
from .deps import get_current_user, require_roles
from .models import Reply, Ticket, User
from .notifications import (
    notify_department_on_ticket_create,
    notify_student_on_reply,
)
from .schemas import (
    ReplyCreate,
    ReplyOut,
    TicketCreate,
    TicketDetailOut,
    TicketOut,
    TicketStatusUpdate,
    TokenResponse,
    UserLogin,
    UserPublic,
    UserRegister,
)

app = FastAPI(title="Campus Compliance Ticketing API")
Base.metadata.create_all(bind=engine)


def normalize_department(value: str) -> str:
    return value.strip().casefold()


def to_ticket_out(ticket: Ticket) -> TicketOut:
    return TicketOut(
        id=ticket.id,
        title=ticket.title,
        description=ticket.description,
        student_id=ticket.student_id,
        student_name=ticket.student.name if ticket.student else None,
        student_email=ticket.student.email if ticket.student else None,
        department=ticket.department,
        status=ticket.status,
        created_at=ticket.created_at,
        updated_at=ticket.updated_at,
    )


def to_reply_out(reply: Reply) -> ReplyOut:
    return ReplyOut(
        id=reply.id,
        ticket_id=reply.ticket_id,
        sender_id=reply.sender_id,
        sender_name=reply.sender.name if reply.sender else None,
        sender_role=reply.sender.role if reply.sender else None,
        message=reply.message,
        created_at=reply.created_at,
    )


def get_ticket_or_404(db: Session, ticket_id: int) -> Ticket:
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return ticket


def validate_ticket_access(user: User, ticket: Ticket):
    is_owner = user.role == "student" and ticket.student_id == user.id
    is_assigned_department = user.role == "department" and normalize_department(
        ticket.department
    ) == normalize_department(user.name)
    is_admin = user.role == "admin"
    if not (is_owner or is_assigned_department or is_admin):
        raise HTTPException(status_code=403, detail="Not authorized to access this ticket")


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.post("/register", response_model=UserPublic, status_code=status.HTTP_201_CREATED)
def register(payload: UserRegister, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(
        name=payload.name.strip(),
        email=payload.email.lower(),
        password_hash=get_password_hash(payload.password),
        role=payload.role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@app.post("/login", response_model=TokenResponse)
def login(payload: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email.lower()).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token(subject=user.email, role=user.role)
    return TokenResponse(
        access_token=token, role=user.role, name=user.name, email=user.email
    )


@app.post("/tickets", response_model=TicketOut, status_code=status.HTTP_201_CREATED)
def create_ticket(
    payload: TicketCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("student")),
):
    ticket = Ticket(
        title=payload.title.strip(),
        description=payload.description.strip(),
        student_id=current_user.id,
        department=payload.department.strip(),
        status="Open",
    )
    db.add(ticket)
    db.commit()
    db.refresh(ticket)
    notify_department_on_ticket_create(ticket.department, ticket.title, ticket.id)
    return to_ticket_out(ticket)


@app.get("/tickets/my", response_model=List[TicketOut])
def get_my_tickets(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("student")),
):
    tickets = (
        db.query(Ticket)
        .filter(Ticket.student_id == current_user.id)
        .order_by(Ticket.updated_at.desc())
        .all()
    )
    return [to_ticket_out(t) for t in tickets]


@app.get("/tickets/department", response_model=List[TicketOut])
def get_department_tickets(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("department")),
):
    tickets = (
        db.query(Ticket)
        .filter(func.lower(Ticket.department) == normalize_department(current_user.name))
        .order_by(Ticket.updated_at.desc())
        .all()
    )
    return [to_ticket_out(t) for t in tickets]


@app.get("/tickets/{ticket_id}", response_model=TicketDetailOut)
def get_ticket_details(
    ticket_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ticket = get_ticket_or_404(db, ticket_id)
    validate_ticket_access(current_user, ticket)
    return TicketDetailOut(
        **to_ticket_out(ticket).model_dump(),
        replies=[to_reply_out(reply) for reply in ticket.replies],
    )


@app.get("/tickets/{ticket_id}/replies", response_model=List[ReplyOut])
def get_ticket_replies(
    ticket_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ticket = get_ticket_or_404(db, ticket_id)
    validate_ticket_access(current_user, ticket)
    replies = (
        db.query(Reply)
        .filter(Reply.ticket_id == ticket_id)
        .order_by(Reply.created_at.asc())
        .all()
    )
    return [to_reply_out(reply) for reply in replies]


@app.post("/tickets/{ticket_id}/reply", response_model=ReplyOut, status_code=201)
def add_reply(
    ticket_id: int,
    payload: ReplyCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ticket = get_ticket_or_404(db, ticket_id)
    validate_ticket_access(current_user, ticket)

    reply = Reply(ticket_id=ticket.id, sender_id=current_user.id, message=payload.message.strip())
    db.add(reply)

    # When department/admin starts responding, move open tickets to in-progress automatically.
    if current_user.role in {"department", "admin"} and ticket.status == "Open":
        ticket.status = "In Progress"
        db.add(ticket)

    db.commit()
    db.refresh(reply)

    if ticket.student and current_user.id != ticket.student_id:
        notify_student_on_reply(ticket.student.email, ticket.id)

    return to_reply_out(reply)


@app.put("/tickets/{ticket_id}/status", response_model=TicketOut)
def update_ticket_status(
    ticket_id: int,
    payload: TicketStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("department", "admin")),
):
    ticket = get_ticket_or_404(db, ticket_id)
    if current_user.role == "department" and normalize_department(
        ticket.department
    ) != normalize_department(current_user.name):
        raise HTTPException(status_code=403, detail="Not authorized for this department ticket")

    ticket.status = payload.status
    db.add(ticket)
    db.commit()
    db.refresh(ticket)
    return to_ticket_out(ticket)


@app.get("/admin/tickets", response_model=List[TicketOut])
def get_all_tickets_admin(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin")),
):
    tickets = db.query(Ticket).order_by(Ticket.updated_at.desc()).all()
    return [to_ticket_out(t) for t in tickets]
