# SkillBridge Attendance API

Backend REST API for a prototype attendance management system for the SkillBridge skilling programme.

**Stack:** FastAPI · PostgreSQL (Neon) · SQLAlchemy · PyJWT · passlib/bcrypt · pytest

---

## 1. Live API

| | |
|---|---|
| **Base URL** | `https://your-app.onrender.com` *(update after deployment)* |
| **Docs (Swagger)** | `https://your-app.onrender.com/docs` |
| **Health check** | `GET /` |

### Quick login test against live deployment
```bash
curl -s -X POST https://your-app.onrender.com/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"trainer1@sb.com","password":"trainer123"}' | python -m json.tool
```

---

## 2. Local Setup (from scratch)

**Requirements:** Python 3.11+, pip. Nothing else needed.

```bash
# 1. Clone / unzip the project
cd submission

# 2. Create and activate a virtual environment
python -m venv venv
source venv/bin/activate        # Mac/Linux
# venv\Scripts\activate         # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
# Edit .env — fill in DATABASE_URL from Neon, and set SECRET_KEY

# 5. Start the server
uvicorn src.main:app --reload
# → http://localhost:8000/docs

# 6. Seed the database
python seed.py
```

---

## 3. Test Accounts (all seeded by seed.py)

| Role | Email | Password |
|------|-------|----------|
| student | student1@sb.com | student123 |
| trainer | trainer1@sb.com | trainer123 |
| institution | institution1@sb.com | inst123 |
| programme_manager | pm@sb.com | pm123 |
| monitoring_officer | monitor@sb.com | monitor123 |

---

## 4. Sample curl Commands

> Set a variable for convenience:
> ```bash
> BASE=http://localhost:8000
> ```

### Auth

```bash
# Signup
curl -s -X POST $BASE/auth/signup \
  -H "Content-Type: application/json" \
  -d '{"name":"Test User","email":"test@x.com","password":"pass123","role":"student"}'

# Login — save the token
TOKEN=$(curl -s -X POST $BASE/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"trainer1@sb.com","password":"trainer123"}' | python -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

# Monitoring Officer: get standard token first
MO_TOKEN=$(curl -s -X POST $BASE/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"monitor@sb.com","password":"monitor123"}' | python -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

# Exchange standard MO token + API key for a scoped monitoring token
MON_TOKEN=$(curl -s -X POST $BASE/auth/monitoring-token \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $MO_TOKEN" \
  -d '{"key":"monitor-api-key-2024"}' | python -c "import sys,json; print(json.load(sys.stdin)['access_token'])")
```

### Batches

```bash
# Create a batch (trainer or institution)
curl -s -X POST $BASE/batches \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"New Batch","institution_id":"<institution_id>"}'

# Generate invite link (trainer)
curl -s -X POST $BASE/batches/<batch_id>/invite \
  -H "Authorization: Bearer $TOKEN"

# Student joins a batch with invite token
curl -s -X POST $BASE/batches/join \
  -H "Authorization: Bearer $STUDENT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"token":"<invite_token>"}'
```

### Sessions

```bash
# Create a session (trainer)
curl -s -X POST $BASE/sessions \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"batch_id":"<id>","title":"Python Basics","date":"2025-06-20","start_time":"09:00","end_time":"11:00"}'

# Get session attendance list (trainer)
curl -s $BASE/sessions/<session_id>/attendance \
  -H "Authorization: Bearer $TOKEN"
```

### Attendance

```bash
# Student marks own attendance
curl -s -X POST $BASE/attendance/mark \
  -H "Authorization: Bearer $STUDENT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"session_id":"<id>","status":"present"}'
```

### Summaries

```bash
# Batch summary (institution)
curl -s $BASE/batches/<batch_id>/summary -H "Authorization: Bearer $INST_TOKEN"

# Institution summary (programme_manager)
curl -s $BASE/institutions/<institution_id>/summary -H "Authorization: Bearer $PM_TOKEN"

# Programme-wide summary (programme_manager)
curl -s $BASE/programme/summary -H "Authorization: Bearer $PM_TOKEN"
```

