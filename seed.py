"""
Seed script for SkillBridge.

Run with:  python seed.py

Creates:
  - 2 institutions
  - 4 trainers  (2 per institution)
  - 15 students (assigned across batches)
  - 3 batches   (2 in inst1, 1 in inst2)
  - 8 sessions  (spread across batches)
  - attendance records for every student in every session
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from datetime import datetime, timedelta, timezone
from src.database import SessionLocal, engine, Base
from src.models import (
    Institution, User, Batch, BatchTrainer, BatchStudent,
    Session, Attendance,
)
from src.auth import hash_password

Base.metadata.create_all(bind=engine)

db = SessionLocal()

print("Seeding database...")

# ── Institutions ─────────────────────────────────────────────────────────────
inst1 = Institution(name="Delhi Institute of Technology")
inst2 = Institution(name="Mumbai Skill Centre")
db.add_all([inst1, inst2])
db.flush()

# ── Trainers ─────────────────────────────────────────────────────────────────
trainers = [
    User(name="Arjun Sharma",   email="trainer1@sb.com", hashed_password=hash_password("trainer123"), role="trainer", institution_id=inst1.id),
    User(name="Priya Mehta",    email="trainer2@sb.com", hashed_password=hash_password("trainer123"), role="trainer", institution_id=inst1.id),
    User(name="Rohit Verma",    email="trainer3@sb.com", hashed_password=hash_password("trainer123"), role="trainer", institution_id=inst2.id),
    User(name="Sneha Iyer",     email="trainer4@sb.com", hashed_password=hash_password("trainer123"), role="trainer", institution_id=inst2.id),
]
db.add_all(trainers)
db.flush()

# ── Students ─────────────────────────────────────────────────────────────────
students = [
    User(name=f"Student {i}", email=f"student{i}@sb.com",
         hashed_password=hash_password("student123"), role="student")
    for i in range(1, 16)
]
db.add_all(students)
db.flush()

# ── Institution accounts ──────────────────────────────────────────────────────
inst_user1 = User(name="DIT Admin",  email="institution1@sb.com", hashed_password=hash_password("inst123"), role="institution", institution_id=inst1.id)
inst_user2 = User(name="MSC Admin",  email="institution2@sb.com", hashed_password=hash_password("inst123"), role="institution", institution_id=inst2.id)

# ── Other roles ────────────────────────────────────────────────────────────────
pm_user  = User(name="Programme Manager", email="pm@sb.com",       hashed_password=hash_password("pm123"),       role="programme_manager")
mo_user  = User(name="Monitoring Officer",email="monitor@sb.com",   hashed_password=hash_password("monitor123"),  role="monitoring_officer")

db.add_all([inst_user1, inst_user2, pm_user, mo_user])
db.flush()

# ── Batches ────────────────────────────────────────────────────────────────────
batch1 = Batch(name="Web Dev Batch A",  institution_id=inst1.id)
batch2 = Batch(name="Data Science Batch B", institution_id=inst1.id)
batch3 = Batch(name="Cloud Computing Batch C", institution_id=inst2.id)
db.add_all([batch1, batch2, batch3])
db.flush()

# ── Batch ↔ Trainer assignments ────────────────────────────────────────────────
db.add_all([
    BatchTrainer(batch_id=batch1.id, trainer_id=trainers[0].id),
    BatchTrainer(batch_id=batch2.id, trainer_id=trainers[1].id),
    BatchTrainer(batch_id=batch3.id, trainer_id=trainers[2].id),
    BatchTrainer(batch_id=batch3.id, trainer_id=trainers[3].id),  # two trainers on batch3
])

# ── Batch ↔ Student assignments ────────────────────────────────────────────────
# batch1: students 0-5, batch2: students 5-9, batch3: students 10-14
for i, s in enumerate(students):
    if i < 6:
        db.add(BatchStudent(batch_id=batch1.id, student_id=s.id))
    elif i < 10:
        db.add(BatchStudent(batch_id=batch2.id, student_id=s.id))
    else:
        db.add(BatchStudent(batch_id=batch3.id, student_id=s.id))

db.flush()

# ── Sessions ──────────────────────────────────────────────────────────────────
base_date = datetime.now(timezone.utc).date()

sessions_data = [
    Session(batch_id=batch1.id, trainer_id=trainers[0].id, title="HTML & CSS Basics",    date=str(base_date - timedelta(days=6)), start_time="09:00", end_time="11:00"),
    Session(batch_id=batch1.id, trainer_id=trainers[0].id, title="JavaScript Intro",      date=str(base_date - timedelta(days=4)), start_time="09:00", end_time="11:00"),
    Session(batch_id=batch1.id, trainer_id=trainers[0].id, title="React Fundamentals",    date=str(base_date - timedelta(days=2)), start_time="10:00", end_time="12:00"),
    Session(batch_id=batch2.id, trainer_id=trainers[1].id, title="Python for Data Science",date=str(base_date - timedelta(days=5)), start_time="14:00", end_time="16:00"),
    Session(batch_id=batch2.id, trainer_id=trainers[1].id, title="Pandas Deep Dive",       date=str(base_date - timedelta(days=3)), start_time="14:00", end_time="16:00"),
    Session(batch_id=batch3.id, trainer_id=trainers[2].id, title="AWS Fundamentals",       date=str(base_date - timedelta(days=7)), start_time="11:00", end_time="13:00"),
    Session(batch_id=batch3.id, trainer_id=trainers[2].id, title="Docker & Containers",    date=str(base_date - timedelta(days=5)), start_time="11:00", end_time="13:00"),
    Session(batch_id=batch3.id, trainer_id=trainers[3].id, title="Kubernetes Intro",       date=str(base_date - timedelta(days=2)), start_time="09:00", end_time="11:00"),
]
db.add_all(sessions_data)
db.flush()

# ── Attendance records ────────────────────────────────────────────────────────
import random
random.seed(42)

batch_student_map = {
    batch1.id: students[:6],
    batch2.id: students[5:10],
    batch3.id: students[10:],
}

statuses = ["present", "present", "present", "absent", "late"]  # weighted

for session in sessions_data:
    enrolled = batch_student_map[session.batch_id]
    for student in enrolled:
        db.add(Attendance(
            session_id=session.id,
            student_id=student.id,
            status=random.choice(statuses),
        ))

db.commit()
print("Done! Seeded:")
print(f"  2 institutions, 4 trainers, 15 students, 3 batches, 8 sessions")
print(f"\nTest accounts:")
print("  student1@sb.com      / student123  (student)")
print("  trainer1@sb.com      / trainer123  (trainer)")
print("  institution1@sb.com  / inst123     (institution)")
print("  pm@sb.com            / pm123       (programme_manager)")
print("  monitor@sb.com       / monitor123  (monitoring_officer)")
db.close()