from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session as DBSession
from sqlalchemy import func

from src.database import get_db
from src.dependencies import require_roles
from src.models import Batch, Session, Attendance, Institution, BatchStudent, User
from src.schemas import BatchSummary, SessionSummary, InstitutionSummary, ProgrammeSummary

router = APIRouter(tags=["summaries"])


def _build_session_summaries(db: DBSession, batch_id: str) -> list[SessionSummary]:
    sessions = db.query(Session).filter(Session.batch_id == batch_id).all()
    result = []
    for s in sessions:
        counts = (
            db.query(Attendance.status, func.count(Attendance.id))
            .filter(Attendance.session_id == s.id)
            .group_by(Attendance.status)
            .all()
        )
        count_map = {status: cnt for status, cnt in counts}
        result.append(SessionSummary(
            session_id=s.id,
            session_title=s.title,
            date=s.date,
            total=sum(count_map.values()),
            present=count_map.get("present", 0),
            absent=count_map.get("absent", 0),
            late=count_map.get("late", 0),
        ))
    return result


@router.get("/batches/{batch_id}/summary", response_model=BatchSummary)
def batch_summary(
    batch_id: str,
    db: DBSession = Depends(get_db),
    current_user: User = Depends(require_roles("institution")),
):
    """Institution sees the attendance summary for one of their batches."""
    batch = db.get(Batch, batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found.")

    if batch.institution_id != current_user.institution_id:
        raise HTTPException(status_code=403, detail="This batch does not belong to your institution.")

    return BatchSummary(
        batch_id=batch.id,
        batch_name=batch.name,
        sessions=_build_session_summaries(db, batch_id),
    )


@router.get("/institutions/{institution_id}/summary", response_model=InstitutionSummary)
def institution_summary(
    institution_id: str,
    db: DBSession = Depends(get_db),
    current_user: User = Depends(require_roles("programme_manager")),
):
    """Programme Manager sees a summary across all batches in an institution."""
    institution = db.get(Institution, institution_id)
    if not institution:
        raise HTTPException(status_code=404, detail="Institution not found.")

    batches = db.query(Batch).filter(Batch.institution_id == institution_id).all()
    batch_summaries = [
        BatchSummary(
            batch_id=b.id,
            batch_name=b.name,
            sessions=_build_session_summaries(db, b.id),
        )
        for b in batches
    ]

    return InstitutionSummary(institution_id=institution_id, batches=batch_summaries)


@router.get("/programme/summary", response_model=ProgrammeSummary)
def programme_summary(
    db: DBSession = Depends(get_db),
    current_user: User = Depends(require_roles("programme_manager")),
):
    """Programme Manager sees the full programme-wide summary."""
    total_students = db.query(func.count(User.id)).filter(User.role == "student").scalar()
    total_sessions = db.query(func.count(Session.id)).scalar()
    total_attendance = db.query(func.count(Attendance.id)).scalar()

    institutions = db.query(Institution).all()
    inst_summaries = []
    for inst in institutions:
        batches = db.query(Batch).filter(Batch.institution_id == inst.id).all()
        batch_summaries = [
            BatchSummary(
                batch_id=b.id,
                batch_name=b.name,
                sessions=_build_session_summaries(db, b.id),
            )
            for b in batches
        ]
        inst_summaries.append(
            InstitutionSummary(institution_id=inst.id, batches=batch_summaries)
        )

    return ProgrammeSummary(
        total_students=total_students,
        total_sessions=total_sessions,
        total_attendance_records=total_attendance,
        by_institution=inst_summaries,
    )