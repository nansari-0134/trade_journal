from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from collections import defaultdict
from .models import Trade, PlannedTrade, StrategyTemplate, InterProductPair, PositionAdjustment, CotReport, PalmOilPriceAndOI, MPOBData, ExportSurveyorData
from . import services
from . import utils as product_utils
import json
import calendar
from datetime import datetime, date, timedelta


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

def dashboard(request):
    open_trades = Trade.objects.filter(status__in=['Open', 'PartiallyReduced']).prefetch_related('legs', 'adjustments')
    closed_trades = Trade.objects.filter(status='Closed').prefetch_related('legs', 'adjustments')
    planned_trades = services.get_active_planned_trades()

    open_summaries = []
    total_fees = 0.0
    for t in open_trades:
        tc = services.calculate_tc_for_trade(t)
        tc_realized = services.calculate_total_realized_tc(t)
        total_fees += abs(tc_realized['tc_postrebate'])
        open_summaries.append({
            'trade': t,
            'legs': t.legs.all(),
            'open_size': t.total_open_size,
            'avg_entry': t.avg_entry_price,
            'realized_pnl': t.realized_pnl,
            'unrealized_pnl': services.get_unrealized_pnl(t.id),
            'tc_pre': tc['tc_prerebate'],
            'tc_post': tc['tc_postrebate'],
        })

    closed_summaries = []
    total_realized = 0.0
    total_win_pnl = 0.0
    total_loss_pnl = 0.0
    win_count = 0
    loss_count = 0

    for t in closed_trades:
        tc_realized = services.calculate_total_realized_tc(t)
        rpnl = t.realized_pnl
        target_pnl = services.calculate_target_pnl(t)
        
        total_realized += rpnl
        total_fees += abs(tc_realized['tc_postrebate'])
        
        if rpnl > 0:
            win_count += 1
            total_win_pnl += rpnl
        elif rpnl < 0:
            loss_count += 1
            total_loss_pnl += abs(rpnl)
            
        closed_summaries.append({
            'trade': t,
            'legs': t.legs.all(),
            'trade_date': t.created_at,
            'gross_pnl': rpnl,
            'target_pnl': target_pnl,
            'net_excl_rebate': round(rpnl - abs(tc_realized['tc_prerebate']), 2),
            'net_incl_rebate': round(rpnl - abs(tc_realized['tc_postrebate']), 2),
            'tc_pre': abs(tc_realized['tc_prerebate']),
            'tc_post': abs(tc_realized['tc_postrebate']),
        })

    total_closed = len(closed_summaries)
    win_rate = (win_count / total_closed * 100) if total_closed > 0 else 0
    
    avg_win = (total_win_pnl / win_count) if win_count > 0 else 0
    avg_loss = (total_loss_pnl / loss_count) if loss_count > 0 else 0
    avg_win_loss = round(avg_win / avg_loss, 2) if avg_loss > 0 else (round(avg_win, 2) if avg_win > 0 else 0)

    # Chart Data: Cumulative Net PnL based on PositionAdjustments
    adjs = PositionAdjustment.objects.all().order_by('timestamp').select_related('trade').prefetch_related('trade__legs')
    daily_net_pnl = defaultdict(float)
    products_data = product_utils.get_products_data()
    
    for adj in adjs:
        date_str = adj.timestamp.strftime('%b %d')
        
        # Calculate TC for this adjustment
        trade = adj.trade
        volume = abs(adj.size_change)
        tc_post = 0.0
        for leg in trade.legs.all():
            if leg.product in products_data:
                tc_post += abs(products_data[leg.product]['tc_post']) * volume * abs(leg.ratio)
        
        daily_net_pnl[date_str] += (adj.pnl - tc_post)

    chart_labels = []
    chart_data = []
    cumulative = 0.0
    for d, pnl in daily_net_pnl.items():
        cumulative += pnl
        chart_labels.append(d)
        chart_data.append(round(cumulative, 4))

    if not chart_labels:
        chart_labels = ['No Data']
        chart_data = [0]

    # Sort closed summaries by created_at desc (already happening naturally by query order if ordering applied, but manual sort ensures it)
    closed_summaries.sort(key=lambda x: x['trade_date'], reverse=True)

    context = {
        'open_summaries': open_summaries,
        'closed_summaries': closed_summaries,
        'planned_trades': planned_trades,
        'total_trades': open_trades.count() + closed_trades.count(),
        'total_open': open_trades.count(),
        'total_open_long': open_trades.filter(direction='Long').count(),
        'total_open_short': open_trades.filter(direction='Short').count(),
        'total_realized': round(total_realized, 2),
        'total_fees': round(total_fees, 2),
        'net_pnl': round(total_realized - total_fees, 2),
        'win_rate': round(win_rate, 2),
        'avg_win_loss': avg_win_loss,
        'chart_labels': json.dumps(chart_labels),
        'chart_data': json.dumps(chart_data),
        'product_groups': product_utils.get_product_groups(),
        'contract_months': product_utils.get_contract_months(),
        'trade_types': Trade.TRADE_TYPE_CHOICES,
    }
    return render(request, 'journal/dashboard.html', context)


