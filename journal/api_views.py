import json
import datetime as dt
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.conf import settings
from .models import Trade, TradeLeg, PositionAdjustment, Account, StrategyTemplate
from . import services
from . import utils as product_utils


def _authenticate_bot_request(request):
    """
    Optional API Key authentication for trading bot endpoints.
    If BOT_API_KEY / TRADE_JOURNAL_API_KEY is configured in settings/env,
    verify against 'X-API-Key' header or 'Authorization: Bearer <token>'.
    If not configured, allow local bot requests freely.
    """
    configured_key = getattr(settings, 'BOT_API_KEY', '') or getattr(settings, 'TRADE_JOURNAL_API_KEY', '')
    if not configured_key:
        return True, None

    auth_header = request.headers.get('Authorization', '')
    api_key_header = request.headers.get('X-API-Key', '')

    provided_key = ''
    if api_key_header:
        provided_key = api_key_header.strip()
    elif auth_header.startswith('Bearer '):
        provided_key = auth_header[7:].strip()

    if provided_key == configured_key:
        return True, None

    return False, JsonResponse({
        'success': False,
        'error': 'Unauthorized. Invalid or missing API key in X-API-Key or Authorization header.'
    }, status=401)


def _parse_request_data(request) -> dict:
    """Extract dict payload from JSON body or POST form data."""
    if request.body:
        try:
            return json.loads(request.body.decode('utf-8'))
        except (json.JSONDecodeError, UnicodeDecodeError):
            pass
    return request.POST.dict()


import uuid

def _resolve_account(account_val):
    """Find Account by UUID or exact/case-insensitive name."""
    if not account_val:
        return Account.objects.first()

    # Try UUID if it looks like a valid UUID string
    try:
        val_str = str(account_val).strip()
        parsed_uuid = uuid.UUID(val_str)
        acc = Account.objects.filter(id=parsed_uuid).first()
        if acc:
            return acc
    except (ValueError, TypeError, AttributeError):
        pass

    # Try Name match
    acc = Account.objects.filter(name__iexact=str(account_val).strip()).first()
    if acc:
        return acc

    return Account.objects.first()


def trade_to_dict(trade: Trade, detailed: bool = False) -> dict:
    """Serialize a Trade instance into a structured JSON-friendly dictionary."""
    tc = services.calculate_total_realized_tc(trade)
    unrealized = services.get_unrealized_pnl(trade.id) if trade.status != 'Closed' else 0.0
    realized = trade.realized_pnl
    open_size = trade.total_open_size
    avg_entry = trade.avg_entry_price

    legs = [
        {
            'id': str(leg.id),
            'product': leg.product,
            'product_group': leg.product_group,
            'contract_month': leg.contract_month,
            'direction': leg.direction,
            'ratio': leg.ratio,
        }
        for leg in trade.legs.all()
    ]

    gross_pnl = round(realized if trade.status == 'Closed' else realized + (unrealized or 0.0), 2)
    net_pnl = round(gross_pnl - abs(tc['tc_postrebate']), 2)

    data = {
        'id': str(trade.id),
        'account': {
            'id': str(trade.account.id),
            'name': trade.account.name,
            'currency': trade.account.currency,
        } if trade.account else None,
        'trade_type': trade.trade_type,
        'direction': trade.direction,
        'status': trade.status,
        'strategy_label': trade.strategy_label,
        'open_size': open_size,
        'avg_entry_price': avg_entry,
        'market_price': trade.market_price,
        'stoploss': trade.stoploss,
        'target': trade.target,
        'realized_pnl': realized,
        'unrealized_pnl': unrealized,
        'gross_pnl': gross_pnl,
        'net_pnl': net_pnl,
        'fees': {
            'commission_pre_rebate': round(abs(tc['tc_prerebate']), 2),
            'fees_post_rebate': round(abs(tc['tc_postrebate']), 2),
            'rebate': round(abs(tc['tc_prerebate'] - tc['tc_postrebate']), 2),
        },
        'trade_date': trade.trade_date.isoformat() if trade.trade_date else None,
        'trade_time': trade.trade_time.isoformat() if trade.trade_time else None,
        'expiry_date': trade.expiry_date.isoformat() if trade.expiry_date else None,
        'analysis': trade.analysis,
        'emotion': trade.emotion,
        'notes': trade.notes,
        'legs': legs,
        'created_at': trade.created_at.isoformat() if trade.created_at else None,
        'updated_at': trade.updated_at.isoformat() if trade.updated_at else None,
    }

    if detailed:
        data['adjustments'] = [
            {
                'id': str(adj.id),
                'action': adj.action,
                'size_change': adj.size_change,
                'price': adj.price,
                'pnl': adj.pnl,
                'notes': adj.notes,
                'timestamp': adj.timestamp.isoformat(),
            }
            for adj in trade.adjustments.all().order_by('timestamp')
        ]

    return data


