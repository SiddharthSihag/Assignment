import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.database import get_db
from src.dependencies import require_roles, get_current_user
from src.models import Batch, BatchInvite, BatchStudent, BatchTrainer, User
from src.schemas import CreateBatchRequest, BatchResponse, InviteResponse, JoinBatchRequest

router = APIRouter(prefix="/batches", tags=["batches"])


@router.post("", response_model=BatchResponse, status_code=201)
def create_batch(
    body: CreateBatchRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("trainer", "institution")),
):
    """Trainer or Institution creates a new batch."""
    # Verify institution exists
    from src.models import Institution
    institution = db.get(Institution, body.institution_id)
    if not institution:
        raise HTTPException(status_code=404, detail="Institution not found.")

    batch = Batch(name=body.name, institution_id=body.institution_id)
    db.add(batch)
    db.flush()

    # Auto-assign the creating trainer to the batch
    if current_user.role == "trainer":
        db.add(BatchTrainer(batch_id=batch.id, trainer_id=current_user.id))

    db.commit()
    db.refresh(batch)
    return batch


@router.post("/{batch_id}/invite", response_model=InviteResponse)
def create_invite(
    batch_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("trainer")),
):
    """Trainer generates a one-time invite token for a batch."""
    batch = db.get(Batch, batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found.")

    # Ensure this trainer is assigned to the batch
    assignment = (
        db.query(BatchTrainer)
        .filter(BatchTrainer.batch_id == batch_id, BatchTrainer.trainer_id == current_user.id)
        .first()
    )
    if not assignment:
        raise HTTPException(status_code=403, detail="You are not assigned to this batch.")

    token = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(days=7)

    invite = BatchInvite(
        batch_id=batch_id,
        token=token,
        created_by=current_user.id,
        expires_at=expires_at,
    )
    db.add(invite)
    db.commit()
    db.refresh(invite)

    return InviteResponse(token=token, expires_at=expires_at, batch_id=batch_id)


@router.post("/join", status_code=200)
def join_batch(
    body: JoinBatchRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("student")),
):
    """Student redeems an invite token to join a batch."""
    invite = (
        db.query(BatchInvite)
        .filter(BatchInvite.token == body.token)
        .first()
    )
    if not invite:
        raise HTTPException(status_code=404, detail="Invite token not found.")
    if invite.used:
        raise HTTPException(status_code=409, detail="Invite token has already been used.")
    if invite.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
        raise HTTPException(status_code=410, detail="Invite token has expired.")

    # Check if already enrolled
    existing = (
        db.query(BatchStudent)
        .filter(BatchStudent.batch_id == invite.batch_id, BatchStudent.student_id == current_user.id)
        .first()
    )
    if existing:
        raise HTTPException(status_code=409, detail="You are already enrolled in this batch.")

    db.add(BatchStudent(batch_id=invite.batch_id, student_id=current_user.id))
    invite.used = True
    db.commit()

    return {"message": "Successfully joined batch.", "batch_id": invite.batch_id}