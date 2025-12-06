from typing import List, Optional, Dict, Any
from app.db.supabase_client import supabase
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class WalletRepository:
    
    def get_wallet_by_user_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get wallet by user/driver ID
        First checks if wallet table exists, then tries different approaches
        """
        try:
            logger.info(f"Looking for wallet for user_id: {user_id}")
            
            # Try different table/column combinations
            wallet = None
            
            # Method 1: Direct wallet table with user_id
            try:
                response = supabase.table("wallets").select("*").eq("user_id", user_id).execute()
                if response.data:
                    wallet = response.data[0]
                    logger.info(f"✅ Found wallet in 'wallets' table (user_id): {wallet.get('id')}")
                    return wallet
            except Exception as e:
                logger.debug(f"No wallet with user_id: {e}")
            
            # Method 2: Direct wallet table with driver_id
            try:
                response = supabase.table("wallets").select("*").eq("driver_id", user_id).execute()
                if response.data:
                    wallet = response.data[0]
                    logger.info(f"✅ Found wallet in 'wallets' table (driver_id): {wallet.get('id')}")
                    return wallet
            except Exception as e:
                logger.debug(f"No wallet with driver_id: {e}")
            
            # Method 3: Check if wallet is embedded in users table
            try:
                response = supabase.table("users").select("*").eq("id", user_id).execute()
                if response.data:
                    user = response.data[0]
                    if 'wallet_balance' in user:
                        # Create wallet object from user data
                        wallet = {
                            'id': user_id,
                            'user_id': user_id,
                            'balance': user.get('wallet_balance', 0.0),
                            'currency': user.get('wallet_currency', 'USD'),
                            'status': 'active',
                            'created_at': user.get('created_at'),
                            'updated_at': user.get('updated_at')
                        }
                        logger.info(f"✅ Found embedded wallet in users table")
                        return wallet
            except Exception as e:
                logger.debug(f"No embedded wallet: {e}")
            
            logger.warning(f"❌ No wallet found for user_id: {user_id}")
            return None
            
        except Exception as e:
            logger.error(f"Error getting wallet for user {user_id}: {e}")
            return None
    
    def get_wallet_by_id(self, wallet_id: str) -> Optional[Dict[str, Any]]:
        """Get wallet by wallet ID"""
        try:
            response = supabase.table("wallets").select("*").eq("id", wallet_id).execute()
            
            if response.data:
                logger.info(f"✅ Found wallet: {wallet_id}")
                return response.data[0]
            return None
            
        except Exception as e:
            logger.error(f"Error getting wallet {wallet_id}: {e}")
            return None
    
    def get_user_wallet_summary(self, user_id: str) -> Dict[str, Any]:
        """Get complete wallet summary for a user"""
        try:
            # Get wallet
            wallet = self.get_wallet_by_user_id(user_id)
            
            if not wallet:
                return {
                    "has_wallet": False,
                    "message": "No wallet found for user"
                }
            
            # Get user details
            user_response = supabase.table("users").select("*").eq("id", user_id).execute()
            user = user_response.data[0] if user_response.data else None
            
            # Get recent transactions
            transactions = self.get_wallet_transactions(wallet['id'], limit=5)
            
            # Get total transactions count
            total_tx_response = supabase.table("transactions")\
                .select("id", count="exact")\
                .eq("wallet_id", wallet['id'])\
                .execute()
            
            return {
                "has_wallet": True,
                "wallet": wallet,
                "user": user,
                "recent_transactions": transactions,
                "total_transactions": total_tx_response.count if total_tx_response.count else 0,
                "last_updated": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting wallet summary for user {user_id}: {e}")
            return {"has_wallet": False, "error": str(e)}
    
    def get_wallet_transactions(self, wallet_id: str, limit: int = 10, 
                                start_date: Optional[str] = None, 
                                end_date: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get transactions for a wallet"""
        try:
            query = supabase.table("transactions").select("*").eq("wallet_id", wallet_id)
            
            if start_date:
                query = query.gte("created_at", start_date)
            if end_date:
                query = query.lte("created_at", end_date)
            
            response = query.order("created_at", desc=True).limit(limit).execute()
            
            return response.data if response.data else []
            
        except Exception as e:
            logger.error(f"Error getting transactions for wallet {wallet_id}: {e}")
            return []
    
    def create_wallet(self, user_id: str, initial_balance: float = 0.0, 
                     currency: str = "USD") -> Optional[Dict[str, Any]]:
        """Create a new wallet for a user"""
        try:
            wallet_data = {
                "user_id": user_id,
                "balance": initial_balance,
                "currency": currency,
                "status": "active",
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }
            
            response = supabase.table("wallets").insert(wallet_data).execute()
            
            if response.data:
                logger.info(f"✅ Created wallet for user {user_id}")
                return response.data[0]
            return None
            
        except Exception as e:
            logger.error(f"Error creating wallet for user {user_id}: {e}")
            return None
    
    def update_wallet_balance(self, wallet_id: str, amount: float, 
                             operation: str = "add") -> Optional[Dict[str, Any]]:
        """Update wallet balance (add or subtract)"""
        try:
            wallet = self.get_wallet_by_id(wallet_id)
            if not wallet:
                return None
            
            current_balance = wallet['balance']
            
            if operation == "add":
                new_balance = current_balance + amount
            elif operation == "subtract":
                new_balance = current_balance - amount
            else:
                return None
            
            response = supabase.table("wallets")\
                .update({
                    "balance": new_balance,
                    "updated_at": datetime.now().isoformat()
                })\
                .eq("id", wallet_id)\
                .execute()
            
            if response.data:
                logger.info(f"✅ Updated wallet {wallet_id} balance to {new_balance}")
                return response.data[0]
            return None
            
        except Exception as e:
            logger.error(f"Error updating wallet balance {wallet_id}: {e}")
            return None

# Create singleton instance
wallet_repository = WalletRepository()