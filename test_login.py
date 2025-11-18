#!/usr/bin/env python3
"""
Test script to verify login API is working.
"""
import requests
import json

def test_login():
    """Test the login API."""
    base_url = 'http://localhost:8000/api'
    
    # Test login
    login_data = {
        'email': 'admin@removealist.com',
        'password': 'admin123'
    }
    
    try:
        print("🧪 Testing Login API...")
        response = requests.post(f'{base_url}/auth/login/', json=login_data)
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Login successful!")
            print(f"   Access Token: {data['data']['access_token'][:50]}...")
            print(f"   User: {data['data']['user']['first_name']} {data['data']['user']['last_name']}")
            print(f"   Email: {data['data']['user']['email']}")
            
            # Test admin dashboard API with the token
            headers = {
                'Authorization': f'Bearer {data["data"]["access_token"]}'
            }
            
            print("\n🧪 Testing Admin Dashboard API...")
            dashboard_response = requests.get(f'{base_url}/admin/dashboard/metrics/', headers=headers)
            
            if dashboard_response.status_code == 200:
                dashboard_data = dashboard_response.json()
                print("✅ Admin Dashboard API working!")
                print(f"   Users: {dashboard_data['data']['users']['total']}")
                print(f"   Bookings: {dashboard_data['data']['bookings']['total']}")
                print(f"   Revenue: ${dashboard_data['data']['revenue']['total']}")
                return True
            else:
                print(f"❌ Admin Dashboard API failed: {dashboard_response.status_code}")
                print(f"   Response: {dashboard_response.text}")
                return False
                
        else:
            print(f"❌ Login failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == '__main__':
    success = test_login()
    if success:
        print("\n🎉 All tests passed! Admin APIs are working correctly.")
        print("\n📝 To access the admin panel:")
        print("   1. Go to http://localhost:3000 (admin panel)")
        print("   2. Login with: admin@removealist.com / admin123")
        print("   3. You should see the dashboard with real data!")
    else:
        print("\n❌ Tests failed. Check the output above for details.")