# RemoveList Backend Deployment Guide

This guide covers deploying the RemoveList backend to a production environment.

## 🏗️ Infrastructure Requirements

### Minimum Server Specifications
- **CPU**: 2 cores
- **RAM**: 4GB
- **Storage**: 20GB SSD
- **OS**: Ubuntu 20.04 LTS or newer

### Required Services
- **PostgreSQL 12+**
- **Redis 6+**
- **Nginx** (reverse proxy)
- **Python 3.8+**

## 🚀 Deployment Steps

### 1. Server Setup

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install required packages
sudo apt install -y python3 python3-pip python3-venv postgresql postgresql-contrib redis-server nginx supervisor git

# Create application user
sudo adduser --system --group --home /opt/removealist-backend www-data
```

### 2. Database Setup

```bash
# Switch to postgres user
sudo -u postgres psql

# Create database and user
CREATE DATABASE removealist_db;
CREATE USER removealist_user WITH PASSWORD 'your_secure_password';
ALTER ROLE removealist_user SET client_encoding TO 'utf8';
ALTER ROLE removealist_user SET default_transaction_isolation TO 'read committed';
ALTER ROLE removealist_user SET timezone TO 'UTC';
GRANT ALL PRIVILEGES ON DATABASE removealist_db TO removealist_user;
\q

# Configure PostgreSQL for production
sudo nano /etc/postgresql/12/main/postgresql.conf
# Set: shared_preload_libraries = 'pg_stat_statements'
# Set: max_connections = 100

sudo systemctl restart postgresql
```

### 3. Redis Configuration

```bash
# Configure Redis
sudo nano /etc/redis/redis.conf
# Set: maxmemory 256mb
# Set: maxmemory-policy allkeys-lru
# Uncomment: requirepass your_redis_password

sudo systemctl restart redis-server
```

### 4. Application Deployment

```bash
# Clone repository
sudo git clone https://github.com/your-repo/removealist-backend.git /opt/removealist-backend
cd /opt/removealist-backend

# Set ownership
sudo chown -R www-data:www-data /opt/removealist-backend

# Switch to app user
sudo -u www-data bash

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create production environment file
cp env.example .env
nano .env
```

### 5. Environment Configuration

Edit `/opt/removealist-backend/.env`:

```env
# Django Settings
SECRET_KEY=your-very-secure-secret-key-here
DEBUG=False
ALLOWED_HOSTS=your-domain.com,www.your-domain.com

# Database
DB_NAME=removealist_db
DB_USER=removealist_user
DB_PASSWORD=your_secure_password
DB_HOST=localhost
DB_PORT=5432

# Redis
REDIS_URL=redis://:your_redis_password@127.0.0.1:6379/1
CELERY_BROKER_URL=redis://:your_redis_password@localhost:6379/0
CELERY_RESULT_BACKEND=redis://:your_redis_password@localhost:6379/0

# Email (using SendGrid)
EMAIL_HOST=smtp.sendgrid.net
EMAIL_PORT=587
EMAIL_HOST_USER=apikey
EMAIL_HOST_PASSWORD=your_sendgrid_api_key
DEFAULT_FROM_EMAIL=RemoveList <noreply@your-domain.com>

# CORS
CORS_ALLOWED_ORIGINS=https://your-frontend-domain.com

# Frontend URL
FRONTEND_URL=https://your-frontend-domain.com

# AWS S3 (for file storage)
USE_S3=True
AWS_ACCESS_KEY_ID=your_aws_access_key
AWS_SECRET_ACCESS_KEY=your_aws_secret_key
AWS_STORAGE_BUCKET_NAME=your-s3-bucket
AWS_S3_REGION_NAME=us-east-1
```

### 6. Django Setup

```bash
# Still as www-data user
cd /opt/removealist-backend
source venv/bin/activate

# Set production settings
export DJANGO_SETTINGS_MODULE=removealist_backend.settings_production

# Run migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Create default data
python manage.py create_checklist_templates
python manage.py create_time_slots

# Collect static files
python manage.py collectstatic --noinput

