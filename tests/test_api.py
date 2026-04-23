"""
pytest test suite for SkillBridge Attendance API.

Tests 1, 3 hit the real (SQLite) test database.
Tests 2, 4, 5 also use the real database via TestClient.

Run with: pytest tests/ -v
"""
import pytest
from fastapi.testclient import TestClient
from src.models import Institution, BatchTrainer

# ─────────────────────────────────────────────────────────────────────────────
# Helper: decode JWT without verification (just inspect payload)
# ─────────────────────────────────────────────────────────────────────────────
import jwt as pyjwt

def decode_payload(token: str) -> dict:
    return pyjwt.decode(token, options={"verify_signature": False})


# ─────────────────────────────────────────────────────────────────────────────
# Test 1 — Student signup and login, valid JWT returned
# (Hits real SQLite database)
# ─────────────────────────────────────────────────────────────────────────────
def test_student_signup_and_login(client: TestClient):
    """
    A new student can sign up and log in.
    Both calls must return a valid JWT containing the correct role.
    """
    signup_resp = client.post("/auth/signup", json={
        "name": "Alice Kumar",
        "email": "alice@test.com",
        "password": "securepass",
        "role": "student",
    })
    assert signup_resp.status_code == 201, signup_resp.text
    signup_token = signup_resp.json()["access_token"]
    assert signup_token

    signup_payload = decode_payload(signup_token)
    assert signup_payload["role"] == "student"
    assert signup_payload["token_type"] == "access"
    assert "sub" in signup_payload
    assert "exp" in signup_payload

    # Now log in
    login_resp = client.post("/auth/login", json={
        "email": "alice@test.com",
        "password": "securepass",
    })
    assert login_resp.status_code == 200, login_resp.text
    login_token = login_resp.json()["access_token"]
    assert login_token

    login_payload = decode_payload(login_token)
    assert login_payload["role"] == "student"
    assert login_payload["token_type"] == "access"


# ─────────────────────────────────────────────────────────────────────────────
# Test 2 — Trainer creates a session with all required fields
# ─────────────────────────────────────────────────────────────────────────────
def test_trainer_creates_session(client: TestClient):
    """
    A trainer can create a session for a batch they are assigned to.
    """
    from tests.conftest import TestingSessionLocal
    db = TestingSessionLocal()

    # Create an institution directly in the DB
    inst = Institution(name="Test Institute")
    db.add(inst)
    db.commit()
    db.refresh(inst)

    # Sign up trainer
    signup = client.post("/auth/signup", json={
        "name": "Bob Trainer",
        "email": "bob.trainer@test.com",
        "password": "trainerpass",
        "role": "trainer",
        "institution_id": inst.id,
    })
    assert signup.status_code == 201
    token = signup.json()["access_token"]
    trainer_id = decode_payload(token)["sub"]
    headers = {"Authorization": f"Bearer {token}"}

    # Create batch
    batch_resp = client.post("/batches", json={
        "name": "Test Batch",
        "institution_id": inst.id,
    }, headers=headers)
    assert batch_resp.status_code == 201, batch_resp.text
    batch_id = batch_resp.json()["id"]

    # Create session
    session_resp = client.post("/sessions", json={
        "batch_id": batch_id,
        "title": "Intro to Python",
        "date": "2025-06-15",
        "start_time": "09:00",
        "end_time": "11:00",
    }, headers=headers)
    assert session_resp.status_code == 201, session_resp.text

    data = session_resp.json()
    assert data["title"] == "Intro to Python"
    assert data["date"] == "2025-06-15"
    assert data["batch_id"] == batch_id

    db.close()


# ─────────────────────────────────────────────────────────────────────────────
# Test 3 — Student marks own attendance successfully
# (Hits real SQLite database)
# ─────────────────────────────────────────────────────────────────────────────
def test_student_marks_attendance(client: TestClient):
    """
    A student enrolled in a batch can mark attendance for a session in that batch.
    """
    from tests.conftest import TestingSessionLocal
    db = TestingSessionLocal()

    # Create institution
    inst = Institution(name="Attendance Test Institute")
    db.add(inst)
    db.commit()
    db.refresh(inst)

    # Create trainer
    trainer_signup = client.post("/auth/signup", json={
        "name": "Carol Trainer",
        "email": "carol.trainer@test.com",
        "password": "pass123",
        "role": "trainer",
        "institution_id": inst.id,
    })
    trainer_token = trainer_signup.json()["access_token"]
    trainer_headers = {"Authorization": f"Bearer {trainer_token}"}

    # Create batch
    batch_resp = client.post("/batches", json={
        "name": "Attendance Batch",
        "institution_id": inst.id,
    }, headers=trainer_headers)
    batch_id = batch_resp.json()["id"]

    # Create session
    session_resp = client.post("/sessions", json={
        "batch_id": batch_id,
        "title": "Test Session",
        "date": "2025-07-01",
        "start_time": "10:00",
        "end_time": "12:00",
    }, headers=trainer_headers)
    session_id = session_resp.json()["id"]

    # Create student
    student_signup = client.post("/auth/signup", json={
        "name": "Dave Student",
        "email": "dave.student@test.com",
        "password": "pass123",
        "role": "student",
    })
    student_token = student_signup.json()["access_token"]
    student_id = decode_payload(student_token)["sub"]
    student_headers = {"Authorization": f"Bearer {student_token}"}

    # Manually enroll student in the batch (simulating invite join)
    from src.models import BatchStudent
    db.add(BatchStudent(batch_id=batch_id, student_id=student_id))
    db.commit()
    db.close()

    # Mark attendance
    mark_resp = client.post("/attendance/mark", json={
        "session_id": session_id,
        "status": "present",
    }, headers=student_headers)
    assert mark_resp.status_code == 201, mark_resp.text
    assert mark_resp.json()["status"] == "present"
    assert mark_resp.json()["student_id"] == student_id


