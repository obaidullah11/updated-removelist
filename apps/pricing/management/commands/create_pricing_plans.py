"""
Management command to create initial pricing plans.
"""
from django.core.management.base import BaseCommand
from apps.pricing.models import PricingPlan


class Command(BaseCommand):
    help = 'Create initial pricing plans'

    def handle(self, *args, **options):
        # Free Plan
        free_plan, created = PricingPlan.objects.get_or_create(
            plan_type='free',
            defaults={
                'name': 'Free',
                'description': 'Basic moving features to get you started',
                'price_monthly': 0.00,
                'price_yearly': 0.00,
                'features': [
                    'Basic move planning',
                    'Simple inventory tracking',
                    'Basic timeline',
                    'Community support'
                ],
                'date_changes_allowed': 0,
                'location_multipliers': {},
                'timeline_multipliers': {},
                'move_type_multipliers': {},
                'is_active': True,
                'is_popular': False
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS('Created Free plan'))

        # Plan+ 
        plus_plan, created = PricingPlan.objects.get_or_create(
            plan_type='plus',
            defaults={
                'name': 'Plan +',
                'description': 'Enhanced features for a smoother moving experience',
                'price_monthly': 49.00,
                'price_yearly': 490.00,
                'features': [
                    'Everything in Free',
                    'Advanced inventory with QR codes',
                    'Task management with timers',
                    'Service provider marketplace',
                    'Priority support',
                    '1-2 date changes allowed',
                    'Export inventory to PDF/Excel'
                ],
                'date_changes_allowed': 2,
                'location_multipliers': {
                    'sydney': 1.2,
                    'melbourne': 1.1,
                    'brisbane': 1.05,
                    'perth': 1.15,
                    'adelaide': 1.0,
                    'canberra': 1.1
                },
                'timeline_multipliers': {
                    'urgent': 1.5,
                    'standard': 1.0,
                    'flexible': 0.9
                },
                'move_type_multipliers': {
                    'interstate': 1.3,
                    'local': 1.0,
                    'international': 1.5
                },
                'is_active': True,
                'is_popular': True
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS('Created Plan+ plan'))

        # Concierge+
        concierge_plan, created = PricingPlan.objects.get_or_create(
            plan_type='concierge',
            defaults={
                'name': 'Concierge +',
                'description': 'Premium white-glove moving experience',
                'price_monthly': 149.00,
                'price_yearly': 1490.00,
                'features': [
                    'Everything in Plan+',
                    'Dedicated move coordinator',
                    'Unlimited date changes',
                    'Premium service providers',
                    'Insurance coordination',
                    'Storage management',
                    'Post-move support',
                    '24/7 priority support',
                    'Custom moving timeline',
                    'Professional packing coordination'
                ],
                'date_changes_allowed': -1,  # Unlimited
                'location_multipliers': {
                    'sydney': 1.3,
                    'melbourne': 1.2,
                    'brisbane': 1.15,
                    'perth': 1.25,
                    'adelaide': 1.1,
                    'canberra': 1.2
                },
                'timeline_multipliers': {
                    'urgent': 1.8,
                    'standard': 1.0,
                    'flexible': 0.85
                },
                'move_type_multipliers': {
                    'interstate': 1.5,
                    'local': 1.0,
                    'international': 2.0
                },
                'is_active': True,
                'is_popular': False
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS('Created Concierge+ plan'))

        self.stdout.write(self.style.SUCCESS('Successfully created all pricing plans'))

