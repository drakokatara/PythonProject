import json
import holidays
from datetime import date
from django.shortcuts import render, redirect
from django.contrib import messages
from .models import Employee, Attendance
from .forms import EmployeeForm, AttendanceForm

def manage_employees(request):
    if request.method == 'POST':
        form = EmployeeForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "✅ Ο υπάλληλος προστέθηκε επιτυχώς!")
            return redirect('manage_employees')
        else:
            messages.error(request, "❌ Σφάλμα κατά την εγγραφή. Ελέγξτε τα στοιχεία.")
    else:
        form = EmployeeForm()

    employees = Employee.objects.all()
    data = []

    # 1. Δημιουργία αργιών ως events για το ημερολόγιο (Yellow/Gold)
    gr_holidays = holidays.Greece(years=date.today().year)
    holiday_events = [
        {
            'title': f"🎉 {name}",
            'start': d.strftime('%Y-%m-%d'),
            'color': '#ffc107',
            'textColor': '#000',
            'allDay': True
        }
        for d, name in gr_holidays.items()
    ]

    for emp in employees:
        # Το report στο models.py υπολογίζει το debt (Office + Leave)
        report = emp.get_monthly_report()

        # Προετοιμασία των παρουσιών του υπαλλήλου με χρώματα
        attendances = Attendance.objects.filter(employee=emp)
        events_list = []

        for a in attendances:
            # Χρώμα βάσει τύπου εργασίας/απουσίας
            if a.work_type == 'OFFICE':
                event_color = '#e30613'  # PCS Red
            elif a.work_type == 'REMOTE':
                event_color = '#0ea5e9'  # Blue
            elif a.work_type == 'LEAVE':
                event_color = '#10b981'  # Green
            elif a.work_type == 'SICK':
                event_color = '#f59e0b'  # Orange
            else:
                event_color = '#6c757d'  # Gray (fallback)

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
            'leave': report['leave_days'],
            'total': report['total_days'],
            'is_ok': report['is_ok'],
            'debt': report['debt'],
            'events_json': json.dumps(events_list)
        })

    # 2. Υπολογισμός στατιστικών για το "Μικρό Παράθυρο" (ΣΗΜΕΡΑ)
    today_date = date.today()
    today_attendances = Attendance.objects.filter(date=today_date)

    stats_today = {
        'office': today_attendances.filter(work_type='OFFICE').count(),
        'remote': today_attendances.filter(work_type='REMOTE').count(),
        'leave':  today_attendances.filter(work_type__in=['LEAVE', 'SICK']).count(),
        'total_emps': employees.count()
    }

    # Λίστα αργιών (μόνο ημερομηνίες) για validation στην JS
    holidays_list = [d.strftime('%Y-%m-%d') for d in gr_holidays.keys()]

    return render(request, 'employees/manage.html', {
        'form': form,
        'employees': data,
        'stats_today': stats_today,
        'holidays_js': json.dumps(holidays_list),
        'holidays_events_json': json.dumps(holiday_events),
    })


def log_attendance(request):
    if request.method == 'POST':
        form = AttendanceForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "✅ Η καταχώρηση ολοκληρώθηκε!")
            return redirect('log_attendance')
        else:
            messages.error(request, "❌ Σφάλμα: Πιθανόν να υπάρχει ήδη καταχώρηση για αυτή την ημέρα.")
    else:
        form = AttendanceForm()

    # Λήψη αργιών για το "κλείδωμα" ημερομηνιών στη φόρμα
    gr_holidays = holidays.Greece(years=date.today().year)
    holidays_list = [d.strftime('%Y-%m-%d') for d in gr_holidays.keys()]

    return render(request, 'employees/log_attendance.html', {
        'form': form,
        'holidays_js': json.dumps(holidays_list)
    })