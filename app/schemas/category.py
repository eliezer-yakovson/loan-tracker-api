from pydantic import BaseModel


class CategoryBase(BaseModel):
    name: str


class CategoryCreate(CategoryBase):
    """Used when the client pushes a category (may include a pre-generated id)."""
    id: str | None = None


class CategoryRead(CategoryBase):
    """Returned to the client."""
    id: str

    model_config = {"from_attributes": True}


class CategoryUpdate(BaseModel):
    """All fields optional — PATCH semantics."""
    name: str | None = None
