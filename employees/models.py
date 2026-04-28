from django.db import models
from django.utils import timezone


class Employee(models.Model):
    full_name = models.CharField(max_length=200, verbose_name="Ονοματεπώνυμο")
    email     = models.EmailField(unique=True, verbose_name="Email")

    def __str__(self):
        return self.full_name

    def get_monthly_report(self):
        today       = timezone.now()
        attendances = self.attendance_set.filter(
            date__month=today.month,
            date__year=today.year
        )
        office_days = attendances.filter(work_type='OFFICE').count()
        total_days  = attendances.count()

        # Κανόνας: τουλάχιστον 2 φορές γραφείο ΚΑΙ 8 συνολικά
        is_ok = (office_days >= 2 and total_days >= 8)

        return {
            'office_days': office_days,
            'remote_days': total_days - office_days,
            'total_days':  total_days,
            'is_ok':       is_ok,
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