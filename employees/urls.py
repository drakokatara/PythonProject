from django.urls import path
from . import views

urlpatterns = [
    path('', views.manage_employees, name='manage_employees'),
    path('delete-employee/<int:employee_id>/', views.delete_employee, name='delete_employee'),
    path('update-attendance-ajax/', views.update_attendance_ajax, name='update_attendance_ajax'),
    path('export-excel/', views.export_attendance_excel, name='export_attendance_excel'),
    path('export-pdf/', views.export_attendance_pdf, name='export_attendance_pdf'),
    path('attendance-range-stats/', views.attendance_range_stats, name='attendance_range_stats'),
    path('bulk-update/', views.bulk_update_attendance, name='bulk_update')
]