# ─────────────────────────────────────────────────────────────────────────────
# Test 4 — POST to /monitoring/attendance returns 405
# ─────────────────────────────────────────────────────────────────────────────
def test_post_to_monitoring_returns_405(client: TestClient):
    """
    Any non-GET method on /monitoring/attendance must return 405.
    We use a valid monitoring token so the auth layer doesn't interfere.
    """
    import os
    from src.auth import create_monitoring_token

    # Sign up a monitoring officer
    client.post("/auth/signup", json={
        "name": "Eve Monitor",
        "email": "eve.monitor@test.com",
        "password": "pass123",
        "role": "monitoring_officer",
    })
    login_resp = client.post("/auth/login", json={
        "email": "eve.monitor@test.com",
        "password": "pass123",
    })
    login_token = login_resp.json()["access_token"]
    user_id = decode_payload(login_token)["sub"]

    # Get a scoped monitoring token
    api_key = os.getenv("MONITORING_API_KEY", "monitor-api-key-2024")
    mon_token_resp = client.post(
        "/auth/monitoring-token",
        json={"key": api_key},
        headers={"Authorization": f"Bearer {login_token}"},
    )
    assert mon_token_resp.status_code == 200, mon_token_resp.text
    mon_token = mon_token_resp.json()["access_token"]
    mon_headers = {"Authorization": f"Bearer {mon_token}"}

    # POST should return 405
    resp = client.post("/monitoring/attendance", headers=mon_headers)
    assert resp.status_code == 405, resp.text

    # PUT should return 405
    resp = client.put("/monitoring/attendance", headers=mon_headers)
    assert resp.status_code == 405

    # DELETE should return 405
    resp = client.delete("/monitoring/attendance", headers=mon_headers)
    assert resp.status_code == 405


# ─────────────────────────────────────────────────────────────────────────────
# Test 5 — Protected endpoint with no token returns 401
# ─────────────────────────────────────────────────────────────────────────────
def test_no_token_returns_401(client: TestClient):
    """
    Requests to protected endpoints without a Bearer token must return 401.
    """
    endpoints = [
        ("POST", "/batches"),
        ("POST", "/sessions"),
        ("POST", "/attendance/mark"),
        ("GET",  "/programme/summary"),
    ]
    for method, path in endpoints:
        if method == "GET":
            resp = client.get(path)
        else:
            resp = client.post(path, json={})
        assert resp.status_code == 401, f"{method} {path} should return 401, got {resp.status_code}"


# ─────────────────────────────────────────────────────────────────────────────
# Bonus Test 6 — Wrong role gets 403
# ─────────────────────────────────────────────────────────────────────────────
def test_wrong_role_returns_403(client: TestClient):
    """A student cannot create a batch (trainer/institution only)."""
    signup = client.post("/auth/signup", json={
        "name": "Frank Student",
        "email": "frank.student@test.com",
        "password": "pass123",
        "role": "student",
    })
    token = signup.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    resp = client.post("/batches", json={"name": "Bad Batch", "institution_id": "fake"}, headers=headers)
    assert resp.status_code == 403


# ─────────────────────────────────────────────────────────────────────────────
# Bonus Test 7 — Student cannot mark attendance for unenrolled session
# ─────────────────────────────────────────────────────────────────────────────
def test_unenrolled_student_gets_403(client: TestClient):
    """A student not in a batch must get 403 when trying to mark attendance."""
    from tests.conftest import TestingSessionLocal
    db = TestingSessionLocal()

    inst = Institution(name="Enroll Test Institute")
    db.add(inst)
    db.commit()
    db.refresh(inst)

    trainer_signup = client.post("/auth/signup", json={
        "name": "Grace Trainer",
        "email": "grace.trainer@test.com",
        "password": "pass123",
        "role": "trainer",
        "institution_id": inst.id,
    })
    trainer_token = trainer_signup.json()["access_token"]
    trainer_headers = {"Authorization": f"Bearer {trainer_token}"}

    batch_resp = client.post("/batches", json={"name": "Restricted Batch", "institution_id": inst.id}, headers=trainer_headers)
    batch_id = batch_resp.json()["id"]

    session_resp = client.post("/sessions", json={
        "batch_id": batch_id,
        "title": "Restricted Session",
        "date": "2025-08-01",
        "start_time": "10:00",
        "end_time": "12:00",
    }, headers=trainer_headers)
    session_id = session_resp.json()["id"]
    db.close()

    # A student NOT enrolled in the batch
    student_signup = client.post("/auth/signup", json={
        "name": "Hank Outsider",
        "email": "hank.outsider@test.com",
        "password": "pass123",
        "role": "student",
    })
    student_token = student_signup.json()["access_token"]
    student_headers = {"Authorization": f"Bearer {student_token}"}

    resp = client.post("/attendance/mark", json={"session_id": session_id, "status": "present"}, headers=student_headers)
    assert resp.status_code == 403, resp.text