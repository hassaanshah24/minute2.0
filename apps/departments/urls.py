# department/urls.py

from django.urls import path
from .views import department_dashboard

app_name = 'departments'

urlpatterns = [
    path('dashboard/', department_dashboard, name='dashboard'),

]
