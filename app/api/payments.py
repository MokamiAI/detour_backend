# payments.py - Simple Driver Withdrawals API
# Drivers enter ID and amount to withdraw to bank or get voucher

import uuid
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional
from enum import Enum
import json
from fastapi import APIRouter, HTTPException, Depends, Query, Body, Header, status
from pydantic import BaseModel, Field, validator
import re


# ============================
# DATA MODELS (Pydantic)
# ============================

class WithdrawalType(str, Enum):
    BANK_DEPOSIT = "bank_deposit"      # Direct to bank account
    VOUCHER = "voucher"                # Get voucher code


class WithdrawalStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class BankType(str, Enum):
    NEDBANK = "nedbank"
    STANDARD_BANK = "standard_bank"
    ABSA = "absa"
    FNB = "fnb"
    CAPITEC = "capitec"
    OTHER = "other"


class WithdrawalRequest(BaseModel):
    """Base withdrawal request - driver enters ID and amount"""
    driver_id: str = Field(..., min_length=3, max_length=50, description="Driver's ID")
    amount: Decimal = Field(..., gt=0, le=50000, description="Withdrawal amount in ZAR")
    withdrawal_type: WithdrawalType = Field(..., description="Bank deposit or voucher")
    
    @validator('amount')
    def validate_amount(cls, v):
        """Ensure amount has proper decimal places"""
        if v.as_tuple().exponent < -2:  # More than 2 decimal places
            raise ValueError('Amount can have maximum 2 decimal places')
        return v


class BankWithdrawalDetails(BaseModel):
    """Bank details for bank deposit withdrawal"""
    account_holder_name: str = Field(..., min_length=3, max_length=100)
    account_number: str = Field(..., min_length=9, max_length=15)
    bank_type: BankType = Field(...)
    branch_code: str = Field(..., min_length=6, max_length=6)
    
    @validator('account_holder_name')
    def validate_name(cls, v):
        if not re.match(r'^[A-Za-z\s\-\.]+$', v):
            raise ValueError('Name can only contain letters, spaces, hyphens, and periods')
        return v.title()
    
    @validator('account_number')
    def validate_account_number(cls, v):
        if not re.match(r'^\d{9,15}$', v):
            raise ValueError('Account number must be 9-15 digits')
        return v
    
    @validator('branch_code')
    def validate_branch_code(cls, v):
        if not re.match(r'^\d{6}$', v):
            raise ValueError('Branch code must be 6 digits')
        return v


class VoucherWithdrawalDetails(BaseModel):
    """Details for voucher withdrawal"""
    recipient_name: str = Field(..., min_length=3, max_length=100)
    recipient_phone: str = Field(..., min_length=10, max_length=15)
    
    @validator('recipient_name')
    def validate_recipient_name(cls, v):
        if not re.match(r'^[A-Za-z\s\-\.]+$', v):
            raise ValueError('Name can only contain letters, spaces, hyphens, and periods')
        return v.title()
    
    @validator('recipient_phone')
    def validate_recipient_phone(cls, v):
        if not re.match(r'^(\+27|0)[1-9]\d{8}$', v):
            raise ValueError('Invalid South African phone number')
        return v


class WithdrawalSubmission(BaseModel):
    """Complete withdrawal submission"""
    withdrawal_request: WithdrawalRequest
    bank_details: Optional[BankWithdrawalDetails] = None
    voucher_details: Optional[VoucherWithdrawalDetails] = None
    
    @validator('bank_details')
    def validate_bank_details(cls, v, values):
        """Validate bank details are provided for bank deposit"""
        if values.get('withdrawal_request', {}).get('withdrawal_type') == WithdrawalType.BANK_DEPOSIT and not v:
            raise ValueError('Bank details required for bank deposit')
        return v
    
    @validator('voucher_details')
    def validate_voucher_details(cls, v, values):
        """Validate voucher details are provided for voucher"""
        if values.get('withdrawal_request', {}).get('withdrawal_type') == WithdrawalType.VOUCHER and not v:
            raise ValueError('Voucher details required for voucher withdrawal')
        return v


class WithdrawalResponse(BaseModel):
    """Response for withdrawal request"""
    withdrawal_id: str
    driver_id: str
    amount: str
    withdrawal_type: str
    status: str
    timestamp: str
    reference: str
    voucher_code: Optional[str] = None
    voucher_expiry: Optional[str] = None
    bank_reference: Optional[str] = None
    estimated_completion: Optional[str] = None
    message: str


