import json
import holidays
from datetime import date
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .models import Employee, Attendance
from .forms import EmployeeForm, AttendanceForm

def manage_employees(request):
    """Διαχείριση υπαλλήλων, λίστα και στατιστικά με υποστήριξη αργιών στο ημερολόγιο"""
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

    # 1. Δημιουργία λίστας αργιών ως events για το ημερολόγιο
    gr_holidays = holidays.Greece(years=date.today().year)
    holiday_events = [
        {
            'title': f"🎉 {name}",
            'start': d.strftime('%Y-%m-%d'),
            'color': '#ffc107',  # PCS Yellow/Gold για τις αργίες
            'textColor': '#000',
            'allDay': True
        }
        for d, name in gr_holidays.items()
    ]

    for emp in employees:
        report = emp.get_monthly_report()

        # Προετοιμασία των παρουσιών του υπαλλήλου
        attendances = Attendance.objects.filter(employee=emp)
        events_list = [
            {
                'title': 'Γραφείο' if a.work_type == 'OFFICE' else 'Τηλεργασία',
                'start': a.date.strftime('%Y-%m-%d'),
                'color': '#e30613' if a.work_type == 'OFFICE' else '#0ea5e9',
            }
            for a in attendances
        ]

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

    # Λίστα αργιών (μόνο ημερομηνίες) για το validation της JS
    holidays_list = [d.strftime('%Y-%m-%d') for d in gr_holidays.keys()]

    return render(request, 'employees/manage.html', {
        'form': form,
        'employees': data,
        'holidays_js': json.dumps(holidays_list),
        'holidays_events_json': json.dumps(holiday_events), # Τα events των αργιών
    })


def log_attendance(request):
    """Καταχώρηση παρουσίας με έλεγχο αργιών"""
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

    gr_holidays = holidays.Greece(years=date.today().year)
    holidays_list = [d.strftime('%Y-%m-%d') for d in gr_holidays.keys()]

    return render(request, 'employees/log_attendance.html', {
        'form': form,
        'holidays_js': json.dumps(holidays_list)
    })