"""
Service layer for trade operations.
All business logic lives here – views should only call these functions.
"""
from django.db import transaction
from django.utils import timezone
from .models import Trade, TradeLeg, PositionAdjustment, PlannedTrade
from . import utils as product_utils
from . import market_data


# ---------------------------------------------------------------------------
# Trade lifecycle
# ---------------------------------------------------------------------------

@transaction.atomic
def open_trade(
    trade_type: str,
    direction: str,
    legs: list[dict],
    size: float,
    price: float | None = None,
    strategy_label: str = '',
    notes: str = '',
) -> Trade:
    """
    Create a new trade with its legs and an initial 'Open' position adjustment.

    Args:
        trade_type: One of Trade.TRADE_TYPE_CHOICES values.
        direction: 'Long' or 'Short'.
        legs: List of dicts, each with keys:
              product, product_group, contract_month, direction, ratio
        size: Initial position size (positive).
        price: Entry price (optional).
        strategy_label: User-defined label.
        notes: Free-text notes.

    Returns:
        The created Trade instance.
    """
    trade = Trade.objects.create(
        trade_type=trade_type,
        direction=direction,
        status='Open',
        strategy_label=strategy_label,
        notes=notes,
    )

    # Auto-generate strategy_label if not provided and legs exist
    if not strategy_label and legs:
        first_leg = legs[0]
        prod = first_leg.get('product', '')
        month = first_leg.get('contract_month', '')
        # We'll set a placeholder for the strategy name if we don't have the template yet
        # though template is usually linked in the view.
        # Let's refine this in the view as well if possible, or here if we pass template.
        trade.strategy_label = f"{prod} {month} {trade_type}".strip()
        trade.save()

    from .models import InterProductPair
    products_info = product_utils.get_products_data()

    for leg_data in legs:
        product_name = leg_data.get('product', '')
        ratio = float(leg_data.get('ratio', 1))
        direction = leg_data.get('direction', 'Buy')
        month = leg_data.get('contract_month', '')
        
        # Check if this "product" is actually an inter-product pair
        pair = InterProductPair.objects.filter(name=product_name).first()
        if pair:
            # Expand into 2 legs
            for pi, sym in enumerate([pair.product_1, pair.product_2]):
                leg_direction = direction if pi == 0 else ('Sell' if direction == 'Buy' else 'Buy')
                info = products_info.get(sym, {})
                TradeLeg.objects.create(
                    trade=trade,
                    product=sym,
                    product_group=info.get('group', ''),
                    contract_month=month,
                    direction=leg_direction,
                    ratio=ratio,
                )
        else:
            # Standard single leg
            info = products_info.get(product_name, {})
            TradeLeg.objects.create(
                trade=trade,
                product=product_name,
                product_group=info.get('group', leg_data.get('product_group', '')),
                contract_month=month,
                direction=direction,
                ratio=ratio,
            )

    PositionAdjustment.objects.create(
        trade=trade,
        action='Open',
        size_change=abs(size),
        price=price,
        notes=notes,
    )

    return trade


def _get_multiplier(trade) -> float:
    """Get the point value multiplier for a trade based on its first leg."""
    first_leg = trade.legs.first()
    if not first_leg:
        return 1.0
    
    products = product_utils.get_products_data()
    p_info = products.get(first_leg.product)
    if not p_info:
        return 1.0
    
    tick_size = p_info.get('tick_size', 0.01)
    tick_value = p_info.get('tick_value', 1.0)
    point_value = p_info.get('point_value', 0.0)
    fx_rate = p_info.get('fx_rate', 1.0)
    display_factor = p_info.get('display_factor', 1.0)
    
    # Formula: (pointValue / displayFactor) * fxRate
    # This correctly scales ES (0.5 / 0.01 = 50) and Crude (1000 / 1 = 1000)
    if point_value > 0 and display_factor > 0:
        return (point_value / display_factor) * fx_rate
        
    return (tick_value / tick_size if tick_size > 0 else 1.0) * fx_rate


