from django.shortcuts import render, get_object_or_404, redirect
from .models import Player, Beverage, Session, SessionItem, Recharge, PricingConfig
from django.utils import timezone
from django.contrib import messages
from django.db import transaction
from decimal import Decimal
from django.db.models import Q

def player_profile(request, player_id):
    player = get_object_or_404(Player, id=player_id)
    sessions = Session.objects.filter(player=player).order_by('-check_in')

    total_minutes = sum([s.get_duration_minutes() for s in sessions if s.check_out])
    total_spent = sum([s.get_total_bill() for s in sessions if s.check_out])

    recharge = Recharge.objects.filter(player=player).order_by('-created_at').first()
    hours_remaining = round(recharge.hours_remaining, 2) if recharge else 0

    return render(request, 'cafe/player_profile.html', {
        'player': player,
        'sessions': sessions,
        'total_minutes': total_minutes,
        'total_spent': total_spent,
        'hours_remaining': hours_remaining,
    })

def home(request):
    active_sessions = Session.objects.filter(check_out__isnull=True)
    return render(request, 'cafe/home.html', {'sessions': active_sessions})

def checkin(request):
    if request.method == 'POST':
        player_id = request.POST.get('player')
        new_name = request.POST.get('new_player_name', '').strip()

        if player_id:
            player = Player.objects.get(id=player_id)
        elif new_name:
            player = Player.objects.filter(name__iexact=new_name).first()
            if not player:
                player = Player.objects.create(name=new_name, contact='')
        else:
            return render(request, 'cafe/checkin.html', {
                'players': Player.objects.all(),
                'error': "Please select an existing player or enter a new name."
            })

        # Check if this player already has an active session
        active_session = Session.objects.filter(player=player, check_out__isnull=True).first()
        if active_session:
            # Player already checked in without checkout
            return render(request, 'cafe/checkin.html', {
                'players': Player.objects.all(),
                'error': f"Player '{player.name}' already has an active session.",
                'active_session': active_session,  # Pass session to template
            })

        # Create new session if no active session found
        session = Session.objects.create(player=player)
        return redirect('add_beverages', session.id)

    players = Player.objects.all()
    return render(request, 'cafe/checkin.html', {'players': players})

def add_beverages(request, session_id):
    session = get_object_or_404(Session, id=session_id)

    if request.method == 'POST':
        bev_id = int(request.POST['beverage'])
        qty = int(request.POST['quantity'])

        bev = Beverage.objects.get(id=bev_id)
        SessionItem.objects.create(session=session, beverage=bev, quantity=qty)
        return redirect('add_beverages', session.id)

    beverages = Beverage.objects.all()
    items = session.sessionitem_set.all()
    return render(request, 'cafe/add_beverages.html', {'session': session, 'beverages': beverages, 'items': items})

def checkout(request, session_id):
    session = get_object_or_404(Session, id=session_id)

    if request.method == 'POST':
        # Finalize checkout
        with transaction.atomic():
            session.check_out = timezone.now()
            session.save()
        return redirect('session_logs')

    # Calculate duration using current time if session not checked out yet
    if session.check_out:
        duration_minutes = session.get_duration_minutes()
        time_charge = session.get_time_total()
    else:
        current_time = timezone.now()
        duration = current_time - session.check_in
        duration_minutes = int(duration.total_seconds() // 60)
        
        # Temporarily calculate time charge for display
        pricing = PricingConfig.objects.first()
        hourly_rate = Decimal(str(pricing.hourly_rate))
        
        # Calculate cost like in get_time_total but with current_time as check_out
        recharge = Recharge.objects.filter(player=session.player).order_by('-created_at').first()
        
        if recharge and recharge.hours_remaining > 0:
            free_minutes = Decimal(str(recharge.hours_remaining)) * 60
            duration_dec = Decimal(duration_minutes)
            if duration_dec <= free_minutes:
                time_charge = Decimal('0.00')
            else:
                minutes_to_bill = duration_dec - free_minutes
                cost = minutes_to_bill * (hourly_rate / 60)
                time_charge = cost.quantize(Decimal('0.01'))
        else:
            cost = Decimal(duration_minutes) * (hourly_rate / 60)
            time_charge = cost.quantize(Decimal('0.01'))

    beverage_charge = session.get_beverage_total()
    total_bill = time_charge + beverage_charge

    return render(request, 'cafe/checkout.html', {
        'session': session,
        'duration_minutes': duration_minutes,
        'time_charge': time_charge,
        'beverage_charge': beverage_charge,
        'total_bill': total_bill,
    })



def session_logs(request):
    sessions = Session.objects.all().order_by('-check_in')
    return render(request, 'cafe/session_logs.html', {'sessions': sessions})

from django.db.models import Q

def recharge_player(request):
    if request.method == 'POST':
        player_id = request.POST.get('player')
        new_name = request.POST.get('new_player_name', '').strip()

        if player_id:
            # Existing player selected
            player = Player.objects.get(id=player_id)
        elif new_name:
            # Check if player exists (case-insensitive)
            player = Player.objects.filter(name__iexact=new_name).first()
            if not player:
                # Create new if not found
                player = Player.objects.create(name=new_name, contact='')
            # else player found, so no duplicate created
        else:
            players = Player.objects.all()
            return render(request, 'cafe/recharge.html', {
                'players': players,
                'error': "Please select an existing player or enter a new player name."
            })

        pricing = PricingConfig.objects.first()
        Recharge.objects.create(
            player=player,
            hours_remaining=pricing.offer_hours
        )
        return redirect('home')

    players = Player.objects.all()
    return render(request, 'cafe/recharge.html', {'players': players})

def manage_beverages(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        price = request.POST.get('price')

        if name and price:
            Beverage.objects.create(name=name, price=price)
            messages.success(request, "Beverage added successfully.")
            return redirect('manage_beverages')

    beverages = Beverage.objects.all()
    return render(request, 'cafe/manage_beverages.html', {'beverages': beverages})




