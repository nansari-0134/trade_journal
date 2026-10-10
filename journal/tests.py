import json
from django.test import TestCase, Client, override_settings
from .models import Account, Trade, TradeLeg, PositionAdjustment


class TradeRestApiTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.account = Account.objects.create(
            name="Apex Bot Account",
            currency="USD",
            initial_balance=50000.0,
            is_default=True
        )

    def test_create_outright_trade(self):
        payload = {
            "account": "Apex Bot Account",
            "trade_type": "Outright",
            "direction": "Long",
            "size": 2.0,
            "price": 70.50,
            "product": "CL",
            "contract_month": "Apr 2026",
            "strategy_label": "Bot Momentum Breakout",
            "stoploss": 69.50,
            "target": 73.00,
            "notes": "Triggered by SMA cross"
        }
        res = self.client.post(
            '/api/trades/',
            data=json.dumps(payload),
            content_type='application/json'
        )
        self.assertEqual(res.status_code, 201)
        data = res.json()
        self.assertTrue(data['success'])
        trade_id = data['trade']['id']

        trade = Trade.objects.get(id=trade_id)
        self.assertEqual(trade.trade_type, 'Outright')
        self.assertEqual(trade.direction, 'Long')
        self.assertEqual(trade.status, 'Open')
        self.assertEqual(trade.total_open_size, 2.0)
        self.assertEqual(trade.avg_entry_price, 70.50)
        self.assertEqual(trade.legs.count(), 1)
        self.assertEqual(trade.legs.first().product, 'CL')
        self.assertEqual(trade.account.name, "Apex Bot Account")

    def test_create_multileg_calendar_spread(self):
        payload = {
            "account": str(self.account.id),
            "trade_type": "CalendarSpread",
            "direction": "Long",
            "size": 3.0,
            "price": 0.45,
            "strategy_label": "CL Apr/May Spread",
            "legs": [
                {"product": "CL", "contract_month": "Apr 2026", "direction": "Buy", "ratio": 1},
                {"product": "CL", "contract_month": "May 2026", "direction": "Sell", "ratio": 1}
            ]
        }
        res = self.client.post(
            '/api/trades/',
            data=json.dumps(payload),
            content_type='application/json'
        )
        self.assertEqual(res.status_code, 201)
        data = res.json()
        self.assertTrue(data['success'])
        self.assertEqual(len(data['trade']['legs']), 2)

    def test_create_trade_validation(self):
        # Missing size
        res = self.client.post(
            '/api/trades/',
            data=json.dumps({"size": -1, "product": "CL"}),
            content_type='application/json'
        )
        self.assertEqual(res.status_code, 400)

        # Missing legs/product
        res = self.client.post(
            '/api/trades/',
            data=json.dumps({"size": 1.0}),
            content_type='application/json'
        )
        self.assertEqual(res.status_code, 400)

    def test_list_trades_and_filters(self):
        # Create 2 trades
        t1 = self.client.post(
            '/api/trades/',
            data=json.dumps({"size": 1, "price": 100, "product": "CL", "direction": "Long"}),
            content_type='application/json'
        ).json()['trade']

        t2 = self.client.post(
            '/api/trades/',
            data=json.dumps({"size": 1, "price": 200, "product": "ZC", "direction": "Short"}),
            content_type='application/json'
        ).json()['trade']

        # List all
        res = self.client.get('/api/trades/')
        self.assertEqual(res.status_code, 200)
        self.assertGreaterEqual(res.json()['count'], 2)

        # Filter by product ZC
        res_zc = self.client.get('/api/trades/?product=ZC')
        self.assertEqual(res_zc.status_code, 200)
        for t in res_zc.json()['trades']:
            products = [leg['product'] for leg in t['legs']]
            self.assertIn('ZC', products)

        # Filter by direction Short
        res_short = self.client.get('/api/trades/?direction=Short')
        self.assertEqual(res_short.status_code, 200)
        for t in res_short.json()['trades']:
            self.assertEqual(t['direction'], 'Short')

    def test_get_trade_detail(self):
        t = self.client.post(
            '/api/trades/',
            data=json.dumps({"size": 2, "price": 75.0, "product": "CL"}),
            content_type='application/json'
        ).json()['trade']

        res = self.client.get(f"/api/trades/{t['id']}/")
        self.assertEqual(res.status_code, 200)
        data = res.json()['trade']
        self.assertEqual(data['id'], t['id'])
        self.assertIn('adjustments', data)
        self.assertEqual(len(data['adjustments']), 1)
        self.assertEqual(data['adjustments'][0]['action'], 'Open')

    def test_update_trade_metadata(self):
        t = self.client.post(
            '/api/trades/',
            data=json.dumps({"size": 1, "price": 50.0, "product": "CL"}),
            content_type='application/json'
        ).json()['trade']

        update_payload = {
            "strategy_label": "Updated Strategy Label",
            "stoploss": 48.0,
            "target": 55.0,
            "notes": "Bot modified target after pivot point test"
        }
        res = self.client.patch(
            f"/api/trades/{t['id']}/",
            data=json.dumps(update_payload),
            content_type='application/json'
        )
        self.assertEqual(res.status_code, 200)
        trade = Trade.objects.get(id=t['id'])
        self.assertEqual(trade.strategy_label, "Updated Strategy Label")
        self.assertEqual(trade.stoploss, 48.0)
        self.assertEqual(trade.target, 55.0)

    def test_adjust_trade_position(self):
        # Open 2 contracts @ 70.0
        t = self.client.post(
            '/api/trades/',
            data=json.dumps({"size": 2.0, "price": 70.0, "product": "CL", "direction": "Long"}),
            content_type='application/json'
        ).json()['trade']

        # 1. Scale in (Add 1 @ 72.0)
        res_add = self.client.post(
            f"/api/trades/{t['id']}/adjust/",
            data=json.dumps({"action": "Add", "size": 1.0, "price": 72.0}),
            content_type='application/json'
        )
        self.assertEqual(res_add.status_code, 200)
        data_add = res_add.json()['trade']
        self.assertEqual(data_add['open_size'], 3.0)
        # VWAP: (2*70 + 1*72) / 3 = 212 / 3 = 70.666667
        self.assertAlmostEqual(data_add['avg_entry_price'], 70.666667, places=4)

        # 2. Scale out / partial take profit (Reduce 1 @ 74.0)
        res_reduce = self.client.post(
            f"/api/trades/{t['id']}/adjust/",
            data=json.dumps({"action": "Reduce", "size": 1.0, "price": 74.0}),
            content_type='application/json'
        )
        self.assertEqual(res_reduce.status_code, 200)
        data_reduce = res_reduce.json()['trade']
        self.assertEqual(data_reduce['open_size'], 2.0)
        self.assertEqual(data_reduce['status'], 'PartiallyReduced')
        self.assertGreater(data_reduce['realized_pnl'], 0)

        # 3. Liquidate / Close remainder @ 75.0
        res_close = self.client.post(
            f"/api/trades/{t['id']}/adjust/",
            data=json.dumps({"action": "Close", "price": 75.0}),
            content_type='application/json'
        )
        self.assertEqual(res_close.status_code, 200)
        data_close = res_close.json()['trade']
        self.assertEqual(data_close['open_size'], 0.0)
        self.assertEqual(data_close['status'], 'Closed')

    def test_delete_trade(self):
        t = self.client.post(
            '/api/trades/',
            data=json.dumps({"size": 1.0, "price": 60.0, "product": "CL"}),
            content_type='application/json'
        ).json()['trade']

        res = self.client.delete(f"/api/trades/{t['id']}/")
        self.assertEqual(res.status_code, 200)
        self.assertFalse(Trade.objects.filter(id=t['id']).exists())

    @override_settings(BOT_API_KEY='secret-bot-key-123')
    def test_api_key_authentication(self):
        # Unauthorized without header
        res_unauth = self.client.get('/api/trades/')
        self.assertEqual(res_unauth.status_code, 401)

        # Authorized with X-API-Key
        res_auth_header = self.client.get(
            '/api/trades/',
            HTTP_X_API_KEY='secret-bot-key-123'
        )
        self.assertEqual(res_auth_header.status_code, 200)

        # Authorized with Authorization Bearer
        res_auth_bearer = self.client.get(
            '/api/trades/',
            HTTP_AUTHORIZATION='Bearer secret-bot-key-123'
        )
        self.assertEqual(res_auth_bearer.status_code, 200)
