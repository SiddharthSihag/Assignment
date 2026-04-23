from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional, Literal
from datetime import datetime


# ─── Auth ────────────────────────────────────────────────────────────────────

class SignupRequest(BaseModel):
    name: str
    email: EmailStr
    password: str
    role: Literal["student", "trainer", "institution", "programme_manager", "monitoring_officer"]
    institution_id: Optional[str] = None

    @field_validator("password")
    @classmethod
    def password_min_length(cls, v):
        if len(v) < 6:
            raise ValueError("Password must be at least 6 characters")
        return v


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class MonitoringTokenRequest(BaseModel):
    key: str


# ─── Batches ─────────────────────────────────────────────────────────────────

class CreateBatchRequest(BaseModel):
    name: str
    institution_id: str


class BatchResponse(BaseModel):
    id: str
    name: str
    institution_id: str
    created_at: datetime

    class Config:
        from_attributes = True


class InviteResponse(BaseModel):
    token: str
    expires_at: datetime
    batch_id: str


class JoinBatchRequest(BaseModel):
    token: str


# ─── Sessions ────────────────────────────────────────────────────────────────

class CreateSessionRequest(BaseModel):
    batch_id: str
    title: str
    date: str        # YYYY-MM-DD
    start_time: str  # HH:MM
    end_time: str    # HH:MM

    @field_validator("date")
    @classmethod
    def validate_date(cls, v):
        try:
            datetime.strptime(v, "%Y-%m-%d")
        except ValueError:
            raise ValueError("date must be in YYYY-MM-DD format")
        return v

    @field_validator("start_time", "end_time")
    @classmethod
    def validate_time(cls, v):
        try:
            datetime.strptime(v, "%H:%M")
        except ValueError:
            raise ValueError("time must be in HH:MM format")
        return v


class SessionResponse(BaseModel):
    id: str
    batch_id: str
    trainer_id: str
    title: str
    date: str
    start_time: str
    end_time: str
    created_at: datetime

    class Config:
        from_attributes = True


# ─── Attendance ───────────────────────────────────────────────────────────────

class MarkAttendanceRequest(BaseModel):
    session_id: str
    status: Literal["present", "absent", "late"]


class AttendanceRecord(BaseModel):
    id: str
    session_id: str
    student_id: str
    status: str
    marked_at: datetime

    class Config:
        from_attributes = True


class AttendanceWithStudent(BaseModel):
    student_id: str
    student_name: str
    status: str
    marked_at: datetime


# ─── Summaries ───────────────────────────────────────────────────────────────

class SessionSummary(BaseModel):
    session_id: str
    session_title: str
    date: str
    total: int
    present: int
    absent: int
    late: int


class BatchSummary(BaseModel):
    batch_id: str
    batch_name: str
    sessions: list[SessionSummary]


class InstitutionSummary(BaseModel):
    institution_id: str
    batches: list[BatchSummary]


class ProgrammeSummary(BaseModel):
    total_students: int
    total_sessions: int
    total_attendance_records: int
    by_institution: list[InstitutionSummary]