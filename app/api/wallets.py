from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from app.db.supabase_client import supabase
import logging
import random
import string
from datetime import datetime

router = APIRouter()
logger = logging.getLogger(__name__)

# Helper functions
def generate_wallet_number() -> str:
    """Generate a unique wallet number"""
    # Generate 10-digit alphanumeric wallet number
    letters = string.ascii_uppercase
    digits = string.digits
    return ''.join(random.choices(letters + digits, k=10))

def get_current_timestamp():
    """Get current timestamp in ISO format"""
    return datetime.now().isoformat()

# ============= BASIC WALLET OPERATIONS =============

@router.get("/user/{user_id}")
async def get_user_wallet(user_id: str):
    """Get wallet information for a specific user"""
    try:
        logger.info(f"Getting wallet for user: {user_id}")
        
        # Check if user exists
        user_response = supabase.table("users").select("*").eq("id", user_id).execute()
        if not user_response.data:
            raise HTTPException(status_code=404, detail=f"User with ID {user_id} not found")
        
        user = user_response.data[0]
        
        # Try to find wallet
        wallet = None
        
        # Check if user has wallet_id field
        if user.get('wallet_id'):
            wallet_response = supabase.table("wallets").select("*").eq("id", user['wallet_id']).execute()
            if wallet_response.data:
                wallet = wallet_response.data[0]
        
        # Search wallet by user_id
        if not wallet:
            wallet_response = supabase.table("wallets").select("*").eq("user_id", user_id).execute()
            if wallet_response.data:
                wallet = wallet_response.data[0]
        
        if wallet:
            # Get recent transactions
            transactions_response = supabase.table("wallet_transactions")\
                .select("*")\
                .eq("wallet_id", wallet['id'])\
                .order("created_at", desc=True)\
                .limit(5)\
                .execute()
            
            transactions = transactions_response.data if transactions_response.data else []
            
            return {
                "success": True,
                "message": "Wallet found",
                "data": {
                    "user": {
                        "id": user.get("id"),
                        "name": user.get("name"),
                        "email": user.get("email"),
                        "phone": user.get("phone")
                    },
                    "wallet": wallet,
                    "recent_transactions": transactions,
                    "has_wallet": True
                }
            }
        else:
            return {
                "success": True,
                "message": "No wallet found for user",
                "data": {
                    "user": {
                        "id": user.get("id"),
                        "name": user.get("name"),
                        "email": user.get("email"),
                        "phone": user.get("phone")
                    },
                    "has_wallet": False,
                    "suggest_action": "create_wallet"
                }
            }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/check/{user_id}")
async def check_wallet(user_id: str):
    """Check if user has a wallet"""
    try:
        # Check user exists
        user_response = supabase.table("users").select("id").eq("id", user_id).execute()
        if not user_response.data:
            return {
                "success": False,
                "error": "User not found",
                "data": {
                    "has_user": False, 
                    "has_wallet": False
                }
            }
        
        # Check for wallet
        wallet_response = supabase.table("wallets")\
            .select("id, wallet_number, balance, currency")\
            .eq("user_id", user_id)\
            .execute()
        
        has_wallet = len(wallet_response.data) > 0
        
        return {
            "success": True,
            "data": {
                "has_user": True,
                "has_wallet": has_wallet,
                "wallet": wallet_response.data[0] if has_wallet else None
            }
        }
        
    except Exception as e:
        logger.error(f"Error: {e}")
        return {
            "success": False,
            "error": str(e),
            "data": {
                "has_user": False,
                "has_wallet": False
            }
        }

