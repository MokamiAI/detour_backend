import requests
import json
import sys

BASE_URL = "http://localhost:8000"

def test_wallet_endpoints():
    """Test wallet API endpoints"""
    
    print("🔍 Testing Wallet API Endpoints")
    print("=" * 60)
    
    # First, get some users to test with
    print("\n1. Getting sample users...")
    response = requests.get(f"{BASE_URL}/api/users/?page=1&limit=3")
    
    if response.status_code != 200:
        print(f"❌ Failed to get users: {response.status_code}")
        return
    
    users_data = response.json()
    users = users_data.get("data", {}).get("users", [])
    
    if not users:
        print("❌ No users found to test with")
        return
    
    print(f"✅ Found {len(users)} users to test with")
    
    # Test each user's wallet
    for i, user in enumerate(users, 1):
        user_id = user.get("id")
        user_name = user.get("name", "Unknown")
        
        print(f"\n{'='*40}")
        print(f"👤 Testing User {i}: {user_name}")
        print(f"   ID: {user_id}")
        print(f"{'='*40}")
        
        # Test 1: Get user wallet
        print(f"\n   Testing: GET /api/wallets/user/{user_id}")
        response = requests.get(f"{BASE_URL}/api/wallets/user/{user_id}")
        
        if response.status_code == 200:
            wallet_data = response.json()
            has_wallet = wallet_data.get("data", {}).get("has_wallet", False)
            
            if has_wallet:
                print(f"   ✅ User has a wallet")
                wallet = wallet_data["data"]
                balance = wallet.get("wallet", {}).get("balance", 0)
                currency = wallet.get("wallet", {}).get("currency", "USD")
                print(f"   💰 Balance: {balance} {currency}")
                
                # Test 2: Get wallet transactions
                print(f"\n   Testing: GET /api/wallets/user/{user_id}/transactions")
                response = requests.get(f"{BASE_URL}/api/wallets/user/{user_id}/transactions?limit=3")
                if response.status_code == 200:
                    tx_data = response.json()
                    tx_count = len(tx_data.get("data", {}).get("transactions", []))
                    print(f"   📊 Found {tx_count} transactions")
                else:
                    print(f"   ⚠️  No transactions or error: {response.status_code}")
                    
            else:
                print(f"   ℹ️  User doesn't have a wallet")
                print(f"   💡 You can create one with: POST /api/wallets/user/{user_id}/create")
                
        elif response.status_code == 404:
            print(f"   ❌ User not found")
        else:
            print(f"   ⚠️  Unexpected status: {response.status_code}")
    
    # Test 3: Get all users with wallets
    print(f"\n{'='*40}")
    print("👥 Testing: GET /api/wallets/users/with-wallets")
    print(f"{'='*40}")
    
    response = requests.get(f"{BASE_URL}/api/wallets/users/with-wallets?limit=5")
    if response.status_code == 200:
        data = response.json()
        users_with_wallets = data.get("data", {}).get("users", [])
        print(f"✅ Found {len(users_with_wallets)} users with wallets")
        
        if users_with_wallets:
            print(f"\n📋 Users with wallets:")
            for user in users_with_wallets[:3]:  # Show first 3
                wallet = user.get("wallet", {})
                print(f"   • {user.get('name')} - Balance: {wallet.get('balance', 0)} {wallet.get('currency', 'USD')}")
    else:
        print(f"❌ Failed: {response.status_code}")
    
    print(f"\n{'='*60}")
    print("🎉 Wallet API Testing Complete!")
    print(f"{'='*60}")
    
    print(f"\n📚 Try these endpoints:")
    print(f"   1. Get wallet for a specific user: GET /api/wallets/user/USER_ID")
    print(f"   2. Create wallet: POST /api/wallets/user/USER_ID/create")
    print(f"   3. Get all users with wallets: GET /api/wallets/users/with-wallets")
    print(f"   4. View API docs: http://localhost:8000/docs")

if __name__ == "__main__":
    print("🔍 Starting Wallet API Tests...")
    print("Note: Make sure the server is running (python run.py)")
    print("-" * 60)
    
    try:
        test_wallet_endpoints()
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to server. Please start it first:")
        print("   python run.py")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        sys.exit(1)