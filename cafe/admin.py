from django.contrib import admin
from .models import PricingConfig, Recharge, Player

# Register your models here.

admin.site.register(Player)
admin.site.register(PricingConfig)
admin.site.register(Recharge)

