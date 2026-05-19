# Set required env vars before any app module is imported.
# These are only used during testing and never reach a real DB or SMTP server.
import os

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost/test")
os.environ.setdefault("SECRET_KEY", "test-secret-key-only-used-in-unit-tests")
