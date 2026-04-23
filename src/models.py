import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship
from src.database import Base


def gen_uuid():
    return str(uuid.uuid4())


class Institution(Base):
    """
    Institutions are the top-level organisational unit.
    Not listed explicitly in the spec, but required because both
    users.institution_id and batches.institution_id reference it.
    """
    __tablename__ = "institutions"

    id = Column(String, primary_key=True, default=gen_uuid)
    name = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    users = relationship("User", back_populates="institution", foreign_keys="User.institution_id")
    batches = relationship("Batch", back_populates="institution")


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=gen_uuid)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False, index=True)
    hashed_password = Column(String, nullable=False)
    role = Column(
        Enum(
            "student", "trainer", "institution",
            "programme_manager", "monitoring_officer",
            name="user_role"
        ),
        nullable=False
    )
    institution_id = Column(String, ForeignKey("institutions.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    institution = relationship("Institution", back_populates="users", foreign_keys=[institution_id])


class Batch(Base):
    __tablename__ = "batches"

    id = Column(String, primary_key=True, default=gen_uuid)
    name = Column(String, nullable=False)
    institution_id = Column(String, ForeignKey("institutions.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    institution = relationship("Institution", back_populates="batches")
    sessions = relationship("Session", back_populates="batch")


class BatchTrainer(Base):
    """
    Many-to-many: multiple trainers can be assigned to the same batch.
    Composite PK avoids duplicate assignments.
    """
    __tablename__ = "batch_trainers"

    batch_id = Column(String, ForeignKey("batches.id"), primary_key=True)
    trainer_id = Column(String, ForeignKey("users.id"), primary_key=True)


class BatchStudent(Base):
    """
    Populated when a student uses an invite token (POST /batches/join).
    """
    __tablename__ = "batch_students"

    batch_id = Column(String, ForeignKey("batches.id"), primary_key=True)
    student_id = Column(String, ForeignKey("users.id"), primary_key=True)


class BatchInvite(Base):
    """
    Trainer generates a one-time invite token. Student redeems it to join the batch.
    used=True once redeemed; expires_at enforces a time window.
    """
    __tablename__ = "batch_invites"

    id = Column(String, primary_key=True, default=gen_uuid)
    batch_id = Column(String, ForeignKey("batches.id"), nullable=False)
    token = Column(String, unique=True, nullable=False)
    created_by = Column(String, ForeignKey("users.id"), nullable=False)
    expires_at = Column(DateTime, nullable=False)
    used = Column(Boolean, default=False)


class Session(Base):
    __tablename__ = "sessions"

    id = Column(String, primary_key=True, default=gen_uuid)
    batch_id = Column(String, ForeignKey("batches.id"), nullable=False)
    trainer_id = Column(String, ForeignKey("users.id"), nullable=False)
    title = Column(String, nullable=False)
    date = Column(String, nullable=False)        # YYYY-MM-DD
    start_time = Column(String, nullable=False)  # HH:MM
    end_time = Column(String, nullable=False)    # HH:MM
    created_at = Column(DateTime, default=datetime.utcnow)

    batch = relationship("Batch", back_populates="sessions")
    attendance_records = relationship("Attendance", back_populates="session")


class Attendance(Base):
    __tablename__ = "attendance"

    id = Column(String, primary_key=True, default=gen_uuid)
    session_id = Column(String, ForeignKey("sessions.id"), nullable=False)
    student_id = Column(String, ForeignKey("users.id"), nullable=False)
    status = Column(
        Enum("present", "absent", "late", name="attendance_status"),
        nullable=False
    )
    marked_at = Column(DateTime, default=datetime.utcnow)

    session = relationship("Session", back_populates="attendance_records")