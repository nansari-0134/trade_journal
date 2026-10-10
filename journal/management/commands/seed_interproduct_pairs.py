"""
Management command to seed inter-product pairs.
"""
from django.core.management.base import BaseCommand
from journal.models import InterProductPair

PAIRS = [
    ('CL-BZ', 'CL', 'BZ'),
    ('CL-BRN', 'CL', 'BRN'),
    ('HOU-WBS', 'HOU', 'WBS'),
    ('BRN-DBI', 'BRN', 'DBI'),
    ('BRN-ADM', 'BRN', 'ADM'),
    ('DBI-ADM', 'DBI', 'ADM'),
    ('WBS-BRN', 'WBS', 'BRN'),
    ('ZW-KE', 'ZW', 'KE'),
]

class Command(BaseCommand):
    help = 'Seed default interproduct pairs'

    def handle(self, *args, **options):
        created = 0
        updated = 0

        for name, p1, p2 in PAIRS:
            obj, was_created = InterProductPair.objects.update_or_create(
                name=name,
                defaults={
                    'product_1': p1,
                    'product_2': p2,
                }
            )
            if was_created:
                created += 1
            else:
                updated += 1

        self.stdout.write(self.style.SUCCESS(
            f'Done: {created} interproduct pairs created.'
        ))
