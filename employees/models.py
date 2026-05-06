from django.db import models
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
import calendar
import holidays


def _count_required_office_days(year, month, from_day, to_day, gr_holidays):

    weeks = 0
    holidays_on_weekdays = 0
    curr = from_day

    while curr <= to_day:
        if curr.weekday() < 5:  # Καθημερινή
            # Νέα εβδομάδα: κάθε Δευτέρα ή η πρώτη μέρα μέτρησης
            if curr.weekday() == 0 or curr == from_day:
                weeks += 1
        curr += timedelta(days=1)

    required = (weeks * 2)
    return max(0, min(8, required))


class Employee(models.Model):
    full_name = models.CharField(max_length=200, verbose_name="Ονοματεπώνυμο")
    email = models.EmailField(unique=True, verbose_name="Email")
    date_joined = models.DateField(
        verbose_name="Ημερομηνία εγγραφής",
        default=date.today
    )

    def __str__(self):
        return self.full_name

    def get_cumulative_debt(self):
        """
        Υπολογίζει το συνολικό χρέος από τον μήνα εγγραφής μέχρι σήμερα.
        Αν ένας μήνας κλείσει με χρέος, αυτό μεταφέρεται στον επόμενο.
        """
        today = date.today()
        join = self.date_joined

        # Ξεκινάμε από τον μήνα εγγραφής
        cursor = join.replace(day=1)
        current_month_start = today.replace(day=1)

        all_attendances = self.attendance_set.all()
        att_by_date = {a.date: a.work_type for a in all_attendances}

        carried_debt = 0  # Χρέος που μεταφέρεται από προηγούμενους μήνες

        while cursor <= current_month_start:
            year = cursor.year
            month = cursor.month
            gr_holidays = holidays.Greece(years=year)

            last_day_of_month = date(year, month, calendar.monthrange(year, month)[1])

            # Η πρώτη μέρα μέτρησης: αν είναι ο μήνας εγγραφής, ξεκινάμε από την ημερομηνία εγγραφής
            if cursor.year == join.year and cursor.month == join.month:
                from_day = join
            else:
                from_day = cursor

            # Η τελευταία μέρα μέτρησης: αν είναι ο τρέχων μήνας, μέχρι σήμερα
            if cursor.year == today.year and cursor.month == today.month:
                to_day = today
            else:
                to_day = last_day_of_month

            required = _count_required_office_days(year, month, from_day, to_day, gr_holidays)

            # Προσθέτουμε το μεταφερόμενο χρέος στις απαιτήσεις αυτού του μήνα
            total_required = required + carried_debt

            # Ημέρες γραφείου αυτού του μήνα
            office_days = sum(
                1 for d, wt in att_by_date.items()
                if wt == 'OFFICE' and d.year == year and d.month == month
            )

            # Χρέος αυτού του μήνα (αν ο μήνας δεν έχει τελειώσει, δεν μεταφέρουμε ακόμα)
            month_debt = total_required - office_days
            if month_debt < 0:
                month_debt = 0

            # Αν ο μήνας έχει κλείσει, μεταφέρουμε το χρέος
            if to_day == last_day_of_month:
                carried_debt = month_debt
            else:
                # Τρέχων μήνας — το χρέος δεν μεταφέρεται ακόμα
                carried_debt = month_debt

            cursor = (cursor + relativedelta(months=1)).replace(day=1)

        return carried_debt

    def get_monthly_report(self):
        today = date.today()
        join = self.date_joined
        year = today.year
        month = today.month
        gr_holidays = holidays.Greece(years=year)

        last_day_of_month = date(year, month, calendar.monthrange(year, month)[1])

        # Από πότε μετράμε αυτόν τον μήνα
        if join.year == year and join.month == month:
            from_day = join
        else:
            from_day = today.replace(day=1)

        attendances = self.attendance_set.filter(date__month=month, date__year=year)
        office_days = attendances.filter(work_type='OFFICE').count()
        remote_days = attendances.filter(work_type='REMOTE').count()
        leave_days = attendances.filter(work_type__in=['LEAVE', 'SICK']).count()
        total_days = office_days + remote_days

        required_this_month = _count_required_office_days(year, month, from_day, today, gr_holidays)

        # Υπολογισμός συνολικού χρέους (με μεταφορές από προηγούμενους μήνες)
        debt = self.get_cumulative_debt()
        is_ok = (debt == 0)

        # Πόσες ημέρες λείπουν ακόμα για να φτάσει τις 8 του μήνα (ανεξάρτητα από carryover)
        monthly_remaining = max(0, 8 - office_days)

        return {
            'office_days': office_days,
            'remote_days': remote_days,
            'leave_days': leave_days,
            'total_days': total_days,
            'required_office': required_this_month,
            'debt': debt,
            'is_ok': is_ok,
            'monthly_remaining': monthly_remaining,
        }


class Attendance(models.Model):
    WORK_TYPE_CHOICES = [
        ('OFFICE', 'Στο Γραφείο'),
        ('REMOTE', 'Τηλεργασία'),
        ('LEAVE', 'Άδεια'),
        ('SICK', 'Ασθένεια'),
    ]

    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)
    date = models.DateField(verbose_name="Ημερομηνία")
    work_type = models.CharField(
        max_length=10,
        choices=WORK_TYPE_CHOICES,
        verbose_name="Τύπος Εργασίας"
    )

    class Meta:
        unique_together = ('employee', 'date')
        verbose_name = "Παρουσία"
        verbose_name_plural = "Παρουσίες"

    def __str__(self):
        return f"{self.employee.full_name} - {self.date} ({self.get_work_type_display()})"