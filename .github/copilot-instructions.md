# Copilot instructions for maa_express

This file gives focused, actionable guidance to AI coding agents working on this codebase.

High-level architecture
- **Framework:** Small Flask application using an application factory in `app.py` (function `create_app()`).
- **Blueprints:** Route logic is split into `blueprints/` modules: `main.py`, `auth.py`, `category1.py`, `admin.py`. Registering occurs in `create_app()`.
- **Models:** All DB models live in `models.py` and use `Flask-SQLAlchemy` (`db` is imported from `models`).
- **Frontend:** Jinja templates in `templates/` and assets in `static/` (CSS in `static/css/styles.css`).
- **Storage & Auth:** Uses Firebase Admin SDK for server-side features. Client-side Firebase config values are read from environment variables in `config.py`.

How the app starts
- Development: run `python app.py`. This calls `create_app()`, runs `db.create_all()` inside an app context, then starts Flask with `debug=True`.
- Production (container): Dockerfile uses `gunicorn` with the `app:create_app()` callable; command: `gunicorn -b 0.0.0.0:8080 app:create_app()`.

Critical environment and secrets
- `.env` at repo root is expected and loaded by `config.py` (see `BASE_DIR/.env`).
- Important env vars used in `config.Config`: `DB_USER`, `DB_PASSWORD`, `DB_NAME`, `DB_HOST`, `FIREBASE_CREDENTIALS`, `FIREBASE_PROJECT_ID`, `FIREBASE_STORAGE_BUCKET`, `SECRET_KEY`, mail/PayPal/Stripe keys.
- `FIREBASE_CREDENTIALS` should point to the service account JSON (the repo contains `serviceAccountKey.json` — set the env var to its path in dev).

Database & migrations
- Uses `Flask-SQLAlchemy` with a MySQL URI composed in `config.py` (URL-encodes `DB_PASSWORD`).
- There are no migration files present; the app calls `db.create_all()` on startup (so changes to models require manual migration planning if you want durable migrations).

Key runtime patterns and conventions
- Session-based login: blueprints set `session["user_id"]` after login. Lookup current user via `User.query.get(session["user_id"])` (see `blueprints/main.py` and `auth.py`).
- Authorization: each blueprint defines local decorators (e.g., `login_required` in `auth.py` and `category1.py`, `admin_required` in `admin.py`). Use those decorators rather than rolling a different mechanism.
- Listing lifecycle (Category1): status values observed in code — `pending_documents`, `pending_phone_verification`, `pending_admin_review`, `approved`, `rejected`, `sold`. Follow these exact strings when updating status.
- File URLs: uploaded documents are stored as URLs on model fields (e.g., `ticket_copy_url`, `passport_front_url`). The server expects the frontend to upload files (likely to Firebase Storage) and send back URLs.

Examples of important routes (useful when writing tests or modifying flows)
- Public index: `GET /` → `main.index()` renders `templates/index.html`.
- Register/login endpoints (client posts idToken): `POST /api/register`, `POST /api/login` (see `blueprints/auth.py`). These verify Firebase ID tokens server-side.
- Category1 create flow: `GET/POST /category1/new` → `POST` creates `Category1Listing` and redirects to `/category1/<listing_uid>/upload-docs`.
- Admin status update: `POST /admin/category1/<listing_uid>/update-status` — allowed values: `approved`, `rejected`.

Testing, build, and debug tips
- To run locally: ensure `.env` contains DB and Firebase paths, then run `python app.py`.
- If MySQL isn't available in dev, point `DB_HOST` at a local dockerized MySQL instance and set correct `DB_USER`, `DB_PASSWORD`, `DB_NAME`.
- Use the Dockerfile to reproduce production behavior (gunicorn + `app:create_app()`).

Dependencies (see `requirements.txt`)
- `Flask`, `Flask-SQLAlchemy`, `mysql-connector-python`, `firebase-admin`, `python-dotenv`, `gunicorn`.

What to watch out for (pitfalls discovered in the code)
- Multiple `login_required` decorators are defined per-blueprint (not centralized). When changing auth behavior, update all decorator definitions.
- No DB migrations: structural model changes may be lost unless you add a migration tool (Alembic/Flask-Migrate).
- Firebase initialization expects `FIREBASE_CREDENTIALS` to point to a valid file path; startup will raise if missing.

Editing guidelines for AI agents
- Prefer minimal, focused edits. Respect the blueprint split — add routes to the appropriate file under `blueprints/`.
- When changing model fields, mention the lack of migrations and propose a migration plan in the PR description.
- Use existing session keys (`user_id`) and status strings for compatibility.
- When adding new env vars, also update `config.py` and mention them in the PR description and README.

If anything in this file is unclear or you want more detail (example tests, a migration plan, or centralizing auth), tell me which area to expand.
