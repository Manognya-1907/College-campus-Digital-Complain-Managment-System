from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, EmailStr, Field

RoleType = Literal["student", "department", "admin"]
TicketStatusType = Literal["Open", "In Progress", "Closed"]


class UserRegister(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)
    role: RoleType


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: RoleType
    name: str
    email: EmailStr


class UserPublic(BaseModel):
    id: int
    name: str
    email: EmailStr
    role: RoleType

    class Config:
        from_attributes = True


class TicketCreate(BaseModel):
    title: str = Field(min_length=3, max_length=255)
    description: str = Field(min_length=5)
    department: str = Field(min_length=2, max_length=100)


class TicketStatusUpdate(BaseModel):
    status: TicketStatusType


class ReplyCreate(BaseModel):
    message: str = Field(min_length=1)


class ReplyOut(BaseModel):
    id: int
    ticket_id: int
    sender_id: int
    sender_name: Optional[str] = None
    sender_role: Optional[str] = None
    message: str
    created_at: datetime


class TicketOut(BaseModel):
    id: int
    title: str
    description: str
    student_id: int
    student_name: Optional[str] = None
    student_email: Optional[EmailStr] = None
    department: str
    status: TicketStatusType
    created_at: datetime
    updated_at: datetime


class TicketDetailOut(TicketOut):
    replies: List[ReplyOut] = []
