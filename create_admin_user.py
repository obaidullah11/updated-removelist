#!/usr/bin/env python3
"""
Script to create an admin user for the admin panel.
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'removealist_backend.settings')
django.setup()

from django.contrib.auth import get_user_model

User = get_user_model()

def create_admin_user():
    """Create an admin user for testing."""
    email = 'admin@removealist.com'
    password = 'admin123'
    
    try:
        # Check if admin user already exists
        if User.objects.filter(email=email).exists():
            print(f"✅ Admin user already exists: {email}")
            admin_user = User.objects.get(email=email)
            admin_user.set_password(password)
            admin_user.save()
            print(f"✅ Password updated for admin user: {email}")
        else:
            # Create new admin user
            admin_user = User.objects.create_superuser(
                email=email,
                password=password,
                first_name='Admin',
                last_name='User',
                phone_number='+1234567890'
            )
            print(f"✅ Created admin user: {email}")
        
        print(f"📧 Email: {email}")
        print(f"🔑 Password: {password}")
        print(f"👤 Name: {admin_user.first_name} {admin_user.last_name}")
        print(f"🔐 Is Superuser: {admin_user.is_superuser}")
        print(f"👑 Is Staff: {admin_user.is_staff}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error creating admin user: {e}")
        return False

if __name__ == '__main__':
    success = create_admin_user()
    sys.exit(0 if success else 1)





