import random
from datetime import datetime, date, time, timedelta
from django.core.management.base import BaseCommand
from django.db import transaction
from journal.models import (
    Account, Trade, TradeLeg, PositionAdjustment, StrategyTemplate
)
from journal import utils as product_utils
from journal import services

PRODUCTS_CATALOG = [
    {"sym": "CL", "name": "Crude Oil", "grp": "Energy", "base_px": 74.50, "tick_sz": 0.01, "mult": 1000.0},
    {"sym": "NG", "name": "Natural Gas", "grp": "Energy", "base_px": 2.650, "tick_sz": 0.001, "mult": 10000.0},
    {"sym": "ZC", "name": "Corn", "grp": "Agriculture", "base_px": 445.0, "tick_sz": 0.25, "mult": 50.0},
    {"sym": "ZS", "name": "Soybeans", "grp": "Agriculture", "base_px": 1040.0, "tick_sz": 0.25, "mult": 50.0},
    {"sym": "ZW", "name": "Wheat", "grp": "Agriculture", "base_px": 570.0, "tick_sz": 0.25, "mult": 50.0},
    {"sym": "FCPO", "name": "Palm Oil", "grp": "Agriculture", "base_px": 4120.0, "tick_sz": 1.0, "mult": 25.0},
    {"sym": "GC", "name": "Gold", "grp": "Metals", "base_px": 2650.0, "tick_sz": 0.10, "mult": 100.0},
    {"sym": "SI", "name": "Silver", "grp": "Metals", "base_px": 31.80, "tick_sz": 0.005, "mult": 5000.0},
    {"sym": "HG", "name": "Copper", "grp": "Metals", "base_px": 4.42, "tick_sz": 0.0005, "mult": 25000.0},
    {"sym": "ES", "name": "E-mini S&P", "grp": "Equity Indices", "base_px": 5780.0, "tick_sz": 0.25, "mult": 50.0},
    {"sym": "NQ", "name": "Nasdaq 100", "grp": "Equity Indices", "base_px": 20450.0, "tick_sz": 0.25, "mult": 20.0},
    {"sym": "6E", "name": "Euro FX", "grp": "Currencies", "base_px": 1.0920, "tick_sz": 0.00005, "mult": 125000.0},
    {"sym": "LE", "name": "Live Cattle", "grp": "Livestock", "base_px": 188.50, "tick_sz": 0.025, "mult": 400.0},
    {"sym": "SB", "name": "Sugar #11", "grp": "Softs", "base_px": 22.40, "tick_sz": 0.01, "mult": 1120.0},
    {"sym": "KC", "name": "Coffee C", "grp": "Softs", "base_px": 248.0, "tick_sz": 0.05, "mult": 375.0},
]

MONTH_CODES = ["Jun 2026", "Jul 2026", "Aug 2026", "Sep 2026", "Oct 2026", "Nov 2026", "Dec 2026", "Jan 2027", "Mar 2027"]

ANALYSIS_TAGS = [
    ["Price action", "Seasonality"],
    ["COT Positioning", "Macro"],
    ["Forward curve backwardation", "Inventory tight"],
    ["Support retest", "COT Data"],
    ["Breakout momentum", "Seasonality"],
    ["Physical S&D Deficit", "MPOB Data"],
    ["Mean reversion", "RSI divergence"],
]

EMOTIONS = ["Confident", "Aggressive", "Going with the Flow", "Fear", "Not so Confident"]