@transaction.atomic
def add_position(trade_id, size: float, price: float | None = None, notes: str = '') -> Trade:
    """Add to an existing trade (even if closed)."""
    trade = Trade.objects.get(pk=trade_id)

    PositionAdjustment.objects.create(
        trade=trade,
        action='Add',
        size_change=abs(size),
        price=price,
        notes=notes,
    )
    trade.status = 'Open'
    trade.save()
    return trade


@transaction.atomic
def reduce_position(
    trade_id,
    size: float,
    price: float | None = None,
    notes: str = '',
) -> Trade:
    """Reduce (partially close) a position on an existing trade."""
    trade = Trade.objects.get(pk=trade_id)

    current_size = trade.total_open_size
    reduce_qty = min(abs(size), current_size)

    pnl = 0.0
    if price is not None:
        # Auto-calculate PnL using multiplier: (Exit - Entry) * Multiplier * Qty
        avg_entry = trade.avg_entry_price
        multiplier = _get_multiplier(trade)
        if avg_entry:
            if trade.direction == 'Long':
                pnl = round((price - avg_entry) * multiplier * reduce_qty, 4)
            else:
                pnl = round((avg_entry - price) * multiplier * reduce_qty, 4)

    PositionAdjustment.objects.create(
        trade=trade,
        action='Reduce',
        size_change=-reduce_qty,
        price=price,
        pnl=pnl,
        notes=notes,
    )

    new_size = trade.total_open_size
    if new_size <= 0:
        trade.status = 'Closed'
    else:
        trade.status = 'PartiallyReduced'
    trade.save()
    return trade


@transaction.atomic
def close_trade(trade_id, price: float | None = None, notes: str = '') -> Trade:
    """Fully close a trade."""
    trade = Trade.objects.get(pk=trade_id)
    current_size = trade.total_open_size

    pnl = 0.0
    if current_size > 0:
        if price is not None:
            # Auto-calculate PnL
            avg_entry = trade.avg_entry_price
            multiplier = _get_multiplier(trade)
            if avg_entry:
                if trade.direction == 'Long':
                    pnl = round((price - avg_entry) * multiplier * current_size, 4)
                else:
                    pnl = round((avg_entry - price) * multiplier * current_size, 4)

        PositionAdjustment.objects.create(
            trade=trade,
            action='Close',
            size_change=-current_size,
            price=price,
            pnl=pnl,
            notes=notes,
        )

    trade.status = 'Closed'
    trade.save()
    return trade


@transaction.atomic
def recalculate_trade_state(trade_id):
    """
    Re-processes all adjustments for a trade in chronological order.
    Corrects pnl values for Reduce/Close actions and determines final status.
    """
    trade = Trade.objects.get(pk=trade_id)
    # Important: sort by timestamp ASC to re-simulate
    adjs = trade.adjustments.all().order_by('timestamp')
    
    current_size = 0.0
    multiplier = _get_multiplier(trade)
    
    # We need to track the average entry price manually as we progress
    # because the trade.avg_entry_price property looks at the DATABASE state,
    # and we are in the middle of re-calculating it.
    running_total_entry_size = 0.0
    running_weighted_entry_sum = 0.0
    
    for adj in adjs:
        if adj.action in ('Open', 'Add'):
            current_size += abs(adj.size_change)
            if adj.price is not None:
                running_total_entry_size += abs(adj.size_change)
                running_weighted_entry_sum += abs(adj.size_change) * adj.price
            # Reset PnL for entry actions just in case
            adj.pnl = 0.0
        
        elif adj.action in ('Reduce', 'Close'):
            reduce_qty = min(abs(adj.size_change), current_size)
            
            # Recalculate PnL based on current running average entry
            current_avg_entry = running_weighted_entry_sum / running_total_entry_size if running_total_entry_size > 0 else 0
            
            pnl = 0.0
            if adj.price is not None and current_avg_entry is not None:
                if trade.direction == 'Long':
                    pnl = round((adj.price - current_avg_entry) * multiplier * reduce_qty, 6)
                else:
                    pnl = round((current_avg_entry - adj.price) * multiplier * reduce_qty, 6)
            
            adj.pnl = pnl
            current_size -= reduce_qty
            # Note: We DON'T reduce the running entry basis on reduction 
            # (standard FIFO/weighted-average behavior usually keeps the basis until new buys)
            # If current_size hits 0, we typically reset the basis for the next "Open/Add"
            if current_size <= 0:
                running_total_entry_size = 0.0
                running_weighted_entry_sum = 0.0

        adj.save()

    # Final Status Update
    has_reduction = any(a.action in ['Reduce', 'Close'] for a in adjs)
    if current_size <= 0:
        trade.status = 'Closed'
    elif has_reduction:
        trade.status = 'PartiallyReduced'
    else:
        trade.status = 'Open'
    
    trade.save()
    return trade


