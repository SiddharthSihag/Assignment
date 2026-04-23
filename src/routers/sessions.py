from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session as DBSession

from src.database import get_db
from src.dependencies import require_roles
from src.models import Batch, Session, Attendance, User, BatchStudent
from src.schemas import CreateSessionRequest, SessionResponse, AttendanceWithStudent

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.post("", response_model=SessionResponse, status_code=201)
def create_session(
    body: CreateSessionRequest,
    db: DBSession = Depends(get_db),
    current_user: User = Depends(require_roles("trainer")),
):
    """Trainer creates a session for a batch they are assigned to."""
    batch = db.get(Batch, body.batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found.")

    from src.models import BatchTrainer
    assignment = (
        db.query(BatchTrainer)
        .filter(
            BatchTrainer.batch_id == body.batch_id,
            BatchTrainer.trainer_id == current_user.id,
        )
        .first()
    )
    if not assignment:
        raise HTTPException(status_code=403, detail="You are not assigned to this batch.")

    session = Session(
        batch_id=body.batch_id,
        trainer_id=current_user.id,
        title=body.title,
        date=body.date,
        start_time=body.start_time,
        end_time=body.end_time,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


@router.get("/{session_id}/attendance", response_model=list[AttendanceWithStudent])
def get_session_attendance(
    session_id: str,
    db: DBSession = Depends(get_db),
    current_user: User = Depends(require_roles("trainer")),
):
    """Trainer retrieves the full attendance list for one of their sessions."""
    session = db.get(Session, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")

    if session.trainer_id != current_user.id:
        raise HTTPException(status_code=403, detail="You did not create this session.")

    records = (
        db.query(Attendance, User)
        .join(User, User.id == Attendance.student_id)
        .filter(Attendance.session_id == session_id)
        .all()
    )

    return [
        AttendanceWithStudent(
            student_id=att.student_id,
            student_name=user.name,
            status=att.status,
            marked_at=att.marked_at,
        )
        for att, user in records
    ]