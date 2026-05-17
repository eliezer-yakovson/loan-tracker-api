---
title: Loan Tracker API
emoji: 💰
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 7860
pinned: false
---

# Loan Tracker API

FastAPI backend for the Hebrew loan-tracking app.

- Database: PostgreSQL (Neon)
- Auth: OTP via email + JWT
- Docs: `/docs`

## Environment Variables (set as Secrets in HF Space settings)

| Variable | Description |
|---|---|
| `DATABASE_URL` | PostgreSQL connection string (Neon) |
| `SECRET_KEY` | JWT signing secret |
| `TOKEN_EXPIRE_DAYS` | JWT expiry in days (default: 7) |
| `FRONTEND_ORIGIN` | Vercel frontend URL for CORS |
| `SMTP_HOST` | SMTP server (e.g. smtp.gmail.com) |
| `SMTP_PORT` | SMTP port (default: 587) |
| `SMTP_USER` | SMTP username |
| `SMTP_PASSWORD` | SMTP app password |
| `SMTP_FROM` | From address |
| `SMTP_FROM_NAME` | From display name |
