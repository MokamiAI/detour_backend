from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from app.db.supabase_client import supabase
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/")
async def get_all_users(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(10, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query(None, description="Search by name or email")
):
    """Get all users from the database"""
    try:
        # Calculate offset for pagination
        offset = (page - 1) * limit
        
        logger.info(f"Fetching users: page={page}, limit={limit}, search={search}")
        
        # Build query
        query = supabase.table("users").select("*")
        
        # Add search if provided
        if search:
            query = query.or_(f"name.ilike.%{search}%,email.ilike.%{search}%")
        
        # Add pagination and ordering
        query = query.order("created_at", desc=True).range(offset, offset + limit - 1)
        
        # Execute query
        response = query.execute()
        
        logger.info(f"✅ Retrieved {len(response.data)} users")
        
        # Get total count for pagination info
        count_query = supabase.table("users").select("id", count="exact")
        if search:
            count_query = count_query.or_(f"name.ilike.%{search}%,email.ilike.%{search}%")
        count_response = count_query.execute()
        
        return {
            "success": True,
            "message": f"Retrieved {len(response.data)} users",
            "data": {
                "users": response.data,
                "pagination": {
                    "page": page,
                    "limit": limit,
                    "total": count_response.count,
                    "total_pages": (count_response.count + limit - 1) // limit if count_response.count else 0,
                    "has_more": (offset + limit) < count_response.count if count_response.count else False
                }
            }
        }
        
    except Exception as e:
        logger.error(f"❌ Error fetching users: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.get("/{user_id}")
async def get_user_by_id(user_id: str):
    """Get a specific user by ID"""
    try:
        logger.info(f"Fetching user with ID: {user_id}")
        
        response = supabase.table("users").select("*").eq("id", user_id).execute()
        
        if not response.data:
            logger.warning(f"User not found: {user_id}")
            raise HTTPException(status_code=404, detail="User not found")
        
        logger.info(f"✅ User found: {user_id}")
        
        return {
            "success": True,
            "message": "User retrieved successfully",
            "data": response.data[0]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error fetching user {user_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.get("/email/{email}")
async def get_user_by_email(email: str):
    """Get a user by email address"""
    try:
        logger.info(f"Fetching user with email: {email}")
        
        response = supabase.table("users").select("*").eq("email", email).execute()
        
        if not response.data:
            logger.warning(f"User not found with email: {email}")
            raise HTTPException(status_code=404, detail="User not found")
        
        logger.info(f"✅ User found with email: {email}")
        
        return {
            "success": True,
            "message": "User retrieved successfully",
            "data": response.data[0]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error fetching user by email {email}: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.get("/stats/count")
async def get_users_count():
    """Get total number of users"""
    try:
        logger.info("Counting total users...")
        
        response = supabase.table("users").select("id", count="exact").execute()
        
        logger.info(f"✅ Total users: {response.count}")
        
        return {
            "success": True,
            "message": "User count retrieved",
            "data": {
                "total_users": response.count
            }
        }
        
    except Exception as e:
        logger.error(f"❌ Error counting users: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")