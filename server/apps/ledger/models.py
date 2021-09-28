from django.db import models


# Create your models here.

class Instrument(models.Model):
    instrument_token = models.CharField(max_length=50)
    exchange_token = models.CharField(max_length=50)
    tradingsymbol = models.CharField(max_length=50, null=True, blank=True)
    name = models.CharField(max_length=50, null=True, blank=True)
    last_price = models.CharField(max_length=50, null=True, blank=True)
    expiry = models.CharField(max_length=50, null=True, blank=True)
    strike = models.CharField(max_length=50, null=True, blank=True)
    tick_size = models.CharField(max_length=50, null=True, blank=True)
    lot_size = models.CharField(max_length=50, null=True, blank=True)
    instrument_type = models.CharField(max_length=20, null=True, blank=True)
    segment = models.CharField(max_length=20, null=True, blank=True)
    exchange = models.CharField(max_length=20, null=True, blank=True)


class TradeSession(models.Model):
    session_id = models.CharField(max_length=150, unique=True)
    session_type = models.CharField(max_length=10, null=True)  # simulation or live
    instrument = models.ForeignKey(Instrument, on_delete=models.SET_NULL, null=True, related_name='instrument')
    ml_model = models.CharField(max_length=100, null=True)
    timeframe = models.CharField(max_length=20, null=True)
    target_profit_percentage = models.CharField(max_length=10, null=True)
    max_profit = models.CharField(max_length=20, null=True)
    stoploss = models.CharField(max_length=20, null=True)
    r2r = models.CharField(max_length=20, null=True)
    total_trades = models.CharField(max_length=10, null=True, blank=True)
    profitable_trades = models.CharField(max_length=10, null=True, blank=True)
    non_profitable_trades = models.CharField(max_length=10, null=True, blank=True)
    profit = models.CharField(max_length=20, null=True, blank=True)
    loss = models.CharField(max_length=20, null=True, blank=True)
    charges = models.CharField(max_length=20, null=True, blank=True)
    gross_profit = models.CharField(max_length=20, null=True, blank=True)
    net_profit = models.CharField(max_length=20, null=True, blank=True)
    start_time = models.DateTimeField(null=True, blank=True)
    end_time = models.DateTimeField(null=True, blank=True)


class Trade(models.Model):
    session = models.ForeignKey(TradeSession, on_delete=models.SET_NULL, null=True)
    type = models.CharField(max_length=10, null=True, blank=True)
    quantity = models.CharField(max_length=20, null=True, blank=True)
    entry = models.CharField(max_length=20, null=True, blank=True)
    exit = models.CharField(max_length=20, null=True, blank=True)
    profit = models.CharField(max_length=20, null=True, blank=True)
    brokerage = models.CharField(max_length=20, null=True, blank=True)
    stt = models.CharField(max_length=20, null=True, blank=True)
    gst = models.CharField(max_length=20, null=True, blank=True)
    sebi_charges = models.CharField(max_length=20, null=True, blank=True)
    stamp_duty = models.CharField(max_length=20, null=True, blank=True)
    total_charges = models.CharField(max_length=20, null=True, blank=True)