# ---------------------------------------------------------------------------
# REST Endpoints for Trading Bots
# ---------------------------------------------------------------------------

@csrf_exempt
@require_http_methods(['GET', 'POST'])
def api_trades(request):
    """
    GET: List trades with filtering.
    POST: Create a new trade entry with legs and initial Open adjustment.
    """
    is_auth, err_resp = _authenticate_bot_request(request)
    if not is_auth:
        return err_resp

    if request.method == 'GET':
        qs = Trade.objects.all().prefetch_related('legs', 'adjustments', 'account').order_by('-created_at')

        # Filters
        account_val = request.GET.get('account')
        if account_val and account_val != 'all':
            acc = _resolve_account(account_val)
            if acc:
                qs = qs.filter(account=acc)

        status_val = request.GET.get('status')
        if status_val:
            qs = qs.filter(status=status_val)

        direction_val = request.GET.get('direction')
        if direction_val:
            qs = qs.filter(direction=direction_val)

        trade_type_val = request.GET.get('trade_type')
        if trade_type_val:
            qs = qs.filter(trade_type=trade_type_val)

        product_val = request.GET.get('product')
        if product_val:
            qs = qs.filter(legs__product=product_val.strip().upper()).distinct()

        # Pagination
        try:
            limit = min(int(request.GET.get('limit', 50)), 500)
            offset = max(int(request.GET.get('offset', 0)), 0)
        except ValueError:
            limit, offset = 50, 0

        total_count = qs.count()
        trades_slice = qs[offset:offset + limit]

        return JsonResponse({
            'success': True,
            'total': total_count,
            'count': len(trades_slice),
            'offset': offset,
            'limit': limit,
            'trades': [trade_to_dict(t, detailed=False) for t in trades_slice]
        })

    # POST: Create Trade
    data = _parse_request_data(request)
    if not data:
        return JsonResponse({'success': False, 'error': 'Empty or invalid JSON payload.'}, status=400)

    # Validate Size
    try:
        size = float(data.get('size', 1.0))
        if size <= 0:
            raise ValueError()
    except (ValueError, TypeError):
        return JsonResponse({'success': False, 'error': "'size' must be a positive number."}, status=400)

    trade_type = data.get('trade_type', 'Outright')
    direction = data.get('direction', 'Long')
    strategy_label = data.get('strategy_label', '').strip()
    notes = data.get('notes', '').strip()
    price = data.get('price')
    try:
        price = float(price) if price is not None and price != '' else None
    except (ValueError, TypeError):
        price = None

    # Resolve Account
    account = _resolve_account(data.get('account'))

    # Build Legs
    legs = []
    raw_legs = data.get('legs')
    if isinstance(raw_legs, list) and len(raw_legs) > 0:
        for leg in raw_legs:
            if isinstance(leg, dict) and leg.get('product'):
                legs.append({
                    'product': str(leg.get('product')).strip().upper(),
                    'product_group': leg.get('product_group', ''),
                    'contract_month': leg.get('contract_month', ''),
                    'direction': leg.get('direction', 'Buy'),
                    'ratio': float(leg.get('ratio', 1)),
                })
    else:
        # Fallback to shorthand: "product" and "contract_month"
        prod = data.get('product', '').strip().upper()
        if prod:
            legs.append({
                'product': prod,
                'product_group': data.get('product_group', ''),
                'contract_month': data.get('contract_month', ''),
                'direction': 'Buy' if direction == 'Long' else 'Sell',
                'ratio': 1.0,
            })

    if not legs:
        return JsonResponse({
            'success': False,
            'error': "At least one leg is required (provide 'legs': [...] or 'product': 'SYMBOL')."
        }, status=400)

    # Optional metadata
    market_price = data.get('market_price')
    stoploss = data.get('stoploss')
    target = data.get('target')
    emotion = data.get('emotion', '')
    analysis = data.get('analysis', [])
    if isinstance(analysis, str):
        analysis = [a.strip() for a in analysis.split(',') if a.strip()]

    # Dates
    trade_date = None
    if data.get('trade_date'):
        try:
            trade_date = dt.date.fromisoformat(data['trade_date'])
        except ValueError:
            trade_date = dt.date.today()
    else:
        trade_date = dt.date.today()

    trade_time = None
    if data.get('trade_time'):
        try:
            trade_time = dt.time.fromisoformat(data['trade_time'])
        except ValueError:
            trade_time = dt.datetime.now().time().replace(microsecond=0)
    else:
        trade_time = dt.datetime.now().time().replace(microsecond=0)

    expiry_date = None
    if data.get('expiry_date'):
        try:
            expiry_date = dt.date.fromisoformat(data['expiry_date'])
        except ValueError:
            pass

    try:
        trade = services.open_trade(
            trade_type=trade_type,
            direction=direction,
            legs=legs,
            size=size,
            price=price,
            strategy_label=strategy_label,
            notes=notes,
            account=account,
        )
        if market_price is not None:
            trade.market_price = float(market_price)
        if stoploss is not None:
            trade.stoploss = float(stoploss)
        if target is not None:
            trade.target = float(target)
        trade.trade_date = trade_date
        trade.trade_time = trade_time
        trade.expiry_date = expiry_date
        trade.analysis = analysis
        trade.emotion = emotion

        # Optional strategy template linkage
        template_id = data.get('strategy_template_id')
        if template_id:
            try:
                trade.strategy_template = StrategyTemplate.objects.get(id=template_id)
                trade.strategy_template.usage_count += 1
                trade.strategy_template.save()
            except StrategyTemplate.DoesNotExist:
                pass

        trade.save()

        return JsonResponse({
            'success': True,
            'message': 'Trade opened successfully.',
            'trade': trade_to_dict(trade, detailed=True)
        }, status=201)

    except Exception as exc:
        return JsonResponse({'success': False, 'error': f'Failed to create trade: {str(exc)}'}, status=500)