@transaction.atomic
def update_adjustment(adj_id, size_change=None, price=None, notes=None):
    """Update an adjustment and trigger recalculation."""
    adj = PositionAdjustment.objects.get(pk=adj_id)
    if size_change is not None:
        size_change = float(size_change)
        if adj.action in ('Open', 'Add'):
            adj.size_change = abs(size_change)
        elif adj.action in ('Reduce', 'Close'):
            adj.size_change = -abs(size_change)
        else:
            adj.size_change = size_change
    if price is not None:
        adj.price = price
    if notes is not None:
        adj.notes = notes
    adj.save()
    recalculate_trade_state(adj.trade.id)
    return adj


@transaction.atomic
def delete_adjustment(adj_id):
    """Delete an adjustment and trigger recalculation."""
    adj = PositionAdjustment.objects.get(pk=adj_id)
    trade_id = adj.trade.id
    adj.delete()
    recalculate_trade_state(trade_id)


# ---------------------------------------------------------------------------
# PnL helpers
# ---------------------------------------------------------------------------

def get_realized_pnl(trade_id) -> float:
    """Total realized PnL for a trade (sum of Reduce/Close adjustment PnLs)."""
    trade = Trade.objects.get(pk=trade_id)
    return trade.realized_pnl


def get_unrealized_pnl(trade_id) -> float | None:
    """
    Unrealized PnL based on live market price.
    Returns None if market price is unavailable.
    """
    trade = Trade.objects.get(pk=trade_id)
    if trade.status == 'Closed':
        return 0.0

    open_size = trade.total_open_size
    avg_entry = trade.avg_entry_price
    if open_size == 0 or avg_entry == 0:
        return None

    # Get primary product from first leg
    first_leg = trade.legs.first()
    if not first_leg:
        return None

    live_price = market_data.get_live_price(first_leg.product, first_leg.contract_month)
    if live_price is None:
        return None

    multiplier = _get_multiplier(trade)
    if trade.direction == 'Long':
        return round((live_price - avg_entry) * multiplier * open_size, 4)
    else:
        return round((avg_entry - live_price) * multiplier * open_size, 4)


def get_trade_summary(trade_id) -> dict:
    """Aggregated summary view for a single trade."""
    trade = Trade.objects.get(pk=trade_id)
    legs = list(trade.legs.values('product', 'product_group', 'contract_month', 'direction', 'ratio'))
    adjustments = list(trade.adjustments.values('timestamp', 'action', 'size_change', 'price', 'pnl', 'notes'))

    return {
        'id': str(trade.id),
        'trade_type': trade.trade_type,
        'direction': trade.direction,
        'status': trade.status,
        'strategy_label': trade.strategy_label,
        'notes': trade.notes,
        'created_at': trade.created_at,
        'updated_at': trade.updated_at,
        'legs': legs,
        'adjustments': adjustments,
        'total_open_size': trade.total_open_size,
        'avg_entry_price': trade.avg_entry_price,
        'realized_pnl': trade.realized_pnl,
        'unrealized_pnl': get_unrealized_pnl(trade_id),
    }


