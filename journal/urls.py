from django.urls import path
from . import views

app_name = 'journal'

urlpatterns = [
    # Dashboard
    path('', views.dashboard, name='dashboard'),

    # All Trades & Analytics
    path('trades/', views.trades_list, name='trades'),
    path('products/fees/', views.products_fees_page, name='products_fees'),

    # Accounts
    path('accounts/switch/<str:account_id>/', views.account_switch, name='account_switch'),
    path('accounts/add/', views.account_add, name='account_add'),
    path('accounts/<uuid:account_id>/delete/', views.account_delete, name='account_delete'),

    # New Trade (dedicated page)
    path('trades/new/', views.trade_new, name='trade_new'),
    path('trades/add/', views.trade_add, name='trade_add'),
    path('trades/<uuid:trade_id>/adjust/', views.trade_adjust, name='trade_adjust'),
    path('trades/<uuid:trade_id>/edit/', views.trade_edit, name='trade_edit'),
    path('trades/<uuid:trade_id>/delete/', views.trade_delete, name='trade_delete'),
    path('adjustments/<uuid:adj_id>/edit/', views.adjustment_edit, name='adjustment_edit'),
    path('adjustments/<uuid:adj_id>/delete/', views.adjustment_delete, name='adjustment_delete'),

    # Strategies
    path('strategies/', views.strategies_page, name='strategies'),
    path('strategies/add/', views.strategy_add, name='strategy_add'),
    path('strategies/<uuid:strategy_id>/edit/', views.strategy_edit, name='strategy_edit'),
    path('strategies/<uuid:strategy_id>/delete/', views.strategy_delete, name='strategy_delete'),
    
    # InterProduct Pairs
    path('pairs/add/', views.pair_add, name='pair_add'),
    path('pairs/<uuid:pair_id>/delete/', views.pair_delete, name='pair_delete'),


    # Planned trades
    path('planned/', views.planned_trades_page, name='planned_trades'),
    path('planned/add/', views.planned_trade_add, name='planned_trade_add'),
    path('planned/<uuid:planned_id>/delete/', views.planned_trade_delete, name='planned_trade_delete'),

    # Calendar
    path('calendar/', views.calendar_view, name='calendar'),

    # JSON API
    path('api/products/', views.api_products, name='api_products'),
    path('api/strategies/', views.api_strategies, name='api_strategies'),

    # COT Report
    path('cot/', views.cot_page, name='cot'),
    path('api/cot/', views.api_cot_data, name='api_cot_data'),
    path('api/cot/sync-markets/', views.api_cot_sync_all_markets, name='api_cot_sync_markets'),

    # Palm Oil Dashboard
    path('palm-oil/', views.palm_oil_dashboard, name='palm_oil_dashboard'),
    path('api/palm-oil/', views.api_palm_oil_data, name='api_palm_oil_data'),
]
