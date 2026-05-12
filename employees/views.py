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

# ReportLab για PDF export
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.enums import TA_CENTER, TA_LEFT

from .models import Employee, Attendance
from .forms import EmployeeForm

# 1. Βοηθητική συνάρτηση για τις Αργίες
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

    # Φέρνουμε τους υπαλλήλους και τις παρουσίες τους
    employees_qs = Employee.objects.prefetch_related('attendance_set').all()
    gr_holidays, holiday_events = get_greek_holidays()

    data = []
    # Ενιαία χρώματα για το ημερολόγιο
    colors = {
        'OFFICE': '#10b981',
        'REMOTE': '#0ea5e9',
        'LEAVE': '#f59e0b',
        'SICK': '#f59e0b'
    }

    total_debt_accumulator = 0

    for emp in employees_qs:
        report = emp.get_monthly_report()
        total_debt_accumulator += report['debt']

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
            'today_status': today_status,
            'progress': progress_percent,
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

    # Στατιστικά Μήνα
    names_month_office = sorted(list(set([a.employee.full_name for a in current_month_atts.filter(work_type='OFFICE')])))
    names_month_remote = sorted(list(set([a.employee.full_name for a in current_month_atts.filter(work_type='REMOTE')])))
    names_month_leave = sorted(list(set([a.employee.full_name for a in current_month_atts.filter(work_type__in=['LEAVE', 'SICK'])])))

    # Υπολογισμός Presence Rate (%)
    total_emp_count = len(data)
    presence_rate = (len(names_today_office) / total_emp_count * 100) if total_emp_count > 0 else 0

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
        'total_count': total_emp_count,
        'total_debt_sum': total_debt_accumulator,
        'presence_rate': round(presence_rate, 1)
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

            # Διαγραφή αν επιλεγεί DELETE, αλλιώς update_or_create
            if new_type == 'DELETE':
                Attendance.objects.filter(employee_id=emp_id, date=selected_date).delete()
                return JsonResponse({'status': 'success', 'action': 'deleted'})
            else:
                attendance, created = Attendance.objects.update_or_create(
                    employee_id=emp_id,
                    date=selected_date,
                    defaults={'work_type': new_type}
                )
                return JsonResponse({'status': 'success', 'action': 'created' if created else 'updated'})

        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

    return JsonResponse({'status': 'error', 'message': 'Invalid method'}, status=400)


# 5. Στατιστικά για εύρος ημερομηνιών
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


