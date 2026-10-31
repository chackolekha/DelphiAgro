# KrishiLink — Farmer → Retailer Order Management

Direct-to-retailer marketplace for farm produce. See `BLUEPRINT.md` for the
architecture, data model and delivery plan this code implements.

## Stack

- **Backend** — Python 3.12+, FastAPI, SQLAlchemy 2.x (async), Alembic, Redis, APScheduler
- **Frontend** — React 18 + Vite + TypeScript + Tailwind (PWA-ready SPA; `/admin` console included)
- **Infra** — PostgreSQL 16, Redis 7, Docker Compose (dev/staging parity with EC2)

## Quick start (Docker — recommended)

```bash
cp .env.example .env            # fill in values (defaults work for dev)
docker compose up --build
```

- Frontend: http://localhost:5173
- API + Swagger docs: http://localhost:8000/docs
- DB migrations run automatically via the `migrate` service.

### Dev login

- `OTP_DEV_ECHO=true` (default in `.env.example`) returns the OTP in the
  `POST /auth/otp/request` response and the UI shows it — no SMS needed.
- `ADMIN_PHONE` in `.env` is seeded as a verified ADMIN user — log in with that
  phone + echoed OTP to reach `/admin`.

### Happy-path walkthrough

1. Register two users (different phones): set roles **farmer** and **retailer**
   via onboarding.
2. Each submits KYC (`/kyc`) → admin approves both in `/admin` → status VERIFIED.
3. Farmer creates a listing (`/farmer/listings`).
4. Retailer browses (`/browse`), places an order, clicks **Pay (dev)** — the stub
   gateway captures instantly (order → PAID).
5. Farmer accepts → packs → dispatches. Retailer's order page shows a 4-digit
   delivery OTP; farmer enters it → DELIVERED. The jobs container settles it
   after `DISPUTE_WINDOW_HOURS` (or admin resolves disputes earlier).

## Local dev without Docker

```bash
# backend (needs Postgres + Redis running, e.g. `docker compose up db redis`)
cd backend
python -m venv .venv && .venv/Scripts/activate      # Windows; source .venv/bin/activate on *nix
pip install -e ".[dev]"
alembic upgrade head
uvicorn app.main:app --reload

# frontend
cd frontend
npm install
npm run dev          # http://localhost:5173, proxies /api → :8000
```

## Tests & checks

```bash
cd backend && pytest app/tests -x -q        # 7 tests: booking, stock, lifecycle, refunds
cd backend && ruff check app && mypy app    # lint + types
cd frontend && npm run build                # tsc + vite build
```

## Layout

```
backend/app/modules/   auth, users, kyc, catalogue, orders, payments,
                       notifications, admin, common — each with
                       router/service/repository(models)/schemas layering
backend/app/jobs.py    timeout sweeps + settlement (Redis-locked)
frontend/src/pages/    login, onboarding, KYC, browse, orders, farmer, admin
e2e/                   (Playwright — Phase 1+)
infra/                 (Terraform — Phase 0 later)
```

## Notable MVP decisions

- **Payment provider `stub`** executes capture/refund/transfer instantly; switch
  `PAYMENTS_PROVIDER=razorpay` + keys for the real gateway + webhooks.
- **KYC is manual-document** (`MANUAL_DOC`) pending the DigiLocker/KUA provider
  decision (BLUEPRINT §13).
- Stock is reserved at order placement under `SELECT FOR UPDATE` and released on
  cancel/reject/timeout. `order_events` is the append-only audit timeline.
