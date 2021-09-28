from django.contrib import admin


from .models import  Instrument, TradeSession, Trade
# Register your models here.

admin.site.register(Instrument)
admin.site.register(Trade)
admin.site.register(TradeSession)