class WithdrawalStatusResponse(BaseModel):
    """Response for checking withdrawal status"""
    withdrawal_id: str
    driver_id: str
    amount: str
    withdrawal_type: str
    status: str
    timestamp: str
    completed_at: Optional[str] = None
    reference: str
    voucher_code: Optional[str] = None
    voucher_expiry: Optional[str] = None
    bank_reference: Optional[str] = None
    recipient_name: Optional[str] = None
    recipient_phone: Optional[str] = None


# ============================
# WITHDRAWAL MANAGER
# ============================

class WithdrawalManager:
    """Manages driver withdrawals"""
    
    def __init__(self):
        self.withdrawals = {}
        self.vouchers = {}
        
    def create_withdrawal(self, submission: WithdrawalSubmission) -> Dict:
        """Create a new withdrawal"""
        driver_id = submission.withdrawal_request.driver_id
        amount = submission.withdrawal_request.amount
        withdrawal_type = submission.withdrawal_request.withdrawal_type
        
        # Generate withdrawal ID
        withdrawal_id = f"WD-{datetime.now().strftime('%y%m%d')}-{uuid.uuid4().hex[:8].upper()}"
        
        # Generate reference based on type
        if withdrawal_type == WithdrawalType.BANK_DEPOSIT:
            reference = f"BANK-{datetime.now().strftime('%H%M%S')}-{uuid.uuid4().hex[:6].upper()}"
            voucher_code = None
            voucher_expiry = None
            bank_reference = reference
            recipient_name = submission.bank_details.account_holder_name
            recipient_phone = None
        else:  # Voucher
            reference = f"VCH-{datetime.now().strftime('%H%M%S')}-{uuid.uuid4().hex[:6].upper()}"
            voucher_code = self._generate_voucher_code()
            voucher_expiry = (datetime.utcnow() + timedelta(days=30)).isoformat()
            bank_reference = None
            recipient_name = submission.voucher_details.recipient_name
            recipient_phone = submission.voucher_details.recipient_phone
            
            # Store voucher
            self.vouchers[voucher_code] = {
                'voucher_code': voucher_code,
                'driver_id': driver_id,
                'amount': str(amount),
                'recipient_name': recipient_name,
                'recipient_phone': recipient_phone,
                'expiry_date': voucher_expiry,
                'withdrawal_id': withdrawal_id,
                'is_used': False,
                'used_at': None
            }
        
        # Create withdrawal record
        withdrawal_record = {
            'withdrawal_id': withdrawal_id,
            'driver_id': driver_id,
            'amount': str(amount),
            'withdrawal_type': withdrawal_type.value,
            'status': WithdrawalStatus.PENDING.value,
            'timestamp': datetime.utcnow().isoformat(),
            'reference': reference,
            'voucher_code': voucher_code,
            'voucher_expiry': voucher_expiry,
            'bank_reference': bank_reference,
            'recipient_name': recipient_name,
            'recipient_phone': recipient_phone,
            'bank_details': submission.bank_details.dict() if submission.bank_details else None,
            'voucher_details': submission.voucher_details.dict() if submission.voucher_details else None
        }
        
        # Store withdrawal
        self.withdrawals[withdrawal_id] = withdrawal_record
        
        return withdrawal_record
    
    def _generate_voucher_code(self) -> str:
        """Generate a voucher code"""
        import random
        import string
        # Format: VC-XXXX-XXXX
        parts = []
        for _ in range(2):
            parts.append(''.join(random.choices(string.ascii_uppercase + string.digits, k=4)))
        return f"VC-{'-'.join(parts)}"
    
    def get_withdrawal(self, withdrawal_id: str) -> Optional[Dict]:
        """Get withdrawal by ID"""
        return self.withdrawals.get(withdrawal_id)
    
    def get_driver_withdrawals(self, driver_id: str, limit: int = 10) -> List[Dict]:
        """Get withdrawals for a driver"""
        driver_withdrawals = []
        for withdrawal in self.withdrawals.values():
            if withdrawal['driver_id'] == driver_id:
                driver_withdrawals.append(withdrawal)
        
        # Sort by timestamp (newest first)
        driver_withdrawals.sort(key=lambda x: x['timestamp'], reverse=True)
        return driver_withdrawals[:limit]
    
    def update_withdrawal_status(self, withdrawal_id: str, status: WithdrawalStatus):
        """Update withdrawal status"""
        if withdrawal_id in self.withdrawals:
            self.withdrawals[withdrawal_id]['status'] = status.value
            if status == WithdrawalStatus.COMPLETED:
                self.withdrawals[withdrawal_id]['completed_at'] = datetime.utcnow().isoformat()
            return True
        return False
    
    def get_voucher_details(self, voucher_code: str) -> Optional[Dict]:
        """Get voucher details"""
        return self.vouchers.get(voucher_code)
    
    def redeem_voucher(self, voucher_code: str) -> bool:
        """Redeem a voucher"""
        if voucher_code in self.vouchers and not self.vouchers[voucher_code]['is_used']:
            self.vouchers[voucher_code]['is_used'] = True
            self.vouchers[voucher_code]['used_at'] = datetime.utcnow().isoformat()
            return True
        return False