# Test the application
python manage.py check --deploy
```

### 7. Create Log Directories

```bash
# Create log directories
sudo mkdir -p /var/log/django /var/log/gunicorn /var/log/celery
sudo chown -R www-data:www-data /var/log/django /var/log/gunicorn /var/log/celery
```

### 8. Systemd Services

```bash
# Copy service files
sudo cp /opt/removealist-backend/systemd/*.service /etc/systemd/system/

# Reload systemd and enable services
sudo systemctl daemon-reload
sudo systemctl enable removealist-backend.service
sudo systemctl enable removealist-celery.service
sudo systemctl enable removealist-celery-beat.service

# Start services
sudo systemctl start removealist-backend.service
sudo systemctl start removealist-celery.service
sudo systemctl start removealist-celery-beat.service

# Check status
sudo systemctl status removealist-backend.service
sudo systemctl status removealist-celery.service
sudo systemctl status removealist-celery-beat.service
```

### 9. Nginx Configuration

```bash
# Remove default site
sudo rm /etc/nginx/sites-enabled/default

# Copy nginx configuration
sudo cp /opt/removealist-backend/nginx.conf /etc/nginx/sites-available/removealist-backend

# Update paths in nginx.conf
sudo nano /etc/nginx/sites-available/removealist-backend
# Update: server_name, ssl certificates, static/media paths

# Enable site
sudo ln -s /etc/nginx/sites-available/removealist-backend /etc/nginx/sites-enabled/

# Test nginx configuration
sudo nginx -t

# Restart nginx
sudo systemctl restart nginx
```

### 10. SSL Certificate (Let's Encrypt)

```bash
# Install certbot
sudo apt install certbot python3-certbot-nginx

# Obtain SSL certificate
sudo certbot --nginx -d your-domain.com -d www.your-domain.com

# Test auto-renewal
sudo certbot renew --dry-run
```

## 🔧 Production Optimizations

### Database Optimization

```sql
-- Connect to PostgreSQL as superuser
sudo -u postgres psql removealist_db

-- Create indexes for better performance
CREATE INDEX CONCURRENTLY idx_users_email ON users(email);
CREATE INDEX CONCURRENTLY idx_moves_user_id ON moves(user_id);
CREATE INDEX CONCURRENTLY idx_moves_move_date ON moves(move_date);
CREATE INDEX CONCURRENTLY idx_bookings_move_id ON bookings(move_id);
CREATE INDEX CONCURRENTLY idx_timeline_events_move_id ON timeline_events(move_id);
CREATE INDEX CONCURRENTLY idx_inventory_rooms_move_id ON inventory_rooms(move_id);

-- Analyze tables
ANALYZE;
```

### Redis Configuration

```bash
# Edit Redis config for production
sudo nano /etc/redis/redis.conf

# Add these optimizations:
# maxmemory 512mb
# maxmemory-policy allkeys-lru
# save 900 1
# save 300 10
# save 60 10000

sudo systemctl restart redis-server
```

### Monitoring Setup

```bash
# Install monitoring tools
sudo apt install htop iotop nethogs

# Setup log rotation
sudo nano /etc/logrotate.d/removealist-backend
```

Add to logrotate config:
```
/var/log/django/*.log {
    daily
    missingok
    rotate 52
    compress
    delaycompress
    notifempty
    create 644 www-data www-data
    postrotate
        systemctl reload removealist-backend.service
    endscript
}

/var/log/gunicorn/*.log {
    daily
    missingok
    rotate 52
    compress
    delaycompress
    notifempty
    create 644 www-data www-data
    postrotate
        systemctl reload removealist-backend.service
    endscript
}

/var/log/celery/*.log {
    daily
    missingok
    rotate 52
    compress
    delaycompress
    notifempty
    create 644 www-data www-data
    postrotate
        systemctl restart removealist-celery.service
        systemctl restart removealist-celery-beat.service
    endscript
}
```

## 🔒 Security Hardening

### Firewall Configuration

```bash
# Configure UFW firewall
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw allow 'Nginx Full'
sudo ufw enable
```

### Fail2Ban Setup

```bash
# Install fail2ban
sudo apt install fail2ban

# Configure fail2ban
sudo nano /etc/fail2ban/jail.local
```

Add to jail.local:
```ini
[DEFAULT]
bantime = 3600
findtime = 600
maxretry = 5

[sshd]
enabled = true

[nginx-http-auth]
enabled = true

[nginx-limit-req]
enabled = true
filter = nginx-limit-req
logpath = /var/log/nginx/error.log
```

### Regular Security Updates

```bash
# Setup automatic security updates
sudo apt install unattended-upgrades
sudo dpkg-reconfigure -plow unattended-upgrades
```

## 📊 Monitoring & Maintenance

### Health Checks

Create a monitoring script:

```bash
#!/bin/bash
# /opt/removealist-backend/scripts/health_check.sh

# Check if services are running
systemctl is-active --quiet removealist-backend.service || echo "Backend service down"
systemctl is-active --quiet removealist-celery.service || echo "Celery worker down"
systemctl is-active --quiet removealist-celery-beat.service || echo "Celery beat down"
systemctl is-active --quiet postgresql || echo "PostgreSQL down"
systemctl is-active --quiet redis-server || echo "Redis down"
systemctl is-active --quiet nginx || echo "Nginx down"

# Check API health
curl -f http://localhost:8000/health/ > /dev/null || echo "API health check failed"

# Check disk space
df -h | awk '$5 > 80 {print "Disk usage high: " $0}'

# Check memory usage
free | awk 'NR==2{printf "Memory usage: %s/%s (%.2f%%)\n", $3,$2,$3*100/$2 }'
```

### Backup Strategy

```bash
#!/bin/bash
# /opt/removealist-backend/scripts/backup.sh

DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/opt/backups"

# Create backup directory
mkdir -p $BACKUP_DIR

# Database backup
sudo -u postgres pg_dump removealist_db > $BACKUP_DIR/db_backup_$DATE.sql

# Media files backup (if not using S3)
tar -czf $BACKUP_DIR/media_backup_$DATE.tar.gz /opt/removealist-backend/media/

# Keep only last 7 days of backups
find $BACKUP_DIR -name "*.sql" -mtime +7 -delete
find $BACKUP_DIR -name "*.tar.gz" -mtime +7 -delete
```

### Performance Monitoring

```bash
# Install and configure monitoring tools
pip install django-extensions
pip install django-debug-toolbar  # Only for staging

# Add to crontab for regular health checks
sudo crontab -e
# Add: */5 * * * * /opt/removealist-backend/scripts/health_check.sh
# Add: 0 2 * * * /opt/removealist-backend/scripts/backup.sh
```

## 🔄 Updates & Maintenance

### Deployment Updates

```bash
#!/bin/bash
# /opt/removealist-backend/scripts/deploy.sh