# ---------------------------------------------------------------------------
# Transaction cost helpers
# ---------------------------------------------------------------------------

def calculate_tc_for_trade(trade) -> dict:
    """
    Calculate total TC pre/post rebate across all legs of a trade.
    Uses the current total open size and the leg ratios.
    """
    products = product_utils.get_products_data()
    total_tc_pre = 0.0
    total_tc_post = 0.0
    open_size = trade.total_open_size

    for leg in trade.legs.all():
        if leg.product in products:
            unit_pre = products[leg.product]['tc_pre']
            unit_post = products[leg.product]['tc_post']
            leg_size = abs(open_size * leg.ratio)
            total_tc_pre += unit_pre * leg_size
            total_tc_post += unit_post * leg_size

    return {
        'tc_prerebate': round(total_tc_pre, 4),
        'tc_postrebate': round(total_tc_post, 4),
    }


def calculate_total_realized_tc(trade) -> dict:
    """
    Calculate total transaction costs for all adjustments (all lots traded).
    Used for closed or partially closed trades to calculate true net profit.
    """
    products = product_utils.get_products_data()
    total_tc_pre = 0.0
    total_tc_post = 0.0
    
    # Sum of absolute size changes (every lot opened or closed costs TC)
    volume = sum(abs(adj.size_change) for adj in trade.adjustments.all())

    for leg in trade.legs.all():
        if leg.product in products:
            unit_pre = products[leg.product]['tc_pre']
            unit_post = products[leg.product]['tc_post']
            leg_volume = volume * abs(leg.ratio)
            total_tc_pre += unit_pre * leg_volume
            total_tc_post += unit_post * leg_volume

    return {
        'tc_prerebate': round(total_tc_pre, 6),
        'tc_postrebate': round(total_tc_post, 6),
    }


def calculate_target_pnl(trade) -> float:
    """
    Calculate potential PnL if initial target was reached for the full initial size.
    """
    if not trade.target:
        return 0.0
        
    avg_entry = trade.avg_entry_price
    if not avg_entry:
        return 0.0
        
    # Initial size is total of all 'Open' and 'Add' actions
    initial_size = sum(adj.size_change for adj in trade.adjustments.filter(action__in=['Open', 'Add']))
    if initial_size == 0:
        return 0.0
        
    multiplier = _get_multiplier(trade)
    if trade.direction == 'Long':
        return round((trade.target - avg_entry) * multiplier * initial_size, 4)
    else:
        return round((avg_entry - trade.target) * multiplier * initial_size, 4)


# ---------------------------------------------------------------------------
# Strategy usage tracking
# ---------------------------------------------------------------------------

def get_most_used_strategies(limit: int = 5) -> list[str]:
    """Return strategy labels ordered by most-used (by trade count)."""
    from django.db.models import Count
    qs = (
        Trade.objects
        .exclude(strategy_label='')
        .values('strategy_label')
        .annotate(count=Count('id'))
        .order_by('-count')[:limit]
    )
    return [item['strategy_label'] for item in qs]


# ---------------------------------------------------------------------------
# Planned trades
# ---------------------------------------------------------------------------

@transaction.atomic
def create_planned_trade(**kwargs) -> PlannedTrade:
    """Create a new planned trade."""
    return PlannedTrade.objects.create(**kwargs)


def get_active_planned_trades():
    """Return all planned trades that haven't been executed or cancelled."""
    return PlannedTrade.objects.filter(status='Planned')


def execute_planned_trade(planned_id) -> PlannedTrade:
    """Mark a planned trade as executed."""
    pt = PlannedTrade.objects.get(pk=planned_id)
    pt.status = 'Executed'
    pt.save()
    return pt
