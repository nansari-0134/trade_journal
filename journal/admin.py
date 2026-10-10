from django.contrib import admin
from .models import Trade, TradeLeg, PositionAdjustment, PlannedTrade, StrategyTemplate


@admin.register(StrategyTemplate)
class StrategyTemplateAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'leg_ratios', 'usage_count', 'is_default')
    list_filter = ('category', 'is_default')
    search_fields = ('name',)


class TradeLegInline(admin.TabularInline):
    model = TradeLeg
    extra = 1


class PositionAdjustmentInline(admin.TabularInline):
    model = PositionAdjustment
    extra = 0
    readonly_fields = ('timestamp',)


@admin.register(Trade)
class TradeAdmin(admin.ModelAdmin):
    list_display = ('id', 'trade_type', 'direction', 'status', 'strategy_label', 'created_at')
    list_filter = ('trade_type', 'direction', 'status')
    search_fields = ('strategy_label', 'notes')
    inlines = [TradeLegInline, PositionAdjustmentInline]


@admin.register(PlannedTrade)
class PlannedTradeAdmin(admin.ModelAdmin):
    list_display = ('id', 'trade_type', 'product', 'direction', 'frequency', 'status', 'created_at')
    list_filter = ('trade_type', 'frequency', 'status')
    search_fields = ('strategy_label', 'reasoning')