# ---------------------------------------------------------------------------
# New Trade Page
# ---------------------------------------------------------------------------

def trade_new(request):
    """Dedicated new trade page with strategy quick-pick."""
    strategies = StrategyTemplate.objects.all()
    # Group strategies by category, but remove 'InterProduct' as requested
    strategy_groups = {}
    for s in strategies:
        if s.category == 'InterProduct':
            continue
        cat = s.get_category_display()
        strategy_groups.setdefault(cat, [])
        strategy_groups[cat].append(s)

    pairs = InterProductPair.objects.all()
    product_groups = product_utils.get_product_groups()
    if pairs.exists():
        product_groups['Interproduct Pairs'] = [p.name for p in pairs]
    context = {
        'product_groups': product_groups,
        'contract_months': product_utils.get_contract_months(),
        'trade_types': Trade.TRADE_TYPE_CHOICES,
        'strategy_groups': strategy_groups,
        'strategies_json': json.dumps([
            {
                'id': str(s.id), 
                'name': s.name, 
                'category': s.category, 
                'strategy_type': s.strategy_type,
                'leg_ratios': s.leg_ratios
            }
            for s in strategies
        ]),
        'pairs_json': json.dumps([
            {'id': str(p.id), 'name': p.name, 'p1': p.product_1, 'p2': p.product_2}
            for p in pairs
        ]),
        'contract_months_json': json.dumps(product_utils.get_contract_months()),
    }
    return render(request, 'journal/trade_new.html', context)


# ---------------------------------------------------------------------------
# Trade CRUD
# ---------------------------------------------------------------------------

def trade_add(request):
    if request.method != 'POST':
        return redirect('journal:trade_new')

    import datetime as dt
    trade_type = request.POST.get('trade_type', 'Outright')
    direction = request.POST.get('direction', 'Long')
    strategy_label = request.POST.get('strategy_label', '')
    notes = request.POST.get('notes', '')
    template_id = request.POST.get('strategy_template')

    size = _safe_float(request.POST.get('size'), 0)
    price = _safe_float(request.POST.get('price'))
    market_price = _safe_float(request.POST.get('market_price'))
    stoploss = _safe_float(request.POST.get('stoploss'))
    target = _safe_float(request.POST.get('target'))

    # New fields
    trade_date_str = request.POST.get('trade_date', '')
    trade_time_str = request.POST.get('trade_time', '')
    expiry_date_str = request.POST.get('expiry_date', '')
    analysis_raw = request.POST.getlist('analysis')
    if not analysis_raw:
        analysis_raw = [a.strip() for a in request.POST.get('analysis_custom', '').split(',') if a.strip()]
    emotion = request.POST.get('emotion', '')
    screenshot = request.POST.get('screenshot_data', '')  # base64 data URL from JS

    try:
        trade_date = dt.date.fromisoformat(trade_date_str) if trade_date_str else dt.date.today()
    except ValueError:
        trade_date = dt.date.today()
    try:
        trade_time = dt.time.fromisoformat(trade_time_str) if trade_time_str else dt.datetime.now().time().replace(microsecond=0)
    except ValueError:
        trade_time = dt.datetime.now().time().replace(microsecond=0)
    try:
        expiry_date = dt.date.fromisoformat(expiry_date_str) if expiry_date_str else None
    except ValueError:
        expiry_date = None

    legs = _parse_legs(request.POST)

    try:
        trade = services.open_trade(
            trade_type=trade_type,
            direction=direction,
            legs=legs,
            size=size,
            price=price,
            strategy_label=strategy_label,
            notes=notes,
        )
        trade.market_price = market_price
        trade.stoploss = stoploss
        trade.target = target
        trade.trade_date = trade_date
        trade.trade_time = trade_time
        trade.expiry_date = expiry_date
        trade.analysis = analysis_raw
        trade.emotion = emotion
        trade.screenshot = screenshot
        if template_id:
            try:
                trade.strategy_template = StrategyTemplate.objects.get(pk=template_id)
                trade.strategy_template.usage_count += 1
                trade.strategy_template.save()
            except StrategyTemplate.DoesNotExist:
                pass
        trade.save()
        messages.success(request, 'Trade opened successfully.')
    except Exception as e:
        messages.error(request, f'Error opening trade: {e}')

    return redirect('journal:dashboard')