@csrf_exempt
@require_http_methods(['GET', 'PUT', 'PATCH', 'DELETE'])
def api_trade_detail(request, trade_id):
    """
    GET: Get full trade state with adjustment event history.
    PUT/PATCH: Update mutable trade details.
    DELETE: Remove trade entry and cascaded data.
    """
    is_auth, err_resp = _authenticate_bot_request(request)
    if not is_auth:
        return err_resp

    try:
        trade = Trade.objects.prefetch_related('legs', 'adjustments', 'account').get(id=trade_id)
    except Trade.DoesNotExist:
        return JsonResponse({'success': False, 'error': f'Trade {trade_id} not found.'}, status=404)

    if request.method == 'GET':
        return JsonResponse({
            'success': True,
            'trade': trade_to_dict(trade, detailed=True)
        })

    if request.method == 'DELETE':
        trade_id_str = str(trade.id)
        trade.delete()
        return JsonResponse({
            'success': True,
            'message': f'Trade {trade_id_str} deleted successfully.'
        })

    # PUT / PATCH: Update metadata
    data = _parse_request_data(request)
    if not data:
        return JsonResponse({'success': False, 'error': 'Empty or invalid JSON payload.'}, status=400)

    if 'strategy_label' in data:
        trade.strategy_label = str(data['strategy_label']).strip()
    if 'notes' in data:
        trade.notes = str(data['notes']).strip()
    if 'direction' in data and data['direction'] in ['Long', 'Short']:
        trade.direction = data['direction']
    if 'trade_type' in data:
        trade.trade_type = data['trade_type']
    if 'market_price' in data:
        trade.market_price = float(data['market_price']) if data['market_price'] is not None else None
    if 'stoploss' in data:
        trade.stoploss = float(data['stoploss']) if data['stoploss'] is not None else None
    if 'target' in data:
        trade.target = float(data['target']) if data['target'] is not None else None
    if 'emotion' in data:
        trade.emotion = str(data['emotion']).strip()
    if 'analysis' in data:
        val = data['analysis']
        trade.analysis = [a.strip() for a in val.split(',')] if isinstance(val, str) else list(val)
    if 'account' in data:
        trade.account = _resolve_account(data['account'])

    trade.save()

    return JsonResponse({
        'success': True,
        'message': 'Trade updated successfully.',
        'trade': trade_to_dict(trade, detailed=True)
    })


