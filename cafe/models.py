from django.db import models
from django.utils import timezone
from decimal import Decimal

class Player(models.Model):
    name = models.CharField(max_length=100)
    contact = models.CharField(max_length=15, blank=True, null=True)

    def __str__(self):
        return self.name

class Beverage(models.Model):
    name = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=6, decimal_places=2)

    def __str__(self):
        return self.name

class Session(models.Model):
    player = models.ForeignKey(Player, on_delete=models.CASCADE)
    check_in = models.DateTimeField(default=timezone.now)
    check_out = models.DateTimeField(blank=True, null=True)
    beverages = models.ManyToManyField(Beverage, through='SessionItem')

    def get_duration_minutes(self):
        if self.check_out:
            duration = self.check_out - self.check_in
            return int(duration.total_seconds() // 60)
        return 0

    def get_beverage_total(self):
        return sum(item.total_price() for item in self.sessionitem_set.all())

    def get_time_total(self):
        duration_minutes = self.get_duration_minutes()
        pricing = PricingConfig.objects.first()
        hourly_rate = Decimal(str(pricing.hourly_rate))
        
        recharge = Recharge.objects.filter(player=self.player).order_by('-created_at').first()
        if recharge and recharge.hours_remaining > 0:
            free_minutes = Decimal(recharge.hours_remaining) * 60
            duration = Decimal(duration_minutes)
            if duration <= free_minutes:
                # All covered by recharge, cost zero
                return Decimal('0.00')
            else:
                minutes_to_bill = duration - free_minutes
                cost = minutes_to_bill * (hourly_rate / 60)
                return cost.quantize(Decimal('0.01'))
        else:
            # No recharge, full billing
            cost = Decimal(duration_minutes) * (hourly_rate / 60)
            return cost.quantize(Decimal('0.01'))
        
    def deduct_recharge_balance(self):
        duration_minutes = self.get_duration_minutes()
        recharge = Recharge.objects.filter(player=self.player).order_by('-created_at').first()
        
        if recharge and recharge.hours_remaining > 0:
            used_hours = duration_minutes / 60
            if recharge.hours_remaining >= used_hours:
                recharge.hours_remaining -= used_hours
            else:
                recharge.hours_remaining = 0
            recharge.save()
        
    def duration_pretty(self):
        if self.check_out:
            duration = self.check_out - self.check_in
            total_minutes = int(duration.total_seconds() // 60)
            hours = total_minutes // 60
            minutes = total_minutes % 60
            if hours:
                return f"{hours} hr {minutes} min"
            return f"{minutes} min"
        return "In Progress"


    def get_total_bill(self):
        return self.get_time_total() + self.get_beverage_total()

class SessionItem(models.Model):
    session = models.ForeignKey(Session, on_delete=models.CASCADE)
    beverage = models.ForeignKey(Beverage, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)

    def total_price(self):
        return self.beverage.price * self.quantity
    
class PricingConfig(models.Model):
    hourly_rate = models.DecimalField(max_digits=6, decimal_places=2, default=60.0)
    offer_amount = models.PositiveIntegerField(default=500)  # ₹
    offer_hours = models.PositiveIntegerField(default=10)    # Hours

    def __str__(self):
        return f"₹{self.hourly_rate}/hr | Offer: ₹{self.offer_amount} = {self.offer_hours} hrs"

class Recharge(models.Model):
    player = models.ForeignKey(Player, on_delete=models.CASCADE)
    hours_remaining = models.FloatField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.player.name} - {self.hours_remaining} hrs left"
    