def trade_adjust(request, trade_id):
    if request.method != 'POST':
        return redirect('journal:dashboard')

    action = request.POST.get('action', 'Add')
    size = _safe_float(request.POST.get('size'), 0)
    price = _safe_float(request.POST.get('price'))
    pnl = _safe_float(request.POST.get('pnl'), 0)
    notes = request.POST.get('notes', '')

    try:
        if action == 'Add':
            services.add_position(trade_id, size, price, notes)
            messages.success(request, 'Position added.')
        elif action == 'Reduce':
            services.reduce_position(trade_id, size, price, notes)
            messages.success(request, 'Position reduced.')
        elif action == 'Close':
            services.close_trade(trade_id, price, notes)
            messages.success(request, 'Trade closed.')
        
        # Ensure status and PnLs are recalculated based on new adjustment
        services.recalculate_trade_state(trade_id)
    except Exception as e:
        messages.error(request, f'Error: {e}')

    return redirect('journal:dashboard')


def trade_edit(request, trade_id):
    trade = get_object_or_404(Trade, pk=trade_id)
    if request.method == 'POST':
        trade.trade_type = request.POST.get('trade_type', trade.trade_type)
        trade.direction = request.POST.get('direction', trade.direction)
        trade.strategy_label = request.POST.get('strategy_label', trade.strategy_label)
        trade.notes = request.POST.get('notes', trade.notes)
        trade.market_price = _safe_float(request.POST.get('market_price'), trade.market_price)
        trade.stoploss = _safe_float(request.POST.get('stoploss'), trade.stoploss)
        trade.target = _safe_float(request.POST.get('target'), trade.target)
        trade.save()
        messages.success(request, 'Trade details updated.')
        return redirect('journal:dashboard')

    context = {
        'trade': trade,
        'product_groups': product_utils.get_product_groups(),
        'contract_months': product_utils.get_contract_months(),
        'trade_types': Trade.TRADE_TYPE_CHOICES,
    }
    return render(request, 'journal/trade_edit.html', context)


def trade_delete(request, trade_id):
    trade = get_object_or_404(Trade, pk=trade_id)
    if request.method == 'POST':
        trade.delete()
        messages.success(request, 'Trade deleted.')
        return redirect('journal:dashboard')
    return render(request, 'journal/trade_confirm_delete.html', {'trade': trade})


@require_POST
def adjustment_edit(request, adj_id):
    """
    Handle editing a single position adjustment.
    """
    adj = get_object_or_404(PositionAdjustment, id=adj_id)
    size_change = request.POST.get('size_change')
    price = request.POST.get('price')
    notes = request.POST.get('notes', '')
    
    if size_change:
        try:
            services.update_adjustment(
                adj_id, 
                size_change=float(size_change),
                price=float(price) if price else None,
                notes=notes
            )
            messages.success(request, 'Adjustment updated.')
        except Exception as e:
            messages.error(request, f'Error: {e}')
            
    return redirect(request.META.get('HTTP_REFERER', 'journal:dashboard'))


