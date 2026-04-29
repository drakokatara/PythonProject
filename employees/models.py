from django.db import models
from datetime import date, timedelta
import holidays


class Employee(models.Model):
    full_name = models.CharField(max_length=200, verbose_name="Ονοματεπώνυμο")
    email = models.EmailField(unique=True, verbose_name="Email")

    def __str__(self):
        return self.full_name

    def get_monthly_report(self):
        today = date.today()
        first_day = today.replace(day=1)

        gr_holidays = holidays.Greece(years=today.year)

        attendances = self.attendance_set.filter(
            date__month=today.month,
            date__year=today.year
        )

        office_days = attendances.filter(work_type='OFFICE').count()
        remote_days = attendances.filter(work_type='REMOTE').count()
        leave_days = attendances.filter(work_type__in=['LEAVE', 'SICK']).count()

        # ΑΛΛΑΓΗ: Το σύνολο μετράει ΜΟΝΟ πραγματική εργασία (Γραφείο ή Remote)
        total_days = office_days + remote_days

        weeks_passed = 0
        holidays_on_weekdays = 0

        curr = first_day
        while curr <= today:
            if curr.weekday() < 5:
                if curr in gr_holidays:
                    holidays_on_weekdays += 1
                if curr.weekday() == 0 or curr == first_day:
                    weeks_passed += 1
            curr += timedelta(days=1)

        required_office_so_far = (weeks_passed * 2) - holidays_on_weekdays

        if required_office_so_far > 8:
            required_office_so_far = 8
        if required_office_so_far < 0:
            required_office_so_far = 0

        # Το χρέος μειώνεται ΜΟΝΟ από τις ημέρες στο γραφείο
        debt = required_office_so_far - office_days

        if debt < 0:
            debt = 0

        is_ok = (office_days >= required_office_so_far)

        return {
            'office_days': office_days,
            'remote_days': remote_days,
            'leave_days': leave_days,  # Παραμένει για να το βλέπεις σαν πληροφορία
            'total_days': total_days,  # Εδώ πλέον δεν περιλαμβάνονται οι άδειες
            'weeks_passed': weeks_passed,
            'holidays_count': holidays_on_weekdays,
            'required_office': required_office_so_far,
            'debt': debt,
            'is_ok': is_ok,
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