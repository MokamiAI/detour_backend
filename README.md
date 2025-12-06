# 🚗 Driver Wallet & Payments API

A FastAPI backend for managing driver wallets, earnings deposits, and withdrawals.

## Features
- **User Management**: Driver registration and authentication
- **Wallet System**: Digital wallets for driver earnings
- **Payments API**: Withdraw earnings to bank or via vouchers
- **No Authentication Required**: Simple driver ID-based withdrawals

## Tech Stack
- **FastAPI** - Modern Python web framework
- **Pydantic** - Data validation
- **Uvicorn** - ASGI server
- **Supabase** - Database (PostgreSQL)

## API Endpoints

### Users
- `GET /api/users/` - List all users
- `GET /api/users/{user_id}` - Get user by ID
- `GET /api/users/email/{email}` - Get user by email

### Wallets
- `GET /api/wallets/user/{user_id}` - Get user's wallet
- `POST /api/wallets/create/{user_id}` - Create wallet
- `POST /api/wallets/{wallet_id}/deposit` - Deposit earnings
- `GET /api/wallets/{wallet_id}/transactions` - Get transaction history

### Payments (Withdrawals)
- `POST /api/payments/withdraw` - Request withdrawal
- `GET /api/payments/status/{withdrawal_id}` - Check withdrawal status
- `GET /api/payments/check-balance/{driver_id}` - Check driver balance
- `GET /api/payments/driver/{driver_id}/history` - Withdrawal history
- `GET /api/payments/voucher/{voucher_code}` - Check voucher

## Installation

1. Clone repository:
```bash
git clone https://github.com/yourusername/wallet-backend.git
cd wallet-backend