@require_POST
def adjustment_delete(request, adj_id):
    """
    Handle deleting a single position adjustment.
    """
    services.delete_adjustment(adj_id)
    messages.success(request, 'Adjustment deleted.')
    return redirect(request.META.get('HTTP_REFERER', 'journal:dashboard'))


# ---------------------------------------------------------------------------
# Strategy Templates
# ---------------------------------------------------------------------------

def strategies_page(request):
    strategies = StrategyTemplate.objects.all().order_by('category', 'name')
    pairs = InterProductPair.objects.all().order_by('name')
    # Find the max number of legs for column headers
    max_legs = max((len(s.leg_ratios) for s in strategies), default=0)
    context = {
        'strategies': strategies,
        'pairs': pairs,
        'max_legs': range(max_legs),
        'max_legs_count': max_legs,
        'categories': StrategyTemplate.CATEGORY_CHOICES,
        'strategy_types': StrategyTemplate.TYPE_CHOICES,
    }
    return render(request, 'journal/strategies.html', context)


def strategy_add(request):
    if request.method != 'POST':
        return redirect('journal:strategies')

    name = request.POST.get('name', '').strip()
    category = request.POST.get('category', 'Custom')
    ratios_str = request.POST.get('leg_ratios', '[]')

    try:
        ratios = json.loads(ratios_str)
        if not isinstance(ratios, list):
            raise ValueError('leg_ratios must be a list')
    except (json.JSONDecodeError, ValueError):
        ratios = []

    if not name:
        messages.error(request, 'Strategy name is required.')
        return redirect('journal:strategies')

    strat_type = request.POST.get('strategy_type', 'Calendar')

    try:
        StrategyTemplate.objects.create(
            name=name, 
            category=category, 
            strategy_type=strat_type,
            leg_ratios=ratios
        )
        messages.success(request, f'Strategy "{name}" created.')
    except Exception as e:
        messages.error(request, f'Error: {e}')

    return redirect('journal:strategies')


def strategy_edit(request, strategy_id):
    strat = get_object_or_404(StrategyTemplate, pk=strategy_id)
    if request.method != 'POST':
        return redirect('journal:strategies')

    strat.name = request.POST.get('name', strat.name).strip()
    strat.category = request.POST.get('category', strat.category)
    strat.strategy_type = request.POST.get('strategy_type', strat.strategy_type)
    ratios_str = request.POST.get('leg_ratios', '[]')
    try:
        strat.leg_ratios = json.loads(ratios_str)
    except json.JSONDecodeError:
        pass
    strat.save()
    messages.success(request, f'Strategy "{strat.name}" updated.')
    return redirect('journal:strategies')


def strategy_delete(request, strategy_id):
    strat = get_object_or_404(StrategyTemplate, pk=strategy_id)
    if request.method == 'POST':
        strat.delete()
        messages.success(request, 'Strategy deleted.')
    return redirect('journal:strategies')


def pair_add(request):
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        p1 = request.POST.get('product_1', '').strip().upper()
        p2 = request.POST.get('product_2', '').strip().upper()
        
        if name and p1 and p2:
            InterProductPair.objects.create(name=name, product_1=p1, product_2=p2)
            messages.success(request, f'Pair "{name}" added.')
        else:
            messages.error(request, 'All pair fields are required.')
    return redirect('journal:strategies')


def pair_delete(request, pair_id):
    pair = get_object_or_404(InterProductPair, pk=pair_id)
    if request.method == 'POST':
        pair.delete()
        messages.success(request, 'Pair deleted.')
    return redirect('journal:strategies')


# ---------------------------------------------------------------------------
# Planned Trades
# ---------------------------------------------------------------------------

