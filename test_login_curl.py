#!/usr/bin/env python3
"""
Test script to show exact curl command for login.
"""
import requests
import json

def test_login_with_curl():
    """Test login and show curl command."""
    url = 'http://localhost:8000/api/auth/login/'
    data = {
        'email': 'admin@removealist.com',
        'password': 'admin123'
    }
    
    print("🧪 Testing Login API...")
    print(f"URL: {url}")
    print(f"Data: {json.dumps(data, indent=2)}")
    print()
    
    try:
        response = requests.post(url, json=data)
        print(f"Status Code: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        print(f"Response Body: {response.text}")
        
        if response.status_code == 200:
            print("\n✅ Login successful!")
            result = response.json()
            print(f"Access Token: {result['data']['access_token'][:50]}...")
        else:
            print(f"\n❌ Login failed with status {response.status_code}")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == '__main__':
    test_login_with_curl()





