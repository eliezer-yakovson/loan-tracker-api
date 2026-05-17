# Import all models here so SQLAlchemy's metadata is aware of every table.
# This is required for Alembic autogenerate and for Base.metadata.create_all().
from app.models.category import Category
from app.models.error_log import ErrorLog
from app.models.loan import Loan
from app.models.month_entry import MonthEntry
from app.models.user import User
from app.models.otp_code import OTPCode

__all__ = ["Category", "ErrorLog", "Loan", "MonthEntry", "User", "OTPCode"]
