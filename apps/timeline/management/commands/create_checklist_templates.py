"""
Management command to create default checklist templates.
"""
from django.core.management.base import BaseCommand
from apps.timeline.models import ChecklistTemplate


class Command(BaseCommand):
    help = 'Create default checklist templates for new moves'

    def handle(self, *args, **options):
        """Create default checklist templates."""
        
        # Clear existing templates
        ChecklistTemplate.objects.all().delete()
        
        templates = [
            # 8 Weeks Before
            {'title': 'Research moving companies and get quotes', 'week': 8, 'priority': 'high'},
            {'title': 'Create a moving budget', 'week': 8, 'priority': 'high'},
            {'title': 'Start decluttering and donating items', 'week': 8, 'priority': 'medium'},
            {'title': 'Research your new neighborhood', 'week': 8, 'priority': 'low'},
            {'title': 'Start using up frozen and perishable food', 'week': 8, 'priority': 'medium'},
            
            # 6 Weeks Before
            {'title': 'Book your moving company', 'week': 6, 'priority': 'high'},
            {'title': 'Order moving supplies (boxes, tape, bubble wrap)', 'week': 6, 'priority': 'high'},
            {'title': 'Start collecting important documents', 'week': 6, 'priority': 'high'},
            {'title': 'Research schools if you have children', 'week': 6, 'priority': 'medium'},
            {'title': 'Plan time off work for moving day', 'week': 6, 'priority': 'medium'},
            
            # 4 Weeks Before
            {'title': 'Notify utility companies of your move', 'week': 4, 'priority': 'high'},
            {'title': 'Update address with bank and credit cards', 'week': 4, 'priority': 'high'},
            {'title': 'Register to vote at new address', 'week': 4, 'priority': 'medium'},
            {'title': 'Transfer prescriptions to new pharmacy', 'week': 4, 'priority': 'medium'},
            {'title': 'Start packing non-essential items', 'week': 4, 'priority': 'medium'},
            {'title': 'Arrange childcare for moving day', 'week': 4, 'priority': 'medium'},
            
            # 2 Weeks Before
            {'title': 'Confirm details with moving company', 'week': 2, 'priority': 'high'},
            {'title': 'Submit change of address with postal service', 'week': 2, 'priority': 'high'},
            {'title': 'Update address with insurance companies', 'week': 2, 'priority': 'high'},
            {'title': 'Notify subscription services of address change', 'week': 2, 'priority': 'medium'},
            {'title': 'Arrange pet transportation', 'week': 2, 'priority': 'medium'},
            {'title': 'Pack a suitcase with essentials', 'week': 2, 'priority': 'medium'},
            
            # 1 Week Before
            {'title': 'Pack everything except daily essentials', 'week': 1, 'priority': 'high'},
            {'title': 'Confirm utility connections at new home', 'week': 1, 'priority': 'high'},
            {'title': 'Get cash for moving day tips', 'week': 1, 'priority': 'medium'},
            {'title': 'Pack cleaning supplies for both homes', 'week': 1, 'priority': 'medium'},
            {'title': 'Charge all electronic devices', 'week': 1, 'priority': 'low'},
            {'title': 'Prepare snacks and water for moving day', 'week': 1, 'priority': 'low'},
            
            # Moving Day (Week 0)
            {'title': 'Be ready before movers arrive', 'week': 0, 'priority': 'high'},
            {'title': 'Do final walkthrough of old home', 'week': 0, 'priority': 'high'},
            {'title': 'Keep important documents with you', 'week': 0, 'priority': 'high'},
            {'title': 'Take photos of valuable items', 'week': 0, 'priority': 'medium'},
            {'title': 'Check inventory list with movers', 'week': 0, 'priority': 'high'},
            {'title': 'Keep phone charged and accessible', 'week': 0, 'priority': 'medium'},
        ]
        
        created_count = 0
        for template_data in templates:
            template, created = ChecklistTemplate.objects.get_or_create(
                title=template_data['title'],
                week=template_data['week'],
                defaults={
                    'priority': template_data['priority'],
                    'is_active': True
                }
            )
            if created:
                created_count += 1
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully created {created_count} checklist templates'
            )
        )
