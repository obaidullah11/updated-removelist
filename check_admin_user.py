#!/usr/bin/env python3
"""
Script to check admin user status.
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'removealist_backend.settings')
django.setup()

from django.contrib.auth import get_user_model

User = get_user_model()

def check_admin_user():
    """Check admin user status."""
    email = 'admin@removealist.com'
    
    try:
        admin_user = User.objects.get(email=email)
        print(f"📧 Email: {admin_user.email}")
        print(f"👤 Name: {admin_user.first_name} {admin_user.last_name}")
        print(f"🔐 Is Superuser: {admin_user.is_superuser}")
        print(f"👑 Is Staff: {admin_user.is_staff}")
        print(f"✅ Is Active: {admin_user.is_active}")
        print(f"📬 Is Email Verified: {admin_user.is_email_verified}")
        print(f"🔑 Has Password: {bool(admin_user.password)}")
        
        if not admin_user.is_email_verified:
            print("\n⚠️  Email verification is required for login!")
            print("🔧 Fixing email verification...")
            admin_user.is_email_verified = True
            admin_user.save()
            print("✅ Email verification enabled!")
        
        return True
        
    except User.DoesNotExist:
        print(f"❌ Admin user not found: {email}")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == '__main__':
    check_admin_user()





