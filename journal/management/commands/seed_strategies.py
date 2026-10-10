"""
Management command to seed default strategy templates.
Derived from the user's reference image showing ~35 predefined strategies.
"""
from django.core.management.base import BaseCommand
from journal.models import StrategyTemplate


# Strategy definitions from the reference image.
# Each tuple: (name, category, strategy_type, [leg_ratios])
# Ratios map to consecutive contract months. Positive=Buy, Negative=Sell.
# Zeros are included to show the month offset gaps.
DEFAULT_STRATEGIES = [
    # === Outrights ===
    ('OR', 'Spread', 'Calendar', [1]),

    # === Month Spreads ===
    ('1MS', 'Spread', 'Calendar', [1, -1]),
    ('2MS', 'Spread', 'Calendar', [1, 0, -1]),
    ('3MS', 'Spread', 'Calendar', [1, 0, 0, -1]),
    ('4MS', 'Spread', 'Calendar', [1, 0, 0, 0, -1]),
    ('5MS', 'Spread', 'Calendar', [1, 0, 0, 0, 0, -1]),
    ('6MS', 'Spread', 'Calendar', [1, 0, 0, 0, 0, 0, -1]),
    ('9MS', 'Spread', 'Calendar', [1, 0, 0, 0, 0, 0, 0, 0, 0, -1]),
    ('12MS', 'Spread', 'Calendar', [1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, -1]),
    ('24MS', 'Spread', 'Calendar', [1] + [0]*22 + [-1]),

    # === Month Flies (Butterflies) ===
    ('1MF', 'Butterfly', 'Calendar', [1, -2, 1]),
    ('2MF', 'Butterfly', 'Calendar', [1, 0, -2, 0, 1]),
    ('3MF', 'Butterfly', 'Calendar', [1, 0, 0, -2, 0, 0, 1]),
    ('6MF', 'Butterfly', 'Calendar', [1, 0, 0, 0, 0, 0, -2, 0, 0, 0, 0, 0, 1]),
    ('9MF', 'Butterfly', 'Calendar', [1, 0, 0, 0, 0, 0, 0, 0, 0, -2, 0, 0, 0, 0, 0, 0, 0, 0, 1]),
    ('12MF', 'Butterfly', 'Calendar', [1] + [0]*11 + [-2] + [0]*11 + [1]),

    # === Month Double Flies ===
    ('1MDF', 'DoubleFly', 'Calendar', [1, -3, 3, -1]),
    ('2MDF', 'DoubleFly', 'Calendar', [1, 0, -3, 0, 3, 0, -1]),
    ('3MDF', 'DoubleFly', 'Calendar', [1, 0, 0, -3, 0, 0, 3, 0, 0, -1]),
    ('6MDF', 'DoubleFly', 'Calendar', [1, 0, 0, 0, 0, 0, -3, 0, 0, 0, 0, 0, 3, 0, 0, 0, 0, 0, -1]),
    ('12MDF', 'DoubleFly', 'Calendar', [1] + [0]*11 + [-3] + [0]*11 + [3] + [0]*11 + [-1]),

    # === Box Spreads ===
    ('1mo Box Spd', 'Spread', 'Calendar', [1, -1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, -1, 0, 1]),
    ('2mo Box Spd', 'Spread', 'Calendar', [1, 0, -1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, -1, 0, 1]),

    # === Condors ===
    ('1M Condor', 'Butterfly', 'Calendar', [1, -1, -1, 1]),
    ('3M Condor', 'Butterfly', 'Calendar', [1, 0, 0, -1, 0, 0, -1, 0, 0, 1]),
    ('3M Ext Fly', 'Butterfly', 'Calendar', [1, 0, 0, 0, -2, 0, 0, 0, 0, 0, 0, 0, 1]),
    ('2M Condor', 'Butterfly', 'Calendar', [1, 0, -1, 0, 0, -1, 0, 1]),

    # === Generic Spreads (G = Generalized) ===
    ('G-1MS', 'Spread', 'Calendar', [1, -1]),
    ('G-2MS', 'Spread', 'Calendar', [1, 0, -1]),
    ('G-1MF', 'Butterfly', 'Calendar', [1, -2, 1]),
    ('G-2MF', 'Butterfly', 'Calendar', [1, 0, -2, 0, 1]),

    # === CSM ===
    ('CSM', 'Custom', 'Custom', []),

    # === Generic Condors/Flies ===
    ('G-1MC', 'Butterfly', 'Calendar', [1, -1, -1, 1]),
    ('G-Fly 2:1', 'Butterfly', 'Calendar', [2, -3, 1]),
    ('G-Fly 1:2', 'Butterfly', 'Calendar', [1, -3, 2]),

    # === Interproduct Specialized Templates ===
    ('1-1 IP Spread', 'InterProduct', 'InterProduct', [1, -1]),
    ('Ratio IP Spread (2:1)', 'InterProduct', 'InterProduct', [2, -1]),
    ('IP Fly', 'InterProduct', 'InterProduct', [1, -2, 1]),
]


class Command(BaseCommand):
    help = 'Seed default strategy templates'

    def handle(self, *args, **options):
        created = 0
        updated = 0

        for name, category, strat_type, ratios in DEFAULT_STRATEGIES:
            obj, was_created = StrategyTemplate.objects.update_or_create(
                name=name,
                defaults={
                    'category': category,
                    'strategy_type': strat_type,
                    'leg_ratios': ratios,
                    'is_default': True,
                }
            )

            if was_created:
                created += 1
            else:
                updated += 1

        self.stdout.write(self.style.SUCCESS(
            f'Done: {created} created, {updated} updated, '
            f'{StrategyTemplate.objects.count()} total'
        ))
