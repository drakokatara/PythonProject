import json
import holidays
from datetime import date
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from .models import Employee, Attendance
from .forms import EmployeeForm, AttendanceForm

def get_greek_holidays():
    """Ανακτά τις ελληνικές αργίες για το τρέχον έτος."""
    gr_holidays = holidays.Greece(years=date.today().year)
    events = [{
        'title': f"🎉 {name}",
        'start': d.strftime('%Y-%m-%d'),
        'color': '#ffc107',
        'textColor': '#000',
        'allDay': True
    } for d, name in gr_holidays.items()]
    return gr_holidays, events

def manage_employees(request):
    """Dashboard διαχείρισης υπαλλήλων και στατιστικών."""
    if request.method == 'POST':
        form = EmployeeForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "✅ Ο υπάλληλος προστέθηκε!")
            return redirect('manage_employees')
        messages.error(request, "❌ Σφάλμα στην εγγραφή. Ελέγξτε τα στοιχεία.")

    form = EmployeeForm()
    # Χρήση prefetch_related για λιγότερα queries στη βάση δεδομένων
    employees_qs = Employee.objects.prefetch_related('attendance_set').all()
    gr_holidays, holiday_events = get_greek_holidays()

    data = []
    colors = {
        'OFFICE': '#e30613',
        'REMOTE': '#0ea5e9',
        'LEAVE': '#10b981',
        'SICK': '#f59e0b'
    }

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
        'form': form,
        'employees': data,
        'stats_today': stats_today,
        'holidays_js': json.dumps([d.strftime('%Y-%m-%d') for d in gr_holidays.keys()]),
        'holidays_events_json': json.dumps(holiday_events),
    })

@require_POST
def delete_employee(request, employee_id):
    """Διαγραφή υπαλλήλου."""
    emp = get_object_or_404(Employee, id=employee_id)
    name = emp.full_name
    emp.delete()
    messages.success(request, f"✅ Ο/Η {name} διαγράφηκε επιτυχώς.")
    return redirect('manage_employees')

@csrf_exempt
def update_attendance_ajax(request):
    """
    Κύρια συνάρτηση καταχώρησης/ενημέρωσης παρουσίας μέσω AJAX.
    Αν η ημερομηνία είναι κενή στο ημερολόγιο, δημιουργεί νέα εγγραφή (Log).
    Αν η ημερομηνία είναι ήδη συμπληρωμένη, την ενημερώνει (Edit/Αλλαγή).
    """
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            emp_id = data.get('emp_id')
            new_type = data.get('work_type')
            date_str = data.get('date')

            if not all([emp_id, new_type, date_str]):
                return JsonResponse({'status': 'error', 'message': 'Ελλιπή δεδομένα'}, status=400)

            # Η μέθοδος update_or_create κάνει αυτόματα τη διάκριση:
            # Αν δεν υπάρχει η εγγραφή (employee_id + date), τη φτιάχνει.
            # Αν υπάρχει, αλλάζει απλώς το work_type.
            attendance, created = Attendance.objects.update_or_create(
                employee_id=emp_id,
                date=date_str,
                defaults={'work_type': new_type}
            )

            return JsonResponse({
                'status': 'success',
                'action': 'created' if created else 'updated'
            })

        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

    return JsonResponse({'status': 'error', 'message': 'Μη αποδεκτή μέθοδος'}, status=400)

def employee_range_stats(request, employee_id):
    """Επιστρέφει στατιστικά παρουσιών για ένα συγκεκριμένο εύρος ημερομηνιών."""
    start_date = request.GET.get('start')
    end_date = request.GET.get('end')

    if not start_date or not end_date:
        return JsonResponse({'error': 'Απαιτείται ημερομηνία έναρξης και λήξης'}, status=400)

    employee = get_object_or_404(Employee, id=employee_id)
    stats = employee.get_stats_for_range(start_date, end_date)

    return JsonResponse(stats)