def planned_trades_page(request):
    planned = PlannedTrade.objects.all()
    strategies = StrategyTemplate.objects.all()
    strategy_groups = {}
    for s in strategies:
        cat = s.get_category_display()
        strategy_groups.setdefault(cat, [])
        strategy_groups[cat].append(s)

    context = {
        'planned_trades': planned,
        'product_groups': product_utils.get_product_groups(),
        'contract_months': product_utils.get_contract_months(),
        'trade_types': Trade.TRADE_TYPE_CHOICES,
        'strategy_groups': strategy_groups,
        'strategies_json': json.dumps([
            {'id': str(s.id), 'name': s.name, 'category': s.category, 'leg_ratios': s.leg_ratios}
            for s in strategies
        ]),
    }
    return render(request, 'journal/planned_trades.html', context)


def planned_trade_add(request):
    if request.method != 'POST':
        return redirect('journal:planned_trades')

    specific_months = request.POST.getlist('specific_months')
    image = request.FILES.get('image')
    template_id = request.POST.get('strategy_template')

    kwargs = {
        'trade_type': request.POST.get('trade_type', 'Outright'),
        'product': request.POST.get('product', ''),
        'product_group': request.POST.get('product_group', ''),
        'contract_month': request.POST.get('contract_month', ''),
        'direction': request.POST.get('direction', ''),
        'strategy_label': request.POST.get('strategy_label', ''),
        'frequency': request.POST.get('frequency', 'Once'),
        'specific_months': specific_months,
        'reasoning': request.POST.get('reasoning', ''),
        'image': image,
        'status': 'Planned',
    }

    if template_id:
        try:
            kwargs['strategy_template'] = StrategyTemplate.objects.get(pk=template_id)
        except StrategyTemplate.DoesNotExist:
            pass

    try:
        services.create_planned_trade(**kwargs)
        messages.success(request, 'Planned trade created.')
    except Exception as e:
        messages.error(request, f'Error: {e}')

    return redirect('journal:planned_trades')


def planned_trade_delete(request, planned_id):
    pt = get_object_or_404(PlannedTrade, pk=planned_id)
    if request.method == 'POST':
        pt.delete()
        messages.success(request, 'Planned trade removed.')
    return redirect('journal:planned_trades')


# ---------------------------------------------------------------------------
# JSON API
# ---------------------------------------------------------------------------

def api_products(request):
    pairs = InterProductPair.objects.all()
    return JsonResponse({
        'products': product_utils.get_product_list(),
        'groups': product_utils.get_product_groups(),
        'contract_months': product_utils.get_contract_months(),
        'interproduct_pairs': [
            {'id': str(p.id), 'name': p.name, 'p1': p.product_1, 'p2': p.product_2}
            for p in pairs
        ]
    })



def api_strategies(request):
    strategies = StrategyTemplate.objects.all()
    return JsonResponse({
        'strategies': [
            {'id': str(s.id), 'name': s.name, 'category': s.category, 'leg_ratios': s.leg_ratios}
            for s in strategies
        ]
    })


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _safe_float(val, default=None):
    if val in (None, ''):
        return default
    try:
        return float(val)
    except (ValueError, TypeError):
        return default


def _parse_legs(post_data) -> list[dict]:
    legs = []
    i = 0
    while True:
        product = post_data.get(f'leg_{i}_product')
        if not product:
            break
        legs.append({
            'product': product,
            'product_group': post_data.get(f'leg_{i}_product_group', ''),
            'contract_month': post_data.get(f'leg_{i}_contract_month', ''),
            'direction': post_data.get(f'leg_{i}_direction', 'Buy'),
            'ratio': post_data.get(f'leg_{i}_ratio', '1'),
        })
        i += 1

    if not legs:
        product = post_data.get('product', '')
        if product:
            legs.append({
                'product': product,
                'product_group': post_data.get('product_group', ''),
                'contract_month': post_data.get('contract_month', ''),
                'direction': 'Buy' if post_data.get('direction') == 'Long' else 'Sell',
                'ratio': '1',
            })

    return legs


# ---------------------------------------------------------------------------
# All Trades Analytics
# ---------------------------------------------------------------------------

