from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('checkin/', views.checkin, name='checkin'),
    path('add_beverages/<int:session_id>/', views.add_beverages, name='add_beverages'),
    path('beverages/', views.manage_beverages, name='manage_beverages'),
    path('checkout/<int:session_id>/', views.checkout, name='checkout'),
    path('logs/', views.session_logs, name='session_logs'),
    path('recharge/', views.recharge_player, name='recharge'),
    path('player/<int:player_id>/', views.player_profile, name='player_profile'),
]
