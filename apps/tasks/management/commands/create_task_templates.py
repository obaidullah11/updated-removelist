"""
Management command to create initial task templates.
"""
from django.core.management.base import BaseCommand
from apps.tasks.models import TaskTemplate


class Command(BaseCommand):
    help = 'Create initial task templates'

    def handle(self, *args, **options):
        templates = [
            # Current Address Tasks
            {
                'title': 'Council Kerbside Booking',
                'description': 'Book council kerbside collection for unwanted items',
                'category': 'council',
                'location': 'current',
                'priority': 'medium',
                'is_external': True,
                'external_url': 'https://www.council.nsw.gov.au/kerbside',
                'subtasks': []
            },
            {
                'title': 'Address Change Checklist',
                'description': 'Update address with banks, insurance, subscriptions',
                'category': 'address_change',
                'location': 'current',
                'priority': 'high',
                'is_external': False,
                'subtasks': [
                    'Bank and credit cards',
                    'Insurance companies',
                    'Employer/HR department',
                    'Tax office',
                    'Electoral roll',
                    'Subscriptions and memberships'
                ]
            },
            {
                'title': 'First Night Bag - Adults',
                'description': 'Pack essentials for the first night in new home',
                'category': 'first_night',
                'location': 'current',
                'priority': 'high',
                'is_external': False,
                'subtasks': [
                    'Change of clothes',
                    'Toiletries',
                    'Medications',
                    'Phone chargers',
                    'Important documents',
                    'Snacks and water'
                ]
            },
            {
                'title': 'First Night Bag - Children',
                'description': 'Pack children\'s essentials and comfort items',
                'category': 'first_night',
                'location': 'current',
                'priority': 'high',
                'is_external': False,
                'subtasks': [
                    'Favorite toys/comfort items',
                    'Extra clothes',
                    'Diapers/supplies',
                    'Snacks and drinks',
                    'Entertainment (books, tablets)',
                    'Any special medications'
                ]
            },
            {
                'title': 'First Night Bag - Pets',
                'description': 'Prepare pet essentials for moving day',
                'category': 'first_night',
                'location': 'current',
                'priority': 'high',
                'is_external': False,
                'subtasks': [
                    'Food and water bowls',
                    'Pet food for 2-3 days',
                    'Leash and collar with ID',
                    'Favorite toys/blankets',
                    'Litter box (cats)',
                    'Medications and vet records'
                ]
            },
            
            # Utilities Tasks
            {
                'title': 'Electricity Service',
                'description': 'Disconnect current and connect new electricity service',
                'category': 'electricity',
                'location': 'utilities',
                'priority': 'high',
                'is_external': False,
                'subtasks': [
                    'Contact current provider for disconnection',
                    'Research providers for new address',
                    'Schedule connection at new property',
                    'Submit meter readings'
                ]
            },
            {
                'title': 'Gas Service',
                'description': 'Transfer or setup gas connection',
                'category': 'gas',
                'location': 'utilities',
                'priority': 'high',
                'is_external': False,
                'subtasks': [
                    'Contact current gas provider',
                    'Arrange disconnection',
                    'Setup new connection',
                    'Schedule safety inspection'
                ]
            },
            {
                'title': 'Water Service',
                'description': 'Transfer water and sewerage services',
                'category': 'water',
                'location': 'utilities',
                'priority': 'high',
                'is_external': False,
                'subtasks': [
                    'Contact water authority',
                    'Arrange final reading',
                    'Setup account for new address',
                    'Update payment details'
                ]
            },
            {
                'title': 'Internet Service',
                'description': 'Transfer or setup internet connection',
                'category': 'internet',
                'location': 'utilities',
                'priority': 'medium',
                'is_external': False,
                'subtasks': [
                    'Contact current ISP',
                    'Check availability at new address',
                    'Schedule installation',
                    'Return old equipment if needed'
                ]
            },
            {
                'title': 'Phone Service',
                'description': 'Transfer landline and mobile services',
                'category': 'phone',
                'location': 'utilities',
                'priority': 'low',
                'is_external': False,
                'subtasks': [
                    'Contact phone provider',
                    'Update service address',
                    'Port numbers if changing providers',
                    'Update emergency contacts'
                ]
            },
            {
                'title': 'Insurance Updates',
                'description': 'Update home, contents, and vehicle insurance',
                'category': 'insurance',
                'location': 'utilities',
                'priority': 'high',
                'is_external': False,
                'subtasks': [
                    'Home/contents insurance',
                    'Vehicle insurance',
                    'Update policy addresses',
                    'Review coverage levels',
                    'Get quotes for new area'
                ]
            },
            
            # Vehicle Tasks
            {
                'title': 'Vehicle Registration Update',
                'description': 'Update vehicle registration with new address',
                'category': 'registration',
                'location': 'vehicles',
                'priority': 'medium',
                'is_external': False,
                'subtasks': [
                    'Update registration details',
                    'Change license address',
                    'Update insurance',
                    'Notify finance company if applicable'
                ]
            },
            
            # Garage Sale Tasks
            {
                'title': 'Garage Sale Planning',
                'description': 'Organize garage sale to reduce moving load',
                'category': 'garage_sale',
                'location': 'garage_sale',
                'priority': 'low',
                'is_external': False,
                'subtasks': [
                    'Sort items to sell',
                    'Price items',
                    'Advertise sale',
                    'Prepare change and bags',
                    'Plan sale layout'
                ]
            }
        ]

        created_count = 0
        for template_data in templates:
            template, created = TaskTemplate.objects.get_or_create(
                title=template_data['title'],
                category=template_data['category'],
                location=template_data['location'],
                defaults=template_data
            )
            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'Created task template: {template.title}')
                )

        self.stdout.write(
            self.style.SUCCESS(f'Successfully created {created_count} task templates')
        )

