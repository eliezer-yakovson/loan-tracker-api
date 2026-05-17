-- ─────────────────────────────────────────────────────────────────────────────
-- Loan Tracker — initial schema
-- Run this in the Neon SQL Editor (or any PostgreSQL 14+ instance) to bootstrap
-- the database without running Alembic migrations.
-- ─────────────────────────────────────────────────────────────────────────────

-- 1. Categories  (e.g. "Bank Hapoalim", "Family")
CREATE TABLE IF NOT EXISTS categories (
    id   VARCHAR PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE
);

-- 2. Loans
CREATE TABLE IF NOT EXISTS loans (
    id               VARCHAR        PRIMARY KEY,
    category_id      VARCHAR        NOT NULL REFERENCES categories(id) ON DELETE CASCADE,
    name             VARCHAR(255)   NOT NULL,
    lender_name      VARCHAR(255)   NOT NULL DEFAULT '',
    original_amount  NUMERIC(12, 2) NOT NULL,
    monthly_amount   NUMERIC(12, 2) NOT NULL,
    total_payments   INTEGER        NOT NULL,
    taken_date       VARCHAR(10)    NOT NULL,           -- YYYY-MM-DD
    monthly_due_day  SMALLINT       NOT NULL,
    notes            TEXT           NOT NULL DEFAULT '',
    CONSTRAINT ck_loans_due_day CHECK (monthly_due_day BETWEEN 1 AND 31)
);

CREATE INDEX IF NOT EXISTS ix_loans_category_id ON loans (category_id);

-- 3. Monthly payment entries
--    One row per (loan × month). Unique constraint enables efficient upserts.
CREATE TABLE IF NOT EXISTS month_entries (
    id                 VARCHAR        PRIMARY KEY,
    loan_id            VARCHAR        NOT NULL REFERENCES loans(id) ON DELETE CASCADE,
    month_key          VARCHAR(7)     NOT NULL,         -- YYYY-MM
    amount             NUMERIC(12, 2) NOT NULL,
    installment_number INTEGER        NOT NULL,
    confirmed          BOOLEAN        NOT NULL DEFAULT FALSE,
    manually_edited    BOOLEAN        NOT NULL DEFAULT FALSE,
    CONSTRAINT uq_month_entries_loan_month UNIQUE (loan_id, month_key)
);

CREATE INDEX IF NOT EXISTS ix_month_entries_loan_id   ON month_entries (loan_id);
CREATE INDEX IF NOT EXISTS ix_month_entries_month_key ON month_entries (month_key);
