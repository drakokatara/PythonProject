from django.db import models
from datetime import date, timedelta

class Employee(models.Model):
    full_name = models.CharField(max_length=200, verbose_name="Ονοματεπώνυμο")
    email     = models.EmailField(unique=True, verbose_name="Email")

    def __str__(self):
        return self.full_name

    def get_monthly_report(self):
        today = date.today()
        first_day = today.replace(day=1)

        # Φέρνουμε όλες τις παρουσίες του τρέχοντος μήνα
        attendances = self.attendance_set.filter(
            date__month=today.month,
            date__year=today.year
        )

        office_days = attendances.filter(work_type='OFFICE').count()
        remote_days = attendances.filter(work_type='REMOTE').count()
        total_days = office_days + remote_days

        # Υπολογισμός εβδομάδων που έχουν περάσει (βάσει Δευτέρων)
        weeks_passed = 0
        current_day = first_day
        while current_day <= today:
            if current_day.weekday() == 0:  # 0 = Δευτέρα
                weeks_passed += 1
            current_day += timedelta(days=1)

        # Αν ο μήνας δεν ξεκίνησε Δευτέρα, προσθέτουμε την πρώτη "σπασμένη" εβδομάδα
        if first_day.weekday() != 0:
            weeks_passed += 1

        # Στόχος: 2 παρουσίες γραφείου ανά εβδομάδα που έχει ξεκινήσει
        required_office_so_far = weeks_passed * 2
        if required_office_so_far > 8:
            required_office_so_far = 8

        # Υπολογισμός χρέους (debt)
        debt = required_office_so_far - office_days
        if debt < 0:
            debt = 0

        # Status OK αν έχει πιάσει το στόχο των 8 (ή τον τρέχοντα εβδομαδιαίο στόχο)
        is_ok = (office_days >= required_office_so_far)

        return {
            'office_days': office_days,
            'remote_days': remote_days,
            'total_days': total_days,
            'weeks_passed': weeks_passed,
            'required_office': required_office_so_far,
            'debt': debt,
            'is_ok': is_ok,
        }


class Attendance(models.Model):
    WORK_TYPE_CHOICES = [
        ('OFFICE',  'Στο Γραφείο'),
        ('REMOTE',  'Τηλεργασία'),
    ]

    employee  = models.ForeignKey(Employee, on_delete=models.CASCADE)
    date      = models.DateField()
    work_type = models.CharField(
        max_length=10,
        choices=WORK_TYPE_CHOICES,
        default='REMOTE',
        verbose_name="Τρόπος Εργασίας"
    )

    class Meta:
        # Ένας υπάλληλος δεν μπορεί να έχει δύο καταχωρήσεις την ίδια μέρα
        unique_together = ('employee', 'date')
        ordering = ['-date']

    def __str__(self):
        return f"{self.employee.full_name} — {self.date} ({self.get_work_type_display()})"