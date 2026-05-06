import json, holidays
from datetime import date
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.views.decorators.http import require_POST
from .models import Employee, Attendance
from .forms import EmployeeForm, AttendanceForm
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt


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
    employees_qs = Employee.objects.prefetch_related('attendance_set').all()
    gr_holidays, holiday_events = get_greek_holidays()

    data = []
    colors = {'OFFICE': '#e30613', 'REMOTE': '#0ea5e9', 'LEAVE': '#10b981', 'SICK': '#f59e0b'}

    for emp in employees_qs:
        report = emp.get_monthly_report()
        events_list = [{
            'title': a.get_work_type_display(),
            'start': a.date.strftime('%Y-%m-%d'),
            'color': colors.get(a.work_type, '#6c757d')
        } for a in emp.attendance_set.all()]

        data.append({
            'id': emp.id,
            'name': emp.full_name,
            'email': emp.email,
            'date_joined': emp.date_joined.strftime('%d/%m/%Y'),
            'office': report['office_days'],
            'total': report['total_days'],
            'is_ok': report['is_ok'],
            'debt': report['debt'],
            'monthly_remaining': report['monthly_remaining'],
            'events_json': json.dumps(events_list)
        })

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


@require_POST
def delete_employee(request, employee_id):
    emp = get_object_or_404(Employee, id=employee_id)
    name = emp.full_name
    emp.delete()
    messages.success(request, f"✅ Ο/Η {name} διαγράφηκε.")
    return redirect('manage_employees')


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


def edit_attendance(request, att_id):
    attendance = get_object_or_404(Attendance, id=att_id)
    if request.method == 'POST':
        form = AttendanceForm(request.POST, instance=attendance)
        if form.is_valid():
            form.save()
            messages.success(request, "✅ Η καταχώρηση ενημερώθηκε επιτυχώς!")
            return redirect('manage_employees')
    else:
        form = AttendanceForm(instance=attendance)

    return render(request, 'employees/log_attendance.html', {
        'form': form,
        'edit_mode': True,
        'attendance': attendance
    })


@csrf_exempt
def update_attendance_ajax(request):
    if request.method == 'POST':
        import json
        data = json.loads(request.body)
        emp_id = data.get('emp_id')
        new_type = data.get('work_type')  # 'OFFICE' ή 'REMOTE'
        date_str = data.get('date')

        # Βρίσκουμε την εγγραφή και την ενημερώνουμε
        attendance = Attendance.objects.filter(employee_id=emp_id, date=date_str).first()
        if attendance:
            attendance.work_type = new_type
            attendance.save()
            return JsonResponse({'status': 'success'})
    return JsonResponse({'status': 'error'}, status=400)