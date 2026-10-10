import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from journal.models import Trade, PositionAdjustment
from journal.services import open_trade, delete_adjustment

try:
    trade = open_trade(
        trade_type='Outright',
        direction='Long',
        size=1,
        price=100,
        legs=[{'product': 'CL', 'direction': 'Buy', 'ratio': 1, 'contract_month': 'M26'}]
    )
    print("Trade created:", trade.id)
    adj = trade.adjustments.first()
    print("Adjustment created:", adj.id)
    
    # Now simulate what adjustment_delete does
    delete_adjustment(adj.id)
    print("Adjustment deleted.")
    
    # Check trade state
    trade.refresh_from_db()
    print("Trade status:", trade.status)
    print("Trade legs count:", trade.legs.count())
    print("Trade adjustments count:", trade.adjustments.count())
except Exception as e:
    import traceback
    traceback.print_exc()
