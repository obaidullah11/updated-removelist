#!/usr/bin/env python3
"""
Test script for admin panel APIs.
"""
import os
import sys
import django
import requests
import json
from datetime import datetime, timedelta

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'removealist_backend.settings')
django.setup()

from django.contrib.auth import get_user_model
from django.utils import timezone
from apps.admin_panel.models import AdminNotification, DashboardMetric

User = get_user_model()

# Test configuration
BASE_URL = 'http://localhost:8000/api'
ADMIN_EMAIL = 'admin@removealist.com'
ADMIN_PASSWORD = 'admin123'

class AdminAPITester:
    def __init__(self):
        self.session = requests.Session()
        self.access_token = None
        self.admin_user = None
        
    def setup_admin_user(self):
        """Create or get admin user for testing."""
        try:
            # Try to get existing admin user
            self.admin_user = User.objects.filter(email=ADMIN_EMAIL).first()
            
            if not self.admin_user:
                # Create admin user
                self.admin_user = User.objects.create_superuser(
                    email=ADMIN_EMAIL,
                    password=ADMIN_PASSWORD,
                    first_name='Admin',
                    last_name='User',
                    phone_number='+1234567890'
                )
                print(f"✅ Created admin user: {ADMIN_EMAIL}")
            else:
                print(f"✅ Found existing admin user: {ADMIN_EMAIL}")
                
        except Exception as e:
            print(f"❌ Error setting up admin user: {e}")
            return False
        
        return True
    
    def login(self):
        """Login and get access token."""
        try:
            response = self.session.post(f'{BASE_URL}/auth/login/', json={
                'email': ADMIN_EMAIL,
                'password': ADMIN_PASSWORD
            })
            
            if response.status_code == 200:
                data = response.json()
                self.access_token = data['data']['access_token']
                self.session.headers.update({
                    'Authorization': f'Bearer {self.access_token}'
                })
                print("✅ Login successful")
                return True
            else:
                print(f"❌ Login failed: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Login error: {e}")
            return False
    
    def test_dashboard_metrics(self):
        """Test dashboard metrics API."""
        print("\n🧪 Testing Dashboard Metrics API...")
        try:
            response = self.session.get(f'{BASE_URL}/admin/dashboard/metrics/')
            
            if response.status_code == 200:
                data = response.json()
                print("✅ Dashboard metrics retrieved successfully")
                print(f"   Users: {data['data']['users']['total']}")
                print(f"   Bookings: {data['data']['bookings']['total']}")
                print(f"   Revenue: ${data['data']['revenue']['total']}")
                return True
            else:
                print(f"❌ Dashboard metrics failed: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Dashboard metrics error: {e}")
            return False
    
    def test_dashboard_analytics(self):
        """Test dashboard analytics API."""
        print("\n🧪 Testing Dashboard Analytics API...")
        try:
            response = self.session.get(f'{BASE_URL}/admin/dashboard/analytics/?days=30')
            
            if response.status_code == 200:
                data = response.json()
                print("✅ Dashboard analytics retrieved successfully")
                print(f"   Booking trends: {len(data['data']['booking_trends'])} days")
                print(f"   Partner status: {len(data['data']['partner_status'])} categories")
                print(f"   Recent activities: {len(data['data']['recent_activities'])} items")
                return True
            else:
                print(f"❌ Dashboard analytics failed: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Dashboard analytics error: {e}")
            return False
    
    def test_users_list(self):
        """Test users list API."""
        print("\n🧪 Testing Users List API...")
        try:
            response = self.session.get(f'{BASE_URL}/admin/users/')
            
            if response.status_code == 200:
                data = response.json()
                print("✅ Users list retrieved successfully")
                print(f"   Total users: {data['count']}")
                print(f"   Users per page: {len(data['results'])}")
                return True
            else:
                print(f"❌ Users list failed: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Users list error: {e}")
            return False
    
    def test_user_detail(self):
        """Test user detail API."""
        print("\n🧪 Testing User Detail API...")
        try:
            # Get first user ID
            users_response = self.session.get(f'{BASE_URL}/admin/users/')
            if users_response.status_code == 200:
                users_data = users_response.json()
                if users_data['results']:
                    user_id = users_data['results'][0]['id']
                    print(f"   Testing with user ID: {user_id}")
                    
                    response = self.session.get(f'{BASE_URL}/admin/users/{user_id}/')
                    
                    if response.status_code == 200:
                        data = response.json()
                        print("✅ User detail retrieved successfully")
                        print(f"   User: {data['data']['full_name']}")
                        print(f"   Email: {data['data']['email']}")
                        return True
                    else:
                        print(f"❌ User detail failed: {response.text}")
                        return False
                else:
                    print("❌ No users found for detail test")
                    return False
            else:
                print("❌ Could not get users for detail test")
                return False
                
        except Exception as e:
            print(f"❌ User detail error: {str(e)}")
            return False
    
    def test_bookings_list(self):
        """Test bookings list API."""
        print("\n🧪 Testing Bookings List API...")
        try:
            response = self.session.get(f'{BASE_URL}/admin/bookings/')
            
            if response.status_code == 200:
                data = response.json()
                print("✅ Bookings list retrieved successfully")
                print(f"   Total bookings: {data['count']}")
                print(f"   Bookings per page: {len(data['results'])}")
                return True
            else:
                print(f"❌ Bookings list failed: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Bookings list error: {e}")
            return False
    
    def test_partners_list(self):
        """Test partners list API."""
        print("\n🧪 Testing Partners List API...")
        try:
            response = self.session.get(f'{BASE_URL}/admin/partners/')
            
            if response.status_code == 200:
                data = response.json()
                print("✅ Partners list retrieved successfully")
                print(f"   Total partners: {data['count']}")
                print(f"   Partners per page: {len(data['results'])}")
                return True
            else:
                print(f"❌ Partners list failed: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Partners list error: {e}")
            return False
    
    def test_notifications_list(self):
        """Test notifications list API."""
        print("\n🧪 Testing Notifications List API...")
        try:
            response = self.session.get(f'{BASE_URL}/admin/notifications/')
            
            if response.status_code == 200:
                data = response.json()
                print("✅ Notifications list retrieved successfully")
                print(f"   Total notifications: {data['count']}")
                print(f"   Notifications per page: {len(data['results'])}")
                return True
            else:
                print(f"❌ Notifications list failed: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Notifications list error: {e}")
            return False
    
    def create_sample_data(self):
        """Create sample data for testing."""
        print("\n📊 Creating sample data...")
        try:
            # Create sample notifications
            AdminNotification.objects.create(
                title="Test Notification 1",
                message="This is a test notification for admin panel",
                notification_type='info',
                user=self.admin_user
            )
            
            AdminNotification.objects.create(
                title="Test Notification 2",
                message="Another test notification",
                notification_type='success'
            )
            
            # Create sample dashboard metrics (only if they don't exist)
            DashboardMetric.objects.get_or_create(
                metric_type='users',
                period='daily',
                date=timezone.now().date(),
                defaults={'value': 100}
            )
            
            DashboardMetric.objects.get_or_create(
                metric_type='bookings',
                period='daily',
                date=timezone.now().date(),
                defaults={'value': 25}
            )
            
            print("✅ Sample data created successfully")
            return True
            
        except Exception as e:
            print(f"❌ Error creating sample data: {e}")
            return False
    
    def run_all_tests(self):
        """Run all API tests."""
        print("🚀 Starting Admin API Tests...")
        print("=" * 50)
        
        # Setup
        if not self.setup_admin_user():
            return False
        
        if not self.login():
            return False
        
        # Create sample data
        self.create_sample_data()
        
        # Run tests
        tests = [
            self.test_dashboard_metrics,
            self.test_dashboard_analytics,
            self.test_users_list,
            self.test_user_detail,
            self.test_bookings_list,
            self.test_partners_list,
            self.test_notifications_list,
        ]
        
        passed = 0
        total = len(tests)
        
        for test in tests:
            if test():
                passed += 1
        
        print("\n" + "=" * 50)
        print(f"📊 Test Results: {passed}/{total} tests passed")
        
        if passed == total:
            print("🎉 All tests passed! Admin APIs are working correctly.")
        else:
            print("⚠️  Some tests failed. Check the output above for details.")
        
        return passed == total

if __name__ == '__main__':
    tester = AdminAPITester()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)
