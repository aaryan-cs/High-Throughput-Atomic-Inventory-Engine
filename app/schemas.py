from pydantic import BaseModel, Field

class ClaimRequest(BaseModel):
    user_id: str = Field(..., min_length=1, max_length=64)
    item_id: str = Field(..., min_length=1, max_length=128)

class ClaimResponse(BaseModel):
    success: bool
    message: str
    order_id: str | None = None
    remaining_stock: int | None = None
    fraud_score: float | None = None
