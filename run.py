import uvicorn
import sys
import os

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

if __name__ == "__main__":
    print("🚀 Starting Users API Server")
    print("=" * 50)
    print("🌐 Server will be available at: http://localhost:8000")
    print("📚 API Documentation: http://localhost:8000/docs")
    print("🔍 Testing endpoint: http://localhost:8000/api/users/")
    print("=" * 50)
    
    try:
        # Import settings to test connection
        from app.config import settings
        print(f"✅ Configuration loaded successfully")
        print(f"📡 Supabase URL: {settings.supabase_url}")
    except Exception as e:
        print(f"❌ Configuration error: {e}")
        print("Please check your .env file")
        sys.exit(1)
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )