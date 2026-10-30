# FDRSETU — AICTE Intelligent Security Deposit & FDR Management Portal

**F**ixed **D**eposit **R**egistration, **E**valuation, **S**ecurity & **T**racking **U**tility
Smart India Hackathon 2026 · Problem Statement **26265** — *Streamline of Security Deposit / FDR Portal*

> Every FDR Connected. Every Deposit Secured. Every Maturity Tracked.

**All data in this application is DEMO / SYNTHETIC.** It is a working prototype, not an official AICTE system.

---

## Architecture

```
fdrsetu/
├── backend/            FastAPI + SQLAlchemy + PostgreSQL (JWT auth, RBAC)
│   └── app/
│       ├── main.py     App entry — mounts all routers under /api
│       ├── models.py   13 tables: users, institutions, banks, fdr_records,
│       │               fdr_documents, mock_bank_ledger, verification_requests,
│       │               verification_history, risk_alerts, renewal_records,
│       │               release_requests, approval_history, notifications, audit_logs
│       ├── seed.py     20 institutions · 5 banks · ~110 FDRs · mock ledger · demo docs
│       └── services/
│           ├── ocr.py        PyMuPDF → Tesseract → mock extraction pipeline
│           ├── risk.py       duplicate/amount/date/missing-field/bank-mismatch checks
│           ├── maturity.py   90/60/30-day alerts + expiry tracking
│           ├── mockbank.py   SIMULATED bank verification API
│           ├── copilot.py    rule-based assistant over live DB records
│           └── reports.py    Excel (openpyxl) + PDF (reportlab) exports
├── frontend/           React 19 + TypeScript + Tailwind v4 + Recharts (Vite)
├── uploads/            Uploaded FDR documents (local storage; S3-compatible design)
├── sample_docs/        sample_fdr.pdf — text-based FDR the OCR demo can parse
└── docker-compose.yml  PostgreSQL + Redis
```

## Quick start

```bash
# Option A — everything at once (requires docker + node + python3.10+)
./start.sh

# Option B — manual
docker compose up -d                       # postgres + redis
cd backend && python3 -m venv venv && ./venv/bin/pip install -r requirements.txt
./venv/bin/python -m app.seed              # first run only
./venv/bin/uvicorn app.main:app --port 8000
cd ../frontend && npm install && npm run dev
```

- Frontend: http://localhost:5173
- API + Swagger docs: http://localhost:8000/docs
- Health: http://localhost:8000/api/health

## Demo credentials — password `Demo@123`

| Role | Email | Sees |
|---|---|---|
| Institution | `institution@fdrsetu.demo` | own FDRs, register/upload/release/renewal |
| AICTE Officer | `officer@fdrsetu.demo` | command centre, verification, risk review, releases, audit |
| Bank Officer | `bank@fdrsetu.demo` | verification requests, mock ledger lookup, confirm details |
| Super Admin | `admin@fdrsetu.demo` | everything + user & role management |

(`inst2@fdrsetu.demo` and `bank.pnb@fdrsetu.demo` also exist.)

## Configuration — `backend/.env`

| Var | Default | Purpose |
|---|---|---|
| `DATABASE_URL` | postgres localhost:5432/fdrsetu | SQLAlchemy URL (SQLite path also works) |
| `JWT_SECRET` | dev secret | token signing — change in production |
| `UPLOAD_DIR` | `../uploads` | document storage |
| `OPENAI_API_KEY` | empty | unset → rule-based copilot (fully functional) |
| `MOCK_BANK_API` | `true` | bank verification is always labelled simulated |
| `REDIS_URL` | localhost | reserved for Celery background workers |

## The 6 demo scenarios

1. **New FDR submission** — login as `institution@` → *Document Upload & AI* → upload `sample_docs/sample_fdr.pdf` → extracted fields → *Review fields & register* → record saved with unique `FDRSETU-xxxxx` UID + QR code.
2. **Duplicate detection** — register an FDR with number `50000000137` (or any existing) → *Risk & Duplicates* shows a HIGH-severity duplicate alert with the reason. Seed already contains a cross-institution duplicate (`FDRSETU-00101`).
3. **Document verification** — officer opens *Verification* → *Request bank verification* → login as `bank@` → *Bank Verification* → tick confirmations → submit → status flips to verified (mock bank API).
4. **Maturity alert** — *Maturity & Renewal* → *Run maturity scan* → 90/60/30-day notifications appear in the bell icon for both institution and officer.
5. **Release request** — institution → *Release / Refund* → submit with supporting doc → officer reviews → approve/reject/observation → full approval history; approved FDRs become `released`.
6. **AI Copilot** — *AI FDR Copilot* → ask e.g. *"How many FDRs are pending verification?"* or *"Show high-risk FDR records"* → answers from live DB with tables.

## Feature notes

- **OCR pipeline**: text PDFs → PyMuPDF; images/scans → Tesseract (when the `tesseract` binary is installed — `apt install tesseract-ocr`); unreadable files → mock mode with all fields highlighted for manual entry.
- **Risk engine**: duplicate numbers (same + cross-institution), amount/IFSC/maturity mismatch vs mock bank ledger, invalid date combos, missing mandatory fields, malformed IFSC → severities low/medium/high. AI flags for review only.
- **Audit trail**: every login, create, upload, verification, release decision and copilot query is logged (visible under *Audit Logs*).
- **Exports**: Excel + PDF reports of the full FDR register from *Reports & Analytics*.
- **Celery + Redis**: stack-ready; maturity scans currently run synchronously at startup and on-demand — wire `run_maturity_scan` into a Celery beat schedule for production.

## API surface (all under `/api`, JWT Bearer)

`POST /auth/login` · `GET /dashboard/kpis|charts` · `GET/POST /institutions` ·
`GET/POST/PUT /fdrs` · `POST /fdrs/documents/upload` · `GET /fdrs/{id}/qrcode|history` ·
`GET/POST /verification/requests` · `GET /verification/bank-lookup/{no}` · `POST /verification/bank-verify` ·
`GET/POST /risk/alerts|scan` · `GET /maturity/upcoming|expired|renewals` · `POST /maturity/scan|renewals` ·
`GET/POST /releases` · `POST /releases/{id}/action` · `POST /copilot/ask` ·
`GET /reports/fdrs.xlsx|fdrs.pdf` · `GET /users` (admin) · `GET /audit-logs` · `GET /notifications`
