from django.urls import path
from . import views

urlpatterns = [
    path('', views.manage_employees, name='manage_employees'),
    path('log/', views.log_attendance, name='log_attendance'),
    path('delete-employee/<int:employee_id>/', views.delete_employee, name='delete_employee'),
]