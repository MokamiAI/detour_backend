import requests
import json
import time

BASE_URL = "http://localhost:8000"

def test_connection():
    """Test basic API connection"""
    print("🔍 Testing API Connection...")
    print("-" * 40)
    
    try:
        # Test root endpoint
        response = requests.get(f"{BASE_URL}/")
        if response.status_code == 200:
            print("✅ API is running!")
            data = response.json()
            print(f"📋 Message: {data.get('message')}")
            return True
        else:
            print(f"❌ API returned status: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to API. Is the server running?")
        print("   Run: python run.py")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_users_endpoints():
    """Test users API endpoints"""
    print("\n📊 Testing Users Endpoints...")
    print("-" * 40)
    
    # 1. Get users count
    print("\n1. Getting users count...")
    try:
        response = requests.get(f"{BASE_URL}/api/users/stats/count")
        if response.status_code == 200:
            data = response.json()
            count = data.get("data", {}).get("total_users", 0)
            print(f"✅ Total users in database: {count}")
            
            if count > 0:
                return True  # We have data to test with
            else:
                print("⚠️  No users found in database")
                return False
        else:
            print(f"❌ Failed to get count: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def get_sample_users():
    """Get sample users to test individual endpoints"""
    print("\n👥 Getting sample users...")
    
    try:
        response = requests.get(f"{BASE_URL}/api/users/?page=1&limit=3")
        if response.status_code == 200:
            data = response.json()
            users = data.get("data", {}).get("users", [])
            
            if users:
                print(f"✅ Retrieved {len(users)} sample users")
                return users
            else:
                print("❌ No users returned")
                return []
        else:
            print(f"❌ Failed to get users: {response.status_code}")
            return []
    except Exception as e:
        print(f"❌ Error: {e}")
        return []

def test_individual_user(user):
    """Test getting a specific user"""
    user_id = user.get("id")
    user_email = user.get("email")
    
    print(f"\n🔍 Testing user: {user.get('name', 'Unknown')}")
    print(f"   ID: {user_id}")
    print(f"   Email: {user_email}")
    
    # Test by ID
    print("   Testing by ID...", end=" ")
    try:
        response = requests.get(f"{BASE_URL}/api/users/{user_id}")
        if response.status_code == 200:
            print("✅ OK")
        else:
            print(f"❌ Failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Test by email if available
    if user_email:
        print("   Testing by email...", end=" ")
        try:
            response = requests.get(f"{BASE_URL}/api/users/email/{user_email}")
            if response.status_code == 200:
                print("✅ OK")
            else:
                print(f"❌ Failed: {response.status_code}")
        except Exception as e:
            print(f"❌ Error: {e}")

def main():
    """Main test function"""
    print("=" * 50)
    print("🔍 USERS API TEST SCRIPT")
    print("=" * 50)
    
    # Wait a moment for server to start
    print("Waiting for server to be ready...")
    time.sleep(2)
    
    # Test connection
    if not test_connection():
        return
    
    # Test users count
    if not test_users_endpoints():
        return
    
    # Get sample users
    users = get_sample_users()
    
    if users:
        # Test individual user endpoints
        print("\n👤 Testing individual user endpoints...")
        print("-" * 40)
        
        for user in users[:2]:  # Test first 2 users
            test_individual_user(user)
    
    print("\n" + "=" * 50)
    print("🎉 TEST COMPLETED!")
    print("=" * 50)
    print("\n📚 You can now:")
    print("1. Visit http://localhost:8000/docs for interactive API docs")
    print("2. View all users: http://localhost:8000/api/users/")
    print("3. View API health: http://localhost:8000/health")
    print("\n💡 Try these commands:")
    print("   curl http://localhost:8000/api/users/stats/count")
    print("   curl http://localhost:8000/api/users/?page=1&limit=5")

if __name__ == "__main__":
    main()