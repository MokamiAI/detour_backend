from typing import List, Optional, Dict, Any
from app.db.supabase_client import supabase
import logging

logger = logging.getLogger(__name__)

class UserRepository:
    def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Return a user dict by id or None"""
        try:
            response = supabase.table("users").select("*").eq("id", user_id).execute()
            if response.data:
                return response.data[0]
            return None
        except Exception as e:
            logger.error(f"Error fetching user {user_id}: {e}")
            return None

    def get_all_users(self, limit: int = 1000) -> List[Dict[str, Any]]:
        """Return a list of users (up to `limit`)"""
        try:
            response = supabase.table("users").select("*").limit(limit).execute()
            return response.data if response.data else []
        except Exception as e:
            logger.error(f"Error fetching all users: {e}")
            return []

# Singleton instance
user_repository = UserRepository()