class Command(BaseCommand):
    help = 'Seeds 200 realistic multi-leg and outright trades distributed across multiple accounts'

    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write("Initializing multi-account seeding...")

        # 1. Setup Accounts
        acc1, _ = Account.objects.get_or_create(
            name="Apex 50K #1",
            defaults={"description": "Primary Funded Prop Desk", "initial_balance": 50000.0, "currency": "USD", "is_default": True}
        )
        acc2, _ = Account.objects.get_or_create(
            name="Topstep 150K",
            defaults={"description": "Secondary Prop Account", "initial_balance": 150000.0, "currency": "USD", "is_default": False}
        )
        acc3, _ = Account.objects.get_or_create(
            name="Personal Futures",
            defaults={"description": "Personal Cash Margin Account", "initial_balance": 75000.0, "currency": "USD", "is_default": False}
        )
        accounts = [acc1, acc2, acc3]
        acc_weights = [0.50, 0.35, 0.15]  # 100 trades acc1, 70 trades acc2, 30 trades acc3

        # Clear existing trades if any
        existing_count = Trade.objects.count()
        if existing_count > 0:
            self.stdout.write(f"Clearing {existing_count} existing trades...")
            Trade.objects.all().delete()

        # Preload templates
        strat_1ms = StrategyTemplate.objects.filter(name__icontains='1MS').first()
        strat_1mf = StrategyTemplate.objects.filter(name__icontains='1MF').first()

        start_date = datetime.now() - timedelta(days=150)
        self.stdout.write("Generating 200 institutional commodity trades...")

        # Cumulative PnL target bias: ~62% win rate
        total_seeded = 0

        for i in range(200):
            # Pick account
            acc = random.choices(accounts, weights=acc_weights, k=1)[0]
            
            # Timestamp distributed from May to Oct 2026
            day_offset = random.randint(0, 145)
            hour = random.randint(8, 17)
            minute = random.randint(0, 59)
            trade_dt = start_date + timedelta(days=day_offset, hours=hour, minutes=minute)
            trade_d = trade_dt.date()
            trade_t = trade_dt.time().replace(microsecond=0)

            # Pick Product
            prod = random.choice(PRODUCTS_CATALOG)
            direction = random.choice(["Long", "Short"])
            size = random.choice([1, 2, 3, 5, 8, 10])
            emotion = random.choice(EMOTIONS)
            analysis = random.choice(ANALYSIS_TAGS)

            # Determine Trade Type & Strategy
            rand_strat = random.random()
            if rand_strat < 0.40:
                trade_type = "Outright"
                template = None
                m1 = random.choice(MONTH_CODES[:4])
                label = f"{prod['sym']} {m1} Outright"
                legs = [{
                    "product": prod["sym"],
                    "product_group": prod["grp"],
                    "contract_month": m1,
                    "direction": "Buy" if direction == "Long" else "Sell",
                    "ratio": 1.0
                }]
                base_entry = round(prod["base_px"] + (random.uniform(-0.05, 0.05) * prod["base_px"]), 3)

            elif rand_strat < 0.80:
                trade_type = "CalendarSpread"
                template = strat_1ms
                m_idx = random.randint(0, 4)
                m1 = MONTH_CODES[m_idx]
                m2 = MONTH_CODES[m_idx + 1]
                label = f"{prod['sym']} {m1}/{m2} 1MS Spread"
                legs = [
                    {"product": prod["sym"], "product_group": prod["grp"], "contract_month": m1, "direction": "Buy" if direction == "Long" else "Sell", "ratio": 1.0},
                    {"product": prod["sym"], "product_group": prod["grp"], "contract_month": m2, "direction": "Sell" if direction == "Long" else "Buy", "ratio": 1.0},
                ]
                # Spreads trade around differential
                base_entry = round(random.uniform(-1.5, 3.5), 3)

            else:
                trade_type = "Butterfly"
                template = strat_1mf
                m_idx = random.randint(0, 3)
                m1 = MONTH_CODES[m_idx]
                m2 = MONTH_CODES[m_idx + 1]
                m3 = MONTH_CODES[m_idx + 2]
                label = f"{prod['sym']} {m1}/{m2}/{m3} 1MF Fly"
                legs = [
                    {"product": prod["sym"], "product_group": prod["grp"], "contract_month": m1, "direction": "Buy" if direction == "Long" else "Sell", "ratio": 1.0},
                    {"product": prod["sym"], "product_group": prod["grp"], "contract_month": m2, "direction": "Sell" if direction == "Long" else "Buy", "ratio": 2.0},
                    {"product": prod["sym"], "product_group": prod["grp"], "contract_month": m3, "direction": "Buy" if direction == "Long" else "Sell", "ratio": 1.0},
                ]
                base_entry = round(random.uniform(-0.8, 1.8), 3)

            # Determine Status:
            # First 175 trades are Closed. Next 15 are Open. Last 10 are PartiallyReduced.
            if i < 175:
                status = "Closed"
            elif i < 190:
                status = "Open"
            else:
                status = "PartiallyReduced"

            # Create Master Trade
            trade = Trade.objects.create(
                trade_type=trade_type,
                direction=direction,
                status=status,
                strategy_label=label,
                strategy_template=template,
                account=acc,
                notes=f"Institutional setup execution. Analysis: {', '.join(analysis)}.",
                trade_date=trade_d,
                trade_time=trade_t,
                analysis=analysis,
                emotion=emotion,
                created_at=trade_dt,
            )

            # Create constituent legs
            for leg in legs:
                TradeLeg.objects.create(
                    trade=trade,
                    product=leg["product"],
                    product_group=leg["product_group"],
                    contract_month=leg["contract_month"],
                    direction=leg["direction"],
                    ratio=leg["ratio"],
                )

            # 1. Initial PositionAdjustment (Open)
            open_adj = PositionAdjustment.objects.create(
                trade=trade,
                action="Open",
                size_change=size,
                price=base_entry,
                pnl=0.0,
                notes="Initial entry fill",
            )
            # Override auto_now timestamp for historical accuracy
            open_adj.timestamp = trade_dt
            open_adj.save(update_fields=['timestamp'])

            # Multiplier for cash PnL
            mult = prod["mult"]

            # 2. Add Adjustments depending on status
            if status == "Closed":
                # Exit duration: 1 to 8 days later
                exit_dt = trade_dt + timedelta(days=random.randint(1, 8), hours=random.randint(1, 4))
                # 62% win probability
                is_win = (random.random() < 0.62)
                if is_win:
                    delta_ticks = random.uniform(0.005, 0.035) * base_entry if abs(base_entry) > 5 else random.uniform(0.15, 1.25)
                    pnl_cash = round(abs(delta_ticks * mult * size), 2)
                    exit_px = round(base_entry + delta_ticks if direction == "Long" else base_entry - delta_ticks, 3)
                else:
                    delta_ticks = random.uniform(0.003, 0.025) * base_entry if abs(base_entry) > 5 else random.uniform(0.10, 0.85)
                    pnl_cash = -round(abs(delta_ticks * mult * size), 2)
                    exit_px = round(base_entry - delta_ticks if direction == "Long" else base_entry + delta_ticks, 3)

                close_adj = PositionAdjustment.objects.create(
                    trade=trade,
                    action="Close",
                    size_change=-size,
                    price=exit_px,
                    pnl=pnl_cash,
                    notes="Take-profit target hit" if is_win else "Stop-loss exit triggered",
                )
                close_adj.timestamp = exit_dt
                close_adj.save(update_fields=['timestamp'])

            elif status == "PartiallyReduced":
                # Partial reduction: close 50%
                reduce_size = max(1, size // 2)
                reduce_dt = trade_dt + timedelta(days=random.randint(1, 3))
                is_win = (random.random() < 0.70)
                delta_ticks = random.uniform(0.005, 0.02) * base_entry if abs(base_entry) > 5 else random.uniform(0.10, 0.60)
                pnl_cash = round(abs(delta_ticks * mult * reduce_size), 2) if is_win else -round(abs(delta_ticks * mult * reduce_size), 2)
                exit_px = round(base_entry + delta_ticks if direction == "Long" else base_entry - delta_ticks, 3)

                red_adj = PositionAdjustment.objects.create(
                    trade=trade,
                    action="Reduce",
                    size_change=-reduce_size,
                    price=exit_px,
                    pnl=pnl_cash,
                    notes="De-risked 50% at 1st target",
                )
                red_adj.timestamp = reduce_dt
                red_adj.save(update_fields=['timestamp'])

            elif status == "Open":
                # Some open trades have a scale-in (Add)
                if random.random() < 0.35:
                    add_size = random.choice([1, 2])
                    add_dt = trade_dt + timedelta(hours=random.randint(2, 24))
                    add_px = round(base_entry * (1.002 if direction == "Long" else 0.998), 3)
                    add_adj = PositionAdjustment.objects.create(
                        trade=trade,
                        action="Add",
                        size_change=add_size,
                        price=add_px,
                        pnl=0.0,
                        notes="Pyramided position on confirmation",
                    )
                    add_adj.timestamp = add_dt
                    add_adj.save(update_fields=['timestamp'])

            total_seeded += 1

        self.stdout.write(self.style.SUCCESS(f"Successfully seeded {total_seeded} institutional trades across 3 accounts!"))
