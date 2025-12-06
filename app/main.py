from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.users import router as users_router
from app.api.wallets import router as wallets_router
from app.api.payments import router as payments_router
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Driver Payments & Withdrawals API",
    description="Simple API for drivers to withdraw earnings - no authentication required",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(users_router, prefix="/api/users", tags=["users"])
app.include_router(wallets_router, prefix="/api/wallets", tags=["wallets"])
app.include_router(payments_router, prefix="/api/payments", tags=["payments"])

@app.get("/")
async def root():
    """Root endpoint - API welcome message"""
    return {
        "message": "Welcome to Driver Payments & Withdrawals API!",
        "version": "1.0.0",
        "description": "Simple API for drivers to withdraw earnings - enter ID and amount",
        "no_authentication": "No login/token required - just driver ID",
        "endpoints": {
            "payments": {
                "request_withdrawal": "POST /api/payments/withdraw",
                "check_status": "GET /api/payments/status/{withdrawal_id}",
                "check_balance": "GET /api/payments/check-balance/{driver_id}",
                "withdrawal_history": "GET /api/payments/driver/{driver_id}/history",
                "check_voucher": "GET /api/payments/voucher/{voucher_code}",
                "redeem_voucher": "POST /api/payments/voucher/{voucher_code}/redeem",
                "verify_bank": "GET /api/payments/verify-bank-account",
                "get_limits": "GET /api/payments/limits"
            }
        },
        "withdrawal_options": {
            "bank_deposit": "Money deposited directly to bank account",
            "voucher": "Get voucher code for cash pickup"
        },
        "simple_usage": "Just provide driver ID, amount, and withdrawal method"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "driver-payments-api",
        "features": ["bank_deposits", "vouchers", "no_authentication"]
    }

@app.get("/api/quick-withdraw")
async def quick_withdraw_guide():
    """Quick guide for withdrawals"""
    return {
        "steps": [
            {
                "step": 1,
                "action": "Check your balance",
                "endpoint": "GET /api/payments/check-balance/{your_driver_id}",
                "example": "/api/payments/check-balance/driver_123"
            },
            {
                "step": 2,
                "action": "Choose withdrawal method",
                "options": [
                    {
                        "method": "Bank Deposit",
                        "min": "R100.00",
                        "max": "R15,000.00",
                        "fee": "R10.00",
                        "time": "24 hours"
                    },
                    {
                        "method": "Voucher",
                        "min": "R50.00",
                        "max": "R5,000.00",
                        "fee": "R5.00",
                        "time": "Immediate"
                    }
                ]
            },
            {
                "step": 3,
                "action": "Submit withdrawal request",
                "endpoint": "POST /api/payments/withdraw",
                "example_request": {
                    "withdrawal_request": {
                        "driver_id": "driver_123",
                        "amount": "1000.00",
                        "withdrawal_type": "bank_deposit"
                    },
                    "bank_details": {
                        "account_holder_name": "John Driver",
                        "account_number": "12345678901",
                        "bank_type": "nedbank",
                        "branch_code": "198765"
                    }
                }
            },
            {
                "step": 4,
                "action": "Check status",
                "endpoint": "GET /api/payments/status/{withdrawal_id}",
                "example": "/api/payments/status/WD-231206-ABC123DEF"
            }
        ]
    }

@app.on_event("startup")
async def startup_event():
    """Run on application startup"""
    logger.info("🚀 Starting Driver Payments & Withdrawals API...")
    logger.info("💰 Simple withdrawals - no authentication required")
    logger.info("💳 Withdrawal Methods: Bank Deposit | Voucher")
    logger.info("👤 Just need: Driver ID + Amount + Withdrawal Method")
    logger.info("🏦 Supported Banks: Nedbank, Standard Bank, ABSA, FNB, Capitec")
    logger.info("🌐 Server running on http://localhost:8000")
    logger.info("📚 Documentation: http://localhost:8000/docs")
    logger.info("💸 Quick Guide: http://localhost:8000/api/quick-withdraw")

@app.on_event("shutdown")
async def shutdown_event():
    """Run on application shutdown"""
    logger.info("🛑 Shutting down Driver Payments API...")
    logger.info("👋 API shutdown complete.")