# Conference Platform

A distributed, role-based platform for managing scientific conferences end-to-end — from participant registration and paper submission through automated `.docx` formatting validation, organizing-committee review, full-text search, and final generation of the printable conference **program** and **proceedings** (collection of theses) as PDF.

Built as a set of decoupled services communicating over the network: a stateless **FastAPI** backend, **PostgreSQL** for structured data, **MinIO** (S3-compatible) for object storage, and **Elasticsearch** for full-text search. The frontend is a lightweight vanilla-JS SPA served by nginx, which also reverse-proxies the API.

---

## Table of contents

- [Features](#features)
- [Architecture](#architecture)
- [Tech stack](#tech-stack)
- [Domain model](#domain-model)
- [Roles & permissions](#roles--permissions)
- [Submission lifecycle (FSM)](#submission-lifecycle-fsm)
- [Thesis validation rules](#thesis-validation-rules)
- [PDF generation](#pdf-generation)
- [Project layout](#project-layout)
- [Getting started](#getting-started)
- [Configuration](#configuration)
- [Security notes](#security-notes)
- [Database migrations](#database-migrations)
- [Elasticsearch indexing](#elasticsearch-indexing)
- [API reference](#api-reference)
- [Testing](#testing)
- [Branding / white-label deployment](#branding--white-label-deployment)

---

## Features

- **JWT authentication** with bcrypt-hashed passwords; first admin is auto-provisioned on startup from environment variables.
- **Role-based access control** with three roles (`participant`, `org_committee`, `admin`) implemented through a many-to-many `user_roles` table and per-route `Depends(require_*)` guards.
- **Conference management** — create, update, deactivate, and delete conferences; configurable submission deadline.
- **Submission workflow** with a strict finite-state machine (draft → submitted → under_review → accepted/rejected) enforced in the service layer.
- **Multi-author submissions** with presenter flag and explicit ordering.
- **File uploads to S3-compatible storage** (MinIO) via streaming multipart, with a per-file `object_key` generated as a UUID.
- **Automatic `.docx` validation** against scientific-thesis formatting rules (page setup, fonts, header structure, paragraph styling, literature block, captions, length heuristics) — see [Thesis validation rules](#thesis-validation-rules).
- **Full-text search** across submissions (title, abstract, authors, section) via Elasticsearch with fuzzy matching and field boosting.
- **PDF program generator** — produces a fully-formatted conference program from accepted submissions, grouped by section, with chairs/secretary/location metadata per section.
- **PDF proceedings generator** — converts every accepted `.docx` to PDF via headless LibreOffice and merges them with a title page and section dividers into a single book-quality PDF.
- **Three frontend dashboards** rendered by role (participant view, organizing-committee review board, admin console) with Bootstrap 5.
- **Fully containerized** with Docker and an `nginx` reverse proxy that serves the SPA and proxies `/api/*` to the FastAPI app.

---

## Architecture

The system is not a monolith — each component is physically and logically isolated and can be scaled independently:

```
                 ┌──────────────────┐
                 │  Browser (SPA)   │
                 └────────┬─────────┘
                          │ HTTP
                 ┌────────▼─────────┐
                 │      nginx       │  serves /  → static SPA
                 │  reverse proxy   │  proxies /api/* → api:8000
                 └────────┬─────────┘
                          │
                 ┌────────▼─────────┐
                 │  FastAPI (api)   │  stateless application node
                 │  uvicorn:8000    │
                 └─┬────────┬───────┘
        ┌──────────┘        │        └────────────┐
        ▼                   ▼                     ▼
┌──────────────┐   ┌────────────────┐   ┌──────────────────┐
│  PostgreSQL  │   │ MinIO (S3 API) │   │  Elasticsearch    │
│  structured  │   │  binary files  │   │  full-text index  │
│     data     │   │  (.docx, .pdf) │   │                   │
└──────────────┘   └────────────────┘   └──────────────────┘
```

The backend node is stateless: every request carries a JWT and all persistent state lives in PostgreSQL, MinIO, or Elasticsearch. Configuration is fully externalized via `pydantic-settings` reading from `.env`.

---

## Tech stack

| Layer                | Technology                                            |
| -------------------- | ----------------------------------------------------- |
| Web framework        | FastAPI 0.115, uvicorn[standard] 0.30                 |
| Language             | Python 3.12                                           |
| Validation           | Pydantic 2 + pydantic-settings                        |
| ORM                  | SQLAlchemy 2.0 (declarative `Mapped` style)           |
| Migrations           | Alembic 1.13 (autogenerate)                           |
| Relational DB        | PostgreSQL (via psycopg2-binary)                      |
| Object storage       | MinIO + boto3 (S3v4 signed)                           |
| Search engine        | Elasticsearch 8.12                                    |
| Authentication       | python-jose (JWT, HS256) + passlib[bcrypt]            |
| `.docx` processing   | python-docx                                           |
| `.docx → PDF`        | headless LibreOffice (subprocess)                     |
| PDF rendering        | WeasyPrint (HTML/CSS → PDF) + Jinja2 templates        |
| PDF merging          | PyPDF2                                                |
| Frontend             | Vanilla JS + Bootstrap 5.3 + Bootstrap Icons          |
| Reverse proxy        | nginx                                                 |
| Containerization     | Docker                                                |
| Dependency manager   | Poetry                                                |
| Linting              | Ruff                                                  |

---

## Domain model

The schema is normalized and uses UUID primary keys everywhere except the static `roles` lookup table (small int).

- **User** — central authentication entity (email, password hash, full name, `is_active`).
- **Role / UserRole** — many-to-many roles assignment. Role deletion is `RESTRICT`ed to preserve referential integrity.
- **Group / GroupMember / ConferenceGroup** — logical groupings of users (reviewers, organizing committee) that can be attached to specific conferences.
- **Conference** — aggregating entity (title, description, `submission_deadline`, `is_active`).
- **Submission** — a paper proposal (title, abstract, section, status, `submitted_at`) belonging to one conference and one primary author.
- **SubmissionAuthor** — co-authors of a submission with ordering and a presenter flag.
- **SubmissionFile** — uploaded files associated with a submission (bucket, `object_key`, MIME type, size, original filename).
- **ValidationReport** — JSON-serialized result of automated `.docx` validation, one-to-one with `SubmissionFile`.

All foreign keys cascade on delete from their parent aggregate (e.g. deleting a `Conference` removes its submissions and their files).

---

## Roles & permissions

| Role ID | Name             | Capabilities                                                                                            |
| ------- | ---------------- | ------------------------------------------------------------------------------------------------------- |
| 1       | `participant`    | Create own submissions, upload files, submit draft → submitted, view only own submissions.              |
| 2       | `org_committee`  | All participant rights + review submissions (any transition), see all submissions, generate program/proceedings. |
| 3       | `admin`          | All org rights + user CRUD, conference CRUD, role assignment / revocation.                              |

Authorization is enforced through `Depends(require_admin)`, `Depends(require_org_committee)`, `Depends(require_participant)` dependencies that check the user's roles against the required set. Where additional rules apply (e.g. participants can only modify their *own* drafts), the check happens explicitly in the route handler.

---

## Submission lifecycle (FSM)

State transitions are explicitly whitelisted in `app/services/submission_service.py`. Any attempt to make a non-allowed transition returns HTTP 422.

```
              ┌──────────────────────┐
              │        draft         │◄──────────────────┐
              └──────────┬───────────┘                   │
                         │ submit (participant)          │
                         ▼                               │
              ┌──────────────────────┐                   │
              │      submitted       │───────────────────┘
              └──────────┬───────────┘   return to draft
                         │ take for review (org)
                         ▼
              ┌──────────────────────┐
              │     under_review     │
              └──────┬───────────┬───┘
              accept │           │ reject
                     ▼           ▼
              ┌──────────┐  ┌──────────┐
              │ accepted │  │ rejected │──── return to draft ──┐
              └──────────┘  └──────────┘                       │
                  terminal                                     │
                                                               ▼
                                                          (back to draft)
```

Participants may **only** drive `draft → submitted` on their own submissions. All other transitions require `org_committee` or `admin`.

---

## Thesis validation rules

The module `app/services/thesis_validation/` automatically checks uploaded `.docx` files against the academic-paper formatting standard the platform was built for. Validation runs on upload, results are persisted as a `ValidationReport`, and the frontend immediately shows the user a per-rule breakdown of errors and warnings.

Checked rules include:

- **Page setup** — A4 size, 20 mm margins on all four sides, no headers or footers (errors).
- **Header structure** — first three non-empty paragraphs must be title / authors / organization, all centered, bold, 14 pt Times New Roman. Title in `UPPERCASE`. Authors in *italic* with a `Surname I. O.` initial-after-surname pattern.
- **Body paragraphs** — justified alignment, 1.15 line spacing, 1.25 cm first-line indent, Times New Roman 14 pt (warnings if style-inherited).
- **Literature block** — must exist at the end of the document, with a dedicated header and numbered items (`1.`, `2.`, …).
- **Figure and table captions** — `Рис. N` / `Таблиця N` patterns must be rendered at 12 pt.
- **Length heuristic** — text content should fit in 1–2 pages (estimated by character count).

Each violation becomes a `ValidationIssue` with a stable `code`, a `severity` (`error` or `warning`), a human-readable `message`, and a `details` dict pinpointing exactly which paragraph/section failed.

---

## PDF generation

Two PDF outputs are produced on demand by the organizing committee, both available from the review dashboard:

### Program (`POST /conferences/{id}/program.pdf`)

A printable program with a title page, a separate page per section listing accepted papers with their authors, chair/secretary attribution, and the section's physical location. The template is `app/templates/program.html` rendered by **Jinja2 + WeasyPrint** using Liberation Serif (TNR-compatible) font face. Section metadata (chairs, secretary, location) is filled in interactively per render from the frontend modal.

### Proceedings / collection (`GET /conferences/{id}/collection.pdf`)

A book-quality merged PDF of all accepted submissions:

1. Fetch all accepted submissions with their latest uploaded `.docx`.
2. For each file: stream from MinIO into a temp dir, convert to PDF via **headless LibreOffice** (`libreoffice --headless --convert-to pdf`).
3. Build a title page and per-section divider pages via WeasyPrint.
4. Merge everything in order with **PyPDF2's `PdfMerger`**.
5. Stream back to the client as `application/pdf`.

LibreOffice must be available in the container image for the proceedings generator to work.

---

## Project layout

```
.
├── app/
│   ├── api/
│   │   ├── deps.py                    # auth / role dependencies
│   │   ├── router.py                  # mounts all routers
│   │   └── routes/                    # admin, auth, conferences, files,
│   │                                  # roles, search, submissions,
│   │                                  # submission_files
│   ├── core/
│   │   ├── config.py                  # pydantic-settings, env-driven
│   │   └── security.py                # JWT + bcrypt
│   ├── db/
│   │   ├── base.py                    # DeclarativeBase
│   │   └── session.py                 # engine, SessionLocal, get_db
│   ├── models/                        # SQLAlchemy 2.0 ORM models
│   ├── schemas/                       # Pydantic v2 schemas
│   ├── services/
│   │   ├── auth_service.py
│   │   ├── conference_service.py
│   │   ├── role_service.py
│   │   ├── submission_service.py
│   │   ├── submission_file_service.py
│   │   ├── search_service.py          # Elasticsearch client
│   │   ├── storage.py                 # boto3 S3 client
│   │   ├── validation_service.py
│   │   ├── thesis_validation/         # .docx rule engine
│   │   ├── program_generator.py       # HTML→PDF via WeasyPrint
│   │   └── collection_generator.py    # .docx→PDF→merge via LibreOffice + PyPDF2
│   ├── scripts/
│   │   └── reindex.py                 # PG → ES backfill
│   ├── templates/
│   │   └── program.html               # Jinja2 template
│   └── main.py                        # FastAPI app + startup hook
├── frontend/
│   ├── index.html                     # login page
│   ├── css/main.css
│   ├── js/
│   │   ├── api.js                     # fetch wrapper
│   │   ├── auth.js                    # localStorage session
│   │   ├── router.js                  # role-based redirect
│   │   ├── admin.js
│   │   ├── review.js
│   │   └── submissions.js
│   └── pages/
│       ├── admin.html
│       ├── review.html
│       └── submissions.html
├── migrations/                        # Alembic
│   ├── env.py
│   └── versions/
├── tests/
│   ├── conftest.py                    # SQLite fixtures, role seeding
│   ├── test_auth.py
│   ├── test_conferences.py
│   └── test_submissions.py
├── alembic.ini
├── Dockerfile
├── nginx.conf
├── pyproject.toml
└── poetry.lock
```

---

## Getting started

### Prerequisites

- Docker and Docker Compose (recommended), or Python 3.12 + Poetry for local dev.
- A `.env` file at the project root (see [Configuration](#configuration)).
- For the proceedings generator: a LibreOffice installation reachable as the `libreoffice` binary inside the API container.

### Run with Docker (recommended)

A `docker-compose.yml` is expected at the project root. It should spin up four services: `api`, `postgres`, `minio`, `elasticsearch`, plus an `nginx` fronting the SPA.

```bash
docker compose up -d --build
docker compose exec api alembic upgrade head    # apply migrations
docker compose exec api python app/scripts/reindex.py   # optional: backfill ES
```

The platform is then reachable at `http://localhost/` (nginx) with the API mounted at `/api/`.

On first startup, the application reads `ADMIN_EMAIL` and `ADMIN_PASSWORD` from the environment and creates the initial admin user if no admin exists yet. **You must set both values yourself before the first run** — never rely on framework defaults for these. See [Security notes](#security-notes).

### Run locally without Docker

```bash
poetry install
export $(cat .env | xargs)
alembic upgrade head
uvicorn app.main:app --reload
```

You'll still need locally-running PostgreSQL, MinIO, and Elasticsearch instances reachable at the URLs configured in `.env`.

---

## Configuration

All settings are loaded from `.env` via `pydantic-settings`. See `app/core/config.py` for the full list. **None of the variables below should be committed to version control with real values** — keep them in `.env` only, and provide a sanitized `.env.example` for collaborators.

| Variable                  | Required | Description                                                       |
| ------------------------- | -------- | ----------------------------------------------------------------- |
| `DATABASE_URL`            | ✅       | SQLAlchemy URL for PostgreSQL                                     |
| `S3_ENDPOINT`             | ✅       | MinIO endpoint (internal Docker hostname or external URL)         |
| `S3_ACCESS_KEY`           | ✅       | MinIO access key                                                  |
| `S3_SECRET_KEY`           | ✅       | MinIO secret key                                                  |
| `S3_BUCKET`               | ✅       | Bucket name (auto-created on first upload)                        |
| `S3_REGION`               |          | S3 region; defaults to `us-east-1` if unset                       |
| `ES_HOST`                 |          | Elasticsearch URL                                                 |
| `SECRET_KEY`              | ✅       | JWT signing key — **must be a strong random value in production** |
| `ACCESS_TOKEN_EXPIRE_MINUTES` |      | JWT lifetime in minutes                                           |
| `ADMIN_EMAIL`             | ✅       | Email of the bootstrap admin created on first startup             |
| `ADMIN_PASSWORD`          | ✅       | Password of the bootstrap admin — **set a strong unique value**   |
| `ADMIN_FULL_NAME`         |          | Display name for the bootstrap admin                              |
| `MINISTRY_TEXT`           |          | Branding line on PDF title pages                                  |
| `INSTITUTION1_TEXT`       |          | First institution block (newlines preserved)                      |
| `INSTITUTION2_TEXT`       |          | Second institution block                                          |
| `CONFERENCE_CITY`         |          | City used in PDF title pages                                      |
| `CONFERENCE_LOCATION`     |          | Default physical location per section                             |
| `SECTION_CONFIGS_JSON`    |          | JSON map of section → `{heads, secretary, location}` defaults     |

---

## Security notes

A few hardening steps are **required** before exposing this platform to the public internet:

- **Generate a fresh `SECRET_KEY`** with at least 32 bytes of entropy (e.g. `python -c "import secrets; print(secrets.token_urlsafe(48))"`). Do not reuse the same key across environments.
- **Set `ADMIN_EMAIL` and `ADMIN_PASSWORD` explicitly** to values you control. Rotate the bootstrap password immediately after first login.
- **Rotate MinIO credentials** — never deploy with the default MinIO root credentials from the official image.
- **Tighten CORS** — the application currently has `allow_origins=["*"]` in `app/main.py`. Restrict this to your actual frontend origin in production.
- **Terminate TLS at nginx** — the included `nginx.conf` listens on port 80 only; add an HTTPS server block with valid certificates before production use.
- **Never commit `.env`** — it is already in `.gitignore`. Provide a `.env.example` with placeholder values for collaborators.

---

## Database migrations

Alembic is configured to dynamically read `DATABASE_URL` from the application settings (`migrations/env.py`), so the same env var drives both the app and migrations.

```bash
# Apply all pending migrations
alembic upgrade head

# Autogenerate a new migration from model changes
alembic revision --autogenerate -m "add some column"

# Roll back one revision
alembic downgrade -1
```

The base revision is empty; the actual schema is built up incrementally through subsequent revisions. The three roles (`participant`, `org_committee`, `admin`) are seeded by a dedicated migration.

---

## Elasticsearch indexing

Submissions are indexed into the `submissions` index automatically on create and on status change. The index document mirrors the relational record plus a flattened authors array:

```json
{
  "id": "<uuid>",
  "title": "...",
  "abstract": "...",
  "section": "...",
  "status": "submitted",
  "conference_id": "<uuid>",
  "authors": [{"full_name": "...", "organization": "...", "email": "..."}]
}
```

The search endpoint runs a `multi_match` with fuzziness and field boosting (`title^3`, `abstract^2`), with optional filtering by `conference_id`. Results are then re-filtered server-side based on the caller's role: participants only see their own submissions.

To backfill the index from PostgreSQL after a wipe or schema change:

```bash
docker compose exec api python app/scripts/reindex.py
```

---

## API reference

OpenAPI/Swagger UI is available at `/docs` and ReDoc at `/redoc` when the API is running. Selected endpoints:

### Auth
- `POST /auth/login` — exchange `{email, password}` for a JWT.
- `GET /auth/me` — current user profile.

### Conferences
- `GET /conferences/?is_active=true` — list conferences.
- `POST /conferences/` — create (admin).
- `PATCH /conferences/{id}` — update (admin).
- `DELETE /conferences/{id}` — delete (admin).
- `POST /conferences/{id}/program.pdf` — generate program PDF (org committee).
- `GET /conferences/{id}/collection.pdf` — generate proceedings PDF (org committee).

### Submissions
- `GET /submissions/sections` — list of allowed section names.
- `POST /submissions/` — create draft (participant).
- `GET /submissions/?conference_id=&status=&section=` — list (role-filtered).
- `GET /submissions/{id}` — single submission with co-authors.
- `PATCH /submissions/{id}/status` — drive the FSM (RBAC-enforced).

### Submission files
- `POST /submissions/{id}/files/` — multipart upload, auto-validates `.docx`.
- `GET /submissions/{id}/files/` — list files attached to a submission.
- `GET /submissions/{id}/files/{file_id}/download` — stream a file from MinIO.
- `GET /submissions/{id}/files/{file_id}/validation` — last validation report.
- `DELETE /submissions/{id}/files/{file_id}` — delete file (from DB and MinIO).

### Search
- `GET /search/submissions?q=&conference_id=` — fuzzy full-text search via Elasticsearch.

### Roles & users (admin)
- `GET /roles/` — list roles.
- `POST /roles/assign` / `POST /roles/revoke` — change a user's roles.
- `GET /admin/users` — list users with their role IDs.
- `POST /admin/users` — create a user with an initial role.
- `DELETE /admin/users/{id}` — remove a user.

---

## Testing

The `tests/` package uses a SQLite-backed `TestClient` with seeded roles and three test users (admin, org, participant). Run with:

```bash
poetry run pytest
```

The current suite covers authentication (success / wrong password / wrong email / missing token / invalid token), conference CRUD and RBAC, submission creation, role-scoped visibility, and FSM validity (including a full happy-path through `draft → submitted → under_review → accepted` and rejection of invalid transitions).

---

## Branding / white-label deployment

The platform ships ready to be re-skinned for any organization without code changes. The settings below — all driven from `.env` — control the strings rendered onto the cover page of the program and the proceedings PDF:

- `MINISTRY_TEXT`
- `INSTITUTION1_TEXT` (newlines preserved)
- `INSTITUTION2_TEXT`
- `CONFERENCE_CITY`
- `CONFERENCE_LOCATION`
- `SECTION_CONFIGS_JSON` — per-section default chairs/secretary/location

Changing these requires no rebuild — just edit `.env` and restart the API container.
