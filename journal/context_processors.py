from .models import Account

def account_context(request):
    """
    Supplies active_account, all_accounts, and is_all_accounts to every template automatically.
    Maintains session-based active account with zero authentication required.
    """
    accounts = list(Account.objects.all().order_by('-is_default', 'name'))

    # If no accounts exist yet, seed a clean default one
    if not accounts:
        default_acc = Account.objects.create(
            name="Main Account",
            description="Primary Trading Account",
            is_default=True
        )
        accounts = [default_acc]

    active_account_id = request.session.get('active_account_id')
    active_account = None

    if active_account_id == 'all':
        active_account = None
    elif active_account_id:
        active_account = next((a for a in accounts if str(a.id) == str(active_account_id)), None)

    # If active_account is still None and active_account_id was not explicitly 'all'
    if active_account is None and active_account_id != 'all':
        active_account = accounts[0]
        request.session['active_account_id'] = str(active_account.id)

    return {
        'all_accounts': accounts,
        'active_account': active_account,
        'is_all_accounts': active_account_id == 'all',
    }