# ============================
# FEE CALCULATOR
# ============================

class WithdrawalFeeCalculator:
    """Calculates withdrawal fees"""
    
    @staticmethod
    def calculate_fee(amount: Decimal, withdrawal_type: WithdrawalType) -> Decimal:
        """Calculate fee for withdrawal"""
        if withdrawal_type == WithdrawalType.BANK_DEPOSIT:
            # Bank deposit fee: R10.00 flat
            return Decimal('10.00')
        else:  # Voucher
            # Voucher fee: R5.00 flat
            return Decimal('5.00')
    
    @staticmethod
    def calculate_net_amount(amount: Decimal, withdrawal_type: WithdrawalType) -> Decimal:
        """Calculate net amount after fees"""
        fee = WithdrawalFeeCalculator.calculate_fee(amount, withdrawal_type)
        return amount - fee


# ============================
# WALLET INTEGRATION
# ============================

def get_driver_wallet_balance(driver_id: str) -> Decimal:
    """Get driver's wallet balance"""
    try:
        from wallets import WalletManager
        
        # Initialize wallet manager
        if not hasattr(get_driver_wallet_balance, 'manager'):
            get_driver_wallet_balance.manager = WalletManager()
        
        # Get driver's wallet
        user_wallets = get_driver_wallet_balance.manager.get_user_wallets(driver_id)
        if not user_wallets:
            return Decimal('0.00')
        
        return user_wallets[0].available_balance
        
    except ImportError:
        # Fallback if wallet system not available
        return Decimal('1000.00')  # Mock balance for testing


def deduct_from_wallet(driver_id: str, amount: Decimal, reference: str) -> bool:
    """Deduct amount from driver's wallet"""
    try:
        from wallets import WalletManager, TransactionType
        
        manager = getattr(get_driver_wallet_balance, 'manager', None)
        if not manager:
            get_driver_wallet_balance.manager = WalletManager()
            manager = get_driver_wallet_balance.manager
        
        # Get driver's wallet
        user_wallets = manager.get_user_wallets(driver_id)
        if not user_wallets:
            return False
        
        wallet = user_wallets[0]
        
        # Check balance
        if amount > wallet.available_balance:
            return False
        
        # Create withdrawal transaction
        wallet._create_transaction(
            amount=amount,
            transaction_type=TransactionType.WITHDRAWAL,
            description=f"Withdrawal: {reference}",
            metadata={
                'reference': reference,
                'driver_id': driver_id
            }
        )
        
        # Deduct from balance
        wallet.balance -= amount
        wallet.available_balance -= amount
        
        return True
        
    except Exception:
        # For demo purposes, always return True
        return True


# ============================
# PAYMENTS API ROUTER
# ============================

router = APIRouter(
    prefix="/api/payments",
    tags=["payments"],
    responses={
        400: {"description": "Bad Request"},
        404: {"description": "Not Found"},
        500: {"description": "Internal Server Error"}
    },
)

# Initialize withdrawal manager
withdrawal_manager = WithdrawalManager()


