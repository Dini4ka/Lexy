# lexy/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('submit-request/', views.submit_request, name='submit_request'),
    path('request/<int:request_id>/', views.request_status, name='request_status'),
    path('how-it-works/', views.how_it_works, name='how_it_works'),
]