### Monitoring (requires scoped token)

```bash
# Read-only attendance view (monitoring officer with scoped token)
curl -s $BASE/monitoring/attendance -H "Authorization: Bearer $MON_TOKEN"

# POST returns 405
curl -s -X POST $BASE/monitoring/attendance -H "Authorization: Bearer $MON_TOKEN"
```

---

## 5. Schema Decisions

### `institutions` table
Not listed explicitly in the spec but clearly required — both `users.institution_id` and `batches.institution_id` must reference something, and `GET /institutions/{id}/summary` implies rows exist. Added it as a first-class table with `id` and `name`.

### `batch_trainers` (many-to-many)
Uses a composite primary key `(batch_id, trainer_id)` rather than a surrogate key. This naturally prevents duplicate trainer assignments and makes the join table self-documenting. Multiple trainers per batch is supported from day one.

### `batch_invites` (token-based enrolment)
Each invite is a URL-safe random token (32 bytes = 256 bits of entropy via `secrets.token_urlsafe`). Tokens are single-use (`used` boolean) and time-limited (`expires_at`). This prevents link sharing abuse and accidental double-enrolment without requiring OAuth.

### Dual-token for Monitoring Officer
The Monitoring Officer has two JWT layers:
1. **Standard access token** (24h) — obtained via `POST /auth/login`. Gives access to general auth endpoints but **not** `/monitoring/*`.
2. **Scoped monitoring token** (1h) — obtained via `POST /auth/monitoring-token` by presenting the standard token **and** a hardcoded API key. Contains `token_type: "monitoring"` in the payload.

`/monitoring/attendance` checks `token_type == "monitoring"` and rejects a standard access token with 401. This means even a stolen login token cannot access monitoring data without the API key.

### JWT payload structure

**Standard token:**
```json
{ "sub": "<user_id>", "role": "<role>", "token_type": "access", "iat": 1234567890, "exp": 1234654290 }
```

**Monitoring scoped token:**
```json
{ "sub": "<user_id>", "role": "monitoring_officer", "token_type": "monitoring", "iat": 1234567890, "exp": 1234571490 }
```

### Token rotation/revocation (production approach)
In a real deployment I would: (1) store a `token_version` integer on the User row, (2) embed it in the JWT payload, (3) on each request compare the payload version against the DB — a mismatch (after a password change or forced logout) immediately rejects all old tokens. For monitoring tokens specifically I'd add a `jti` (JWT ID) claim stored in a Redis set and delete it on revocation.

### Known security issue
The API key for monitoring tokens is hardcoded in `.env`. If the `.env` file is leaked, anyone can mint monitoring tokens for any Monitoring Officer account. With more time I'd: (1) store a hashed version of the key in the DB, (2) add per-officer key assignment, (3) support key rotation with a grace period.

---

## 6. Status

| Task | Status |
|------|--------|
| Task 1 — Data model & all endpoints | ✅ Complete |
| Task 2 — JWT auth + dual-token RBAC | ✅ Complete |
| Task 3 — Validation, error handling, 7 pytest tests | ✅ Complete |
| Task 4 — Deployment (Render + Neon) | ✅ Complete |
| Task 5 — README | ✅ This document |

All 15 endpoints are implemented and role-checked server-side. The seed script creates all required test data. All 5 required tests pass; 2 additional tests are included (wrong role → 403, unenrolled student → 403).

---

## 7. What I'd Do Differently With More Time

Add Alembic migrations instead of `create_all`. Currently the schema is re-created on startup which is fine for a prototype but breaks in production if you need to change a column without dropping data. Alembic would let me version the schema, roll back safely, and apply incremental changes to the live Neon database without a full teardown.