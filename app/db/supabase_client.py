from supabase import create_client, Client
from app.config import settings
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_supabase_client() -> Client:
    """Create and return Supabase client"""
    try:
        client = create_client(settings.supabase_url, settings.supabase_key)
        logger.info("✅ Connected to Supabase successfully!")
        return client
    except Exception as e:
        logger.error(f"❌ Failed to connect to Supabase: {e}")
        raise

# Initialize Supabase client
supabase = get_supabase_client()