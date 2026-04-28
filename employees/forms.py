from django import forms
from .models import Employee, Attendance


class EmployeeForm(forms.ModelForm):
    class Meta:
        model  = Employee
        fields = ['full_name', 'email']
        widgets = {
            'full_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'π.χ. Γιώργος Παπαδόπουλος'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'π.χ. gpapadopoulos@company.gr'
            }),
        }


class AttendanceForm(forms.ModelForm):
    class Meta:
        model  = Attendance
        fields = ['employee', 'date', 'work_type']
        widgets = {
            'employee':  forms.Select(attrs={'class': 'form-select'}),
            'date':      forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'work_type': forms.Select(attrs={'class': 'form-select'}),
        }

    def clean_date(self):
        date = self.cleaned_data.get('date')
        if date:
            # 5 = Σάββατο, 6 = Κυριακή
            if date.weekday() in [5, 6]:
                day_name = "Σάββατο" if date.weekday() == 5 else "Κυριακή"
                raise forms.ValidationError(
                    f"❌ Η {date.strftime('%d/%m/%Y')} είναι {day_name}. "
                    f"Δεν επιτρέπονται καταχωρήσεις για Σαββατοκύριακα."
                )
        return date