def trades_list(request):
    all_trades = Trade.objects.all().prefetch_related('legs', 'adjustments').order_by('-created_at')
    
    strategy_pnl = defaultdict(float)
    product_pnl = defaultdict(float)
    group_pnl = defaultdict(float)
    
    # New Time-Based Aggregations
    day_pnl = defaultdict(float)
    week_pnl = defaultdict(float)
    month_pnl = defaultdict(float)
    year_pnl = defaultdict(float)
    
    trade_list = []
    
    # Pre-fetch products data once instead of in loop
    products_data = product_utils.get_products_data()
    
    for t in all_trades:
        tc_realized = services.calculate_total_realized_tc(t)
        if t.status == 'Closed':
            pnl = t.realized_pnl
        else:
            pnl = t.realized_pnl + (services.get_unrealized_pnl(t.id) or 0.0)
            
        net_pnl = round(pnl - abs(tc_realized['tc_postrebate']), 2)
        
        # Attribute PnL to strategy
        strat_label = t.strategy_label if t.strategy_label else "Unknown"
        strategy_pnl[strat_label] += net_pnl
        
        # Attribute PnL to Product and Group (using first leg)
        if t.legs.exists():
            first_leg = t.legs.first()
            prod_symbol = first_leg.product
            
            prod_info = products_data.get(prod_symbol, {})
            group = prod_info.get('group', 'Unknown')
            
            product_pnl[prod_symbol] += net_pnl
            group_pnl[group] += net_pnl
            
        # Time-based Aggregations
        if t.created_at:
            # Day (Mon, Tue, etc.)
            day_name = t.created_at.strftime("%a")
            day_pnl[day_name] += net_pnl
            
            # Week of month categorization (approximate 1-4)
            day_val = t.created_at.day
            week_num = (day_val - 1) // 7 + 1
            week_label = f"Week {week_num}"
            week_pnl[week_label] += net_pnl
            
            # Month (Jan, Feb, etc.)
            month_name = t.created_at.strftime("%b")
            month_pnl[month_name] += net_pnl
            
            # Year
            year_val = str(t.created_at.year)
            year_pnl[year_val] += net_pnl
            
        # Simplified and Corrected Cost Logic
        net_commission = abs(tc_realized['tc_prerebate'])
        total_rebate = abs(tc_realized['tc_prerebate'] - tc_realized['tc_postrebate'])
        # net_pnl already subtracted tc_postrebate (which is tc_pre - rebate)
        # So net_pnl = gross_pnl - (tc_pre - rebate) = gross_pnl - tc_pre + rebate
        # This IS the standard Net PnL inclusive of rebates.
        net_pnl_with_rebate = net_pnl 

        trade_list.append({
            'trade': t,
            'legs': t.legs.all(),
            'net_pnl': net_pnl,
            'net_pnl_with_rebate': net_pnl_with_rebate,
            'status': t.status,
            'open_size': t.total_open_size,
            'avg_entry': t.avg_entry_price,
            'net_commission': round(net_commission, 2),
            'total_rebate': round(total_rebate, 2),
        })

    # Optional: order some dictionaries so axes are logical. Days of week:
    days_order = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
    sorted_day_pnl = {d: day_pnl[d] for d in days_order if d in day_pnl}
    # For others like week, month, year, assuming natural alphabetic or built-in order is fine, or sorting by key
    sorted_month_pnl = dict(sorted(month_pnl.items(), key=lambda item: ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'].index(item[0]) if item[0] in ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'] else 0))
    sorted_week_pnl = dict(sorted(week_pnl.items()))
    sorted_year_pnl = dict(sorted(year_pnl.items()))

    context = {
        'trades': trade_list,
        'strategy_labels': json.dumps(list(strategy_pnl.keys())),
        'strategy_data': json.dumps([round(v, 2) for v in strategy_pnl.values()]),
        'product_labels': json.dumps(list(product_pnl.keys())),
        'product_data': json.dumps([round(v, 2) for v in product_pnl.values()]),
        'group_labels': json.dumps(list(group_pnl.keys())),
        'group_data': json.dumps([round(v, 2) for v in group_pnl.values()]),
        'day_labels': json.dumps(list(sorted_day_pnl.keys())),
        'day_data': json.dumps([round(v, 2) for v in sorted_day_pnl.values()]),
        'week_labels': json.dumps(list(sorted_week_pnl.keys())),
        'week_data': json.dumps([round(v, 2) for v in sorted_week_pnl.values()]),
        'month_labels': json.dumps(list(sorted_month_pnl.keys())),
        'month_data': json.dumps([round(v, 2) for v in sorted_month_pnl.values()]),
        'year_labels': json.dumps(list(sorted_year_pnl.keys())),
        'year_data': json.dumps([round(v, 2) for v in sorted_year_pnl.values()]),
    }
    return render(request, 'journal/trades.html', context)

