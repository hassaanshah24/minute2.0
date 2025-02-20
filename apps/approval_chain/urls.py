from django.urls import path
from . import views

app_name = 'approval_chain'

urlpatterns = [
    path('create/', views.create_approval_chain, name='create'),
]
