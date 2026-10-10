import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'trade_journal.settings')
django.setup()

from journal.models import Trade, PositionAdjustment
from journal import services
import traceback

trade = Trade.objects.first()
print(f"Testing delete for trade ID: {trade.id}")
if trade.adjustments.exists():
    adj = trade.adjustments.last()
    print(f"Found adjustment: ID={adj.id}, Action={adj.action}, Size={adj.size_change}")
    
    try:
        services.delete_adjustment(adj.id)
        print("Delete successful!")
    except Exception as e:
        print("Exception during delete:")
        traceback.print_exc()
else:
    print("No adjustments found for this trade.")
