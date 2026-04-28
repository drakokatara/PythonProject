from django.urls import path
from . import views

urlpatterns = [
    path('',views.manage_employees, name='manage_employees'),
    path('attendance/', views.log_attendance,   name='log_attendance'),
    path('calendar/<int:employee_id>/', views.employee_calendar, name='employee_calendar'),
]