@csrf_exempt
@require_http_methods(['POST'])
def api_trade_adjust(request, trade_id):
    """
    POST: Position adjustment endpoint for bots to scale-in, take profit, or close.
    Payload:
      {
        "action": "Add" | "Reduce" | "Close",
        "size": 1.0,           (required for Add and Reduce)
        "price": 74.50,        (execution price)
        "notes": "Scale-out 50%"
      }
    """
    is_auth, err_resp = _authenticate_bot_request(request)
    if not is_auth:
        return err_resp

    try:
        trade = Trade.objects.get(id=trade_id)
    except Trade.DoesNotExist:
        return JsonResponse({'success': False, 'error': f'Trade {trade_id} not found.'}, status=404)

    data = _parse_request_data(request)
    if not data:
        return JsonResponse({'success': False, 'error': 'Empty or invalid JSON payload.'}, status=400)

    action = str(data.get('action', '')).capitalize()
    if action not in ['Add', 'Reduce', 'Close']:
        return JsonResponse({
            'success': False,
            'error': f"Invalid action '{action}'. Must be 'Add', 'Reduce', or 'Close'."
        }, status=400)

    if trade.status == 'Closed' and action in ['Reduce', 'Close']:
        return JsonResponse({
            'success': False,
            'error': f"Trade {trade_id} is already Closed. Cannot {action}."
        }, status=400)

    price = data.get('price')
    try:
        price = float(price) if price is not None and price != '' else None
    except (ValueError, TypeError):
        price = None

    notes = str(data.get('notes', '')).strip()

    try:
        if action == 'Add':
            size = float(data.get('size', 0))
            if size <= 0:
                return JsonResponse({'success': False, 'error': "'size' must be > 0 for 'Add'."}, status=400)
            services.add_position(trade.id, size, price, notes)
            msg = f"Position added (+{size} contracts)."

        elif action == 'Reduce':
            size = float(data.get('size', 0))
            if size <= 0:
                return JsonResponse({'success': False, 'error': "'size' must be > 0 for 'Reduce'."}, status=400)
            services.reduce_position(trade.id, size, price, notes)
            msg = f"Position reduced (-{size} contracts)."

        elif action == 'Close':
            services.close_trade(trade.id, price, notes)
            msg = "Trade closed completely."

        services.recalculate_trade_state(trade.id)
        trade.refresh_from_db()

        return JsonResponse({
            'success': True,
            'message': msg,
            'trade': trade_to_dict(trade, detailed=True)
        })

    except Exception as exc:
        return JsonResponse({'success': False, 'error': f'Failed to adjust trade: {str(exc)}'}, status=500)
