import json
import holidays
from datetime import date
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .models import Employee, Attendance
from .forms import EmployeeForm, AttendanceForm


def manage_employees(request):
    """Διαχείριση υπαλλήλων, λίστα και στατιστικά με υποστήριξη αργιών, αδειών και ασθενειών"""
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

    # 1. Δημιουργία λίστας αργιών ως events για το ημερολόγιο (Κίτρινο χρώμα)
    gr_holidays = holidays.Greece(years=date.today().year)
    holiday_events = [
        {
            'title': f"🎉 {name}",
            'start': d.strftime('%Y-%m-%d'),
            'color': '#ffc107',  # PCS Yellow/Gold
            'textColor': '#000',
            'allDay': True
        }
        for d, name in gr_holidays.items()
    ]

    for emp in employees:
        # Το report στο models.py τώρα υπολογίζει (office_days + leave_days) για το debt
        report = emp.get_monthly_report()

        # Προετοιμασία των παρουσιών του υπαλλήλου με χρωματική κωδικοποίηση
        attendances = Attendance.objects.filter(employee=emp)
        events_list = []

        for a in attendances:
            # Καθορισμός χρώματος βάσει του work_type
            event_color = '#e30613'  # Default: PCS Red (Office)
            if a.work_type == 'REMOTE':
                event_color = '#0ea5e9'  # Blue
            elif a.work_type == 'LEAVE':
                event_color = '#10b981'  # Green
            elif a.work_type == 'SICK':
                event_color = '#f59e0b'  # Orange

            events_list.append({
                'title': a.get_work_type_display(),
                'start': a.date.strftime('%Y-%m-%d'),
                'color': event_color,
            })

        data.append({
            'id': emp.id,
            'name': emp.full_name,
            'email': emp.email,
            'office': report['office_days'],
            'remote': report['remote_days'],
            'leave': report['leave_days'],  # Προσθήκη στην αναφορά
            'total': report['total_days'],
            'is_ok': report['is_ok'],
            'debt': report['debt'],
            'events_json': json.dumps(events_list)
        })

    # Λίστα αργιών για το validation της JS στη φόρμα εγγραφής (αν χρειαστεί)
    holidays_list = [d.strftime('%Y-%m-%d') for d in gr_holidays.keys()]

    return render(request, 'employees/manage.html', {
        'form': form,
        'employees': data,
        'holidays_js': json.dumps(holidays_list),
        'holidays_events_json': json.dumps(holiday_events),
    })


def log_attendance(request):
    """Καταχώρηση παρουσίας με επιλογές για Γραφείο, Τηλεργασία, Άδεια, Ασθένεια"""
    if request.method == 'POST':
        form = AttendanceForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "✅ Η καταχώρηση ολοκληρώθηκε!")
            return redirect('log_attendance')
        else:
            messages.error(request, "❌ Πιθανόν να υπάρχει ήδη καταχώρηση για αυτή την ημέρα.")
    else:
        form = AttendanceForm()

    # Αργίες για το "κλείδωμα" ημερομηνιών στη JS
    gr_holidays = holidays.Greece(years=date.today().year)
    holidays_list = [d.strftime('%Y-%m-%d') for d in gr_holidays.keys()]

    return render(request, 'employees/log_attendance.html', {
        'form': form,
        'holidays_js': json.dumps(holidays_list)
    })