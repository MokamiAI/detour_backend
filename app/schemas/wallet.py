from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
import re

class WalletStatus(str, Enum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    CLOSED = "closed"

class TransactionType(str, Enum):
    DEPOSIT = "deposit"
    WITHDRAWAL = "withdrawal"
    TRANSFER = "transfer"
    PAYMENT = "payment"
    REFUND = "refund"

class TransactionStatus(str, Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class WalletBase(BaseModel):
    user_id: str
    balance: float = Field(default=0.0, ge=0)
    currency: str = Field(default="ZAR", min_length=3, max_length=3)
    wallet_number: str
    status: WalletStatus = Field(default=WalletStatus.ACTIVE)
    
    @validator('wallet_number')
    def validate_wallet_number(cls, v):
        if not re.match(r'^[A-Z0-9]{8,20}$', v):
            raise ValueError('Wallet number must be 8-20 alphanumeric characters')
        return v
    
    @validator('currency')
    def validate_currency(cls, v):
        if not v.isalpha() or not v.isupper():
            raise ValueError('Currency must be uppercase alphabetic (e.g., ZAR, USD)')
        return v

class WalletCreate(WalletBase):
    pass

class WalletUpdate(BaseModel):
    balance: Optional[float] = Field(None, ge=0)
    currency: Optional[str] = Field(None, min_length=3, max_length=3)
    status: Optional[WalletStatus] = None

class WalletResponse(WalletBase):
    id: str
    created_at: datetime
    updated_at: datetime
    last_transaction_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

class TransactionBase(BaseModel):
    wallet_id: str
    transaction_type: TransactionType
    amount: float
    currency: str = Field(default="ZAR", min_length=3, max_length=3)
    reference: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None
    status: TransactionStatus = Field(default=TransactionStatus.PENDING)
    metadata: Optional[Dict[str, Any]] = None
    
    @validator('amount')
    def validate_amount(cls, v):
        if v <= 0:
            raise ValueError('Amount must be greater than 0')
        return v

class TransactionCreate(TransactionBase):
    pass

class TransactionResponse(TransactionBase):
    id: str
    created_at: datetime
    
    class Config:
        from_attributes = True

class WalletWithTransactions(WalletResponse):
    recent_transactions: List[TransactionResponse] = []

class APIResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

class DepositRequest(BaseModel):
    amount: float = Field(..., gt=0, description="Amount to deposit")
    currency: str = Field(default="ZAR", description="Currency code")
    description: Optional[str] = Field("Deposit to wallet", description="Transaction description")
    reference: Optional[str] = Field(None, description="External reference ID")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")

class WithdrawalRequest(BaseModel):
    amount: float = Field(..., gt=0, description="Amount to withdraw")
    currency: str = Field(default="ZAR", description="Currency code")
    description: Optional[str] = Field("Withdrawal from wallet", description="Transaction description")
    bank_details: Optional[Dict[str, Any]] = Field(None, description="Bank account details for withdrawal")
    reference: Optional[str] = Field(None, description="External reference ID")

class TransferRequest(BaseModel):
    to_wallet_number: str = Field(..., description="Recipient wallet number")
    amount: float = Field(..., gt=0, description="Amount to transfer")
    currency: str = Field(default="ZAR", description="Currency code")
    description: Optional[str] = Field(None, description="Transfer description")
    reference: Optional[str] = Field(None, description="External reference ID")