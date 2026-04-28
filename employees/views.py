from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .models import Employee, Attendance
from .forms import EmployeeForm, AttendanceForm


def manage_employees(request):
    """Προσθήκη υπαλλήλου + λίστα όλων"""
    if request.method == 'POST':
        form = EmployeeForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "✅ Ο υπάλληλος προστέθηκε!")
            return redirect('manage_employees')
        else:
            messages.error(request, "❌ Έλεγξε τα στοιχεία.")
    else:
        form = EmployeeForm()

    employees = Employee.objects.all()
    data = []
    for emp in employees:
        report = emp.get_monthly_report()
        data.append({
            'id':     emp.id,
            'name':   emp.full_name,
            'email':  emp.email,
            'office': report['office_days'],
            'remote': report['remote_days'],
            'total':  report['total_days'],
            'is_ok':  report['is_ok'],
        })

    return render(request, 'employees/manage.html', {
        'form':      form,
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


def employee_calendar(request, employee_id):
    """Ημερολόγιο παρουσιών ενός υπαλλήλου"""
    employee    = get_object_or_404(Employee, id=employee_id)
    attendances = Attendance.objects.filter(employee=employee)
    report      = employee.get_monthly_report()

    events = [
        {
            'title': 'Γραφείο' if a.work_type == 'OFFICE' else 'Τηλεργασία',
            'start': a.date.strftime('%Y-%m-%d'),
            'color': '#198754' if a.work_type == 'OFFICE' else '#0dcaf0',
        }
        for a in attendances
    ]

    return render(request, 'employees/calendar.html', {
        'employee': employee,
        'events':   events,
        'report':   report,
    })