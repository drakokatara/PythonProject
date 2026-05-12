from django import forms
from .models import Employee


class EmployeeForm(forms.ModelForm):
    class Meta:
        model  = Employee
        fields = ['full_name', 'email', 'date_joined', 'initial_debt']
        widgets = {
            'full_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'π.χ. Γιώργος Παπαδόπουλος'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'π.χ. gpapadopoulos@company.gr'}),
            'date_joined': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'initial_debt': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
        }