# ---------------------------------------------------------------------------
# Calendar
# ---------------------------------------------------------------------------

def calendar_view(request):
    # Year/Month from request or current
    now = datetime.now()
    year_str = request.GET.get('year')
    month_str = request.GET.get('month')
    
    year = int(year_str) if year_str and year_str.isdigit() else now.year
    month = int(month_str) if month_str and month_str.isdigit() else now.month
    
    # Range of transactions for this month
    start_date = datetime(year, month, 1)
    if month == 12:
        next_month_date = datetime(year + 1, 1, 1)
    else:
        next_month_date = datetime(year, month + 1, 1)
        
    adjustments = PositionAdjustment.objects.filter(
        timestamp__gte=start_date,
        timestamp__lt=next_month_date
    ).select_related('trade').prefetch_related('trade__legs')
    
    products_data = product_utils.get_products_data()
    
    daily_stats = defaultdict(lambda: {'gross': 0.0, 'net': 0.0})
    
    for adj in adjustments:
        day_str = adj.timestamp.strftime('%Y-%m-%d')
        daily_stats[day_str]['gross'] += adj.pnl
        
        # Calculate TC for this adjustment
        trade = adj.trade
        volume = abs(adj.size_change)
        tc_post = 0.0
        for leg in trade.legs.all():
            if leg.product in products_data:
                # Use abs() because unit TC from spreadsheet is negative
                tc_post += abs(products_data[leg.product]['tc_post']) * volume * abs(leg.ratio)
        
        daily_stats[day_str]['net'] += (adj.pnl - tc_post)
        
    # Generate calendar matrix with stats
    cal = calendar.Calendar(firstweekday=6) # 6 = Sunday start
    month_days = cal.monthdatescalendar(year, month)
    
    calendar_data = []
    for week in month_days:
        week_data = []
        for d in week:
            day_str = d.strftime('%Y-%m-%d')
            stats = daily_stats.get(day_str, {'gross': 0, 'net': 0})
            week_data.append({
                'date': d,
                'is_current_month': d.month == month,
                'stats': stats,
                'is_today': d == date.today()
            })
        calendar_data.append(week_data)
    
    month_name = calendar.month_name[month]
    prev_month_date = start_date - timedelta(days=1)
    
    context = {
        'calendar_data': calendar_data,
        'current_month': month,
        'current_year': year,
        'month_name': month_name,
        'prev_month': prev_month_date.month,
        'prev_year': prev_month_date.year,
        'next_month': next_month_date.month,
        'next_year': next_month_date.year,
        'today': date.today(),
    }
    return render(request, 'journal/calendar.html', context)


# ---------------------------------------------------------------------------
# Product Fees & Rebates
# ---------------------------------------------------------------------------

def products_fees_page(request):
    products = product_utils.get_products_data()
    context = {
        'products': sorted(products.items(), key=lambda x: (x[1]['group'], x[0]))
    }
    return render(request, 'journal/products_fees.html', context)


# ---------------------------------------------------------------------------
# COT Report
# ---------------------------------------------------------------------------

def cot_page(request):
    """Render the CFTC COT explorer page."""
    from . import cot_service
    grouped_markets = cot_service.get_grouped_markets()
    market_count = sum(len(v) for v in grouped_markets.values())
    return render(request, 'journal/cot.html', {
        'grouped_markets': grouped_markets,
        'market_count': market_count,
    })


