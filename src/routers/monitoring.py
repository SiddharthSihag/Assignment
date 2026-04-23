from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session as DBSession

from src.database import get_db
from src.dependencies import get_monitoring_user
from src.models import Attendance, Session, User

router = APIRouter(prefix="/monitoring", tags=["monitoring"])

# All HTTP methods we want to handle on this path
_METHODS = ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]


@router.api_route("/attendance", methods=_METHODS)
def monitoring_attendance(
    request: Request,
    db: DBSession = Depends(get_db),
    current_user=Depends(get_monitoring_user),
):
    """
    Read-only attendance view for Monitoring Officers.

    - GET  → returns all attendance records with student & session info.
    - Any other method → 405 Method Not Allowed (as required by spec).

    Authentication: requires a short-lived monitoring-scoped token
    (obtained via POST /auth/monitoring-token), NOT the standard login token.
    """
    if request.method != "GET":
        return JSONResponse(
            status_code=405,
            content={"detail": "Method Not Allowed. This endpoint is read-only."},
            headers={"Allow": "GET"},
        )

    records = (
        db.query(Attendance, Session, User)
        .join(Session, Session.id == Attendance.session_id)
        .join(User, User.id == Attendance.student_id)
        .all()
    )

    return [
        {
            "attendance_id": att.id,
            "student_id": att.student_id,
            "student_name": user.name,
            "session_id": att.session_id,
            "session_title": session.title,
            "session_date": session.date,
            "status": att.status,
            "marked_at": att.marked_at.isoformat(),
        }
        for att, session, user in records
    ]