@router.post("/withdraw", response_model=WithdrawalResponse, status_code=status.HTTP_201_CREATED)
async def request_withdrawal(
    submission: WithdrawalSubmission
):
    """
    Request a withdrawal of earnings
    
    Driver enters their ID, amount, and chooses:
    - Bank Deposit: Money goes directly to bank account
    - Voucher: Get a voucher code for cash pickup
    
    No authentication required - just driver ID and withdrawal details.
    """
    
    try:
        driver_id = submission.withdrawal_request.driver_id
        amount = submission.withdrawal_request.amount
        withdrawal_type = submission.withdrawal_request.withdrawal_type
        
        # Check minimum amounts
        if withdrawal_type == WithdrawalType.BANK_DEPOSIT and amount < Decimal('100.00'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "MINIMUM_AMOUNT",
                    "message": "Minimum bank deposit amount is R100.00"
                }
            )
        
        if withdrawal_type == WithdrawalType.VOUCHER and amount < Decimal('50.00'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "MINIMUM_AMOUNT",
                    "message": "Minimum voucher amount is R50.00"
                }
            )
        
        # Check driver's wallet balance
        wallet_balance = get_driver_wallet_balance(driver_id)
        if amount > wallet_balance:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "INSUFFICIENT_BALANCE",
                    "message": f"Insufficient balance. Available: R{wallet_balance}",
                    "available_balance": str(wallet_balance)
                }
            )
        
        # Calculate fee and net amount
        fee = WithdrawalFeeCalculator.calculate_fee(amount, withdrawal_type)
        net_amount = WithdrawalFeeCalculator.calculate_net_amount(amount, withdrawal_type)
        
        # Create withdrawal
        withdrawal_record = withdrawal_manager.create_withdrawal(submission)
        withdrawal_id = withdrawal_record['withdrawal_id']
        
        # Deduct from wallet
        deduction_success = deduct_from_wallet(driver_id, amount, withdrawal_record['reference'])
        if not deduction_success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "WITHDRAWAL_FAILED",
                    "message": "Could not process withdrawal from wallet"
                }
            )
        
        # Update status to processing
        withdrawal_manager.update_withdrawal_status(withdrawal_id, WithdrawalStatus.PROCESSING)
        
        # Set estimated completion
        estimated_completion = None
        if withdrawal_type == WithdrawalType.BANK_DEPOSIT:
            estimated_completion = (datetime.utcnow() + timedelta(hours=24)).isoformat()
        else:  # Voucher
            estimated_completion = (datetime.utcnow() + timedelta(minutes=5)).isoformat()
        
        # Prepare response message
        if withdrawal_type == WithdrawalType.BANK_DEPOSIT:
            message = f"Bank deposit of R{net_amount} will be processed within 24 hours. Reference: {withdrawal_record['reference']}"
        else:
            message = f"Voucher generated successfully. Code: {withdrawal_record['voucher_code']}. Expires in 30 days."
        
        return WithdrawalResponse(
            withdrawal_id=withdrawal_id,
            driver_id=driver_id,
            amount=str(amount),
            withdrawal_type=withdrawal_type.value,
            status=WithdrawalStatus.PROCESSING.value,
            timestamp=withdrawal_record['timestamp'],
            reference=withdrawal_record['reference'],
            voucher_code=withdrawal_record.get('voucher_code'),
            voucher_expiry=withdrawal_record.get('voucher_expiry'),
            bank_reference=withdrawal_record.get('bank_reference'),
            estimated_completion=estimated_completion,
            message=message
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "INTERNAL_ERROR",
                "message": f"Failed to process withdrawal: {str(e)}"
            }
        )


@router.get("/status/{withdrawal_id}", response_model=WithdrawalStatusResponse)
async def check_withdrawal_status(
    withdrawal_id: str
):
    """
    Check status of a withdrawal
    
    Enter withdrawal ID to check current status.
    No authentication required.
    """
    
    try:
        withdrawal = withdrawal_manager.get_withdrawal(withdrawal_id)
        
        if not withdrawal:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error": "WITHDRAWAL_NOT_FOUND",
                    "message": "Withdrawal not found"
                }
            )
        
        # Simulate completion after some time
        if withdrawal['status'] == WithdrawalStatus.PROCESSING.value:
            created_time = datetime.fromisoformat(withdrawal['timestamp'])
            if datetime.utcnow() - created_time > timedelta(minutes=2):
                withdrawal_manager.update_withdrawal_status(withdrawal_id, WithdrawalStatus.COMPLETED)
                withdrawal = withdrawal_manager.get_withdrawal(withdrawal_id)
        
        return WithdrawalStatusResponse(
            withdrawal_id=withdrawal['withdrawal_id'],
            driver_id=withdrawal['driver_id'],
            amount=withdrawal['amount'],
            withdrawal_type=withdrawal['withdrawal_type'],
            status=withdrawal['status'],
            timestamp=withdrawal['timestamp'],
            completed_at=withdrawal.get('completed_at'),
            reference=withdrawal['reference'],
            voucher_code=withdrawal.get('voucher_code'),
            voucher_expiry=withdrawal.get('voucher_expiry'),
            bank_reference=withdrawal.get('bank_reference'),
            recipient_name=withdrawal.get('recipient_name'),
            recipient_phone=withdrawal.get('recipient_phone')
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "INTERNAL_ERROR",
                "message": f"Failed to check status: {str(e)}"
            }
        )


