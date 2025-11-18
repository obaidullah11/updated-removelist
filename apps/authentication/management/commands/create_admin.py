"""
Django management command to create an admin user.
"""
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from django.db import transaction

User = get_user_model()


class Command(BaseCommand):
    help = 'Create an admin user for the admin panel'

    def add_arguments(self, parser):
        parser.add_argument(
            '--email',
            type=str,
            default='admin@removealist.com',
            help='Email address for the admin user (default: admin@removealist.com)'
        )
        parser.add_argument(
            '--password',
            type=str,
            default='admin123',
            help='Password for the admin user (default: admin123)'
        )
        parser.add_argument(
            '--first-name',
            type=str,
            default='Admin',
            help='First name for the admin user (default: Admin)'
        )
        parser.add_argument(
            '--last-name',
            type=str,
            default='User',
            help='Last name for the admin user (default: User)'
        )
        parser.add_argument(
            '--phone',
            type=str,
            default='+1234567890',
            help='Phone number for the admin user (default: +1234567890)'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force creation even if user already exists'
        )

    def handle(self, *args, **options):
        email = options['email']
        password = options['password']
        first_name = options['first_name']
        last_name = options['last_name']
        phone = options['phone']
        force = options['force']

        try:
            with transaction.atomic():
                # Check if user already exists
                if User.objects.filter(username=email).exists():
                    if not force:
                        raise CommandError(
                            f'User with email {email} already exists. '
                            'Use --force to update existing user.'
                        )
                    else:
                        # Update existing user
                        user = User.objects.get(username=email)
                        user.first_name = first_name
                        user.last_name = last_name
                        user.phone_number = phone
                        user.role_type = 'admin'
                        user.is_staff = True
                        user.is_superuser = True
                        user.is_email_verified = True
                        user.set_password(password)
                        user.save()
                        
                        self.stdout.write(
                            self.style.SUCCESS(
                                f'Successfully updated admin user: {email}'
                            )
                        )
                        return

                # Create new admin user
                user = User.objects.create_user(
                    username=email,  # Set username to email since USERNAME_FIELD is email
                    email=email,
                    password=password,
                    first_name=first_name,
                    last_name=last_name,
                    phone_number=phone,
                    role_type='admin',
                    is_staff=True,
                    is_superuser=True,
                    is_email_verified=True
                )

                self.stdout.write(
                    self.style.SUCCESS(
                        f'Successfully created admin user: {email}'
                    )
                )
                self.stdout.write(
                    self.style.WARNING(
                        f'Login credentials:\n'
                        f'Email: {email}\n'
                        f'Password: {password}\n'
                        f'Role: Admin'
                    )
                )

        except Exception as e:
            raise CommandError(f'Error creating admin user: {str(e)}')
