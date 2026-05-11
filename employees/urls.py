from django.urls import path
from . import views

urlpatterns = [
    path('', views.manage_employees, name='manage_employees'),
    path('delete-employee/<int:employee_id>/', views.delete_employee, name='delete_employee'),
    path('update-attendance-ajax/', views.update_attendance_ajax, name='update_attendance_ajax'),
    path('employee-stats/<int:employee_id>/', views.employee_range_stats, name='employee_range_stats'),
    path('export-excel/', views.export_attendance_excel, name='export_attendance_excel'),
]