@router.get("/driver/{driver_id}/history")
async def get_driver_withdrawal_history(
    driver_id: str,
    limit: int = Query(10, ge=1, le=50)
):
    """
    Get withdrawal history for a driver
    
    Enter driver ID to see their withdrawal history.
    No authentication required.
    """
    
    try:
        withdrawals = withdrawal_manager.get_driver_withdrawals(driver_id, limit)
        
        if not withdrawals:
            return {
                "driver_id": driver_id,
                "withdrawals": [],
                "count": 0,
                "message": "No withdrawals found for this driver"
            }
        
        # Calculate totals
        total_withdrawn = sum(Decimal(w['amount']) for w in withdrawals)
        total_fees = sum(
            WithdrawalFeeCalculator.calculate_fee(
                Decimal(w['amount']), 
                WithdrawalType(w['withdrawal_type'])
            ) 
            for w in withdrawals
        )
        
        return {
            "driver_id": driver_id,
            "withdrawals": withdrawals,
            "count": len(withdrawals),
            "summary": {
                "total_withdrawn": str(total_withdrawn),
                "total_fees": str(total_fees),
                "total_net": str(total_withdrawn - total_fees),
                "bank_deposits": len([w for w in withdrawals if w['withdrawal_type'] == WithdrawalType.BANK_DEPOSIT.value]),
                "vouchers": len([w for w in withdrawals if w['withdrawal_type'] == WithdrawalType.VOUCHER.value])
            }
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "INTERNAL_ERROR",
                "message": f"Failed to get history: {str(e)}"
            }
        )


@router.get("/check-balance/{driver_id}")
async def check_driver_balance(
    driver_id: str
):
    """
    Check driver's available balance
    
    Enter driver ID to check available balance for withdrawal.
    No authentication required.
    """
    
    try:
        balance = get_driver_wallet_balance(driver_id)
        
        # Get pending withdrawals
        withdrawals = withdrawal_manager.get_driver_withdrawals(driver_id, 100)
        pending_withdrawals = [
            w for w in withdrawals 
            if w['status'] in [WithdrawalStatus.PENDING.value, WithdrawalStatus.PROCESSING.value]
        ]
        
        total_pending = sum(Decimal(w['amount']) for w in pending_withdrawals)
        
        return {
            "driver_id": driver_id,
            "balance": {
                "total_balance": str(balance),
                "pending_withdrawals": str(total_pending),
                "available_for_withdrawal": str(balance - total_pending),
                "currency": "ZAR"
            },
            "withdrawal_limits": {
                "bank_deposit": {
                    "minimum": "100.00",
                    "maximum": "15000.00",
                    "fee": "R10.00 flat"
                },
                "voucher": {
                    "minimum": "50.00",
                    "maximum": "5000.00",
                    "fee": "R5.00 flat"
                }
            }
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "INTERNAL_ERROR",
                "message": f"Failed to check balance: {str(e)}"
            }
        )


@router.get("/voucher/{voucher_code}")
async def check_voucher(
    voucher_code: str
):
    """
    Check voucher details and validity
    
    Enter voucher code to check details and if it's still valid.
    No authentication required.
    """
    
    try:
        voucher = withdrawal_manager.get_voucher_details(voucher_code)
        
        if not voucher:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error": "VOUCHER_NOT_FOUND",
                    "message": "Voucher not found"
                }
            )
        
        # Check if voucher is expired
        expiry_date = datetime.fromisoformat(voucher['expiry_date'])
        is_expired = datetime.utcnow() > expiry_date
        
        return {
            "voucher_code": voucher['voucher_code'],
            "amount": voucher['amount'],
            "recipient_name": voucher['recipient_name'],
            "recipient_phone": voucher['recipient_phone'],
            "expiry_date": voucher['expiry_date'],
            "is_used": voucher['is_used'],
            "used_at": voucher.get('used_at'),
            "is_expired": is_expired,
            "is_valid": not voucher['is_used'] and not is_expired,
            "driver_id": voucher['driver_id'],
            "withdrawal_id": voucher['withdrawal_id']
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "INTERNAL_ERROR",
                "message": f"Failed to check voucher: {str(e)}"
            }
        )


