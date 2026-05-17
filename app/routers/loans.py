from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.engine import get_db
from app.repositories.loan_repository import LoanRepository
from app.schemas.loan import LoanCreate, LoanRead, LoanUpdate

router = APIRouter(prefix="/loans", tags=["loans"])


@router.get("/", response_model=list[LoanRead])
async def list_loans(
    category_id: str | None = Query(default=None, description="Filter by category"),
    db: AsyncSession = Depends(get_db),
):
    repo = LoanRepository(db)
    if category_id:
        return await repo.get_by_category(category_id)
    return await repo.get_all()


@router.get("/{loan_id}", response_model=LoanRead)
async def get_loan(loan_id: str, db: AsyncSession = Depends(get_db)):
    repo = LoanRepository(db)
    loan = await repo.get_by_id(loan_id)
    if not loan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Loan not found")
    return loan


@router.post("/", response_model=LoanRead, status_code=status.HTTP_201_CREATED)
async def create_loan(data: LoanCreate, db: AsyncSession = Depends(get_db)):
    repo = LoanRepository(db)
    loan = await repo.create(data)
    await db.commit()
    return loan


@router.patch("/{loan_id}", response_model=LoanRead)
async def update_loan(
    loan_id: str,
    data: LoanUpdate,
    db: AsyncSession = Depends(get_db),
):
    repo = LoanRepository(db)
    loan = await repo.update(loan_id, data)
    if not loan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Loan not found")
    await db.commit()
    return loan


@router.delete("/{loan_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_loan(loan_id: str, db: AsyncSession = Depends(get_db)):
    repo = LoanRepository(db)
    deleted = await repo.delete(loan_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Loan not found")
    await db.commit()
