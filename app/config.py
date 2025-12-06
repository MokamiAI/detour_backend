from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # Supabase Configuration
    supabase_url: str
    supabase_key: str
    supabase_service_key: Optional[str] = None
    
    # App Configuration
    environment: str = "development"
    
    # Wallet Configuration
    default_currency: str = "USD"
    min_wallet_balance: float = 0.0
    max_wallet_balance: float = 10000.0
    
    class Config:
        env_file = ".env"
        env_file_encoding = 'utf-8'

# Create settings instance
settings = Settings()