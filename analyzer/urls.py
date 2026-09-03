from django.urls import path
from . import views

urlpatterns = [
    path('', views.home_page, name='home'),  # Points to home_page
    path('analyze/', views.analyze, name='analyze'),
    path('dashboard/', views.dashboard, name='dashboard'),
]