import json, holidays
from datetime import date
from django.shortcuts import render, redirect
from django.contrib import messages
from django.db.models import Q
from .models import Employee, Attendance
from .forms import EmployeeForm, AttendanceForm


# Helper συνάρτηση για τις αργίες
def get_greek_holidays():
    gr_holidays = holidays.Greece(years=date.today().year)
    events = [{
        'title': f"🎉 {name}",
        'start': d.strftime('%Y-%m-%d'),
        'color': '#ffc107', 'textColor': '#000', 'allDay': True
    } for d, name in gr_holidays.items()]
    return gr_holidays, events


def manage_employees(request):
    if request.method == 'POST':
        form = EmployeeForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "✅ Ο υπάλληλος προστέθηκε!")
            return redirect('manage_employees')
        messages.error(request, "❌ Σφάλμα στην εγγραφή.")

    form = EmployeeForm()
    # Χρήση prefetch_related για να μην "χτυπάμε" τη βάση σε κάθε loop
    employees_qs = Employee.objects.prefetch_related('attendance_set').all()
    gr_holidays, holiday_events = get_greek_holidays()

    data = []
    # Mapping χρωμάτων για καθαρότερο κώδικα
    colors = {'OFFICE': '#e30613', 'REMOTE': '#0ea5e9', 'LEAVE': '#10b981', 'SICK': '#f59e0b'}

    for emp in employees_qs:
        report = emp.get_monthly_report()
        # Δημιουργία events λίστας με list comprehension
        events_list = [{
            'title': a.get_work_type_display(),
            'start': a.date.strftime('%Y-%m-%d'),
            'color': colors.get(a.work_type, '#6c757d')
        } for a in emp.attendance_set.all()]

        data.append({
            'id': emp.id, 'name': emp.full_name, 'email': emp.email,
            'office': report['office_days'], 'total': report['total_days'],
            'is_ok': report['is_ok'], 'debt': report['debt'],
            'events_json': json.dumps(events_list)
        })

    # Stats Today
    today = date.today()
    today_atts = Attendance.objects.filter(date=today)
    stats_today = {
        'office': today_atts.filter(work_type='OFFICE').count(),
        'remote': today_atts.filter(work_type='REMOTE').count(),
        'leave': today_atts.filter(work_type__in=['LEAVE', 'SICK']).count(),
        'total_emps': employees_qs.count()
    }

    return render(request, 'employees/manage.html', {
        'form': form, 'employees': data, 'stats_today': stats_today,
        'holidays_js': json.dumps([d.strftime('%Y-%m-%d') for d in gr_holidays.keys()]),
        'holidays_events_json': json.dumps(holiday_events),
    })


def log_attendance(request):
    if request.method == 'POST':
        form = AttendanceForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "✅ Η καταχώρηση ολοκληρώθηκε!")
            return redirect('log_attendance')
        messages.error(request, "❌ Σφάλμα: Διπλή καταχώρηση για την ίδια μέρα.")

    form = AttendanceForm()
    gr_holidays, _ = get_greek_holidays()

    return render(request, 'employees/log_attendance.html', {
        'form': form,
        'holidays_js': json.dumps([d.strftime('%Y-%m-%d') for d in gr_holidays.keys()])
    })