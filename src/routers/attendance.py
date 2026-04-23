from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session as DBSession

from src.database import get_db
from src.dependencies import require_roles
from src.models import Session, Attendance, BatchStudent, User
from src.schemas import MarkAttendanceRequest, AttendanceRecord

router = APIRouter(prefix="/attendance", tags=["attendance"])


@router.post("/mark", response_model=AttendanceRecord, status_code=201)
def mark_attendance(
    body: MarkAttendanceRequest,
    db: DBSession = Depends(get_db),
    current_user: User = Depends(require_roles("student")),
):
    """
    Student marks their own attendance for a session.

    Rules:
    - Student must be enrolled in the batch the session belongs to (403 otherwise).
    - A student cannot mark attendance twice for the same session (409).
    """
    # Verify session exists
    session = db.get(Session, body.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")

    # Verify student is enrolled in this session's batch
    enrollment = (
        db.query(BatchStudent)
        .filter(
            BatchStudent.batch_id == session.batch_id,
            BatchStudent.student_id == current_user.id,
        )
        .first()
    )
    if not enrollment:
        raise HTTPException(
            status_code=403,
            detail="You are not enrolled in the batch for this session.",
        )

    # Prevent duplicate attendance
    existing = (
        db.query(Attendance)
        .filter(
            Attendance.session_id == body.session_id,
            Attendance.student_id == current_user.id,
        )
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=409,
            detail="Attendance already marked for this session.",
        )

    record = Attendance(
        session_id=body.session_id,
        student_id=current_user.id,
        status=body.status,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record