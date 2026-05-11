import json
import holidays
from datetime import date
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill

from .models import Employee, Attendance
from .forms import EmployeeForm

# 1. Βοηθητική συνάρτηση για τις Αργίες (Πρέπει να είναι στην αρχή)
def get_greek_holidays():
    """Επιστρέφει τις ελληνικές αργίες για το τρέχον έτος."""
    gr_holidays = holidays.Greece(years=date.today().year)
    events = [{
        'title': f"🎉 {name}",
        'start': d.strftime('%Y-%m-%d'),
        'color': '#ffc107',
        'textColor': '#000',
        'allDay': True
    } for d, name in gr_holidays.items()]
    return gr_holidays, events


# 2. Η Κεντρική View του Dashboard
def manage_employees(request):
    # --- Χειρισμός Φόρμας Προσθήκης Νέου Υπαλλήλου ---
    if request.method == 'POST':
        form = EmployeeForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "✅ Ο υπάλληλος προστέθηκε!")
            return redirect('manage_employees')
        messages.error(request, "❌ Σφάλμα στην εγγραφή. Ελέγξτε τα στοιχεία.")

    form = EmployeeForm()
    today = date.today()

    # Φέρνουμε τους υπαλλήλους και τις παρουσίες τους με 1 query (prefetch_related)
    employees_qs = Employee.objects.prefetch_related('attendance_set').all()
    gr_holidays, holiday_events = get_greek_holidays()

    data = []
    # Χρώματα για το ημερολόγιο (Frontend)
    colors = {
        'OFFICE': '#10b981',
        'REMOTE': '#0ea5e9',
        'LEAVE': '#f59e0b',
        'SICK': '#F59eOb'
    }

    for emp in employees_qs:
        report = emp.get_monthly_report()

        # --- Quick Status Logic (Για το Dot Παρουσίας) ---
        today_att = emp.attendance_set.filter(date=today).first()
        today_status = today_att.work_type if today_att else 'NONE'

        # Προετοιμασία λίστας γεγονότων για το FullCalendar
        events_list = [{
            'title': a.get_work_type_display(),
            'start': a.date.strftime('%Y-%m-%d'),
            'color': colors.get(a.work_type, '#6c757d')
        } for a in emp.attendance_set.all()]

        # --- Progress Bar Calculation (Στόχος 8 ημέρες) ---
        progress_percent = min(100, int((report['office_days'] / 8) * 100))

        data.append({
            'id': emp.id,
            'name': emp.full_name,
            'email': emp.email,
            'date_joined': emp.date_joined.strftime('%d/%m/%Y'),
            'office': report['office_days'],
            'total': report['total_days'],
            'is_ok': report['is_ok'],
            'debt': report['debt'],
            'today_status': today_status,   # Για το Dot
            'progress': progress_percent,   # Για την Μπάρα Προόδου
            'monthly_remaining': report['monthly_remaining'],
            'events_json': json.dumps(events_list)
        })

    # --- Υπολογισμός Γενικών Στατιστικών Dashboard ---
    current_month_atts = Attendance.objects.filter(
        date__year=today.year,
        date__month=today.month
    ).select_related('employee')

    # Στατιστικά Σήμερα
    today_atts = current_month_atts.filter(date=today)
    names_today_office = [a.employee.full_name for a in today_atts.filter(work_type='OFFICE')]
    names_today_remote = [a.employee.full_name for a in today_atts.filter(work_type='REMOTE')]
    names_today_leave = [a.employee.full_name for a in today_atts.filter(work_type__in=['LEAVE', 'SICK'])]

    # Στατιστικά Μήνα (Unique ονόματα για το hover tooltips)
    names_month_office = sorted(list(set([a.employee.full_name for a in current_month_atts.filter(work_type='OFFICE')])))
    names_month_remote = sorted(list(set([a.employee.full_name for a in current_month_atts.filter(work_type='REMOTE')])))
    names_month_leave = sorted(list(set([a.employee.full_name for a in current_month_atts.filter(work_type__in=['LEAVE', 'SICK'])])))

    stats_summary = {
        'today': {
            'office': len(names_today_office),
            'remote': len(names_today_remote),
            'leave': len(names_today_leave),
            'names_office': ", ".join(names_today_office) or "Κανένας",
            'names_remote': ", ".join(names_today_remote) or "Κανένας",
            'names_leave': ", ".join(names_today_leave) or "Κανένας",
        },
        'month': {
            'office': current_month_atts.filter(work_type='OFFICE').count(),
            'remote': current_month_atts.filter(work_type='REMOTE').count(),
            'leave': current_month_atts.filter(work_type__in=['LEAVE', 'SICK']).count(),
            'names_office': ", ".join(names_month_office) or "Κανένας",
            'names_remote': ", ".join(names_month_remote) or "Κανένας",
            'names_leave': ", ".join(names_month_leave) or "Κανένας",
        },
        'total_emps': employees_qs.count()
    }

    return render(request, 'employees/manage.html', {
        'form': form,
        'employees': data,
        'stats': stats_summary,
        'holidays_js': json.dumps([d.strftime('%Y-%m-%d') for d in gr_holidays.keys()]),
        'holidays_events_json': json.dumps(holiday_events),
    })


