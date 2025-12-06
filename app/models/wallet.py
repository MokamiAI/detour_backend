from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum

class WalletStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    PENDING = "pending"

class TransactionType(str, Enum):
    CREDIT = "credit"
    DEBIT = "debit"
    TRANSFER = "transfer"
    REFUND = "refund"

class TransactionStatus(str, Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class WalletBase(BaseModel):
    driver_id: Optional[str] = Field(None, description="Driver/user ID")
    user_id: Optional[str] = Field(None, description="User ID (alternative to driver_id)")
    balance: float = Field(0.0, ge=0, description="Current wallet balance")
    currency: str = Field("USD", description="Currency code")
    status: WalletStatus = Field(WalletStatus.ACTIVE, description="Wallet status")
    
    class Config:
        from_attributes = True

class WalletCreate(WalletBase):
    pass

class WalletResponse(WalletBase):
    id: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class WalletWithUser(WalletResponse):
    user: Optional[dict] = Field(None, description="User details")

class TransactionBase(BaseModel):
    wallet_id: str
    amount: float
    transaction_type: TransactionType
    description: str
    reference_id: Optional[str] = None
    status: TransactionStatus = TransactionStatus.COMPLETED
    metadata: Optional[dict] = Field(None, description="Additional transaction data")

class TransactionCreate(TransactionBase):
    pass

class TransactionResponse(TransactionBase):
    id: str
    created_at: datetime
    
    class Config:
        from_attributes = True

class WalletSummary(BaseModel):
    wallet: WalletResponse
    user: dict
    recent_transactions: List[dict]
    total_transactions: int