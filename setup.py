#!/usr/bin/env python3
"""
Setup script for RemoveList Backend
"""
import os
import sys
import subprocess
from pathlib import Path

def run_command(command, description):
    """Run a command and handle errors."""
    print(f"\n🔄 {description}...")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed:")
        print(f"Error: {e.stderr}")
        return False

def check_requirements():
    """Check if required software is installed."""
    print("🔍 Checking requirements...")
    
    # Check Python version
    if sys.version_info < (3, 8):
        print("❌ Python 3.8+ is required")
        return False
    print(f"✅ Python {sys.version.split()[0]} found")
    
    # Check if PostgreSQL is available
    try:
        subprocess.run("psql --version", shell=True, check=True, capture_output=True)
        print("✅ PostgreSQL found")
    except subprocess.CalledProcessError:
        print("⚠️  PostgreSQL not found. Please install PostgreSQL 12+")
        print("   Ubuntu/Debian: sudo apt-get install postgresql postgresql-contrib")
        print("   macOS: brew install postgresql")
        print("   Windows: Download from https://www.postgresql.org/download/")
    
    # Check if Redis is available
    try:
        subprocess.run("redis-cli --version", shell=True, check=True, capture_output=True)
        print("✅ Redis found")
    except subprocess.CalledProcessError:
        print("⚠️  Redis not found. Please install Redis 6+")
        print("   Ubuntu/Debian: sudo apt-get install redis-server")
        print("   macOS: brew install redis")
        print("   Windows: Download from https://redis.io/download")
    
    return True

def setup_environment():
    """Set up the development environment."""
    print("\n🚀 Setting up RemoveList Backend...")
    
    # Check requirements
    if not check_requirements():
        return False
    
    # Install Python dependencies
    if not run_command("pip install -r requirements.txt", "Installing Python dependencies"):
        return False
    
    # Check if .env exists
    if not Path(".env").exists():
        if Path("env.example").exists():
            run_command("cp env.example .env", "Creating .env file from template")
            print("📝 Please edit .env file with your configuration")
        else:
            print("⚠️  No .env file found. Please create one based on env.example")
    
    # Create database (if PostgreSQL is available)
    try:
        subprocess.run("psql --version", shell=True, check=True, capture_output=True)
        print("\n📊 Setting up database...")
        
        # Try to create database
        create_db_cmd = "createdb removealist_db 2>/dev/null || echo 'Database may already exist'"
        subprocess.run(create_db_cmd, shell=True)
        
        # Run migrations
        if not run_command("python manage.py makemigrations", "Creating migrations"):
            return False
        
        if not run_command("python manage.py migrate", "Running migrations"):
            return False
        
        # Create default data
        if not run_command("python manage.py create_checklist_templates", "Creating checklist templates"):
            print("⚠️  Failed to create checklist templates (you can run this manually later)")
        
        if not run_command("python manage.py create_time_slots", "Creating time slots"):
            print("⚠️  Failed to create time slots (you can run this manually later)")
        
    except subprocess.CalledProcessError:
        print("⚠️  PostgreSQL not available. Skipping database setup.")
        print("   Please set up PostgreSQL and run migrations manually:")
        print("   python manage.py makemigrations")
        print("   python manage.py migrate")
    
    # Collect static files
    run_command("python manage.py collectstatic --noinput", "Collecting static files")
    
    print("\n🎉 Setup completed!")
    print("\n📋 Next steps:")
    print("1. Edit .env file with your configuration")
    print("2. Create a superuser: python manage.py createsuperuser")
    print("3. Start the development server: python manage.py runserver")
    print("4. Start Celery worker: celery -A removealist_backend worker --loglevel=info")
    print("5. Visit http://localhost:8000/admin/ to access admin panel")
    
    return True

def main():
    """Main setup function."""
    if len(sys.argv) > 1 and sys.argv[1] == "--docker":
        print("🐳 Docker setup detected")
        print("Use docker-compose up to start all services")
        return
    
    setup_environment()

if __name__ == "__main__":
    main()