# 3. Διαγραφή Υπαλλήλου
@require_POST
def delete_employee(request, employee_id):
    emp = get_object_or_404(Employee, id=employee_id)
    name = emp.full_name
    emp.delete()
    messages.success(request, f"✅ Ο/Η {name} διαγράφηκε επιτυχώς.")
    return redirect('manage_employees')


# 4. Ενημέρωση Παρουσίας μέσω AJAX (Ημερολόγιο)
@csrf_exempt
def update_attendance_ajax(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            emp_id = data.get('emp_id')
            new_type = data.get('work_type')
            date_str = data.get('date')

            selected_date = date.fromisoformat(date_str)

            # Έλεγχος για Σαββατοκύριακο
            if selected_date.weekday() in [5, 6]:
                return JsonResponse({'status': 'error', 'message': 'Δεν επιτρέπονται καταχωρήσεις Σαββατοκύριακα!'}, status=400)

            # Έλεγχος για Αργίες
            gr_holidays = holidays.Greece(years=selected_date.year)
            if selected_date in gr_holidays:
                return JsonResponse({'status': 'error', 'message': f'Η ημέρα είναι αργία: {gr_holidays.get(selected_date)}'}, status=400)

            attendance, created = Attendance.objects.update_or_create(
                employee_id=emp_id,
                date=selected_date,
                defaults={'work_type': new_type}
            )
            return JsonResponse({'status': 'success', 'action': 'created' if created else 'updated'})

        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

    return JsonResponse({'status': 'error', 'message': 'Invalid method'}, status=400)


# 5. Στατιστικά για συγκεκριμένο εύρος ημερομηνιών
def employee_range_stats(request, employee_id):
    start_date = request.GET.get('start')
    end_date = request.GET.get('end')

    if not start_date or not end_date:
        return JsonResponse({'error': 'Απαιτείται ημερομηνία έναρξης και λήξης'}, status=400)

    employee = get_object_or_404(Employee, id=employee_id)
    stats = employee.get_stats_for_range(start_date, end_date)
    return JsonResponse(stats)


# 6. Εξαγωγή σε Excel
def export_attendance_excel(request):
    wb = Workbook()
    ws = wb.active
    ws.title = "Μηνιαία Αναφορά Παρουσίας"

    headers = ['Ονοματεπώνυμο', 'Email', 'Γραφείο', 'Τηλεργασία', 'Άδειες/Ασθ.', 'Χρέος (Ημέρες)']
    ws.append(headers)

    header_fill = PatternFill(start_color="991B1B", end_color="991B1B", fill_type="solid")
    for cell in ws[1]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.alignment = Alignment(horizontal="center")
        cell.fill = header_fill

    employees = Employee.objects.all()
    for emp in employees:
        report = emp.get_monthly_report()
        ws.append([
            emp.full_name,
            emp.email,
            report['office_days'],
            report['remote_days'],
            report['leave_days'],
            report['debt']
        ])

    for col in ws.columns:
        max_length = 0
        column = col[0].column_letter
        for cell in col:
            if cell.value:
                max_length = max(max_length, len(str(cell.value)))
        ws.column_dimensions[column].width = max_length + 2

    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )
    response['Content-Disposition'] = 'attachment; filename="Attendance_Report.xlsx"'
    wb.save(response)
    return response