def api_cot_data(request):
    """JSON endpoint: returns time-series + seasonality for a given market_code."""
    from . import cot_service
    market_code = request.GET.get('market_code', '').strip()
    trigger_fetch = request.GET.get('trigger_fetch', '0') == '1'

    if not market_code:
        return JsonResponse({'error': 'market_code required'}, status=400)

    new_rows = 0
    fetch_error = None
    
    # Check if we have any data locally. If not, auto-trigger a fetch.
    has_data = cot_service.get_latest_saved_date(market_code) is not None
    
    if trigger_fetch or not has_data:
        try:
            new_rows = cot_service.fetch_and_save_cot(market_code)
        except Exception as exc:
            fetch_error = str(exc)

    data = cot_service.get_chart_data(market_code)
    latest = cot_service.get_latest_saved_date(market_code)
    return JsonResponse({
        'market_code': market_code,
        'latest_date': latest.isoformat() if latest else None,
        'new_rows': new_rows,
        'fetch_error': fetch_error,
        'time_series': data['time_series'],
        'seasonality_weekly': data['seasonality_weekly'],
        'seasonality_monthly': data['seasonality_monthly'],
    })


def api_cot_sync_all_markets(request):
    """
    Fetch the full list of available CFTC markets and cache it locally.
    Called by the 'Sync All Markets' button in the COT UI.
    Returns JSON with total market count and group breakdown.
    """
    from . import cot_service
    try:
        markets, total = cot_service.fetch_all_available_markets()
        groups = {}
        for m in markets:
            groups[m['group']] = groups.get(m['group'], 0) + 1
        return JsonResponse({
            'success': True,
            'total': total,
            'groups': groups,
        })
    except Exception as exc:
        return JsonResponse({'success': False, 'error': str(exc)}, status=502)

# ---------------------------------------------------------------------------
# Palm Oil Dashboard
# ---------------------------------------------------------------------------

def palm_oil_dashboard(request):
    """Render the Palm Oil Fundamentals dashboard."""
    return render(request, 'journal/palm_oil.html')


def api_palm_oil_data(request):
    """JSON endpoint: returns all chart data for Palm Oil dashboard."""
    # 1. Price Forward Curve
    latest_price_date_obj = PalmOilPriceAndOI.objects.order_by('-date').first()
    prices = []
    if latest_price_date_obj:
        latest_date = latest_price_date_obj.date
        price_qs = PalmOilPriceAndOI.objects.filter(date=latest_date).order_by('contract_month')
        prices = [
            {'contract': p.contract_month, 'close': p.close_price, 'oi': p.open_interest}
            for p in price_qs
        ]
        
    # 2. Historical OI (aggregate total OI per date for seasonality)
    import datetime
    from django.db.models import Sum
    today = datetime.date.today()
    three_years_ago = today.replace(year=today.year - 3)
    
    oi_qs = PalmOilPriceAndOI.objects.filter(date__gte=three_years_ago).values('date').annotate(total_oi=Sum('open_interest')).order_by('date')
    
    oi_history = [
        {'date': item['date'].isoformat(), 'total_oi': item['total_oi']}
        for item in oi_qs if item['total_oi']
    ]

    # 3. MPOB Data
    mpob_qs = MPOBData.objects.all().order_by('year', 'month')
    mpob_data = [
        {
            'year': m.year,
            'month': m.month,
            'production': m.production,
            'imports': m.imports,
            'exports': m.exports,
            'local_consumption': m.local_consumption,
            'end_stocks': m.end_stocks,
        }
        for m in mpob_qs
    ]

    # 4. Surveyor Data
    surveyor_qs = ExportSurveyorData.objects.all().order_by('year', 'month', 'surveyor')
    surveyor_data = [
        {
            'year': s.year,
            'month': s.month,
            'surveyor': s.surveyor,
            'day_1_to_10': s.day_1_to_10,
            'day_1_to_15': s.day_1_to_15,
            'day_1_to_20': s.day_1_to_20,
            'day_1_to_25': s.day_1_to_25,
            'full_month': s.full_month,
        }
        for s in surveyor_qs
    ]

    return JsonResponse({
        'latest_price_date': latest_price_date_obj.date.isoformat() if latest_price_date_obj else None,
        'prices': prices,
        'oi_history': oi_history,
        'mpob_data': mpob_data,
        'surveyor_data': surveyor_data,
    })
