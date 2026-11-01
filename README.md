# Delphi Agro — Farmer → Retailer Order Management

Direct-to-retailer marketplace for farm produce. See `BLUEPRINT.md` for the
architecture, data model and delivery plan this code implements.

## Stack

- **Backend** — Python 3.12+, FastAPI, SQLAlchemy 2.x (async), Alembic, APScheduler
- **Frontend** — React 18 + Vite + TypeScript + Tailwind (PWA-ready SPA; `/admin` console included)
- **Infra** — Neon Postgres (external, free tier), Docker Compose on a single EC2 host.
  OTP / rate-limit / idempotency state lives in a process-local TTL store
  (`app/core/kv.py`) — no Redis service needed.

## Quick start (Docker — recommended)

```bash
cp .env.example .env            # set DATABASE_URL to your Neon pooled URL
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
# backend (needs DATABASE_URL set — Neon or any reachable Postgres)
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

## Deployment — Git → Docker Hub → AWS EC2

`.github/workflows/ci.yml` implements the full path on every push to `main`:

1. **CI**: backend lint/typecheck/tests, frontend build (also runs on PRs).
2. **Images**: builds `krishilink-backend` and `krishilink-frontend`, tags them
   `latest` + git SHA, pushes to Docker Hub.
3. **Deploy**: SCPs `docker-compose.prod.yml` **and a generated `.env`** (built
   from GitHub secrets) to the EC2 host, then SSH `docker compose pull && up -d`
   (migrations run via the `migrate` service against Neon before the API
   starts), followed by a `/health` smoke check.
4. **Rollback**: on the host, `TAG=<previous-sha> docker compose up -d`.

### Database — Neon (free tier)

The database is external; no Postgres container runs on EC2.

1. Create a Neon project → copy the **pooled** connection string
   (`ep-xxx-pooler.<region>.aws.neon.tech`).
2. Convert the driver prefix: `postgresql://` → `postgresql+asyncpg://` and keep
   `?sslmode=require`. Example:
   `postgresql+asyncpg://user:pw@ep-xxx-pooler.us-east-1.aws.neon.tech/krishilink?sslmode=require`
3. On the EC2 host, put it in `~/krishilink/db.env` — **not** in GitHub secrets:

   ```bash
   echo 'DATABASE_URL=postgresql+asyncpg://user:pw@ep-xxx-pooler.us-east-2.aws.neon.tech/neondb?sslmode=require' \
     > ~/krishilink/db.env && chmod 600 ~/krishilink/db.env
   ```

   `docker-compose.prod.yml` reads `env_file: [.env, db.env]` — `.env` is
   rewritten by CI on each deploy; `db.env` is yours alone.

Free-tier notes: compute auto-suspends after ~5 min idle — the first request of
a quiet period takes ~1s to wake. `pool_pre_ping` + `pool_recycle` and
asyncpg's disabled statement cache (PgBouncer pooler requirement) are already
handled in `backend/app/core/db.py`. Schema changes deploy automatically via
the `migrate` service (`alembic upgrade head`).

### One-time EC2 host setup

```bash
# on the EC2 instance (Amazon Linux 2023 / Ubuntu)
sudo dnf install -y docker docker-compose-plugin && sudo systemctl enable --now docker
sudo usermod -aG docker $USER        # re-login after this
mkdir -p ~/krishilink
# create db.env with your Neon URL (see "Database — Neon" above);
# .env is written by the CI deploy step — no need to create it
```

### GitHub secrets to set (repo → Settings → Secrets and variables → Actions)

| Secret | Value |
|---|---|
| `DOCKERHUB_USERNAME` | Docker Hub username (used in image names) |
| `DOCKERHUB_TOKEN` | Docker Hub access token (read+write) |
| `EC2_HOST` | Public IP or DNS of the EC2 instance |
| `EC2_USER` | SSH user, e.g. `ec2-user` / `ubuntu` |
| `EC2_SSH_KEY` | Full private key (PEM) for that user |
| `JWT_SECRET` | Random secret, e.g. `openssl rand -hex 32` |
| `ADMIN_PHONE` | Phone that gets the seeded ADMIN role, e.g. `+91xxxxxxxxxx` |
| `CORS_ORIGINS` | `http://<ec2-ip>` or your domain (comma-separated) |
| `PAYMENTS_PROVIDER` | Optional — defaults to `stub`; `razorpay` for live |
| `RAZORPAY_KEY_ID` / `RAZORPAY_KEY_SECRET` / `RAZORPAY_WEBHOOK_SECRET` | Optional — only when `PAYMENTS_PROVIDER=razorpay` |

Inbound rules on the security group: `22` (your IP), `80` (world). The API is
reached through the frontend's nginx proxy — no port 8000 exposure needed.

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
backend/app/jobs.py    timeout sweeps + settlement (single instance)
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
