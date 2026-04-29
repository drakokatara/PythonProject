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

        # Ορίζουμε τις ελληνικές αργίες για το τρέχον έτος
        gr_holidays = holidays.Greece(years=today.year)

        # Φέρνουμε όλες τις καταχωρήσεις του τρέχοντος μήνα
        attendances = self.attendance_set.filter(
            date__month=today.month,
            date__year=today.year
        )

        office_days = attendances.filter(work_type='OFFICE').count()
        remote_days = attendances.filter(work_type='REMOTE').count()
        leave_days = attendances.filter(work_type__in=['LEAVE', 'SICK']).count()

        total_days = office_days + remote_days + leave_days

        # Υπολογισμός εβδομάδων και αργιών που έπεσαν σε εργάσιμη μέρα (Δευ-Παρ)
        weeks_passed = 0
        holidays_on_weekdays = 0

        curr = first_day
        while curr <= today:
            if curr.weekday() < 5:  # Δευτέρα έως Παρασκευή
                if curr in gr_holidays:
                    holidays_on_weekdays += 1

                # Κάθε Δευτέρα (ή αν είναι η 1η του μήνα) μετράμε μια εβδομάδα
                if curr.weekday() == 0 or curr == first_day:
                    weeks_passed += 1
            curr += timedelta(days=1)

        # Στόχος: 2 παρουσίες/εβδομάδα ΜΕΙΟΝ τις αργίες
        required_office_so_far = (weeks_passed * 2) - holidays_on_weekdays

        # Κόφτες ασφαλείας για τον στόχο
        if required_office_so_far > 8:
            required_office_so_far = 8
        if required_office_so_far < 0:
            required_office_so_far = 0

        # Υπολογισμός χρέους: Μόνο οι ημέρες γραφείου μειώνουν το χρέος.
        # Οι άδειες (leave_days) δεν προσμετρώνται εδώ πλέον.
        debt = required_office_so_far - office_days

        if debt < 0:
            debt = 0

        # Η κατάσταση είναι OK μόνο αν οι ημέρες γραφείου καλύπτουν τον στόχο
        is_ok = (office_days >= required_office_so_far)

        return {
            'office_days': office_days,
            'remote_days': remote_days,
            'leave_days': leave_days,
            'total_days': total_days,
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
        unique_together = ('employee', 'date')  # Ένας υπάλληλος, μία καταχώρηση ανά ημέρα
        verbose_name = "Παρουσία"
        verbose_name_plural = "Παρουσίες"

    def __str__(self):
        return f"{self.employee.full_name} - {self.date} ({self.get_work_type_display()})"