@router.post("/create/{user_id}")
async def create_wallet_for_user(user_id: str):
    """Create a new wallet for a user"""
    try:
        logger.info(f"Creating wallet for user: {user_id}")
        
        # Check if user exists
        user_response = supabase.table("users").select("*").eq("id", user_id).execute()
        if not user_response.data:
            raise HTTPException(status_code=404, detail=f"User with ID {user_id} not found")
        
        user = user_response.data[0]
        
        # Check if user already has a wallet
        existing_wallet_response = supabase.table("wallets")\
            .select("*")\
            .eq("user_id", user_id)\
            .execute()
        
        if existing_wallet_response.data:
            return {
                "success": False,
                "message": "User already has a wallet",
                "data": {
                    "wallet": existing_wallet_response.data[0],
                    "user": {
                        "id": user.get("id"),
                        "name": user.get("name")
                    }
                }
            }
        
        # Generate unique wallet number
        wallet_number = generate_wallet_number()
        
        # Create wallet data
        wallet_data = {
            "user_id": user_id,
            "balance": 0.00,
            "currency": "ZAR",
            "wallet_number": wallet_number,
            "status": "active",
            "created_at": get_current_timestamp(),
            "updated_at": get_current_timestamp()
        }
        
        # Insert wallet
        wallet_response = supabase.table("wallets").insert(wallet_data).execute()
        
        if not wallet_response.data:
            raise HTTPException(status_code=500, detail="Failed to create wallet")
        
        wallet = wallet_response.data[0]
        
        # Update user with wallet_id if column exists
        try:
            supabase.table("users")\
                .update({"wallet_id": wallet['id']})\
                .eq("id", user_id)\
                .execute()
        except:
            logger.warning("Could not update user with wallet_id (column may not exist)")
        
        return {
            "success": True,
            "message": "Wallet created successfully",
            "data": {
                "wallet": wallet,
                "user": {
                    "id": user.get("id"),
                    "name": user.get("name"),
                    "email": user.get("email")
                }
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating wallet: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/number/{wallet_number}")
async def get_wallet_by_number(wallet_number: str):
    """Get wallet information by wallet number"""
    try:
        logger.info(f"Getting wallet by number: {wallet_number}")
        
        wallet_response = supabase.table("wallets").select("*").eq("wallet_number", wallet_number).execute()
        
        if not wallet_response.data:
            raise HTTPException(status_code=404, detail=f"No wallet found with number {wallet_number}")
        
        wallet = wallet_response.data[0]
        
        # Get user information
        user_response = supabase.table("users").select("*").eq("id", wallet['user_id']).execute()
        user = user_response.data[0] if user_response.data else None
        
        return {
            "success": True,
            "message": "Wallet found",
            "data": {
                "wallet": wallet,
                "user": user
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/all")
async def get_all_wallets(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(10, ge=1, le=100, description="Items per page"),
    status: Optional[str] = Query(None, description="Filter by status (active, suspended, closed)")
):
    """Get all wallets with pagination"""
    try:
        # Calculate offset
        offset = (page - 1) * limit
        
        # Build query
        query = supabase.table("wallets").select("*")
        
        if status:
            query = query.eq("status", status)
        
        # Get wallets with pagination
        wallets_response = query\
            .order("created_at", desc=True)\
            .range(offset, offset + limit - 1)\
            .execute()
        
        wallets = wallets_response.data if wallets_response.data else []
        
        # Get total count
        count_query = supabase.table("wallets").select("id", count="exact")
        if status:
            count_query = count_query.eq("status", status)
        count_response = count_query.execute()
        
        total_count = count_response.count if count_response.count else 0
        
        # Get user information for each wallet
        for wallet in wallets:
            user_response = supabase.table("users")\
                .select("id, name, email")\
                .eq("id", wallet['user_id'])\
                .execute()
            wallet['user'] = user_response.data[0] if user_response.data else None
        
        return {
            "success": True,
            "message": f"Retrieved {len(wallets)} wallets",
            "data": {
                "wallets": wallets,
                "pagination": {
                    "page": page,
                    "limit": limit,
                    "total": total_count,
                    "total_pages": (total_count + limit - 1) // limit if total_count else 0,
                    "has_more": (offset + limit) < total_count
                }
            }
        }
        
    except Exception as e:
        logger.error(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============= TRANSACTION OPERATIONS =============

@router.get("/{wallet_id}/transactions")
async def get_wallet_transactions(
    wallet_id: str,
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(10, ge=1, le=100, description="Items per page"),
    transaction_type: Optional[str] = Query(None, description="Filter by transaction type"),
    status: Optional[str] = Query(None, description="Filter by status")
):
    """Get transactions for a wallet"""
    try:
        # First, check if wallet exists
        wallet_response = supabase.table("wallets").select("*").eq("id", wallet_id).execute()
        if not wallet_response.data:
            raise HTTPException(status_code=404, detail=f"Wallet with ID {wallet_id} not found")
        
        wallet = wallet_response.data[0]
        
        # Calculate offset
        offset = (page - 1) * limit
        
        # Build query
        query = supabase.table("wallet_transactions").select("*").eq("wallet_id", wallet_id)
        
        if transaction_type:
            query = query.eq("transaction_type", transaction_type)
        if status:
            query = query.eq("status", status)
        
        # Get transactions
        transactions_response = query\
            .order("created_at", desc=True)\
            .range(offset, offset + limit - 1)\
            .execute()
        
        transactions = transactions_response.data if transactions_response.data else []
        
        # Get total count
        count_query = supabase.table("wallet_transactions").select("id", count="exact").eq("wallet_id", wallet_id)
        if transaction_type:
            count_query = count_query.eq("transaction_type", transaction_type)
        if status:
            count_query = count_query.eq("status", status)
        count_response = count_query.execute()
        
        total_count = count_response.count if count_response.count else 0
        
        return {
            "success": True,
            "message": f"Retrieved {len(transactions)} transactions",
            "data": {
                "wallet": wallet,
                "transactions": transactions,
                "pagination": {
                    "page": page,
                    "limit": limit,
                    "total": total_count,
                    "total_pages": (total_count + limit - 1) // limit if total_count else 0,
                    "has_more": (offset + limit) < total_count
                }
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============= DEPOSIT/ADD MONEY =============

@router.post("/{wallet_id}/deposit")
async def deposit_to_wallet(
    wallet_id: str,
    amount: float = Query(..., gt=0, description="Amount to deposit"),
    currency: str = Query("ZAR", description="Currency code"),
    description: str = Query("Deposit to wallet", description="Transaction description"),
    reference: Optional[str] = Query(None, description="External reference ID")
):
    """Deposit money to a wallet"""
    try:
        logger.info(f"Depositing {amount} {currency} to wallet {wallet_id}")
        
        # Check if wallet exists
        wallet_response = supabase.table("wallets").select("*").eq("id", wallet_id).execute()
        if not wallet_response.data:
            raise HTTPException(status_code=404, detail=f"Wallet with ID {wallet_id} not found")
        
        wallet = wallet_response.data[0]
        
        # Check wallet status
        if wallet.get('status') != 'active':
            raise HTTPException(status_code=400, detail=f"Wallet is {wallet.get('status')}")
        
        # Update wallet balance
        current_balance = float(wallet['balance'])
        new_balance = current_balance + amount
        
        update_response = supabase.table("wallets")\
            .update({
                "balance": new_balance,
                "updated_at": get_current_timestamp(),
                "last_transaction_at": get_current_timestamp()
            })\
            .eq("id", wallet_id)\
            .execute()
        
        if not update_response.data:
            raise HTTPException(status_code=500, detail="Failed to update wallet balance")
        
        updated_wallet = update_response.data[0]
        
        # Create transaction record
        transaction_data = {
            "wallet_id": wallet_id,
            "transaction_type": "deposit",
            "amount": amount,
            "currency": currency,
            "reference": reference,
            "description": description,
            "status": "completed",
            "created_at": get_current_timestamp(),
            "metadata": {
                "source": "manual_deposit",
                "previous_balance": current_balance,
                "new_balance": new_balance
            }
        }
        
        transaction_response = supabase.table("wallet_transactions").insert(transaction_data).execute()
        
        transaction = transaction_response.data[0] if transaction_response.data else None
        
        return {
            "success": True,
            "message": f"Successfully deposited {amount} {currency} to wallet",
            "data": {
                "wallet": updated_wallet,
                "transaction": transaction,
                "deposit_details": {
                    "amount": amount,
                    "currency": currency,
                    "previous_balance": current_balance,
                    "new_balance": new_balance
                }
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing deposit: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
    
    
# ============= WITHDRAWAL =============

@router.post("/{wallet_id}/withdrawal/request")
async def request_withdrawal(
    wallet_id: str,
    amount: float = Query(..., gt=0, description="Amount to withdraw"),
    currency: str = Query("ZAR", description="Currency code"),
    description: str = Query("Withdrawal request", description="Transaction description"),
    bank_account_name: str = Query(..., description="Bank account holder name"),
    bank_account_number: str = Query(..., description="Bank account number"),
    bank_name: str = Query(..., description="Bank name"),
    bank_code: Optional[str] = Query(None, description="Bank code/SWIFT/IFSC")
):
    """Request a withdrawal from wallet"""
    try:
        logger.info(f"Withdrawal request: {amount} {currency} from wallet {wallet_id}")
        
        # Check if wallet exists
        wallet_response = supabase.table("wallets").select("*").eq("id", wallet_id).execute()
        if not wallet_response.data:
            raise HTTPException(status_code=404, detail=f"Wallet with ID {wallet_id} not found")
        
        wallet = wallet_response.data[0]
        
        # Check wallet status
        if wallet.get('status') != 'active':
            raise HTTPException(status_code=400, detail=f"Wallet is {wallet.get('status')}")
        
        # Check sufficient balance
        current_balance = float(wallet['balance'])
        if current_balance < amount:
            raise HTTPException(
                status_code=400, 
                detail=f"Insufficient balance. Available: {current_balance} {currency}, Requested: {amount} {currency}"
            )
        
        # Check minimum withdrawal amount (e.g., 50 ZAR)
        if amount < 50:
            raise HTTPException(
                status_code=400,
                detail="Minimum withdrawal amount is 50 ZAR"
            )
        
        # Create withdrawal transaction with 'pending' status
        transaction_data = {
            "wallet_id": wallet_id,
            "transaction_type": "withdrawal",
            "amount": amount,
            "currency": currency,
            "reference": f"WDR_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "description": description,
            "status": "pending",
            "created_at": get_current_timestamp(),
            "metadata": {
                "bank_details": {
                    "account_name": bank_account_name,
                    "account_number": bank_account_number,
                    "bank_name": bank_name,
                    "bank_code": bank_code
                },
                "withdrawal_type": "bank_transfer",
                "requested_at": get_current_timestamp(),
                "previous_balance": current_balance
            }
        }
        
        transaction_response = supabase.table("wallet_transactions").insert(transaction_data).execute()
        
        if not transaction_response.data:
            raise HTTPException(status_code=500, detail="Failed to create withdrawal request")
        
        transaction = transaction_response.data[0]
        
        # Note: We DON'T deduct balance yet - balance will be deducted when withdrawal is approved/completed
        # This prevents users from spending money that's being withdrawn
        
        return {
            "success": True,
            "message": "Withdrawal request submitted successfully",
            "data": {
                "transaction": transaction,
                "wallet": wallet,
                "withdrawal_details": {
                    "amount": amount,
                    "currency": currency,
                    "current_balance": current_balance,
                    "bank_account": bank_account_name,
                    "reference": transaction['reference'],
                    "status": "pending",
                    "estimated_processing": "1-3 business days"
                }
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing withdrawal request: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.post("/{wallet_id}/withdrawal/{transaction_id}/approve")
async def approve_withdrawal(wallet_id: str, transaction_id: str):
    """Approve and process a withdrawal request"""
    try:
        logger.info(f"Approving withdrawal {transaction_id} for wallet {wallet_id}")
        
        # Check if transaction exists and is a pending withdrawal
        transaction_response = supabase.table("wallet_transactions")\
            .select("*")\
            .eq("id", transaction_id)\
            .eq("wallet_id", wallet_id)\
            .eq("transaction_type", "withdrawal")\
            .eq("status", "pending")\
            .execute()
        
        if not transaction_response.data:
            raise HTTPException(
                status_code=404, 
                detail=f"Pending withdrawal transaction not found or already processed"
            )
        
        transaction = transaction_response.data[0]
        amount = float(transaction['amount'])
        
        # Check wallet
        wallet_response = supabase.table("wallets").select("*").eq("id", wallet_id).execute()
        if not wallet_response.data:
            raise HTTPException(status_code=404, detail=f"Wallet not found")
        
        wallet = wallet_response.data[0]
        current_balance = float(wallet['balance'])
        
        # Check sufficient balance (again, in case balance changed)
        if current_balance < amount:
            raise HTTPException(
                status_code=400, 
                detail=f"Insufficient balance. Available: {current_balance}, Withdrawal amount: {amount}"
            )
        
        # Deduct from wallet balance
        new_balance = current_balance - amount
        
        update_response = supabase.table("wallets")\
            .update({
                "balance": new_balance,
                "updated_at": get_current_timestamp(),
                "last_transaction_at": get_current_timestamp()
            })\
            .eq("id", wallet_id)\
            .execute()
        
        if not update_response.data:
            raise HTTPException(status_code=500, detail="Failed to update wallet balance")
        
        updated_wallet = update_response.data[0]
        
        # Update transaction status to completed
        transaction_update_response = supabase.table("wallet_transactions")\
            .update({
                "status": "completed",
                "metadata": {
                    **transaction.get('metadata', {}),
                    "approved_at": get_current_timestamp(),
                    "previous_balance": current_balance,
                    "new_balance": new_balance,
                    "processed_by": "system"
                }
            })\
            .eq("id", transaction_id)\
            .execute()
        
        updated_transaction = transaction_update_response.data[0] if transaction_update_response.data else transaction
        
        # TODO: In production, here you would:
        # 1. Call Silicon Enterprise API to process the actual bank transfer
        # 2. Update transaction with Silicon Enterprise reference ID
        # 3. Set up webhook to receive status updates
        
        return {
            "success": True,
            "message": "Withdrawal approved and processed successfully",
            "data": {
                "transaction": updated_transaction,
                "wallet": updated_wallet,
                "withdrawal_details": {
                    "amount": amount,
                    "currency": transaction['currency'],
                    "previous_balance": current_balance,
                    "new_balance": new_balance,
                    "status": "completed",
                    "processed_at": get_current_timestamp()
                }
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error approving withdrawal: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.post("/{wallet_id}/withdrawal/{transaction_id}/cancel")
async def cancel_withdrawal(wallet_id: str, transaction_id: str):
    """Cancel a pending withdrawal request"""
    try:
        logger.info(f"Cancelling withdrawal {transaction_id} for wallet {wallet_id}")
        
        # Check if transaction exists and is a pending withdrawal
        transaction_response = supabase.table("wallet_transactions")\
            .select("*")\
            .eq("id", transaction_id)\
            .eq("wallet_id", wallet_id)\
            .eq("transaction_type", "withdrawal")\
            .eq("status", "pending")\
            .execute()
        
        if not transaction_response.data:
            raise HTTPException(
                status_code=404, 
                detail=f"Pending withdrawal transaction not found or already processed"
            )
        
        transaction = transaction_response.data[0]
        
        # Update transaction status to cancelled
        transaction_update_response = supabase.table("wallet_transactions")\
            .update({
                "status": "cancelled",
                "metadata": {
                    **transaction.get('metadata', {}),
                    "cancelled_at": get_current_timestamp(),
                    "cancelled_by": "user"
                }
            })\
            .eq("id", transaction_id)\
            .execute()
        
        updated_transaction = transaction_update_response.data[0] if transaction_update_response.data else transaction
        
        return {
            "success": True,
            "message": "Withdrawal cancelled successfully",
            "data": {
                "transaction": updated_transaction,
                "note": "Balance was not deducted since withdrawal was still pending"
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cancelling withdrawal: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/{wallet_id}/withdrawals")
async def get_withdrawal_history(
    wallet_id: str,
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(10, ge=1, le=100, description="Items per page"),
    status: Optional[str] = Query(None, description="Filter by status (pending, completed, failed, cancelled)")
):
    """Get withdrawal history for a wallet"""
    try:
        # Check if wallet exists
        wallet_response = supabase.table("wallets").select("*").eq("id", wallet_id).execute()
        if not wallet_response.data:
            raise HTTPException(status_code=404, detail=f"Wallet with ID {wallet_id} not found")
        
        wallet = wallet_response.data[0]
        
        # Calculate offset
        offset = (page - 1) * limit
        
        # Build query for withdrawals only
        query = supabase.table("wallet_transactions")\
            .select("*")\
            .eq("wallet_id", wallet_id)\
            .eq("transaction_type", "withdrawal")
        
        if status:
            query = query.eq("status", status)
        
        # Get withdrawals
        withdrawals_response = query\
            .order("created_at", desc=True)\
            .range(offset, offset + limit - 1)\
            .execute()
        
        withdrawals = withdrawals_response.data if withdrawals_response.data else []
        
        # Get total count
        count_query = supabase.table("wallet_transactions")\
            .select("id", count="exact")\
            .eq("wallet_id", wallet_id)\
            .eq("transaction_type", "withdrawal")
        
        if status:
            count_query = count_query.eq("status", status)
        
        count_response = count_query.execute()
        total_count = count_response.count if count_response.count else 0
        
        # Calculate statistics
        completed_withdrawals = supabase.table("wallet_transactions")\
            .select("amount")\
            .eq("wallet_id", wallet_id)\
            .eq("transaction_type", "withdrawal")\
            .eq("status", "completed")\
            .execute()
        
        total_withdrawn = sum(float(tx['amount']) for tx in completed_withdrawals.data) if completed_withdrawals.data else 0
        
        pending_withdrawals = supabase.table("wallet_transactions")\
            .select("amount")\
            .eq("wallet_id", wallet_id)\
            .eq("transaction_type", "withdrawal")\
            .eq("status", "pending")\
            .execute()
        
        pending_amount = sum(float(tx['amount']) for tx in pending_withdrawals.data) if pending_withdrawals.data else 0
        
        return {
            "success": True,
            "message": f"Retrieved {len(withdrawals)} withdrawals",
            "data": {
                "wallet": wallet,
                "withdrawals": withdrawals,
                "statistics": {
                    "total_withdrawals": total_count,
                    "total_amount_withdrawn": total_withdrawn,
                    "pending_withdrawals": len(pending_withdrawals.data) if pending_withdrawals.data else 0,
                    "pending_amount": pending_amount,
                    "available_balance": wallet['balance']
                },
                "pagination": {
                    "page": page,
                    "limit": limit,
                    "total": total_count,
                    "total_pages": (total_count + limit - 1) // limit if total_count else 0,
                    "has_more": (offset + limit) < total_count
                }
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting withdrawal history: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============= QUICK WITHDRAWAL (Simulated Silicon Enterprise Integration) =============

@router.post("/{wallet_id}/withdraw/quick")
async def quick_withdraw(
    wallet_id: str,
    amount: float = Query(..., gt=0, description="Amount to withdraw"),
    currency: str = Query("ZAR", description="Currency code"),
    description: Optional[str] = Query("Quick withdrawal", description="Transaction description")
):
    """Quick withdrawal - simulates Silicon Enterprise integration"""
    try:
        logger.info(f"Quick withdrawal: {amount} {currency} from wallet {wallet_id}")
        
        # Check if wallet exists
        wallet_response = supabase.table("wallets").select("*").eq("id", wallet_id).execute()
        if not wallet_response.data:
            raise HTTPException(status_code=404, detail=f"Wallet with ID {wallet_id} not found")
        
        wallet = wallet_response.data[0]
        
        # Check wallet status
        if wallet.get('status') != 'active':
            raise HTTPException(status_code=400, detail=f"Wallet is {wallet.get('status')}")
        
        # Check sufficient balance
        current_balance = float(wallet['balance'])
        if current_balance < amount:
            raise HTTPException(
                status_code=400, 
                detail=f"Insufficient balance. Available: {current_balance} {currency}, Requested: {amount} {currency}"
            )
        
        # Check minimum withdrawal amount
        if amount < 50:
            raise HTTPException(
                status_code=400,
                detail="Minimum withdrawal amount is 50 ZAR"
            )
        
        # Simulate Silicon Enterprise API call
        logger.info(f"Simulating Silicon Enterprise API call for withdrawal...")
        
        # Generate Silicon Enterprise reference
        silicon_ref = f"SE_{datetime.now().strftime('%Y%m%d')}_{random.randint(1000, 9999)}"
        
        # Create transaction with 'completed' status (simulating instant processing)
        transaction_data = {
            "wallet_id": wallet_id,
            "transaction_type": "withdrawal",
            "amount": amount,
            "currency": currency,
            "reference": silicon_ref,
            "description": description or "Quick withdrawal via Silicon Enterprise",
            "status": "completed",
            "created_at": get_current_timestamp(),
            "metadata": {
                "provider": "silicon_enterprise",
                "provider_reference": silicon_ref,
                "withdrawal_type": "instant",
                "processing_time": "instant",
                "previous_balance": current_balance,
                "provider_response": {
                    "status": "success",
                    "message": "Transfer initiated successfully",
                    "estimated_arrival": "1-2 business days"
                }
            }
        }
        
        # Deduct from wallet balance
        new_balance = current_balance - amount
        
        update_response = supabase.table("wallets")\
            .update({
                "balance": new_balance,
                "updated_at": get_current_timestamp(),
                "last_transaction_at": get_current_timestamp()
            })\
            .eq("id", wallet_id)\
            .execute()
        
        if not update_response.data:
            raise HTTPException(status_code=500, detail="Failed to update wallet balance")
        
        updated_wallet = update_response.data[0]
        
        # Create transaction record
        transaction_response = supabase.table("wallet_transactions").insert(transaction_data).execute()
        
        transaction = transaction_response.data[0] if transaction_response.data else None
        
        # Simulate webhook response from Silicon Enterprise
        logger.info(f"Simulating Silicon Enterprise webhook for completed transfer...")
        
        return {
            "success": True,
            "message": "Withdrawal processed successfully via Silicon Enterprise",
            "data": {
                "wallet": updated_wallet,
                "transaction": transaction,
                "withdrawal_details": {
                    "amount": amount,
                    "currency": currency,
                    "previous_balance": current_balance,
                    "new_balance": new_balance,
                    "provider": "Silicon Enterprise",
                    "provider_reference": silicon_ref,
                    "status": "completed",
                    "estimated_arrival": "1-2 business days",
                    "processing_fee": "0.00",  # Example: no fee
                    "net_amount": amount
                }
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing quick withdrawal: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")    


# ============= FUEL VOUCHERS =============

@router.post("/{wallet_id}/voucher/request")
async def request_fuel_voucher(
    wallet_id: str,
    amount: float = Query(..., gt=0, description="Voucher amount"),
    currency: str = Query("ZAR", description="Currency code"),
    description: str = Query("Fuel voucher", description="Transaction description"),
    station_name: str = Query(..., description="Fuel station name"),
    station_location: str = Query(..., description="Fuel station location"),
    vehicle_registration: Optional[str] = Query(None, description="Vehicle registration number"),
    #metadata: Optional[Dict[str, Any]] = Body(None, description="Additional metadata")
):
    """Request a fuel voucher instead of cash withdrawal"""
    try:
        logger.info(f"Fuel voucher request: {amount} {currency} from wallet {wallet_id}")
        
        # Check if wallet exists
        wallet_response = supabase.table("wallets").select("*").eq("id", wallet_id).execute()
        if not wallet_response.data:
            raise HTTPException(status_code=404, detail=f"Wallet with ID {wallet_id} not found")
        
        wallet = wallet_response.data[0]
        
        # Check wallet status
        if wallet.get('status') != 'active':
            raise HTTPException(status_code=400, detail=f"Wallet is {wallet.get('status')}")
        
        # Check sufficient balance
        current_balance = float(wallet['balance'])
        if current_balance < amount:
            raise HTTPException(
                status_code=400, 
                detail=f"Insufficient balance. Available: {current_balance} {currency}, Requested: {amount} {currency}"
            )
        
        # Check minimum voucher amount (e.g., 100 ZAR)
        if amount < 100:
            raise HTTPException(
                status_code=400,
                detail="Minimum fuel voucher amount is 100 ZAR"
            )
        
        # Check maximum voucher amount (e.g., 5000 ZAR)
        if amount > 5000:
            raise HTTPException(
                status_code=400,
                detail="Maximum fuel voucher amount is 5,000 ZAR"
            )
        
        # Generate unique voucher code
        voucher_code = f"FV{random.randint(100000, 999999)}"
        
        # Generate PIN for voucher (4-digit)
        voucher_pin = str(random.randint(1000, 9999))
        
        # Create voucher transaction with 'pending' status
        transaction_data = {
            "wallet_id": wallet_id,
            "transaction_type": "withdrawal",  # Still a withdrawal type
            "amount": amount,
            "currency": currency,
            "reference": voucher_code,
            "description": description,
            "status": "pending",
            "created_at": get_current_timestamp(),
            "metadata": {
                "voucher_type": "fuel",
                "voucher_code": voucher_code,
                "voucher_pin": voucher_pin,  # In production, this should be encrypted/hashed
                "station_name": station_name,
                "station_location": station_location,
                "vehicle_registration": vehicle_registration,
                "expires_at": (datetime.now().replace(hour=23, minute=59, second=59) 
                              .strftime('%Y-%m-%dT%H:%M:%S')),
                "requested_at": get_current_timestamp(),
                "previous_balance": current_balance,
                "provider": "fuel_advance_engine",
                "provider_status": "generating",
                #**(metadata or {})
            }
        }
        
        transaction_response = supabase.table("wallet_transactions").insert(transaction_data).execute()
        
        if not transaction_response.data:
            raise HTTPException(status_code=500, detail="Failed to create fuel voucher request")
        
        transaction = transaction_response.data[0]
        
        # Simulate fuel-advance engine API call
        logger.info(f"Simulating fuel-advance engine API call for voucher {voucher_code}...")
        
        # In production, you would:
        # 1. Call fuel-advance engine API
        # 2. Get actual voucher details from their system
        # 3. Update transaction with real voucher data
        
        return {
            "success": True,
            "message": "Fuel voucher request submitted successfully",
            "data": {
                "transaction": transaction,
                "wallet": wallet,
                "voucher_details": {
                    "amount": amount,
                    "currency": currency,
                    "voucher_code": voucher_code,
                    "station_name": station_name,
                    "station_location": station_location,
                    "expires_at": transaction_data['metadata']['expires_at'],
                    "status": "generating",
                    "estimated_ready": "Within 5 minutes"
                },
                "note": "Voucher will be available shortly. Check voucher status for PIN."
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing fuel voucher request: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.post("/{wallet_id}/voucher/{transaction_id}/generate")
async def generate_fuel_voucher(wallet_id: str, transaction_id: str):
    """Generate and activate a fuel voucher (simulating fuel-advance engine)"""
    try:
        logger.info(f"Generating fuel voucher for transaction {transaction_id}")
        
        # Check if transaction exists and is a pending voucher withdrawal
        transaction_response = supabase.table("wallet_transactions")\
            .select("*")\
            .eq("id", transaction_id)\
            .eq("wallet_id", wallet_id)\
            .eq("transaction_type", "withdrawal")\
            .eq("status", "pending")\
            .execute()
        
        if not transaction_response.data:
            raise HTTPException(
                status_code=404, 
                detail=f"Pending voucher transaction not found or already processed"
            )
        
        transaction = transaction_response.data[0]
        
        # Check if this is a voucher transaction
        metadata = transaction.get('metadata', {})
        if metadata.get('voucher_type') != 'fuel':
            raise HTTPException(
                status_code=400,
                detail="Transaction is not a fuel voucher request"
            )
        
        amount = float(transaction['amount'])
        
        # Check wallet
        wallet_response = supabase.table("wallets").select("*").eq("id", wallet_id).execute()
        if not wallet_response.data:
            raise HTTPException(status_code=404, detail=f"Wallet not found")
        
        wallet = wallet_response.data[0]
        current_balance = float(wallet['balance'])
        
        # Check sufficient balance
        if current_balance < amount:
            raise HTTPException(
                status_code=400, 
                detail=f"Insufficient balance. Available: {current_balance}, Voucher amount: {amount}"
            )
        
        # Deduct from wallet balance
        new_balance = current_balance - amount
        
        update_response = supabase.table("wallets")\
            .update({
                "balance": new_balance,
                "updated_at": get_current_timestamp(),
                "last_transaction_at": get_current_timestamp()
            })\
            .eq("id", wallet_id)\
            .execute()
        
        if not update_response.data:
            raise HTTPException(status_code=500, detail="Failed to update wallet balance")
        
        updated_wallet = update_response.data[0]
        
        # Generate QR code data (simulated)
        voucher_code = metadata.get('voucher_code', f"FV{random.randint(100000, 999999)}")
        voucher_pin = metadata.get('voucher_pin', str(random.randint(1000, 9999)))
        
        # Simulate fuel-advance engine response
        fuel_advance_response = {
            "voucher_id": voucher_code,
            "pin": voucher_pin,
            "qr_code": f"https://api.qrserver.com/v1/create-qr-code/?size=150x150&data={voucher_code}",
            "barcode": voucher_code,
            "generated_at": get_current_timestamp(),
            "valid_until": metadata.get('expires_at'),
            "station_codes": ["STN001", "STN045", "STN128"],  # Valid station codes
            "terms": "Valid for fuel purchase only. Non-transferable.",
            "engine_reference": f"FE{random.randint(1000000, 9999999)}"
        }
        
        # Update transaction status to completed with voucher details
        transaction_update_response = supabase.table("wallet_transactions")\
            .update({
                "status": "completed",
                "metadata": {
                    **metadata,
                    "generated_at": get_current_timestamp(),
                    "previous_balance": current_balance,
                    "new_balance": new_balance,
                    "provider": "fuel_advance_engine",
                    "provider_status": "active",
                    "provider_reference": fuel_advance_response['engine_reference'],
                    "voucher_details": {
                        "voucher_id": fuel_advance_response['voucher_id'],
                        "pin": fuel_advance_response['pin'],
                        "qr_code": fuel_advance_response['qr_code'],
                        "barcode": fuel_advance_response['barcode'],
                        "valid_stations": fuel_advance_response['station_codes'],
                        "terms": fuel_advance_response['terms'],
                        "valid_until": fuel_advance_response['valid_until']
                    }
                }
            })\
            .eq("id", transaction_id)\
            .execute()
        
        updated_transaction = transaction_update_response.data[0] if transaction_update_response.data else transaction
        
        return {
            "success": True,
            "message": "Fuel voucher generated successfully",
            "data": {
                "transaction": updated_transaction,
                "wallet": updated_wallet,
                "voucher": {
                    **fuel_advance_response,
                    "amount": amount,
                    "currency": transaction['currency'],
                    "station_name": metadata.get('station_name'),
                    "station_location": metadata.get('station_location'),
                    "vehicle_registration": metadata.get('vehicle_registration'),
                    "instructions": [
                        "Present this voucher at any participating fuel station",
                        "Provide voucher code and PIN to attendant",
                        "Voucher is valid for fuel purchase only",
                        f"Expires: {fuel_advance_response['valid_until']}"
                    ]
                }
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating fuel voucher: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/{wallet_id}/vouchers")
async def get_fuel_vouchers(
    wallet_id: str,
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(10, ge=1, le=100, description="Items per page"),
    status: Optional[str] = Query(None, description="Filter by status")
):
    """Get fuel voucher history for a wallet"""
    try:
        # Check if wallet exists
        wallet_response = supabase.table("wallets").select("*").eq("id", wallet_id).execute()
        if not wallet_response.data:
            raise HTTPException(status_code=404, detail=f"Wallet with ID {wallet_id} not found")
        
        wallet = wallet_response.data[0]
        
        # Calculate offset
        offset = (page - 1) * limit
        
        # Build query for voucher transactions only
        query = supabase.table("wallet_transactions")\
            .select("*")\
            .eq("wallet_id", wallet_id)\
            .eq("transaction_type", "withdrawal")
        
        if status:
            query = query.eq("status", status)
        
        # Get all withdrawals first
        withdrawals_response = query\
            .order("created_at", desc=True)\
            .execute()
        
        # Filter for vouchers only (based on metadata)
        vouchers = []
        for tx in withdrawals_response.data:
            metadata = tx.get('metadata', {})
            if metadata.get('voucher_type') == 'fuel':
                vouchers.append(tx)
        
        # Apply pagination
        total_vouchers = len(vouchers)
        paginated_vouchers = vouchers[offset:offset + limit]
        
        # Calculate statistics
        active_vouchers = []
        expired_vouchers = []
        total_voucher_amount = 0
        
        for voucher in vouchers:
            amount = float(voucher['amount'])
            total_voucher_amount += amount
            
            metadata = voucher.get('metadata', {})
            voucher_details = metadata.get('voucher_details', {})
            
            if voucher['status'] == 'completed' and voucher_details:
                expires_at = voucher_details.get('valid_until')
                if expires_at:
                    expires_date = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
                    if expires_date > datetime.now():
                        active_vouchers.append(voucher)
                    else:
                        expired_vouchers.append(voucher)
        
        return {
            "success": True,
            "message": f"Retrieved {len(paginated_vouchers)} fuel vouchers",
            "data": {
                "wallet": wallet,
                "vouchers": paginated_vouchers,
                "statistics": {
                    "total_vouchers": total_vouchers,
                    "total_amount": total_voucher_amount,
                    "active_vouchers": len(active_vouchers),
                    "expired_vouchers": len(expired_vouchers),
                    "available_balance": wallet['balance']
                },
                "pagination": {
                    "page": page,
                    "limit": limit,
                    "total": total_vouchers,
                    "total_pages": (total_vouchers + limit - 1) // limit if total_vouchers else 0,
                    "has_more": (offset + limit) < total_vouchers
                }
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting fuel vouchers: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/voucher/{voucher_code}")
async def get_voucher_details(voucher_code: str):
    """Get details of a specific fuel voucher"""
    try:
        logger.info(f"Getting details for voucher: {voucher_code}")
        
        # Find transaction with this voucher code
        transaction_response = supabase.table("wallet_transactions")\
            .select("*")\
            .eq("reference", voucher_code)\
            .execute()
        
        if not transaction_response.data:
            raise HTTPException(status_code=404, detail=f"Voucher {voucher_code} not found")
        
        transaction = transaction_response.data[0]
        
        # Check if it's a fuel voucher
        metadata = transaction.get('metadata', {})
        if metadata.get('voucher_type') != 'fuel':
            raise HTTPException(
                status_code=400,
                detail="This is not a fuel voucher"
            )
        
        # Get wallet info
        wallet_response = supabase.table("wallets").select("*").eq("id", transaction['wallet_id']).execute()
        wallet = wallet_response.data[0] if wallet_response.data else None
        
        # Get user info
        user = None
        if wallet:
            user_response = supabase.table("users").select("*").eq("id", wallet['user_id']).execute()
            user = user_response.data[0] if user_response.data else None
        
        # Check if voucher is expired
        is_expired = False
        expiry_date = None
        voucher_details = metadata.get('voucher_details', {})
        
        if voucher_details and 'valid_until' in voucher_details:
            expiry_date = voucher_details['valid_until']
            expires_date = datetime.fromisoformat(expiry_date.replace('Z', '+00:00'))
            is_expired = expires_date < datetime.now()
        
        # Determine voucher status
        voucher_status = transaction['status']
        if voucher_status == 'completed' and is_expired:
            voucher_status = 'expired'
        
        return {
            "success": True,
            "message": "Voucher details retrieved",
            "data": {
                "voucher": {
                    "code": voucher_code,
                    "amount": transaction['amount'],
                    "currency": transaction['currency'],
                    "status": voucher_status,
                    "created_at": transaction['created_at'],
                    "expires_at": expiry_date,
                    "is_expired": is_expired,
                    "details": voucher_details,
                    "metadata": {
                        k: v for k, v in metadata.items() 
                        if k not in ['voucher_pin', 'pin']  # Don't expose PIN in public endpoint
                    }
                },
                "user": {
                    "id": user.get('id') if user else None,
                    "name": user.get('name') if user else None
                } if user else None,
                "wallet": wallet
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting voucher details: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/voucher/{voucher_code}/redeem")
async def redeem_fuel_voucher(
    voucher_code: str,
    station_code: str = Query(..., description="Fuel station code"),
    amount_used: Optional[float] = Query(None, description="Amount used (if partial redemption)"),
    attendant_id: Optional[str] = Query(None, description="Attendant/employee ID")
):
    """Redeem a fuel voucher at a station"""
    try:
        logger.info(f"Redeeming voucher {voucher_code} at station {station_code}")
        
        # Find transaction with this voucher code
        transaction_response = supabase.table("wallet_transactions")\
            .select("*")\
            .eq("reference", voucher_code)\
            .eq("status", "completed")\
            .execute()
        
        if not transaction_response.data:
            raise HTTPException(status_code=404, detail=f"Voucher {voucher_code} not found or not active")
        
        transaction = transaction_response.data[0]
        
        # Check if it's a fuel voucher
        metadata = transaction.get('metadata', {})
        if metadata.get('voucher_type') != 'fuel':
            raise HTTPException(
                status_code=400,
                detail="This is not a fuel voucher"
            )
        
        # Check if voucher is already redeemed
        voucher_details = metadata.get('voucher_details', {})
        if voucher_details.get('redeemed'):
            raise HTTPException(
                status_code=400,
                detail="Voucher has already been redeemed"
            )
        
        # Check if voucher is expired
        if voucher_details.get('valid_until'):
            expiry_date = datetime.fromisoformat(voucher_details['valid_until'].replace('Z', '+00:00'))
            if expiry_date < datetime.now():
                raise HTTPException(
                    status_code=400,
                    detail="Voucher has expired"
                )
        
        # Check if station is valid
        valid_stations = voucher_details.get('valid_stations', [])
        if valid_stations and station_code not in valid_stations:
            raise HTTPException(
                status_code=400,
                detail=f"Voucher not valid at station {station_code}. Valid stations: {', '.join(valid_stations)}"
            )
        
        # Calculate amount used
        voucher_amount = float(transaction['amount'])
        amount_to_use = amount_used if amount_used else voucher_amount
        
        if amount_to_use > voucher_amount:
            raise HTTPException(
                status_code=400,
                detail=f"Amount used ({amount_to_use}) exceeds voucher amount ({voucher_amount})"
            )
        
        # Update transaction with redemption details
        redemption_data = {
            "redeemed_at": get_current_timestamp(),
            "station_code": station_code,
            "amount_used": amount_to_use,
            "attendant_id": attendant_id,
            "remaining_balance": voucher_amount - amount_to_use if amount_used else 0,
            "redemption_reference": f"RED_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        }
        
        # Update metadata
        updated_metadata = {
            **metadata,
            "voucher_details": {
                **voucher_details,
                "redeemed": True,
                "redemption_details": redemption_data
            }
        }
        
        transaction_update_response = supabase.table("wallet_transactions")\
            .update({
                "metadata": updated_metadata
            })\
            .eq("id", transaction['id'])\
            .execute()
        
        updated_transaction = transaction_update_response.data[0] if transaction_update_response.data else transaction
        
        # If partial redemption, create a new transaction for remaining balance
        remaining_balance = voucher_amount - amount_to_use
        if amount_used and remaining_balance > 0:
            # Create new voucher for remaining balance
            new_voucher_code = f"FV{random.randint(100000, 999999)}"
            
            new_transaction_data = {
                "wallet_id": transaction['wallet_id'],
                "transaction_type": "withdrawal",
                "amount": remaining_balance,
                "currency": transaction['currency'],
                "reference": new_voucher_code,
                "description": f"Partial redemption remaining from {voucher_code}",
                "status": "completed",
                "created_at": get_current_timestamp(),
                "metadata": {
                    "voucher_type": "fuel",
                    "voucher_code": new_voucher_code,
                    "voucher_pin": str(random.randint(1000, 9999)),
                    "station_name": metadata.get('station_name'),
                    "station_location": metadata.get('station_location'),
                    "vehicle_registration": metadata.get('vehicle_registration'),
                    "expires_at": voucher_details.get('valid_until'),
                    "previous_balance": 0,
                    "provider": "fuel_advance_engine",
                    "provider_status": "active",
                    "voucher_details": {
                        "voucher_id": new_voucher_code,
                        "pin": str(random.randint(1000, 9999)),
                        "qr_code": f"https://api.qrserver.com/v1/create-qr-code/?size=150x150&data={new_voucher_code}",
                        "barcode": new_voucher_code,
                        "valid_stations": valid_stations,
                        "terms": "Valid for fuel purchase only. Non-transferable.",
                        "valid_until": voucher_details.get('valid_until')
                    }
                }
            }
            
            supabase.table("wallet_transactions").insert(new_transaction_data).execute()
        
        return {
            "success": True,
            "message": f"Voucher redeemed successfully for {amount_to_use} {transaction['currency']}",
            "data": {
                "redemption": redemption_data,
                "voucher": {
                    "code": voucher_code,
                    "original_amount": voucher_amount,
                    "amount_used": amount_to_use,
                    "remaining_balance": remaining_balance if amount_used else 0,
                    "new_voucher_code": new_voucher_code if amount_used and remaining_balance > 0 else None
                },
                "receipt": {
                    "station": station_code,
                    "date_time": redemption_data['redeemed_at'],
                    "reference": redemption_data['redemption_reference'],
                    "attendant": attendant_id
                }
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error redeeming voucher: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


 
# ============= TEST ENDPOINTS =============

@router.get("/test/connection")
async def test_wallet_connection():
    """Test wallet database connection"""
    try:
        # Test wallets table
        wallets_response = supabase.table("wallets").select("count", count="exact").limit(1).execute()
        
        # Test wallet_transactions table
        transactions_response = supabase.table("wallet_transactions").select("count", count="exact").limit(1).execute()
        
        return {
            "success": True,
            "message": "Wallet database connection successful",
            "data": {
                "wallets_table": {
                    "exists": True,
                    "record_count": wallets_response.count
                },
                "transactions_table": {
                    "exists": True,
                    "record_count": transactions_response.count
                }
            }
        }
        
    except Exception as e:
        logger.error(f"Wallet connection test failed: {e}")
        return {
            "success": False,
            "message": "Wallet database connection failed",
            "error": str(e)
        }

@router.get("/test/create-sample")
async def create_sample_wallet():
    """Create a sample wallet for testing"""
    try:
        # Get a user to create wallet for
        users_response = supabase.table("users").select("*").limit(1).execute()
        
        if not users_response.data:
            return {
                "success": False,
                "message": "No users found to create sample wallet"
            }
        
        user = users_response.data[0]
        user_id = user['id']
        
        # Check if user already has wallet
        existing_wallet_response = supabase.table("wallets")\
            .select("*")\
            .eq("user_id", user_id)\
            .execute()
        
        if existing_wallet_response.data:
            wallet = existing_wallet_response.data[0]
            
            # Add sample deposit if wallet exists
            deposit_response = await deposit_to_wallet(
                wallet_id=wallet['id'],
                amount=500.00,
                currency="ZAR",
                description="Sample test deposit",
                reference="TEST_001"
            )
            
            return {
                "success": True,
                "message": "User already has a wallet, added sample deposit",
                "data": deposit_response
            }
        
        # Create new wallet
        create_response = await create_wallet_for_user(user_id)
        
        if create_response['success']:
            wallet = create_response['data']['wallet']
            
            # Add sample deposit
            deposit_response = await deposit_to_wallet(
                wallet_id=wallet['id'],
                amount=1000.00,
                currency="ZAR",
                description="Initial sample deposit",
                reference="TEST_INITIAL"
            )
            
            return {
                "success": True,
                "message": "Sample wallet created with initial deposit",
                "data": {
                    "wallet_creation": create_response,
                    "initial_deposit": deposit_response
                }
            }
        else:
            return create_response
        
    except Exception as e:
        logger.error(f"Error creating sample wallet: {e}")
        return {
            "success": False,
            "message": "Error creating sample wallet",
            "error": str(e)
        }

@router.get("/test")
async def test_wallet_endpoint():
    """Test endpoint to verify wallets API is working"""
    return {
        "success": True,
        "message": "Wallets API is working!",
        "endpoints": {
            "get_user_wallet": "GET /api/wallets/user/{user_id}",
            "check_wallet": "GET /api/wallets/check/{user_id}",
            "create_wallet": "POST /api/wallets/create/{user_id}",
            "get_wallet_by_number": "GET /api/wallets/number/{wallet_number}",
            "get_all_wallets": "GET /api/wallets/all",
            "get_transactions": "GET /api/wallets/{wallet_id}/transactions",
            "deposit": "POST /api/wallets/{wallet_id}/deposit",
            "test_connection": "GET /api/wallets/test/connection",
            "create_sample": "GET /api/wallets/test/create-sample"
        }
    }