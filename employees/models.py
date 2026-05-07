from django.db import models
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
import calendar
import holidays

def _count_required_office_days(from_day, to_day):
    """
    Υπολογίζει τις απαιτούμενες ημέρες γραφείου (2 ανά εβδομάδα).
    """
    weeks = 0
    curr = from_day

    while curr <= to_day:
        # 0 = Δευτέρα
        if curr.weekday() < 5:
            # Αν είναι Δευτέρα ή η πρώτη μέρα της περιόδου, μετράμε νέα εβδομάδα
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
    # Νέο πεδίο για το αρχικό χρέος που προσθέσαμε
    initial_debt = models.IntegerField(default=0, verbose_name="Αρχικό Χρέος Ημερών")

    def __str__(self):
        return self.full_name

    def get_cumulative_debt(self):
        """
        Υπολογίζει το σωρευτικό χρέος ξεκινώντας από το initial_debt.
        """
        today = date.today()
        join = self.date_joined

        # Ξεκινάμε από την αρχή του μήνα εγγραφής
        cursor = join.replace(day=1)
        current_month_start = today.replace(day=1)

        all_attendances = self.attendance_set.all()
        att_by_date = {a.date: a.work_type for a in all_attendances}

        # Ξεκινάμε με το αρχικό χρέος που ορίστηκε κατά την εγγραφή
        carried_debt = self.initial_debt

        while cursor <= current_month_start:
            year = cursor.year
            month = cursor.month

            last_day_of_month = date(year, month, calendar.monthrange(year, month)[1])

            # Καθορισμός εύρους ημερών για τον υπολογισμό
            if cursor.year == join.year and cursor.month == join.month:
                from_day = join
            else:
                from_day = cursor

            if cursor.year == today.year and cursor.month == today.month:
                to_day = today
            else:
                to_day = last_day_of_month

            # Υπολογισμός απαιτήσεων περιόδου
            required = _count_required_office_days(from_day, to_day)

            # Συνολικές απαιτήσεις (τρέχουσες + παλιό χρέος)
            total_required = required + carried_debt

            # Ημέρες που όντως ήρθε στο γραφείο αυτόν τον μήνα
            office_days = sum(
                1 for d, wt in att_by_date.items()
                if wt == 'OFFICE' and d.year == year and d.month == month
            )

            # Υπολογισμός χρέους που απομένει
            month_debt = max(0, total_required - office_days)

            # Το χρέος μεταφέρεται στον επόμενο κύκλο
            carried_debt = month_debt

            cursor = (cursor + relativedelta(months=1)).replace(day=1)

        return carried_debt

    def get_monthly_report(self):
        """
        Συγκεντρώνει τα στατιστικά του τρέχοντος μήνα.
        """
        today = date.today()
        join = self.date_joined
        year = today.year
        month = today.month

        # Από πότε μετράμε για τον τρέχοντα μήνα
        if join.year == year and join.month == month:
            from_day = join
        else:
            from_day = today.replace(day=1)

        attendances = self.attendance_set.filter(date__month=month, date__year=year)
        office_days = attendances.filter(work_type='OFFICE').count()
        remote_days = attendances.filter(work_type='REMOTE').count()
        leave_days = attendances.filter(work_type__in=['LEAVE', 'SICK']).count()
        total_days = office_days + remote_days

        # Απαιτούμενες ημέρες για το διάστημα που έχει περάσει στον τρέχοντα μήνα
        required_this_month = _count_required_office_days(from_day, today)

        # Συνολικό χρέος (περιλαμβάνει το αρχικό χρέος και το ιστορικό)
        debt = self.get_cumulative_debt()
        is_ok = (debt == 0)

        # Υπόλοιπο μέχρι το πλαφόν των 8 ημερών
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