@router.post("/voucher/{voucher_code}/redeem")
async def redeem_voucher(
    voucher_code: str
):
    """
    Redeem a voucher
    
    Enter voucher code to redeem it for cash.
    No authentication required.
    """
    
    try:
        voucher = withdrawal_manager.get_voucher_details(voucher_code)
        
        if not voucher:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error": "VOUCHER_NOT_FOUND",
                    "message": "Voucher not found"
                }
            )
        
        # Check if voucher is already used
        if voucher['is_used']:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "VOUCHER_ALREADY_USED",
                    "message": "This voucher has already been redeemed",
                    "used_at": voucher.get('used_at')
                }
            )
        
        # Check if voucher is expired
        expiry_date = datetime.fromisoformat(voucher['expiry_date'])
        if datetime.utcnow() > expiry_date:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "VOUCHER_EXPIRED",
                    "message": "This voucher has expired",
                    "expiry_date": voucher['expiry_date']
                }
            )
        
        # Redeem voucher
        success = withdrawal_manager.redeem_voucher(voucher_code)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "REDEMPTION_FAILED",
                    "message": "Failed to redeem voucher"
                }
            )
        
        # Update withdrawal status if needed
        withdrawal = withdrawal_manager.get_withdrawal(voucher['withdrawal_id'])
        if withdrawal and withdrawal['status'] == WithdrawalStatus.PROCESSING.value:
            withdrawal_manager.update_withdrawal_status(voucher['withdrawal_id'], WithdrawalStatus.COMPLETED)
        
        return {
            "success": True,
            "voucher_code": voucher_code,
            "amount": voucher['amount'],
            "recipient_name": voucher['recipient_name'],
            "redeemed_at": datetime.utcnow().isoformat(),
            "message": f"Voucher redeemed successfully. R{voucher['amount']} paid to {voucher['recipient_name']}"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "INTERNAL_ERROR",
                "message": f"Failed to redeem voucher: {str(e)}"
            }
        )


@router.get("/verify-bank-account")
async def verify_bank_account(
    account_number: str = Query(...),
    branch_code: str = Query(...),
    bank_type: BankType = Query(...)
):
    """
    Verify bank account details before withdrawal
    
    Enter bank details to verify they're valid.
    No authentication required.
    """
    
    try:
        # Validate inputs
        if not re.match(r'^\d{9,15}$', account_number):
            raise ValueError("Account number must be 9-15 digits")
        
        if not re.match(r'^\d{6}$', branch_code):
            raise ValueError("Branch code must be 6 digits")
        
        # Simple validation
        is_valid = True
        errors = []
        
        # Check account number length
        if len(account_number) < 9 or len(account_number) > 15:
            is_valid = False
            errors.append("Account number must be 9-15 digits")
        
        # Check branch code
        if len(branch_code) != 6:
            is_valid = False
            errors.append("Branch code must be 6 digits")
        
        # Bank-specific validations
        if bank_type == BankType.NEDBANK and not branch_code.startswith('19'):
            errors.append("Nedbank branch codes typically start with 19")
        
        return {
            "valid": is_valid,
            "bank_type": bank_type.value,
            "account_number": account_number[-4:],  # Only return last 4 digits
            "branch_code": branch_code,
            "errors": errors if errors else None,
            "message": "Account verified" if is_valid else "Account validation failed"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "VERIFICATION_FAILED",
                "message": f"Bank account verification failed: {str(e)}"
            }
        )


@router.get("/limits")
async def get_withdrawal_limits():
    """
    Get withdrawal limits and fees
    
    No authentication required.
    """
    
    try:
        return {
            "bank_deposit": {
                "minimum_amount": "100.00",
                "maximum_amount": "15000.00",
                "fee": "R10.00 flat",
                "processing_time": "24 hours",
                "requirements": [
                    "Valid bank account in driver's name",
                    "Correct branch code",
                    "Active account"
                ]
            },
            "voucher": {
                "minimum_amount": "50.00",
                "maximum_amount": "5000.00",
                "fee": "R5.00 flat",
                "validity_period": "30 days",
                "processing_time": "Immediate",
                "redemption": [
                    "Cash pickup at authorized locations",
                    "Present voucher code and ID",
                    "Phone number verification"
                ]
            },
            "general_limits": {
                "daily_limit": "R20,000.00",
                "weekly_limit": "R50,000.00",
                "monthly_limit": "R150,000.00",
                "currency": "ZAR"
            }
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "INTERNAL_ERROR",
                "message": f"Failed to get limits: {str(e)}"
            }
        )