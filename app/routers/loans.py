from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.engine import get_db
from app.models.user import User
from app.repositories.loan_repository import LoanRepository
from app.routers.auth import get_current_user
from app.schemas.loan import LoanCreate, LoanRead, LoanUpdate

router = APIRouter(prefix="/loans", tags=["loans"])


@router.get("/", response_model=list[LoanRead])
async def list_loans(
    category_id: str | None = Query(default=None, description="Filter by category"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    repo = LoanRepository(db)
    if category_id:
        return await repo.get_by_category(category_id, current_user.id)
    return await repo.get_all(current_user.id)


@router.get("/{loan_id}", response_model=LoanRead)
async def get_loan(
    loan_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    repo = LoanRepository(db)
    loan = await repo.get_by_id(loan_id)
    if not loan or loan.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Loan not found")
    return loan


@router.post("/", response_model=LoanRead, status_code=status.HTTP_201_CREATED)
async def create_loan(
    data: LoanCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    repo = LoanRepository(db)
    loan = await repo.create(data, current_user.id)
    await db.commit()
    return loan


@router.patch("/{loan_id}", response_model=LoanRead)
async def update_loan(
    loan_id: str,
    data: LoanUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    repo = LoanRepository(db)
    loan = await repo.get_by_id(loan_id)
    if not loan or loan.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Loan not found")
    updated = await repo.update(loan_id, data)
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Loan not found")
    await db.commit()
    return updated


@router.delete("/{loan_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_loan(
    loan_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    repo = LoanRepository(db)
    loan = await repo.get_by_id(loan_id)
    if not loan or loan.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Loan not found")
    await repo.delete(loan_id)
    await db.commit()
