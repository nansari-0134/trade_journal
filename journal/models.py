from django.db import models
import uuid
import datetime


class InterProductPair(models.Model):
    """
    Stores predefined inter-product pairs (e.g., CL-BZ).
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=50, unique=True, help_text='e.g. CL-BZ')
    product_1 = models.CharField(max_length=30)
    product_2 = models.CharField(max_length=30)
    
    def __str__(self):
        return f"{self.name} ({self.product_1} vs {self.product_2})"


class StrategyTemplate(models.Model):
    """
    Predefined strategy configuration storing leg ratios.
    e.g. 1MS=[1,-1], 1MF=[1,-2,1], 1MDF=[1,3,3,-1]
    The ratios map to consecutive contract months relative to the front month.
    """
    CATEGORY_CHOICES = [
        ('Spread', 'Spread'),
        ('Butterfly', 'Butterfly'),
        ('DoubleFly', 'Double Fly'),
        ('InterProduct', 'Inter-Product'),
        ('Custom', 'Custom'),
    ]
    
    TYPE_CHOICES = [
        ('Calendar', 'Calendar (Same Product, Different Months)'),
        ('InterProduct', 'Interproduct (Different Products, Same Month)'),
        ('Custom', 'Custom'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=50, unique=True, help_text='e.g. 1MS, 2MF, G-Fly 2:1')
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='Custom')
    strategy_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='Calendar')
    leg_ratios = models.JSONField(
        default=list,
        help_text='List of leg ratios e.g. [1, -1] for spread, [1, -2, 1] for fly'
    )
    is_default = models.BooleanField(default=False, help_text='Seeded by system')
    usage_count = models.IntegerField(default=0, help_text='Track popularity for sorting')


    class Meta:
        ordering = ['-usage_count', 'name']

    def __str__(self):
        return f"{self.name} ({self.category}) {self.leg_ratios}"

    @property
    def num_legs(self):
        return len(self.leg_ratios)

    @property
    def non_zero_legs(self):
        """Return list of (index, ratio) for non-zero legs."""
        return [(i, r) for i, r in enumerate(self.leg_ratios) if r != 0]


class Trade(models.Model):
    """
    Parent trade record. A trade can be a simple outright or a complex
    multi-leg strategy (spread, butterfly, etc.). Each trade has one or
    more TradeLeg records and an audit trail of PositionAdjustments.
    """
    TRADE_TYPE_CHOICES = [
        ('Outright', 'Outright'),
        ('CalendarSpread', 'Calendar Spread'),
        ('Butterfly', 'Butterfly'),
        ('DoubleFly', 'Double Fly'),
        ('InterProductSpread', 'Inter-Product Spread'),
        ('SpreadVsSpread', 'Spread vs Spread'),
    ]
    DIRECTION_CHOICES = [
        ('Long', 'Long'),
        ('Short', 'Short'),
    ]
    STATUS_CHOICES = [
        ('Open', 'Open'),
        ('PartiallyReduced', 'Partially Reduced'),
        ('Closed', 'Closed'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    trade_type = models.CharField(max_length=30, choices=TRADE_TYPE_CHOICES, default='Outright')
    direction = models.CharField(max_length=10, choices=DIRECTION_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Open')
    strategy_label = models.CharField(max_length=200, blank=True, default='',
                                      help_text='User-defined label, e.g. "CL 1M Spread"')
    strategy_template = models.ForeignKey(
        StrategyTemplate, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='trades'
    )
    notes = models.TextField(blank=True, default='')
    
    # Date/Time fields - editable but default to entry time
    trade_date = models.DateField(null=True, blank=True, help_text='Date of trade entry (defaults to today)')
    trade_time = models.TimeField(null=True, blank=True, help_text='Time of trade entry (defaults to now)')
    
    # Analysis sources (list of strings stored as JSON)
    analysis = models.JSONField(
        default=list, blank=True,
        help_text='List of analysis sources e.g. ["Seasonality", "Price action"]'
    )
    
    # Trade expiry date
    expiry_date = models.DateField(null=True, blank=True, help_text='When does this trade expire')

    # Emotion at trade entry
    EMOTION_CHOICES = [
        ('Fear', 'Fear'),
        ('Aggressive', 'Aggressive'),
        ('Confident', 'Confident'),
        ('Not so Confident', 'Not so Confident'),
        ('Going with the Flow', 'Going with the Flow'),
    ]
    emotion = models.CharField(max_length=30, blank=True, default='', choices=EMOTION_CHOICES)

    # Screenshot (stored as base64 data URL)
    screenshot = models.TextField(blank=True, default='', help_text='Base64-encoded screenshot')

    # Price tracking
    market_price = models.FloatField(null=True, blank=True, help_text='Current market price')
    stoploss = models.FloatField(null=True, blank=True, help_text='Stop loss level')
    target = models.FloatField(null=True, blank=True, help_text='Target level')

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.trade_type} | {self.direction} | {self.strategy_label or 'Unlabeled'}"

    @property
    def total_open_size(self):
        """Current open position size (sum of all adjustments)."""
        result = self.adjustments.aggregate(total=models.Sum('size_change'))
        return result['total'] or 0

    @property
    def realized_pnl(self):
        """Sum of PnL from all Reduce/Close adjustments."""
        close_actions = self.adjustments.filter(action__in=['Reduce', 'Close'])
        result = close_actions.aggregate(total=models.Sum('pnl'))
        return round(result['total'] or 0, 6)

    @property
    def avg_entry_price(self):
        """Weighted average entry price from Open/Add adjustments."""
        opens = self.adjustments.filter(action__in=['Open', 'Add']).exclude(price__isnull=True)
        total_size = 0
        weighted_sum = 0
        for adj in opens:
            if adj.size_change and adj.price is not None:
                total_size += abs(adj.size_change)
                weighted_sum += abs(adj.size_change) * float(adj.price)
        return round(weighted_sum / total_size, 6) if total_size else 0


class TradeLeg(models.Model):
    """
    Individual leg of a strategy trade. An Outright has 1 leg,
    a Calendar Spread has 2, a Butterfly has 3, etc.
    """
    LEG_DIRECTION_CHOICES = [
        ('Buy', 'Buy'),
        ('Sell', 'Sell'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    trade = models.ForeignKey(Trade, on_delete=models.CASCADE, related_name='legs')

    product = models.CharField(max_length=30, help_text='Symbol from Products.xlsx')
    product_group = models.CharField(max_length=50, blank=True, default='')
    contract_month = models.CharField(max_length=20, blank=True, default='',
                                      help_text='e.g. "Jun 2026" or "M26"')
    direction = models.CharField(max_length=10, choices=LEG_DIRECTION_CHOICES)
    ratio = models.FloatField(default=1.0, help_text='Quantity multiplier for this leg')

    class Meta:
        ordering = ['id']

    def __str__(self):
        return f"{self.direction} {self.ratio}x {self.product} {self.contract_month}"


class PositionAdjustment(models.Model):
    """
    Immutable audit log entry for every position change on a trade.
    Adding, reducing, and closing positions are all recorded here.
    """
    ACTION_CHOICES = [
        ('Open', 'Open'),
        ('Add', 'Add'),
        ('Reduce', 'Reduce'),
        ('Close', 'Close'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    trade = models.ForeignKey(Trade, on_delete=models.CASCADE, related_name='adjustments')
    timestamp = models.DateTimeField(auto_now_add=True)

    action = models.CharField(max_length=10, choices=ACTION_CHOICES)
    size_change = models.FloatField(
        help_text='Positive for Open/Add, negative for Reduce/Close'
    )
    price = models.FloatField(null=True, blank=True)
    pnl = models.FloatField(default=0, help_text='Realized PnL from this specific adjustment')
    notes = models.CharField(max_length=500, blank=True, default='')

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.action} {self.size_change} @ {self.price}"


class PlannedTrade(models.Model):
    """
    Trade idea / plan with optional scheduling and image-based reasoning.
    """
    FREQUENCY_CHOICES = [
        ('Once', 'Once'),
        ('Monthly', 'Monthly'),
        ('Yearly', 'Yearly'),
        ('SpecificMonths', 'Specific Months'),
    ]
    STATUS_CHOICES = [
        ('Planned', 'Planned'),
        ('Executed', 'Executed'),
        ('Cancelled', 'Cancelled'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    trade_type = models.CharField(max_length=30, choices=Trade.TRADE_TYPE_CHOICES, default='Outright')
    product = models.CharField(max_length=30, blank=True, default='')
    product_group = models.CharField(max_length=50, blank=True, default='')
    contract_month = models.CharField(max_length=20, blank=True, default='')
    direction = models.CharField(max_length=10, choices=Trade.DIRECTION_CHOICES, blank=True)
    strategy_label = models.CharField(max_length=200, blank=True, default='')
    strategy_template = models.ForeignKey(
        StrategyTemplate, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='planned_trades'
    )

    frequency = models.CharField(max_length=20, choices=FREQUENCY_CHOICES, default='Once')
    specific_months = models.JSONField(
        default=list, blank=True,
        help_text='List of month names, e.g. ["Mar", "Sep"]'
    )

    reasoning = models.TextField(blank=True, default='')
    image = models.ImageField(upload_to='planned_trade_images/', null=True, blank=True)

    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='Planned')

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"[{self.status}] {self.trade_type} {self.product} – {self.strategy_label}"


class CotReport(models.Model):
    """
    Stores CFTC Commitments of Traders (Legacy Futures Only) data, cached locally.
    Unique per (report_date, market_code) to prevent duplicates.
    """
    report_date = models.DateField(db_index=True)
    market_code = models.CharField(max_length=20, db_index=True)
    market_name = models.CharField(max_length=200, blank=True)
    commodity_name = models.CharField(max_length=100, blank=True)
    commodity_group = models.CharField(max_length=100, blank=True)

    open_interest = models.BigIntegerField(default=0)

    # Non-Commercial (Speculators)
    noncomm_long = models.BigIntegerField(default=0)
    noncomm_short = models.BigIntegerField(default=0)
    noncomm_spread = models.BigIntegerField(default=0)

    # Commercial (Hedgers)
    comm_long = models.BigIntegerField(default=0)
    comm_short = models.BigIntegerField(default=0)

    # Non-Reportable (Small Speculators)
    nonrept_long = models.BigIntegerField(default=0)
    nonrept_short = models.BigIntegerField(default=0)

    week_of_year = models.IntegerField(default=0)
    year = models.IntegerField(default=0)

    class Meta:
        unique_together = ('report_date', 'market_code')
        ordering = ['-report_date']

    def __str__(self):
        return f"{self.market_code} – {self.report_date}"

    def save(self, *args, **kwargs):
        import datetime
        d = self.report_date
        if isinstance(d, str):
            d = datetime.date.fromisoformat(d[:10])
        self.week_of_year = d.isocalendar()[1]
        self.year = d.year
        super().save(*args, **kwargs)

# -----------------------------------------------------------------------------
# Palm Oil Fundamentals & Market Data Models
# -----------------------------------------------------------------------------

class PalmOilPriceAndOI(models.Model):
    """
    Stores daily price and Open Interest for specific FCPO contract months.
    """
    date = models.DateField(db_index=True)
    contract_month = models.CharField(max_length=20, help_text='e.g. "Jun 2026" or "M26"', db_index=True)
    
    open_price = models.FloatField(null=True, blank=True)
    high_price = models.FloatField(null=True, blank=True)
    low_price = models.FloatField(null=True, blank=True)
    close_price = models.FloatField(null=True, blank=True)
    
    open_interest = models.BigIntegerField(null=True, blank=True)
    volume = models.BigIntegerField(null=True, blank=True)
    
    class Meta:
        unique_together = ('date', 'contract_month')
        ordering = ['-date', 'contract_month']

    def __str__(self):
        return f"{self.contract_month} on {self.date}"


class MPOBData(models.Model):
    """
    Stores monthly MPOB (Malaysian Palm Oil Board) statistics.
    """
    year = models.IntegerField(db_index=True)
    month = models.IntegerField(db_index=True)  # 1-12
    
    production = models.FloatField(null=True, blank=True, help_text="Crude Palm Oil Production (in metric tonnes)")
    imports = models.FloatField(null=True, blank=True, help_text="Total Imports (in metric tonnes)")
    exports = models.FloatField(null=True, blank=True, help_text="Total Exports (in metric tonnes)")
    local_consumption = models.FloatField(null=True, blank=True, help_text="Local Disappearance/Consumption (in metric tonnes)")
    end_stocks = models.FloatField(null=True, blank=True, help_text="Closing Stocks (in metric tonnes)")
    
    class Meta:
        unique_together = ('year', 'month')
        ordering = ['-year', '-month']
        verbose_name = "MPOB Data"
        verbose_name_plural = "MPOB Data"

    def __str__(self):
        return f"MPOB Data {self.year}-{self.month:02d}"


class ExportSurveyorData(models.Model):
    """
    Stores high-frequency export estimates from surveyors like SGS, ITS, AmSpec.
    """
    SURVEYOR_CHOICES = [
        ('SGS', 'SGS'),
        ('ITS', 'ITS'),
        ('AmSpec', 'AmSpec'),
    ]
    
    year = models.IntegerField(db_index=True)
    month = models.IntegerField(db_index=True)  # 1-12
    surveyor = models.CharField(max_length=20, choices=SURVEYOR_CHOICES, db_index=True)
    
    # Export quantities for typical periods in the month
    day_1_to_10 = models.FloatField(null=True, blank=True)
    day_1_to_15 = models.FloatField(null=True, blank=True)
    day_1_to_20 = models.FloatField(null=True, blank=True)
    day_1_to_25 = models.FloatField(null=True, blank=True)
    full_month = models.FloatField(null=True, blank=True)
    
    class Meta:
        unique_together = ('year', 'month', 'surveyor')
        ordering = ['-year', '-month', 'surveyor']

    def __str__(self):
        return f"{self.surveyor} {self.year}-{self.month:02d}"