cd /opt/removealist-backend

# Pull latest changes
sudo -u www-data git pull origin main

# Activate virtual environment
sudo -u www-data bash -c "source venv/bin/activate && pip install -r requirements.txt"

# Run migrations
sudo -u www-data bash -c "source venv/bin/activate && python manage.py migrate"

# Collect static files
sudo -u www-data bash -c "source venv/bin/activate && python manage.py collectstatic --noinput"

# Restart services
sudo systemctl restart removealist-backend.service
sudo systemctl restart removealist-celery.service
sudo systemctl restart removealist-celery-beat.service

# Check status
sudo systemctl status removealist-backend.service
```

### Zero-Downtime Deployment

For zero-downtime deployments, consider using:
- **Blue-Green Deployment**: Maintain two identical production environments
- **Rolling Updates**: Update servers one by one
- **Load Balancer**: Use multiple backend servers

## 🆘 Troubleshooting

### Common Issues

1. **Service won't start**
   ```bash
   sudo journalctl -u removealist-backend.service -f
   ```

2. **Database connection issues**
   ```bash
   sudo -u www-data psql -h localhost -U removealist_user removealist_db
   ```

3. **Redis connection issues**
   ```bash
   redis-cli -a your_redis_password ping
   ```

4. **Static files not loading**
   ```bash
   sudo -u www-data python manage.py collectstatic --noinput
   ```

5. **Email not sending**
   ```bash
   # Check Celery logs
   tail -f /var/log/celery/worker.log
   ```

### Log Locations

- **Django**: `/var/log/django/removealist.log`
- **Gunicorn**: `/var/log/gunicorn/access.log`, `/var/log/gunicorn/error.log`
- **Celery**: `/var/log/celery/worker.log`, `/var/log/celery/beat.log`
- **Nginx**: `/var/log/nginx/removealist_access.log`, `/var/log/nginx/removealist_error.log`
- **PostgreSQL**: `/var/log/postgresql/postgresql-12-main.log`

This deployment guide provides a comprehensive setup for a production-ready RemoveList backend. Adjust configurations based on your specific requirements and infrastructure.