# 7. Εξαγωγή σε PDF
def export_attendance_pdf(request):
    today = date.today()
    month_name = today.strftime('%B %Y')

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=1.5*cm, leftMargin=1.5*cm,
        topMargin=2*cm, bottomMargin=2*cm,
        title=f"Αναφορά Παρουσιών {month_name}",
    )

    # ── Styles ───────────────────────────────────────────────────────────────
    brand_red  = colors.HexColor('#991B1B')
    light_red  = colors.HexColor('#FEE2E2')
    green      = colors.HexColor('#065F46')
    green_bg   = colors.HexColor('#D1FAE5')
    red_txt    = colors.HexColor('#991B1B')
    muted      = colors.HexColor('#64748B')
    border_c   = colors.HexColor('#E2E8F0')
    row_alt    = colors.HexColor('#F8FAFC')

    title_style = ParagraphStyle('Title', fontName='Helvetica-Bold', fontSize=20,
                                 textColor=brand_red, alignment=TA_LEFT, spaceAfter=4)
    sub_style   = ParagraphStyle('Sub', fontName='Helvetica', fontSize=10,
                                 textColor=muted, alignment=TA_LEFT, spaceAfter=2)
    ok_style    = ParagraphStyle('OK', fontName='Helvetica-Bold', fontSize=9,
                                 textColor=green, alignment=TA_CENTER)
    debt_style  = ParagraphStyle('Debt', fontName='Helvetica-Bold', fontSize=9,
                                 textColor=red_txt, alignment=TA_CENTER)
    cell_style  = ParagraphStyle('Cell', fontName='Helvetica', fontSize=9,
                                 textColor=colors.HexColor('#1E293B'), alignment=TA_CENTER)

    story = []

    # ── Header ───────────────────────────────────────────────────────────────
    story.append(Paragraph("PCS Attendance Management", title_style))
    story.append(Paragraph(f"Μηνιαία Αναφορά Παρουσιών — {month_name}", sub_style))
    story.append(Paragraph(f"Εκτυπώθηκε: {today.strftime('%d/%m/%Y')}", sub_style))
    story.append(Spacer(1, 0.5*cm))

    # ── Summary row ──────────────────────────────────────────────────────────
    employees = Employee.objects.all()
    total_debt = sum(emp.get_cumulative_debt() for emp in employees)
    emp_count  = employees.count()
    ok_count   = sum(1 for emp in employees if emp.get_cumulative_debt() == 0)

    summary_data = [
        ['Σύνολο Υπαλλήλων', 'Εντάξει', 'Με Χρέος', 'Συνολικό Χρέος'],
        [str(emp_count), str(ok_count), str(emp_count - ok_count), f"{total_debt} ημ."],
    ]
    summary_table = Table(summary_data, colWidths=[4*cm, 4*cm, 4*cm, 4*cm])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND',   (0,0), (-1,0), brand_red),
        ('TEXTCOLOR',    (0,0), (-1,0), colors.white),
        ('FONTNAME',     (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE',     (0,0), (-1,-1), 9),
        ('ALIGN',        (0,0), (-1,-1), 'CENTER'),
        ('VALIGN',       (0,0), (-1,-1), 'MIDDLE'),
        ('ROWBACKGROUNDS',(0,1), (-1,-1), [colors.white]),
        ('GRID',         (0,0), (-1,-1), 0.5, border_c),
        ('TOPPADDING',   (0,0), (-1,-1), 6),
        ('BOTTOMPADDING',(0,0), (-1,-1), 6),
        ('ROUNDEDCORNERS', [4]),
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 0.6*cm))

    # ── Main Table ───────────────────────────────────────────────────────────
    col_widths = [5.5*cm, 3*cm, 3*cm, 2.5*cm, 3*cm]
    headers = ['Ονοματεπώνυμο', 'Γραφείο', 'Τηλεργασία', 'Άδειες/Ασθ.', 'Κατάσταση']
    table_data = [headers]

    for emp in employees:
        report = emp.get_monthly_report()
        if report['is_ok']:
            status = Paragraph('ΕΝΤΆΞΕΙ', ok_style)
        else:
            status = Paragraph(f"ΧΡΕΟΣ -{report['debt']}", debt_style)

        table_data.append([
            Paragraph(emp.full_name, cell_style),
            Paragraph(str(report['office_days']), cell_style),
            Paragraph(str(report['remote_days']), cell_style),
            Paragraph(str(report['leave_days']), cell_style),
            status,
        ])

    main_table = Table(table_data, colWidths=col_widths, repeatRows=1)

    row_styles = []
    for i in range(1, len(table_data)):
        bg = row_alt if i % 2 == 0 else colors.white
        row_styles.append(('BACKGROUND', (0,i), (-1,i), bg))
        # Χρωματισμός κελιού κατάστασης
        emp_report = employees[i-1].get_monthly_report()
        if emp_report['is_ok']:
            row_styles.append(('BACKGROUND', (4,i), (4,i), green_bg))
        else:
            row_styles.append(('BACKGROUND', (4,i), (4,i), light_red))

    main_table.setStyle(TableStyle([
        # Header
        ('BACKGROUND',    (0,0), (-1,0), brand_red),
        ('TEXTCOLOR',     (0,0), (-1,0), colors.white),
        ('FONTNAME',      (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE',      (0,0), (-1,-1), 9),
        ('ALIGN',         (0,0), (-1,-1), 'CENTER'),
        ('VALIGN',        (0,0), (-1,-1), 'MIDDLE'),
        ('GRID',          (0,0), (-1,-1), 0.5, border_c),
        ('TOPPADDING',    (0,0), (-1,-1), 7),
        ('BOTTOMPADDING', (0,0), (-1,-1), 7),
        ('LEFTPADDING',   (0,0), (-1,-1), 6),
        ('RIGHTPADDING',  (0,0), (-1,-1), 6),
        *row_styles,
    ]))
    story.append(main_table)

    # ── Footer note ──────────────────────────────────────────────────────────
    story.append(Spacer(1, 0.5*cm))
    story.append(Paragraph(
        f"* Αναφορά για τον τρέχοντα μήνα ({month_name}). Απαίτηση: 8 ημέρες γραφείου/μήνα.",
        ParagraphStyle('Note', fontName='Helvetica', fontSize=7, textColor=muted)
    ))

    doc.build(story)
    buffer.seek(0)

    filename = f"Attendance_{today.strftime('%Y_%m')}.pdf"
    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


@csrf_exempt
def bulk_update_attendance(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            employee_ids = data.get('employee_ids', [])
            work_type = data.get('work_type')
            selected_date = date.today()

            if not employee_ids or not work_type:
                return JsonResponse({'status': 'error', 'message': 'Λείπουν δεδομένα'}, status=400)

            # Μαζική ενημέρωση/δημιουργία
            for emp_id in employee_ids:
                Attendance.objects.update_or_create(
                    employee_id=emp_id,
                    date=selected_date,
                    defaults={'work_type': work_type}
                )

            return JsonResponse({'status': 'success', 'count': len(employee_ids)})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    return JsonResponse({'status': 'error'}, status=400)