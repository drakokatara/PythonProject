from django.db import models
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
import calendar
import holidays


def _count_required_office_days(from_day, to_day):
    """
    Υπολογίζει τις απαιτούμενες ημέρες γραφείου (2 ανά εβδομάδα) για ένα διάστημα.
    """
    weeks = 0
    curr = from_day
    while curr <= to_day:
        if curr.weekday() < 5:  # Δευτέρα έως Παρασκευή
            if curr.weekday() == 0 or curr == from_day:
                weeks += 1
        curr += timedelta(days=1)

    required = (weeks * 2)
    return max(0, min(8, required))  # Μέγιστο 8 ημέρες το μήνα


class Employee(models.Model):
    full_name = models.CharField(max_length=200, verbose_name="Ονοματεπώνυμο")
    email = models.EmailField(unique=True, verbose_name="Email")
    date_joined = models.DateField(
        verbose_name="Ημερομηνία εγγραφής στο σύστημα",
        default=date.today
    )
    initial_debt = models.IntegerField(
        default=0,
        verbose_name="Αρχικό Χρέος Ημερών"
    )

    def __str__(self):
        return self.full_name

    def get_cumulative_debt(self):
        """
        Υπολογίζει το χρέος ξεκινώντας ΜΟΝΟ από τον τρέχοντα μήνα.
        """
        today = date.today()
        current_month_start = today.replace(day=1)

        from_day = max(current_month_start, self.date_joined)
        to_day = today

        all_attendances = self.attendance_set.all()
        att_by_date = {a.date: a.work_type for a in all_attendances}

        carried_debt = self.initial_debt

        required = _count_required_office_days(from_day, to_day)
        total_required = required + carried_debt

        office_days = sum(
            1 for d, wt in att_by_date.items()
            if wt == 'OFFICE' and d.year == today.year and d.month == today.month
        )

        return max(0, total_required - office_days)

    def get_monthly_report(self):
        today = date.today()
        year = today.year
        month = today.month

        current_month_start = today.replace(day=1)
        from_day = max(current_month_start, self.date_joined)

        attendances = self.attendance_set.filter(date__month=month, date__year=year)
        office_days = attendances.filter(work_type='OFFICE').count()
        remote_days = attendances.filter(work_type='REMOTE').count()
        leave_days = attendances.filter(work_type__in=['LEAVE', 'SICK']).count()

        required_this_month = _count_required_office_days(from_day, today)
        debt = self.get_cumulative_debt()

        return {
            'office_days': office_days,
            'remote_days': remote_days,
            'leave_days': leave_days,
            'total_days': office_days + remote_days,
            'required_office': required_this_month,
            'debt': debt,
            'is_ok': (debt == 0),
            'monthly_remaining': max(0, 8 - office_days),
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