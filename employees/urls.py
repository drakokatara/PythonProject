from django.urls import path
from . import views

urlpatterns = [
    path('', views.manage_employees, name='manage_employees'),
    path('log/', views.log_attendance, name='log_attendance'),
    path('delete-employee/<int:employee_id>/', views.delete_employee, name='delete_employee'),
    path('edit-attendance/<int:att_id>/', views.edit_attendance, name='edit_attendance'),
    path('update-attendance-ajax/', views.update_attendance_ajax, name='update_attendance_ajax'),
]