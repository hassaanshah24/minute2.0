from django import forms
from django.contrib.auth.forms import AuthenticationForm
from .models import CustomUser
from apps.departments.models import Department

class CustomLoginForm(AuthenticationForm):
    username = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control shadow-sm bg-white rounded-3',
            'placeholder': 'Username'
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control shadow-sm bg-white rounded-3',
            'placeholder': 'Password'
        })
    )

class CustomUserAdminForm(forms.ModelForm):
    department = forms.ModelChoiceField(
        queryset=Department.objects.all(),
        required=False,
        help_text="Select a department for the user.",
        widget=forms.Select(attrs={
            'class': 'form-control shadow-sm bg-white rounded-3'
        })
    )

    class Meta:
        model = CustomUser
        fields = '__all__'

    def clean_employee_id(self):
        employee_id = self.cleaned_data.get('employee_id')
        if CustomUser.objects.filter(employee_id=employee_id).exists():
            raise forms.ValidationError(f"A user with employee ID '{employee_id}' already exists.")
        return employee_id


class ProfileUpdateForm(forms.ModelForm):
    department = forms.ModelChoiceField(
        queryset=Department.objects.all(),
        required=False,
        help_text="Select a department.",
        widget=forms.Select(attrs={
            'class': 'form-control shadow-sm bg-white rounded-3'
        })
    )
    profile_picture = forms.ImageField(
        required=False,
        help_text="Upload a profile picture.",
        widget=forms.ClearableFileInput(attrs={
            'class': 'form-control shadow-sm bg-white rounded-3'
        })
    )

    class Meta:
        model = CustomUser
        fields = ['email', 'designation', 'phone_number', 'department', 'profile_picture']
        widgets = {
            'email': forms.EmailInput(attrs={
                'class': 'form-control shadow-sm bg-white rounded-3',
                'placeholder': 'Email'
            }),
            'designation': forms.TextInput(attrs={
                'class': 'form-control shadow-sm bg-white rounded-3',
                'placeholder': 'Designation'
            }),
            'phone_number': forms.TextInput(attrs={
                'class': 'form-control shadow-sm bg-white rounded-3',
                'placeholder': 'Phone Number'
            }),
        }
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if CustomUser.objects.filter(email=email).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("A user with this email already exists.")
        return email
