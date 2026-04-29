import json  # Χρειάζεται για να περάσουμε τα δεδομένα στην JavaScript
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .models import Employee, Attendance
from .forms import EmployeeForm, AttendanceForm


def manage_employees(request):
    if request.method == 'POST':
        form = EmployeeForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "✅ Ο υπάλληλος προστέθηκε!")
            # Σιγουρέψου ότι το 'manage_employees' είναι το σωστό name στο urls.py
            return redirect('manage_employees')
        else:
            messages.error(request, "❌ Έλεγξε τα στοιχεία.")
    else:
        form = EmployeeForm()

    employees = Employee.objects.all()
    data = []

    for emp in employees:
        report = emp.get_monthly_report()

        attendances = Attendance.objects.filter(employee=emp)
        events_list = [
            {
                'title': 'Γραφείο' if a.work_type == 'OFFICE' else 'Τηλεργασία',
                'start': a.date.strftime('%Y-%m-%d'),
                'color': '#10b981' if a.work_type == 'OFFICE' else '#0ea5e9',
            }
            for a in attendances
        ]
        # -----------------------------------------------------------

        data.append({
            'id': emp.id,
            'name': emp.full_name,
            'email': emp.email,
            'office': report['office_days'],
            'remote': report['remote_days'],
            'total': report['total_days'],
            'is_ok': report['is_ok'],
            'debt': report['debt'],
            'events_json': json.dumps(events_list)
        })

    return render(request, 'employees/manage.html', {
        'form': form,
        'employees': data,
    })


def log_attendance(request):
    """Καταχώρηση παρουσίας"""
    if request.method == 'POST':
        form = AttendanceForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "✅ Η παρουσία καταχωρήθηκε!")
            return redirect('log_attendance')
        else:
            messages.error(request, "❌ Πιθανόν να υπάρχει ήδη καταχώρηση για αυτή την ημέρα.")
    else:
        form = AttendanceForm()

    return render(request, 'employees/log_attendance.html', {'form': form})